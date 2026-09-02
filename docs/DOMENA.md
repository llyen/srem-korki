# Podpięcie własnej domeny (korkisrem.pl)

Strona działa pod adresem `https://llyen.github.io/srem-korki/`. Własna domena
skraca go do `https://korkisrem.pl` — łatwiej podać ją sąsiadowi przez telefon
i lepiej wygląda w lokalnych grupach.

**Czego nie zmienia:** hosting nadal jest bezpłatny (GitHub Pages), pomiary
działają tak samo. Jedynym nowym kosztem jest sama domena, odnawiana co roku.

---

## Zanim kupisz

Domena `korkisrem.pl` **była wolna** przy sprawdzeniu 2 września 2026
(zapytanie do rejestru NASK, `whois.dns.pl`). Sprawdź ponownie przed zakupem —
to stan na jeden dzień.

Na co patrzeć przy wyborze rejestratora:

- **Cena odnowienia, nie pierwszego roku.** Promocje na pierwszy rok bywają
  kilkukrotnie tańsze niż kolejne lata. To koszt powtarzalny.
- **DNS w cenie.** Potrzebujesz panelu, w którym samodzielnie dodasz rekordy
  `A`, `AAAA` i `CNAME`. Większość rejestratorów daje to bezpłatnie.
- **Domena wygasła = strona znika.** Włącz automatyczne odnawianie i pilnuj
  adresu e-mail przypisanego do domeny.

Wybór rejestratora nie ma tu znaczenia technicznego — GitHub Pages wymaga
zwykłych rekordów `A`, które obsługuje każdy panel DNS.

---

## Kolejność kroków ma znaczenie

> Dokumentacja GitHuba ostrzega wprost: **najpierw dodaj domenę w ustawieniach
> repozytorium, dopiero potem skonfiguruj DNS.** Odwrotna kolejność pozwala
> komuś obcemu opublikować własną stronę pod Twoim adresem, zanim zdążysz go
> zająć.

Źródło: [Managing a custom domain for your GitHub Pages site](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)

---

## Krok 1. Dodanie domeny w GitHubie

1. `github.com/llyen/srem-korki` → **Settings** → **Pages**
2. Pole **Custom domain** → wpisz `korkisrem.pl` → **Save**

GitHub utworzy w repozytorium plik `CNAME` z tą nazwą. To normalne — nie
usuwaj go. Do czasu skonfigurowania DNS strona pod nową domeną jeszcze nie
zadziała.

Warto też wykonać **weryfikację domeny** (Settings → Pages → *Verify domain*).
Dodaje ona jeden rekord `TXT` i blokuje możliwość przejęcia adresu przez inne
konto GitHuba.

## Krok 2. Rekordy w panelu DNS

### Gdzie to jest w AZ.pl

Panel Klienta → **Domeny** → kliknij `korkisrem.pl` → **Zarządzaj rekordami
DNS** (bywa też jako *Skonfiguruj DNS hostingu*).

**Warunek wstępny:** domena musi być delegowana na serwery DNS AZ.pl
(`ns6.az.pl`, `ns7.az.pl`, `ns8.az.pl`). Bez tego panel nie pozwoli edytować
strefy — rekordy trzeba by wtedy wpisywać u operatora, na którego wskazuje
delegacja. Hosting w AZ.pl **nie jest** do tego potrzebny.

Źródło: [pomoc.az.pl — modyfikacja rekordów domeny](https://pomoc.az.pl/kategorie/jak-przejsc-do-modyfikacji-rekordow-domeny/)

### Rekordy do wpisania

Dla adresu głównego (`korkisrem.pl`) — cztery rekordy `A`:

| Typ | Nazwa / host | Wartość |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |

Opcjonalnie IPv6 — cztery rekordy `AAAA`:

| Typ | Nazwa / host | Wartość |
|---|---|---|
| AAAA | `@` | `2606:50c0:8000::153` |
| AAAA | `@` | `2606:50c0:8001::153` |
| AAAA | `@` | `2606:50c0:8002::153` |
| AAAA | `@` | `2606:50c0:8003::153` |

Dla `www` — jeden rekord `CNAME`:

| Typ | Nazwa / host | Wartość |
|---|---|---|
| CNAME | `www` | `llyen.github.io.` |

Uwagi:

- Zapis `@` oznacza domenę główną; część paneli wymaga wpisania pełnej nazwy
  albo pozostawienia pola pustego.
- Jeśli rejestrator dodał własny rekord domyślny (np. stronę parkingową),
  **usuń go** — inaczej ruch pójdzie w dwa miejsca naraz.
- W wartości `CNAME` kropka na końcu bywa wymagana. Jeśli panel jej nie
  przyjmuje, wpisz bez kropki.
- Adresy IP pochodzą z dokumentacji GitHuba (stan na 2 września 2026)
  i zostały potwierdzone praktycznie — `llyen.github.io` rozwiązuje się
  dokładnie na te cztery adresy.

## Krok 3. Sprawdzenie

```powershell
python scripts/sprawdz_domene.py korkisrem.pl
```

Skrypt sprawdza rekordy `A`, `AAAA`, wpis `www` oraz to, czy strona odpowiada
po HTTPS. Zaczyna od **kontroli pozytywnej** na `llyen.github.io`: jeśli ona
zawiedzie, problem leży w połączeniu lub DNS-ie komputera, a nie w konfiguracji
domeny — i wynik dla `korkisrem.pl` nic by nie znaczył.

**Zmiany w DNS propagują się do 24 godzin.** Wynik „konfiguracja jeszcze
niekompletna” zaraz po wpisaniu rekordów nie oznacza błędu.

## Krok 4. HTTPS

Gdy DNS zacznie działać, GitHub wystawi certyfikat (Let's Encrypt) — trwa to
od kilku minut do godziny. Następnie w **Settings → Pages** zaznacz
**Enforce HTTPS**.

Opcja bywa nieaktywna, dopóki certyfikat nie zostanie wystawiony. To nie błąd,
tylko kolejność.

---

## Co się zmieni po podpięciu

- `https://llyen.github.io/srem-korki/` zacznie **przekierowywać** na nową
  domenę — stare linki nie przestaną działać.
- Ścieżki w kodzie są względne, więc nic nie wymaga poprawek.
- Drugie źródło danych (`raw.githubusercontent.com`) działa niezależnie od
  domeny i pozostaje bez zmian.
- Licznik odwiedzin w Cloudflare Web Analytics zacznie zbierać ruch pod nową
  nazwą; dane sprzed zmiany zostają przy starym adresie.

## Warto zrobić po zmianie

Dodać do `index.html` znaczniki z pełnym adresem — bez nich udostępnienie
linku na Facebooku pokazuje uboższy podgląd:

```html
<link rel="canonical" href="https://korkisrem.pl/">
<meta property="og:url" content="https://korkisrem.pl/">
```

Nie dodano ich wcześniej celowo: wpisanie adresu, który jeszcze nie istnieje,
byłoby deklaracją niezgodną ze stanem faktycznym.
