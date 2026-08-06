/*
 * Railing Generator - parametric railing and infill-pattern engine
 * Copyright (C) 2026 Gleinkaa
 *
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or (at your
 * option) any later version. It is distributed WITHOUT ANY WARRANTY; without
 * even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE. See the GNU Affero General Public License for more details.
 *
 * A commercial licence without the copyleft obligation is available:
 * see COMMERCIAL-LICENSE.md.
 */

// UI-Verdrahtung: Regler -> Modell -> Viewer/BOM, plus Export-Funktionen.
import { buildModel, DEFAULT_PARAMS } from './model.js';
import { CATALOG } from './catalog.js';
import { Viewer } from './viewer.js';
import { DESIGNS, FAMILIES } from './patterns.js';

const params = { ...DEFAULT_PARAMS };
const viewer = new Viewer(document.getElementById('viewport'));
let model = null;

// ---- Steuerelement-Schema ---------------------------------------------------
const profOpts = (role) => CATALOG[role].map((p, i) => [i, p.name]);

const SECTIONS = [
  {
    title: 'Geometrie', open: true, items: [
      { k: 'lauflaenge', t: 'range', label: 'Lauflänge', min: 600, max: 10000, step: 50, unit: 'mm' },
      { k: 'steigung', t: 'range', label: 'Steigung gesamt', min: 0, max: 5000, step: 50, unit: 'mm' },
      { k: 'gelaenderhoehe', t: 'range', label: 'Geländerhöhe', min: 850, max: 1300, step: 10, unit: 'mm' },
      { k: 'untergurtAbstand', t: 'range', label: 'Untergurt-Abstand', min: 40, max: 150, step: 5, unit: 'mm' },
      { k: 'fuellstabAbstand', t: 'range', label: 'Füllstab-Abstand (Achse)', min: 60, max: 160, step: 1, unit: 'mm' },
      { k: 'zeigeTreppe', t: 'check', label: 'Treppe anzeigen' },
    ],
  },
  {
    title: 'Muster', open: true, items: [
      // Der Musterindex 0–33 IST der Vertrag der Engine: dieselbe Nummer waehlt
      // in der Grasshopper-Definition dasselbe Muster. Die Reihenfolge im
      // Auswahlfeld folgt deshalb dem Index, nicht dem Alphabet.
      { k: 'muster', t: 'pattern', label: 'Muster' },
      { k: 'musterDichte', t: 'range', label: 'Muster-Dichte (Rapport-Faktor)', min: 0.4, max: 3, step: 0.05, unit: '×' },
      // Nur die fuenf Zufallsmuster lesen den Seed; bei allen anderen aendert er
      // nichts, deshalb wird der Regler dort ausgeblendet.
      { k: 'musterSeed', t: 'seed', label: 'Muster-Seed', showIf: (p) => !!DESIGNS[p.muster]?.zufall },
    ],
  },
  {
    title: 'Profile', open: false, items: [
      { k: 'handlaufProfil', t: 'select', label: 'Handlauf-Profil', opts: profOpts('handrail') },
      { k: 'untergurtProfil', t: 'select', label: 'Untergurt-Profil', opts: profOpts('untergurt') },
      { k: 'postenProfil', t: 'select', label: 'Posten-Profil', opts: profOpts('post') },
      // Kanal `a` der Muster-Engine — der Grundstab jedes Musters.
      { k: 'fuellstabProfil', t: 'select', label: 'Füllstab-Profil (Kanal a)', opts: profOpts('infill') },
      // Kanal `b` — Diagonalen, Riegel, Zweitstäbe. Nicht jedes Muster nutzt ihn.
      { k: 'diagonalProfil', t: 'select', label: 'Zweitprofil (Kanal b)', opts: profOpts('infill') },
    ],
  },
  {
    title: 'Montage', open: false, items: [
      {
        k: 'montageTyp', t: 'select', label: 'Montage-Typ', opts: [
          [0, 'Seitlich / Fascia (Ankerplatte an der Stirnseite)'],
          [1, 'Aufgesetzt / Top (Fußplatte, 4 Bolzen)'],
        ],
      },
      {
        k: 'anzahlPfosten', t: 'select', label: 'Anzahl Montagepunkte (Pfosten)', opts: [
          [0, 'Automatisch (Teilung ≤ 1200 mm)'],
          ...Array.from({ length: 11 }, (_, i) => [i + 2, `${i + 2} Pfosten`]),
        ],
      },
      { k: 'pfostenMittig', t: 'check', label: 'Pfosten immer in Stufenmitte' },
      { k: 'platteBreite', t: 'range', label: 'Platte Breite', min: 80, max: 150, step: 5, unit: 'mm', showIf: (p) => p.montageTyp === 0 },
      { k: 'platteHoehe', t: 'range', label: 'Platte Höhe', min: 160, max: 260, step: 5, unit: 'mm', showIf: (p) => p.montageTyp === 0 },
      { k: 'platteBreiteTop', t: 'range', label: 'Fußplatte Breite', min: 100, max: 140, step: 5, unit: 'mm', showIf: (p) => p.montageTyp === 1 },
      { k: 'platteTiefe', t: 'range', label: 'Fußplatte Tiefe', min: 100, max: 140, step: 5, unit: 'mm', showIf: (p) => p.montageTyp === 1 },
      { k: 'platteDicke', t: 'range', label: 'Platte Dicke', min: 8, max: 12, step: 1, unit: 'mm' },
      { k: 'bolzenLaenge', t: 'range', label: 'Bolzen Länge', min: 60, max: 160, step: 5, unit: 'mm' },
    ],
  },
];

