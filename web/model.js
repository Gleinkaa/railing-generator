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

// Parametrisches Modell des Stiegengeländers — Portierung der Grasshopper-Logik
// nach reinem JavaScript. Keine Rendering-Abhängigkeit: buildModel(params)
// liefert Rahmen-Mittellinien, Platten/Bolzen, Stufen, das Ergebnis der
// Muster-Engine, die Stückliste und Compliance-Hinweise. Alle Maße in
// Millimetern, Koordinaten [x, y, z]: x = Laufrichtung, z = Höhe, y = quer
// (Stufen bei y > 0, Auskragung bei y < 0).
//
// Die Füllung baut seit Phase 14 der Musterkatalog (`patterns.js`, 34 Muster)
// und nicht mehr der dreiwertige `fuellungStil`. Dieses Modul liefert der
// Engine nur die Feldgrenzen als Kurvenpaar und reicht ihr Ergebnis
// unverändert an Ansicht und Stückliste weiter.

import { CATALOG, DIAGONAL_INFILL_INDEX } from './catalog.js';
import { buildPattern, clampIndex, DESIGNS } from './patterns.js';
import { line, curveLength, solidVolume } from './bay.js';
import { DEFAULT_PARAMS as MUSTER_PARAMS, withParams } from './patterns/params.js';

export const DEFAULT_PARAMS = {
  // Geometrie (Phase 0–3)
  lauflaenge: 4000,        // Lauf der Treppe (horizontal)
  steigung: 2000,          // Gesamtsteigung (vertikal)
  gelaenderhoehe: 1000,    // OENORM B 5371: >= 1000 mm (Systemlinie Handlauf)
  untergurtAbstand: 100,   // < 120 mm — 120-mm-Kugel (OIB RL 4) kommt nicht durch
  // Nomineller Achsabstand der Füllstäbe (legal max 132 bei Ø12). Seit der
  // Musterkatalog die Füllung baut, bestimmt NICHT mehr dieser Wert die
  // Stabteilung, sondern der Rapport des Musters (`musterDichte`, gedeckelt
  // über GMAX + STABB). Der Regler bleibt als Eingang der lichten-Weite-Prüfung
  // erhalten — offener Punkt für die Oberfläche: entweder an den Rapport
  // koppeln oder als eigenständige Vorgabe kennzeichnen.
  fuellstabAbstand: 115,
  maxPfostenAbstand: 1200, // Eurocode 1 / Holmdruck 3.0 kN/m

  // Profile (Phase 6) — 0-basierte Katalogindizes
  handlaufProfil: 0,
  untergurtProfil: 0,
  postenProfil: 0,
  fuellstabProfil: 0,
  diagonalProfil: DIAGONAL_INFILL_INDEX,

  // Montage (Phase 7): 0 = seitlich (Fascia), 1 = aufgesetzt (Top)
  montageTyp: 0,
  anzahlPfosten: 0,        // 0 = automatisch (Teilung <= 1200 mm), sonst gewünschte Anzahl
  pfostenMittig: true,     // Pfosten/Montagepunkte immer in Stufenmitte platzieren
  platteBreite: 100,
  platteHoehe: 220,
  platteBreiteTop: 120,
  platteTiefe: 120,
  platteDicke: 10,
  bolzenDurchmesser: 12,
  bolzenLaenge: 100,
  bolzenOffsetV: 75,
  bolzenOffsetXY: 20,
  bolzenMasseKg: 0.12,

  // Füllung (Phase 14): Musterkatalog statt der früheren drei Füllungsstile.
  // `fuellungStil` 0/1/2 gibt es nicht mehr — der Musterregler hat ihn ersetzt,
  // genau wie in der Grasshopper-Definition (`Muster`, 34 Einträge).
  muster: 30,              // Index in DESIGNS; 30 = 'bar-vertical' (Referenzfall)
  musterDichte: 1.0,       // Rapport-Faktor (GH: 'Muster-Rapport-Faktor')
  musterSeed: 1,           // Basis-Seed der Muster-Engine (GH: Eingang S)

  // Fertigungs- und Normparameter der Muster-Engine. Bewusst hineingespreizt
  // statt abgeschrieben: die Zahlen sind die Fallbacks der Python-Engine und
  // dürfen nur an EINER Stelle stehen (web/patterns/params.js).
  ...MUSTER_PARAMS,

  // Treppe (nur Kontext-Darstellung)
  trittbreite: 1200,
  stufenstaerke: 24,
  zeigeTreppe: true,
};

