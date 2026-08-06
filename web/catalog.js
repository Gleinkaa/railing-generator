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

// Stahlprofil-Katalog — Portierung von grasshopper/profiles.py (single source of truth).
// Der 0-basierte Zeilenindex je Rolle IST der Wert des zugehörigen Profil-Selektors;
// Geometrie (Querschnitt) und BOM-Masse (kg/m) kommen aus derselben Zeile und können
// daher nie auseinanderlaufen.
//
// section:  'round' -> Kreis mit Durchmesser dia (dx ungenutzt)
//           'rect'/'flat' -> Rechteck dx × dia (Außenmaße)
// wall beeinflusst nur kg/m, nie die gezeichnete Kontur (repräsentative Volumen).
// kg/m: Vollmaterial = Fläche·7.85e-6; Hohlprofile scharfkantig (siehe
// Research/profile_catalog.md — reproduziert die Anker 1.993 / 2.386 exakt).

export const CATALOG = {
  handrail: [
    { name: 'Rundrohr 42.4x2.0', section: 'round', dx: null, dia: 42.4, wall: 2.0, kgm: 1.993 },
    { name: 'Rundrohr 33.7x2.0', section: 'round', dx: null, dia: 33.7, wall: 2.0, kgm: 1.564 },
    { name: 'Rundrohr 48.3x2.6', section: 'round', dx: null, dia: 48.3, wall: 2.6, kgm: 2.930 },
    { name: 'SHS 40x40x2.0',     section: 'rect',  dx: 40,   dia: 40,   wall: 2.0, kgm: 2.386 },
    { name: 'RHS 40x20x2.0',     section: 'rect',  dx: 40,   dia: 20,   wall: 2.0, kgm: 1.758 },
    { name: 'Flachstahl 40x10',  section: 'flat',  dx: 40,   dia: 10,   wall: null, kgm: 3.140 },
    { name: 'Flachstahl 50x10',  section: 'flat',  dx: 50,   dia: 10,   wall: null, kgm: 3.925 },
  ],
  post: [
    { name: 'SHS 40x40x2.0',     section: 'rect',  dx: 40,   dia: 40,   wall: 2.0, kgm: 2.386 },
    { name: 'RHS 50x30x2.0',     section: 'rect',  dx: 50,   dia: 30,   wall: 2.0, kgm: 2.386 },
    { name: 'SHS 50x50x2.0',     section: 'rect',  dx: 50,   dia: 50,   wall: 2.0, kgm: 3.014 },
    { name: 'RHS 60x40x3.0',     section: 'rect',  dx: 60,   dia: 40,   wall: 3.0, kgm: 4.427 },
    { name: 'Rundrohr 42.4x2.0', section: 'round', dx: null, dia: 42.4, wall: 2.0, kgm: 1.993 },
    { name: 'Flachstahl 50x10',  section: 'flat',  dx: 50,   dia: 10,   wall: null, kgm: 3.925 },
    { name: 'Flachstahl 60x10',  section: 'flat',  dx: 60,   dia: 10,   wall: null, kgm: 4.710 },
    { name: 'Flachstahl 80x10',  section: 'flat',  dx: 80,   dia: 10,   wall: null, kgm: 6.280 },
  ],
  infill: [
    { name: 'Rundstahl 12',      section: 'round', dx: null, dia: 12,   wall: null, kgm: 0.888 },
    { name: 'Rundstahl 10',      section: 'round', dx: null, dia: 10,   wall: null, kgm: 0.617 },
    { name: 'Rundstahl 14',      section: 'round', dx: null, dia: 14,   wall: null, kgm: 1.208 },
    { name: 'Flachstahl 30x5',   section: 'flat',  dx: 30,   dia: 5,    wall: null, kgm: 1.178 },
    { name: 'Flachstahl 40x8',   section: 'flat',  dx: 40,   dia: 8,    wall: null, kgm: 2.512 },
    { name: 'Vierkant 12x12',    section: 'rect',  dx: 12,   dia: 12,   wall: null, kgm: 1.130 },
    { name: 'RHS 40x20x2.0',     section: 'rect',  dx: 40,   dia: 20,   wall: 2.0, kgm: 1.758 },
  ],
  // Untergurt = unterer Gurt, auf dem die Füllstäbe stehen — Strukturgurt, kein
  // Handlauf; der Katalog fuehrt daher Flachstahl / SHS an.
  untergurt: [
    { name: 'Flachstahl 40x10',  section: 'flat',  dx: 40,   dia: 10,   wall: null, kgm: 3.140 },
    { name: 'Flachstahl 50x10',  section: 'flat',  dx: 50,   dia: 10,   wall: null, kgm: 3.925 },
    { name: 'Flachstahl 60x10',  section: 'flat',  dx: 60,   dia: 10,   wall: null, kgm: 4.710 },
    { name: 'SHS 40x40x2.0',     section: 'rect',  dx: 40,   dia: 40,   wall: 2.0, kgm: 2.386 },
    { name: 'RHS 40x20x2.0',     section: 'rect',  dx: 40,   dia: 20,   wall: 2.0, kgm: 1.758 },
    { name: 'Rundrohr 33.7x2.0', section: 'round', dx: null, dia: 33.7, wall: 2.0, kgm: 1.564 },
    { name: 'Rundstahl 12',      section: 'round', dx: null, dia: 12,   wall: null, kgm: 0.888 },
  ],
};

// Index des Flachstahls 40x8 in `infill` — Standardprofil der Dekor-Diagonalen
export const DIAGONAL_INFILL_INDEX = 4;
