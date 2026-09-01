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
- Punkt odniesienia przy wyborze punktów startowych: Stary Rynek,
  `52.09238, 17.02226` (Nominatim, zapytanie `Rynek, Śrem, Polska`).
  Służy wyłącznie jako środek okręgu o promieniu 7 km — cele tras są inne
  i opisano je w sekcji 2b.

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

Ósma trasa — „Z obwodnicy do centrum” — nie należy do tej grupy. Jej punkt
startowy to **Rondo Premiera Stanisława Mikołajczyka** (`52.10643, 17.04321`,
OSM `ref = "432;434"`), przy którym stoi stacja BP. Rondo leży 2,03 km od
Starego Rynku i jest węzłem obwodnicy z ul. Średzką, czyli faktycznym wjazdem
do miasta od strony Poznania i Środy Wlkp. Punkt wybrano dlatego, że
na odcinku 2,3 km kilkuminutowy zator jest widoczny wyraźnie, podczas gdy na
trasach dojazdowych o długości 7–9 km rozmywa się w czasie jazdy poza miastem.

W rejonie Śremu OSM zna dwie stacje BP — druga (`52.09041, 17.01592`) stoi
w mieście przy moście Kęszyckiego i **nie** jest tym punktem. Spośród sześciu
nazwanych rond w rejonie Śremu tylko Rondo Mikołajczyka leży na obwodnicy
(`ref = "432;434"`); pozostałe znajdują się wewnątrz miasta. Dlatego pozostałym
wjazdom nie nadano nazw punktów orientacyjnych — nie istnieją.

**Jak te punkty nazwano na stronie.** Karty nie podają „7 km”, bo obok widnieje
kilometraż rzeczywistej trasy (7,3–8,9 km) i zestawienie dwóch różnych liczb
myliło czytelnika. Zamiast tego każdy punkt opisano najbliższą miejscowością,
ustaloną przez odwrotne geokodowanie w Nominatim (`/reverse`, `zoom=14`)
i zweryfikowaną dystansem do centroidu tej miejscowości:

| Trasa | Najbliższa miejscowość | Odległość punktu od niej |
|---|---|---|
| Od Poznania / Kórnika | Rudunek (przysiółek Niesłabina), gm. Śrem | 1,18 km |
| Od Środy Wlkp. | Luciny, gm. Śrem | 830 m |
| Od Gostynia | Drzonek, gm. Dolsk | 248 m |
| Od Leszna / Krzywinia | Wyrzeka, gm. Śrem | 450 m |
| Od Czempinia / Kościana | Manieczki, gm. Brodnica | 317 m |

Punkt północny jest jedynym oddalonym od zabudowy, dlatego opisano go „za
Rudunkiem”, a nie „przy Rudunku”: leży 1,18 km na północ od niego
(52.1547 wobec 52.1442), czyli po stronie Zaniemyśla, do którego jest jeszcze
8,65 km. Pozostałe cztery punkty leżą w granicach 250–830 m od wsi, co
uzasadnia sformułowanie „przy”.

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
trasie (2,1 km, 5,5 km, 7,5 km itd.) to `lengthInMeters` z odpowiedzi TomTom,
czyli rzeczywista długość przejazdu po drogach. Jest ona zawsze większa od
odległości w linii prostej i to ona ma znaczenie praktyczne. Odległość prosta
posłużyła wyłącznie do wyboru punktów pomiarowych.

Poprawność geograficzną tras zweryfikowano niezależnie w OSRM (silnik na danych
OSM, bez ruchu), przed pierwszym zapytaniem do TomTom:

| Trasa | Długość po drogach (OSRM) |
|---|---|
| obwodnica-plac20 | 2,10 km |
| od-poznania-plac20 | 7,48 km |
| od-srody-plac20 | 7,13 km |
| od-gostynia-staszica | 5,52 km |
| od-leszna-most-bp | 9,68 km |
| od-czempinia-rondo-ak | 7,35 km |
| objazd-gostynska | 4,82 km |
| wyjazd-plac20-poznan | 7,52 km |

