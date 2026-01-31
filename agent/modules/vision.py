"""
Moduł Vision - Widzenie Agenta
==============================
Obsługuje:
- Przechwytywanie ekranu (screenshots)
- OCR (rozpoznawanie tekstu)
- Analizę obrazów z AI
- Detekcję elementów UI
- Śledzenie zmian na ekranie
"""

import asyncio
import base64
import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import mss
import mss.tools
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import numpy as np
from loguru import logger

from agent.config.settings import get_settings


@dataclass
class ScreenRegion:
    """Definicja regionu ekranu."""
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        return {"left": self.x, "top": self.y, "width": self.width, "height": self.height}

    def center(self) -> Tuple[int, int]:
        """Środek regionu."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class DetectedText:
    """Wykryty tekst z OCR."""
    text: str
    confidence: float
    bbox: ScreenRegion
    level: int = 0  # Block, paragraph, line, word

    def __str__(self) -> str:
        return f"{self.text} (conf: {self.confidence:.2f})"


@dataclass
class UIElement:
    """Wykryty element interfejsu."""
    type: str  # button, textfield, checkbox, etc.
    text: Optional[str]
    region: ScreenRegion
    confidence: float
    properties: Dict[str, Any] = None

    def click_point(self) -> Tuple[int, int]:
        """Punkt do kliknięcia (środek elementu)."""
        return self.region.center()


class VisionModule:
    """
    Moduł widzenia agenta - analiza ekranu i obrazów.
    """

    def __init__(self):
        self.settings = get_settings().vision
        self._sct = None
        self._ensure_dirs()

        logger.info("VisionModule zainicjalizowany")

    def _ensure_dirs(self):
        """Upewnij się że katalogi istnieją."""
        self.settings.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def _get_sct(self) -> mss.mss:
        """Lazy initialization screen capture."""
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    # ==================== Screenshots ====================

    async def capture_screen(
        self,
        monitor: int = None,
        region: ScreenRegion = None,
        save_path: Path = None
    ) -> bytes:
        """
        Przechwyć ekran lub jego część.

        Args:
            monitor: Numer monitora (None = wszystkie)
            region: Region do przechwycenia
            save_path: Opcjonalna ścieżka do zapisu

        Returns:
            Bytes obrazu PNG
        """
        sct = self._get_sct()

        if region:
            grab_area = region.to_dict()
        elif monitor is not None:
            grab_area = sct.monitors[monitor]
        else:
            grab_area = sct.monitors[self.settings.monitor_index]

        # Przechwyć
        screenshot = sct.grab(grab_area)

        # Konwertuj do PNG bytes
        png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)

        # Opcjonalnie zapisz
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(png_bytes)
            logger.debug(f"Screenshot zapisany: {save_path}")

        return png_bytes

    async def capture_screen_pil(
        self,
        monitor: int = None,
        region: ScreenRegion = None
    ) -> Image.Image:
        """Przechwyć ekran jako PIL Image."""
        png_bytes = await self.capture_screen(monitor, region)
        return Image.open(io.BytesIO(png_bytes))

    async def capture_with_timestamp(self, prefix: str = "screenshot") -> Path:
        """Przechwyć i zapisz z timestampem."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        save_path = self.settings.screenshot_dir / filename
        await self.capture_screen(save_path=save_path)
        return save_path

    async def capture_window(self, window_title: str) -> Optional[bytes]:
        """
        Przechwyć konkretne okno (Windows).
        """
        try:
            import pyautogui
            import pygetwindow as gw

            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                logger.warning(f"Nie znaleziono okna: {window_title}")
                return None

            window = windows[0]
            region = ScreenRegion(
                x=window.left,
                y=window.top,
                width=window.width,
                height=window.height
            )
            return await self.capture_screen(region=region)

        except ImportError:
            logger.error("pygetwindow nie jest zainstalowany")
            return None

    # ==================== OCR ====================

    async def extract_text(
        self,
        image: Union[bytes, Path, Image.Image],
        lang: str = None
    ) -> str:
        """
        Wyodrębnij tekst z obrazu (OCR).

        Args:
            image: Obraz jako bytes, ścieżka lub PIL Image
            lang: Język OCR (np. 'pol', 'eng', 'pol+eng')

        Returns:
            Rozpoznany tekst
        """
        # Konwertuj do PIL Image
        if isinstance(image, bytes):
            pil_image = Image.open(io.BytesIO(image))
        elif isinstance(image, Path):
            pil_image = Image.open(image)
        else:
            pil_image = image

        lang = lang or self.settings.ocr_language

        # OCR w osobnym wątku (CPU intensive)
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None,
            lambda: pytesseract.image_to_string(pil_image, lang=lang)
        )

        return text.strip()

    async def extract_text_with_boxes(
        self,
        image: Union[bytes, Path, Image.Image],
        lang: str = None,
        min_confidence: float = 60.0
    ) -> List[DetectedText]:
        """
        Wyodrębnij tekst z pozycjami (bounding boxes).

        Returns:
            Lista DetectedText z pozycjami
        """
        # Konwertuj do PIL Image
        if isinstance(image, bytes):
            pil_image = Image.open(io.BytesIO(image))
        elif isinstance(image, Path):
            pil_image = Image.open(image)
        else:
            pil_image = image

        lang = lang or self.settings.ocr_language

        # OCR z danymi szczegółowymi
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: pytesseract.image_to_data(pil_image, lang=lang, output_type=pytesseract.Output.DICT)
        )

        results = []
        n_boxes = len(data['level'])

        for i in range(n_boxes):
            conf = float(data['conf'][i])
            text = data['text'][i].strip()

            if conf >= min_confidence and text:
                region = ScreenRegion(
                    x=data['left'][i],
                    y=data['top'][i],
                    width=data['width'][i],
                    height=data['height'][i]
                )
                results.append(DetectedText(
                    text=text,
                    confidence=conf / 100.0,
                    bbox=region,
                    level=data['level'][i]
                ))

        return results

    async def extract_text_from_screen(self) -> str:
        """Przechwyć ekran i wyodrębnij tekst."""
        screenshot = await self.capture_screen()
        return await self.extract_text(screenshot)

    async def find_text_on_screen(
        self,
        search_text: str,
        case_sensitive: bool = False
    ) -> List[DetectedText]:
        """
        Znajdź tekst na ekranie i zwróć jego pozycje.

        Args:
            search_text: Tekst do znalezienia
            case_sensitive: Czy uwzględniać wielkość liter

        Returns:
            Lista znalezionych wystąpień z pozycjami
        """
        screenshot = await self.capture_screen()
        all_text = await self.extract_text_with_boxes(screenshot)

        if not case_sensitive:
            search_text = search_text.lower()

        results = []
        for item in all_text:
            text = item.text if case_sensitive else item.text.lower()
            if search_text in text:
                results.append(item)

        return results

    # ==================== Detekcja Elementów UI ====================

    async def detect_buttons(
        self,
        image: Union[bytes, Path, Image.Image] = None
    ) -> List[UIElement]:
        """
        Wykryj przyciski na obrazie/ekranie.
        Używa kombinacji OCR i detekcji kształtów.
        """
        if image is None:
            image = await self.capture_screen()

        # Konwertuj do numpy array dla OpenCV
        if isinstance(image, bytes):
            nparr = np.frombuffer(image, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image, Path):
            cv_image = cv2.imread(str(image))
        else:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Konwertuj do grayscale
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Detekcja krawędzi
        edges = cv2.Canny(gray, 50, 150)

        # Znajdź kontury
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        buttons = []
        for contour in contours:
            # Aproksymacja konturu
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Sprawdź czy to prostokąt (4 wierzchołki)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)

                # Filtruj po rozmiarze (typowy przycisk)
                if 30 < w < 500 and 20 < h < 100:
                    region = ScreenRegion(x=x, y=y, width=w, height=h)

                    # Wyodrębnij tekst z regionu
                    roi = cv_image[y:y+h, x:x+w]
                    roi_pil = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                    text = await self.extract_text(roi_pil)

                    buttons.append(UIElement(
                        type="button",
                        text=text if text else None,
                        region=region,
                        confidence=0.7
                    ))

        return buttons

    async def detect_text_fields(
        self,
        image: Union[bytes, Path, Image.Image] = None
    ) -> List[UIElement]:
        """Wykryj pola tekstowe na obrazie/ekranie."""
        if image is None:
            image = await self.capture_screen()

        # Podobna logika jak dla przycisków, ale szukamy dłuższych prostokątów
        if isinstance(image, bytes):
            nparr = np.frombuffer(image, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image, Path):
            cv_image = cv2.imread(str(image))
        else:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_fields = []
        for contour in contours:
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)

                # Pola tekstowe są zwykle szersze niż wysokie
                if w > 100 and 20 < h < 60 and w / h > 3:
                    region = ScreenRegion(x=x, y=y, width=w, height=h)
                    text_fields.append(UIElement(
                        type="textfield",
                        text=None,
                        region=region,
                        confidence=0.6
                    ))

        return text_fields

    # ==================== Porównywanie Obrazów ====================

    async def compare_images(
        self,
        image1: Union[bytes, Path, Image.Image],
        image2: Union[bytes, Path, Image.Image]
    ) -> float:
        """
        Porównaj dwa obrazy i zwróć podobieństwo (0-1).
        """
        # Konwertuj do numpy arrays
        def to_numpy(img):
            if isinstance(img, bytes):
                nparr = np.frombuffer(img, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(img, Path):
                return cv2.imread(str(img))
            else:
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        img1 = to_numpy(image1)
        img2 = to_numpy(image2)

        # Upewnij się że mają ten sam rozmiar
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

        # Oblicz różnicę
        diff = cv2.absdiff(img1, img2)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Oblicz podobieństwo
        similarity = 1.0 - (np.mean(diff_gray) / 255.0)

        return similarity

    async def find_image_on_screen(
        self,
        template: Union[bytes, Path, Image.Image],
        threshold: float = 0.8
    ) -> Optional[ScreenRegion]:
        """
        Znajdź obraz na ekranie (template matching).

        Args:
            template: Obraz wzorcowy do znalezienia
            threshold: Próg dopasowania (0-1)

        Returns:
            Region gdzie znaleziono obraz lub None
        """
        screenshot = await self.capture_screen()

        # Konwertuj do OpenCV
        screen_arr = np.frombuffer(screenshot, np.uint8)
        screen = cv2.imdecode(screen_arr, cv2.IMREAD_COLOR)

        if isinstance(template, bytes):
            tmpl_arr = np.frombuffer(template, np.uint8)
            tmpl = cv2.imdecode(tmpl_arr, cv2.IMREAD_COLOR)
        elif isinstance(template, Path):
            tmpl = cv2.imread(str(template))
        else:
            tmpl = cv2.cvtColor(np.array(template), cv2.COLOR_RGB2BGR)

        # Template matching
        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = tmpl.shape[:2]
            return ScreenRegion(
                x=max_loc[0],
                y=max_loc[1],
                width=w,
                height=h
            )

        return None

    # ==================== Monitoring Ekranu ====================

    async def wait_for_change(
        self,
        region: ScreenRegion = None,
        timeout: float = 30.0,
        threshold: float = 0.05
    ) -> bool:
        """
        Czekaj aż coś się zmieni na ekranie.

        Args:
            region: Region do monitorowania (None = cały ekran)
            timeout: Maksymalny czas oczekiwania
            threshold: Minimalna zmiana do wykrycia (0-1)

        Returns:
            True jeśli wykryto zmianę, False jeśli timeout
        """
        initial = await self.capture_screen(region=region)
        start_time = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(self.settings.capture_interval)

            current = await self.capture_screen(region=region)
            similarity = await self.compare_images(initial, current)

            if similarity < (1.0 - threshold):
                logger.debug(f"Wykryto zmianę na ekranie (similarity: {similarity:.2f})")
                return True

            if asyncio.get_event_loop().time() - start_time > timeout:
                return False

    async def wait_for_text(
        self,
        text: str,
        timeout: float = 30.0,
        interval: float = 1.0
    ) -> Optional[DetectedText]:
        """
        Czekaj aż określony tekst pojawi się na ekranie.

        Returns:
            DetectedText jeśli znaleziono, None jeśli timeout
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            results = await self.find_text_on_screen(text)
            if results:
                return results[0]

            if asyncio.get_event_loop().time() - start_time > timeout:
                return None

            await asyncio.sleep(interval)

    # ==================== Pomocnicze ====================

    async def annotate_image(
        self,
        image: Union[bytes, Path, Image.Image],
        annotations: List[Tuple[ScreenRegion, str, str]]  # (region, label, color)
    ) -> Image.Image:
        """
        Dodaj adnotacje do obrazu.

        Args:
            image: Obraz bazowy
            annotations: Lista (region, etykieta, kolor)

        Returns:
            Obraz z adnotacjami
        """
        if isinstance(image, bytes):
            pil_image = Image.open(io.BytesIO(image))
        elif isinstance(image, Path):
            pil_image = Image.open(image)
        else:
            pil_image = image.copy()

        draw = ImageDraw.Draw(pil_image)

        for region, label, color in annotations:
            # Rysuj prostokąt
            draw.rectangle(
                [region.x, region.y, region.x + region.width, region.y + region.height],
                outline=color,
                width=2
            )
            # Dodaj etykietę
            draw.text((region.x, region.y - 15), label, fill=color)

        return pil_image

    def image_to_base64(self, image: Union[bytes, Path, Image.Image]) -> str:
        """Konwertuj obraz do base64."""
        if isinstance(image, bytes):
            return base64.b64encode(image).decode("utf-8")
        elif isinstance(image, Path):
            with open(image, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        else:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ==================== Singleton ====================

_vision_module: Optional[VisionModule] = None


def get_vision() -> VisionModule:
    """Pobierz singleton modułu Vision."""
    global _vision_module
    if _vision_module is None:
        _vision_module = VisionModule()
    return _vision_module
