'use strict';

const ODSWIEZANIE_MS = 120 * 1000;
// Odswiezenie licznika wieku danych bez ponownego pobierania.
const ODSWIEZANIE_WIEKU_MS = 20 * 1000;

// Poza szczytem pomiar wykonywany jest co 30 min, a CDN trzyma plik do 10 min,
// wiec dane starsze niz ~40 min sa tam normalne. Ostrzegamy dopiero powyzej.
// Wieczorem i noca (po ok. 20:00 czasu lokalnego) pomiarow nie ma wcale, wiec
// ostrzezenie bedzie wtedy widoczne stale - i tak ma byc, bo liczba jest wtedy
// faktycznie nieaktualna.
const PROG_NIEAKTUALNE_MIN = 50;

// Dwa zrodla tych samych danych. GitHub Pages serwuje je z naglowkiem
// max-age=600 i ignoruje parametr query w kluczu cache, wiec potrafi oddac plik
// starszy o 10 minut. raw.githubusercontent.com ma max-age=300. Pobieramy oba
// i pokazujemy nowszy - jesli jedno zrodlo zawiedzie, zostaje drugie.
const ZRODLA = [
  'data/current.json',
  'https://raw.githubusercontent.com/llyen/srem-korki/main/data/current.json'
];

const ETYKIETY = {
  plynnie: 'płynnie',
  umiarkowanie: 'lekko wolniej',
  utrudnienia: 'utrudnienia',
  korek: 'korek'
};

let profil = null;
let trasyMeta = [];
let ostatnieDane = null;

function minuty(sekundy) {
  return Math.max(0, Math.round(sekundy / 60));
}

function odmianaMinut(n) {
  if (n === 1) return 'minuta';
  const dziesiatki = n % 100;
  const jednosci = n % 10;
  if (jednosci >= 2 && jednosci <= 4 && !(dziesiatki >= 12 && dziesiatki <= 14)) return 'minuty';
  return 'minut';
}

// Kolor slupka na wykresie profilu godzinowego. Uzywa wylacznie bezwzglednego
// opoznienia, bo profil agreguje mediany z wielu pomiarow i nie przechowuje
// czasu przejazdu przy pustej drodze, wiec proporcji nie da sie odtworzyc.
// Progi sa te same, co kolumna "Opoznienie" w progach z config.json, a bramka
// minimalnej straty (2,5 i 5 min) nie zmienia tu wyniku: kazde opoznienie
// przekraczajace 8 minut i tak ja spelnia.
function poziomZOpoznienia(opoznienieMin) {
  if (opoznienieMin <= 3) return 'plynnie';
  if (opoznienieMin <= 8) return 'umiarkowanie';
  if (opoznienieMin <= 15) return 'utrudnienia';
  return 'korek';
}

function formatCzasu(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
}

