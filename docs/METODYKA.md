# Metodyka — skąd pochodzą dane

Dokument opisuje źródła i sposób wyznaczenia każdej liczby na stronie, tak aby
wynik dał się odtworzyć i zweryfikować.

## 1. Kontekst drogowy

| Fakt | Status | Źródło |
|---|---|---|
| Remont mostu im. Daniela Kęszyckiego w Śremie | potwierdzony w mediach lokalnych | doniesienia prasowe, lipiec 2026 |
| Ruch na moście jednokierunkowy, dozwolony kierunek na Poznań | potwierdzony w mediach lokalnych | jw. |
| Objazd w kierunku Leszna przez obwodnicę (DW434) i ul. Gostyńską | potwierdzony w mediach lokalnych | jw. |
| Planowany termin zakończenia prac | **niepewny** — podawany koniec 2026 z zastrzeżeniem możliwych opóźnień | jw. |

Opisy w interfejsie strony celowo nie podają daty zakończenia remontu, ponieważ
nie jest ona pewna. Przed publikacją warto potwierdzić stan organizacji ruchu
w komunikatach Urzędu Miejskiego w Śremie oraz zarządcy drogi (WZDW Poznań).

## 2. Geometria dróg i punkty pomiarowe

Współrzędne pochodzą wyłącznie z OpenStreetMap (Overpass API), nie zostały
oszacowane ręcznie. Użyte zapytania:

```overpassql
// przebieg dróg wojewódzkich w rejonie Śremu
way["ref"~"^(434|432|310)$"]["highway"](52.00,16.90,52.16,17.12);
out geom;

// obwodnica i mosty
way["name"~"[Oo]bwodnica"](52.02,16.95,52.14,17.10);
way["highway"~"^(primary|secondary|tertiary)$"]["bridge"](52.07,17.00,52.11,17.06);
out geom;
```

Ustalenia:

- Most im. Daniela Kęszyckiego: odcinek `52.09142,17.01793` → `52.09274,17.02061`,
  w OSM sklasyfikowany jako `highway=tertiary`.
- Obwodnica Śremu: ciąg o `ref = "432;434"` przebiegający wschodnią stroną miasta
  wzdłuż ok. `lon 17.042`.
- Punkt odniesienia w mieście: Stary Rynek, `52.09238, 17.02226`
  (Nominatim, zapytanie `Rynek, Śrem, Polska`).

Punkty startowe tras wybrano algorytmicznie: spośród wszystkich węzłów danej
drogi wojewódzkiej wybrano ten, którego **odległość w linii prostej** od Starego
Rynku jest najbliższa 7 km, w zadanym zakresie azymutu. Dzięki temu każdy punkt
leży na rzeczywistej jezdni, a nie „mniej więcej tam”.

| Trasa | Punkt startowy | W linii prostej od Rynku |
|---|---|---|
| Od Poznania / Kórnika (DW434) | 52.15470, 17.03502 | 6,99 km |
| Od Środy Wlkp. (DW432) | 52.13573, 17.09824 | 7,10 km |
| Od Gostynia (DW434) | 52.03303, 17.05592 | 7,00 km |
| Od Leszna / Krzywinia (DW432) | 52.04938, 16.94743 | 7,02 km |
| Od Czempinia / Kościana (DW310) | 52.11414, 16.92563 | 7,05 km |

**Jak policzono te odległości.** Wzorem równoprostokątnym (rzut walcowy
równoodległościowy) na kuli o promieniu 6371 km, z korekcją południków przez
cosinus średniej szerokości geograficznej. To przybliżenie, więc sprawdzono jego
błąd względem dokładnego wzoru Vincentego na elipsoidzie WGS84:

| Trasa | Wzór równoprostokątny | Haversine | WGS84 (Vincenty) | Błąd |
|---|---|---|---|---|
| Od Poznania | 6,984 km | 6,984 km | 6,989 km | 5 m |
| Od Środy | 7,082 km | 7,082 km | 7,096 km | 14 m |
| Od Gostynia | 6,989 km | 6,989 km | 6,996 km | 7 m |
| Od Leszna | 7,002 km | 7,002 km | 7,016 km | 14 m |
| Od Czempinia | 7,029 km | 7,029 km | 7,050 km | 21 m |

Największy błąd to 21 m na 7 km, czyli 0,3%. Dla zadania „wybierz węzeł drogi
mniej więcej 7 km od centrum” jest to bez znaczenia — sąsiednie węzły OSM na tych
drogach dzieli i tak kilkadziesiąt metrów.

**To nie są odległości pokazywane na stronie.** Kilometry widoczne przy każdej
trasie (7,8 km, 8,9 km, 17,9 km itd.) to `lengthInMeters` z odpowiedzi TomTom,
czyli rzeczywista długość przejazdu po drogach. Jest ona zawsze większa od
odległości w linii prostej i to ona ma znaczenie praktyczne. Odległość prosta
posłużyła wyłącznie do wyboru punktów pomiarowych.

Poprawność geograficzną tras zweryfikowano niezależnie w OSRM (silnik na danych
OSM, bez ruchu), przed pierwszym zapytaniem do TomTom:

