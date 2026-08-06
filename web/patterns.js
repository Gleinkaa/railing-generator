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

// patterns.js — die Musterregistry: Metadatentabelle (34 Eintraege) + Dispatch.
//
// 1:1 portiert aus `grasshopper/patterns.py`: die Liste `DESIGNS`
// (Zeilen 91–393) und der Abschnitt "Ablauf" (Zeilen 1096–1210).
//
// ---------------------------------------------------------------------------
// Der Index IST der Vertrag
// ---------------------------------------------------------------------------
// `DESIGNS[i]` steht an derselben Position wie in der Grasshopper-Engine. Der
// Musterregler im .gh-Dokument, die Regressionstests und die eingefrorenen
// Referenzmassen haengen alle an dieser Zahl. Ein Eintrag darf deshalb NIE
// umsortiert, eingeschoben oder entfernt werden — nur ergaenzt (am Ende).
//
// ---------------------------------------------------------------------------
// Feldnamen
// ---------------------------------------------------------------------------
// Bewusste Entscheidung: die technischen Felder behalten ihre DEUTSCHEN Namen
// aus der Python-Engine (`rap`, `gap`, `gapf`, `profile`, `oben`, `unten`,
// `verb`, `sonder`, `zufall`, `norm`), damit sich Python- und JS-Tabelle Zeile
// fuer Zeile gegeneinander lesen lassen. Kein camelCase-Umbau, kein
// Uebersetzen — das waere eine Diff-Wueste ohne fachlichen Gewinn.
// Nur `description` ist neu und englisch, weil dieser Text in die Oberflaeche
// geht.
//
//   key    kebab-case Schluessel, zugleich Schluessel in BUILDERS.
//   name   Anzeigename.
//   fam    Familie: 'Formed' | 'Organic' | 'Rhythm' | 'Lines' (siehe FAMILIES).
//   description
//          Kurzbeschreibung fuer die Oberflaeche (englisch, ein Satz).
//   rap    Rapport = Wiederholeinheit in mm ueber die Feldbreite. Das Reststueck
//          am Feldende wird nie abgeschnitten: die Einheitenzahl wird gerundet
//          und der Rapport auf die tatsaechliche Feldbreite gedehnt/gestaucht
//          (siehe `Bay.units`).
//   gap    true  = die Oeffnungsweite dieses Musters wird direkt vom Rapport
//                  bestimmt -> Rapport wird auf Gmax + Stabbreite gedeckelt.
//          false = die Oeffnung entsteht aus der Musterform, nicht aus dem
//                  Rapport -> Deckelung waere wirkungslos, Bewertung steht in
//                  `norm`.
//   gapf   nur dort gesetzt, wo die groesste Oeffnung um einen bekannten Faktor
//          UEBER dem Rapport liegt; verschaerft den Deckel entsprechend.
//   norm   Bewertung nach OIB-Richtlinie 4, Ausgabe Mai 2023 (im Wortlaut
//          geprueft). Die beiden massgebenden Punkte:
//            4.2.4  Oeffnungen duerfen ZUMINDEST IN EINER RICHTUNG nicht
//                   groesser als 12 cm sein. Oesterreich prueft also KEINE
//                   120-mm-Kugel wie Deutschland, sondern eine
//                   Richtungsbedingung — ein 40 x 700 mm Schlitz ist konform.
//            4.2.3  Zwischen 15 cm und 60 cm ueber Stufenvorderkante duerfen
//                   keine horizontalen oder schraegen Elemente liegen, ausser
//                   sie springen nicht mehr als 3 cm vor, die Oeffnungen sind
//                   vertikal <= 2 cm, oder es ist ein Lochblech mit Loch
//                   Ø <= 4 cm. Einen Grenzwinkel nennt die Richtlinie NICHT —
//                   deshalb ist er ein Regler (KWINK), Default 60 deg nach
//                   Sachverstaendigenpraxis, 75 deg als konservative Variante.
//          OENORM B 5371:2021 ist kostenpflichtig und wurde nicht im Volltext
//          geprueft; bei Widerspruch gilt ohnehin die OIB-RL 4 (verbindlich
//          ueber die Bautechnikverordnungen der Laender).
//   profile
//          Ausgabekanal -> ['INFILL', 0-basierter Index in der Rollenliste des
//          Profilkatalogs]. Stab1 wird mit dem Fuellstab-Profil gesweept
//          (INFILL, Default 0), Stab2 mit dem Diagonal-Profil (INFILL, Default
//          DIAGONAL_INFILL_INDEX = 4). Stahl- und Holz-Solids werden ueber
//          Volumen x Dichte verwogen und haben deshalb GAR KEINE Profilzeile —
//          sie stehen mit `null` da statt mit einem erfundenen Index.
//          Eingetragen ist die Zeile, mit der die Engine den Kanal in der
//          Grundeinstellung baut; ein musterweiser Vorzugsquerschnitt ist in
//          der Engine nicht verdrahtet (die Profilregler gelten global) und
//          waere hier eine unbelegte Behauptung — siehe offene Werkstattfrage
//          shop-decision-6.
//   oben / unten / verb / sonder / zufall
//          Konstruktionsangaben: Anschluss oben, Anschluss unten, Verbindungen
//          untereinander, Sonderbauteile, Zufallsanteil. `null` heisst "nichts
//          eingetragen" — NICHT "unbekannt, wird schon passen".
//   status 'done'  oder  'open:<Verweis>'.
//          'open:detail-X.Y'      = offener Detailpunkt X.Y der Rework-Vorgaben.
//          'open:shop-decision-N' = offene Werkstattentscheidung Nr. N.
//          Wo die Python-Tabelle beide Verweise fuehrt, stehen sie hier durch
//          Komma getrennt hintereinander.
//          `open` heisst: die KONSTRUKTIONSFRAGE ist offen und darf nicht von
//          Agenten beantwortet werden — nicht, dass das Muster unzulaessig
//          waere. Die Normbewertung steht in `norm` und ist davon unabhaengig.
//
// Hinweis zur Portierung: an vier Stellen (Index 9, 21, 24, 28) benutzte der
// deutsche Konstruktionstext den frueheren Musternamen als Formwort. Dort steht
// jetzt der geometrische Begriff (Schlaufenbogen, Gittersteg, geschwungenes
// Band); die Aussage ist unveraendert.

