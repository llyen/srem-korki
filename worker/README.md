# Wyzwalacz pomiarów (Cloudflare Worker)

Ten katalog zawiera mały program, który na sygnał z zewnętrznego zegara każe
GitHubowi wykonać pomiar czasów przejazdu. Sam nie odpytuje TomTomu i nie
przetwarza danych — jedynie naciska przycisk, który wcześniej trzeba było
naciskać ręcznie.

**Worker nie jest zegarem.** Zegar stoi w serwisie cron-job.org i wywołuje
adres Workera z parametrem `?wyzwol=<klucz>`. Powód opisuje sekcja
„Dlaczego zegar jest na zewnątrz”. Konfigurację zegara tworzy skrypt
`scripts/konfiguruj_zegar.py` w katalogu głównym projektu.

Taki podział ma konkretną zaletę: **token GitHuba nie opuszcza Cloudflare**.
Usługa zewnętrzna zna wyłącznie adres i klucz wyzwalacza, a oba można
unieważnić w minutę bez ruszania tokenu.

## Dlaczego zegar jest na zewnątrz

Harmonogram próbowano trzymać kolejno w dwóch miejscach. Obie platformy
przyjęły konfigurację i nie uruchomiły zadania ani razu.

**GitHub Actions (`on: schedule`)** — 0 przebiegów z harmonogramu przy 39
uruchomieniach ręcznych, wszystkich zakończonych powodzeniem.

| Co sprawdzono | Wynik |
|---|---|
| Gałąź domyślna | `main`, zgodna z lokalizacją pliku workflow |
| Struktura `on: schedule` | poprawna, zweryfikowana parserem YAML |
| Uprawnienia Actions | `enabled: true`, `allowed_actions: all` |
| Stan workflow | `state: active` |
| Repozytorium | publiczne, nie fork, nie zarchiwizowane |
| Czas od ostatniej edycji pliku | ponad godzina — okno rejestracji harmonogramu minęło |

**Cloudflare Cron Triggers** — to samo, mimo poprawnie zapisanych cronów
widocznych w panelu i w API. Rozstrzygnął test niezależny od telemetrii
Cloudflare (której nie dało się zaufać — GraphQL zwracał zero wywołań w okresie,
gdy Worker na pewno został wywołany): cron ustawiony na każdą minutę wykonywał
odczyt z API GitHuba, obniżający licznik `x-ratelimit-remaining`. Przez pięć
kolejnych terminów licznik nie drgnął, przy działającej kontroli pozytywnej.

Pełny zapis obu diagnoz jest w `docs/METODYKA.md`, sekcja 3c.

Kanał `workflow_dispatch` działa natomiast bezawaryjnie — i to jego używa
ten Worker.

## Co trzeba zrobić raz

### 1. Token GitHuba

Wejdź na <https://github.com/settings/personal-access-tokens/new> i utwórz
token o dostępie ograniczonym do jednego repozytorium:

- **Resource owner:** `llyen`
- **Repository access:** *Only select repositories* → `llyen/srem-korki`
- **Repository permissions** → **Actions: Read and write**
  (GitHub sam dołoży wymagane *Metadata: Read-only* — tak ma być)
- **Expiration:** wybierz świadomie. Po wygaśnięciu pomiary przestaną się
  uruchamiać, a Worker zapisze w logu `HTTP 401`.

Nie nadawaj innych uprawnień. Token nie może zapisywać kodu ani czytać
prywatnych repozytoriów — ma tylko uruchamiać ten jeden workflow.

Skopiuj wartość tokenu, bo GitHub pokaże ją tylko raz.

#### Ważność tokenu — trzeba pilnować

Token używany produkcyjnie jest ważny **do 30 lipca 2027**. Datę można
sprawdzić w każdej chwili, bez zaglądania do sekretu — zwraca ją diagnostyka
Workera w polu `token_wygasa`:

```powershell
Invoke-RestMethod 'https://srem-korki-cron.jakub-461.workers.dev/?diag=1'
```

