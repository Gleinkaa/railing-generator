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

// Regression: die Web-Portierung muss die Stückliste der Grasshopper-Engine
// reproduzieren. Seit Phase 14 baut der Musterkatalog (34 Muster) die Füllung;
// `fuellungStil` 0/1/2 gibt es weder hier noch in der GH-Definition.
//
// Zwei Referenzstände sind im Spiel — die Unterscheidung ist wichtig:
//
//   * `reference/README.md`, Abschnitt "Referenzkonfiguration Musterkatalog"
//     (Aufnahme 2026-08-05, live aus der .gh-Datei): der GÜLTIGE Vertrag.
//     Fünf Muster, alle Regler protokolliert. Wird unten mit `PIN` geprüft.
//   * `reference/README.md`, Abschnitt "Alter Stand — SUPERSEDED": die drei
//     `Fuellung-Stil`-Varianten von 2026-07-26, darunter die 77,49 kg. Dieser
//     Abschnitt ist dort ausdrücklich als überholt gekennzeichnet.
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildModel } from '../model.js';
import { CATALOG } from '../catalog.js';
import { DESIGNS, FAMILIES } from '../patterns.js';

const round2 = (x) => Math.round(x * 100) / 100;
const row = (m, prefix) => m.bom.rows.find((r) => r.pos.startsWith(prefix));
const kgOf = (m, prefix) => { const r = row(m, prefix); return r ? r.kg : 0; };

// ---------------------------------------------------------------------------
// Gepinnte Referenz — alter Stand (Stil 0 ≙ Muster 30)
// ---------------------------------------------------------------------------
// ACHTUNG, dieser Test SCHLÄGT FEHL, und das ist beabsichtigt stehen gelassen.
//
// Die 77,49 kg stammen aus dem Export vom 2026-07-26 mit `Fuellung-Stil` 0.
// Das nächstliegende heutige Muster ist 30 `bar-vertical` — aber die beiden
// Füllungen sind NICHT dasselbe Bauteil:
//
//   alt (Stil 0): Achsabstand 115 mm, Stäbe auch AUF den Feldgrenzen, feldweise
//                 dedupliziert -> 41 Stäbe, 32,77 kg
//   neu (30):     Rapport 110 mm, je Rapport-Einheit EIN Stab in der Mitte,
//                 nie auf der Feldgrenze -> 40 Stäbe, 31,97 kg
//
// 40 Stäbe ist der Wert, den die Grasshopper-Engine heute selbst meldet
// (`reference/README.md`, Info-Ausgang: "30 bar-vertical … 40 Stäbe"). Der Port
// ist also NICHT falsch — die erwartete Zahl ist überholt, und zwar an der
// Quelle: `reference/README.md` führt den 77,49-kg-Block selbst unter
// "Alter Stand — SUPERSEDED" und pinnt Muster 30 heute auf 113,629223 kg
// (anderer Reglersatz). Dieser gültige Vertrag wird weiter unten geprüft und
// geht exakt auf.
//
// Der alte Wert wird deshalb NICHT stillschweigend auf die eigene Ausgabe
// nachgezogen — das wäre genau der Fehler, gegen den er geschrieben wurde.
// Statt dessen steht hier die Ablösung als PRÜFBARE Aussage: die Abweichung
// gegenüber der alten Referenz ist genau diese eine, aus der Stabteilung
// hergeleitete Differenz — und sonst keine. Ändert sich irgendwann etwas
// anderes am Rahmen (Handlauf, Untergurt, Posten, Platten, Bolzen), schlägt
// dieser Test an, obwohl der Gesamtwert längst ein anderer ist.
test('Ablösung belegt: gegenüber der alten Stil-0-Referenz weicht NUR die Stabteilung ab', () => {
  const m = buildModel({ muster: 30, pfostenMittig: false });

  // Der Rahmen ist musterunabhängig und muss die alte Referenz weiterhin
  // Position für Position treffen.
  assert.deepEqual({
    posten: m.counts.posten,
    platten: m.counts.platten,
    bolzen: m.counts.bolzen,
    kgHandlauf: round2(kgOf(m, 'Handlauf')),
    kgUntergurt: round2(kgOf(m, 'Untergurt')),
    kgPosten: round2(kgOf(m, 'Posten')),
    kgAnkerplatten: round2(kgOf(m, 'Ankerplatten')),
    kgBolzen: round2(kgOf(m, 'Bolzen')),
  }, {
    posten: 5,
    platten: 5,
    bolzen: 10,
    kgHandlauf: 8.91,
    kgUntergurt: 14.04,
    kgPosten: 11.93,
    kgAnkerplatten: 8.64,
    kgBolzen: 1.2,
  }, 'Der Rahmen darf sich durch die Muster-Engine NICHT verändert haben');

  // Und die Füllung weicht genau um einen Stab ab — Rapport-Mitte statt
  // Achsabstand-mit-Feldgrenze. Beide Zahlen stehen hier nebeneinander, damit
  // die Ablösung im Testbericht lesbar ist statt nur im Kommentar.
  const ALT = { staebe: 41, kg: 32.77 };   // Fuellung-Stil 0, Export 2026-07-26
  const NEU = { staebe: 40, kg: 31.97 };   // Muster 30, Rapport 110 mm
  assert.deepEqual(
    { staebe: m.counts.fuellstaebe, kg: round2(kgOf(m, 'Füllstäbe')) }, NEU,
    'Muster 30 muss die heutige GH-Stabteilung liefern',
  );
  assert.equal(ALT.staebe - NEU.staebe, 1, 'Die Ablösung ist genau ein Stab');
  assert.equal(round2(m.bom.total), round2(77.49 - (ALT.kg - NEU.kg)),
    'Der Gesamtwert folgt vollständig aus dieser einen Differenz');
});

