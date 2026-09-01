"""Generuje PRZYKLADOWE dane do lokalnego podgladu strony bez klucza TomTom.

To NIE sa pomiary rzeczywistego ruchu. Wynik jest jawnie oznaczony
w polu "zrodlo", a strona wyswietla wtedy czerwone ostrzezenie.
Nie uruchamiaj tego skryptu w srodowisku produkcyjnym.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "config.json"
DATA = ROOT / "data"

random.seed(42)


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    teraz = datetime.now(timezone.utc).replace(microsecond=0)
    trasy = []
    for i, t in enumerate(cfg["trasy"]):
        bez_ruchu = 480 + i * 40
        opoznienie = random.choice([30, 120, 300, 600, 1100])
        czas = bez_ruchu + opoznienie
        ratio = czas / bez_ruchu
        opozn_min = opoznienie / 60
        if ratio <= 1.15 and opozn_min <= 3:
            poziom = "plynnie"
        elif ratio <= 1.4 and opozn_min <= 8:
            poziom = "umiarkowanie"
        elif ratio <= 1.8 and opozn_min <= 15:
            poziom = "utrudnienia"
        else:
            poziom = "korek"
        trasy.append(
            {
                "id": t["id"],
                "nazwa": t["nazwa"],
                "opis": t["opis"],
                "droga": t["droga"],
                "skad": t.get("skad", ""),
                "dokad": t.get("dokad", ""),
                "uwaga": t.get("uwaga", ""),
                "czas_s": czas,
                "czas_bez_ruchu_s": bez_ruchu,
                "opoznienie_s": opoznienie,
                "dlugosc_m": 7000 + i * 500,
                "ratio": round(ratio, 3),
                "poziom": poziom,
            }
        )

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "current.json").write_text(
        json.dumps(
            {
                "pobrano_utc": teraz.isoformat(),
                "pobrano_lokalnie": (teraz + timedelta(hours=2)).isoformat(),
                "zrodlo": "DANE PRZYKŁADOWE - podglad lokalny, nie pomiar ruchu",
                "trasy": trasy,
                "bledy": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Zapisano data/current.json z danymi PRZYKLADOWYMI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
