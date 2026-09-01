"""Buduje profil godzinowy (mediana opoznienia wg dnia tygodnia i godziny).

Czyta wszystkie pliki data/history/*.csv i zapisuje data/profile.json.
Profil sluzy do odpowiedzi na pytanie "o ktorej najlepiej jechac".

Zasada rzetelnosci: komorki z liczba pomiarow mniejsza niz MIN_PROBEK
sa oznaczane jako brak danych, a nie wypelniane wartoscia przyblizona.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history"
WYJSCIE = ROOT / "data" / "profile.json"

MIN_PROBEK = 3


def main() -> int:
    kubelki: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    liczba_wierszy = 0

    for plik in sorted(HISTORY.glob("*.csv")):
        with plik.open(newline="", encoding="utf-8") as fh:
            for wiersz in csv.DictReader(fh):
                try:
                    klucz = (wiersz["trasa"], int(wiersz["dzien_tygodnia"]), int(wiersz["godzina"]))
                    kubelki[klucz].append(int(wiersz["opoznienie_s"]))
                    liczba_wierszy += 1
                except (KeyError, ValueError):
                    continue

    profil: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for (trasa, dzien, godzina), wartosci in kubelki.items():
        if len(wartosci) < MIN_PROBEK:
            continue
        profil[trasa][f"{dzien}-{godzina}"] = {
            "mediana_opoznienia_s": int(statistics.median(wartosci)),
            "probek": len(wartosci),
        }

    WYJSCIE.write_text(
        json.dumps(
            {
                "min_probek": MIN_PROBEK,
                "pomiarow_lacznie": liczba_wierszy,
                "profil": profil,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"OK: {liczba_wierszy} pomiarow, {sum(len(v) for v in profil.values())} komorek profilu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
