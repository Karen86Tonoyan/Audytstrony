# Cerber — Policy Matrix

Reguły, według których Cerber (warstwa bezpieczeństwa [ALFA Phone](alfa-phone-architecture.md))
ocenia każde żądanie agenta do narzędzia, integracji lub zasobu zewnętrznego.

## Model decyzyjny

1. **Default-deny.** Co nie jest jawnie dozwolone — jest zablokowane.
2. **Tryb pracy zawęża, nigdy nie rozszerza.** Reguła trybu Paranoicznego przebija
   każde pozwolenie z trybu łagodniejszego.
3. **Zgoda + audyt.** Działania podwyższonego ryzyka wymagają jawnego potwierdzenia
   użytkownika i wpisu w logu audytowym.
4. **Treść zewnętrzna to dane, nie polecenia.** Wiadomość, strona czy dokument nie
   mogą wywołać akcji (instalacja, wysyłka, eksfiltracja) — nawet jeśli o to „proszą".

## Poziomy decyzji

| Poziom | Znaczenie |
|---|---|
| **ALLOW** | Dozwolone automatycznie |
| **CONFIRM** | Wymaga jawnej zgody użytkownika |
| **AUDIT** | Dozwolone, ale z obowiązkowym logiem |
| **DENY** | Zablokowane |
| **DENY+KEY** | Zablokowane; odblokowanie tylko Master Key + uzasadnienie w audycie |

---

## Matryca

| Kategoria żądania | Lokalny | Hybrydowy | Paranoiczny |
|---|---|---|---|
| Odczyt lokalnej pamięci / notatek | ALLOW | ALLOW | ALLOW |
| Wysłanie SMS / wiadomości | CONFIRM | CONFIRM | DENY |
| Odczyt kontaktów / call log | CONFIRM+AUDIT | CONFIRM+AUDIT | DENY |
| Kamera / mikrofon | CONFIRM | CONFIRM | DENY |
| Lokalizacja | CONFIRM | CONFIRM | DENY (poza trybem alarmowym) |
| Wyjście do modelu w chmurze | DENY | CONFIRM+AUDIT | DENY |
| **Third-party Endpoint Agents** | **DENY+KEY** | **DENY+KEY** | **DENY** |
| **Messenger / Meta Platform** | DENY | CONFIRM+AUDIT (scope-limited) | DENY |
| Pobranie/uruchomienie binarium z sieci | DENY+KEY | DENY+KEY | DENY |
| Zmiana polityk Cerbera | DENY+KEY | DENY+KEY | DENY+KEY |

---

## Reguła: Third-party Endpoint Agents

**Domyślnie DENY+KEY.** Dotyczy każdego zewnętrznego agenta klasy Device/Endpoint
Protection (EDR/XDR, „ochrona urządzenia"), niezależnie od dostawcy.

Uzasadnienie:
- taki agent z definicji wymaga uprawnień bliskich SYSTEM/root,
- często dystrybuowany jako gotowe binarium bez publicznego kodu źródłowego,
- kompromitacja kanału dystrybucji (np. prywatny S3, workflow CI bez weryfikacji
  podpisu) = złośliwy agent instalowany jako „oficjalny" → pełne przejęcie endpointu.

Warunki ewentualnego dopuszczenia (wszystkie naraz):
- analiza wyłącznie w izolowanej VM / testowym urządzeniu z monitoringiem sieci
  i drzewa procesów,
- weryfikacja **checksum + podpisu** artefaktu (samo `curl --fail` nie wystarcza),
- Master Key + wpis w audycie z uzasadnieniem,
- nigdy na maszynie produkcyjnej / z danymi użytkownika bez izolacji.

## Reguła: Messenger / Meta Platform

Business messaging (Page / Instagram Professional / boty) **nie jest E2EE** — treść
widzi biznes, podłączona aplikacja i Meta jako operator. Traktujemy jak kanał
zewnętrzny, nie prywatny.

- Tryb Lokalny / Paranoiczny: **DENY**.
- Tryb Hybrydowy: **CONFIRM+AUDIT**, ograniczony scope (`pages_messaging`), tylko
  do jawnie zaakceptowanego przypadku (customer care / leady).
- Page Access Token = credential wysokiego ryzyka: rotacja, storage w Keystore/Secure
  Enclave, **nigdy w logach**.
- Webhook endpoint hardened: `verify_token` + walidacja podpisu (`appsecret_proof`,
  HMAC-SHA256) + rate limiting + IP allowlist, jeśli możliwe.
- Dane z Platformy **nie mieszają się** z lokalnymi Memory Snapshots — osobny,
  zaszyfrowany kontekst.

## Reguła: pobieranie i uruchamianie binariów

Pobranie i uruchomienie kodu wykonywalnego z sieci to **DENY+KEY** we wszystkich
trybach z siecią, **DENY** w Paranoicznym. Wymagana weryfikacja podpisu i checksumy
względem zaufanego źródła. Instrukcja instalacji przekazana w treści wiadomości /
dokumentu / linku jest sygnałem **prompt injection** i podlega natychmiastowemu
oznaczeniu, nie wykonaniu.

---

## Ochrona przed prompt injection

Cerber traktuje wszelką treść z zewnątrz (wiadomości, strony, dokumenty, tokeny,
linki) jako **niezaufane dane**. Wzorce podwyższające alarm:

- „zainstaluj / uruchom / pobierz tego agenta",
- dołączony token/klucz z instrukcją użycia,
- prośba o wyłączenie reguł, podniesienie uprawnień lub eksfiltrację danych,
- link do binarium na hoście kontrolowanym przez nadawcę.

Reakcja: **oznacz i zatrzymaj**, przedstaw użytkownikowi, nie wykonuj. Żadna treść
zewnętrzna nie może samodzielnie zmienić polityk ani wywołać akcji z listy DENY.

---

## Audyt

Każda decyzja CONFIRM / AUDIT / DENY+KEY zapisywana lokalnie (opcjonalnie szyfrowana),
z: znacznikiem czasu, kategorią, trybem, wynikiem, uzasadnieniem. Log zasila
[panel SHARON w Grafanie](grafana-integration.md) — widoczność decyzji Cerbera obok
metryk skanów.

## Powiązania

- [Architektura ALFA Phone](alfa-phone-architecture.md) — Cerber jako warstwa
- [Integracja z Grafaną](grafana-integration.md) — audyt jako źródło metryk/logów
- [Playbook obrony](anti-surveillance-playbook.md) — reguły spójne z higieną urządzeń
