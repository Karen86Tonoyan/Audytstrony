"""
CERBER SECURITY v7 - Local AI Bridge (PHI-3)
Copyright (c) 2025 Karen Tonoyan - Projekt ALFA
Licensed under Proprietary License - see LICENSE file

Lokalny mostek do modelu PHI-3:
- Całkowicie offline (bez połączeń zewnętrznych)
- Integracja z nano_banana (warstwa bezpieczeństwa)
- Support dla CPU i CUDA
- CLI interaktywny i batch mode
"""

import os
import sys
import json
import argparse
from typing import Optional

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARNING] torch / transformers not installed!")

# Import nano_banana (bezpieczeństwo)
try:
    from nano_banana import NanoBanana
except ImportError:
    # Fallback jeśli nie może zaimportować
    print("[WARNING] nano_banana not found, running without security layer!")
    class NanoBanana:  # type: ignore
        def cerber_filter(self, text):
            return {"ok": True, "threats": []}
        def clean(self, text):
            return text


# ============================================================================
# KONFIGURACJA
# ============================================================================

# Ścieżka do lokalnego modelu PHI-3
# Oczekujemy struktury: models/phi-3-mini-4k-instruct/*
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "phi-3-mini-4k-instruct")

# Auto-detekcja CUDA lub CPU
DEVICE = "cuda" if torch.cuda.is_available() if TORCH_AVAILABLE else False else "cpu"

# Cache dla modelu (singleton pattern)
_tokenizer: Optional[Any] = None
_model: Optional[Any] = None


# ============================================================================
# FUNKCJE GŁÓWNE
# ============================================================================

def check_dependencies() -> bool:
    """
    Sprawdza czy wszystkie zależności są dostępne

    Returns:
        bool: True jeśli wszystko OK
    """
    if not TORCH_AVAILABLE:
        print("[ERROR] PyTorch / Transformers not installed")
        print("Install: pip install torch transformers")
        return False

    if not os.path.isdir(MODEL_PATH):
        print(f"[ERROR] Model path not found: {MODEL_PATH}")
        print()
        print("INSTRUKCJA INSTALACJI MODELU PHI-3:")
        print("1. Pobierz model z: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct")
        print("2. Rozpakuj do: models/phi-3-mini-4k-instruct/")
        print("3. Struktura powinna wyglądać:")
        print("   models/phi-3-mini-4k-instruct/")
        print("     ├── config.json")
        print("     ├── tokenizer.json")
        print("     ├── model.safetensors")
        print("     └── ...")
        return False

    return True


def load_model():
    """
    Ładuje model PHI-3 do pamięci (singleton pattern)

    Returns:
        tuple: (tokenizer, model)

    Raises:
        RuntimeError: Jeśli model nie może zostać załadowany
    """
    global _tokenizer, _model

    # Jeśli już załadowany - zwróć z cache
    if _tokenizer is not None and _model is not None:
        return _tokenizer, _model

    if not check_dependencies():
        raise RuntimeError("Dependencies not met - cannot load model")

    print(f"[AI] Loading PHI-3 from: {MODEL_PATH}")
    print(f"[AI] Device: {DEVICE}")

    # Załaduj tokenizer
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    # Wybierz dtype zależnie od urządzenia
    if DEVICE == "cuda":
        torch_dtype = torch.float16  # fp16 dla GPU
    else:
        torch_dtype = torch.float32  # fp32 dla CPU

    # Załaduj model
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch_dtype,
        device_map="auto" if DEVICE == "cuda" else None,
        trust_remote_code=True,  # PHI-3 może wymagać custom code
    )

    # Przenieś na odpowiednie urządzenie
    if DEVICE == "cpu":
        _model.to("cpu")

    # Tryb ewaluacji (nie trenujemy)
    _model.eval()

    print(f"[AI] Model loaded successfully (device: {DEVICE})")
    return _tokenizer, _model