import {
  p_loop_u, p_panel_stagger, p_ray_diamond, p_bar_bead, p_vee_pair,
  p_panel_slat, p_arch_stack, p_hook_j, p_lattice_diamond, p_loop_drop,
} from './patterns/formed.js';
import {
  p_panel_segment, p_sheet_ellipse, p_rake_random, p_weave_band,
  p_sheet_grain, p_bar_cross_fine,
} from './patterns/organic.js';
import {
  p_bar_wave, p_chevron_h, p_line_density, p_bar_width_wave, p_bar_alternate,
  p_grid_split, p_rake_cross, p_bar_scatter, p_wave_overlay,
} from './patterns/rhythm.js';
import {
  p_bar_graded, p_frame_u, p_bar_railed, p_flat_horizontal, p_hatch_45,
  p_bar_vertical, p_bar_twist, p_rake_uniform, p_vee_center,
} from './patterns/lines.js';
import { Bay } from './bay.js';
import { DEFAULT_PARAMS, withParams } from './patterns/params.js';

/** Die vier Familien in Indexreihenfolge — Gruppierung in der Oberflaeche. */
export const FAMILIES = ['Formed', 'Organic', 'Rhythm', 'Lines'];

/** Default-Muster der Engine, falls der Regler nichts Brauchbares liefert. */
export const DEFAULT_INDEX = 30; // grasshopper/patterns.py:1151 — Referenzfall

