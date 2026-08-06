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

// rhythm.js — Familie "Rhythm" (Katalog-Indizes 16–24).
//
// 1:1 aus `grasshopper/patterns.py` portiert (Zeilen 869–996). Die Geometrie
// ist unveraendert: gleiche Konstanten, gleiche Schleifengrenzen, gleiche
// Reihenfolge der Ablagen in y.a / y.b / y.st / y.hz. Die Stueckliste und die
// Regressionstests vergleichen diese Listen POSITIONSWEISE — Umsortieren waere
// ein stiller Fehler.
//
// Abweichung von der Python-Fassung, und zwar die einzige: die GH-Eingaenge
// (FLACH_D, AUSLAGE, ...) sind dort Modul-Globals, hier werden sie als `P`
// durchgereicht (siehe params.js).
//
// Zufall: nur `p_rake_cross` zieht aus `y.rnd`. Der Zufallsstrom ist positionell
// — ein zusaetzlicher oder fehlender `random()`-Zug verschiebt jeden folgenden
// Wert und laesst die Geometrie von der Grasshopper-Engine abdriften.

/**
 * @typedef {import('../bay.js').Bay} Bay
 */

/**
 * Senkrechte Staebe mit Wellenbewegung: je Einheit ein kalt gebogener Stab,
 * als kubischer Bezier vom Untergurt zum Handlauf. Fuellt `a`.
 * Nicht zufallsbehaftet.   (grasshopper/patterns.py:869-874)
 *
 * @param {Bay} y
 * @param {number} rap   gedehnter Rapport in mm
 * @param {object} P     Parameter aus params.js
 */
export function p_bar_wave(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s = st * (i + 0.5);
    const amp = st * 0.35;
    y.bez([s, 0.0], [s + amp, y.H * 0.33], [s - amp, y.H * 0.66], [s, y.H], 'a');
  }
}