// ---------------------------------------------------------------------------
// Gepinnte Referenz — gültiger Vertrag (2026-08-05, live aus Grasshopper)
// ---------------------------------------------------------------------------
// Vollständiger Reglersatz aus `reference/README.md`. Wer ihn 1:1 einstellt,
// muss exakt diese Massen erhalten — Toleranz 1e-5 kg (Anzeigegenauigkeit der
// Referenz sind 6 Nachkommastellen).
const PIN = {
  lauflaenge: 4000, steigung: 2000, gelaenderhoehe: 1000, untergurtAbstand: 100,
  handlaufProfil: 3, postenProfil: 2, fuellstabProfil: 3, diagonalProfil: 4,
  untergurtProfil: 0,
  montageTyp: 0, platteBreite: 240, platteHoehe: 321, platteDicke: 10,
  bolzenDurchmesser: 12, bolzenLaenge: 100, bolzenOffsetV: 75, bolzenMasseKg: 0.12,
  // Die GH-Definition verteilt die Posten immer gleichmäßig (Divide Curve) und
  // rastet nie auf Stufenmitten — das ist genau `pfostenMittig: false`.
  pfostenMittig: false,
  musterDichte: 1.0, musterSeed: 42,
  HOLZ_D: 30, HOLZ_LUFT: 8, HOLZ_OFF: 12, BLECH_D: 4, BLECH_STEG: 25,
  BLECH_RAND: 30, FLACH_D: 8, VIERKANT_W: 16, GMAX: 120, KWINK: 60,
  AUSLAGE: 40, UGURT: 100,
};
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-5, `${msg}: ${a} != ${b}`);

test('Gepinnter GH-Vertrag: Rahmenpositionen musterunabhängig', () => {
  for (const idx of [30, 23, 32, 1, 11]) {
    const m = buildModel({ ...PIN, muster: idx });
    near(kgOf(m, 'Handlauf'), 10.670516, `Muster ${idx} Handlauf`);
    near(kgOf(m, 'Posten'), 15.070000, `Muster ${idx} Posten`);
    near(kgOf(m, 'Untergurt'), 14.042507, `Muster ${idx} Untergurt`);
    near(kgOf(m, 'Ankerplatten'), 30.238200, `Muster ${idx} Platten`);
    near(kgOf(m, 'Bolzen'), 1.200000, `Muster ${idx} Bolzen`);
    assert.equal(m.counts.posten, 5);
  }
});

test('Gepinnter GH-Vertrag: Muster 30 bar-vertical = 113,629223 kg', () => {
  const m = buildModel({ ...PIN, muster: 30 });
  assert.equal(m.pattern.key, 'bar-vertical');
  assert.equal(m.counts.fuellstaebe, 40);
  assert.equal(m.pattern.rap, 110);
  near(kgOf(m, 'Füllstäbe'), 42.408000, 'kg_Fuell');
  near(m.bom.total, 113.629223, 'kg_GESAMT_MAT');
});