// --------------------------------------------------------------- Katalogdaten
export const DESIGNS = [
  // ------------------------------------------------------------------ Formed
  {
    key: 'loop-u', name: 'U-Loop', fam: 'Formed',
    description: 'Paired bars joined by a U-bend that seats on the bottom rail',
    rap: 120.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Schenkel stumpf an den Handlauf geschweisst',
    unten: 'U-Bogen liegt auf dem Untergurt auf, beidseitig verschweisst',
    verb: 'keine Kreuzungen — jede Schlaufe ist ein Bauteil aus Rundstahl gebogen',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: Bogenscheitel liegt waagrecht — Zone A pruefen (Kanal Norm).',
    status: 'open:detail-6.3',
  },
  {
    key: 'panel-stagger', name: 'Staggered Panels', fam: 'Formed',
    description: 'Offset timber blocks carried on steel rails, staggered per bay',
    rap: 100.0, gap: false,
    profile: { Stab2: ['INFILL', 4], Holz: null },
    oben: 'Holzbloecke enden frei — Last traegt der Stahlriegel',
    unten: '2 Flachstahlriegel spannen Posten zu Posten, Holz davor verschraubt',
    verb: 'Holz auf Riegel verschraubt (Langloch quer zur Faser)',
    sonder: 'Holz', zufall: 'seed + Feldindex, Blockhoehe 0.42..0.72*H',
    norm: 'OIB 4.2.3 kritisch: die versetzten Block-Oberkanten sind Trittkanten. Zulaessig nur ueber Vorsprung <= 30 mm.',
    status: 'open:shop-decision-5',
  },
  {
    key: 'ray-diamond', name: 'Ray Diamond', fam: 'Formed',
    description: 'Radiating bars inside diamond frames, fine and open',
    rap: 340.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Rautenspitze am Handlauf angeschweisst',
    unten: 'Rautenspitze am Untergurt angeschweisst',
    verb: 'Strahlen an den Rautenrahmen geschweisst, Rahmen an Nachbarraute',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 bedingt: Rautenfeld > 120 mm in beiden Richtungen. Strahlen unterteilen es nur teilweise.',
    status: 'done',
  },
  {
    key: 'bar-bead', name: 'Beaded Bars', fam: 'Formed',
    description: 'Vertical bars threaded with round discs at mid height',
    rap: 115.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Stab am Handlauf angeschweisst',
    unten: 'Stab am Untergurt angeschweisst',
    verb: 'Ringe auf die Staebe aufgeschoben und verschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. Ringe springen vor — 4.2.3 Vorsprung <= 30 mm pruefen.',
    status: 'done',
  },
  {
    key: 'vee-pair', name: 'Vee Pairs', fam: 'Formed',
    description: 'Alternating V-shaped bar pairs, apex down on the bottom rail',
    rap: 95.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'beide Schenkelenden am Handlauf',
    unten: 'Scheitel auf dem Untergurt',
    verb: 'Scheitel gebogen, keine Schweissnaht in der Spitze',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: Schenkel praktisch lotrecht (>80 deg bei ueblichen Feldern, Horizontalprojektion max. halber Rapport) — Zone A unkritisch, solange steiler als Kw.',
    status: 'done',
  },
  {
    key: 'panel-slat', name: 'Wide Slats', fam: 'Formed',
    description: 'Broad timber lamellas held in a steel frame, narrow joints',
    rap: 140.0, gap: false,
    profile: { Stab2: ['INFILL', 4], Holz: null },
    oben: 'Holzlamelle endet frei unter dem Handlauf',
    unten: '2 Flachstahlriegel tragen, Holz davor verschraubt',
    verb: 'Holz auf Riegel verschraubt (Langloch quer zur Faser)',
    sonder: 'Holz', zufall: null,
    norm: 'OIB 4.2.4 konform (geschlossene Flaeche, Fuge 8-12 mm). 4.2.3 unkritisch, da durchgehend vertikal.',
    status: 'open:shop-decision-5',
  },
  {
    key: 'arch-stack', name: 'Stacked Arches', fam: 'Formed',
    description: 'Two rows of arches divided by an intermediate rail',
    rap: 155.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'grosse Boegen am Handlauf',
    unten: 'kleine Boegen auf dem Untergurt',
    verb: 'Zwischenriegel spannt Posten zu Posten, Boegen beidseitig angeschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 bedingt: Bogenfelder > 120 mm. 4.2.3: Bogenscheitel waagrecht — Zone A pruefen.',
    status: 'open:detail-6.3',
  },
  {
    key: 'hook-j', name: 'J-Hooks', fam: 'Formed',
    description: 'Bars bent into a J, the arched foot resting on the bottom rail',
    rap: 135.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'langer Schenkel am Handlauf, Rueckläufer endet am Zwischenriegel',
    unten: 'U-Bogen liegt auf dem Untergurt auf',
    verb: 'J-Haken aus einem Stueck gebogen; Rueckläufer an den Zwischenriegel geschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: U-Bogen unten liegt meist unter 150 mm — pruefen.',
    status: 'open:detail-6.3',
  },
  {
    key: 'lattice-diamond', name: 'Diamond Lattice', fam: 'Formed',
    description: 'Diamond grid with disc accents at the crossings',
    rap: 210.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Holz: null },
    oben: 'Rautenspitze am Handlauf',
    unten: 'Rautenspitze am Untergurt, Aussenspitzen an den Posten',
    verb: 'Rauten an den Spitzen miteinander, mit den Gurten und den Posten verschweisst — keine Stabkreuzungen',
    sonder: 'Holz (nur Scheiben-Akzente)', zufall: null,
    norm: 'OIB 4.2.3 direkter Treffer (schraege Elemente + vorspringende Scheiben). Nur mit Vorsprung <= 30 mm oder Raute erst ab 600 mm.',
    status: 'open:shop-decision-3',
  },
  {
    key: 'loop-drop', name: 'Loop and Drop', fam: 'Formed',
    description: 'Wide bottom loops carrying a teardrop stem to the handrail',
    rap: 180.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Tropfen-Stiel am Handlauf',
    unten: 'Schlaufenschenkel auf dem Untergurt',
    verb: 'Tropfenspitze auf den Schlaufenbogen geschweisst — beide Teile haengen zusammen',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 bedingt: der Schlaufenbogen bildet eine Oeffnung > 120 mm. 4.2.3: Bogenscheitel waagrecht.',
    status: 'open:detail-6.3',
  },
  // ----------------------------------------------------------------- Organic
  {
    key: 'panel-segment', name: 'Segmented Panels', fam: 'Organic',
    description: 'Timber segments stacked in two or three per column on three rails',
    rap: 85.0, gap: false,
    profile: { Stab2: ['INFILL', 4], Holz: null },
    oben: 'oberstes Segment endet frei unter dem Handlauf',
    unten: '3 Flachstahlriegel (0,25/0,50/0,75 H) tragen, Holzsegmente davor '
      + 'verschraubt — der mittlere traegt das Mittelsegment der Dreierstapel',
    verb: 'je Segment 1 Schraube pro Riegel, Fuge zwischen den Segmenten',
    sonder: 'Holz', zufall: 'seed + Feldindex, 2..3 Segmente je Spalte',
    norm: 'OIB 4.2.3: jede Stapelfuge ist eine horizontale Trittkante. Segmentdicke <= 30 mm oder Fugen ausserhalb 150-600 mm.',
    status: 'open:shop-decision-5',
  },
  {
    key: 'sheet-ellipse', name: 'Ellipse Sheet', fam: 'Organic',
    description: 'Laser-cut sheet with elliptical voids, edges captured in channel',
    rap: 140.0, gap: false,
    profile: { Stahl: null },
    oben: 'Blechkante in U-Profil am Handlauf gefasst',
    unten: 'Blechkante in U-Profil am Untergurt gefasst',
    verb: 'Blech lasergeschnitten, umlaufend eingefasst — keine Stabkreuzungen',
    sonder: 'Laserblech', zufall: null,
    norm: 'OIB 4.2.4: Nebenachse <= 120 mm. In Zone A normgedeckt nur, wenn der Ausschnitt in einen Kreis Ø 40 mm passt (Lochblech-Ausnahme).',
    status: 'open:shop-decision-4',
  },
  {
    key: 'rake-random', name: 'Random Rake', fam: 'Organic',
    description: 'Densely raked bars at irregular angles, seeded per bay',
    rap: 45.0, gap: false,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'jeder Halm am Handlauf angeschweisst',
    unten: 'jeder Halm am Untergurt angeschweisst',
    verb: 'Halme kreuzen sich frei, Kreuzungen nicht verbunden',
    sonder: null, zufall: 'seed + Feldindex, Fusspunkt und Neigung je Halm',
    norm: 'OIB 4.2.3: geneigte Halme. Zone A nur zulaessig, wenn steiler als die eingestellte Winkelgrenze.',
    status: 'open:shop-decision-1',
  },
  {
    key: 'weave-band', name: 'Woven Bands', fam: 'Organic',
    description: 'Curved diagonal bands crossing over and under each other',
    rap: 125.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'beide Bandrichtungen am Handlauf',
    unten: 'beide Bandrichtungen am Untergurt',
    verb: 'Baender kreuzen mittig, an der Kreuzung verschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4: Maschen zwischen den Baendern pruefen. 4.2.3: Bandtangente wird in Zone A flach.',
    status: 'done',
  },
  {
    key: 'sheet-grain', name: 'Grain Sheet', fam: 'Organic',
    description: 'Laser-cut sheet with irregular vertical strips, grain-like',
    rap: 125.0, gap: false,
    profile: { Stahl: null },
    oben: 'Blechkante in U-Profil am Handlauf gefasst',
    unten: 'Blechkante in U-Profil am Untergurt gefasst',
    verb: 'Blech lasergeschnitten, umlaufend eingefasst',
    sonder: 'Laserblech', zufall: 'seed + Feldindex, Streifenbreite',
    norm: 'OIB 4.2.4 guenstigste Blechvariante (Richtungsbedingung, Streifen durchlaufend vertikal). 4.2.3: keine Schlitzenden zwischen 150 und 600 mm.',
    status: 'done',
  },
  {
    key: 'bar-cross-fine', name: 'Fine Crossings', fam: 'Organic',
    description: 'Slim verticals overlaid with short diagonal crossings',
    rap: 80.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Staebe und Diagonalen am Handlauf',
    unten: 'Staebe und Diagonalen am Untergurt',
    verb: 'Diagonalen vor die Staebe gesetzt und an den Kreuzungen geheftet',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform ueber das Vertikalfeld. 4.2.3: die Diagonalen liegen in Zone A — Vorsprung <= 30 mm.',
    status: 'done',
  },
  // ------------------------------------------------------------------ Rhythm
  {
    key: 'bar-wave', name: 'Wave Bars', fam: 'Rhythm',
    description: 'Vertical bars displaced along a sine, one wavelength per bay',
    rap: 95.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Stabende am Handlauf, Tangente annaehernd lotrecht (Bezier, < 10 deg)',
    unten: 'Stabende am Untergurt, Tangente annaehernd lotrecht (Bezier, < 10 deg)',
    verb: 'keine Kreuzungen — jeder Stab ein Bauteil, kalt gebogen',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. Tangente bleibt ueberall steil.',
    status: 'done',
  },
  {
    key: 'chevron-h', name: 'Horizontal Chevron', fam: 'Rhythm',
    description: 'Stacked horizontal chevrons, apex alternating left and right',
    rap: 185.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'oberste Zackenreihe endet am Handlauf',
    unten: 'unterste Zackenreihe endet am Untergurt',
    verb: 'jede Reihe spannt durchlaufend von Posten zu Posten',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3 kritisch: Zackenreihen wirken waagrecht. In Zone A lichter Spalt <= 20 mm noetig.',
    status: 'done',
  },
  {
    key: 'line-density', name: 'Density Lines', fam: 'Rhythm',
    description: 'Fine verticals whose spacing tightens and opens across the bay',
    rap: 40.0, gap: true, gapf: 0.78,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Stab am Handlauf',
    unten: 'Stab am Untergurt',
    verb: 'keine Kreuzungen',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4: Dichte-Modulation schwankt um +-28 % — massgebend ist die WEITESTE Oeffnung; der Rapport-Deckel ist dafuer um Faktor 0.78 verschaerft (gapf).',
    status: 'done',
  },
  {
    key: 'bar-width-wave', name: 'Width Wave', fam: 'Rhythm',
    description: 'Bars whose width swells and shrinks along a wave',
    rap: 70.0, gap: true,
    profile: { Stahl: null },
    oben: 'Flachstahl am Handlauf',
    unten: 'Flachstahl am Untergurt',
    verb: 'keine Kreuzungen — Breite variiert, Dicke konstant',
    sonder: 'Flachstahl mit wechselnder Breite (Laserzuschnitt)', zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
    status: 'done',
  },
  {
    key: 'bar-alternate', name: 'Alternating Bars', fam: 'Rhythm',
    description: 'Wide and narrow bars alternating in a fixed ratio',
    rap: 100.0, gap: true,
    profile: { Stahl: null },
    oben: 'Flachstahl am Handlauf',
    unten: 'Flachstahl am Untergurt',
    verb: 'keine Kreuzungen — 2 Breiten im Wechsel',
    sonder: 'Flachstahl, 2 Breiten', zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
    status: 'done',
  },
  {
    key: 'grid-split', name: 'Split Grid', fam: 'Rhythm',
    description: 'Rectangular modules, each divided by one diagonal',
    rap: 220.0, gap: false,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Gitterstege am Handlauf',
    unten: 'Gitterstege am Untergurt',
    verb: 'Gitterknoten halb ueberblattet, Diagonalen eingeschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: waagrechte Gitterstege und Diagonalen duerfen nicht in 150-600 mm liegen. Teilung entsprechend waehlen.',
    status: 'done',
  },
  {
    key: 'rake-cross', name: 'Crossed Rakes', fam: 'Rhythm',
    description: 'Two opposed rakes of bars crossing between the rails',
    rap: 90.0, gap: false,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Kopf jedes Stabs am Handlauf',
    unten: 'Fuss jedes Stabs am Untergurt',
    verb: 'Kreuzungen nicht verbunden — Staebe liegen in einer Ebene versetzt',
    sonder: null, zufall: 'seed + Feldindex, Kopfversatz je Stab, +-1.6 Rapport',
    norm: 'OIB 4.2.3: geneigte Staebe. Zone A nur, wenn steiler als die Winkelgrenze.',
    status: 'open:detail-6.6, shop-decision-1',
  },
  {
    key: 'bar-scatter', name: 'Scattered Diagonals', fam: 'Rhythm',
    description: 'Even verticals with diagonals scattered between them',
    rap: 100.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Staebe und Diagonalen am Handlauf',
    unten: 'Staebe und Diagonalen am Untergurt',
    verb: 'Diagonalen vorgesetzt, an Kreuzungen geheftet',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform ueber das Vertikalfeld. 4.2.3: Diagonalen aus Zone A heraushalten oder Vorsprung <= 30 mm.',
    status: 'done',
  },
  {
    key: 'wave-overlay', name: 'Wave Overlay', fam: 'Rhythm',
    description: 'Straight bar field with wave bands set in front of it',
    rap: 60.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Staebe am Handlauf',
    unten: 'Staebe am Untergurt',
    verb: 'geschwungene Baender aus Flachstahl VORGESETZT (Auslage), an jedem Kreuzungsstab geheftet',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3 kritisch: die vorgesetzten Baender sind waagrecht UND springen um die Auslage vor. Auslage <= 30 mm halten.',
    status: 'done',
  },
  // ------------------------------------------------------------------- Lines
  {
    key: 'bar-graded', name: 'Graded Bars', fam: 'Lines',
    description: 'Vertical bars stepping through several thicknesses',
    rap: 85.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'alle Staebe am Handlauf',
    unten: 'alle Staebe am Untergurt',
    verb: 'keine Kreuzungen — jeder 3. Stab im staerkeren Profil',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
    status: 'open:detail-6.6',
  },
  {
    key: 'frame-u', name: 'U-Frames', fam: 'Lines',
    description: 'Open U-frames standing side by side on the bottom rail',
    rap: 140.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'beide Schenkel am Handlauf',
    unten: 'Querstueck liegt auf dem Untergurt auf',
    verb: 'U aus einem Stueck gekantet, Querstueck auf den Untergurt geschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: das Querstueck liegt auf dem Untergurt, meist unter 150 mm — pruefen.',
    status: 'done',
  },
  {
    key: 'bar-railed', name: 'Railed Bars', fam: 'Lines',
    description: 'Vertical bars articulated by horizontal cross rails',
    rap: 90.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'Staebe am Handlauf',
    unten: 'Staebe am Untergurt',
    verb: '2 Querriegel durchlaufend von Posten zu Posten, Staebe daran geheftet',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: die 2 Querriegel sind waagrecht. Mindestens einer liegt typisch in Zone A — Lage pruefen.',
    status: 'done',
  },
  {
    key: 'flat-horizontal', name: 'Horizontal Flats', fam: 'Lines',
    description: 'Horizontal flat sections carried by intermediate posts',
    rap: 175.0, gap: true,
    profile: { Stab1: ['INFILL', 0], Stab2: ['INFILL', 4] },
    oben: 'oberstes Flachprofil unter dem Handlauf',
    unten: 'unterstes Flachprofil ueber dem Untergurt',
    verb: 'Flachprofile an Posten und Zwischenpfosten geschweisst',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3 praktisch K.O.: reine Horizontalteilung. In Zone A waere lichter Spalt <= 20 mm noetig — damit ist es dieses Muster nicht mehr.',
    status: 'open:detail-6.6, shop-decision-2',
  },
  {
    key: 'hatch-45', name: '45 Degree Hatch', fam: 'Lines',
    description: 'Dense uniform hatch at 45 degrees, louvre-like',
    rap: 70.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Schraffurenden am Handlauf oder am Posten',
    unten: 'Schraffurenden am Untergurt oder am Posten',
    verb: 'keine Kreuzungen — einseitige 45deg-Schar',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: 45-deg-Schar = Leitersprossen. In Zone A unzulaessig ohne Zusatzmassnahme.',
    status: 'done',
  },
  {
    key: 'bar-vertical', name: 'Vertical Bars', fam: 'Lines',
    description: 'Evenly spaced vertical bars, the reference infill',
    rap: 110.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Stab am Handlauf',
    unten: 'Stab am Untergurt',
    verb: 'keine Kreuzungen',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.4 konform (Referenzfall), lichte Weite <= Gmax. 4.2.3 unkritisch.',
    status: 'done',
  },
  {
    key: 'bar-twist', name: 'Twisted Bars', fam: 'Lines',
    description: 'Square bars twisted about their own axis',
    rap: 120.0, gap: true,
    profile: { Stahl: null },
    oben: 'Stab am Handlauf',
    unten: 'Stab am Untergurt',
    verb: 'keine Kreuzungen — Vierkantstab um die eigene Achse tordiert',
    sonder: 'tordierter Vierkantstab (Sonderfertigung)', zufall: null,
    norm: 'OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3 unkritisch, durchgehend vertikal.',
    status: 'done',
  },
  {
    key: 'rake-uniform', name: 'Uniform Rake', fam: 'Lines',
    description: 'Fine bars raked at one constant angle',
    rap: 80.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'Diagonalende am Handlauf oder am Posten',
    unten: 'Diagonalende am Untergurt oder am Posten',
    verb: 'keine Kreuzungen — einheitliche Neigung',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: einheitliche Neigung. Zone A nur, wenn steiler als die Winkelgrenze.',
    status: 'open:shop-decision-1',
  },
  {
    key: 'vee-center', name: 'Centre Vee', fam: 'Lines',
    description: 'Vertical bars kinked into a shallow V at mid height',
    rap: 95.0, gap: true,
    profile: { Stab1: ['INFILL', 0] },
    oben: 'oberer Schenkel am Handlauf',
    unten: 'unterer Schenkel am Untergurt',
    verb: 'Knick auf halber Hoehe, aus einem Stueck gekantet',
    sonder: null, zufall: null,
    norm: 'OIB 4.2.3: die Knickpunkte liegen alle auf halber Hoehe und bilden eine Reihe. Lage gegen Zone A pruefen.',
    status: 'open:detail-6.3',
  },
];

