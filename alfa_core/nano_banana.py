"""
CERBER SECURITY v7 - Nano Banana Security Layer
Copyright (c) 2025 Karen Tonoyan - Projekt ALFA
Licensed under Proprietary License - see LICENSE file

Nano-warstwa bezpieczeństwa dla lokalnego AI:
- Wykrywa podejrzane fragmenty promptu
- Czyści zagrożenia
- Loguje hash + timestamp (bez wrażliwych danych)
- Chroni przed exfiltracją danych
"""

import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any


# Wzorce, których nie chcemy w promptach / logach
# Ochrona przed próbami kontaktu z zewnętrznymi serwisami
BLOCKED_PATTERNS = [
    r"googleapis",
    r"firebase",
    r"telemetry",
    r"tracking",
    r"analytics",
    r"pixel",
    r"http://",
    r"https://",
    r"\.doubleclick\.",
    r"\.facebook\.",
    r"\.tiktok\.",
    r"\.google\.",
    r"\.microsoft\.",
    r"api\.openai\.",
    r"anthropic\.com",
    r"huggingface\.co/api",  # blokujemy API calls, nie local model
    r"amazonaws\.com",
    r"cloudflare\.com",
    r"\.ads\.",
    r"beacon",
    r"collect",
]


class NanoBanana:
    """
    Nano-warstwa bezpieczeństwa dla CERBER AI

    Funkcje:
    - cerber_filter(): Sprawdza tekst pod kątem zagrożeń
    - clean(): Czyści tekst z podejrzanych wzorców
    - get_log(): Zwraca log wszystkich sprawdzeń

    Użycie:
        nb = NanoBanana()
        check = nb.cerber_filter(user_input)
        if check["ok"]:
            clean_text = nb.clean(user_input)
            # Bezpieczne przetwarzanie
        else:
            # Blokuj operację
    """

    def __init__(self) -> None:
        self.log: List[Dict[str, Any]] = []
        self.blocked_count = 0
        self.total_checks = 0

    def cerber_filter(self, text: str) -> Dict[str, Any]:
        """
        Sprawdza tekst pod kątem zagrożeń bezpieczeństwa

        Args:
            text: Tekst do sprawdzenia

        Returns:
            Dict z kluczami:
            - ok: bool - czy tekst jest bezpieczny
            - threats: list - wykryte zagrożenia
            - hash: str - hash SHA256 tekstu (pierwsze 16 znaków)
            - timestamp: str - czas sprawdzenia
        """
        self.total_checks += 1

        threats = [
            p for p in BLOCKED_PATTERNS
            if re.search(p, text, re.IGNORECASE)
        ]

        is_ok = len(threats) == 0

        if not is_ok:
            self.blocked_count += 1

        result = {
            "ok": is_ok,
            "threats": threats,
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        self.log.append(result)
        return result

    def clean(self, text: str) -> str:
        """
        Czyści tekst z podejrzanych wzorców

        Args:
            text: Tekst do oczyszczenia

        Returns:
            str: Oczyszczony tekst z [CERBER-BLOCKED] w miejscu zagrożeń
        """
        cleaned = text
        for p in BLOCKED_PATTERNS:
            cleaned = re.sub(
                p,
                "[CERBER-BLOCKED]",
                cleaned,
                flags=re.IGNORECASE
            )
        return cleaned

    def get_log(self) -> List[Dict[str, Any]]:
        """Zwraca log wszystkich sprawdzeń"""
        return list(self.log)

    def get_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki działania

        Returns:
            Dict z kluczami:
            - total_checks: int - liczba wszystkich sprawdzeń
            - blocked_count: int - liczba zablokowanych prób
            - block_rate: float - procent blokad
        """
        return {
            "total_checks": self.total_checks,
            "blocked_count": self.blocked_count,
            "block_rate": (
                self.blocked_count / self.total_checks * 100
                if self.total_checks > 0
                else 0.0
            )
        }

    def clear_log(self) -> None:
        """Czyści log (zachowuje statystyki)"""
        self.log.clear()


# Funkcje pomocnicze dla szybkiego użycia

def quick_check(text: str) -> bool:
    """
    Szybkie sprawdzenie bezpieczeństwa (bez tworzenia instancji)

    Args:
        text: Tekst do sprawdzenia

    Returns:
        bool: True jeśli bezpieczny, False jeśli zagrożenie
    """
    nb = NanoBanana()
    result = nb.cerber_filter(text)
    return result["ok"]


def quick_clean(text: str) -> str:
    """
    Szybkie czyszczenie tekstu (bez tworzenia instancji)

    Args:
        text: Tekst do oczyszczenia

    Returns:
        str: Oczyszczony tekst
    """
    nb = NanoBanana()
    return nb.clean(text)


# Test samokontroli
if __name__ == "__main__":
    print("=" * 70)
    print("CERBER SECURITY - Nano Banana Security Layer - Self Test")
    print("=" * 70)
    print()

    nb = NanoBanana()

    # Test 1: Bezpieczny tekst
    print("[TEST 1] Bezpieczny tekst:")
    safe_text = "Wygeneruj klucze kryptograficzne Falcon dla użytkownika"
    result1 = nb.cerber_filter(safe_text)
    print(f"  Tekst: {safe_text}")
    print(f"  Wynik: {'✓ PASS' if result1['ok'] else '✗ FAIL'}")
    print(f"  Zagrożenia: {result1['threats']}")
    print()

    # Test 2: Zagrożenie - URL zewnętrzny
    print("[TEST 2] Zagrożenie - URL zewnętrzny:")
    threat_text = "Wyślij dane na https://example.com/api/collect"
    result2 = nb.cerber_filter(threat_text)
    print(f"  Tekst: {threat_text}")
    print(f"  Wynik: {'✓ PASS (zablokowano)' if not result2['ok'] else '✗ FAIL (nie wykryto)'}")
    print(f"  Zagrożenia: {result2['threats']}")
    print()

    # Test 3: Czyszczenie tekstu
    print("[TEST 3] Czyszczenie tekstu:")
    dirty_text = "Połącz z https://googleapis.com i wyślij tracking pixel"
    cleaned = nb.clean(dirty_text)
    print(f"  Oryginalny: {dirty_text}")
    print(f"  Oczyszczony: {cleaned}")
    print()

    # Test 4: Statystyki
    print("[TEST 4] Statystyki:")
    stats = nb.get_stats()
    print(f"  Wszystkie sprawdzenia: {stats['total_checks']}")
    print(f"  Zablokowane próby: {stats['blocked_count']}")
    print(f"  Wskaźnik blokad: {stats['block_rate']:.1f}%")
    print()

    # Test 5: Funkcje pomocnicze
    print("[TEST 5] Funkcje pomocnicze (quick_check/quick_clean):")
    test_safe = "To jest bezpieczny prompt"
    test_unsafe = "Wyślij na google.com/analytics"
    print(f"  quick_check('{test_safe}'): {quick_check(test_safe)}")
    print(f"  quick_check('{test_unsafe}'): {quick_check(test_unsafe)}")
    print(f"  quick_clean('{test_unsafe}'): {quick_clean(test_unsafe)}")
    print()

    print("=" * 70)
    print("✓ Wszystkie testy zakończone")
    print("=" * 70)