/**
 * Vier gestapelte waagrechte Zackenreihen, Spitze abwechselnd oben und unten;
 * oberste und unterste Reihe zusaetzlich an Handlauf bzw. Untergurt angebunden.
 * Fuellt `a` (Reihen) und `b` (Anbinder). Nicht zufallsbehaftet.
 * (grasshopper/patterns.py:877-902)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_chevron_h(y, rap, P) {
  const rows = 4;
  const [n, st] = y.units(rap);
  for (let r = 0; r < rows; r++) {
    const base = y.H * (r + 0.5) / rows;
    const amp = y.H / rows * 0.40;
    const pts = [[0.0, base - amp]];
    for (let i = 0; i < n; i++) {
      pts.push([i * st + st / 2.0, base + amp]);
      pts.push([(i + 1) * st, base - amp]);
    }
    // Reihe endet exakt am Posten; oberste/unterste Reihe zusaetzlich an den
    // Gurt angebunden, damit die Fuellung nicht nur an den Posten haengt.
    y.poly(pts, 'a');
    if (r === rows - 1) {
      // Hochpunkt, nicht Feldmitte: die Spitzen liegen bei i*st + st/2,
      // die Tiefpunkte bei i*st. Auf halber Feldbreite sitzt je nach
      // Einheitenzahl ein Tiefpunkt — der Anbinder haette dort ins Leere
      // gezeigt.
      const sp = st * Math.floor(n / 2) + st / 2.0;
      y.seg(sp, base + amp, sp, y.H, 'b');
    }
    if (r === 0 && n >= 2) {
      // n=1: der einzige innere Tiefpunkt-Index waere 0 — der Anbinder
      // laege exakt in der Postenachse. Die Reihe haengt dann ohnehin
      // an beiden Posten.
      const sp = st * Math.floor(n / 2);
      y.seg(sp, base - amp, sp, 0.0, 'b');
    }
  }
}

/**
 * Feine senkrechte Linien, deren Abstand ueber das Feld sinusfoermig enger und
 * weiter wird. Fuellt `a`. Nicht zufallsbehaftet.  (grasshopper/patterns.py:905-914)
 *
 * Die Modulation schwankt um +-28 %; massgebend fuer OIB 4.2.4 ist die WEITESTE
 * Oeffnung. Deshalb traegt dieses Muster im Katalog `gapf = 0.78` und der
 * Rapport-Deckel `(GMAX + STABB) * gapf` ist entsprechend verschaerft
 * (grasshopper/patterns.py:1177-1182). Der Deckel wirkt VOR dem Aufruf, `rap` kommt
 * hier bereits gedeckelt an — die Abstandsrechnung unten bleibt davon unberuehrt.
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_line_density(y, rap, P) {
  const [n] = y.units(rap);
  // (i+0.5)/n statt i/n ueber n+1 Staebe: die Randstaebe lagen exakt AUF den
  // Posten (sin(0) = sin(2pi) = 0, keine Verschiebung) — im Profil versenkt
  // und unsichtbar, aber je Zwischenposten 2*H Rundstahl doppelt in der
  // Stueckliste. Die Dichte-Modulation selbst bleibt unveraendert.
  for (let i = 0; i < n; i++) {
    const f = (i + 0.5) / Math.max(n, 1);
    const s = y.L * (f - 0.045 * Math.sin(2 * Math.PI * f));
    y.seg(Math.max(0.0, Math.min(y.L, s)), 0.0, Math.max(0.0, Math.min(y.L, s)), y.H, 'a');
  }
}

/**
 * Flachstahl-Staebe, deren Breite entlang einer Welle an- und abschwillt
 * (Laserzuschnitt, Dicke konstant). Fuellt `st`. Nicht zufallsbehaftet.
 * (grasshopper/patterns.py:917-924)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_bar_width_wave(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const f = i / Math.max(n - 1, 1);
    const bw = st * (0.25 + 0.60 * (0.5 + 0.5 * Math.sin(4 * Math.PI * f)));
    const cs = st * (i + 0.5);
    y.plate([[[cs - bw / 2.0, 0.0], [cs + bw / 2.0, 0.0],
      [cs + bw / 2.0, y.H], [cs - bw / 2.0, y.H]]], P.FLACH_D, 'st');
  }
}

/**
 * Abwechselnd breite und schmale Flachstaebe in festem Verhaeltnis.
 * Fuellt `st`. Nicht zufallsbehaftet.  (grasshopper/patterns.py:927-933)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_bar_alternate(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const bw = st * (i % 2 === 0 ? 0.72 : 0.20);
    const cs = st * (i + 0.5);
    y.plate([[[cs - bw / 2.0, 0.0], [cs + bw / 2.0, 0.0],
      [cs + bw / 2.0, y.H], [cs - bw / 2.0, y.H]]], P.FLACH_D, 'st');
  }
}

/**
 * Rechteckmodule, jedes von genau einer Diagonale geteilt; die Diagonalrichtung
 * wechselt schachbrettartig. Fuellt `a` (Stege) und `b` (Diagonalen).
 * Nicht zufallsbehaftet.  (grasshopper/patterns.py:936-954)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_grid_split(y, rap, P) {
  const [nx, sx] = y.units(rap);
  const ny = 2;
  const sy = y.H / ny;
  // Nur die INNEREN Stege: i=0/nx lagen exakt auf den Posten, j=0/ny exakt
  // in Untergurt und Handlauf — der Modulrahmen existiert als Struktur
  // bereits, die deckungsgleichen Staebe waren nur versteckte Stueckliste
  // (2*(L+H) Rundstahl je Feld).
  for (let i = 1; i < nx; i++) {
    y.seg(i * sx, 0.0, i * sx, y.H, 'a');
  }
  for (let j = 1; j < ny; j++) {
    y.seg(0.0, j * sy, y.L, j * sy, 'a');
  }
  for (let i = 0; i < nx; i++) {
    for (let j = 0; j < ny; j++) {
      const s0 = i * sx;
      const t0 = j * sy;
      if ((i + j) % 2 === 0) {
        y.seg(s0, t0, s0 + sx, t0 + sy, 'b');
      } else {
        y.seg(s0, t0 + sy, s0 + sx, t0, 'b');
      }
    }
  }
}

/**
 * Schraegstaebe mit zufaelligem Kopfversatz — die Staebe kreuzen einander
 * zwischen den Gurten. Fuellt `a`. ZUFALLSBEHAFTET: genau EIN
 * `y.rnd.random()`-Zug je Einheit, in Schleifenreihenfolge.
 * (grasshopper/patterns.py:957-966)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_rake_cross(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s0 = st * (i + 0.5);
    const s1 = s0 + (y.rnd.random() - 0.5) * st * 3.2;
    // Klemmung mit halbem Rapport Randabstand: der harte [0,L]-Clamp
    // stapelte Stabkoepfe exakt in die Ecke Posten/Handlauf (mehrere
    // Staebe koinzident, streckenweise IM Posten).
    const lo = Math.min(st * 0.5, y.L / 2.0);
    y.seg(s0, 0.0, Math.max(lo, Math.min(y.L - lo, s1)), y.H, 'a');
  }
}

/**
 * Gleichmaessige Senkrechte mit einzelnen, eingestreuten Diagonalen.
 * Fuellt `a` (Senkrechte) und `b` (Diagonalen, um AUSLAGE vorgesetzt).
 * Nicht zufallsbehaftet — die "Streuung" ist deterministisch.
 * (grasshopper/patterns.py:969-982)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_bar_scatter(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a');
  }
  // Schrittweite >= 2, sonst wird aus "eingestreut" bei kleinen n eine
  // lueckenlose Diagonalschar; und mindestens EINE Diagonale, sonst
  // degeneriert das Muster im schmalen Feld zu Vertical Bars.
  const step = Math.max(2, Math.floor(n / 3));
  let picks = [];
  for (let i = 1; i < n - 1; i += step) picks.push(i);
  if (picks.length === 0 && n >= 2) {
    picks = [Math.floor(n / 2)];
  }
  for (const i of picks) {
    const s0 = st * (i + 0.5);
    y.seg(s0, 0.0, Math.min(s0 + st, y.L), y.H, 'b', P.AUSLAGE);
  }
}

/**
 * Gerades Stabfeld mit zwei davor gesetzten Wellenbaendern (je Band zwei
 * Bezier-Haelften). Fuellt `a` (Staebe) und `b` (Baender, um AUSLAGE
 * vorgesetzt). Nicht zufallsbehaftet.  (grasshopper/patterns.py:985-996)
 *
 * @param {Bay} y
 * @param {number} rap
 * @param {object} P
 */
export function p_wave_overlay(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a');
  }
  for (const f of [0.30, 0.70]) {
    const t = y.H * f;
    const amp = y.H * 0.12;
    const half = y.L / 2.0;
    y.bez([0.0, t], [half * 0.5, t + amp * 2], [half * 0.5, t - amp * 2],
      [half, t], 'b', P.AUSLAGE);
    y.bez([half, t], [half * 1.5, t + amp * 2], [half * 1.5, t - amp * 2],
      [y.L, t], 'b', P.AUSLAGE);
  }
}
