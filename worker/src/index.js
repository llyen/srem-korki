/**
 * Zewnętrzny wyzwalacz pomiarów dla srem-korki.
 *
 * Po co to istnieje
 * -----------------
 * Workflow `update-traffic.yml` miał własny harmonogram (`on: schedule`), ale
 * GitHub nie uruchomił go ani razu: 0 przebiegów z harmonogramu przy 39
 * uruchomieniach ręcznych, wszystkich zakończonych powodzeniem. Konfiguracja
 * była poprawna (gałąź domyślna, Actions włączone, repozytorium publiczne,
 * składnia zweryfikowana parserem YAML), więc przyczyna leży po stronie
 * platformy i nie dało się jej usunąć z naszej strony.
 *
 * Harmonogram Cloudflare zawiódł tak samo: wyrażenia cron są zapisane i widać
 * je w panelu, ale Worker nie budzi się ani razu (test z 1 września 2026 -
 * cron "* * * * *", 5 kolejnych terminów bez jednego zapytania do API
 * GitHuba, przy działającej kontroli pozytywnej).
 *
 * Dlatego rolę zegara pełni usługa zewnętrzna, która wywołuje adres tego
 * Workera z parametrem `?wyzwol=<klucz>`, a Worker zamawia pomiar przez
 * `workflow_dispatch`. To ten sam kanał, który działa bezawaryjnie przy
 * uruchomieniach ręcznych.
 *
 * Token GitHuba zostaje po stronie Cloudflare - zewnętrzny zegar zna wyłącznie
 * adres i klucz wyzwalacza, które można unieważnić bez ruszania tokenu.
 *
 * Zamierzony harmonogram jest opisany w `wrangler.toml`.
 */

const REPOZYTORIUM = "llyen/srem-korki";
const PLIK_WORKFLOW = "update-traffic.yml";
const GALAZ = "main";

// GitHub odrzuca żądania bez nagłówka User-Agent.
const UZYTKOWNIK = "srem-korki-cron";

const PROBY = 2;
const ODSTEP_MS = 3000;

/**
 * Wysyła jedno żądanie workflow_dispatch.
 * Zwraca obiekt z wynikiem zamiast rzucać wyjątkiem, żeby log był czytelny.
 */
async function wyslijZadanie(token) {
  const adres =
    `https://api.github.com/repos/${REPOZYTORIUM}` +
    `/actions/workflows/${PLIK_WORKFLOW}/dispatches`;

  const odpowiedz = await fetch(adres, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": UZYTKOWNIK,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: GALAZ }),
  });

  // Powodzenie to 204 No Content - GitHub nie zwraca treści.
  if (odpowiedz.status === 204) {
    return { ok: true, status: 204 };
  }

  let tresc = "";
  try {
    tresc = (await odpowiedz.text()).slice(0, 300);
  } catch (blad) {
    tresc = `(nie udało się odczytać treści: ${blad})`;
  }
  return { ok: false, status: odpowiedz.status, tresc };
}

/**
 * Porownuje ciagi w czasie niezaleznym od liczby zgodnych znakow.
 * Zwykle === konczy porownanie na pierwszej roznicy, co przy publicznym
 * adresie pozwalaloby odgadywac klucz znak po znaku.
 */
function rowneStaloczasowo(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) {
    return false;
  }
  let roznica = 0;
  for (let i = 0; i < a.length; i += 1) {
    roznica |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return roznica === 0;
}

/**
 * Zamawia pomiar przez workflow_dispatch.
 * Zwraca true, jesli GitHub przyjal zadanie - endpoint HTTP musi odroznic
 * powodzenie od porazki, zeby zewnetrzny zegar mogl zglosic blad.
 */