// Der frühere mulberry32-Generator ist mit den Dekor-Diagonalen entfallen. Den
// Zufall der Muster liefert jetzt ausschließlich `PyRandom` in bay.js — eine
// Portierung des CPython-Mersenne-Twisters. Ein zweiter, einfacherer PRNG in
// diesem Modul wäre eine Falle: er liefert bei gleichem Seed still eine ANDERE
// Geometrie als die Grasshopper-Engine (siehe Kopfkommentar in bay.js).

const STEEL_DENSITY = 7.85e-6; // kg/mm^3

// Rohdichte Holz. Die Muster-Engine (`grasshopper/patterns.py`) beschreibt für
// den Kanal `hz` nur den Weg "Volumen × Rohdichte" und legt selbst KEINE Zahl
// fest — die Zahl ist im Grasshopper-Dokument ein eigener Regler
// (`Holz-Rohdichte`). Der gepinnte Reglersatz vom 2026-08-05 in
// `reference/README.md` protokolliert ihn mit 600 kg/m³, und die dort
// abgelesene Masse kg_Holz = 27,584006 kg für Muster 01 hängt an genau diesem
// Wert. Deshalb steht hier 600 und nicht der oft zitierte Eichenwert von rund
// 700 kg/m³: ein anderer Wert würde die Web-Stückliste stumm gegen die
// Referenzaufnahme verschieben.
// Das ist trotzdem eine ANNAHME über die Holzart und kein Naturkonstante —
// Fichte liegt bei rund 470, Eiche bei rund 700 kg/m³. Wer eine andere Art
// verbaut, muss diesen Wert (und in Grasshopper den Regler) anpassen.
const WOOD_DENSITY = 0.60e-6; // kg/mm^3 — Annahme, siehe Kommentar

function len3(a, b) {
  return Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
}

