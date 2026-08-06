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

// shared.js — Hilfsfunktionen, die sich mehrere Musterfamilien teilen.
//
// Die Python-Engine hat diese Helfer auf Modulebene stehen, weil dort alle 34
// Muster in EINER Datei liegen. Hier sind sie auf vier Familien-Dateien
// aufgeteilt, also braucht es einen gemeinsamen Ort — sonst laegen zwei Kopien
// derselben Formel herum und wuerden irgendwann auseinanderlaufen.

/**
 * Geschlossener Ellipsenring in (s,t) mit k Stuetzpunkten.
 * Portierung von `_ellipse_loop` (grasshopper/patterns.py:780-782).
 *
 * Der Ring wird NICHT explizit geschlossen zurueckgegeben — `Bay._loops`
 * haengt den Anfangspunkt selbst wieder an.
 *
 * Benutzt von `lattice-diamond` (Scheiben-Akzente) sowie von den beiden
 * Laserblech-Mustern `sheet-ellipse` und `sheet-grain` (Aussparungen).
 */
export function ellipseLoop(cs, ct, rs, rt, k = 24) {
  const pts = [];
  for (let i = 0; i < k; i++) {
    pts.push([
      cs + rs * Math.cos(2 * Math.PI * i / k),
      ct + rt * Math.sin(2 * Math.PI * i / k),
    ]);
  }
  return pts;
}
