#!/usr/bin/env python3
"""Sprawdza, czy wlasna domena jest poprawnie podpieta do GitHub Pages.

Uzycie:
    python scripts/sprawdz_domene.py korkisrem.pl

Skrypt nie korzysta z bibliotek zewnetrznych - pyta system o rekordy przez
socket.getaddrinfo i probuje pobrac strone po HTTPS.

Uwaga o metodzie: getaddrinfo zwraca adresy IP po rozwinieciu calego lancucha
(CNAME tez), wiec nie odroznia rekordu A od CNAME. Dla wlasciwej domeny to
wystarcza - liczy sie, czy ruch trafia na adresy GitHuba. Rodzaj rekordu
sprawdz w panelu DNS albo poleceniem Resolve-DnsName.

Uruchamiany jest z kontrola pozytywna: to samo badanie wykonuje na
llyen.github.io, o ktorym wiadomo, ze wskazuje na GitHub Pages. Jesli kontrola
zawiedzie, znaczy to, ze zawodzi metoda pomiaru, a nie konfiguracja domeny.
"""
from __future__ import annotations

import socket
import ssl
import sys
import urllib.error
import urllib.request

# Adresy GitHub Pages wg dokumentacji (sprawdzone 2 wrzesnia 2026):
# https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
ADRESY_A = {
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
}
ADRESY_AAAA = {
    "2606:50c0:8000::153",
    "2606:50c0:8001::153",
    "2606:50c0:8002::153",
    "2606:50c0:8003::153",
}

KONTROLA = "llyen.github.io"
TYTUL_STRONY = "Korki"


def adresy(nazwa: str, rodzina: int) -> set[str]:
    try:
        wyniki = socket.getaddrinfo(nazwa, 443, rodzina, socket.SOCK_STREAM)
    except socket.gaierror:
        return set()
    return {w[4][0] for w in wyniki}


def normalizuj_ipv6(adr: set[str]) -> set[str]:
    """Zapis IPv6 bywa rozny (2606:50c0:8000:0::153), wiec porownujemy binarnie."""
    znormalizowane = set()
    for a in adr:
        try:
            znormalizowane.add(socket.inet_ntop(socket.AF_INET6, socket.inet_pton(socket.AF_INET6, a)))
        except OSError:
            znormalizowane.add(a)
    return znormalizowane


def pobierz(url: str) -> tuple[int | str, str]:
    zadanie = urllib.request.Request(url, headers={"User-Agent": "srem-korki-sprawdzenie"})
    try:
        with urllib.request.urlopen(zadanie, timeout=15) as odp:
            tresc = odp.read(4000).decode("utf-8", errors="replace")
            return odp.status, tresc
    except urllib.error.HTTPError as blad:
        return blad.code, ""
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as blad:
        return f"blad: {blad}", ""


def zbadaj(nazwa: str, oczekuj_github: bool) -> dict[str, object]:
    a = adresy(nazwa, socket.AF_INET)
    aaaa = normalizuj_ipv6(adresy(nazwa, socket.AF_INET6))
    return {
        "a": a,
        "aaaa": aaaa,
        "a_zgodne": a == ADRESY_A,
        "a_czesciowe": bool(a & ADRESY_A) and a != ADRESY_A,
        "aaaa_zgodne": aaaa == normalizuj_ipv6(ADRESY_AAAA),
        "wskazuje_github": bool(a & ADRESY_A) or bool(aaaa & normalizuj_ipv6(ADRESY_AAAA)),
        "oczekuj_github": oczekuj_github,
    }


def opis(nazwa: str, wynik: dict[str, object]) -> list[str]:
    linie = [f"--- {nazwa} ---"]
    a = sorted(wynik["a"])  # type: ignore[arg-type]
    aaaa = sorted(wynik["aaaa"])  # type: ignore[arg-type]
    linie.append(f"  A    : {', '.join(a) if a else 'brak'}")
    linie.append(f"  AAAA : {', '.join(aaaa) if aaaa else 'brak'}")

    if wynik["a_zgodne"]:
        linie.append("  ocena A    : OK, wszystkie cztery adresy GitHub Pages")
    elif wynik["a_czesciowe"]:
        brak = sorted(ADRESY_A - set(wynik["a"]))  # type: ignore[arg-type]
        obce = sorted(set(wynik["a"]) - ADRESY_A)  # type: ignore[arg-type]
        linie.append(f"  ocena A    : NIEPELNE - brakuje {', '.join(brak) or 'nic'}")
        if obce:
            linie.append(f"               obce adresy do usuniecia: {', '.join(obce)}")
    elif a:
        linie.append("  ocena A    : adresy nie naleza do GitHub Pages")
    else:
        linie.append("  ocena A    : brak rekordu (albo DNS jeszcze sie nie rozpropagowal)")

    if aaaa:
        linie.append("  ocena AAAA : " + ("OK" if wynik["aaaa_zgodne"] else "niezgodne z lista GitHuba"))
    else:
        linie.append("  ocena AAAA : brak (dopuszczalne, IPv6 jest opcjonalne)")
    return linie


def main() -> int:
    if len(sys.argv) != 2:
        print("Uzycie: python scripts/sprawdz_domene.py <domena>")
        return 2
    domena = sys.argv[1].strip().lower().removeprefix("http://").removeprefix("https://").rstrip("/")
    if domena.startswith("www."):
        domena = domena[4:]

    print(f"Sprawdzanie domeny: {domena}\n")

    kontrola = zbadaj(KONTROLA, oczekuj_github=True)
    if not kontrola["wskazuje_github"]:
        print("KONTROLA POZYTYWNA ZAWIODLA.")
        print(f"  {KONTROLA} nie rozwiazuje sie na adresy GitHub Pages, wiec wynik dla")
        print("  Twojej domeny nic nie znaczy. Sprawdz polaczenie sieciowe lub DNS.")
        for linia in opis(KONTROLA, kontrola):
            print(linia)
        return 1
    print(f"Kontrola pozytywna: {KONTROLA} wskazuje na GitHub Pages - metoda dziala.\n")

    apex = zbadaj(domena, oczekuj_github=True)
    for linia in opis(domena, apex):
        print(linia)

    www = zbadaj(f"www.{domena}", oczekuj_github=True)
    print()
    print(f"--- www.{domena} ---")
    if www["wskazuje_github"]:
        print("  OK: rozwiazuje sie na GitHub Pages (rekord CNAME dziala)")
    elif www["a"] or www["aaaa"]:
        print("  UWAGA: rozwiazuje sie, ale nie na GitHub Pages")
    else:
        print("  brak wpisu (dodaj CNAME www -> llyen.github.io)")

    print()
    print("--- HTTPS ---")
    for adres in (f"https://{domena}/", f"https://www.{domena}/"):
        status, tresc = pobierz(adres)
        if status == 200 and TYTUL_STRONY in tresc:
            print(f"  {adres} -> HTTP 200, strona serwisu")
        elif status == 200:
            print(f"  {adres} -> HTTP 200, ale tresc nie wyglada na nasza strone")
        else:
            print(f"  {adres} -> {status}")

    gotowe = bool(apex["a_zgodne"]) and bool(www["wskazuje_github"])
    print()
    print("WYNIK: konfiguracja kompletna." if gotowe else "WYNIK: konfiguracja jeszcze niekompletna.")
    if not gotowe:
        print("Zmiany w DNS potrafia propagowac sie do 24 godzin - jesli rekordy sa juz")
        print("wpisane w panelu, po prostu powtorz sprawdzenie pozniej.")
    return 0 if gotowe else 1


if __name__ == "__main__":
    raise SystemExit(main())
