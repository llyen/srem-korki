"""Wyznacza punkty pomiarowe tras na podstawie danych OpenStreetMap.

Skrypt odtwarza sposob, w jaki powstaly wspolrzedne w scripts/config.json:
pobiera z Overpass API wezly drog wojewodzkich wokol Sremu i dla kazdego
kierunku wybiera wezel o odleglosci w linii prostej najblizszej 7 km od
Starego Rynku.

Uruchamiaj tylko przy zmianie zestawu tras - Overpass to zasob wspolny
i nie nalezy go odpytywac bez potrzeby.

Uzycie:
    python scripts/wyznacz_punkty.py
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.parse
import urllib.request

OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "srem-korki/1.0 (projekt niekomercyjny)"

CENTRUM = (52.09238, 17.02226)  # Stary Rynek w Sremie, zrodlo: Nominatim
CEL_KM = 7.0

# (nazwa, ref drogi, zakres azymutu w stopniach od centrum)
KIERUNKI = [
    ("od-poznania (DW434, polnoc)", "434", (330.0, 30.0)),
    ("od-srody (DW432, polnocny wschod)", "432", (35.0, 80.0)),
    ("od-gostynia (DW434, poludnie)", "434", (150.0, 200.0)),
    ("od-leszna (DW432, poludniowy zachod)", "432", (200.0, 250.0)),
    ("od-czempinia (DW310, zachod)", "310", (260.0, 310.0)),
]

BBOX = (51.95, 16.75, 52.25, 17.25)


def odleglosc_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Przyblizenie rownoprostokatne. Blad wzgledem WGS84 to ok. 0,3% na 7 km."""
    r = 6371.0
    p = math.pi / 180
    x = (b[0] - a[0]) * p
    y = (b[1] - a[1]) * p * math.cos((a[0] + b[0]) / 2 * p)
    return r * math.hypot(x, y)


def azymut(a: tuple[float, float], b: tuple[float, float]) -> float:
    p = math.pi / 180
    y = (b[1] - a[1]) * math.cos((a[0] + b[0]) / 2 * p)
    x = b[0] - a[0]
    return (math.atan2(y, x) / p + 360) % 360


def w_zakresie(kat: float, zakres: tuple[float, float]) -> bool:
    od, do = zakres
    return od <= kat <= do if od <= do else kat >= od or kat <= do


def pobierz_wezly(refy: set[str]) -> dict[str, list[tuple[float, float]]]:
    wzorzec = "|".join(sorted(refy))
    zapytanie = (
        "[out:json][timeout:180];\n"
        f'way["ref"~"^({wzorzec})$"]["highway"]'
        f"({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});\nout geom;"
    )
    dane = urllib.parse.urlencode({"data": zapytanie}).encode()
    req = urllib.request.Request(OVERPASS, data=dane, headers={"User-Agent": UA})

    for proba in range(4):
        try:
            with urllib.request.urlopen(req, timeout=200) as odp:
                wynik = json.loads(odp.read().decode("utf-8"))
                break
        except Exception as exc:  # noqa: BLE001 - Overpass bywa przeciazony
            print(f"  proba {proba + 1} nieudana: {exc}", file=sys.stderr)
            time.sleep(25)
    else:
        raise SystemExit("Overpass nie odpowiedzial. Sprobuj pozniej.")

    wezly: dict[str, list[tuple[float, float]]] = {}
    for element in wynik.get("elements", []):
        ref = element.get("tags", {}).get("ref", "")
        for punkt in element.get("geometry", []) or []:
            wezly.setdefault(ref, []).append((punkt["lat"], punkt["lon"]))
    return wezly


def main() -> int:
    refy = {ref for _, ref, _ in KIERUNKI}
    print(f"Pobieram wezly drog {sorted(refy)} z Overpass API...")
    wezly = pobierz_wezly(refy)
    print(f"Pobrano {sum(len(v) for v in wezly.values())} wezlow.\n")

    print(f"{'kierunek':<38} {'lat':>9} {'lon':>9} {'km':>6} {'azymut':>7}")
    for nazwa, ref, zakres in KIERUNKI:
        kandydaci = [
            (p, odleglosc_km(CENTRUM, p))
            for p in wezly.get(ref, [])
            if w_zakresie(azymut(CENTRUM, p), zakres)
        ]
        if not kandydaci:
            print(f"{nazwa:<38} BRAK KANDYDATOW - sprawdz zakres azymutu")
            continue
        (lat, lon), km = min(kandydaci, key=lambda x: abs(x[1] - CEL_KM))
        print(f"{nazwa:<38} {lat:9.5f} {lon:9.5f} {km:6.2f} {azymut(CENTRUM, (lat, lon)):7.0f}")

    print("\nWspolrzedne przenies recznie do scripts/config.json po weryfikacji na mapie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
