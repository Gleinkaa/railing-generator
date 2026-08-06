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

// params.js — die Fertigungs- und Normparameter, die jedes Muster braucht.
//
// In der Grasshopper-Engine sind das Eingaenge des Script-Bausteins: GH legt
// sie als Modul-Globals an, und `patterns.py` liest sie einfach als HOLZ_D,
// HOLZ_LUFT, ... Im Browser gibt es diesen Mechanismus nicht, also werden sie
// hier als EIN Objekt durchgereicht. Jede Musterfunktion hat deshalb die
// Signatur
//
//     p_<key>(y, rap, P)
//
// mit `y` = Bay (siehe bay.js), `rap` = gedehnter Rapport in mm, `P` = dieses
// Objekt. Das ist die einzige bewusste Abweichung von der 1:1-Portierung —
// Globals waeren hier ein Modulzustand, den zwei nebeneinander gerechnete
// Konfigurationen sich teilen wuerden.
//
// Die Defaults sind exakt die Fallbacks der Python-Engine (`_pos`/`_num`
// Aufrufe im Abschnitt "Ablauf"). Wer sie aendert, aendert die Referenzmassen.

/** Grad -> Radiant, wie `DEG` in der Python-Engine. */
export const DEG = Math.PI / 180.0;

export const DEFAULT_PARAMS = {
  HOLZ_D: 30.0,      // Holzdicke mm
  HOLZ_LUFT: 8.0,    // Luftspalt / Bodenabstand Holz mm
  BLECH_D: 4.0,      // Blechdicke mm
  BLECH_STEG: 25.0,  // min. Steg zwischen Aussparungen mm
  BLECH_RAND: 30.0,  // min. Randabstand Aussparung mm
  HOLZ_OFF: 12.0,    // Auslage Holz vor den Stahlriegel mm
  FLACH_D: 8.0,      // Dicke Flachstahl mit wechselnder Breite mm
  VIERKANT_W: 16.0,  // Kantenmass tordierter Vierkantstab mm
  AUSLAGE: 0.0,      // Vorsprung vorgesetzter Elemente mm
  GMAX: 120.0,       // groesste zulaessige lichte Weite mm (OIB 4.2.4)
  STABB: 12.0,       // Stabbreite des Fuellprofils mm
  UGURT: 100.0,      // Untergurt ueber Nosinglinie mm
  KWINK: 60.0,       // Grenzwinkel "begehbar" in Grad (OIB 4.2.3, Zone A)
};

/** Defaults mit Ueberschreibungen mischen — fehlende Schluessel bleiben Default. */
export function withParams(overrides) {
  return { ...DEFAULT_PARAMS, ...(overrides || {}) };
}
