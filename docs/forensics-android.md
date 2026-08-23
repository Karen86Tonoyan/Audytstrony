# Informatyka śledcza urządzeń mobilnych — Android

Usługa zabezpieczania i analizy danych z urządzeń z systemem Android na potrzeby
postępowań, sporów oraz wewnętrznych dochodzeń w organizacjach.

---

## 1. Podstawa prawna i zgoda

**Pracujemy wyłącznie na urządzeniach, do których zlecający ma tytuł prawny.**
Przed rozpoczęciem prac wymagamy jednego z poniższych:

- pisemnej zgody właściciela urządzenia (badania na zlecenie osoby prywatnej),
- oświadczenia pracodawcy o własności sprzętu służbowego wraz z podstawą wewnętrzną
  (regulamin, polityka monitoringu, obowiązek informacyjny wobec pracownika),
- postanowienia organu procesowego lub zlecenia kancelarii prowadzącej sprawę.

Zakres pozyskiwanych danych ograniczamy do minimum niezbędnego dla celu badania
(zasada minimalizacji, art. 5 ust. 1 lit. c RODO). Dane osób trzecich występujące
w materiale (rozmówcy, nadawcy wiadomości) podlegają temu samemu reżimowi ochrony.

**Czego nie robimy:** nie prowadzimy niejawnego monitoringu osób, nie omijamy
zabezpieczeń urządzeń nienależących do zlecającego, nie pozyskujemy danych bez
udokumentowanej podstawy.

---

## 2. Warianty usługi

| Wariant | Zakres | Typowe zastosowanie |
|---|---|---|
| **Triage** | Szybkie zabezpieczenie logiczne, wykaz artefaktów, ocena czy pełne badanie ma sens | Wstępna weryfikacja przed decyzją o sporze |
| **Standard** | Akwizycja logiczna, parsowanie artefaktów, oś czasu, raport z sumami kontrolnymi | Sprawy rodzinne, pracownicze, cywilne |
| **Rozszerzony** | Standard + analiza aplikacji komunikacyjnych, korelacja wielu urządzeń, analiza relacji | Dochodzenia wewnętrzne, wyciek danych |
| **Anty-spyware** | Kontrola urządzenia pod kątem oprogramowania szpiegowskiego (MVT + IOC) | Podejrzenie stalkerware / kompromitacji |

Wycena indywidualna — zależy od liczby urządzeń, stanu blokady i wymaganego terminu.

---

## 3. Przebieg badania

1. **Przyjęcie materiału** — protokół przekazania, opis stanu urządzenia, fotografia,
   nadanie identyfikatora sprawy.
2. **Izolacja** — tryb samolotowy / klatka Faradaya, aby zapobiec zdalnej modyfikacji
   lub czyszczeniu urządzenia.
3. **Akwizycja** — pozyskanie danych metodą adekwatną do urządzenia (patrz §4).
4. **Weryfikacja integralności** — SHA-256 obrazu i pojedynczych artefaktów,
   utrwalenie sum w protokole.
5. **Parsowanie i analiza** — dekodowanie baz danych, budowa osi czasu, analiza relacji.
6. **Raport** — dokument końcowy wraz z załącznikami (patrz §7).
7. **Zwrot / retencja** — zwrot urządzenia, uzgodniony okres przechowywania kopii
   roboczej, następnie trwałe usunięcie.

Łańcuch dowodowy (chain of custody) dokumentujemy na każdym z powyższych etapów.

---

## 4. Metody akwizycji

### Akwizycja logiczna (bez roota)

Podstawowa i najczęściej stosowana metoda. Pozyskuje dane udostępniane przez
API systemu i dostawców treści (content providers).

- ADB oraz zapytania do content providerów (`content query --uri content://call_log/calls`,
  `content://contacts/...`)
- dedykowane aplikacje pomocnicze uruchamiane na urządzeniu (AFLogical OSE, ForensicEye)
- kopie zapasowe systemowe — na nowszych wersjach Androida mocno ograniczone

Wymaga odblokowanego urządzenia i włączonego debugowania USB.

### Akwizycja pełna / fizyczna

Obraz całego systemu plików lub pamięci. Zakres nieporównanie szerszy
(dane usunięte, cache, artefakty systemowe), ale wymaga:

- odblokowanego bootloadera, roota lub podatności w danym modelu,
- w skrajnych przypadkach metod sprzętowych (JTAG, chip-off) — niszczących dla urządzenia.

W tym obszarze dominują rozwiązania komercyjne klasy laboratoryjnej. Jeżeli sprawa
tego wymaga, kierujemy materiał do laboratorium partnerskiego.

---

## 5. Stack narzędziowy

### Otwartoźródłowe (podstawa naszego procesu)