def generate_local_response(
    prompt: str,
    max_new_tokens: int = 256,
    temperature: float = 0.4,
    top_p: float = 0.9,
) -> str:
    """
    Główna funkcja: generuje odpowiedź z lokalnego PHI-3

    Przepływ:
    1. Prompt → nano_banana (filtr bezpieczeństwa)
    2. Jeśli OK → czyszczenie
    3. Generacja z PHI-3
    4. Post-processing
    5. Zwrot odpowiedzi

    Args:
        prompt: Zapytanie użytkownika
        max_new_tokens: Max długość odpowiedzi (default: 256)
        temperature: Kreatywność modelu (0.0-1.0, default: 0.4)
        top_p: Nucleus sampling (default: 0.9)

    Returns:
        str: Odpowiedź modelu lub błąd

    Security:
        Cały prompt jest filtrowany przez nano_banana
    """
    # KROK 1: Bezpieczeństwo - nano_banana filter
    nb = NanoBanana()
    check = nb.cerber_filter(prompt)

    if not check["ok"]:
        threats_str = ", ".join(check["threats"])
        return (
            f"[CERBER BLOCK] Wykryto zagrożenia bezpieczeństwa\n"
            f"Wzorce: {threats_str}\n"
            f"Hash: {check['hash']}\n"
            f"Czas: {check['timestamp']}\n\n"
            f"Ten prompt został zablokowany przez warstwę bezpieczeństwa Cerber."
        )

    # KROK 2: Czyszczenie (nawet jeśli check ok, czyścimy na wszelki wypadek)
    cleaned = nb.clean(prompt)

    # KROK 3: Załaduj model
    try:
        tokenizer, model = load_model()
    except Exception as e:
        return f"[ERROR] Nie można załadować modelu: {str(e)}"

    # KROK 4: Tokenizacja
    inputs = tokenizer(cleaned, return_tensors="pt")

    if DEVICE == "cuda":
        inputs = inputs.to("cuda")
    else:
        inputs = inputs.to("cpu")

    # KROK 5: Generacja
    try:
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
    except Exception as e:
        return f"[ERROR] Błąd podczas generacji: {str(e)}"

    # KROK 6: Dekodowanie
    text = tokenizer.decode(output[0], skip_special_tokens=True)

    # KROK 7: Post-processing
    # PHI-3 czasem powtarza prompt - odcinamy
    if text.startswith(cleaned):
        text = text[len(cleaned):].lstrip()

    # Usuń nadmiarowe białe znaki
    text = text.strip()

    if not text:
        return "[INFO] Model nie wygenerował odpowiedzi (pusta odpowiedź)"

    return text


# ============================================================================
# FUNKCJE TESTOWE
# ============================================================================