Po wygaśnięciu Worker zacznie dostawać `HTTP 401`, pomiary się zatrzymają,
a strona pokaże ostatni udany odczyt wraz z jego wiekiem — nic nie zawiadomi
o tym samo z siebie.

Odnowienie to wygenerowanie nowego tokenu i jedno polecenie:

```powershell
npx wrangler secret put GITHUB_TOKEN
```

Ponowne wdrożenie nie jest potrzebne. Trwałą alternatywą, która nie wymaga
rotacji, jest **GitHub App** — jej klucz prywatny nie wygasa, a Worker wymienia
go na krótkotrwały token instalacyjny przy każdym wywołaniu. Wymaga to około
50 dodatkowych linii kodu (podpis JWT przez WebCrypto) i jednorazowej
konfiguracji aplikacji. Nie zostało to wdrożone.

### 2. Wdrożenie Workera

W tym katalogu (`worker/`):

```powershell
npm install
npx wrangler login      # otworzy przeglądarkę, zatwierdź dostęp
npx wrangler deploy
npx wrangler secret put GITHUB_TOKEN        # wklej token z kroku 1
npx wrangler secret put KLUCZ_WYZWALACZA    # patrz krok 3
```

Sekrety trafiają do Cloudflare i **nie są zapisane w tym repozytorium**.
Po ich ustawieniu nie trzeba wdrażać ponownie.

### 3. Klucz wyzwalacza

Adres Workera jest publiczny, więc endpoint zamawiający pomiar musi być
chroniony — każde wywołanie kosztuje 8 zapytań z ograniczonej puli TomTom.
Klucz jest porównywany stałoczasowo, żeby po publicznym adresie nie dało się
go odgadywać znak po znaku.

Wygenerowanie i zapisanie:

```powershell
$bajty = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bajty)
$klucz = [Convert]::ToBase64String($bajty).Replace('+','-').Replace('/','_').TrimEnd('=')
[IO.File]::WriteAllText(".klucz-wyzwalacza.txt", $klucz)
$klucz | npx wrangler secret put KLUCZ_WYZWALACZA
```

Plik `.klucz-wyzwalacza.txt` jest w `.gitignore` i służy skryptowi
`scripts/konfiguruj_zegar.py` do zbudowania adresu dla zegara. Nie wypisuj
klucza na ekran ani do rozmowy — trzymaj go w pliku.

Unieważnienie klucza to wygenerowanie nowego i ponowne uruchomienie
`scripts/konfiguruj_zegar.py`. Token GitHuba pozostaje wtedy nietknięty.

#### Pułapka: subdomena workers.dev

Cloudflare odmówi zapisania cron triggerów, dopóki konto nie ma subdomeny
`workers.dev` — nawet gdy Worker jej nie używa (`workers_dev = false`):

> You need a workers.dev subdomain in order to proceed. Please go to the
> dashboard and open the Workers menu. `[code: 10063]`

Wystarczy raz otworzyć w panelu **Workers & Pages**; subdomena tworzy się
wtedy automatycznie. Potem `wrangler deploy` przechodzi.

W tym projekcie subdomena jest zresztą konieczna z innego powodu: to właśnie
pod tym adresem Worker przyjmuje sygnał zegara.

#### Pułapka: Windows na ARM64

Na tej stacji roboczej (`win32 arm64`) zwykłe `npm install` **przerywa się
błędem**, bo Cloudflare nie publikuje binarki `workerd` dla tej architektury:

```
notsup Unsupported platform for @cloudflare/workerd-windows-64:
wanted {"os":"win32","cpu":"x64"} (current: {"os":"win32","cpu":"arm64"})
```

Obejście — wymuszenie wersji x64, którą Windows uruchamia przez emulację,
oraz doinstalowanie natywnej binarki esbuild:

```powershell
npm install --ignore-scripts --no-audit --no-fund
npm install @cloudflare/workerd-windows-64 --cpu=x64 --os=win32 --force
npm install "@esbuild/win32-arm64@$((Get-Content node_modules\esbuild\package.json -Raw | ConvertFrom-Json).version)" --force
```

