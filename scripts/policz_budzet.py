#!/usr/bin/env python3
"""Liczy zuzycie darmowego limitu TomTom na podstawie harmonogramu pomiarow.

Zadna liczba w dokumentacji projektu nie ma byc przepisana z pamieci - ten
skrypt czyta definicje zadan z scripts/konfiguruj_zegar.py (to samo zrodlo,
z ktorego konfigurowany jest zegar w cron-job.org) i mnozy liczbe przebiegow
przez liczbe tras z scripts/config.json.

Uwaga: harmonogram w worker/wrangler.toml jest NIECZYNNY - Cloudflare nie budzi
Workera. Zostal tam wylacznie jako zapis historyczny i nie wolno go tu liczyc.

Uzycie:
    python scripts/policz_budzet.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
KORZEN = KATALOG.parent
sys.path.insert(0, str(KATALOG))

from konfiguruj_zegar import ZADANIA, STREFA  # noqa: E402

PLIK_CONFIG = KATALOG / "config.json"

# Darmowy prog Routing API to 20 000 zapytan miesiecznie. Skrypt pomiarowy
# pilnuje wlasnego, nizszego progu, zeby zostawic zapas na uruchomienia reczne.
LIMIT_MIESIECZNY = 20_000
PROG_ROBOCZY = 18_500
NAJDLUZSZY_MIESIAC = 31


def terminy_zadania(zadanie: dict) -> set[tuple[int, int]]:
    """Zwraca zbior par (godzina, minuta) dla jednego zadania zegara."""
    return {(g, m) for g in zadanie["godziny"] for m in zadanie["minuty"]}


def main() -> int:
    config = json.loads(PLIK_CONFIG.read_text(encoding="utf-8"))
    trasy = config["trasy"]

    print("Zrodlo harmonogramu: scripts/konfiguruj_zegar.py (cron-job.org)")
    print(f"Strefa czasowa: {STREFA}")
    print(f"Liczba tras: {len(trasy)}\n")

    wszystkie_terminy: set[tuple[int, int]] = set()

    for zadanie in ZADANIA:
        terminy = terminy_zadania(zadanie)
        nachodzace = wszystkie_terminy & terminy
        wszystkie_terminy |= terminy

        print(f"  {zadanie['tytul']:<40} {len(terminy):>3} przebiegow/dobe")
        if nachodzace:
            print(
                f"    UWAGA: {len(nachodzace)} terminow pokrywa sie z "
                f"wczesniejszym zadaniem - policzone raz."
            )

    przebiegi = len(wszystkie_terminy)
    dziennie = przebiegi * len(trasy)
    miesiecznie = dziennie * NAJDLUZSZY_MIESIAC
    udzial = miesiecznie / PROG_ROBOCZY * 100

    print(f"\n  Razem: {przebiegi} przebiegow/dobe x {len(trasy)} tras "
          f"= {dziennie} zapytan/dobe")
    print(f"  Najdluzszy miesiac ({NAJDLUZSZY_MIESIAC} dni): {miesiecznie} zapytan")
    print(f"  Prog roboczy: {PROG_ROBOCZY} (limit TomTom: {LIMIT_MIESIECZNY})")
    print(f"  Wykorzystanie progu: {udzial:.1f}%")

    zapas_dziennie = (PROG_ROBOCZY // NAJDLUZSZY_MIESIAC) - dziennie
    if zapas_dziennie >= 0:
        print(f"  Zapas: {zapas_dziennie} zapytan/dobe "
              f"= {zapas_dziennie // len(trasy)} dodatkowych przebiegow")
    else:
        print(f"  PRZEKROCZENIE o {-zapas_dziennie} zapytan/dobe")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
