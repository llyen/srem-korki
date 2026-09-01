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
drogi wojewódzkiej wybrano ten, którego odległość od Starego Rynku jest
najbliższa 7 km, w zadanym zakresie azymutu. Dzięki temu każdy punkt leży na
rzeczywistej jezdni, a nie „mniej więcej tam”.

| Trasa | Punkt startowy | Odległość od Rynku |
|---|---|---|
| Od Poznania / Kórnika (DW434) | 52.15470, 17.03502 | 7,0 km |
| Od Środy Wlkp. (DW432) | 52.13573, 17.09824 | 7,1 km |
| Od Gostynia (DW434) | 52.03303, 17.05592 | 7,0 km |
| Od Leszna / Krzywinia (DW432) | 52.04938, 16.94743 | 7,0 km |
| Od Czempinia / Kościana (DW310) | 52.11414, 16.92563 | 7,0 km |

Trasa „objazd obwodnicą” prowadzi z punktu północnego na DW434 przez punkt
pośredni na obwodnicy (`52.09198, 17.04189`) do punktu południowo-zachodniego na
DW432. Punkt pośredni jest konieczny, ponieważ silnik wyznaczania trasy nie musi
uwzględniać tymczasowej organizacji ruchu na moście.

## 3. Pomiar czasu przejazdu

Źródło: **TomTom Routing API v1**, endpoint `calculateRoute`.

Parametry: `traffic=true`, `travelMode=car`, `routeType=fastest`,
`computeTravelTimeFor=all`, `departAt=now`.

Z odpowiedzi wykorzystywane są pola `summary`:

- `travelTimeInSeconds` — czas przejazdu z uwzględnieniem bieżącego ruchu,
- `noTrafficTravelTimeInSeconds` — czas przy pustej drodze (odniesienie),
- `trafficDelayInSeconds` — opóźnienie wynikające z ruchu,
- `lengthInMeters` — długość trasy.

Częstotliwość: co 10 minut w godzinach 04:00–21:59 UTC. Przy 7 trasach daje to
ok. 756 zapytań na dobę, poniżej darmowego limitu TomTom (2 500/dobę).

**Ograniczenie, o którym trzeba wiedzieć:** dane TomTom pochodzą z floty pojazdów
i urządzeń nawigacyjnych. Na drogach wojewódzkich w mniejszym mieście próbka jest
mniejsza niż na autostradzie, więc pomiar może reagować z opóźnieniem i wygładzać
krótkie zatory. Strona nie jest źródłem urzędowym i tak jest opisana.

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