def self_test() -> int:
    """
    Test samokontroli dla instalatora .bat

    Sprawdza:
    - Dostępność zależności
    - Obecność modelu
    - Możliwość generacji prostej odpowiedzi

    Returns:
        int: 0 przy powodzeniu, 1 przy błędzie
    """
    print("=" * 70)
    print("CERBER AI LOCAL - Self Test")
    print("=" * 70)
    print()

    # Test 1: Zależności
    print("[TEST 1/4] Sprawdzanie zależności...")
    if not TORCH_AVAILABLE:
        print("  [✗] PyTorch / Transformers NOT INSTALLED")
        print("  Zainstaluj: pip install torch transformers")
        return 1
    else:
        print("  [✓] PyTorch / Transformers OK")

    # Test 2: Model path
    print()
    print("[TEST 2/4] Sprawdzanie ścieżki modelu...")
    if not os.path.isdir(MODEL_PATH):
        print(f"  [✗] Model NOT FOUND: {MODEL_PATH}")
        print("  Pobierz PHI-3 z Hugging Face")
        return 1
    else:
        print(f"  [✓] Model path exists: {MODEL_PATH}")

    # Test 3: Ładowanie modelu
    print()
    print("[TEST 3/4] Ładowanie modelu do pamięci...")
    try:
        tokenizer, model = load_model()
        print("  [✓] Model załadowany pomyślnie")
    except Exception as e:
        print(f"  [✗] Błąd ładowania: {str(e)}")
        return 1

    # Test 4: Generacja odpowiedzi
    print()
    print("[TEST 4/4] Test generacji odpowiedzi...")
    try:
        prompt = (
            "Jesteś lokalnym modelem AI systemu Cerber Security. "
            "Odpowiedz jednym krótkim zdaniem po polsku: Co to jest Cerber?"
        )
        reply = generate_local_response(prompt, max_new_tokens=64)

        if not reply:
            print("  [✗] PUSTA ODPOWIEDŹ – coś jest nie tak")
            return 1

        if reply.startswith("[CERBER BLOCK]") or reply.startswith("[ERROR]"):
            print(f"  [✗] Błąd w odpowiedzi: {reply}")
            return 1

        print("  [✓] Model odpowiedział:")
        print(f"      \"{reply}\"")

    except Exception as e:
        print(f"  [✗] Wyjątek: {str(e)}")
        return 1

    # Sukces!
    print()
    print("=" * 70)
    print("✓ Wszystkie testy przeszły pomyślnie!")
    print("CERBER AI LOCAL jest gotowy do użycia")
    print("=" * 70)
    return 0


# ============================================================================
# CLI INTERFACE
# ============================================================================

def interactive_mode():
    """
    Tryb interaktywny - chat z lokalnym AI

    Użytkownik wpisuje pytania, AI odpowiada
    Zakończenie: CTRL+C lub 'exit'
    """
    print("=" * 70)
    print("CERBER AI LOCAL - Tryb Interaktywny (PHI-3)")
    print("=" * 70)
    print()
    print("Wpisz swoje pytanie, naciśnij Enter.")
    print("Zakończ przez: 'exit', 'quit' lub CTRL+C")
    print()
    print("-" * 70)

    try:
        while True:
            user_input = input("\n[TY] > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n[EXIT] Zakończono sesję.")
                break

            print()
            print("[AI] Generuję odpowiedź...")
            answer = generate_local_response(user_input)

            print()
            print(f"[AI] > {answer}")
            print()
            print("-" * 70)

    except KeyboardInterrupt:
        print("\n\n[EXIT] Zakończono przez CTRL+C.")
    except Exception as e:
        print(f"\n[ERROR] Nieoczekiwany błąd: {str(e)}")


def main():
    """
    Główny punkt wejścia CLI

    Obsługuje:
    - --self-test: Test systemu (dla instalatora)
    - --prompt "text": Pojedyncze pytanie
    - bez argumentów: Tryb interaktywny
    """
    parser = argparse.ArgumentParser(
        description="CERBER AI Local Bridge (PHI-3 + nano_banana)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:

  1. Test systemu (dla instalatora):
     python ai_local.py --self-test

  2. Pojedyncze pytanie:
     python ai_local.py --prompt "Kim jest Cerber?"

  3. Tryb interaktywny (domyślny):
     python ai_local.py

Copyright (c) 2025 Karen Tonoyan - Projekt ALFA
        """
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Uruchom test integracyjny (dla instalatora .bat)",
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="Zadaj pojedyncze pytanie lokalnemu modelowi",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maksymalna długość odpowiedzi (default: 256)",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="Temperatura generacji 0.0-1.0 (default: 0.4)",
    )

    args = parser.parse_args()

    # Opcja 1: Self-test
    if args.self_test:
        exit_code = self_test()
        sys.exit(exit_code)

    # Opcja 2: Pojedyncze pytanie
    if args.prompt:
        answer = generate_local_response(
            args.prompt,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        print(answer)
        sys.exit(0)

    # Opcja 3: Tryb interaktywny (domyślny)
    interactive_mode()


if __name__ == "__main__":
    main()