| Narzędzie | Rola | Zastosowanie |
|---|---|---|
| **ALEAPP** | Parser artefaktów | Najmocniejsze wolne narzędzie do parsowania artefaktów Androida — kontakty, rejestry połączeń, komunikatory, przeglądarki, logi systemowe. Przyjmuje zrzuty ADB, pełny system plików oraz wyniki narzędzi komercyjnych. [github.com/abrignoni/ALEAPP](https://github.com/abrignoni/ALEAPP) |
| **MVT + AndroidQF** | Wykrywanie kompromitacji | AndroidQF zbiera materiał, MVT weryfikuje go względem wskaźników kompromitacji (IOC). Podstawa wariantu anty-spyware. [mvt.re](https://mvt.re) |
| **Autopsy / The Sleuth Kit** | Platforma analityczna | Oś czasu, wyszukiwanie pełnotekstowe, odzyskiwanie danych usuniętych. Akceptowane w postępowaniach sądowych. |
| **AFLogical OSE** | Akwizycja na urządzeniu | Kontakty, rejestry połączeń, SMS/MMS — proste, sprawdzone rozwiązanie. |
| **ForensicEye** | Akwizycja modułowa | Zbieranie danych bez roota, uruchamiane bezpośrednio na urządzeniu. |
| **ADB + zapytania do content providerów** | Fundament | Precyzyjne, skryptowalne pozyskiwanie wskazanych zbiorów danych. |

### Komercyjne (dostęp przez laboratoria partnerskie)

Stosowane tam, gdzie potrzebna jest akwizycja fizyczna, obejście blokady lub
raport w formacie przyjętym przez konkretny organ.

| Narzędzie | Charakterystyka |
|---|---|
| **Cellebrite UFED** | Standard branżowy, najszersze wsparcie urządzeń, akwizycja fizyczna i logiczna |
| **MSAB XRY** | Silne wsparcie Androida, rozbudowane raportowanie, popularne w Europie |
| **Oxygen Forensic Detective** | Dobry stosunek możliwości do ceny, szerokie wsparcie aplikacji |
| **Magnet AXIOM** | Najmocniejsza warstwa analityczna — oś czasu, korelacje między źródłami |
| **MOBILedit Forensic Express** | Rozwiązanie all-in-one, dobre wsparcie aplikacji |
| **Belkasoft X / Paraben E3** | Alternatywy o rosnącym udziale w rynku |

---

## 6. Kluczowe artefakty

Zbiory danych najczęściej istotne dla przebiegu sprawy:

| Ścieżka / zbiór | Zawartość |
|---|---|
| `/data/data/com.android.providers.contacts/databases/contacts2.db` | Kontakty oraz rejestr połączeń |
| `mmssms.db` | Wiadomości SMS i MMS |
| Bazy aplikacji komunikacyjnych | WhatsApp, Signal, Messenger i inne — zakres zależny od wersji i szyfrowania |
| Historia przeglądarek | Odwiedzone adresy, wyszukiwania, pobrania |
| Logi systemowe i zdarzenia zasilania | Rekonstrukcja aktywności urządzenia w czasie |
| Dane lokalizacyjne | Wyłącznie w zakresie objętym zgodą i celem badania |

Zawartość faktycznie dostępna zależy od wersji Androida, producenta, stanu blokady
oraz zastosowanego przez aplikacje szyfrowania.

---

## 7. Produkt końcowy

Raport w formacie PDF zawierający:

- opis materiału, stanu urządzenia i warunków przekazania,
- podstawę prawną badania,
- zastosowaną metodykę i wersje użytych narzędzi,
- sumy kontrolne SHA-256 materiału źródłowego i wyników,
- ustalenia wraz z odwołaniem do konkretnych artefaktów,
- oś czasu zdarzeń,
- jednoznaczne oddzielenie **ustaleń** od **interpretacji**,
- wykaz ograniczeń badania.

Załączniki: eksporty tabelaryczne (CSV/XLSX), zabezpieczone kopie artefaktów,
protokół łańcucha dowodowego.

---

## 8. Ograniczenia

Deklarujemy je przed przyjęciem zlecenia, nie po badaniu:

- **Urządzenie zablokowane** — bez znanego kodu PIN/hasła zakres akwizycji jest
  radykalnie ograniczony lub zerowy; nowsze modele Samsung i Pixel skutecznie
  opierają się większości metod.
- **Szyfrowanie end-to-end** — treści Signal czy WhatsApp odczytujemy tylko wtedy,
  gdy są zapisane na badanym urządzeniu i dostępne po jego odblokowaniu.
- **Dane usunięte** — możliwe do odzyskania głównie przy akwizycji pełnej;
  przy logicznej z reguły niedostępne.
- **Chmura** — dane w usługach zdalnych wymagają odrębnej podstawy prawnej
  i osobnego trybu pozyskania.
- **Brak gwarancji rezultatu** — badanie może wykazać brak śladów istotnych dla sprawy.
  To również jest wynik i tak zostaje opisany w raporcie.

---

## 9. Dane kontaktowe

Zgłoszenia spraw i wycena: patrz [README](../README.md).
