"""Wyznacza korytarz tras - liste punktow geograficznych, ktore pokrywaja
rzeczywisty przebieg wszystkich tras z config.json.

Sluzy do filtrowania zdarzen drogowych: pokazujemy tylko te, ktore leza przy
naszych trasach, a nie wszystko, co TomTom widzi w prostokacie wokol Sremu.

Geometrie pobiera z TomTom Routing API (to samo API co pomiary czasu, wiec
ten sam prog 20 000 zapytan miesiecznie). Uruchamiany RECZNIE i rzadko -
przebieg drog nie zmienia sie z godziny na godzine. Wynik trafia do repo,
wiec workflow nie musi go pobierac.

Uzycie:
    TOMTOM_API_KEY=... python scripts/wyznacz_korytarz.py

Wymaga wylacznie biblioteki standardowej.
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "config.json"
WYNIK = ROOT / "data" / "korytarz.json"

for strumien in (sys.stdout, sys.stderr):
    try:
        strumien.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

API_BASE = "https://api.tomtom.com/routing/1/calculateRoute"
TIMEOUT = 30

# Co ile metrow zostawiamy punkt polilinii. TomTom zwraca punkty co kilka metrow,
# co dawaloby plik na setki kilobajtow bez zysku dokladnosci - przy promieniu
# dopasowania 250 m (patrz fetch_incidents.py) siatka co 100 m w zupelnosci
# wystarcza, bo najwieksza mozliwa luka miedzy punktami jest duzo mniejsza
# niz promien.
KROK_M = 100


def odleglosc_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Odleglosc po powierzchni kuli (haversine), w metrach."""
    R = 6371000.0
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def pobierz_geometrie(punkty: list[dict], klucz: str) -> list[tuple[float, float]]:
    lokalizacje = ":".join(f"{p['lat']},{p['lon']}" for p in punkty)
    params = urllib.parse.urlencode(
        {
            "key": klucz,
            "traffic": "false",  # interesuje nas sam przebieg drogi, nie biezacy ruch
            "travelMode": "car",
            "routeType": "fastest",
            "routeRepresentation": "polyline",
        }
    )
    url = f"{API_BASE}/{lokalizacje}/json?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as odp:
        dane = json.loads(odp.read().decode("utf-8"))
    wynik: list[tuple[float, float]] = []
    for leg in dane["routes"][0]["legs"]:
        for p in leg["points"]:
            wynik.append((float(p["latitude"]), float(p["longitude"])))
    return wynik


def przerzedz(punkty: list[tuple[float, float]], krok_m: float) -> list[tuple[float, float]]:
    """Zostawia pierwszy punkt, potem kolejny dopiero po przebyciu krok_m."""
    if not punkty:
        return []
    wynik = [punkty[0]]
    for p in punkty[1:]:
        if odleglosc_m(wynik[-1][0], wynik[-1][1], p[0], p[1]) >= krok_m:
            wynik.append(p)
    if wynik[-1] != punkty[-1]:
        wynik.append(punkty[-1])
    return wynik


def main() -> int:
    klucz = os.environ.get("TOMTOM_API_KEY", "").strip()
    if not klucz:
        print("BLAD: brak zmiennej srodowiskowej TOMTOM_API_KEY", file=sys.stderr)
        return 2

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    trasy = cfg["trasy"]
    wszystkie: list[list[float]] = []
    opis_tras = []

    for trasa in trasy:
        try:
            surowe = pobierz_geometrie(trasa["punkty"], klucz)
        except Exception as exc:  # noqa: BLE001
            print(f"BLAD: trasa {trasa['id']}: {exc}", file=sys.stderr)
            return 1
        rzadkie = przerzedz(surowe, KROK_M)
        dlugosc = sum(
            odleglosc_m(a[0], a[1], b[0], b[1]) for a, b in zip(rzadkie, rzadkie[1:])
        )
        print(
            f"  {trasa['id']:<24} punktow {len(surowe):>4} -> {len(rzadkie):>3}, "
            f"dlugosc {dlugosc / 1000:.2f} km"
        )
        opis_tras.append({"id": trasa["id"], "punktow": len(rzadkie), "dlugosc_km": round(dlugosc / 1000, 2)})
        wszystkie.extend([round(p[0], 5), round(p[1], 5)] for p in rzadkie)

    # Usuwamy duplikaty - trasy nakladaja sie na wspolnych odcinkach w miescie.
    unikalne = []
    widziane = set()
    for para in wszystkie:
        klucz_p = (para[0], para[1])
        if klucz_p not in widziane:
            widziane.add(klucz_p)
            unikalne.append(para)

    WYNIK.parent.mkdir(parents=True, exist_ok=True)
    WYNIK.write_text(
        json.dumps(
            {
                "_opis": (
                    "Punkty (lat, lon) na przebiegu tras z config.json, przerzedzone co "
                    f"{KROK_M} m. Sluzy do filtrowania zdarzen drogowych - patrz "
                    "scripts/fetch_incidents.py."
                ),
                "wyznaczono_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "zrodlo": "TomTom Routing API (routeRepresentation=polyline, traffic=false)",
                "krok_m": KROK_M,
                "trasy": opis_tras,
                "punkty": unikalne,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"OK: {len(unikalne)} unikalnych punktow -> {WYNIK.relative_to(ROOT)}")
    print(f"    zapytan do API: {len(trasy)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
