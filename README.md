# Korki Śrem

Prosta, bezpłatna strona pokazująca, ile obecnie trwa wjazd do Śremu głównymi
drogami wojewódzkimi — w związku z remontem mostu im. Daniela Kęszyckiego
i objazdem przez obwodnicę.

Projekt niekomercyjny, bez reklam. Jedyny licznik to Cloudflare Web Analytics,
który według deklaracji dostawcy nie zbiera danych osobowych odwiedzających.

## Jak to działa

```
cron-job.org (zegar: co 10 min w szczycie, co 30 min poza nim,
        │     w nocy nic) — wywołuje adres Workera z kluczem
        ▼
Cloudflare Worker — zamawia pomiar przez API GitHuba
        ▼
GitHub Actions
        │  TomTom Routing API — czas przejazdu z uwzględnieniem ruchu
        ▼
data/current.json  +  data/history/YYYY-MM.csv
        │
        ▼
GitHub Pages — statyczna strona (index.html) czyta JSON
```

Nie ma serwera ani bazy danych. Klucz API żyje wyłącznie jako sekret w GitHub
Actions i nigdy nie trafia do przeglądarki.

Ten łańcuch jest dłuższy, niż wypadałoby dla tak prostego zadania, bo **dwie
platformy przyjęły harmonogram i go nie zrealizowały**: najpierw wbudowany
`on: schedule` GitHuba, potem cron triggers Cloudflare. Obie awarie
udokumentowano pomiarami w [`docs/METODYKA.md`](docs/METODYKA.md) (sekcja 3c).
Rolę zegara pełni więc usługa zewnętrzna, ale token GitHuba zostaje po stronie
Workera — cron-job.org zna wyłącznie adres i klucz wyzwalacza, które można
unieważnić bez ruszania tokenu.

## Monitorowane trasy

| Trasa | Droga |
|---|---|
| Z obwodnicy do centrum | rondo Mikołajczyka (BP) → Plac 20 Października |
| Od Poznania / Kórnika | DW434 |
| Od Środy Wielkopolskiej | DW432 |
| Od Gostynia (ul. Gostyńska) | DW434 |
| Od Leszna / Krzywinia przez most | DW432 + most Kęszyckiego |
| Od Czempinia / Kościana | DW310 |
| Objazd obwodnicą na Gostyńską | obwodnica + Gostyńska |
| Wyjazd ze Śremu na Poznań | DW434 |

Współrzędne punktów pochodzą z OpenStreetMap — szczegóły w
[docs/METODYKA.md](docs/METODYKA.md).

## Uruchomienie

### 1. Klucz TomTom

1. Załóż darmowe konto na <https://developer.tomtom.com/>.
2. Utwórz aplikację z włączonym produktem **Routing API**.
3. Skopiuj klucz.

**Limit darmowy: 20 000 zapytań miesięcznie** dla Routing API
(zweryfikowane na <https://docs.tomtom.com/pricing>, wrzesień 2026 — pozycja
„Routing API… Free 20K monthly”). Nie mylić z *Matrix* Routing API, który ma
próg 2,5 tys./mies.

Ten projekt zużywa **480 zapytań na dobę = 14 880 miesięcznie** (31 dni) — mieści
się w progu z zapasem ok. 26%. Liczbę przelicza `scripts/policz_budzet.py`
z definicji zadań w `scripts/konfiguruj_zegar.py`. Dodatkowo `fetch_traffic.py`
sam przerywa pomiary po przekroczeniu 18 500 zapytań w miesiącu, licząc je
z plików historii.

Klucza **nie zapisuj w repozytorium**. Dodaj go jako sekret:

```powershell
gh secret set TOMTOM_API_KEY --repo llyen/srem-korki
```

lub w interfejsie: *Settings → Secrets and variables → Actions → New repository secret*,
nazwa `TOMTOM_API_KEY`.

### 2. Pierwszy pomiar

