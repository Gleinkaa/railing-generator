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

// lines.js — Familie "Lines" (Muster-Indizes 25–33), 1:1 portiert aus
// `grasshopper/patterns.py` (Zeilen 999–1080).
//
// Die geradlinige Familie: senkrechte Staebe, waagrechte Riegel, gleichmaessige
// Schraegen. Hier steckt keine Zufallskomponente — jede Funktion dieser Datei
// ist deterministisch, `y.rnd` wird nirgends angefasst.
//
// `p_bar_vertical` (grasshopper/patterns.py:1051) ist der REFERENZFALL der Engine:
// Index 30 ist der Default, auf den zurueckgefallen wird, und die festgehaltene
// Referenzmasse von 77,49 kg wird gegen genau dieses Muster gemessen. Ein
// Off-by-one in der Stabzahl faellt optisch nicht auf, verschiebt aber die
// gesamte Stueckliste.
//
// Signatur ueberall `p_x(y, rap, P)`: `y` = Bay (bay.js), `rap` = gedehnter
// Rapport in mm, `P` = Parameterobjekt (params.js). In der Grasshopper-Engine
// sind die Parameter Modul-Globals; siehe Kopfkommentar von params.js.

import { pyRound } from '../bay.js';

/**
 * Senkrechte Staebe, bei denen jeder dritte im Diagonalprofil ausgefuehrt wird —
 * die Staerke stuft sich also ueber das Feld ab.
 * Kanaele: `a` (Fuellstab) und `b` (Diagonal). Nicht randomisiert.
 * grasshopper/patterns.py:999
 */
export function p_bar_graded(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s = st * (i + 0.5);
    y.seg(s, 0.0, s, y.H, i % 3 === 0 ? 'b' : 'a');
  }
}

/**
 * Offene U-Rahmen, die nebeneinander auf dem Untergurt stehen: zwei senkrechte
 * Schenkel bis zum Handlauf, unten durch ein Querstueck verbunden.
 * Kanal: `a`. Nicht randomisiert.
 * grasshopper/patterns.py:1006
 */
export function p_frame_u(y, rap, P) {
  const [n, st] = y.units(rap);
  // Querstueck AUF dem Untergurt, nicht IN ihm: bei t=0 verlief seine
  // Mittellinie exakt in der Untergurt-Mittellinie und verschwand komplett
  // im Gurtprofil — im Render blieben scheinbar nackte Stabpaare uebrig,
  // das U war unsichtbar. 2*STABB Aufstand (Default 24 mm) raeumt die halbe
  // Hoehe des Standard-Untergurts (Flachstahl 40x10 hochkant: 20 mm) frei;
  // die leichte Restueberdeckung liest sich als Schweissanschluss.
  const t0 = P.STABB * 2.0;
  for (let i = 0; i < n; i++) {
    const s0 = i * st + st * 0.18;
    const s1 = (i + 1) * st - st * 0.18;
    y.poly([[s0, y.H], [s0, t0], [s1, t0], [s1, y.H]], 'a');
  }
}

/**
 * Senkrechte Staebe, gegliedert durch zwei durchlaufende Querriegel auf 32 %
 * und 68 % der Feldhoehe.
 * Kanaele: `a` (Staebe), `b` (Riegel). Nicht randomisiert.
 * grasshopper/patterns.py:1021
 */
export function p_bar_railed(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a');
  }
  for (const f of [0.32, 0.68]) {
    y.seg(0.0, y.H * f, y.L, y.H * f, 'b');
  }
}

/**
 * Waagrechte Flachprofile ueber die volle Feldlaenge, in der Feldmitte durch
 * einen senkrechten Zwischenposten gehalten. Die Teilung laeuft hier ueber die
 * HOEHE, nicht ueber die Laenge — deshalb kein `y.units()`.
 * Kanaele: `a` (Flachprofile), `b` (Posten). Nicht randomisiert.
 * grasshopper/patterns.py:1029
 */