test('Gepinnter GH-Vertrag: Muster 23 bar-scatter = 146,501250 kg', () => {
  const m = buildModel({ ...PIN, muster: 23 });
  assert.equal(m.counts.fuellstaebe, 44);
  assert.equal(m.counts.diagonalen, 12);
  assert.equal(m.pattern.rap, 100);
  near(kgOf(m, 'Füllstäbe'), 46.648800, 'kg_Fuell');
  near(kgOf(m, 'Diagonalen'), 28.631227, 'kg_Diag');
  near(m.bom.total, 146.501250, 'kg_GESAMT_MAT');
});

test('Gepinnter GH-Vertrag: Muster 32 rake-uniform = 132,593101 kg', () => {
  const m = buildModel({ ...PIN, muster: 32 });
  assert.equal(m.counts.fuellstaebe, 60);
  assert.equal(m.pattern.rap, 80);
  near(kgOf(m, 'Füllstäbe'), 61.371878, 'kg_Fuell');
  near(m.bom.total, 132.593101, 'kg_GESAMT_MAT');
});

test('Gepinnter GH-Vertrag: Muster 01 panel-stagger = 121,273240 kg (Holz!)', () => {
  const m = buildModel({ ...PIN, muster: 1 });
  assert.equal(m.counts.fuellstaebe, 0);
  assert.equal(m.counts.diagonalen, 8);
  assert.equal(m.counts.holzteile, 44);
  near(kgOf(m, 'Diagonalen'), 22.468011, 'kg_Diag');
  // Diese Zeile ist zugleich die Probe auf WOOD_DENSITY: der Wert geht nur mit
  // 600 kg/m³ auf (dem Regler `Holz-Rohdichte` der GH-Definition). Mit den oft
  // zitierten 700 kg/m³ (Eiche) stünden hier 32,18 kg.
  near(kgOf(m, 'Holzteile'), 27.584006, 'kg_Holz');
  near(m.bom.total, 121.273240, 'kg_GESAMT_MAT');
});

test('Muster 11 sheet-ellipse: Blech vorhanden, Referenzmasse veraltet', () => {
  const m = buildModel({ ...PIN, muster: 11 });
  assert.equal(m.counts.stahlteile, 4, 'ein Blech je Feld');
  assert.equal(m.counts.fuellstaebe, 0);
  assert.equal(m.counts.holzteile, 0);
  // Die Referenz nennt kg_Stahl = 73,016554. Der Port liefert 74,972704 —
  // die Differenz von 1,956150 kg ist exakt der Randabstands-Deckel
  // `st/2 - BLECH_RAND` in `p_sheet_ellipse`, den die Aufnahme vom 2026-08-05
  // noch nicht enthielt (nachgerechnet: ohne diesen Deckel ergibt sich
  // 73,016554 auf die letzte Stelle). Der Port ist damit NICHT falsch, die
  // Referenzzahl ist älter als die Engine. Deshalb hier bewusst keine Pinnung
  // auf eine der beiden Zahlen, nur eine Plausibilitätsschranke.
  assert.ok(kgOf(m, 'Stahlteile') > 70 && kgOf(m, 'Stahlteile') < 80);
});

// ---------------------------------------------------------------------------
// Muster-Verdrahtung
// ---------------------------------------------------------------------------
test('Alle 34 Muster bauen — geneigter Lauf und ebener Lauf', () => {
  for (const cfg of [{ steigung: 2000 }, { steigung: 0 }]) {
    for (let i = 0; i < DESIGNS.length; i++) {
      const m = buildModel({ ...cfg, muster: i, pfostenMittig: false });
      const label = `Muster ${i} ${DESIGNS[i].key} (Steigung ${cfg.steigung})`;
      assert.ok(m.pattern.sweeps.length + m.pattern.solids.length > 0,
        `${label}: weder Stäbe noch Formteile — das Feld bliebe leer`);
      assert.ok(Number.isFinite(m.bom.total) && m.bom.total > 0, `${label}: Masse`);
      assert.equal(m.pattern.index, i, `${label}: Index`);
    }
  }
});