Dwie trasy startujące przy stacji BP opisano osobno w sekcji 3b — tam też
znajduje się rozkład ich długości na poszczególne odcinki.

## 2b. Punkty docelowe w mieście

Pierwsza wersja kierowała wszystkie trasy dojazdowe na Stary Rynek
(`52.09238, 17.02226`, Nominatim). Zostało to zmienione na wniosek autora
projektu: kierowca nie jedzie „do centrum” w ogóle, tylko do konkretnego
miejsca, a każdy wjazd ma inne naturalne zakończenie. Obecne cele:

| Trasa | Punkt docelowy | Współrzędne | Źródło w OSM |
|---|---|---|---|
| od Poznania / Kórnika | Plac 20 Października | `52.09485, 17.02137` | centroid 7 odcinków `highway=residential` tworzących obrys placu |
| od Środy Wlkp. | Plac 20 Października | `52.09485, 17.02137` | jw. |
| od Gostynia | Gostyńska × Staszica | `52.0786487, 17.0288189` | `node 270295855` — jedyny wspólny węzeł obu ulic |
| od Czempinia / Kościana | rondo Armii Krajowej | `52.088824, 17.015192` | `way 29092946`, `junction=roundabout` |
| od Leszna / Krzywinia | rondo Mikołajczyka (przy BP) | `52.10643, 17.04321` | `node` z `ref="432;434"` przy stacji BP |
| wyjazd na Poznań (start) | Plac 20 Października | `52.09485, 17.02137` | jw. |

Trasa od Leszna prowadzi przez **oba mosty**: najpierw remontowany most
im. Kęszyckiego (przejezdny wyłącznie w stronę Poznania), potem przez miasto
i most Majora Stefana Chosłowskiego na obwodnicę. Jest to więc pełny przejazd
tranzytowy z kierunku Leszna w stronę Poznania, a nie sam przejazd przez most.
Wschodni wylot mostu Kęszyckiego (`52.09274, 17.02061`) pozostał w trasie jako
**punkt pośredni** — bez niego przy zatorze w mieście silnik mógłby
przekierować pomiar na obwodnicę i mierzylibyśmy zupełnie inną drogę.
Weryfikacja w OSRM: wariant z punktem pośrednim i bez niego dają identyczne
9,68 km i 13,0 min, a przebieg obejmuje ulice Śremską, Kilińskiego, most
Kęszyckiego, Piłsudskiego, most Chosłowskiego i Średzką.

**Rondo „przy jednostce wojskowej”** zidentyfikowano tak: w OSM w promieniu
gminy istnieje jeden teren `landuse=military` o nazwie *6 Batalion Dowodzenia
Sił Powietrznych (JW 4430)* (`way 293800724`). Zmierzono odległość od jego
granicy do centroidów wszystkich rond w okolicy:

| Rondo | Odległość od ogrodzenia jednostki |
|---|---|
| **Armii Krajowej** | **56 m** |
| Powstańców Wielkopolskich | 296 m |
| Jana Pawła II | 487 m |

Różnica jest na tyle duża, że przypisanie nie budzi wątpliwości.

Zmiana punktu docelowego zmienia geometrię trasy, więc — zgodnie z zasadą
opisaną w sekcji 3b — każda z tych tras dostała **nowe `id`**. Pomiary spod
starych identyfikatorów zostają w historii, ale nie są już zasilane.

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

## 3b. Dwie trasy z ronda przy stacji BP

Obie startują w tym samym miejscu — **Rondo Premiera Stanisława Mikołajczyka**
(`52.10643, 17.04321`, OSM `ref = "432;434"`), przy którym stoi stacja BP.
Rondo jest węzłem obwodnicy z ul. Średzką i leży 2,03 km od Starego Rynku.

