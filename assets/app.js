'use strict';

const ODSWIEZANIE_MS = 90 * 1000;
const PROG_NIEAKTUALNE_MIN = 35;

const ETYKIETY = {
  plynnie: 'płynnie',
  umiarkowanie: 'lekko wolniej',
  utrudnienia: 'utrudnienia',
  korek: 'korek'
};

let profil = null;
let trasyMeta = [];

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
    const karta = document.createElement('article');
    karta.className = 'karta ' + t.poziom;

    const dodatek = opozn > 0
      ? 'o ' + opozn + ' ' + odmianaMinut(opozn) + ' dłużej niż przy pustej drodze'
      : 'bez opóźnienia względem pustej drogi';

    karta.innerHTML =
      '<div class="droga"></div>' +
      '<h3></h3>' +
      '<div class="wiersz-czasu">' +
        '<span class="czas"></span><span class="jednostka"></span>' +
        '<span class="etykieta ' + t.poziom + '"></span>' +
      '</div>' +
      '<p class="szczegoly"></p>' +
      '<p class="opis"></p>';

    karta.querySelector('.droga').textContent = t.droga;
    karta.querySelector('h3').textContent = t.nazwa;
    karta.querySelector('.czas').textContent = String(czas);
    karta.querySelector('.jednostka').textContent = odmianaMinut(czas);
    karta.querySelector('.etykieta').textContent = ETYKIETY[t.poziom] || t.poziom;
    karta.querySelector('.szczegoly').textContent =
      dodatek + ' · ' + (t.dlugosc_m / 1000).toFixed(1).replace('.', ',') + ' km';
    karta.querySelector('.opis').textContent = t.opis;

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

function renderAktualizacja(dane) {
  const el = document.getElementById('aktualizacja');
  el.hidden = false;
  el.textContent = 'Ostatni pomiar: ' + formatCzasu(dane.pobrano_utc);

  const wiekMin = (Date.now() - new Date(dane.pobrano_utc).getTime()) / 60000;
  const ostrz = document.getElementById('stan-nieaktualne');
  if (wiekMin > PROG_NIEAKTUALNE_MIN) {
    ostrz.hidden = false;
    ostrz.textContent =
      'Uwaga: dane mają ' + Math.round(wiekMin) + ' min i mogą nie odpowiadać sytuacji na drodze.';
  } else {
    ostrz.hidden = true;
  }
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
    const odp = await fetch('data/current.json?t=' + Date.now(), { cache: 'no-store' });
    if (!odp.ok) throw new Error('HTTP ' + odp.status);
    const dane = await odp.json();

    trasyMeta = dane.trasy.map(function (t) { return { id: t.id, nazwa: t.nazwa }; });
    renderKarty(dane);
    renderAktualizacja(dane);
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
    blad.hidden = false;
    blad.textContent =
      'Nie udało się pobrać aktualnych danych (' + e.message + '). Spróbuj odświeżyć stronę za chwilę.';
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

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) wczytaj();
  });
}

document.addEventListener('DOMContentLoaded', start);