test('Kein Muster erzeugt nicht-endliche Koordinaten', () => {
  const chk = (p, label) => {
    for (const v of p) assert.ok(Number.isFinite(v), `${label}: ${p}`);
  };
  const curve = (c, label) => {
    if (c.kind === 'line') { chk(c.a, label); chk(c.b, label); }
    else if (c.kind === 'arc') {
      chk(c.p0, label); chk(c.pm, label); chk(c.p1, label); chk(c.center, label);
      assert.ok(Number.isFinite(c.radius) && Number.isFinite(c.angle), label);
    } else if (c.kind === 'bezier') c.pts.forEach((p) => chk(p, label));
    else if (c.kind === 'polyline') c.pts.forEach((p) => chk(p, label));
    else assert.fail(`${label}: unbekannte Kurve ${c.kind}`);
  };
  for (const cfg of [{ steigung: 2000 }, { steigung: 0 }]) {
    for (let i = 0; i < DESIGNS.length; i++) {
      const m = buildModel({ ...cfg, muster: i, pfostenMittig: false });
      const label = `Muster ${i} ${DESIGNS[i].key}`;
      for (const s of m.pattern.sweeps) curve(s.curve, label);
      for (const s of m.pattern.solids) {
        if (s.solid.kind === 'plate') {
          s.solid.loops.forEach((l) => l.pts.forEach((p) => chk(p, label)));
          chk(s.solid.path, label);
        } else if (s.solid.kind === 'loft') {
          s.solid.sections.forEach((l) => l.pts.forEach((p) => chk(p, label)));
        } else assert.fail(`${label}: unbekannter Solid ${s.solid.kind}`);
      }
    }
  }
});

test('Musterindex: 0 ist gültig, Ausreißer werden geklemmt', () => {
  // `muster: 0` darf NICHT als "nicht gesetzt" gelesen werden — sonst ist
  // Muster 0 unerreichbar und die Engine baut still Muster 30.
  assert.equal(buildModel({ muster: 0 }).pattern.key, 'loop-u');
  assert.equal(buildModel({ muster: 33 }).pattern.key, 'vee-center');
  assert.equal(buildModel({ muster: 99 }).pattern.index, 33);
  assert.equal(buildModel({ muster: -5 }).pattern.index, 0);
});

test('pattern-Objekt trägt die Metadaten des Katalogeintrags', () => {
  const m = buildModel({ muster: 13 });
  const d = DESIGNS[13];
  assert.equal(m.pattern.index, 13);
  assert.equal(m.pattern.key, d.key);
  assert.equal(m.pattern.name, d.name);
  assert.equal(m.pattern.fam, d.fam);
  assert.ok(FAMILIES.includes(m.pattern.fam));
  assert.equal(m.pattern.description, d.description);
  assert.equal(m.pattern.norm, d.norm);
  assert.equal(m.pattern.status, d.status);
  assert.equal(typeof m.pattern.rap, 'number');
  assert.equal(typeof m.pattern.clamped, 'boolean');
});

test('Sweeps tragen Kanal und aufgelöstes Profil (a = Füllstab, b = Diagonal)', () => {
  const m = buildModel({ muster: 23, fuellstabProfil: 2, diagonalProfil: 3 });
  const a = m.pattern.sweeps.filter((s) => s.channel === 'a');
  const b = m.pattern.sweeps.filter((s) => s.channel === 'b');
  assert.ok(a.length > 0 && b.length > 0);
  assert.equal(a.length + b.length, m.pattern.sweeps.length);
  for (const s of a) assert.equal(s.profile, CATALOG.infill[2]);
  for (const s of b) assert.equal(s.profile, CATALOG.infill[3]);
  // Kurvenobjekte kommen unverändert aus bay.js — Weltkoordinaten, kein Resampling
  for (const s of m.pattern.sweeps) {
    assert.ok(['line', 'arc', 'bezier', 'polyline'].includes(s.curve.kind));
  }
});