async function wyzwolPomiar(env, wyrazenieCron) {
  const token = env.GITHUB_TOKEN;
  if (!token) {
    console.error(
      "Brak sekretu GITHUB_TOKEN. Ustaw go poleceniem: npx wrangler secret put GITHUB_TOKEN"
    );
    return false;
  }

  for (let proba = 1; proba <= PROBY; proba += 1) {
    const wynik = await wyslijZadanie(token);

    if (wynik.ok) {
      console.log(
        `Pomiar wyzwolony (cron: ${wyrazenieCron}, próba ${proba}/${PROBY}).`
      );
      return true;
    }

    console.error(
      `Nieudane wyzwolenie (cron: ${wyrazenieCron}, próba ${proba}/${PROBY}): ` +
        `HTTP ${wynik.status} ${wynik.tresc}`
    );

    // 401, 403 i 404 to błędy tokenu albo uprawnień - ponowienie nic nie zmieni.
    // (404 przy poprawnym adresie zwykle oznacza token bez dostępu do repo.)
    if (wynik.status === 401 || wynik.status === 403 || wynik.status === 404) {
      return false;
    }

    if (proba < PROBY) {
      await new Promise((gotowe) => setTimeout(gotowe, ODSTEP_MS));
    }
  }

  return false;
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(wyzwolPomiar(env, controller.cron));
  },

  /**
   * Worker jest wystawiony pod adresem *.workers.dev z dwóch powodów: bez tego
   * wdrożenie kończy się komunikatem "No targets deployed", a od czasu, gdy
   * harmonogram Cloudflare przestał budzić Workera, to właśnie ten adres jest
   * kanałem, którym zewnętrzny zegar (cron-job.org) zamawia pomiar.
   *
   * Obsługiwane są trzy przypadki:
   *   ?diag=1            - sprawdza dostęp do API GitHuba, wykonuje sam odczyt
   *   ?wyzwol=<klucz>    - zamawia pomiar; wymaga sekretu KLUCZ_WYZWALACZA
   *   pozostałe          - krótka informacja, bez żadnych skutków
   *
   * Wyzwalanie jest chronione kluczem, bo adres jest publiczny, a każdy pomiar
   * zużywa 8 zapytań do TomTom z ograniczonej puli miesięcznej.
   */
  async fetch(request, env) {
    const adres = new URL(request.url);

    const podanyKlucz = adres.searchParams.get("wyzwol");
    if (podanyKlucz !== null) {
      const oczekiwany = env.KLUCZ_WYZWALACZA;
      if (!oczekiwany) {
        return new Response("Brak sekretu KLUCZ_WYZWALACZA w Workerze.\n", { status: 500 });
      }
      if (!rowneStaloczasowo(podanyKlucz, oczekiwany)) {
        // Ten sam komunikat co przy braku klucza - nie podpowiadamy, czy klucz
        // byl bliski prawdziwego.
        return new Response("Brak dostepu.\n", { status: 403 });
      }

      const wynik = await wyzwolPomiar(env, "zegar zewnetrzny");
      return Response.json(
        { zamowiono_pomiar: wynik !== false },
        { status: wynik === false ? 502 : 202 }
      );
    }

    if (adres.searchParams.get("diag") === "1") {
      const token = env.GITHUB_TOKEN;
      const raport = {
        sekret_widoczny: Boolean(token),
        dlugosc_sekretu: token ? token.length : 0,
      };

      if (token) {
        try {
          const odpowiedz = await fetch(
            `https://api.github.com/repos/${REPOZYTORIUM}/actions/workflows/${PLIK_WORKFLOW}`,
            {
              headers: {
                Accept: "application/vnd.github+json",
                Authorization: `Bearer ${token}`,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": UZYTKOWNIK,
              },
            }
          );
          raport.odczyt_workflow_http = odpowiedz.status;
          raport.limit_pozostalo = odpowiedz.headers.get("x-ratelimit-remaining");
        } catch (blad) {
          raport.odczyt_workflow_http = `wyjatek: ${blad}`;
        }
      }

      return Response.json(raport);
    }

    return new Response(
      "Wyzwalacz pomiarów dla https://llyen.github.io/srem-korki/\n" +
        "Pomiar zamawia wyłącznie żądanie z poprawnym kluczem. Bez niego\n" +
        "ten adres nic nie uruchamia.\n",
      { headers: { "Content-Type": "text/plain; charset=utf-8" } }
    );
  },
};
