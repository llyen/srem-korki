#!/usr/bin/env python3
"""Liczy zuzycie darmowego limitu TomTom na podstawie harmonogramu Workera.

Zadna liczba w dokumentacji projektu nie ma byc przepisana z pamieci - ten
skrypt rozwija wyrazenia cron z worker/wrangler.toml i mnozy liczbe przebiegow
przez liczbe tras z scripts/config.json.

Uzycie:
    python scripts/policz_budzet.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
KORZEN = KATALOG.parent

PLIK_WRANGLER = KORZEN / "worker" / "wrangler.toml"
PLIK_CONFIG = KATALOG / "config.json"

# Darmowy prog Routing API to 20 000 zapytan miesiecznie. Skrypt pomiarowy
# pilnuje wlasnego, nizszego progu, zeby zostawic zapas na uruchomienia reczne.
LIMIT_MIESIECZNY = 20_000
PROG_ROBOCZY = 18_500
NAJDLUZSZY_MIESIAC = 31


def rozwin_pole(pole: str, zakres: range) -> set[int]:
    """Zamienia jedno pole wyrazenia cron na zbior wartosci.

    Obsluguje: '*', liczby, listy po przecinku, zakresy 'a-b' i krok '*/n'.
    """
    wartosci: set[int] = set()

    for czesc in pole.split(","):
        czesc = czesc.strip()
        krok = 1

        if "/" in czesc:
            czesc, tekst_kroku = czesc.split("/", 1)
            krok = int(tekst_kroku)

        if czesc == "*":
            kandydaci = list(zakres)
        elif "-" in czesc:
            poczatek, koniec = (int(x) for x in czesc.split("-", 1))
            kandydaci = list(range(poczatek, koniec + 1))
        else:
            kandydaci = [int(czesc)]

        wartosci.update(kandydaci[::krok] if krok > 1 else kandydaci)

    return wartosci


def przebiegi_na_dobe(wyrazenie: str) -> tuple[int, set[tuple[int, int]]]:
    """Zwraca liczbe uruchomien na dobe i zbior par (godzina, minuta).

    Zaklada, ze pola dnia miesiaca, miesiaca i dnia tygodnia to '*'. Gdyby
    kiedys przestaly nimi byc, skrypt przerwie zamiast podac zla liczbe.
    """
    pola = wyrazenie.split()
    if len(pola) != 5:
        raise ValueError(f"Wyrazenie cron musi miec 5 pol: {wyrazenie!r}")

    minuta, godzina, dzien_miesiaca, miesiac, dzien_tygodnia = pola

    for nazwa, pole in (
        ("dzien miesiaca", dzien_miesiaca),
        ("miesiac", miesiac),
        ("dzien tygodnia", dzien_tygodnia),
    ):
        if pole != "*":
            raise ValueError(
                f"Skrypt liczy tylko harmonogramy codzienne, a pole "
                f"'{nazwa}' to {pole!r}. Popraw skrypt zamiast zgadywac wynik."
            )

    minuty = rozwin_pole(minuta, range(0, 60))
    godziny = rozwin_pole(godzina, range(0, 24))
    terminy = {(g, m) for g in godziny for m in minuty}
    return len(terminy), terminy


def wczytaj_crony(sciezka: Path) -> list[str]:
    """Wyciaga wyrazenia cron z sekcji [triggers] pliku wrangler.toml.

    Swiadomie bez biblioteki TOML - plik ma jedna tablice crons, a zaleznosc
    zewnetrzna byla by tu nieproporcjonalna do zadania.
    """
    tekst = sciezka.read_text(encoding="utf-8")
    dopasowanie = re.search(r"crons\s*=\s*\[(.*?)\]", tekst, re.DOTALL)
    if not dopasowanie:
        raise ValueError(f"Nie znalazlem tablicy 'crons' w {sciezka}")

    return re.findall(r'"([^"]+)"', dopasowanie.group(1))


def main() -> int:
    crony = wczytaj_crony(PLIK_WRANGLER)
    config = json.loads(PLIK_CONFIG.read_text(encoding="utf-8"))
    trasy = config["trasy"]

    print(f"Plik harmonogramu: {PLIK_WRANGLER.relative_to(KORZEN)}")
    print(f"Liczba tras: {len(trasy)}\n")

    wszystkie_terminy: set[tuple[int, int]] = set()

    for wyrazenie in crony:
        liczba, terminy = przebiegi_na_dobe(wyrazenie)
        nachodzace = wszystkie_terminy & terminy
        wszystkie_terminy |= terminy

        print(f"  {wyrazenie:<36} {liczba:>3} przebiegow/dobe")
        if nachodzace:
            print(
                f"    UWAGA: {len(nachodzace)} terminow pokrywa sie z "
                f"wczesniejszym wyrazeniem - policzone raz."
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