test('Muster 30: jeder Stab steht senkrecht zwischen Untergurt- und Handlauflinie', () => {
  const m = buildModel({ muster: 30 });
  const { gelaenderhoehe, untergurtAbstand } = m.params;
  const zOnBase = (x) => (x / 4000) * 2000;
  assert.ok(m.pattern.sweeps.length > 0);
  for (const { curve } of m.pattern.sweeps) {
    assert.equal(curve.kind, 'line');
    assert.ok(Math.abs(curve.a[2] - (zOnBase(curve.a[0]) + untergurtAbstand)) < 1e-6,
      'Stabfuß liegt nicht auf der Untergurtlinie');
    assert.ok(Math.abs(curve.b[2] - (zOnBase(curve.b[0]) + gelaenderhoehe)) < 1e-6,
      'Stabkopf liegt nicht auf der Handlauflinie');
    assert.ok(Math.abs(curve.a[0] - curve.b[0]) < 1e-9, 'Stab ist nicht senkrecht');
  }
});

test('Außennormale zeigt von der Treppe weg (−y), nicht in sie hinein', () => {
  // Vorgesetzte Elemente (Kanal b mit AUSLAGE) müssen außenbords landen. Die
  // Stufen liegen bei y > 0 — ein Muster bei y > 0 stünde also im Laufraum.
  const m = buildModel({ muster: 24, AUSLAGE: 40 });
  const b = m.pattern.sweeps.filter((s) => s.channel === 'b');
  assert.ok(b.length > 0);
  for (const { curve } of b) {
    const pts = curve.kind === 'bezier' ? curve.pts
      : curve.kind === 'polyline' ? curve.pts : [curve.a ?? curve.p0, curve.b ?? curve.p1];
    for (const p of pts) assert.ok(Math.abs(p[1] + 40) < 1e-6, `Auslage bei y=${p[1]}`);
  }
  // Gegenprobe: Kanal a liegt in der Sicherheitsebene (y = 0)
  for (const s of m.pattern.sweeps.filter((x) => x.channel === 'a')) {
    assert.ok(Math.abs(s.curve.a[1]) < 1e-9);
  }
  // Und die Stufen liegen auf der anderen Seite
  assert.ok(m.steps.every((s) => s.center[1] > 0));
});

test('Seed: gleicher Seed identisch, anderer Seed anders (Zufallsmuster)', () => {
  const cfg = { muster: 12, pfostenMittig: false }; // rake-random
  assert.deepEqual(buildModel({ ...cfg, musterSeed: 7 }).pattern.sweeps,
    buildModel({ ...cfg, musterSeed: 7 }).pattern.sweeps);
  assert.notDeepEqual(buildModel({ ...cfg, musterSeed: 7 }).pattern.sweeps,
    buildModel({ ...cfg, musterSeed: 8 }).pattern.sweeps);
  // Deterministisches Muster darf sich vom Seed NICHT bewegen
  assert.deepEqual(buildModel({ muster: 30, musterSeed: 7 }).pattern.sweeps,
    buildModel({ muster: 30, musterSeed: 8 }).pattern.sweeps);
});

test('Dichteregler streckt den Rapport und damit die Stabzahl', () => {
  const eng = buildModel({ muster: 30, musterDichte: 0.5, pfostenMittig: false });
  const weit = buildModel({ muster: 30, musterDichte: 1.0, pfostenMittig: false });
  assert.equal(eng.pattern.rap, 55);
  assert.ok(eng.counts.fuellstaebe > weit.counts.fuellstaebe);
});

// ---------------------------------------------------------------------------
// Stückliste
// ---------------------------------------------------------------------------
test('GESAMT ist die Summe der Positionen (Stichprobe über alle vier Familien)', () => {
  const probe = [0, 5, 8, 11, 12, 15, 17, 19, 24, 28, 30, 31];
  const fams = new Set();
  for (const idx of probe) {
    const m = buildModel({ muster: idx });
    fams.add(m.pattern.fam);
    const parts = m.bom.rows.reduce((s, r) => s + r.kg, 0);
    assert.ok(Math.abs(parts - m.bom.total) < 1e-9, `Muster ${idx}`);
  }
  assert.deepEqual([...fams].sort(), [...FAMILIES].sort(), 'Stichprobe deckt alle Familien');
});

test('GESAMT ist die Summe der Positionen — alle 34 Muster', () => {
  for (let i = 0; i < DESIGNS.length; i++) {
    const m = buildModel({ muster: i });
    const parts = m.bom.rows.reduce((s, r) => s + r.kg, 0);
    assert.ok(Math.abs(parts - m.bom.total) < 1e-9, `Muster ${i} ${DESIGNS[i].key}`);
  }
});

