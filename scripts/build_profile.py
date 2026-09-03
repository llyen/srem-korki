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
KONFIG = ROOT / "scripts" / "config.json"

MIN_PROBEK = 3


def aktualne_trasy() -> list[str]:
    """Identyfikatory tras, ktore strona rzeczywiscie pokazuje.

    Historia zawiera takze trasy wycofane: zmiana geometrii oznacza w tym
    projekcie nowe id, wiec stare pomiary opisuja inny przejazd. Wpuszczenie
    ich do profilu podstawialoby pod aktualna trase wynik z innej drogi.
    """
    konfig = json.loads(KONFIG.read_text(encoding="utf-8"))
    return [t["id"] for t in konfig["trasy"]]


def main() -> int:
    trasy = aktualne_trasy()
    kubelki: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    liczba_wierszy = 0
    pominietych = 0
    pomiarow_trasy: dict[str, int] = {t: 0 for t in trasy}
    daty: set[str] = set()

    for plik in sorted(HISTORY.glob("*.csv")):
        with plik.open(newline="", encoding="utf-8") as fh:
            for wiersz in csv.DictReader(fh):
                try:
                    trasa = wiersz["trasa"]
                    # Historia zapisuje dzien tygodnia w konwencji Pythona
                    # (datetime.weekday(): poniedzialek=0 ... niedziela=6),
                    # a strona filtruje wpisy wartoscia z Date.getDay()
                    # (niedziela=0 ... sobota=6). Bez tej zamiany kazdy pomiar
                    # trafialby pod dzien wczesniejszy - pomiary ze srody
                    # pokazywaly sie jako wtorkowe.
                    # Zamiana jest tutaj, a nie w fetch_traffic.py, zeby nie
                    # ruszac juz zapisanych danych surowych.
                    dzien = (int(wiersz["dzien_tygodnia"]) + 1) % 7
                    godzina = int(wiersz["godzina"])
                    opoznienie = int(wiersz["opoznienie_s"])
                except (KeyError, ValueError):
                    continue
                liczba_wierszy += 1
                # Data dnia pomiarowego brana wprost z czas_utc. Pomiary
                # wykonujemy tylko miedzy 6:00 a 20:00 czasu lokalnego, czyli
                # 4:00-18:00 UTC, wiec doba UTC i lokalna zawsze pokrywaja sie
                # tego samego dnia - nie trzeba tu przeliczac strefy. Gdyby
                # kiedys doszly pomiary nocne, to zalozenie przestanie
                # obowiazywac i date trzeba bedzie liczyc ze strefy lokalnej.
                czas = wiersz.get("czas_utc", "")
                if len(czas) >= 10:
                    daty.add(czas[:10])
                if trasa not in pomiarow_trasy:
                    pominietych += 1
                    continue
                kubelki[(trasa, dzien, godzina)].append(opoznienie)
                pomiarow_trasy[trasa] += 1

    profil: dict[str, dict[str, dict[str, object]]] = {t: {} for t in trasy}
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
                "pomiarow_trasy_wycofane": pominietych,
                "pomiarow_trasy": pomiarow_trasy,
                "dni_pomiarowe": len(daty),
                "od": min(daty) if daty else None,
                "do": max(daty) if daty else None,
                "profil": profil,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"OK: {liczba_wierszy} pomiarow w historii, {pominietych} z tras wycofanych, "
        f"{sum(len(v) for v in profil.values())} komorek profilu"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