// ---- Steuerelemente bauen -----------------------------------------------------
const controlsEl = document.getElementById('controls');
const widgets = []; // {item, wrap, refresh}

function makeControl(item) {
  const wrap = document.createElement('div');
  wrap.className = 'ctl';
  let refresh = () => {};
  if (item.t === 'range') {
    const label = document.createElement('label');
    const out = document.createElement('output');
    label.append(item.label, out);
    const input = document.createElement('input');
    Object.assign(input, { type: 'range', min: item.min, max: item.max, step: item.step });
    input.value = params[item.k];
    input.addEventListener('input', () => {
      params[item.k] = Number(input.value);
      out.value = `${input.value} ${item.unit}`;
      update();
    });
    refresh = () => { input.value = params[item.k]; out.value = `${params[item.k]} ${item.unit}`; };
    wrap.append(label, input);
  } else if (item.t === 'select') {
    const label = document.createElement('label');
    label.textContent = item.label;
    const sel = document.createElement('select');
    for (const [v, txt] of item.opts) {
      const o = document.createElement('option');
      o.value = v; o.textContent = txt;
      sel.append(o);
    }
    sel.value = params[item.k];
    sel.addEventListener('change', () => { params[item.k] = Number(sel.value); update(); });
    refresh = () => { sel.value = params[item.k]; };
    wrap.append(label, sel);
  } else if (item.t === 'pattern') {
    // Musterauswahl: nach Familie gruppiert, aber INNERHALB der Familie nach
    // Index sortiert — die Nummer im Text ist der Wert, mit dem dasselbe Muster
    // in der Grasshopper-Definition am Regler steht. Wer sie umsortiert, bricht
    // die Vergleichbarkeit beider Engines.
    const label = document.createElement('label');
    label.textContent = item.label;
    const sel = document.createElement('select');
    for (const fam of FAMILIES) {
      const grp = document.createElement('optgroup');
      grp.label = fam;
      DESIGNS.forEach((d, i) => {
        if (d.fam !== fam) return;
        const o = document.createElement('option');
        o.value = i;
        o.textContent = `${String(i).padStart(2, '0')} — ${d.name}`;
        grp.append(o);
      });
      sel.append(grp);
    }
    const info = document.createElement('div');
    info.className = 'patinfo';
    const describe = () => {
      const d = DESIGNS[params[item.k]];
      if (!d) { info.textContent = ''; return; }
      const bits = [`<div class="patdesc">${d.description}</div>`];
      if (d.sonder) bits.push(`<div class="patmeta">Sondermaterial: ${d.sonder}</div>`);
      if (d.zufall) bits.push('<div class="patmeta">Zufallsmuster — der Seed ändert die Geometrie.</div>');
      // `norm` ist eine TEXTBEWERTUNG aus der Engine, kein gerechnetes Urteil.
      // Deshalb steht sie hier als Hinweis und nicht bei den Warnungen.
      if (d.norm) bits.push(`<div class="patnorm">${d.norm}</div>`);
      // `status` markiert eine offene KONSTRUKTIONSfrage (Schweissfolge, Holzdicke
      // …), nicht einen Normverstoss — der Unterschied gehoert in die Anzeige.
      if (d.status && d.status !== 'done') {
        bits.push(`<div class="patopen">Offene Fertigungsentscheidung (${d.status}) — Detail ist mit dem ausführenden Betrieb zu klären.</div>`);
      }
      info.innerHTML = bits.join('');
    };
    sel.value = params[item.k];
    sel.addEventListener('change', () => {
      params[item.k] = Number(sel.value);
      describe();
      update();
    });
    refresh = () => { sel.value = params[item.k]; describe(); };
    describe();
    wrap.append(label, sel, info);
  } else if (item.t === 'check') {
    const label = document.createElement('label');
    label.className = 'chk';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = params[item.k];
    input.addEventListener('change', () => { params[item.k] = input.checked; update(); });
    label.append(input, item.label);
    refresh = () => { input.checked = params[item.k]; };
    wrap.append(label);
  } else if (item.t === 'seed') {
    const label = document.createElement('label');
    label.textContent = item.label;
    const row = document.createElement('div');
    row.className = 'seedrow';
    const input = document.createElement('input');
    Object.assign(input, { type: 'number', min: 0, step: 1 });
    input.value = params[item.k];
    input.addEventListener('change', () => { params[item.k] = Number(input.value) || 0; update(); });
    const btn = document.createElement('button');
    btn.textContent = '🎲 mischen';
    btn.addEventListener('click', () => {
      params[item.k] = Math.floor(Math.random() * 100000);
      input.value = params[item.k];
      update();
    });
    row.append(input, btn);
    refresh = () => { input.value = params[item.k]; };
    wrap.append(label, row);
  }
  widgets.push({ item, wrap, refresh });
  return wrap;
}