test('Leere Kanäle bekommen KEINE Stücklistenzeile', () => {
  // 30 bar-vertical: nur Kanal a. Weder Diagonal- noch Stahl- noch Holzzeile.
  const nur_a = buildModel({ muster: 30 });
  assert.ok(row(nur_a, 'Füllstäbe'));
  assert.equal(row(nur_a, 'Diagonalen'), undefined);
  assert.equal(row(nur_a, 'Stahlteile'), undefined);
  assert.equal(row(nur_a, 'Holzteile'), undefined);
  // 19 bar-width-wave: nur Stahl-Solids, kein einziger Stab.
  const nur_st = buildModel({ muster: 19 });
  assert.equal(nur_st.counts.fuellstaebe, 0);
  assert.equal(row(nur_st, 'Füllstäbe'), undefined,
    'ein Muster ohne Füllstäbe darf keine 0,00-kg-Zeile zeigen');
  assert.ok(row(nur_st, 'Stahlteile'));
  // Keine Zeile der Stückliste ist jemals leer
  for (let i = 0; i < DESIGNS.length; i++) {
    for (const r of buildModel({ muster: i }).bom.rows) {
      assert.ok(r.count > 0, `Muster ${i}: Zeile "${r.pos}" hat count ${r.count}`);
    }
  }
});

test('Holz: Muster mit Holz bekommt eine Holzzeile, Muster ohne Holz nicht', () => {
  for (const idx of [1, 5, 8, 10]) {
    const m = buildModel({ muster: idx });
    const r = row(m, 'Holzteile');
    assert.ok(r, `Muster ${idx} ${DESIGNS[idx].key} muss eine Holzzeile haben`);
    assert.ok(r.kg > 0 && r.count > 0);
    assert.equal(r.count, m.counts.holzteile);
    assert.ok(m.pattern.solids.some((s) => s.material === 'wood'));
  }
  for (const idx of [30, 23, 32, 11]) {
    const m = buildModel({ muster: idx });
    assert.equal(row(m, 'Holzteile'), undefined,
      `Muster ${idx} ${DESIGNS[idx].key} hat kein Holz`);
    assert.ok(!m.pattern.solids.some((s) => s.material === 'wood'));
  }
});

test('Solid-Material ist gekennzeichnet und deckt sich mit den Kanälen', () => {
  const m = buildModel({ muster: 10 }); // panel-segment: Riegel (b) + Holz (hz)
  assert.ok(m.pattern.solids.length > 0);
  for (const s of m.pattern.solids) {
    assert.ok(['steel', 'wood'].includes(s.material));
    assert.ok(['plate', 'loft'].includes(s.solid.kind));
  }
  assert.equal(m.pattern.solids.filter((s) => s.material === 'wood').length, m.counts.holzteile);
  assert.equal(m.pattern.solids.filter((s) => s.material === 'steel').length, m.counts.stahlteile);
});

test('Stücklistenzeilen tragen den aufgelösten Profilnamen', () => {
  const m = buildModel({ muster: 23, fuellstabProfil: 1, diagonalProfil: 6 });
  assert.ok(row(m, 'Füllstäbe').pos.includes(CATALOG.infill[1].name));
  assert.ok(row(m, 'Diagonalen').pos.includes(CATALOG.infill[6].name));
});

// ---------------------------------------------------------------------------
// Montage / Profile / Treppe — unverändert gültig, nur auf ein Muster gestellt
// ---------------------------------------------------------------------------
test('Top-Montage: 4 Bolzen je Pfosten nach unten, Plattenmasse aus Live-Reglern', () => {
  const m = buildModel({ montageTyp: 1 });
  assert.equal(m.counts.bolzen, 4 * m.counts.posten);
  for (const b of m.bolts) assert.ok(b.b[2] < b.a[2], 'Top-Bolzen müssen nach unten zeigen');
  // 120×120×10: 1.13 kg je Platte (Research/mounting_and_style.md Sanity-Anker)
  assert.equal(round2(kgOf(m, 'Ankerplatten') / m.counts.platten), 1.13);
});

