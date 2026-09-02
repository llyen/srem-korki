"""Konfiguruje zewnetrzny zegar pomiarow w serwisie cron-job.org.

Po co osobny zegar
------------------
Harmonogram probowano trzymac najpierw w GitHub Actions (`on: schedule`),
potem w cron triggers Cloudflare. Zadna z tych platform nie uruchomila zadania
ani razu, mimo poprawnej konfiguracji potwierdzonej w ich wlasnych API.
Dowody sa opisane w docs/METODYKA.md, sekcja 3c.

Zegar wola adres Workera z parametrem ?wyzwol=<klucz>, a Worker zamawia pomiar
przez workflow_dispatch. Dzieki temu token GitHuba zostaje w Cloudflare -
serwis zewnetrzny zna tylko adres i klucz wyzwalacza, ktore mozna uniewaznic
bez ruszania tokenu.

Strefa czasowa
--------------
W przeciwienstwie do GitHuba i Cloudflare (wylacznie UTC) cron-job.org
przyjmuje strefe lokalna. Pory pomiarow sa wiec zapisane w Europe/Warsaw i nie
przesuwaja sie przy zmianie czasu na zimowy.

Uzycie:
    $env:CRONJOB_API_KEY = "<klucz API z cron-job.org>"
    python scripts/konfiguruj_zegar.py
    python scripts/konfiguruj_zegar.py --sprawdz   # sam podglad, bez zmian
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLIK_KLUCZA = ROOT / "worker" / ".klucz-wyzwalacza.txt"

API = "https://api.cron-job.org"
ADRES_WORKERA = "https://srem-korki-cron.jakub-461.workers.dev/"
STREFA = "Europe/Warsaw"

# Prefiks tytulu. Zadania na koncie zaczynajace sie od niego, ktorych nie ma
# na liscie ZADANIA, sa kasowane - patrz komentarz przy sprzataniu w main().
PREFIKS = "srem-korki:"

# Szczyt: co 10 minut. Rano 6:00-9:59, popoludniu 14:00-17:59 czasu lokalnego.
# Poza szczytem: co 20 minut, 10:00-13:59 i 18:00-19:59.
# Noc (20:00-6:00) pominieta swiadomie - nie ma wtedy zatorow, a kazdy pomiar
# kosztuje 8 zapytan z ograniczonej puli TomTom.
ZADANIA = [
    {
        "tytul": "srem-korki: szczyt (co 10 min)",
        "godziny": [6, 7, 8, 9, 14, 15, 16, 17],
        "minuty": [4, 14, 24, 34, 44, 54],
    },
    {
        "tytul": "srem-korki: poza szczytem (co 20 min)",
        "godziny": [10, 11, 12, 13, 18, 19],
        "minuty": [12, 32, 52],
    },
]


def zapytaj(metoda: str, sciezka: str, klucz: str, dane: dict | None = None) -> dict:
    zadanie = urllib.request.Request(
        f"{API}{sciezka}",
        method=metoda,
        data=json.dumps(dane).encode("utf-8") if dane is not None else None,
        headers={
            "Authorization": f"Bearer {klucz}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(zadanie, timeout=30) as odp:
            tresc = odp.read().decode("utf-8")
            return json.loads(tresc) if tresc.strip() else {}
    except urllib.error.HTTPError as blad:
        tresc = blad.read().decode("utf-8", "replace")
        raise SystemExit(f"BLAD {metoda} {sciezka}: HTTP {blad.code} {tresc}") from blad


def opis_zadania(zadanie: dict, adres: str) -> dict:
    return {
        "url": adres,
        "enabled": True,
        "title": zadanie["tytul"],
        "saveResponses": True,
        "requestMethod": 0,
        "requestTimeout": 30,
        "notification": {"onFailure": True, "onSuccess": False, "onDisable": True},
        "schedule": {
            "timezone": STREFA,
            "expiresAt": 0,
            "hours": zadanie["godziny"],
            "minutes": zadanie["minuty"],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1],
        },
    }


def main() -> int:
    tylko_podglad = "--sprawdz" in sys.argv

    klucz_api = os.environ.get("CRONJOB_API_KEY", "").strip()
    if not klucz_api:
        print("Brak zmiennej CRONJOB_API_KEY.", file=sys.stderr)
        return 2

    if not PLIK_KLUCZA.exists():
        print(f"Brak pliku z kluczem wyzwalacza: {PLIK_KLUCZA}", file=sys.stderr)
        return 2
    adres = ADRES_WORKERA + "?wyzwol=" + PLIK_KLUCZA.read_text(encoding="utf-8").strip()

    istniejace = {
        z.get("title"): z.get("jobId")
        for z in zapytaj("GET", "/jobs", klucz_api).get("jobs", [])
    }
    print(f"Zadan na koncie: {len(istniejace)}")

    for zadanie in ZADANIA:
        tytul = zadanie["tytul"]
        pomiarow = len(zadanie["godziny"]) * len(zadanie["minuty"])
        print(f"\n{tytul}: {pomiarow} pomiarow na dobe")

        if tylko_podglad:
            continue

        opis = opis_zadania(zadanie, adres)
        if tytul in istniejace:
            zapytaj("PATCH", f"/jobs/{istniejace[tytul]}", klucz_api, {"job": opis})
            job_id = istniejace[tytul]
            print(f"  zaktualizowano zadanie {job_id}")
        else:
            job_id = zapytaj("PUT", "/jobs", klucz_api, {"job": opis})["jobId"]
            print(f"  utworzono zadanie {job_id}")
            # Tworzenie jest limitowane do 5 zadan na minute.
            time.sleep(1)

        szczegoly = zapytaj("GET", f"/jobs/{job_id}/history", klucz_api)
        for znacznik in szczegoly.get("predictions", [])[:3]:
            czas = time.strftime("%Y-%m-%d %H:%M", time.localtime(znacznik))
            print(f"  nastepne uruchomienie: {czas}")

    laczna = sum(len(z["godziny"]) * len(z["minuty"]) for z in ZADANIA)

    # Zadania sa dopasowywane po tytule, wiec zmiana tytulu (np. gdy zmieni sie
    # czestotliwosc w nazwie) tworzy nowe zadanie i zostawia stare dzialajace.
    # Dwa zadania strzelalyby rownolegle i po cichu podwajaly zuzycie TomToma,
    # dlatego osierocone zadania z naszym prefiksem trzeba skasowac.
    nasze = {z["tytul"] for z in ZADANIA}
    osierocone = {
        tytul: job_id
        for tytul, job_id in istniejace.items()
        if tytul and tytul.startswith(PREFIKS) and tytul not in nasze
    }
    for tytul, job_id in osierocone.items():
        if tylko_podglad:
            print(f"\nDO SKASOWANIA (osierocone): {tytul} [{job_id}]")
        else:
            zapytaj("DELETE", f"/jobs/{job_id}", klucz_api)
            print(f"\nskasowano osierocone zadanie: {tytul} [{job_id}]")

    print(f"\nRazem {laczna} pomiarow na dobe x 8 tras = {laczna * 8} zapytan do TomTom.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