function renderKarty(dane) {
  const kontener = document.getElementById('karty');
  kontener.innerHTML = '';

  dane.trasy.forEach(function (t) {
    const opozn = minuty(t.opoznienie_s);
    const czas = minuty(t.czas_s);
    const km = (t.dlugosc_m / 1000).toFixed(1).replace('.', ',');
    const karta = document.createElement('article');
    karta.className = 'karta ' + t.poziom;

    karta.innerHTML =
      '<div class="karta-tytul"><h3></h3><span class="droga"></span></div>' +
      '<div class="wiersz-czasu">' +
        '<span class="czas"></span><span class="jednostka"></span>' +
        '<span class="etykieta ' + t.poziom + '"></span>' +
      '</div>' +
      '<p class="szczegoly"></p>' +
      '<details class="wiecej"><summary>szczegóły</summary>' +
        '<p class="odcinek"></p><p class="opis"></p><p class="uwaga" hidden></p>' +
      '</details>';

    karta.querySelector('h3').textContent = t.nazwa;
    karta.querySelector('.droga').textContent = t.droga;
    karta.querySelector('.czas').textContent = String(czas);
    karta.querySelector('.jednostka').textContent = odmianaMinut(czas);
    karta.querySelector('.etykieta').textContent = ETYKIETY[t.poziom] || t.poziom;

    karta.querySelector('.szczegoly').textContent =
      (opozn > 0 ? '+' + opozn + ' min' : 'bez opóźnienia') + ' · ' + km + ' km';

    const odcinek = karta.querySelector('.odcinek');
    if (t.skad && t.dokad) {
      odcinek.textContent = t.skad + ' → ' + t.dokad + ', ' + km + ' km';
    } else {
      odcinek.hidden = true;
    }

    karta.querySelector('.opis').textContent =
      t.opis + (opozn > 0
        ? ' Teraz o ' + opozn + ' ' + odmianaMinut(opozn) + ' dłużej niż przy pustej drodze.'
        : ' Teraz bez opóźnienia względem pustej drogi.');

    if (t.uwaga) {
      const uwaga = karta.querySelector('.uwaga');
      uwaga.hidden = false;
      uwaga.textContent = t.uwaga;
    }

    kontener.appendChild(karta);
  });

  (dane.bledy || []).forEach(function (b) {
    const karta = document.createElement('article');
    karta.className = 'karta bledna';
    karta.innerHTML = '<h3></h3><p class="opis">Brak pomiaru w tym cyklu.</p>';
    karta.querySelector('h3').textContent = b.nazwa;
    kontener.appendChild(karta);
  });
}

function renderAktualizacja() {
  if (!ostatnieDane) return;
  const el = document.getElementById('aktualizacja');
  const wiekMin = Math.floor((Date.now() - new Date(ostatnieDane.pobrano_utc).getTime()) / 60000);

  let wiek;
  if (wiekMin < 1) {
    wiek = 'przed chwilą';
  } else {
    wiek = wiekMin + ' ' + odmianaMinut(wiekMin) + ' temu';
  }

  el.hidden = false;
  el.textContent = 'Pomiar o ' + formatCzasu(ostatnieDane.pobrano_utc) + ' — ' + wiek;

  const ostrz = document.getElementById('stan-nieaktualne');
  if (wiekMin > PROG_NIEAKTUALNE_MIN) {
    ostrz.hidden = false;
    ostrz.textContent =
      'Uwaga: ostatni udany pomiar był ' + wiekMin + ' min temu. Dane mogą nie odpowiadać sytuacji na drodze.';
  } else {
    ostrz.hidden = true;
  }
}

async function pobierzNajswiezsze() {
  const proby = ZRODLA.map(function (url) {
    return fetch(url + '?t=' + Date.now(), { cache: 'no-store' }).then(function (odp) {
      if (!odp.ok) throw new Error('HTTP ' + odp.status);
      return odp.json();
    });
  });

  const wyniki = await Promise.allSettled(proby);
  const udane = wyniki
    .filter(function (w) { return w.status === 'fulfilled' && w.value && w.value.pobrano_utc; })
    .map(function (w) { return w.value; });

  if (!udane.length) {
    const powod = wyniki
      .map(function (w) { return w.reason ? w.reason.message : '?'; })
      .join(', ');
    throw new Error(powod);
  }

  udane.sort(function (a, b) {
    return new Date(b.pobrano_utc) - new Date(a.pobrano_utc);
  });
  return udane[0];
}

function wypelnijWyborTrasy() {
  const sel = document.getElementById('wybor-trasy');
  sel.innerHTML = '';
  trasyMeta.forEach(function (t) {
    const o = document.createElement('option');
    o.value = t.id;
    o.textContent = t.nazwa;
    sel.appendChild(o);
  });
}

