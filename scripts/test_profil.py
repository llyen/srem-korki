"""Sprawdza, czy dzien tygodnia nie gubi sie po drodze do wykresu profilu.

Lancuch jest trzyogniwowy i kazde ogniwo liczy dni inaczej:

  fetch_traffic.py  zapisuje datetime.weekday()  -> poniedzialek = 0
  build_profile.py  przelicza (weekday + 1) % 7  -> niedziela    = 0
  assets/app.js     czyta Date.getDay()          -> niedziela    = 0

Pomylka o jeden nie wywala niczego z bledem - po prostu pokazuje wykres
z innego dnia, czego nie widac golym okiem. Dlatego test sprawdza:

  1. zgodnosc zapisu w historii z faktyczna data pomiaru (czas_utc),
  2. przelozenie na klucz profilu dla wszystkich 7 dni tygodnia,
  3. czy klucze w data/profile.json trafiaja w te dni, ktore wynikaja
     z historii.

Uruchomienie: python scripts/test_profil.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history"
PROFIL = ROOT / "data" / "profile.json"

NAZWY_PL = ["poniedzialek", "wtorek", "sroda", "czwartek", "piatek", "sobota", "niedziela"]
NAZWY_JS = ["niedziela", "poniedzialek", "wtorek", "sroda", "czwartek", "piatek", "sobota"]

# Ten sam wzor, ktorego uzywa fetch_traffic.py. Powtorzony tutaj celowo:
# test ma byc niezalezny od kodu, ktory sprawdza.
def offset_pl(moment_utc: datetime) -> int:
    rok = moment_utc.year
    ost_marzec = max(d for d in range(25, 32) if datetime(rok, 3, d).weekday() == 6)
    ost_pazdziernik = max(d for d in range(25, 32) if datetime(rok, 10, d).weekday() == 6)
    start = datetime(rok, 3, ost_marzec, 1, tzinfo=timezone.utc)
    koniec = datetime(rok, 10, ost_pazdziernik, 1, tzinfo=timezone.utc)
    return 2 if start <= moment_utc < koniec else 1


def na_klucz_profilu(weekday: int) -> int:
    """Konwersja uzywana w build_profile.py."""
    return (weekday + 1) % 7


def test_mapowanie_wszystkich_dni() -> list[str]:
    """Kazdy z 7 dni musi trafic pod wlasciwy numer JS.

    Daty dobrane tak, zeby pokryc caly tydzien - bierzemy siedem kolejnych
    dni, wiec kazdy dzien tygodnia wystapi doklandie raz, niezaleznie od tego,
    od ktorego zaczniemy.
    """
    bledy = []
    baza = datetime(2026, 9, 7)  # poniedzialek, sprawdzony ponizej
    if baza.weekday() != 0:
        bledy.append(f"zla data bazowa testu: {baza:%Y-%m-%d} nie jest poniedzialkiem")
        return bledy

    for i in range(7):
        dzien = baza + timedelta(days=i)
        py = dzien.weekday()
        js_oczekiwany = int(dzien.strftime("%w"))  # niezalezne zrodlo: %w = niedziela 0
        js_policzony = na_klucz_profilu(py)
        if js_policzony != js_oczekiwany:
            bledy.append(
                f"{dzien:%Y-%m-%d} ({NAZWY_PL[py]}): przeliczono na {js_policzony} "
                f"({NAZWY_JS[js_policzony]}), a powinno byc {js_oczekiwany} "
                f"({NAZWY_JS[js_oczekiwany]})"
            )
    return bledy


def test_zapis_historii() -> tuple[list[str], dict[int, int]]:
    """dzien_tygodnia i godzina w CSV musza zgadzac sie z czas_utc."""
    bledy = []
    rozklad: dict[int, int] = defaultdict(int)
    sprawdzonych = 0

    for plik in sorted(HISTORY.glob("*.csv")):
        with plik.open(newline="", encoding="utf-8") as fh:
            for nr, wiersz in enumerate(csv.DictReader(fh), start=2):
                try:
                    utc = datetime.fromisoformat(wiersz["czas_utc"])
                    zapisany_dzien = int(wiersz["dzien_tygodnia"])
                    zapisana_godz = int(wiersz["godzina"])
                except (KeyError, ValueError):
                    continue

                lokalny = utc + timedelta(hours=offset_pl(utc))
                sprawdzonych += 1
                rozklad[na_klucz_profilu(lokalny.weekday())] += 1

                if lokalny.weekday() != zapisany_dzien:
                    bledy.append(
                        f"{plik.name}:{nr} czas {wiersz['czas_utc']} to "
                        f"{NAZWY_PL[lokalny.weekday()]} ({lokalny.weekday()}), "
                        f"a zapisano {zapisany_dzien}"
                    )
                if lokalny.hour != zapisana_godz:
                    bledy.append(
                        f"{plik.name}:{nr} czas {wiersz['czas_utc']} to godzina "
                        f"{lokalny.hour} lokalnie, a zapisano {zapisana_godz}"
                    )
                if len(bledy) > 20:
                    bledy.append("... (dalsze bledy pominieto)")
                    return bledy, rozklad

    print(f"  sprawdzono {sprawdzonych} wierszy historii")
    return bledy, rozklad


def test_klucze_profilu(rozklad_z_historii: dict[int, int]) -> list[str]:
    """Dni obecne w profilu musza wynikac z dni obecnych w historii."""
    bledy = []
    if not PROFIL.exists():
        return [f"brak pliku {PROFIL}"]

    dane = json.loads(PROFIL.read_text(encoding="utf-8"))
    dni_w_profilu = set()
    for komorki in dane["profil"].values():
        for klucz in komorki:
            dzien, _, godzina = klucz.partition("-")
            if not dzien.isdigit() or not godzina.isdigit():
                bledy.append(f"nieczytelny klucz profilu: {klucz}")
                continue
            if not 0 <= int(dzien) <= 6:
                bledy.append(f"dzien poza zakresem 0-6: {klucz}")
            dni_w_profilu.add(int(dzien))

    dni_w_historii = {d for d, ile in rozklad_z_historii.items() if ile > 0}
    nadmiarowe = dni_w_profilu - dni_w_historii
    if nadmiarowe:
        bledy.append(
            "profil zawiera dni, ktorych nie ma w historii: "
            + ", ".join(NAZWY_JS[d] for d in sorted(nadmiarowe))
        )
    return bledy


def main() -> int:
    print("1. Mapowanie dni tygodnia (wszystkie 7 dni)")
    bledy_map = test_mapowanie_wszystkich_dni()
    if bledy_map:
        for b in bledy_map:
            print("  BLAD: " + b)
    else:
        print("  OK: kazdy z 7 dni trafia pod wlasciwy numer")

    print("\n2. Zgodnosc zapisu w historii z data pomiaru")
    bledy_hist, rozklad = test_zapis_historii()
    if bledy_hist:
        for b in bledy_hist:
            print("  BLAD: " + b)
    else:
        print("  OK: dzien tygodnia i godzina zgadzaja sie z czas_utc")

    print("\n3. Pokrycie dni w danych")
    for d in range(7):
        ile = rozklad.get(d, 0)
        stan = f"{ile} pomiarow" if ile else "BRAK DANYCH"
        print(f"  {NAZWY_JS[d].ljust(13)} (klucz {d}): {stan}")

    print("\n4. Klucze w profile.json")
    bledy_prof = test_klucze_profilu(rozklad)
    if bledy_prof:
        for b in bledy_prof:
            print("  BLAD: " + b)
    else:
        print("  OK: klucze profilu mieszcza sie w dniach obecnych w historii")

    wszystkie = bledy_map + bledy_hist + bledy_prof
    print("\nWYNIK: " + ("BLEDY: " + str(len(wszystkie)) if wszystkie else "wszystko sie zgadza"))
    return 1 if wszystkie else 0


if __name__ == "__main__":
    sys.exit(main())