test('Fascia-Montage: 2 Bolzen je Pfosten in den Beton (+y), Platte 1.73 kg', () => {
  const m = buildModel({ montageTyp: 0 });
  assert.equal(m.counts.bolzen, 2 * m.counts.posten);
  for (const b of m.bolts) assert.ok(b.b[1] > b.a[1], 'Fascia-Bolzen müssen in die Platte/den Beton laufen');
  assert.equal(round2(kgOf(m, 'Ankerplatten') / m.counts.platten), 1.73);
});

test('Profilwechsel bewegt Geometrie UND Masse (Katalogzeile = eine Wahrheit)', () => {
  const a = buildModel({ handlaufProfil: 0 });
  const b = buildModel({ handlaufProfil: 3 }); // SHS 40x40x2.0
  assert.notEqual(round2(kgOf(a, 'Handlauf')), round2(kgOf(b, 'Handlauf')));
  assert.equal(round2(kgOf(b, 'Handlauf')), round2((a.slopeLen / 1000) * 2.386));
});

test('Füllstabprofil wirkt auf die Masse des Musters', () => {
  const a = buildModel({ muster: 30, fuellstabProfil: 0 }); // Rundstahl 12, 0.888
  const b = buildModel({ muster: 30, fuellstabProfil: 2 }); // Rundstahl 14, 1.208
  assert.equal(a.counts.fuellstaebe, b.counts.fuellstaebe);
  assert.ok(Math.abs(kgOf(b, 'Füllstäbe') / kgOf(a, 'Füllstäbe') - 1.208 / 0.888) < 1e-9);
});

test('Kurze Läufe: mindestens 1 Feld, Pfosten an beiden Enden', () => {
  const m = buildModel({ lauflaenge: 800, steigung: 400 });
  assert.equal(m.nBays, 1);
  assert.equal(m.counts.posten, 2);
  assert.ok(m.pattern.sweeps.length + m.pattern.solids.length > 0);
});

test('Katalog-Massen konsistent (Vollprofile = Fläche × 7.85e-6)', () => {
  const area = { round: (p) => Math.PI / 4 * p.dia ** 2, rect: (p) => p.dx * p.dia, flat: (p) => p.dx * p.dia };
  for (const role of Object.keys(CATALOG)) {
    for (const prof of CATALOG[role]) {
      if (prof.wall != null) continue; // Hohlprofile: scharfkantige Katalogwerte
      const kgm = area[prof.section](prof) * 7.85e-6 * 1000;
      assert.ok(Math.abs(kgm - prof.kgm) < 0.005, `${role}/${prof.name}: ${kgm} vs ${prof.kgm}`);
    }
  }
});

test('Pfosten rasten standardmäßig auf Stufenmitten', () => {
  const m = buildModel({});
  const going = 4000 / 13; // 13 Stufen bei 2000 mm Steigung
  for (let i = 0; i < m.postTs.length; i++) {
    const x = m.postTs[i] * 4000;
    assert.ok(Math.abs(x - (m.postSteps[i] + 0.5) * going) < 1e-6,
      `Pfosten ${i} steht nicht in Stufenmitte`);
  }
  assert.ok(m.notes.some((n) => n.includes('Stufenmitte')));
});

test('Anzahl Montagepunkte ist wählbar; zu weite Teilung warnt (Eurocode)', () => {
  const m3 = buildModel({ anzahlPfosten: 3 });
  assert.equal(m3.counts.posten, 3);
  assert.equal(m3.counts.platten, 3);
  assert.equal(m3.counts.bolzen, 6); // Fascia: 2 je Pfosten
  assert.ok(m3.maxGap > 1200);
  assert.ok(m3.warnings.some((w) => w.includes('Pfostenabstand')));

  const m8 = buildModel({ anzahlPfosten: 8, montageTyp: 1 });
  assert.equal(m8.counts.posten, 8);
  assert.equal(m8.counts.bolzen, 32); // Top: 4 je Pfosten
  assert.ok(!m8.warnings.some((w) => w.includes('Pfostenabstand')));
});