| Trasa | Cel | Długość (OSRM) | Czas bez ruchu |
|---|---|---|---|
| Z obwodnicy do centrum | Plac 20 Października | 2,10 km | 3,2 min |
| Objazd obwodnicą na Gostyńską | Gostyńska × Staszica | 4,82 km | 4,8 min |

**Cel pierwszej trasy.** Plac 20 Października jest w OSM siedmioma odcinkami
jezdni (`highway=residential`) tworzącymi obrys placu; jako punkt przyjęto ich
centroid `52.09485, 17.02137`. Trasa prowadzi ul. Średzką, **mostem Majora
Stefana Chosłowskiego** (`52.10385, 17.03572`) i ul. Poznańską. To inny most niż
remontowany most Daniela Kęszyckiego (`52.09208, 17.01927`) — obiekty
potwierdzone w OSM jako osobne.

**Cel drugiej trasy.** Skrzyżowanie ul. Gostyńskiej z ul. Stanisława Staszica
wyznaczono jednoznacznie: zapytanie Overpass o wspólne węzły odcinków obu ulic
zwróciło **dokładnie jeden** wynik — `node 270295855`, `52.0786487, 17.0288189`.

Rozkład drugiej trasy według kroków OSRM:

| Odcinek | Długość |
|---|---|
| wyjazd z ronda Mikołajczyka | 79 m |
| obwodnica (odcinki bez nazwy własnej) | 3 908 m |
| ul. Gostyńska do skrzyżowania ze Staszica | 832 m |

3,91 km obwodnicy zgadza się z niezależnym pomiarem jej długości: suma jezdni
o `ref = "432;434"` w OSM daje 4,06 km. Trasa pokrywa więc niemal całą
obwodnicę i jest tym samym ciągiem, którym prowadzony jest objazd zamkniętego
kierunku na moście. Dodano punkt pośredni `52.09198, 17.04189`; nie zmienia on
geometrii (4,82 km z waypointem i bez), ale zabezpiecza przed sytuacją, w której
silnik przy zatorze na obwodnicy przełączyłby trasę na przejazd przez miasto
i pomiar zacząłby dotyczyć czegoś innego.

**Co zastąpiły te trasy.** Do 1 września 2026 mierzone były: „Z obwodnicy do
centrum” z celem na Starym Rynku (2,30 km) oraz „Objazd obwodnicą
(Poznań → Leszno)” — przejazd tranzytowy o długości 17,9 km, z czego 14 km
stanowiły dojazdy po 7 km z obu stron miasta. Ta druga trasa była mylona
z długością samej obwodnicy i rozmywała sygnał: kilkuminutowy zator na 4 km
obwodnicy ginął w 14 km swobodnej jazdy poza miastem. Obie zastąpiono trasami
z tabeli powyżej.

Ponieważ zmieniła się geometria, a nie tylko opis, **nadano nowe identyfikatory**
(`obwodnica-plac20`, `objazd-gostynska`). Pomiary sprzed zmiany zostają
w historii pod dawnymi identyfikatorami (`obwodnica-centrum` — 1 pomiar,
`objazd-obwodnica` — 6 pomiarów) i nie są mieszane z nowymi przy liczeniu
profilu godzinowego.
## 3c. Zużycie darmowego limitu

Darmowy próg Routing API to **20 000 zapytań miesięcznie**
(źródło: <https://docs.tomtom.com/pricing>, weryfikacja 1 września 2026 —
wiersz „Routing API … Free 20K monthly”, identyczny dla TomTom Maps i Orbis
Maps). Próg 2,5 tys./mies. dotyczy *Matrix* Routing API, czyli innego produktu.

Harmonogram dobrano tak, żeby zmieścić się z zapasem:

| Okno (UTC) | Czas letni (CEST) | Czas zimowy (CET) | Częstotliwość | Przebiegów/dobę |
|---|---|---|---|---|
| 04:00–07:59 | 06:00–09:59 | 05:00–08:59 | co 10 min | 24 |
| 12:00–16:59 | 14:00–18:59 | 13:00–17:59 | co 10 min | 30 |
| 08:00–11:59 | 10:00–13:59 | 09:00–12:59 | co godzinę | 4 |
| 17:00–21:59 | 19:00–23:59 | 18:00–22:59 | co godzinę | 5 |
| 22:00–03:59 | 00:00–05:59 | 23:00–04:59 | **brak pomiarów** | 0 |

63 przebiegi × 8 tras = **504 zapytania na dobę ≈ 15 600 miesięcznie**
(31 dni), czyli ok. 22% zapasu do progu.

W nocy pomiarów nie ma świadomie: ruch jest wtedy swobodny, a każde zapytanie
zużywa ten sam limit, co zapytanie w szczycie. Konsekwencja jest taka, że nad
ranem strona pokaże pomiar sprzed kilku godzin — dlatego wiek danych jest na
niej wypisany wprost, a ostrzeżenie o nieaktualności pojawia się po 80 minutach.

Dodanie ósmej trasy („Z obwodnicy do centrum”) wymagało korekty: przy
dotychczasowych 72 przebiegach dawałoby 17 856 zapytań miesięcznie, a więc
zaledwie 12% zapasu — zbyt blisko progu, przy którym twardy limit w skrypcie
zatrzymałby pomiary przed końcem miesiąca. Zamiast rozrzedzać szczyt (gdzie
rozdzielczość 10 min jest najbardziej potrzebna) zmniejszono częstotliwość poza
szczytem z 30 do 60 minut. Dobowe zużycie pozostało dokładnie takie samo jak
przy siedmiu trasach.

Okna w UTC są celowo szersze niż polski szczyt, bo cron nie zna czasu letniego —
ten sam zapis musi działać przy UTC+1 i UTC+2.

### Dlaczego minuty nie są okrągłe

Pierwsza wersja harmonogramu używała zapisów `*/10` i `0`, czyli uruchamiała się
o pełnej godzinie i co dziesięć minut od niej. Przez pierwsze trzy godziny
istnienia repozytorium **nie wykonał się ani jeden przebieg z harmonogramu** —
osiem uruchomień w historii pochodziło wyłącznie z ręcznego `workflow_dispatch`,
a zapytanie `GET /repos/.../actions/runs?event=schedule` zwracało
`total_count=0`. Konfiguracja była przy tym poprawna: repozytorium publiczne,
workflow `active`, Actions włączone, plik na gałęzi domyślnej.

Przyczynę opisuje dokumentacja GitHuba w sekcji `schedule`:

> The schedule event can be delayed during periods of high loads of GitHub
> Actions workflow runs. High load times include the start of every hour. If the
> load is sufficiently high enough, **some queued jobs may be dropped**. To
> decrease the chance of delay, schedule your workflow to run at a different
> time of the hour.
>
> — [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

Oba crony trafiały dokładnie w minutę zerową, czyli w moment największego
obciążenia platformy. Po korekcie uruchamiają się w minutach `4, 14, 24, 34, 44,
54` (szczyt) oraz `27` (poza szczytem). Liczba przebiegów i zużycie limitu nie
zmieniły się ani o jedno zapytanie — zmienił się wyłącznie moment startu.

Wniosek praktyczny: harmonogram GitHub Actions **nie jest gwarancją**, tylko
prośbą. Dlatego strona pokazuje wiek danych wprost i ostrzega, gdy pomiar jest
starszy niż 80 minut, zamiast udawać, że liczba jest zawsze świeża.

Niezależnie od harmonogramu `fetch_traffic.py` przed każdym przebiegiem liczy
zapytania wykonane w bieżącym miesiącu (jeden wiersz historii = jedno zapytanie)
i przerywa pracę po 18 500. To zabezpieczenie na wypadek ręcznych uruchomień
i zmian w konfiguracji.

**Ograniczenie, o którym trzeba wiedzieć:** dane TomTom pochodzą z floty pojazdów
i urządzeń nawigacyjnych. Na drogach wojewódzkich w mniejszym mieście próbka jest
mniejsza niż na autostradzie, więc pomiar może reagować z opóźnieniem i wygładzać
krótkie zatory. Strona nie jest źródłem urzędowym i tak jest opisana.

## 3d. Jak świeże są dane widoczne w przeglądarce

### Wersjonowanie CSS i JavaScriptu

GitHub Pages serwuje wszystkie pliki z nagłówkiem `Cache-Control: max-age=600`
i nie pozwala tego zmienić. W praktyce oznacza to, że po wydaniu poprawki
przeglądarka może pobrać nowy `index.html`, ale zostać przy starym
`assets/style.css` — a wtedy użytkownik widzi albo rozjechany układ, albo (jak
w przypadku poprawionej legendy kolorów) po prostu starą treść, mimo że serwer
ma już nową.

Dlatego odnośniki do arkusza stylów i skryptu zawierają skrót zawartości pliku:

```html
<link rel="stylesheet" href="assets/style.css?v=a43c3a04">
<script src="assets/app.js?v=15bbec7f"></script>
```

Skrót wylicza `scripts/wersjonuj_zasoby.py` (pierwsze 8 znaków SHA-256).
Zmiana choćby jednego znaku w pliku zmienia adres, więc przeglądarka pobiera go
ponownie; gdy plik jest nietknięty, skrót zostaje ten sam i cache działa
normalnie. Skrypt jest idempotentny i uruchamia się automatycznie w workflow
przy każdym pomiarze, więc nie trzeba o nim pamiętać przy ręcznej edycji.

**Czego to nie naprawia:** sam `index.html` nadal podlega dziesięciominutowemu
cache'owi i tu nic nie da się zrobić bez własnego serwera. Po wydaniu zmiany
w treści strony trzeba więc albo odczekać do 10 minut, albo wymusić odświeżenie
(Ctrl+F5). Dotyczy to wyglądu i tekstów — nie liczb, bo te pobierane są osobno
i opisano je niżej.

Na wiek liczby na ekranie składają się trzy niezależne opóźnienia:

| Składnik | Wartość | Uwaga |
| --- | --- | --- |
| Cykl pomiaru | 10 min w szczycie, 60 min poza nim | harmonogram z sekcji 3c |
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
ostrzega, gdy pomiar jest starszy niż 80 min. Próg dobrano tak, aby nie
alarmował fałszywie poza szczytem (60 min cyklu + 10 min cache + margines).

## 4. Klasyfikacja kolorystyczna

Kolor jest heurystyką, nie pomiarem. Wynika z ostrzejszego z dwóch kryteriów:
stosunku czasu przejazdu do czasu przy pustej drodze oraz bezwzględnego
opóźnienia w minutach.

| Poziom (na stronie) | Nazwa w danych | Stosunek czasu | Opóźnienie | Wymagana realna strata |
|---|---|---|---|---|
| płynnie | `plynnie` | ≤ 1,15 | ≤ 3 min | — |
| lekko wolniej | `umiarkowanie` | ≤ 1,40 | ≤ 8 min | — |
| utrudnienia | `utrudnienia` | ≤ 1,80 | ≤ 15 min | ≥ 2,5 min |
| korek | `korek` | powyżej | powyżej | ≥ 5 min |

Druga kolumna to identyfikator zapisywany w `data/current.json` i w historii CSV.
Różni się od napisu widocznego na stronie tylko w jednym przypadku: poziom
`umiarkowanie` wyświetlany jest jako **„lekko wolniej”**, bo tak brzmi
naturalniej. Mapowanie znajduje się w stałej `ETYKIETY` w `assets/app.js` i przy
zmianie nazw trzeba poprawić je razem z legendą w `index.html`.

### Dlaczego doszła kolumna „wymagana realna strata”

Pierwsza wersja opierała ostrzeżenia wyłącznie na dwóch pierwszych kryteriach.
Po dodaniu tras krótkich (2,1 km z obwodnicy na Plac 20 Października i 4,8 km
objazdu) okazało się, że sam stosunek czasu daje wyniki nieporównywalne między
trasami — próg „korka” zależał od tego, jak długa jest trasa:

| Trasa | Czas przy pustej drodze | „Korek” od straty (przed) | Po poprawce |
|---|---|---|---|
| obwodnica → Plac 20 Października | 3,4 min | **2,7 min** | 5,1 min |
| objazd na Gostyńską | 4,5 min | 3,6 min | 5,1 min |
| od Gostynia | 10,5 min | **8,4 min** | 8,4 min |

Trzykrotny rozrzut oznaczał, że strona krzyczała „korek” przy stracie niecałych
trzech minut, zachęcając do objazdu droższego niż samo stanie. Dlatego poziomy
`utrudnienia` i `korek` wymagają teraz **jednocześnie** przekroczenia proporcji
i minimalnej realnej straty czasu (`progi.min_strata_min` w `scripts/config.json`).
Rozrzut progu „korka” spadł z 2,7–8,4 min do 5,1–8,5 min.

Sprawdzenie tej kalibracji na bieżących danych: `python scripts/test_progi.py`.
Skrypt niczego nie zapisuje — wypisuje, przy jakiej stracie czasu każda trasa
zmienia kolor.

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

## 7. Statystyki odwiedzin

Strona liczy odwiedziny przez **Cloudflare Web Analytics**. Powód jest prosty:
bez żadnego licznika nie da się stwierdzić, czy projekt komukolwiek służy, a to
jedyna przesłanka do decyzji, czy go rozwijać.

**Dlaczego nie wystarczy to, co daje GitHub.** Zakładka *Insights → Traffic*
w repozytorium liczy wyłącznie wejścia na stronę projektu na github.com oraz
klony, a nie ruch na `llyen.github.io`. Potwierdza to odpowiedź GitHub Support:
*„The traffic insights inside your repository only relate to views of your
repository on GitHub.com, not views of your Pages site"*. Sprawdzone też
empirycznie — po kilkudziesięciu odsłonach strony `traffic/views` zwracało
`count=0`. GitHub Pages nie ma wbudowanej statystyki odwiedzin.

**Co zostało wybrane i dlaczego.** Cloudflare Web Analytics działa bez zmiany
DNS i bez przepuszczania ruchu przez Cloudflare — wystarczy jeden znacznik
`<script>` w `index.html`. Dokumentacja opisuje usługę jako *„free,
privacy-first analytics for your website without changing your DNS or using
Cloudflare's proxy"* i deklaruje: *„Cloudflare Web Analytics does not collect or
use your visitors' personal data"*.

Skrypt ładuje się z `static.cloudflareinsights.com/beacon.min.js`, a dane
trafiają do `cloudflareinsights.com/cdn-cgi/rum` (adres dla witryn nieobsługiwanych
przez proxy Cloudflare). Token w kodzie strony nie jest sekretem — identyfikuje
witrynę i z założenia jest publiczny.

**Czego nie twierdzę.** W dokumentacji Cloudflare nie znalazłem wprost zdania,
że licznik nie używa ciasteczek, choć taka formuła krąży po internecie. Dlatego
stopka strony mówi dokładnie tyle, ile deklaruje dostawca — że nie zbiera danych
osobowych — i ani słowa więcej. Ocena, czy w tej sytuacji potrzebna jest zgoda
odwiedzającego, wykracza poza tę metodykę; przesłanką za jej brakiem jest
deklarowany brak danych osobowych i brak profilowania.

**Odrzucona alternatywa.** GoatCounter (otwarty kod, możliwość postawienia
u siebie) był drugim kandydatem. Odpadł, bo jego darmowy plan jest ograniczony
do zastosowań niekomercyjnych o warunkach, których nie udało się potwierdzić
w dokumentacji dostawcy — a Cloudflare nie stawia takiego warunku wprost.