Sprawdzone — po tych trzech poleceniach działa i `wrangler deploy --dry-run`,
i lokalny `wrangler dev`. Na maszynie x64 nie jest to potrzebne.

### 4. Sprawdzenie, czy działa

Worker ma endpoint diagnostyczny, który **nie uruchamia pomiaru** — sprawdza
tylko, czy widzi sekret i czy dociera do API GitHuba:

```powershell
Invoke-RestMethod "https://srem-korki-cron.jakub-461.workers.dev/?diag=1"
```

Oczekiwana odpowiedź: `sekret_widoczny: True`, `odczyt_workflow_http: 200`.

Pełny test łańcucha (uruchomi prawdziwy pomiar i zużyje 8 zapytań TomTom):

```powershell
$klucz = (Get-Content .klucz-wyzwalacza.txt -Raw).Trim()
Invoke-WebRequest "https://srem-korki-cron.jakub-461.workers.dev/?wyzwol=$klucz"
gh run list --repo llyen/srem-korki --limit 3
```

Oczekiwane: `HTTP 202` z treścią `{"zamowiono_pomiar":true}`, a na liście
przebiegów nowe uruchomienie `workflow_dispatch` sprzed kilkunastu sekund.

Podgląd logów Workera na żywo:

```powershell
npx wrangler tail
```

## Harmonogram

**Pory pomiarów nie są ustawiane tutaj.** Definiuje je
`scripts/konfiguruj_zegar.py`, a wykonuje cron-job.org — w strefie
`Europe/Warsaw`, więc bez przesunięcia przy zmianie czasu na zimowy:

| Okno (czas lokalny) | Częstotliwość |
|---|---|
| 06:00–09:59 | co 10 minut |
| 10:00–13:59 | co 30 minut |
| 14:00–17:59 | co 10 minut |
| 18:00–19:59 | co 30 minut |
| 20:00–05:59 | brak pomiarów |

Razem 60 przebiegów na dobę × 8 tras = **480 zapytań dziennie**.
W najdłuższym miesiącu 14 880 z budżetu 18 500 (80%). Liczby przelicza
`python scripts/policz_budzet.py` — nie przepisuj ich z pamięci.

Tablica `crons` w `wrangler.toml` jest **nieczynna** i została wyłącznie jako
zapis zamierzonych pór. Gdyby harmonogram Cloudflare kiedyś ożył, pomiary
wykonywałyby się podwójnie — przy zmianach pór trzeba pamiętać o obu miejscach.

## Ważne: dlaczego workflow nie ma już `schedule`

Bloki `on: schedule` zostały z `update-traffic.yml` usunięte. Gdyby harmonogram
GitHuba kiedyś ożył równolegle z zewnętrznym zegarem, pomiary wykonywałyby się
podwójnie: 960 zapytań dziennie zamiast 480, czyli wyczerpanie miesięcznego
limitu TomTom około 19 dnia miesiąca. Jeden wyzwalacz, jedno źródło prawdy.

Jeśli kiedykolwiek zrezygnujesz z tego rozwiązania, przywróć `schedule`
w workflow — wyrażenia cron są tam zapisane w komentarzu.

## Zmiana harmonogramu

Pory pomiarów zmienia się w `scripts/konfiguruj_zegar.py` (listy `godziny`
i `minuty`), a potem uruchamia skrypt ponownie — zaktualizuje istniejące
zadania zamiast tworzyć nowe:

```powershell
$env:CRONJOB_API_KEY = "<klucz API z cron-job.org>"
python scripts/konfiguruj_zegar.py
```

Ponowne wdrażanie Workera **nie jest** wtedy potrzebne — Worker nie zna pór.

Pamiętaj o przeliczeniu budżetu: `python scripts/policz_budzet.py`. Skrypt
czyta ten sam plik, więc liczby w dokumentacji nie rozjadą się z konfiguracją.