| Trasa | Długość po drogach (OSRM) |
|---|---|
| od-poznania | 7,7 km |
| od-srody | 7,3 km |
| od-gostynia | 7,8 km |
| od-leszna-most | 7,4 km |
| od-czempinia | 8,2 km |
| objazd-obwodnica | 17,9 km |
| wyjazd-na-poznan | 7,7 km |

Zgodność długości objazdu w OSRM (17,9 km) i w TomTom (17,902 km) potwierdza, że
punkt pośredni faktycznie wymusza przejazd obwodnicą, a nie skrótem przez miasto.

Trasa „objazd obwodnicą” prowadzi z punktu północnego na DW434 przez punkt
pośredni na obwodnicy (`52.09198, 17.04189`) do punktu południowo-zachodniego na
DW432. Punkt pośredni jest konieczny, ponieważ silnik wyznaczania trasy nie musi
uwzględniać tymczasowej organizacji ruchu na moście.

## 3. Pomiar czasu przejazdu

Źródło: **TomTom Routing API v1**, endpoint `calculateRoute`.

Parametry: `traffic=true`, `travelMode=car`, `routeType=fastest`,
`computeTravelTimeFor=all`, `departAt=now`.

Z odpowiedzi `summary` wykorzystywane są pola:

- `travelTimeInSeconds` — czas przejazdu z uwzględnieniem bieżącego ruchu,
- `noTrafficTravelTimeInSeconds` — czas przy pustej drodze (odniesienie),
- `trafficDelayInSeconds` — opóźnienie względem **typowego** ruchu o tej porze,
- `lengthInMeters` — długość trasy.

**Uwaga interpretacyjna.** `trafficDelayInSeconds` nie jest różnicą wobec pustej
drogi. W pomiarze z 1 września 2026, godz. 8:56, trasa „od Leszna przez most”
miała `travelTime = 781 s`, `noTrafficTravelTime = 590 s`, ale
`trafficDelay = 81 s`. Pierwsza różnica (191 s) to strata wobec pustej drogi,
druga (81 s) — wobec typowego ruchu w środę rano. Strona pokazuje wielkość
`czas − czas_bez_ruchu`, bo to ona odpowiada opisowi „dłużej niż przy pustej
drodze”. Wartość TomTom zapisujemy osobno jako `opoznienie_wzgl_typowego_s`.

## 3b. Co oznacza 17,9 km trasy „objazd obwodnicą”

To najczęściej mylona liczba na stronie, więc rozpisujemy ją jawnie. **Nie jest
to długość obwodnicy Śremu.** Obwodnica ma ok. 4 km — suma długości wszystkich
jezdni o `ref = "432;434"` w OSM to 4,06 km, a jej rozpiętość północ–południe
3,83 km.

17,9 km to długość całego mierzonego przejazdu tranzytowego:

| Składowa | Ok. |
|---|---|
| dojazd DW434 z punktu 7 km na północ od Śremu | 7 km |
| obwodnica Śremu | 4 km |
| dalej DW432 do punktu 7 km na południowy zachód | 7 km |

Punkty skrajne to `52.15470, 17.03502` (DW434 od strony Kórnika) oraz
`52.04938, 16.94743` (DW432 w stronę Krzywinia i Leszna) — te same, których
używają trasy „Od Poznania” i „Od Leszna”. Dzięki temu liczby są porównywalne
między sobą, ale **nie** z trasami wjazdowymi, które kończą się na Starym Rynku.

Ile faktycznie nadkłada objazd? Porównanie w OSRM (ten sam silnik, ta sama para
punktów skrajnych):

| Wariant | Długość | Czas bez ruchu |
|---|---|---|
| przez obwodnicę (stan obecny) | 17,9 km | 20 min |
| trasa swobodna przez miasto i most | 15,1 km | 18 min |

Objazd nadkłada więc ok. **2,8 km**. Sam dystans nie jest dużym problemem —
dolegliwy jest czas, bo cały ruch tranzytowy i lokalny spotyka się na jednym
ciągu. W pomiarze z 1 września 2026 objazd zajmował 25 min przy 17 min bez ruchu.

**Zastrzeżenie:** wariant „przez miasto i most” policzono w OSRM na danych OSM,
które w chwili pomiaru nie zawierały tymczasowego ruchu jednokierunkowego na
moście. Ta liczba opisuje więc stan sprzed remontu, a nie dostępną dziś
alternatywę. Traktuj ją jako punkt odniesienia, nie jako podpowiedź nawigacyjną.

## 3c. Zużycie darmowego limitu

Darmowy próg Routing API to **20 000 zapytań miesięcznie**
(źródło: <https://docs.tomtom.com/pricing>, weryfikacja 1 września 2026 —
wiersz „Routing API … Free 20K monthly”, identyczny dla TomTom Maps i Orbis
Maps). Próg 2,5 tys./mies. dotyczy *Matrix* Routing API, czyli innego produktu.

Harmonogram dobrano tak, żeby zmieścić się z zapasem:

| Okno (UTC) | Częstotliwość | Przebiegów/dobę |
|---|---|---|
| 04:00–07:59 i 12:00–16:59 | co 10 min | 54 |
| 08:00–11:59 i 17:00–21:59 | co 30 min | 18 |

72 przebiegi × 7 tras = **504 zapytania na dobę ≈ 15 300 miesięcznie**.

Okna w UTC są celowo szersze niż polski szczyt, bo cron nie zna czasu letniego —
ten sam zapis musi działać przy UTC+1 i UTC+2.

Niezależnie od harmonogramu `fetch_traffic.py` przed każdym przebiegiem liczy
zapytania wykonane w bieżącym miesiącu (jeden wiersz historii = jedno zapytanie)
i przerywa pracę po 18 500. To zabezpieczenie na wypadek ręcznych uruchomień
i zmian w konfiguracji.

**Ograniczenie, o którym trzeba wiedzieć:** dane TomTom pochodzą z floty pojazdów
i urządzeń nawigacyjnych. Na drogach wojewódzkich w mniejszym mieście próbka jest
mniejsza niż na autostradzie, więc pomiar może reagować z opóźnieniem i wygładzać
krótkie zatory. Strona nie jest źródłem urzędowym i tak jest opisana.

## 3d. Jak świeże są dane widoczne w przeglądarce

Na wiek liczby na ekranie składają się trzy niezależne opóźnienia:

| Składnik | Wartość | Uwaga |
| --- | --- | --- |
| Cykl pomiaru | 10 min w szczycie, 30 min poza nim | harmonogram z sekcji 3c |
| Cache CDN | do 10 min (GitHub Pages) lub do 5 min (raw.githubusercontent.com) | patrz niżej |
| Odpytywanie przez stronę | 2 min | `ODSWIEZANIE_MS` w `assets/app.js` |

**Zmierzone zachowanie cache.** GitHub Pages serwuje `data/current.json`
z nagłówkiem `Cache-Control: max-age=600` przez CDN Fastly. Sprawdzono serią
żądań z *różnymi* losowymi parametrami query: pierwsze żądanie zwróciło
`X-Cache: MISS`, `Age: 0`, kolejne — `X-Cache: HIT` z rosnącym `Age`
(4, 8, 13 s). Oznacza to, że **query string nie jest częścią klucza cache**,
więc popularny zabieg `?t=Date.now()` nie wymusza świeżej odpowiedzi.
Ten sam plik serwowany z `raw.githubusercontent.com` ma `Cache-Control:
max-age=300` i nagłówek `Access-Control-Allow-Origin: *`, czyli daje się
pobrać z przeglądarki i jest cachowany o połowę krócej.

**Rozwiązanie.** Strona odpytuje oba adresy równolegle
(`Promise.allSettled`) i wyświetla ten wynik, który ma nowszy znacznik
`pobrano_utc`. Jeśli jedno źródło zawiedzie (np. blokada sieciowa), drugie
nadal działa. Nie jest to obejście limitu cache — to wybór świeższej
z dwóch dostępnych kopii.

**Konsekwencja dla użytkownika.** W najgorszym przypadku liczba na ekranie
może pochodzić sprzed ok. 15 min w szczycie. Dlatego strona pokazuje wiek
danych wprost („Pomiar o 09:16 — 4 minuty temu”), aktualizowany co 20 s, oraz
ostrzega, gdy pomiar jest starszy niż 50 min. Próg 50 min dobrano tak, aby nie
alarmował fałszywie poza szczytem (30 min cyklu + 10 min cache + margines).

## 4. Klasyfikacja kolorystyczna

Kolor jest heurystyką, nie pomiarem. Wynika z ostrzejszego z dwóch kryteriów:
stosunku czasu przejazdu do czasu przy pustej drodze oraz bezwzględnego
opóźnienia w minutach.

| Poziom | Stosunek czasu | Opóźnienie |
|---|---|---|
| płynnie | ≤ 1,15 | ≤ 3 min |
| lekko wolniej | ≤ 1,40 | ≤ 8 min |
| utrudnienia | ≤ 1,80 | ≤ 15 min |
| korek | powyżej | powyżej |

Progi znajdują się w `scripts/config.json` i można je skorygować po zebraniu
pierwszych tygodni pomiarów — obecne wartości są punktem wyjścia, a nie wynikiem
kalibracji na danych ze Śremu.

## 5. Profil godzinowy

`scripts/build_profile.py` liczy medianę opóźnienia w podziale na trasę, dzień
tygodnia i godzinę. Komórki mające mniej niż 3 pomiary są pomijane i wyświetlane
jako brak danych — celowo, żeby nie sugerować wniosków z pojedynczego pomiaru.
Sensowny profil powstanie dopiero po kilku tygodniach zbierania danych.

## 6. Czego strona nie wie

- Nie zna przyczyny zatoru (kolizja, roboty, ruch świąteczny).
- Nie uwzględnia czasowych zamknięć ogłaszanych przez zarządcę drogi.
- Nie mierzy ruchu pieszego i rowerowego przez most.
- Nie obejmuje objazdów drogami powiatowymi i gminnymi, którymi część kierowców
  faktycznie jeździ.
