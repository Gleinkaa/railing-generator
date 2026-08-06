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

// formed.js — Musterfamilie "Formed" (Index 0–9),
// 1:1 portiert aus `grasshopper/patterns.py`, Abschnitt "Muster".
//
// ---------------------------------------------------------------------------
// Was hier steht und was nicht
// ---------------------------------------------------------------------------
// Jede Funktion ist eine mechanische Uebersetzung ihres Python-Gegenstuecks:
// dieselben Konstanten, dieselben Schleifengrenzen, dieselbe REIHENFOLGE der
// Ablagen in `y.a` / `y.b` / `y.st` / `y.hz`. Die Reihenfolge ist Teil des
// Vertrags — Stueckliste und Regressionstests vergleichen die Listen
// positionsweise, ein umsortierter Push faellt in der Ansicht nicht auf und in
// der Stueckliste sofort.
//
// Kanaele:
//   y.a   Staebe im Profil "Fuellstab"   (Hauptfigur)
//   y.b   Staebe im Profil "Diagonal"    (Riegel, Akzente, Zierteile)
//   y.st  Stahl-Solids (Bleche, Flachstahl)
//   y.hz  Holz-Solids  (Bloecke, Lamellen, Scheiben)
//
// Signatur: `p_x(y, rap, P)` — die Grasshopper-Engine liest HOLZ_D, HOLZ_LUFT
// usw. als Modul-Globals; im Browser kommen sie als `P` herein (siehe
// params.js). Das ist die einzige bewusste Abweichung von der 1:1-Portierung.
//
// `y.arc3(...)` der Python-Engine heisst hier `y.bowFlat(...)`: in bay.js gibt
// es bereits eine freie Funktion `arc3(p0, pm, p1)`, die einen echten
// WELT-Kreisbogen baut. Beide sind an derselben Stelle plausibel und liefern
// unterschiedliche Geometrie — deshalb der andere Name.

import { arc3 } from '../bay.js';
import { ellipseLoop } from './shared.js';


// ------------------------------------------------------------------- Muster

/**
 * U-Loop (Index 0) — je Einheit zwei senkrechte Staebe, unten durch einen
 * U-Bogen verbunden, der auf dem Untergurt aufsitzt.
 * Kanaele: `a`. Nicht zufaellig.  (grasshopper/patterns.py:596-604)
 */
export function p_loop_u(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const r = st * 0.34;
    const s0 = i * st + st * 0.5 - r;
    const s1 = s0 + 2 * r;
    y.seg(s0, y.H, s0, r, 'a');
    y.bow([s0, r], [s0 + r, 0.0], [s1, r], 'a');
    y.seg(s1, r, s1, y.H, 'a');
  }
}

/**
 * Staggered Panels (Index 1) — zwei durchlaufende Riegel, davor je Einheit ein
 * in Hoehe und Lage versetzter Holzblock.
 * Kanaele: `b` (Riegel), `hz` (Bloecke). ZUFAELLIG: zwei `random()`-Zuege je
 * Einheit (Blockhoehe, Blocklage).  (grasshopper/patterns.py:607-627)
 */
export function p_panel_stagger(y, rap, P) {
  const [n, st] = y.units(rap);
  const rails = [0.30 * y.H, 0.70 * y.H];
  for (const r of rails) {
    y.seg(0.0, r, y.L, r, 'b');
  }
  for (let i = 0; i < n; i++) {
    const bh = y.H * (0.42 + y.rnd.random() * 0.30);
    // Luftspalt wie bei Wide Slats/Segmented Panels: der Katalog sagt
    // "Holzbloecke enden frei" — ohne Klemmung stiessen Bloecke buendig an
    // Handlauf oder Untergurt (im Render sichtbar). Zufallsfolge unveraendert:
    // weiterhin genau ein random()-Zug fuer die Lage.
    const span = Math.max(0.0, y.H - bh - 2.0 * P.HOLZ_LUFT);
    let bt = P.HOLZ_LUFT + span * y.rnd.random();
    // K2: jeder Block muss mindestens EINEN Riegel ueberdecken, sonst haengt
    // er in der Luft. Statt zu verwerfen wird er auf den naechsten Riegel
    // geschoben — das Muster bleibt zufaellig, die Konstruktion bleibt gueltig.
    if (!rails.some((r) => bt <= r && r <= bt + bh)) {
      // Python `min(..., key=...)` behaelt bei Gleichstand den ERSTEN Riegel.
      let near = rails[0];
      let best = Math.abs(rails[0] - (bt + bh / 2.0));
      for (let k = 1; k < rails.length; k++) {
        const d = Math.abs(rails[k] - (bt + bh / 2.0));
        if (d < best) { best = d; near = rails[k]; }
      }
      bt = Math.max(P.HOLZ_LUFT, Math.min(y.H - bh - P.HOLZ_LUFT, near - bh / 2.0));
    }
    y.block(i * st + st * 0.12, bt, i * st + st * 0.88, bt + bh, P.HOLZ_D, 'hz',
      P.HOLZ_OFF);
  }
}