// -------------------------------------------------------------------- Dispatch
// Schluessel -> Bauroutine. Gegenstueck zu `BUILDERS` in grasshopper/patterns.py:
// die Tabelle ist die EINZIGE Stelle, an der ein Muster mit seiner Geometrie
// verdrahtet wird. `assertRegistry()` prueft, dass keine Zeile fehlt.
export const BUILDERS = {
  'loop-u': p_loop_u,
  'panel-stagger': p_panel_stagger,
  'ray-diamond': p_ray_diamond,
  'bar-bead': p_bar_bead,
  'vee-pair': p_vee_pair,
  'panel-slat': p_panel_slat,
  'arch-stack': p_arch_stack,
  'hook-j': p_hook_j,
  'lattice-diamond': p_lattice_diamond,
  'loop-drop': p_loop_drop,
  'panel-segment': p_panel_segment,
  'sheet-ellipse': p_sheet_ellipse,
  'rake-random': p_rake_random,
  'weave-band': p_weave_band,
  'sheet-grain': p_sheet_grain,
  'bar-cross-fine': p_bar_cross_fine,
  'bar-wave': p_bar_wave,
  'chevron-h': p_chevron_h,
  'line-density': p_line_density,
  'bar-width-wave': p_bar_width_wave,
  'bar-alternate': p_bar_alternate,
  'grid-split': p_grid_split,
  'rake-cross': p_rake_cross,
  'bar-scatter': p_bar_scatter,
  'wave-overlay': p_wave_overlay,
  'bar-graded': p_bar_graded,
  'frame-u': p_frame_u,
  'bar-railed': p_bar_railed,
  'flat-horizontal': p_flat_horizontal,
  'hatch-45': p_hatch_45,
  'bar-vertical': p_bar_vertical,
  'bar-twist': p_bar_twist,
  'rake-uniform': p_rake_uniform,
  'vee-center': p_vee_center,
};