function renderProfil() {
  const sekcja = document.getElementById('sekcja-profil');
  const wykres = document.getElementById('wykres');
  const brak = document.getElementById('profil-brak');

  if (!profil || !profil.profil) { sekcja.hidden = true; return; }

  const trasa = document.getElementById('wybor-trasy').value;
  const dzien = document.getElementById('wybor-dnia').value;
  const dane = profil.profil[trasa] || {};

  const godziny = [];
  for (let g = 5; g <= 22; g++) {
    const wpis = dane[dzien + '-' + g];
    godziny.push({ g: g, wpis: wpis || null });
  }

  const maks = Math.max.apply(null, godziny.map(function (x) {
    return x.wpis ? x.wpis.mediana_opoznienia_s : 0;
  }).concat([300]));

  const maPomiary = godziny.some(function (x) { return x.wpis; });
  sekcja.hidden = false;
  brak.hidden = maPomiary;
  wykres.hidden = !maPomiary;
  wykres.innerHTML = '';

  godziny.forEach(function (x) {
    const kol = document.createElement('div');
    kol.className = 'slupek';
    const opoznMin = x.wpis ? minuty(x.wpis.mediana_opoznienia_s) : null;
    const wys = x.wpis ? Math.max(2, Math.round((x.wpis.mediana_opoznienia_s / maks) * 110)) : 0;
    const poziom = opoznMin === null ? '' : poziomZOpoznienia(opoznMin);

    const pasek = document.createElement('div');
    pasek.className = 'pasek ' + poziom;
    pasek.style.height = wys + 'px';
    if (x.wpis) {
      pasek.title = 'godz. ' + x.g + ':00 — mediana +' + opoznMin + ' min (' + x.wpis.probek + ' pomiarów)';
    }

    const wart = document.createElement('div');
    wart.className = 'wart';
    wart.textContent = opoznMin === null ? '–' : '+' + opoznMin;

    const godz = document.createElement('div');
    godz.className = 'godz';
    godz.textContent = x.g;

    kol.appendChild(pasek);
    kol.appendChild(wart);
    kol.appendChild(godz);
    wykres.appendChild(kol);
  });
}

async function wczytaj() {
  const ladowanie = document.getElementById('stan-ladowania');
  const blad = document.getElementById('stan-bledu');
  try {
    const dane = await pobierzNajswiezsze();
    ostatnieDane = dane;

    trasyMeta = dane.trasy.map(function (t) { return { id: t.id, nazwa: t.nazwa }; });
    renderKarty(dane);
    renderAktualizacja();
    ladowanie.hidden = true;

    if (String(dane.zrodlo || '').indexOf('PRZYKŁADOWE') !== -1) {
      blad.hidden = false;
      blad.textContent =
        'To są dane przykładowe wygenerowane lokalnie, a nie pomiar rzeczywistego ruchu. Nie planuj na ich podstawie podróży.';
    } else {
      blad.hidden = true;
    }

    const sel = document.getElementById('wybor-trasy');
    const poprzednia = sel.value;
    wypelnijWyborTrasy();
    if (poprzednia) sel.value = poprzednia;
    renderProfil();
  } catch (e) {
    ladowanie.hidden = true;
    if (!ostatnieDane) {
      blad.hidden = false;
      blad.textContent =
        'Nie udało się pobrać danych (' + e.message + '). Spróbuj odświeżyć stronę za chwilę.';
    }
  }
}

async function wczytajProfil() {
  try {
    const odp = await fetch('data/profile.json?t=' + Date.now(), { cache: 'no-store' });
    if (!odp.ok) return;
    profil = await odp.json();
    renderProfil();
  } catch (e) {
    /* profil jest opcjonalny - brak historii nie jest bledem */
  }
}

function start() {
  const dzis = new Date().getDay();
  document.getElementById('wybor-dnia').value = String(dzis);
  document.getElementById('wybor-trasy').addEventListener('change', renderProfil);
  document.getElementById('wybor-dnia').addEventListener('change', renderProfil);

  wczytaj();
  wczytajProfil();
  setInterval(wczytaj, ODSWIEZANIE_MS);
  setInterval(renderAktualizacja, ODSWIEZANIE_WIEKU_MS);

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) wczytaj();
  });
}

document.addEventListener('DOMContentLoaded', start);
