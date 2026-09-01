# Wyzwalacz pomiarów (Cloudflare Worker)

Ten katalog zawiera mały program, który o wyznaczonych porach każe GitHubowi
wykonać pomiar czasów przejazdu. Sam nie odpytuje TomTomu i nie przetwarza
danych — jedynie naciska przycisk, który wcześniej trzeba było naciskać ręcznie.

## Dlaczego to w ogóle powstało

Workflow `update-traffic.yml` miał własny harmonogram (`on: schedule`).
GitHub nie uruchomił go **ani razu**: 0 przebiegów z harmonogramu przy 39
uruchomieniach ręcznych, wszystkich zakończonych powodzeniem.

Sprawdzone i wykluczone jako przyczyna:

| Co sprawdzono | Wynik |
|---|---|
| Gałąź domyślna | `main`, zgodna z lokalizacją pliku workflow |
| Struktura `on: schedule` | poprawna, zweryfikowana parserem YAML |
| Uprawnienia Actions | `enabled: true`, `allowed_actions: all` |
| Stan workflow | `state: active` |
| Repozytorium | publiczne, nie fork, nie zarchiwizowane |
| Czas od ostatniej edycji pliku | ponad godzina — okno rejestracji harmonogramu minęło |

Przyczyna pozostaje nieznana i leży poza naszym zasięgiem. Kanał
`workflow_dispatch` działa natomiast bezawaryjnie — i to jego używa ten Worker.

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

Token użyty przy pierwszym wdrożeniu (1 września 2026) jest ważny **8 dni**.
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
npx wrangler secret put GITHUB_TOKEN   # wklej token z kroku 1
```

Sekret trafia do Cloudflare i **nie jest zapisany w tym repozytorium**.
Po jego ustawieniu nie trzeba wdrażać ponownie.

#### Pułapka: subdomena workers.dev

Cloudflare odmówi zapisania cron triggerów, dopóki konto nie ma subdomeny
`workers.dev` — nawet gdy Worker jej nie używa (`workers_dev = false`):

> You need a workers.dev subdomain in order to proceed. Please go to the
> dashboard and open the Workers menu. `[code: 10063]`

Wystarczy raz otworzyć w panelu **Workers & Pages**; subdomena tworzy się
wtedy automatycznie. Potem `wrangler deploy` przechodzi.

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

### 3. Sprawdzenie, czy działa

Najprostszy test — wymuszenie przebiegu bez czekania na porę pomiaru:

```powershell
npx wrangler tail
```

i w drugim oknie:

```powershell
gh run list --repo llyen/srem-korki --limit 5
```

Po najbliższej porze z harmonogramu w `wrangler tail` powinien pojawić się
wpis `Pomiar wyzwolony`, a na liście przebiegów — nowe uruchomienie.

Można też sprawdzić lokalnie, jeszcze przed wdrożeniem:

```powershell
npx wrangler dev --test-scheduled
```

a następnie w drugim oknie wywołać `http://localhost:8787/__scheduled`.
Uwaga: ten tryb naprawdę wyśle żądanie do GitHuba, więc uruchomi pomiar.

## Harmonogram

Pory pomiarów są w `wrangler.toml`. Cloudflare uruchamia crony w czasie UTC,
dokładnie tak samo jak robił to GitHub, więc godziny pozostały bez zmian:

| Okno (UTC) | Częstotliwość | Czas lokalny latem |
|---|---|---|
| 04:00–07:59 | co 10 minut | 06:00–09:59 |
| 08:00–11:59 | co 30 minut | 10:00–13:59 |
| 12:00–15:59 | co 10 minut | 14:00–17:59 |
| 16:00–17:59 | co 30 minut | 18:00–19:59 |
| 18:00–03:59 | brak pomiarów | 20:00–05:59 |

Razem 60 przebiegów na dobę × 8 tras = **480 zapytań dziennie**.
W najdłuższym miesiącu 14 880 z budżetu 18 500 (80%).

Darmowy plan Workers dopuszcza **5 cron triggerów na konto** — zużywamy 2.
Źródło: <https://developers.cloudflare.com/workers/platform/limits/>

## Ważne: dlaczego workflow nie ma już `schedule`

Bloki `on: schedule` zostały z `update-traffic.yml` usunięte. Gdyby harmonogram
GitHuba kiedyś ożył równolegle z tym Workerem, pomiary wykonywałyby się
podwójnie: 960 zapytań dziennie zamiast 480, czyli wyczerpanie miesięcznego
limitu TomTom około 19 dnia miesiąca. Jeden wyzwalacz, jedno źródło prawdy.

Jeśli kiedykolwiek zrezygnujesz z Workera, przywróć `schedule` w workflow —
wyrażenia cron są tam zapisane w komentarzu.

## Zmiana harmonogramu

Po edycji `crons` w `wrangler.toml` trzeba wdrożyć ponownie:

```powershell
npx wrangler deploy
```

Cloudflare zapowiada, że zmiany harmonogramu propagują się **do 15 minut**.
Źródło: <https://developers.cloudflare.com/workers/configuration/cron-triggers/>

Pamiętaj o przeliczeniu budżetu — pomaga w tym `scripts/policz_budzet.py`.