```powershell
$env:TOMTOM_API_KEY = "twoj_klucz"
python scripts/fetch_traffic.py
python scripts/build_profile.py
```

Albo w GitHubie: zakładka *Actions → Aktualizacja danych o ruchu → Run workflow*.

### 3. Podgląd lokalny

```powershell
python scripts/mock_data.py     # dane PRZYKŁADOWE, tylko do podglądu wyglądu
python -m http.server 8000
```

Strona: <http://localhost:8000>. Przy danych przykładowych wyświetla się czerwone
ostrzeżenie — to celowe.

### 4. Publikacja

*Settings → Pages → Source: Deploy from a branch → `main` / `/ (root)`*.

Strona pojawi się pod adresem `https://korkisrem.pl/` (adres `https://llyen.github.io/srem-korki/`
przekierowuje na własną domenę — konfiguracja opisana w `docs/DOMENA.md`).

### 5. Harmonogram pomiarów

Zegar stoi w serwisie **cron-job.org** i wywołuje chroniony adres Cloudflare
Workera z katalogu `worker/`, a Worker zamawia pomiar w GitHub Actions.
Zadania zegara tworzy skrypt `scripts/konfiguruj_zegar.py` — konfiguracja jest
odtwarzalna z kodu, a nie wyklikana w panelu:

```powershell
$env:CRONJOB_API_KEY = "<klucz API z cron-job.org>"
python scripts/konfiguruj_zegar.py
```

Instrukcja wdrożenia samego Workera — token GitHuba, klucz wyzwalacza,
`wrangler deploy`, weryfikacja — jest w [`worker/README.md`](worker/README.md).

Bez tego kroku strona działa, ale dane aktualizują się tylko przy ręcznym
uruchomieniu workflow.

## Struktura

```
index.html              strona
assets/                 style i skrypt frontendu
scripts/config.json     definicje tras i progi kolorów
scripts/wyznacz_punkty.py  odtwarza współrzędne punktów z OpenStreetMap
scripts/fetch_traffic.py  pomiar (TomTom → data/)
scripts/build_profile.py  profil godzinowy z historii
scripts/konfiguruj_zegar.py  zadania zegara w cron-job.org (pory pomiarów)
scripts/policz_budzet.py  przelicza zużycie limitu TomTom z harmonogramu
scripts/mock_data.py    dane przykładowe do podglądu
data/current.json       ostatni pomiar
data/history/           historia pomiarów (CSV, miesięcznie)
docs/METODYKA.md        źródła danych i sposób liczenia
worker/                 Cloudflare Worker — przyjmuje sygnał zegara
.github/workflows/      przebieg pomiaru (uruchamiany przez Workera)
```

## Ograniczenia

- To **nie jest oficjalne źródło informacji**. Oficjalne komunikaty publikuje
  Urząd Miejski w Śremie i zarządca drogi.
- Dane TomTom na drogach wojewódzkich mają mniejszą próbkę niż na trasach
  szybkiego ruchu — krótkie zatory mogą być wygładzone lub opóźnione w czasie.
- Progi kolorów to wartości wyjściowe, nie skalibrowane na danych ze Śremu.
  Warto je skorygować po kilku tygodniach zbierania historii.
- Profil godzinowy wymaga kilku tygodni pomiarów, zanim zacznie coś znaczyć.
- Strona odświeża się sama co 2 minuty (oraz po powrocie do karty), ale liczba
  na ekranie może być starsza od rzeczywistości nawet o kilkanaście minut:
  składa się na to cykl pomiaru (10 min w szczycie) i cache CDN GitHub Pages
  (`max-age=600`, którego nie da się ominąć parametrem `?t=`). Dlatego strona
  zawsze pokazuje wiek danych wprost. Szczegóły i pomiary — `docs/METODYKA.md`,
  sekcja 3d.

## Licencja

Kod: MIT (plik `LICENSE`).
Dane o ruchu pochodzą z TomTom i podlegają warunkom TomTom.
Geometria dróg: OpenStreetMap, licencja ODbL.