export function p_flat_horizontal(y, rap, P) {
  const n = Math.max(Math.trunc(pyRound(y.H / Math.max(rap, 1.0))), 2);
  for (let i = 0; i < n; i++) {
    const t = y.H * (i + 0.5) / n;
    y.seg(0.0, t, y.L, t, 'a');
  }
  y.seg(y.L / 2.0, 0.0, y.L / 2.0, y.H, 'b');
}

/**
 * Dichte, gleichmaessige Schraffur unter 45° im Feldsystem (Steigung 1:1 in
 * s/t), lamellenartig. Laeuft von `-y.H` an, damit die angeschnittenen Dreiecke
 * an beiden Feldenden entstehen.
 * Kanal: `a`. Nicht randomisiert.
 * grasshopper/patterns.py:1037
 */
export function p_hatch_45(y, rap, P) {
  const [, st] = y.units(rap);
  let k = -y.H;
  while (k < y.L) {
    const s0 = Math.max(k, 0.0);
    const s1 = Math.min(k + y.H, y.L);
    // Fertigungs-Mindestlaenge statt TOL: je nach L mod st blieb in der
    // Ecke am Posten ein Millimeter-Stummel uebrig, der gebaut, gesweept
    // und in der Stueckliste gezaehlt wurde.
    if ((s1 - s0) * Math.sqrt(2.0) > 30.0) {
      y.seg(s0, s0 - k, s1, s1 - k, 'a');
    }
    k += st;
  }
}

/**
 * Gleichmaessig geteilte senkrechte Staebe — das Referenz-Fuellfeld der Engine
 * (Index 30, Default). Jeder Stab sitzt in der Mitte seiner Rapport-Einheit.
 * Kanal: `a`. Nicht randomisiert.
 * grasshopper/patterns.py:1051
 */
export function p_bar_vertical(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a');
  }
}

/**
 * Vierkantstaebe, um die eigene Achse tordiert. Einziges Muster dieser Familie,
 * das `y.twisted()` benutzt: das liefert einen gelofteten SOLID, keine
 * gesweepte Kurve.
 * Kanal: `st` (Stahl-Solids). Nicht randomisiert.
 * grasshopper/patterns.py:1057
 */
export function p_bar_twist(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.twisted(st * (i + 0.5), 0.0, y.H, P.VIERKANT_W, 1.0);
  }
}

/**
 * Feine Staebe unter EINEM konstanten Winkel geneigt. Die Neigung ist ueber
 * `lean` an den Rapport gekoppelt, die Randstaebe werden auf [0, L]
 * zurueckgeschnitten und laufen deshalb nicht ueber die volle Hoehe.
 * Kanal: `a`. Nicht randomisiert.
 * grasshopper/patterns.py:1063
 */
export function p_rake_uniform(y, rap, P) {
  const [n, st] = y.units(rap);
  const lean = st * 0.8;
  for (let i = 0; i < n + 1; i++) {
    const s0 = i * st;
    const bs = s0 - lean / 2.0;
    const ts = s0 + lean / 2.0;
    const bc = Math.max(bs, 0.0);
    const tc = Math.min(ts, y.L);
    if (tc <= bc) continue;
    y.seg(bc, y.H * (bc - bs) / lean, tc, y.H * (tc - bs) / lean, 'a');
  }
}

/**
 * Senkrechte Staebe, auf halber Hoehe zu einem flachen V geknickt. Der Knick
 * zeigt in Feldrichtung; er wird bei `y.L` gekappt, der letzte Stab bekommt
 * deshalb ein flacheres V.
 * Kanal: `a`. Nicht randomisiert.
 * grasshopper/patterns.py:1075
 */
export function p_vee_center(y, rap, P) {
  const [n, st] = y.units(rap);
  const dx = st * 0.45;
  for (let i = 0; i < n; i++) {
    const s = st * (i + 0.5);
    y.poly([[s, y.H], [Math.min(s + dx, y.L), y.H / 2.0], [s, 0.0]], 'a');
  }
}