/**
 * Ray Diamond (Index 2) — je Einheit eine Raute, darin 12 vom Mittelpunkt bis
 * zum Rautenrand laufende Strahlen.
 * Kanaele: `a` (Raute), `b` (Strahlen). Nicht zufaellig.
 * (grasshopper/patterns.py:630-641)
 */
export function p_ray_diamond(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const cs = st * (i + 0.5);
    const ct = y.H / 2.0;
    const rx = st * 0.5;
    const ry = y.H / 2.0;
    y.poly([[cs - rx, ct], [cs, ct + ry], [cs + rx, ct], [cs, ct - ry],
      [cs - rx, ct]], 'a');
    for (let k = 0; k < 12; k++) {
      const ang = 2 * Math.PI * k / 12.0;
      const ca = Math.cos(ang);
      const sa = Math.sin(ang);
      const d = 1.0 / (Math.abs(ca) / rx + Math.abs(sa) / ry);
      y.seg(cs, ct, cs + d * ca, ct + d * sa, 'b');
    }
  }
}

/**
 * Beaded Bars (Index 3) — durchlaufender Senkrechtstab, auf zwei Hoehen von je
 * zwei Halbkreisen zu einer runden Verdickung umschlossen.
 * Kanaele: `a` (Stab), `b` (Halbkreise, je Verdickung 2 Stueck).
 * Nicht zufaellig.  (grasshopper/patterns.py:644-653)
 *
 * Einziger Bauplatz, an dem das Original ausserhalb der Bay-Methoden Geometrie
 * baut (`rg.ArcCurve(rg.Arc(...))` ueber drei WELTpunkte). Gegenstueck hier ist
 * die freie Funktion `arc3` aus bay.js — sie ist genau dafuer da und liefert
 * `null`, wo Rhino `Arc.IsValid == false` melden wuerde; `part()` wirft das
 * dann weg. Bewusst NICHT `y.bow`/`y.bowFlat`: die Verdickung ist im Original
 * ein echter Weltkreis.
 */
export function p_bar_bead(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s = st * (i + 0.5);
    y.seg(s, 0.0, s, y.H, 'a');
    for (const f of [0.33, 0.66]) {
      const r = st * 0.22;
      const ct = y.H * f;
      y.part([arc3(y.P(s - r, ct), y.P(s, ct + r), y.P(s + r, ct)),
        arc3(y.P(s + r, ct), y.P(s, ct - r), y.P(s - r, ct))], 'b');
    }
  }
}

/**
 * Vee Pairs (Index 4) — je Einheit ein V, Spitze unten auf dem Untergurt.
 * Kanaele: `a`. Nicht zufaellig.  (grasshopper/patterns.py:656-660)
 */
export function p_vee_pair(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s0 = i * st;
    y.poly([[s0, y.H], [s0 + st / 2.0, 0.0], [s0 + st, y.H]], 'a');
  }
}

/**
 * Wide Slats (Index 5) — zwei durchlaufende Riegel, davor breite Holzlamellen
 * mit schmaler Fuge.
 * Kanaele: `b` (Riegel), `hz` (Lamellen). Nicht zufaellig.
 * (grasshopper/patterns.py:663-673)
 */
export function p_panel_slat(y, rap, P) {
  const [n, st] = y.units(rap);
  for (const r of [0.25 * y.H, 0.75 * y.H]) {
    y.seg(0.0, r, y.L, r, 'b');
  }
  for (let i = 0; i < n; i++) {
    // Fuge absolut statt proportional: 0.12*st waren beim Nennrapport
    // schon 16,8 mm — der norm-Text bewertet aber eine 8-12-mm-Fuge.
    // HOLZ_LUFT (Default 8) ist dieselbe Konvention wie vertikal.
    y.block(i * st + P.HOLZ_LUFT / 2.0, P.HOLZ_LUFT,
      (i + 1) * st - P.HOLZ_LUFT / 2.0, y.H - P.HOLZ_LUFT,
      P.HOLZ_D, 'hz', P.HOLZ_OFF);
  }
}