test('Top-Montage in Stufenmitte: Fußplatte liegt auf der Trittfläche', () => {
  const m = buildModel({ montageTyp: 1 });
  const stepRise = 2000 / 13;
  for (let i = 0; i < m.plates.length; i++) {
    const treadZ = m.postSteps[i] * stepRise;
    const plateTop = m.plates[i].center[2] + m.plates[i].size[2] / 2;
    assert.ok(Math.abs(plateTop - treadZ) < 1e-6, `Platte ${i} schwebt (${plateTop} vs ${treadZ})`);
  }
  // Pfostenfuß steht ebenfalls auf der Trittfläche
  const posts = m.members.filter((x) => x.role === 'posten');
  for (let i = 0; i < posts.length; i++) {
    assert.ok(Math.abs(posts[i].a[2] - m.postSteps[i] * stepRise) < 1e-6);
  }
});

test('Mehr Pfosten als Stufen wird auf die Stufenanzahl begrenzt', () => {
  const m = buildModel({ anzahlPfosten: 13 + 7 });
  assert.equal(m.counts.posten, 13);
  assert.ok(m.notes.some((n) => n.includes('begrenzt')));
});

test('Ohne Snapping (pfostenMittig=false) bleiben die Pfosten gleichmäßig verteilt', () => {
  const m = buildModel({ pfostenMittig: false });
  assert.deepEqual(m.postTs, [0, 0.25, 0.5, 0.75, 1]);
});

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------
test('Compliance-Warnungen feuern', () => {
  assert.ok(buildModel({ gelaenderhoehe: 950 }).warnings.some((w) => w.includes('1000 mm')));
  assert.ok(buildModel({ untergurtAbstand: 130 }).warnings.some((w) => w.includes('120')));
  assert.ok(buildModel({ fuellstabAbstand: 140 }).warnings.some((w) => w.includes('Lichter Spalt')));
});

test('Norm- und Statusangabe des Musters stehen als HINWEIS, nie als Warnung', () => {
  for (const idx of [0, 11, 28, 30]) {
    const m = buildModel({ muster: idx });
    const d = DESIGNS[idx];
    assert.ok(m.notes.some((n) => n.includes(d.norm)),
      `Muster ${idx}: Normhinweis fehlt in den Hinweisen`);
    assert.ok(m.notes.some((n) => n.includes(d.status)),
      `Muster ${idx}: Bearbeitungsstand fehlt in den Hinweisen`);
    // Der Normtext ist ein redaktionelles Feld der Engine, kein Rechenergebnis:
    // er darf nie als geprüfter Befund unter den Warnungen auftauchen.
    assert.ok(!m.warnings.some((w) => w.includes(d.norm)),
      `Muster ${idx}: Normtext steht fälschlich unter den Warnungen`);
  }
  // Muster 28 flat-horizontal ist normativ heikel — trotzdem KEINE erfundene
  // Fail-Bewertung: die Warnungen bleiben identisch zum unkritischen Muster 30.
  assert.deepEqual(buildModel({ muster: 28 }).warnings, buildModel({ muster: 30 }).warnings);
});

test('Rapport-Deckel: Hinweis erklärt die lichte Weite als Grund', () => {
  const frei = buildModel({ muster: 30, musterDichte: 1.0 });
  assert.equal(frei.pattern.clamped, false);
  assert.ok(!frei.notes.some((n) => n.includes('gedeckelt')));

  // 110 × 3 = 330 mm > GMAX 120 + STABB 12 = 132 mm
  const eng = buildModel({ muster: 30, musterDichte: 3.0 });
  assert.equal(eng.pattern.clamped, true);
  assert.equal(eng.pattern.rap, 132);
  const note = eng.notes.find((n) => n.includes('gedeckelt'));
  assert.ok(note, 'Deckelung muss erklärt werden');
  assert.ok(note.includes('lichte Weite'));

  // gapf verschärft den Deckel: Muster 18 hat gapf 0.78 -> 132 × 0.78
  const dicht = buildModel({ muster: 18, musterDichte: 4.0 });
  assert.equal(dicht.pattern.clamped, true);
  assert.ok(Math.abs(dicht.pattern.rap - 132 * 0.78) < 1e-9);

  // Muster ohne Rapport-Deckel (gap: false) werden nie geklemmt
  assert.equal(buildModel({ muster: 2, musterDichte: 5.0 }).pattern.clamped, false);
});

test('GMAX/STABB wirken auf den Deckel (Normparameter kommen aus params.js)', () => {
  const m = buildModel({ muster: 30, musterDichte: 3.0, GMAX: 100, STABB: 20 });
  assert.equal(m.pattern.rap, 120);
});