export function buildModel(p = {}) {
  const P = { ...DEFAULT_PARAMS, ...p };
  const run = Math.max(P.lauflaenge, 1);
  const rise = Math.max(P.steigung, 0);
  const slopeLen = Math.hypot(run, rise);

  // Punkt auf der Treppenbasislinie (Nasenlinie) bei Parameter t in [0,1]
  const base = (t) => [t * run, 0, t * rise];

  const profHand = CATALOG.handrail[P.handlaufProfil] || CATALOG.handrail[0];
  const profUg = CATALOG.untergurt[P.untergurtProfil] || CATALOG.untergurt[0];
  const profPost = CATALOG.post[P.postenProfil] || CATALOG.post[0];
  const profFuell = CATALOG.infill[P.fuellstabProfil] || CATALOG.infill[0];
  const profDiag = CATALOG.infill[P.diagonalProfil] || CATALOG.infill[DIAGONAL_INFILL_INDEX];

  const members = []; // {role, profile, a, b}
  const add = (role, profile, a, b) => members.push({ role, profile, a, b });

  // --- Phase 1: Leitkurven -------------------------------------------------
  const zHand = P.gelaenderhoehe;
  const zUg = P.untergurtAbstand;
  add('handlauf', profHand, [0, 0, zHand], [run, 0, rise + zHand]);
  add('untergurt', profUg, [0, 0, zUg], [run, 0, rise + zUg]);

  // --- Treppenraster (für Stufenmitten-Snapping und Kontext-Darstellung) ----
  const nSteps = rise > 0 ? Math.max(1, Math.round(rise / 160)) : 0;
  const going = nSteps > 0 ? run / nSteps : run;
  const stepRise = nSteps > 0 ? rise / nSteps : 0;

  // --- Phase 2: Hauptpfosten / Montagepunkte --------------------------------
  // Anzahl wählbar ('Anzahl Pfosten', 0 = automatisch nach der 1200-mm-Regel);
  // mit 'pfostenMittig' rasten die Pfosten immer auf Stufenmitten, damit die
  // Befestigung nie auf einer Stufenkante landet.
  const autoPosts = Math.max(1, Math.ceil(slopeLen / P.maxPfostenAbstand)) + 1;
  let nPosts = P.anzahlPfosten > 0 ? Math.max(2, Math.round(P.anzahlPfosten)) : autoPosts;
  const snap = P.pfostenMittig && nSteps > 1;
  const notes = [];
  if (snap && nPosts > nSteps) {
    notes.push(`Anzahl Pfosten auf ${nSteps} begrenzt (nur ${nSteps} Stufenmitten vorhanden).`);
    nPosts = nSteps;
  }
  const postTs = [];
  const postSteps = []; // Stufenindex je Pfosten (nur im Snap-Modus belegt)
  if (snap) {
    for (let k = 0; k < nPosts; k++) {
      const idx = Math.round((k * (nSteps - 1)) / (nPosts - 1));
      postSteps.push(idx);
      postTs.push(((idx + 0.5) * going) / run);
    }
  } else {
    for (let i = 0; i < nPosts; i++) postTs.push(i / (nPosts - 1));
  }
  for (let i = 0; i < postTs.length; i++) {
    const [x, , z] = base(postTs[i]);
    // Aufgesetzte Montage in Stufenmitte: Pfostenfuß steht auf der Trittfläche
    // (halbe Steigung unter der Nasenlinie), sonst auf der Basislinie.
    const zFoot = snap && P.montageTyp === 1 ? postSteps[i] * stepRise : z;
    add('posten', profPost, [x, 0, zFoot], [x, 0, z + zHand]);
  }
  const nBays = nPosts - 1;

  // Feldgrenzen für die Füllung: Untergurt an allen Pfosten schneiden; Endstücke
  // vor dem ersten / nach dem letzten Pfosten gehören mit zum Füllfeld.
  const bounds = [0, ...postTs.filter((t) => t > 1e-9 && t < 1 - 1e-9), 1];
  const segments = [];
  for (let i = 0; i + 1 < bounds.length; i++) {
    if (bounds[i + 1] - bounds[i] > 1e-9) segments.push([bounds[i], bounds[i + 1]]);
  }

  // --- Phase 14: Füllung aus dem Musterkatalog -------------------------------
  // Je Feld ein Kurvenpaar: `lo` läuft auf der Untergurtlinie, `hi` auf der
  // Handlauflinie desselben Feldes. Beide sind an DENSELBEN Feldgrenzen
  // geschnitten — `Bay` leitet daraus O, Feldlänge L (entlang der Neigung) und
  // Feldhöhe H = zHand − zUg (lotrecht) ab.
  const bays = segments.map(([ta, tb]) => {
    const a = base(ta);
    const b = base(tb);
    return {
      lo: line([a[0], 0, a[2] + zUg], [b[0], 0, b[2] + zUg]),
      hi: line([a[0], 0, a[2] + zHand], [b[0], 0, b[2] + zHand]),
    };
  });

  // Außennormale des Feldsystems (`Bay.Nh`) — die Richtung, in die vorgesetzte
  // Muster auskragen. Hergeleitet, nicht geraten:
  //   * Die Stufen liegen bei y > 0 (`steps[].center[1] = +trittbreite/2`),
  //     der begehbare Raum ist also die positive y-Halbebene.
  //   * Die Fascia-Platte sitzt bei y = −platteDicke/2, ihre Bolzen laufen von
  //     y = −platteDicke aus NACH +y in den Beton: die Platte liegt außenbords,
  //     das Bauwerk innenbords.
  //   * Die vor Phase 14 fest verdrahteten Dekor-Diagonalen lagen bei
  //     y = −(Diagonal-Auslage), also ebenfalls in −y. Der Musterkatalog setzt
  //     seine vorgesetzten Elemente mit `AUSLAGE` um Nh vor — mit dieser
  //     Normale landen sie an derselben Stelle wie vorher.
  // Außen (von der Treppe weg) ist damit eindeutig −y.
  // Eine invertierte Normale baut jedes vorgesetzte Muster in den Treppenraum
  // hinein. Längen, Massen und Stückzahlen bleiben dabei bitgleich — der Fehler
  // ist nur im Bild zu sehen. Deshalb steht die Herleitung hier und nicht im
  // Kopf des nächsten Lesers.
  const NRM = [0, -1, 0];

  // Fertigungs-/Normparameter der Engine aus P herausziehen (Schlüssel kommen
  // aus params.js, damit hier keine zweite Zahlenliste entsteht).
  const musterParams = withParams(
    Object.fromEntries(Object.keys(MUSTER_PARAMS).map((k) => [k, P[k]])),
  );
  const musterIdx = clampIndex(P.muster);
  const design = DESIGNS[musterIdx];
  const pat = buildPattern(musterIdx, bays, {
    normal: NRM,
    seed: P.musterSeed,
    density: P.musterDichte,
    params: musterParams,
  });

  // Kanal a -> Füllstabprofil, Kanal b -> Diagonalprofil (patterns.js: `profile`
  // je Muster; die Profilregler gelten global). Kurvenobjekte bleiben exakt so,
  // wie bay.js sie liefert — Weltkoordinaten, keine Umwandlung, kein Resampling.
  const sweeps = [
    ...pat.a.map((curve) => ({ curve, profile: profFuell, channel: 'a' })),
    ...pat.b.map((curve) => ({ curve, profile: profDiag, channel: 'b' })),
  ];
  const solids = [
    ...pat.st.map((solid) => ({ solid, material: 'steel' })),
    ...pat.hz.map((solid) => ({ solid, material: 'wood' })),
  ];

  const lenA = pat.a.reduce((s, c) => s + curveLength(c), 0);
  const lenB = pat.b.reduce((s, c) => s + curveLength(c), 0);
  const volSt = pat.st.reduce((s, x) => s + solidVolume(x), 0);
  const volHz = pat.hz.reduce((s, x) => s + solidVolume(x), 0);

  // --- Phase 7: Montage ------------------------------------------------------
  const plates = []; // {center, size} — achsenparallele Boxen [dx, dy, dz]
  const bolts = [];  // {a, b, dia} — Zylinder-Mittellinien
  const fascia = P.montageTyp === 0;
  for (let i = 0; i < postTs.length; i++) {
    const [x, , z] = base(postTs[i]);
    // In Stufenmitte sitzt die Fußplatte auf der Trittfläche, nicht auf der Nasenlinie
    const zFoot = snap && !fascia ? postSteps[i] * stepRise : z;
    if (fascia) {
      // Hochkant-Platte an der Stirnseite der Kante, Bolzen quer in den Beton
      plates.push({
        center: [x, -P.platteDicke / 2, z],
        size: [P.platteBreite, P.platteDicke, P.platteHoehe],
      });
      for (const dv of [+P.bolzenOffsetV, -P.bolzenOffsetV]) {
        bolts.push({
          a: [x, -P.platteDicke, z + dv],
          b: [x, -P.platteDicke + P.bolzenLaenge, z + dv],
          dia: P.bolzenDurchmesser,
        });
      }
    } else {
      // Fußplatte flach unter dem Pfostenfuß, 4 Bolzen senkrecht nach unten
      plates.push({
        center: [x, 0, zFoot - P.platteDicke / 2],
        size: [P.platteBreiteTop, P.platteTiefe, P.platteDicke],
      });
      const ox = P.platteBreiteTop / 2 - P.bolzenOffsetXY;
      const oy = P.platteTiefe / 2 - P.bolzenOffsetXY;
      for (const [sx, sy] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
        bolts.push({
          a: [x + sx * ox, sy * oy, zFoot],
          b: [x + sx * ox, sy * oy, zFoot - P.bolzenLaenge],
          dia: P.bolzenDurchmesser,
        });
      }
    }
  }

  // --- Treppe (Kontext) ------------------------------------------------------
  const steps = [];
  if (P.zeigeTreppe && nSteps > 0) {
    for (let i = 0; i < nSteps; i++) {
      // Vorderkante (Nase) der Stufe i liegt auf der Basislinie bei t = i/nSteps
      steps.push({
        center: [i * going + going / 2, P.trittbreite / 2, i * stepRise - P.stufenstaerke / 2],
        size: [going + 30, P.trittbreite, P.stufenstaerke],
      });
    }
  }

  // --- Phase 5/9: Stückliste (BOM) -------------------------------------------
  const sumLen = (role) =>
    members.filter((m) => m.role === role).reduce((s, m) => s + len3(m.a, m.b), 0);

  const kg = (mm, kgm) => (mm / 1000) * kgm; // mm -> m VOR der Multiplikation!

  const plateFootprint = fascia
    ? P.platteBreite * P.platteHoehe
    : P.platteBreiteTop * P.platteTiefe;
  const plateMassEach = plateFootprint * P.platteDicke * STEEL_DENSITY;

  // Leere Kanäle bekommen KEINE Zeile. Eine Zeile "Holzteile … 0,00 kg" bei
  // einem Muster ganz ohne Holz behauptet ein Material, das nicht verbaut wird.
  const bomRows = [
    { pos: `Handlauf ${profHand.name}`, count: 1, lenMm: sumLen('handlauf'), kg: kg(sumLen('handlauf'), profHand.kgm) },
    { pos: `Untergurt ${profUg.name}`, count: 1, lenMm: sumLen('untergurt'), kg: kg(sumLen('untergurt'), profUg.kgm) },
    { pos: `Posten ${profPost.name}`, count: postTs.length, lenMm: sumLen('posten'), kg: kg(sumLen('posten'), profPost.kgm) },
    ...(pat.a.length
      ? [{ pos: `Füllstäbe ${profFuell.name}`, count: pat.a.length, lenMm: lenA, kg: kg(lenA, profFuell.kgm) }]
      : []),
    ...(pat.b.length
      ? [{ pos: `Diagonalen ${profDiag.name}`, count: pat.b.length, lenMm: lenB, kg: kg(lenB, profDiag.kgm) }]
      : []),
    // Solids werden über Volumen × Dichte verwogen, nicht über kg/m — sie haben
    // deshalb gar keine Profilzeile (patterns.js, Feld `profile`: null).
    ...(pat.st.length
      ? [{ pos: 'Stahlteile Muster', count: pat.st.length, lenMm: null, kg: volSt * STEEL_DENSITY }]
      : []),
    ...(pat.hz.length
      ? [{ pos: 'Holzteile Muster', count: pat.hz.length, lenMm: null, kg: volHz * WOOD_DENSITY }]
      : []),
    { pos: 'Ankerplatten', count: plates.length, lenMm: null, kg: plates.length * plateMassEach },
    { pos: `Bolzen M${P.bolzenDurchmesser}`, count: bolts.length, lenMm: null, kg: bolts.length * P.bolzenMasseKg },
  ];
  const total = bomRows.reduce((s, r) => s + r.kg, 0);

  // --- Compliance-Prüfungen ---------------------------------------------------
  const warnings = [];
  const infillCross = profFuell.dx ?? profFuell.dia;
  const clearGap = P.fuellstabAbstand - infillCross;
  if (clearGap > 120) {
    warnings.push(`Lichter Spalt der Füllstäbe ${clearGap.toFixed(0)} mm > 120 mm — ` +
      `OIB RL 4 (120-mm-Kugel) verletzt. Achsabstand auf ≤ ${120 + infillCross} mm senken.`);
  }
  if (P.gelaenderhoehe < 1000) {
    warnings.push(`Geländerhöhe ${P.gelaenderhoehe} mm < 1000 mm — ÖNORM B 5371 / OIB RL 4 ` +
      `fordern ≥ 1000 mm Absturzsicherung.`);
  }
  if (P.untergurtAbstand >= 120) {
    warnings.push(`Untergurt-Abstand ${P.untergurtAbstand} mm ≥ 120 mm — die 120-mm-Kugel ` +
      `passt unter dem Geländer durch.`);
  }
  // Pfostenabstand entlang der Neigung (inkl. Endüberstände als halbe Prüfweite)
  let maxGap = 0;
  for (let i = 0; i + 1 < postTs.length; i++) {
    maxGap = Math.max(maxGap, (postTs[i + 1] - postTs[i]) * slopeLen);
  }
  if (maxGap > P.maxPfostenAbstand + 1e-6) {
    warnings.push(`Pfostenabstand ${maxGap.toFixed(0)} mm > ${P.maxPfostenAbstand} mm — ` +
      `Holmdruck 3,0 kN/m (Eurocode 1) nicht gesichert. Mehr Montagepunkte wählen.`);
  }

  notes.push(`Lichter Spalt Füllstäbe: ${clearGap.toFixed(0)} mm (Anforderung ≤ 120 mm).`);

  // --- Muster: Hinweise, KEINE berechnete Bewertung ---------------------------
  // `norm` und `status` sind Textfelder der Engine (redaktionell gepflegt), kein
  // Rechenergebnis. Sie stehen deshalb unter den Hinweisen und nie unter den
  // Warnungen: eine Zeile in `warnings` liest sich als geprüfter Befund.
  notes.push(`Muster ${musterIdx} „${design.name}“ (${design.fam}), `
    + `Rapport ${pat.rap.toFixed(0)} mm, ${pat.a.length + pat.b.length} Stäbe, `
    + `${pat.st.length + pat.hz.length} Formteile.`);
  notes.push(`Normhinweis zum Muster (Angabe der Engine, keine berechnete `
    + `Bewertung): ${design.norm}`);
  notes.push(`Bearbeitungsstand des Musters: ${design.status}`);
  if (pat.clamped) {
    const roh = design.rap * P.musterDichte;
    notes.push(`Rapport von ${roh.toFixed(0)} auf ${pat.rap.toFixed(0)} mm gedeckelt. `
      + `Bei diesem Muster bestimmt der Rapport die lichte Weite direkt, deshalb `
      + `hängt die Grenze am MUSTER und nicht am Regler: ein weit aufgezogener `
      + `Dichteregler könnte sonst ein unzulässiges Feld ausliefern. Deckel = `
      + `(Öffnung max ${musterParams.GMAX} mm + Stabbreite ${musterParams.STABB} mm)`
      + `${design.gapf ? ` × ${design.gapf} (größte Öffnung liegt um diesen Faktor über dem Rapport)` : ''}.`);
  }

  if (snap) {
    notes.push(`Pfosten stehen in Stufenmitte (Stufen ${postSteps.map((i) => i + 1).join(', ')}); ` +
      `größter Pfostenabstand ${maxGap.toFixed(0)} mm.`);
  }

  return {
    params: P,
    slopeLen, nBays, postTs, postSteps, maxGap,
    members, plates, bolts, steps,
    // Ergebnis der Muster-Engine. `curve`/`solid` sind unverändert die Objekte
    // aus bay.js in Weltkoordinaten — die Ansicht sweept sie selbst.
    pattern: {
      index: musterIdx,
      key: design.key,
      name: design.name,
      fam: design.fam,
      description: design.description,
      rap: pat.rap,
      clamped: pat.clamped,
      norm: design.norm,
      status: design.status,
      // Aussenrichtung des Feldes, explizit mitgegeben statt implizit
      // vorausgesetzt: die Ansicht braucht sie, um Flachprofile mit der
      // breiten Seite nach aussen zu sweepen. Ohne diese Zeile riet der
      // Viewer auf [0,1,0] — bei symmetrischen Querschnitten unsichtbar,
      // bei Flachstahl waere es die falsche Kante nach vorne.
      normal: NRM,
      sweeps,
      solids,
    },
    bom: { rows: bomRows, total },
    warnings, notes,
    counts: {
      posten: postTs.length,
      fuellstaebe: pat.a.length,
      diagonalen: pat.b.length,
      stahlteile: pat.st.length,
      holzteile: pat.hz.length,
      platten: plates.length,
      bolzen: bolts.length,
    },
  };
}
