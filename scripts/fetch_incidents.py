"""Pobiera zdarzenia drogowe z TomTom Traffic Incidents API i zostawia tylko te,
ktore leza przy trasach wjazdowych do Sremu.

Zapisuje data/incidents.json - zrodlo danych dla sekcji "Utrudnienia" na stronie.

Dlaczego filtr: prostokat obejmujacy nasze trasy lapie tez zdarzenia z okolic
Poznania i Kornika, ktore mieszkanca Sremu nie dotycza. Filtrujemy po odleglosci
od rzeczywistej geometrii tras (data/korytarz.json, tworzony przez
scripts/wyznacz_korytarz.py).

Wymaga zmiennej srodowiskowej TOMTOM_API_KEY.
Uzywa wylacznie biblioteki standardowej.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KORYTARZ = DATA / "korytarz.json"
WYNIK = DATA / "incidents.json"

for strumien in (sys.stdout, sys.stderr):
    try:
        strumien.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

API = "https://api.tomtom.com/traffic/services/5/incidentDetails"
TIMEOUT = 30
RETRIES = 3

# Darmowy prog TomTom dla Traffic Incidents API Details: 2 500 zapytan miesiecznie
# (zweryfikowane na https://docs.tomtom.com/pricing, wrzesien 2026). To osobny,
# znacznie wezszy prog niz 20 000 dla Routing API, ktore obsluguje pomiary czasu.
LIMIT_MIESIECZNY = 2500
ZAPAS = 300

# Minimalny odstep miedzy zapytaniami. Pomiary czasu przejazdu chodza co 10-20 min,
# ale zdarzenia drogowe zmieniaja sie wolniej, a prog jest waski - patrz wyzej.
# Odstep liczymy od znacznika w data/incidents.json, wiec jest odporny na to,
# jak gesto workflow zostanie wywolany.
MIN_ODSTEP_MIN = 28

# Promien dopasowania zdarzenia do trasy. Korytarz ma punkty co 100 m, wiec
# 250 m obejmuje takze zdarzenia opisane na sasiedniej jezdni lub na wezle,
# a jednoczesnie odsiewa rownolegle ulice odlegle o kilkaset metrow.
PROMIEN_M = 250

# Margines wokol korytarza przy budowie prostokata zapytania (stopnie).
# ~0.02 stopnia to ok. 2 km - zapas na zdarzenia opisane odcinkiem
# zaczynajacym sie tuz obok naszej trasy.
MARGINES_ST = 0.02

KATEGORIE = {
    0: "nieznane",
    1: "wypadek",
    2: "mgla",
    3: "niebezpieczne warunki",
    4: "deszcz",
    5: "oblodzenie",
    6: "korek",
    7: "zwezenie",
    8: "zamkniecie",
    9: "roboty",
    10: "wiatr",
    11: "zalanie",
    14: "unieruchomiony pojazd",
}

# Kategorie, ktore realnie zmieniaja sposob dojazdu. Deszcz czy wiatr sa
# w API traktowane jako zdarzenia drogowe, ale na stronie o korkach
# bylyby szumem.
ISTOTNE = {1, 3, 6, 7, 8, 9, 11, 14}

# TomTom zwraca polskie opisy w formie zdekomponowanej i z bledna diakrytyka:
# "zamkniȩty" to litera "e" + U+0327 COMBINING CEDILLA, zamiast "e" + U+0328
# COMBINING OGONEK. Po podmianie znaku laczacego normalizacja NFC sklada
# poprawne "ę" i "ą". Sprawdzone na odpowiedzi API z 2 wrzesnia 2026.
ZLY_OGONEK = "\u0327"
DOBRY_OGONEK = "\u0328"


def popraw_znaki(tekst: str) -> str:
    return unicodedata.normalize("NFC", tekst.replace(ZLY_OGONEK, DOBRY_OGONEK))


def czas_lokalny(moment: datetime) -> datetime:
    """Zwraca moment w czasie polskim (CET/CEST) - kopia logiki z fetch_traffic.py."""
    rok = moment.year
    ost_marzec = max(d for d in range(25, 32) if datetime(rok, 3, d).weekday() == 6)
    ost_pazdziernik = max(d for d in range(25, 32) if datetime(rok, 10, d).weekday() == 6)
    start = datetime(rok, 3, ost_marzec, 1, tzinfo=timezone.utc)
    koniec = datetime(rok, 10, ost_pazdziernik, 1, tzinfo=timezone.utc)
    offset = 2 if start <= moment.astimezone(timezone.utc) < koniec else 1
    return moment.astimezone(timezone(timedelta(hours=offset)))


def odleglosc_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def wczytaj_poprzednie() -> dict:
    if not WYNIK.exists():
        return {}
    try:
        return json.loads(WYNIK.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def zapytaj(bbox: str, klucz: str) -> dict:
    pola = (
        "{incidents{geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,"
        "events{description,iconCategory},startTime,endTime,from,to,length,delay,"
        "roadNumbers,probabilityOfOccurrence}}}"
    )
    params = urllib.parse.urlencode(
        {
            "key": klucz,
            "bbox": bbox,
            "fields": pola,
            "language": "pl-PL",
            "timeValidityFilter": "present",
        }
    )
    url = f"{API}?{params}"
    ostatni: Exception | None = None
    for proba in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as odp:
                return json.loads(odp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            tresc = exc.read().decode("utf-8", "replace")[:300]
            ostatni = RuntimeError(f"HTTP {exc.code}: {tresc}")
            if exc.code in (400, 403):
                break
        except Exception as exc:  # noqa: BLE001
            ostatni = exc
        time.sleep(2 * (proba + 1))
    raise RuntimeError(f"TomTom nie odpowiedzial poprawnie: {ostatni}")


def wierzcholki(geometria: dict) -> list[tuple[float, float]]:
    """Zwraca liste (lat, lon) - GeoJSON podaje wspolrzedne jako [lon, lat]."""
    wsp = geometria.get("coordinates") or []
    if geometria.get("type") == "Point":
        wsp = [wsp]
    wynik = []
    for para in wsp:
        if isinstance(para, (list, tuple)) and len(para) >= 2:
            wynik.append((float(para[1]), float(para[0])))
    return wynik


def przy_trasie(punkty_zdarzenia, korytarz, promien_m: float) -> bool:
    for lat, lon in punkty_zdarzenia:
        for klat, klon in korytarz:
            # tani filtr wstepny - haversine dla 262 x N par kosztuje niepotrzebnie
            if abs(lat - klat) > 0.01 or abs(lon - klon) > 0.02:
                continue
            if odleglosc_m(lat, lon, klat, klon) <= promien_m:
                return True
    return False


def main() -> int:
    klucz = os.environ.get("TOMTOM_API_KEY", "").strip()
    if not klucz:
        print("BLAD: brak zmiennej srodowiskowej TOMTOM_API_KEY", file=sys.stderr)
        return 2

    if not KORYTARZ.exists():
        print(
            "BLAD: brak data/korytarz.json - uruchom najpierw scripts/wyznacz_korytarz.py",
            file=sys.stderr,
        )
        return 2

    kor = json.loads(KORYTARZ.read_text(encoding="utf-8"))
    korytarz = [(p[0], p[1]) for p in kor["punkty"]]

    teraz_utc = datetime.now(timezone.utc).replace(microsecond=0)
    teraz_pl = czas_lokalny(teraz_utc)
    poprzednie = wczytaj_poprzednie()

    # Odstep miedzy zapytaniami
    poprzedni_czas = poprzednie.get("pobrano_utc")
    if poprzedni_czas:
        try:
            ile_minut = (teraz_utc - datetime.fromisoformat(poprzedni_czas)).total_seconds() / 60
            if ile_minut < MIN_ODSTEP_MIN:
                print(
                    f"POMINIETO: od ostatniego pobrania minelo {ile_minut:.0f} min "
                    f"(minimum {MIN_ODSTEP_MIN}). Dane bez zmian."
                )
                return 0
        except ValueError:
            pass  # zepsuty znacznik nie moze blokowac pobrania

    # Budzet miesieczny
    zuzycie = poprzednie.get("zuzycie_miesieczne") or {}
    miesiac = f"{teraz_pl:%Y-%m}"
    zapytan = int(zuzycie.get("zapytan", 0)) if zuzycie.get("miesiac") == miesiac else 0
    budzet = LIMIT_MIESIECZNY - ZAPAS
    if zapytan + 1 > budzet:
        print(
            f"STOP: budzet miesieczny wyczerpany ({zapytan}/{budzet} zapytan). "
            "Pobranie pominiete, zeby nie wygenerowac kosztow.",
            file=sys.stderr,
        )
        return 0

    laty = [p[0] for p in korytarz]
    lony = [p[1] for p in korytarz]
    bbox = "{:.4f},{:.4f},{:.4f},{:.4f}".format(
        min(lony) - MARGINES_ST,
        min(laty) - MARGINES_ST,
        max(lony) + MARGINES_ST,
        max(laty) + MARGINES_ST,
    )

    try:
        odp = zapytaj(bbox, klucz)
    except Exception as exc:  # noqa: BLE001
        print(f"BLAD: {exc}", file=sys.stderr)
        return 1

    wszystkich = len(odp.get("incidents") or [])
    zdarzenia = []
    for inc in odp.get("incidents") or []:
        p = inc.get("properties") or {}
        kat = int(p.get("iconCategory") or 0)
        if kat not in ISTOTNE:
            continue
        if not przy_trasie(wierzcholki(inc.get("geometry") or {}), korytarz, PROMIEN_M):
            continue
        opisy = [e.get("description") for e in (p.get("events") or []) if e.get("description")]
        zdarzenia.append(
            {
                "opis": popraw_znaki("; ".join(opisy)) or KATEGORIE.get(kat, "zdarzenie"),
                "kategoria": kat,
                "kategoria_nazwa": KATEGORIE.get(kat, "zdarzenie"),
                "waga": int(p.get("magnitudeOfDelay") or 0),
                "od": popraw_znaki(p.get("from") or ""),
                "do": popraw_znaki(p.get("to") or ""),
                "drogi": p.get("roadNumbers") or [],
                "opoznienie_s": int(p["delay"]) if p.get("delay") is not None else None,
                "dlugosc_m": int(p["length"]) if p.get("length") is not None else None,
                "od_kiedy": p.get("startTime") or "",
                "do_kiedy": p.get("endTime") or "",
            }
        )

    # Scalanie par opisujacych ten sam odcinek w obu kierunkach - dla mieszkanca
    # "Zamkniete: A -> B" i "Zamkniete: B -> A" to jedna informacja.
    scalone: dict[tuple, dict] = {}
    for z in zdarzenia:
        klucz_z = (z["opis"], z["kategoria"], frozenset({z["od"], z["do"]}))
        istniejace = scalone.get(klucz_z)
        if istniejace is None:
            scalone[klucz_z] = z
            continue
        istniejace["obie_strony"] = True
        # zostawiamy ostrzejszy wariant, bo o nim uzytkownik powinien wiedziec
        if z["waga"] > istniejace["waga"]:
            istniejace["waga"] = z["waga"]
        if (z["opoznienie_s"] or 0) > (istniejace["opoznienie_s"] or 0):
            istniejace["opoznienie_s"] = z["opoznienie_s"]

    finalne = sorted(
        scalone.values(),
        key=lambda z: (-z["waga"], -(z["opoznienie_s"] or 0), z["opis"]),
    )

    DATA.mkdir(parents=True, exist_ok=True)
    WYNIK.write_text(
        json.dumps(
            {
                "pobrano_utc": teraz_utc.isoformat(),
                "pobrano_lokalnie": teraz_pl.isoformat(),
                "zrodlo": "TomTom Traffic Incidents API v5 (timeValidityFilter=present)",
                "bbox": bbox,
                "promien_dopasowania_m": PROMIEN_M,
                "zdarzen_w_prostokacie": wszystkich,
                "zdarzen_przy_trasach": len(finalne),
                "zuzycie_miesieczne": {
                    "miesiac": miesiac,
                    "zapytan": zapytan + 1,
                    "budzet": budzet,
                },
                "zdarzenia": finalne,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"OK: {wszystkich} zdarzen w prostokacie -> {len(finalne)} przy trasach, "
        f"zuzycie: {zapytan + 1}/{budzet}"
    )
    for z in finalne:
        strony = " (obie strony)" if z.get("obie_strony") else ""
        print(f"  [{z['waga']}] {z['kategoria_nazwa']:<12} {z['opis']} | {z['od']} -> {z['do']}{strony}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