/**
 * Stacked Arches (Index 6) — Zwischenriegel auf 0.38 H, darueber der grosse
 * haengende Bogen, darunter der kleine stehende.
 * Kanaele: `a` (Boegen mit Schenkeln), `b` (Zwischenriegel). Nicht zufaellig.
 * (grasshopper/patterns.py:676-692)
 */
export function p_arch_stack(y, rap, P) {
  const [n, st] = y.units(rap);
  const rt = y.H * 0.38;
  y.seg(0.0, rt, y.L, rt, 'b');
  for (let i = 0; i < n; i++) {
    const r = st * 0.36;
    const s0 = i * st + st * 0.5 - r;
    const s1 = s0 + 2 * r;
    y.seg(s0, y.H, s0, rt + r, 'a');
    y.bow([s0, rt + r], [s0 + r, rt], [s1, rt + r], 'a');
    y.seg(s1, rt + r, s1, y.H, 'a');
    const r2 = st * 0.20;
    const s2 = i * st + st * 0.5 - r2;
    const s3 = s2 + 2 * r2;
    y.seg(s2, 0.0, s2, rt - r2, 'a');
    y.bow([s2, rt - r2], [s2 + r2, rt], [s3, rt - r2], 'a');
    y.seg(s3, rt - r2, s3, 0.0, 'a');
  }
}

/**
 * J-Hooks (Index 7) — Stab vom Handlauf herab, unten in einen J-Bogen gelegt,
 * der auf dem Untergurt aufsitzt und wieder bis zum Zwischenriegel steigt.
 * Kanaele: `a` (Haken), `b` (Zwischenriegel). Nicht zufaellig.
 * (grasshopper/patterns.py:695-704)
 */
export function p_hook_j(y, rap, P) {
  const [n, st] = y.units(rap);
  const rt = y.H * 0.45;
  y.seg(0.0, rt, y.L, rt, 'b');
  for (let i = 0; i < n; i++) {
    const r = st * 0.26;
    const s = st * (i + 0.5) - r;
    y.seg(s, y.H, s, r, 'a');
    y.bow([s, r], [s + r, 0.0], [s + 2 * r, r], 'a');
    y.seg(s + 2 * r, r, s + 2 * r, rt, 'a');
  }
}

/**
 * Diamond Lattice (Index 8) — Rautengitter mit einer runden Holzscheibe im
 * Kreuzungspunkt.
 * Kanaele: `a` (Raute), `hz` (Scheibe, entfaellt im gestauchten Feld).
 * Nicht zufaellig.  (grasshopper/patterns.py:707-718)
 */
export function p_lattice_diamond(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const cs = st * (i + 0.5);
    y.poly([[cs - st / 2.0, y.H / 2.0], [cs, y.H], [cs + st / 2.0, y.H / 2.0],
      [cs, 0.0], [cs - st / 2.0, y.H / 2.0]], 'a');
    const d = Math.min(st, y.H) * 0.16;
    // SCHEIBE heisst rund: der block() lieferte ein schiefes Parallelogramm.
    // Im gestauchten Endfeld (d unter ~20 mm) entfaellt der Akzent ganz,
    // statt als Holz-Chip zu enden.
    if (d > 20.0) {
      y.plate([ellipseLoop(cs, y.H / 2.0, d, d)], P.HOLZ_D, 'hz', P.HOLZ_OFF);
    }
  }
}

/**
 * Loop and Drop (Index 9) — breite stehende Schlaufe unten, darueber ein
 * Tropfen, der am Handlauf haengt und auf dem Schlaufenscheitel aufsitzt.
 * Kanaele: `a` (Schlaufe), `b` (Tropfenstiel + zwei flache Boegen).
 * Nicht zufaellig.  (grasshopper/patterns.py:721-734)
 */
export function p_loop_drop(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const cs = st * (i + 0.5);
    const r = st * 0.30;
    const top = y.H * 0.62;
    y.seg(cs - r, 0.0, cs - r, top - r, 'a');
    y.bow([cs - r, top - r], [cs, top], [cs + r, top - r], 'a');
    y.seg(cs + r, top - r, cs + r, 0.0, 'a');
    // Tropfen: Stiel am Handlauf, Spitze sitzt AUF dem Loop-and-Drop-Bogen
    const mid = (y.H * 0.88 + top) / 2.0;
    y.seg(cs, y.H, cs, y.H * 0.88, 'b');
    y.bowFlat([cs, y.H * 0.88], [cs - r * 0.45, mid], [cs, top], 'b');
    y.bowFlat([cs, top], [cs + r * 0.45, mid], [cs, y.H * 0.88], 'b');
  }
}