// ------------------------------------------------------------------ Eingaenge
/**
 * Zahl vom Eingang — 0 IST ein gueltiger Wert (grasshopper/patterns.py:1099).
 *
 * In der Grasshopper-Engine stand hier einmal `return f if f > 0 else fallback`.
 * Das hat JEDE Null als "nicht angeschlossen" gelesen: Muster 0 war damit
 * unerreichbar, der Regler stand auf 0 und die Engine baute stumm Muster 30.
 * Nichts hat gewarnt — der Regler zeigte 0, die Geometrie war gueltig, nur
 * eben die falsche. In JavaScript waere `index || 30` genau derselbe Fehler.
 */
function _num(v, fallback) {
  if (v === null || v === undefined) return fallback;
  if (typeof v === 'string' && v.trim() === '') return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Wie `_num`, aber fuer Masse, die zwingend > 0 sein muessen (Dicken, Breiten,
 * Rapport-Faktoren). Hier IST 0 sinnlos und wird zum Default.
 * (grasshopper/patterns.py:1115)
 */
function _pos(v, fallback) {
  const f = _num(v, fallback);
  return f > 0 ? f : fallback;
}

/**
 * Reglerwert -> gueltiger Musterindex (grasshopper/patterns.py:1151-1152).
 *
 * ACHTUNG: die Klammerung `_num(...)` vor dem Clampen ist Absicht. Nur ein
 * NICHT interpretierbarer Eingang faellt auf `fallback` zurueck; eine echte 0
 * bleibt 0. Kein `index || DEFAULT_INDEX` — siehe `_num`.
 */
export function clampIndex(index, fallback = DEFAULT_INDEX) {
  const n = Math.trunc(_num(index, fallback));
  return Math.max(0, Math.min(DESIGNS.length - 1, n));
}

// ------------------------------------------------------------------- Rapport
/**
 * Gedehnter Rapport eines Musters (grasshopper/patterns.py:1169-1183).
 *
 * Abgeleitete Deckelung statt Slider-Grenze: der Rapport darf nie so gross
 * werden, dass die LICHTE Weite Gmax ueberschreitet. Gleiche Logik wie der
 * bestehende Diagonal-Deckel — die Grenze haengt am MUSTER, nicht am Regler,
 * damit ein weit aufgezogener Regler kein unzulaessiges Feld ausliefern kann.
 * gapf: Muster, deren groesste Oeffnung um einen bekannten Faktor UEBER dem
 * Rapport liegt (Dichte-Modulation +28 %), verschaerfen den Deckel
 * entsprechend — sonst garantiert er die 4.2.4-Konformitaet gerade nicht.
 *
 * @param {object} design  Eintrag aus DESIGNS
 * @param {number} density Dichteregler (Python `_pos(Dc, 1.0)`: 0 ist sinnlos)
 * @param {object} P       Parameter aus params.js (GMAX, STABB)
 * @returns {{rap: number, clamped: boolean}} clamped = der Deckel hat gegriffen
 */
export function rapportFor(design, density = 1.0, P = DEFAULT_PARAMS) {
  const dichte = _pos(density, 1.0);
  let rap = design.rap * dichte;
  let clamped = false;
  if (design.gap) {
    const cap = (P.GMAX + P.STABB) * (design.gapf ?? 1.0);
    if (rap > cap) {
      rap = cap;
      clamped = true;
    }
  }
  return { rap, clamped };
}

// ---------------------------------------------------------------------- Seed
/**
 * Seed eines Feldes (grasshopper/patterns.py:1197: `seed0 + idx * 977 + i * 131`).
 *
 * Die beiden Primzahlen sind Teil des Vertrags, nicht Geschmackssache: sie
 * halten die Zufallsmuster ueber Muster- und Feldwechsel hinweg auseinander,
 * und JEDE Abweichung liefert eine andere Geometrie als die Grasshopper-Engine
 * — bei identischen Eingaben, ohne Fehlermeldung.
 */
export function seedFor(baseSeed, patternIndex, bayIndex) {
  return baseSeed + patternIndex * 977 + bayIndex * 131;
}

// -------------------------------------------------------------------- Aufbau
/**
 * Ein Muster ueber alle Felder bauen — Gegenstueck zur Hauptschleife der
 * Python-Engine (grasshopper/patterns.py:1194-1208).
 *
 * @param {number} index  Musterindex 0..33 (0 ist gueltig!)
 * @param {Array<{lo: object, hi: object}>} bays
 *        Feldweise Kurvenpaare: `lo` = Untergurtsegment, `hi` = Handlaufsegment.
 *        Beide muessen an denselben Postenparametern geschattert sein — in der
 *        Python-Engine sind das zwei getrennte Listen, deren Laengen dort hart
 *        geprueft werden; hier erzwingt das Paar die Zuordnung schon strukturell.
 * @param {object} [opts]
 * @param {number[]} [opts.normal]  Aussennormale, Default [0, 1, 0]
 * @param {number}   [opts.seed]    Basis-Seed, Default 1
 * @param {number}   [opts.density] Dichteregler, Default 1.0
 * @param {object}   [opts.params]  Ueberschreibungen zu DEFAULT_PARAMS
 * @returns {{design: object, rap: number, clamped: boolean, bays: Bay[],
 *            a: object[], b: object[], st: object[], hz: object[]}}
 *          a/b/st/hz sind die Kanaele ALLER Felder, in Feldreihenfolge
 *          aneinandergehaengt — genau die Reihenfolge, gegen die Stueckliste
 *          und Regressionstests positionsweise vergleichen.
 */
export function buildPattern(index, bays, opts = {}) {
  const idx = clampIndex(index);
  const design = DESIGNS[idx];

  const P = withParams(opts.params);
  const normal = opts.normal || [0, 1, 0];
  const seed0 = Math.trunc(_num(opts.seed, 1));
  const { rap, clamped } = rapportFor(design, _pos(opts.density, 1.0), P);

  const build = BUILDERS[design.key];
  if (typeof build !== 'function') {
    throw new TypeError(`Kein Builder fuer Muster "${design.key}" (Index ${idx})`);
  }

  const out = { design, rap, clamped, bays: [], a: [], b: [], st: [], hz: [] };
  const list = bays || [];
  for (let i = 0; i < list.length; i++) {
    const pair = list[i];
    if (!pair || !pair.lo || !pair.hi) {
      // Stillschweigend ueberspringen waere genau die Fehlerklasse, die dieses
      // Modell schon zweimal gruen durchlaufen hat: ein fehlendes Feld faellt
      // in der Ansicht nicht auf, in der Stueckliste sofort.
      throw new TypeError(`Feld ${i}: lo/hi fehlen — Untergurt und Handlauf muessen `
        + 'an denselben Postenparametern geschattert sein');
    }
    const y = new Bay(pair.lo, pair.hi, normal, seedFor(seed0, idx, i));
    build(y, rap, P);
    out.bays.push(y);
    out.a.push(...y.a);
    out.b.push(...y.b);
    out.st.push(...y.st);
    out.hz.push(...y.hz);
  }
  return out;
}

// ------------------------------------------------------------------- Pruefung
/**
 * Selbsttest der Registry. Absichtlich hier und nicht nur im Testordner: eine
 * halb verdrahtete Tabelle soll beim ersten Aufruf knallen, nicht stumm ein
 * falsches Muster bauen.
 */
export function assertRegistry() {
  if (DESIGNS.length !== 34) {
    throw new Error(`DESIGNS: ${DESIGNS.length} Eintraege, erwartet 34`);
  }
  const seen = new Set();
  DESIGNS.forEach((d, i) => {
    if (seen.has(d.key)) throw new Error(`Doppelter Schluessel "${d.key}" bei Index ${i}`);
    seen.add(d.key);
    if (!FAMILIES.includes(d.fam)) throw new Error(`Index ${i}: unbekannte Familie "${d.fam}"`);
    if (!(d.key in BUILDERS)) throw new Error(`Index ${i}: "${d.key}" fehlt in BUILDERS`);
  });
  Object.keys(BUILDERS).forEach((k) => {
    if (!seen.has(k)) throw new Error(`BUILDERS kennt "${k}", DESIGNS nicht`);
  });
  return true;
}
