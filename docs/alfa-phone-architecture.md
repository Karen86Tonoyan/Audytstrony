# ALFA Phone — architektura

Lokalny, prywatny asystent AI działający **na własnym urządzeniu użytkownika**.
Dokument opisuje docelową architekturę oraz realistyczne granice tego, co da się
zrobić na telefonie w 2026 r.

---

## Zasada nadrzędna (i granica etyczna)

ALFA Phone działa na urządzeniu należącym do użytkownika, który go świadomie
uruchamia. Każdy dostęp do danych i sprzętu (SMS, kontakty, mikrofon, lokalizacja)
przechodzi przez **widoczny broker uprawnień z potwierdzeniem** — użytkownik w każdej
chwili wie, co agent robi, i może to zablokować.

To odróżnia produkt od oprogramowania szpiegującego: nie ma trybu ukrytego, nie ma
działania bez wiedzy właściciela urządzenia, nie ma zbierania danych osób trzecich
bez podstawy. Ta zasada jest wymaganiem architektonicznym, nie deklaracją
marketingową — jeśli jakakolwiek funkcja ją łamie, nie wchodzi do produktu.

---

## Filozofia

- **Offline-first** — dane użytkownika domyślnie nie opuszczają urządzenia
- **Zero Trust** — każde żądanie do narzędzia jest weryfikowane, nic nie jest zaufane z góry
- **Privacy by design** — minimalizacja danych, lokalne przetwarzanie, szyfrowanie w spoczynku
- **Modularność** — każdy komponent da się wyłączyć lub wymienić
- **Przejrzystość** — użytkownik widzi i kontroluje działania agenta

---

## Warstwy

```
┌─────────────────────────────────────────────┐
│              ALFA Phone (UI)                 │
│         Native Shell — Android / iOS         │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│              Agent Core (Local AI)           │
│  LLM on-device / hybryda • Tool Calling      │
│  Planning • Memory • Oracle (decyzje)        │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│           Cerber — warstwa bezpieczeństwa    │
│  Policy Engine • Prompt Injection Filter     │
│  Permission Broker • Device Attestation      │
│  Runtime Monitoring • Audit Log              │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│           Device Capabilities                │
│  Kamera • Mikrofon • SMS • Kontakty          │
│  Lokalizacja • BT • Wi-Fi • Sensory          │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│        Secure Backend (opcjonalny)           │
│  Sync E2EE • Multi-device • Backup           │
└──────────────────────────────────────────────┘
```

---

## Komponenty

### A. UI (Shell)

- **Android**: Kotlin + Jetpack Compose
- **iOS**: SwiftUI
- **Wspólna logika**: Kotlin Multiplatform (KMP) — realistyczniejsze i dojrzalsze
  niż Skip dla logiki biznesowej i warstwy bezpieczeństwa
- Ekrany: Dashboard (status agenta), Chat, Moduły, Ustawienia uprawnień, Tryb alarmowy

### B. Agent Core

- **Model lokalny**: mały model on-device (Phi-3 / Gemma-2 / Qwen2.5 klasy 2–4B)
  przez `llama.cpp`, MLX (iOS) lub ONNX Runtime
- **Tool calling**: każde narzędzie deklaruje wymagane uprawnienia; wywołanie
  przechodzi przez Cerbera
- **Memory**: lokalne snapshoty + kompresja semantyczna, żeby pamięć nie puchła
- **Oracle**: silnik decyzyjny — co wolno automatycznie, a co wymaga eskalacji do
  użytkownika

> **Realizm on-device.** Model 2–4B na telefonie radzi sobie z prostym tool-callingiem,
> streszczaniem i klasyfikacją, ale nie z złożonym rozumowaniem. Tryb hybrydowy
> (mocniejszy model w chmurze) będzie potrzebny częściej, niż sugeruje „offline-first" —
> i każde takie wyjście poza urządzenie musi być jawne oraz objęte zgodą.

### C. Cerber — warstwa bezpieczeństwa (rdzeń)

Każde żądanie agenta do narzędzia przechodzi przez Cerbera:

- **Policy Engine** — reguły typu „nigdy nie wyślij SMS bez potwierdzenia",
  „lokalizacja tylko w trybie alarmowym"
- **Permission Broker** — pośredniczy w dostępie do sprzętu, pokazuje użytkownikowi
  co i po co
- **Prompt Injection Filter** — ochrona przed przejęciem agenta przez treść
  z zewnątrz (wiadomość, strona, dokument)
- **Device Attestation** — wykrywanie root/jailbreak, weryfikacja integralności
- **Runtime Monitoring + Audit Log** — lokalny, opcjonalnie szyfrowany dziennik działań

### D. Device Capabilities

- Uprawnienia przyznawane świadomie przez użytkownika, odwoływalne w każdej chwili
- Klucze w Android Keystore / iOS Keychain / Secure Enclave
- Respektowanie ograniczeń systemu (App Ops, Doze, background limits) — **nie**
  ich obchodzenie

### E. Backend (opcjonalny)

Tylko do synchronizacji, backupu i funkcji multi-device. Wszystko E2EE.
Stack: Supabase / własny edge + silne szyfrowanie. Domyślnie wyłączony.

---

## Tryby pracy

| Tryb | Opis |
|---|---|
| **Lokalny** (domyślny) | Wszystko na urządzeniu, zero sieci dla danych użytkownika |
| **Hybrydowy** | Lokalny agent + mocniejszy model w chmurze za jawną zgodą |
| **Paranoiczny** | Zero sieci, tylko model lokalny, maksymalne restrykcje Cerbera |
| **Alarmowy** | Szybkie akcje: lokalizacja + powiadomienie zaufanych osób |

---

## Stack

| Warstwa | Technologia | Uwagi |
|---|---|---|
| UI | Kotlin + Compose / SwiftUI | Natywnie, najlepsza wydajność |
| Wspólna logika | Kotlin Multiplatform | Dojrzalsze niż Skip dla tej warstwy |
| Model lokalny | llama.cpp / MLX / ONNX Runtime | Inference on-device |
| Agent | Własny runtime tool-callingu | Pełna kontrola nad Cerberem |
| Bezpieczeństwo | Cerber + Keystore/Keychain | Broker uprawnień + attestation |
| Baza lokalna | SQLite + SQLCipher | Szyfrowana w spoczynku |
| Sync (opc.) | Supabase + E2EE | Domyślnie wyłączony |

---

## Roadmapa

**Faza 1 — MVP (2–3 mies.)**
Android, lokalny chat z małym modelem, podstawowe narzędzia (SMS, kontakty, notatki),
Cerber w wersji podstawowej (permission broker + policy engine).

**Faza 2 — Pełny agent**
Tool calling przez Cerbera, Memory + kompresja, Oracle, tryb alarmowy.

**Faza 3 — Multi-device + iOS**
Sync E2EE, wersja iOS, rozbudowane polityki.

**Faza 4 — Produkcja**
Hardening, audyt zewnętrzny (red team), certyfikaty, monetyzacja.

---

## Otwarte pytania

- Który model lokalny realnie mieści się w budżecie pamięci/baterii telefonu docelowego?
- Gdzie dokładnie przebiega granica lokalny/hybrydowy dla konkretnych funkcji?
- Jak wygląda UX potwierdzeń Cerbera, żeby nie męczył użytkownika, a nadal chronił?
- Model monetyzacji i zgodność (RODO) przy funkcjach multi-device.
