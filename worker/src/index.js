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
 * Ten Worker zastępuje tamten harmonogram: o wyznaczonych porach wywołuje
 * `workflow_dispatch` przez API GitHuba. To ten sam kanał, który działa
 * bezawaryjnie przy uruchomieniach ręcznych.
 *
 * Harmonogram jest zapisany w `wrangler.toml` i odwzorowuje dokładnie ten,
 * który wcześniej stał w pliku workflow.
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

async function wyzwolPomiar(env, wyrazenieCron) {
  const token = env.GITHUB_TOKEN;
  if (!token) {
    console.error(
      "Brak sekretu GITHUB_TOKEN. Ustaw go poleceniem: npx wrangler secret put GITHUB_TOKEN"
    );
    return;
  }

  for (let proba = 1; proba <= PROBY; proba += 1) {
    const wynik = await wyslijZadanie(token);

    if (wynik.ok) {
      console.log(
        `Pomiar wyzwolony (cron: ${wyrazenieCron}, próba ${proba}/${PROBY}).`
      );
      return;
    }

    console.error(
      `Nieudane wyzwolenie (cron: ${wyrazenieCron}, próba ${proba}/${PROBY}): ` +
        `HTTP ${wynik.status} ${wynik.tresc}`
    );

    // 401, 403 i 404 to błędy tokenu albo uprawnień - ponowienie nic nie zmieni.
    // (404 przy poprawnym adresie zwykle oznacza token bez dostępu do repo.)
    if (wynik.status === 401 || wynik.status === 403 || wynik.status === 404) {
      return;
    }

    if (proba < PROBY) {
      await new Promise((gotowe) => setTimeout(gotowe, ODSTEP_MS));
    }
  }
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(wyzwolPomiar(env, controller.cron));
  },

  /**
   * Worker nie musi mieć publicznego adresu, ale jeśli ktoś na niego trafi,
   * niech dostanie zrozumiałą odpowiedź. Ten kanał świadomie NIE wyzwala
   * pomiaru - inaczej dowolna osoba mogłaby wyczerpać limit zapytań TomTom.
   */
  async fetch() {
    return new Response(
      "Wyzwalacz pomiarów dla https://llyen.github.io/srem-korki/\n" +
        "Działa wyłącznie według harmonogramu. Ten adres nic nie uruchamia.\n",
      { headers: { "Content-Type": "text/plain; charset=utf-8" } }
    );
  },
};
