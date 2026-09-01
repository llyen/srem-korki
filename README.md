# Korki Śrem

Prosta, bezpłatna strona pokazująca, ile obecnie trwa wjazd do Śremu głównymi
drogami wojewódzkimi — w związku z remontem mostu im. Daniela Kęszyckiego
i objazdem przez obwodnicę.

Projekt niekomercyjny, bez reklam, bez śledzenia użytkowników.

## Jak to działa

```
GitHub Actions (co 10 min)
        │  TomTom Routing API — czas przejazdu z uwzględnieniem ruchu
        ▼
data/current.json  +  data/history/YYYY-MM.csv
        │
        ▼
GitHub Pages — statyczna strona (index.html) czyta JSON
```

Nie ma serwera ani bazy danych. Klucz API żyje wyłącznie jako sekret w GitHub
Actions i nigdy nie trafia do przeglądarki.

## Monitorowane trasy

| Trasa | Droga |
|---|---|
| Od Poznania / Kórnika | DW434 |
| Od Środy Wielkopolskiej | DW432 |
| Od Gostynia (ul. Gostyńska) | DW434 |
| Od Leszna / Krzywinia przez most | DW432 + most Kęszyckiego |
| Od Czempinia / Kościana | DW310 |
| Objazd obwodnicą (Poznań → Leszno) | DW434 / obwodnica |
| Wyjazd ze Śremu na Poznań | DW434 |

Współrzędne punktów pochodzą z OpenStreetMap — szczegóły w
[docs/METODYKA.md](docs/METODYKA.md).

## Uruchomienie

### 1. Klucz TomTom

1. Załóż darmowe konto na <https://developer.tomtom.com/>.
2. Utwórz aplikację z włączonym produktem **Routing API**.
3. Skopiuj klucz. Darmowy próg to 2 500 zapytań na dobę; ten projekt zużywa
   ok. 756 dziennie.

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

Strona pojawi się pod adresem `https://llyen.github.io/srem-korki/`.

## Struktura

```
index.html              strona
assets/                 style i skrypt frontendu
scripts/config.json     definicje tras i progi kolorów
scripts/fetch_traffic.py  pomiar (TomTom → data/)
scripts/build_profile.py  profil godzinowy z historii
scripts/mock_data.py    dane przykładowe do podglądu
data/current.json       ostatni pomiar
data/history/           historia pomiarów (CSV, miesięcznie)
docs/METODYKA.md        źródła danych i sposób liczenia
.github/workflows/      harmonogram pomiarów
```

## Ograniczenia

- To **nie jest oficjalne źródło informacji**. Oficjalne komunikaty publikuje
  Urząd Miejski w Śremie i zarządca drogi.
- Dane TomTom na drogach wojewódzkich mają mniejszą próbkę niż na trasach
  szybkiego ruchu — krótkie zatory mogą być wygładzone lub opóźnione w czasie.
- Progi kolorów to wartości wyjściowe, nie skalibrowane na danych ze Śremu.
  Warto je skorygować po kilku tygodniach zbierania historii.
- Profil godzinowy wymaga kilku tygodni pomiarów, zanim zacznie coś znaczyć.

## Licencja

Kod: MIT (plik `LICENSE`).
Dane o ruchu pochodzą z TomTom i podlegają warunkom TomTom.
Geometria dróg: OpenStreetMap, licencja ODbL.