for (const sec of SECTIONS) {
  const det = document.createElement('details');
  det.className = 'box';
  det.open = sec.open;
  const sum = document.createElement('summary');
  sum.textContent = sec.title;
  det.append(sum);
  for (const item of sec.items) det.append(makeControl(item));
  controlsEl.append(det);
}

// ---- BOM / Warnungen ------------------------------------------------------------
const fmt = (x) => x.toLocaleString('de-AT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function renderBom(m) {
  const t = document.getElementById('bom');
  const rows = m.bom.rows
    .map((r) => `<tr><td>${r.pos}</td><td class="cnt">${r.count || ''}</td><td>${fmt(r.kg)} kg</td></tr>`)
    .join('');
  // Stueckzahl: Summe ueber ALLE Zaehler des Modells statt einer fixen Liste.
  // Die Muster-Engine bringt je nach Muster eigene Kanaele mit (Bleche, Holz),
  // eine fest verdrahtete Addition haette sie stillschweigend unterschlagen.
  // +2 = Handlauf und Untergurt, die keinen eigenen Zaehler haben.
  const stk = Object.values(m.counts).reduce((s, v) => s + (Number(v) || 0), 0) + 2;
  t.innerHTML =
    `<tr><th>Position</th><th class="cnt">Stk.</th><th>Masse</th></tr>${rows}` +
    `<tr class="total"><td>GESAMT</td><td class="cnt">${stk}</td><td>${fmt(m.bom.total)} kg</td></tr>`;
  document.getElementById('warnings').innerHTML =
    m.warnings.map((w) => `<div class="warn">⚠ ${w}</div>`).join('');
  document.getElementById('notes').innerHTML =
    m.notes.map((n) => `<div class="note">${n}</div>`).join('');
}

// ---- Update-Schleife --------------------------------------------------------------
let framed = false;
function update() {
  model = buildModel(params);
  viewer.update(model);
  renderBom(model);
  for (const { item, wrap } of widgets) {
    wrap.style.display = item.showIf && !item.showIf(params) ? 'none' : '';
  }
  if (!framed) { viewer.frame(model); framed = true; }
}
update();

// ---- Export -----------------------------------------------------------------------
function download(name, data, mime) {
  const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

// Dateiname aus Index + Musterschluessel: die Nummer macht den Export einer
// Grasshopper-Reglerstellung zuordenbar, der Schluessel macht ihn lesbar.
const baseName = () => {
  const i = params.muster;
  const d = DESIGNS[i];
  return `railing_${String(i).padStart(2, '0')}_${d ? d.key : 'unknown'}`;
};
const withStairs = () => document.getElementById('exp-stairs').checked;

document.getElementById('exp-obj').addEventListener('click', () => {
  download(`${baseName()}.obj`, viewer.exportOBJ(withStairs()), 'model/obj');
});
document.getElementById('exp-stl').addEventListener('click', () => {
  download(`${baseName()}.stl`, new Blob([viewer.exportSTL(withStairs())]), 'model/stl');
});
document.getElementById('exp-csv').addEventListener('click', () => {
  const sep = ';';
  const lines = [['Position', 'Stueck', 'Laenge_mm', 'Masse_kg'].join(sep)];
  for (const r of model.bom.rows) {
    lines.push([r.pos, r.count, r.lenMm == null ? '' : r.lenMm.toFixed(0), r.kg.toFixed(2)].join(sep));
  }
  lines.push(['GESAMT', '', '', model.bom.total.toFixed(2)].join(sep));
  download(`${baseName()}_BOM.csv`, '\uFEFF' + lines.join('\r\n'), 'text/csv;charset=utf-8');
});
document.getElementById('exp-json').addEventListener('click', () => {
  const data = { generator: 'StiegengelaenderGeneratorWeb', version: 1, params, bom: model.bom, counts: model.counts };
  download(`${baseName()}_Konfiguration.json`, JSON.stringify(data, null, 2), 'application/json');
});
document.getElementById('exp-png').addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = viewer.screenshotPNG();
  a.download = `${baseName()}.png`;
  a.click();
});
document.getElementById('imp-json').addEventListener('change', async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    const src = data.params ?? data;
    for (const k of Object.keys(DEFAULT_PARAMS)) {
      if (k in src && typeof src[k] === typeof DEFAULT_PARAMS[k]) params[k] = src[k];
    }
    for (const { refresh } of widgets) refresh();
    framed = false;
    update();
  } catch {
    alert('Konfigurationsdatei konnte nicht gelesen werden.');
  }
  ev.target.value = '';
});
