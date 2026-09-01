"""Dopisuje skrot zawartosci do odnosnikow CSS/JS w index.html.

Powod: GitHub Pages serwuje pliki z naglowkiem Cache-Control max-age=600, a
przegladarka potrafi trzymac arkusz stylow i skrypt znacznie dluzej niz sam
dokument HTML. Bez wersjonowania uzytkownik dostaje nowy HTML ze starym CSS,
co wyglada jak zepsuta strona albo - czesciej - jak brak zmian.

Parametr ?v=<skrot> zmienia adres zasobu przy kazdej modyfikacji jego tresci,
wiec przegladarka pobiera go ponownie. Gdy plik sie nie zmienil, skrot zostaje
ten sam i cache dziala normalnie.

Uruchomienie: python scripts/wersjonuj_zasoby.py
Zwraca kod 0 zawsze; wypisuje, czy cokolwiek zmienil.
"""

import hashlib
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

KORZEN = Path(__file__).resolve().parent.parent
STRONA = KORZEN / "index.html"
ZASOBY = ["assets/style.css", "assets/app.js"]


def skrot(sciezka: Path) -> str:
    return hashlib.sha256(sciezka.read_bytes()).hexdigest()[:8]


def main() -> int:
    tresc = STRONA.read_text(encoding="utf-8")
    oryginal = tresc
    zmiany = []

    for zasob in ZASOBY:
        plik = KORZEN / zasob
        if not plik.exists():
            print(f"BLAD: brak pliku {zasob}", file=sys.stderr)
            return 1

        nowy = skrot(plik)
        wzorzec = re.compile(re.escape(zasob) + r"(\?v=[0-9a-f]+)?")

        obecne = {m.group(1) for m in wzorzec.finditer(tresc)}
        if not obecne:
            print(f"OSTRZEZENIE: {zasob} nie wystepuje w index.html", file=sys.stderr)
            continue

        tresc = wzorzec.sub(f"{zasob}?v={nowy}", tresc)
        if obecne != {f"?v={nowy}"}:
            zmiany.append(f"{zasob} -> ?v={nowy}")

    if tresc != oryginal:
        STRONA.write_text(tresc, encoding="utf-8")
        for z in zmiany:
            print(f"zaktualizowano: {z}")
    else:
        print("bez zmian - skroty zasobow sa aktualne")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
