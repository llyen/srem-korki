"""Pobiera czasy przejazdu tras wjazdowych do Sremu z TomTom Routing API.

Zapisuje:
  data/current.json          - ostatni pomiar (zrodlo danych dla strony)
  data/history/YYYY-MM.csv   - historia pomiarow (do profilu godzinowego)

Wymaga zmiennej srodowiskowej TOMTOM_API_KEY.
Uzywa wylacznie biblioteki standardowej - brak zaleznosci do instalacji w CI.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "config.json"
DATA = ROOT / "data"
HISTORY = DATA / "history"

# konsola Windows domyslnie uzywa cp1252 - bez tego polskie znaki wywalaja print()
for strumien in (sys.stdout, sys.stderr):
    try:
        strumien.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

API_BASE = "https://api.tomtom.com/routing/1/calculateRoute"
TIMEOUT = 30
RETRIES = 3
TZ_PL = timezone(timedelta(hours=1))  # czas urzedowy zapisujemy jako lokalny offset wyliczony nizej


def czas_lokalny(moment: datetime) -> datetime:
    """Zwraca moment w czasie polskim (CET/CEST) bez zaleznosci zewnetrznych.

    Reguła UE: czas letni od ostatniej niedzieli marca do ostatniej niedzieli
    pazdziernika, przelaczenie o 01:00 UTC.
    """
    rok = moment.year
    ost_marzec = max(d for d in range(25, 32) if datetime(rok, 3, d).weekday() == 6)
    ost_pazdziernik = max(d for d in range(25, 32) if datetime(rok, 10, d).weekday() == 6)
    start = datetime(rok, 3, ost_marzec, 1, tzinfo=timezone.utc)
    koniec = datetime(rok, 10, ost_pazdziernik, 1, tzinfo=timezone.utc)
    offset = 2 if start <= moment.astimezone(timezone.utc) < koniec else 1
    return moment.astimezone(timezone(timedelta(hours=offset)))


def zapytaj_tomtom(punkty: list[dict], klucz: str) -> dict:
    lokalizacje = ":".join(f"{p['lat']},{p['lon']}" for p in punkty)
    params = urllib.parse.urlencode(
        {
            "key": klucz,
            "traffic": "true",
            "travelMode": "car",
            "routeType": "fastest",
            "computeTravelTimeFor": "all",
            "departAt": "now",
        }
    )
    url = f"{API_BASE}/{lokalizacje}/json?{params}"
    ostatni_blad: Exception | None = None
    for proba in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as odp:
                return json.loads(odp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            tresc = exc.read().decode("utf-8", "replace")[:300]
            ostatni_blad = RuntimeError(f"HTTP {exc.code}: {tresc}")
            if exc.code in (400, 403):  # blad zapytania lub klucza - ponawianie nie pomoze
                break
        except Exception as exc:  # noqa: BLE001 - chcemy ponowic kazdy blad sieci
            ostatni_blad = exc
        time.sleep(2 * (proba + 1))
    raise RuntimeError(f"TomTom nie odpowiedzial poprawnie: {ostatni_blad}")


def ocen_poziom(ratio: float, opoznienie_min: float, progi: dict) -> str:
    pr = progi["ratio"]
    po = progi["opoznienie_min"]

    def wg(wartosc, prog):
        if wartosc <= prog["zielony"]:
            return 0
        if wartosc <= prog["zolty"]:
            return 1
        if wartosc <= prog["czerwony"]:
            return 2
        return 3

    poziom = max(wg(ratio, pr), wg(opoznienie_min, po))
    return ["plynnie", "umiarkowanie", "utrudnienia", "korek"][poziom]


def main() -> int:
    klucz = os.environ.get("TOMTOM_API_KEY", "").strip()
    if not klucz:
        print("BLAD: brak zmiennej srodowiskowej TOMTOM_API_KEY", file=sys.stderr)
        return 2

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    teraz_utc = datetime.now(timezone.utc).replace(microsecond=0)
    teraz_pl = czas_lokalny(teraz_utc)

    wyniki = []
    bledy = []
    for trasa in cfg["trasy"]:
        try:
            odp = zapytaj_tomtom(trasa["punkty"], klucz)
            s = odp["routes"][0]["summary"]
            czas = int(s["travelTimeInSeconds"])
            bez_ruchu = int(s.get("noTrafficTravelTimeInSeconds") or czas)
            bez_ruchu = max(bez_ruchu, 1)
            opoznienie = int(s.get("trafficDelayInSeconds") or max(0, czas - bez_ruchu))
            ratio = czas / bez_ruchu
            wyniki.append(
                {
                    "id": trasa["id"],
                    "nazwa": trasa["nazwa"],
                    "opis": trasa["opis"],
                    "droga": trasa["droga"],
                    "czas_s": czas,
                    "czas_bez_ruchu_s": bez_ruchu,
                    "opoznienie_s": opoznienie,
                    "dlugosc_m": int(s["lengthInMeters"]),
                    "ratio": round(ratio, 3),
                    "poziom": ocen_poziom(ratio, opoznienie / 60, cfg["progi"]),
                }
            )
        except Exception as exc:  # noqa: BLE001 - jedna zepsuta trasa nie moze zabic calego przebiegu
            print(f"OSTRZEZENIE: trasa {trasa['id']}: {exc}", file=sys.stderr)
            bledy.append({"id": trasa["id"], "nazwa": trasa["nazwa"], "blad": str(exc)[:200]})

    if not wyniki:
        print("BLAD: nie udalo sie pobrac zadnej trasy - nie nadpisuje danych", file=sys.stderr)
        return 1

    DATA.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)

    current = {
        "pobrano_utc": teraz_utc.isoformat(),
        "pobrano_lokalnie": teraz_pl.isoformat(),
        "zrodlo": "TomTom Routing API (traffic=true)",
        "trasy": wyniki,
        "bledy": bledy,
    }
    (DATA / "current.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    plik_hist = HISTORY / f"{teraz_pl:%Y-%m}.csv"
    nowy = not plik_hist.exists()
    with plik_hist.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nowy:
            w.writerow(
                ["czas_utc", "dzien_tygodnia", "godzina", "trasa", "czas_s", "czas_bez_ruchu_s", "opoznienie_s"]
            )
        for r in wyniki:
            w.writerow(
                [
                    teraz_utc.isoformat(),
                    teraz_pl.weekday(),
                    teraz_pl.hour,
                    r["id"],
                    r["czas_s"],
                    r["czas_bez_ruchu_s"],
                    r["opoznienie_s"],
                ]
            )

    print(f"OK: {len(wyniki)} tras, bledy: {len(bledy)}")
    for r in wyniki:
        print(f"  {r['id']:<20} {r['czas_s'] // 60:>3} min (+{r['opoznienie_s'] // 60} min) {r['poziom']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
