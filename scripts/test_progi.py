"""Kontrola klasyfikacji kolorow na danych z data/current.json.

Uruchomienie: python scripts/test_progi.py
Skrypt niczego nie zapisuje - sluzy do sprawdzenia, przy jakiej realnej stracie
czasu kazda trasa zmienia kolor. Powstal po tym, jak okazalo sie, ze trasa
2-kilometrowa osiagala poziom "korek" przy stracie 2,7 minuty, a trasa
9-kilometrowa dopiero przy 8,4 minuty.
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

from fetch_traffic import ocen_poziom  # noqa: E402

KORZEN = Path(__file__).resolve().parent.parent
PROGI = json.loads((KORZEN / "scripts" / "config.json").read_text(encoding="utf-8"))["progi"]
CURRENT = KORZEN / "data" / "current.json"

POZIOMY = ["plynnie", "umiarkowanie", "utrudnienia", "korek"]


def prog_straty(bez_ruchu_min: float, docelowy: str) -> float:
    """Najmniejsza strata w minutach, przy ktorej trasa osiaga dany poziom."""
    strata = 0.0
    while strata < 120:
        if ocen_poziom((bez_ruchu_min + strata) / bez_ruchu_min, strata, PROGI) == docelowy:
            return strata
        strata += 0.1
    return float("nan")


def main() -> int:
    dane = json.loads(CURRENT.read_text(encoding="utf-8"))

    print(f"Dane z {dane['pobrano_lokalnie']}\n")
    print(f"{'trasa':<20}{'km':>6}{'pusta':>7}{'strata':>8}{'poziom':>14}")
    for t in sorted(dane["trasy"], key=lambda x: x["dlugosc_m"]):
        bez = t["czas_bez_ruchu_s"] / 60
        strata = t["opoznienie_s"] / 60
        poziom = ocen_poziom(t["czas_s"] / t["czas_bez_ruchu_s"], strata, PROGI)
        oznaczenie = "" if poziom == t["poziom"] else f"  (bylo: {t['poziom']})"
        print(
            f"{t['id']:<20}{t['dlugosc_m'] / 1000:>6.2f}{bez:>7.1f}"
            f"{strata:>8.1f}{poziom:>14}{oznaczenie}"
        )

    print("\nPrzy jakiej stracie czasu trasa zmienia kolor:")
    print(f"{'trasa':<20}{'pusta':>7}{'umiark.':>10}{'utrudn.':>10}{'korek':>8}")
    for t in sorted(dane["trasy"], key=lambda x: x["dlugosc_m"]):
        bez = t["czas_bez_ruchu_s"] / 60
        progi = [prog_straty(bez, p) for p in POZIOMY[1:]]
        print(f"{t['id']:<20}{bez:>7.1f}" + "".join(f"{p:>10.1f}" for p in progi))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
