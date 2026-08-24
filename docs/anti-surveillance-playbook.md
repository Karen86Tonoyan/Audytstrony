# Playbook: ochrona przed śledzeniem i spyware

Praktyczna lista kontrolna do sprawdzania **własnych** urządzeń — telefonów i
komputerów — pod kątem oprogramowania szpiegującego, stalkerware i monitorowania.
To jednocześnie checklista, którą docelowo automatyzuje panel SHARON.

> **Zakres.** Playbook dotyczy urządzeń, które należą do Ciebie albo których
> właściciel wyraził zgodę na sprawdzenie. Sprawdzanie cudzego urządzenia bez wiedzy
> właściciela jest nielegalne — i nie jest obroną, tylko atakiem.

> **Uczciwe zastrzeżenie.** Żadne narzędzie nie wykrywa wszystkiego. Wynik „czysto"
> oznacza brak *znanych* oznak ataku, a nie absolutną pewność. Pewność daje dopiero
> profesjonalna analiza forensyczna.

---

## Telefon — Android

| Narzędzie | Rola |
|---|---|
| **Google Play Protect** | Wbudowany skan aplikacji (także spoza Play). Sklep Play → profil → Play Protect → Skanuj |
| **Malwarebytes Mobile Security** | Skan malware, audyt uprawnień aplikacji |
| **RethinkDNS** | Firewall i podgląd połączeń aplikacji, bez roota |
| **Hypatia** | Open-source skaner malware; instaluj tylko z F-Droid/GitHub |
| **MVT (Amnesty)** | Analiza forensyczna kopii pod kątem znanego spyware (Pegasus itd.); `mvt-android` |

Przejrzyj ręcznie: **administratorów urządzenia**, dostęp do **ułatwień dostępu**,
aktywne **VPN i profile zarządzania**, aplikacje z dostępem do SMS/kontaktów/lokalizacji.

## Telefon — iPhone

| Narzędzie | Rola |
|---|---|
| **Lockdown Mode** | Tryb wysokiego bezpieczeństwa Apple — zmniejsza powierzchnię ataku |
| **Safety Check** | Przegląd, kto/co ma dostęp do lokalizacji, zdjęć, mikrofonu |
| **MVT dla iOS** | Analiza zaszyfrowanej kopii pod kątem wskaźników kompromitacji |
| **iVerify** | Komercyjny threat hunting dla osób/organizacji wysokiego ryzyka |

## Komputer — Windows

| Narzędzie | Rola |
|---|---|
| **Microsoft Defender** | Ochrona w czasie rzeczywistym + pełne skanowanie |
| **Microsoft Defender Offline** | Skan przed startem Windows — utrudnia ukrycie się rootkitom |
| **Malwarebytes** | Dodatkowy skaner (druga opinia) |
| **Autoruns** (Sysinternals) | Co startuje razem z systemem |
| **TCPView** (Sysinternals) | Aktywne połączenia i procesy |
| **Wireshark** | Analiza ruchu — wymaga interpretacji |

## Komputer — macOS / Linux

| Narzędzie | Platforma | Rola |
|---|---|---|
| **KnockKnock** | macOS | Trwałe mechanizmy uruchamiania |
| **LuLu** | macOS | Firewall połączeń wychodzących |
| **Malwarebytes** | macOS | Skan malware/PUP |
| **Lynis** | Linux/macOS | Audyt konfiguracji bezpieczeństwa |
| **rkhunter** | Linux | Kontrola rootkitów |
| **ClamAV** | Linux/macOS | Skaner AV (jako dodatek, nie jedyna ochrona) |

## Ochrona przed śledzeniem w sieci

- **Firefox + uBlock Origin** / **Brave** — blokowanie trackerów i fingerprintingu
- **NextDNS** / **AdGuard DNS** — filtrowanie domen śledzących i malware na poziomie DNS
- **Privacy Badger** — ograniczanie skryptów śledzących
- **EFF Cover Your Tracks** — test, jak przeglądarka jest identyfikowana
- **Mullvad VPN** — ogranicza obserwację ruchu przez sieć/dostawcę (nie chroni przed malware, nie daje anonimowości)
- **Signal** — szyfrowana komunikacja (nie zabezpieczy zainfekowanego urządzenia)

---

## Kolejność kontroli (gdy podejrzewasz kompromitację)

1. **Odłącz urządzenie od sieci**, ale **nie kasuj danych**, jeśli mogą być dowodem.
2. **Kopia ważnych danych** na bezpieczny nośnik — bez przenoszenia nieznanych plików wykonywalnych.
3. **Android**: Play Protect + Malwarebytes; przegląd uprawnień, administratorów, ułatwień dostępu, VPN.
4. **iPhone**: aktualizacje, Safety Check, rozważ Lockdown Mode, MVT przy konkretnym podejrzeniu.
5. **Windows**: pełny skan Defender → **Defender Offline** → Autoruns → TCPView.
6. **Zmień hasła z INNEGO, zaufanego urządzenia**, włącz MFA — najlepiej **kluczem sprzętowym FIDO2/WebAuthn** — i wyloguj wszystkie sesje.
7. **Nie instaluj losowych aplikacji „anty-haker"** — część sama zbiera dane lub straszy fałszywym alarmem.

## Gdy podejrzewasz zaawansowany atak (mercenary spyware)

- **Nie resetuj** telefonu przed zabezpieczeniem dowodów — reset niszczy ślady.
- MVT wymaga wiedzy technicznej i **nie wykryje najnowszego spyware** bez aktualnych
  wskaźników kompromitacji. Amnesty wprost to zaznacza.
- Przy realnym podejrzeniu — analiza forensyczna (patrz [karta usługi forensyki](forensics-android.md)).

---

## Zalecany zestaw minimum (dla programisty)

- **Telefon**: Play Protect + Malwarebytes + MVT
- **Windows**: Defender Offline + Autoruns + TCPView
- **Sieć**: Firefox/Brave + uBlock Origin + NextDNS
- **Konta**: passkeys / klucz FIDO2 zamiast haseł i kodów odzyskiwania

---

## Źródła

- [Amnesty Security Lab — Tools and Guides (MVT)](https://securitylab.amnesty.org/tools-and-guides/)
- [MVT — mvt-project](https://github.com/mvt-project/mvt)
- [EFF — Surveillance Self-Defense](https://ssd.eff.org/)
- [EFF — Cover Your Tracks](https://www.eff.org/pages/cover-your-tracks)
- [Microsoft Defender Offline](https://learn.microsoft.com/en-us/defender-endpoint/microsoft-defender-offline)
- [Apple — Lockdown Mode](https://support.apple.com/guide/security/sec2437264f0/web)
- [CISA — Mobile Cybersecurity Shared Services](https://www.cisa.gov/resources-tools/services/mobile-cybersecurity-shared-services)
- [SafetyDetectives — Best Anti-Spyware Software 2026](https://www.safetydetectives.com/blog/the-best-anti-spyware-software/)
- [privacytools.io — Device Integrity Tools 2026](https://privacytools.io/device-integrity)
