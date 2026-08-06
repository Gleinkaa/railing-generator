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

// organic.js — Musterfamilie "Organic" (Katalogindizes 10–15),
// 1:1 portiert aus `grasshopper/patterns.py`.
//
// ---------------------------------------------------------------------------
// Was diese Familie besonders macht
// ---------------------------------------------------------------------------
// Zwei der sechs Muster sind LASERBLECHE (`y.plate()` mit Aussparungsringen),
// nicht Stabwerk: die Aussenkontur ist das Feldrechteck, jede Aussparung ein
// weiterer Ring. Die Steg- und Randdeckel (BLECH_STEG, BLECH_RAND) sind
// Fertigungsgrenzen, keine Optik — ein Blech mit 8 mm Steg zwischen zwei
// Loechern verzieht sich beim Schneiden und ist Ausschuss.
//
// Drei der sechs Muster sind ZUFALLSMUSTER. Der Zufallsstrom ist POSITIONELL:
// jeder zusaetzliche oder fehlende `y.rnd.random()` / `y.rnd.randrange()`
// verschiebt alle folgenden Werte und liefert stillschweigend eine andere
// Geometrie als die Grasshopper-Engine — bei gleichem Seed, ohne Fehlermeldung.
// Reihenfolge und Anzahl der Zuege sind deshalb Teil des Vertrags, genau wie
// die Reihenfolge der Pushes in `y.a` / `y.b` / `y.st` / `y.hz`.

// Aus bay.js wird nichts gebraucht: keines der sechs Muster rundet, misst
// Winkel oder baut Geometrie ausserhalb der Bay-Methoden. `y` bringt alles mit.
// Der Ellipsenring liegt in shared.js, weil `lattice-diamond` (Familie Formed)
// dieselbe Formel benutzt — die Python-Engine hat dafuer genau eine Kopie.
import { ellipseLoop } from './shared.js';

// ------------------------------------------------------------------ Muster 10
/**
 * Segmented Panels — Holzsegmente, je Spalte 2 oder 3 gestapelt, getragen von
 * drei durchlaufenden Stahlriegeln.
 * (grasshopper/patterns.py:737-777)
 *
 * Kanaele: `b` (drei Riegel), `hz` (Holzsegmente).
 * ZUFALLSMUSTER — je Einheit ein `randrange(2)` und ein `random()`, in dieser
 * Reihenfolge.
 */
export function p_panel_segment(y, rap, P) {
  const [n, st] = y.units(rap);
  // K2 wie bei Staggered Panels, nur eine Stufe frueher: JEDES Segment braucht
  // einen Riegel, auf den es geschraubt wird ("je Segment 1 Schraube pro
  // Riegel"). Eine Spalte stapelt 2 ODER 3 Segmente. Mit nur zwei Riegeln
  // (0.25/0.75 H) bleibt fuer den Dreierstapel nach dem Schubfachschluss
  // zwangslaeufig ein Segment ohne Riegel uebrig — das mittlere schwebte
  // zwischen beiden. Es laesst sich auch durch Verschieben der Fugen nicht
  // heilen: drei disjunkte Segmente koennen nicht je einen von zwei Riegeln
  // enthalten. Deshalb ein Riegel je moeglicher Segmentlage. Der dritte auf
  // halber Hoehe traegt das Mittelsegment; bei Zweierstapeln liegt er innerhalb
  // der Segmente und stoert weder Optik noch Fuge. Die HOLZGEOMETRIE bleibt
  // unveraendert — weder Zufallsfolge noch Segmenthoehen aendern sich dadurch.
  const rails = [0.25 * y.H, 0.50 * y.H, 0.75 * y.H];
  for (const r of rails) {
    y.seg(0.0, r, y.L, r, 'b');
  }
  for (let i = 0; i < n; i++) {
    const segs = Math.min(2 + y.rnd.randrange(2), rails.length);
    const t0 = P.HOLZ_LUFT + y.rnd.random() * y.H * 0.06;
    const sh = (y.H - t0 - P.HOLZ_LUFT) / segs;
    // Segment k wird dem Riegel sel[k] zugeordnet: erstes Segment auf den
    // untersten, letztes auf den obersten Riegel, der Rest gleichmaessig
    // dazwischen. Bei 2 Segmenten sind das die beiden AEUSSEREN Riegel
    // (0.25/0.75 H) — genau die Zuordnung von vorher.
    const sel = [];
    for (let k = 0; k < segs; k++) {
      sel.push(rails[Math.floor(k * (rails.length - 1) / (segs - 1))]);
    }
    // Fugen der gleichmaessigen Segment-Teilung. Trifft die Teilung ihren
    // Riegel (bei allen praxisnahen Feldhoehen der Fall), bleibt sie
    // unangetastet; sonst wandert die Fuge MINIMAL in das zulaessige
    // Fenster — Staggered Panels schiebt den Block, hier wandert die Fuge,
    // damit die gleichmaessige Staffelung erhalten bleibt. HOLZ_LUFT Abstand,
    // weil die Blockkante um die halbe Fugenbreite hinter der Fuge zurueckliegt.
    const cut = [];
    for (let k = 0; k <= segs; k++) cut.push(t0 + k * sh);
    for (let k = 1; k < segs; k++) {
      const lo = sel[k - 1] + P.HOLZ_LUFT;
      const hi = sel[k] - P.HOLZ_LUFT;
      cut[k] = lo < hi ? Math.min(Math.max(cut[k], lo), hi) : 0.5 * (lo + hi);
    }
    cut[0] = Math.max(0.0, Math.min(cut[0], sel[0] - P.HOLZ_LUFT));
    cut[segs] = Math.min(y.H, Math.max(cut[segs], sel[segs - 1] + P.HOLZ_LUFT));
    for (let k = 0; k < segs; k++) {
      y.block(i * st + st * 0.12, cut[k] + P.HOLZ_LUFT / 2.0,
        i * st + st * 0.88, cut[k + 1] - P.HOLZ_LUFT / 2.0,
        P.HOLZ_D, 'hz', P.HOLZ_OFF);
    }
  }
}

// ------------------------------------------------------------------ Muster 11
/**
 * Ellipse Sheet — Laserblech ueber das ganze Feld, je Einheit eine elliptische
 * Aussparung auf halber Hoehe.
 * (grasshopper/patterns.py:785-798)
 *
 * Kanaele: `st` (genau ein Blech-Solid mit Aussenkontur + Loechern).
 * Nicht zufaellig.
 */
export function p_sheet_ellipse(y, rap, P) {
  const [n, st] = y.units(rap);
  const outer = [[0.0, 0.0], [y.L, 0.0], [y.L, y.H], [0.0, y.H]];
  const holes = [];
  for (let i = 0; i < n; i++) {
    const cs = st * (i + 0.5);
    // Deckel auch fuer den RANDABSTAND: BLECH_RAND galt bisher nur
    // vertikal — zur Feldkante blieben mit dem Default-Rapport nur 28 mm,
    // im schmalen Feld sogar nur BLECH_STEG/2.
    const rs = Math.min(st * 0.30, (st - P.BLECH_STEG) / 2.0, st / 2.0 - P.BLECH_RAND);
    const rt = Math.min(y.H * 0.38, (y.H - 2 * P.BLECH_RAND) / 2.0);
    if (rs > 5.0 && rt > 5.0) {
      holes.push(ellipseLoop(cs, y.H / 2.0, rs, rt));
    }
  }
  y.plate([outer, ...holes], P.BLECH_D, 'st');
}

// ------------------------------------------------------------------ Muster 12
/**
 * Random Rake — dichte Halme in unregelmaessiger Neigung, Fusspunkt am
 * Untergurt, Kopf am Handlauf.
 * (grasshopper/patterns.py:801-811)
 *
 * Kanaele: `a`.
 * ZUFALLSMUSTER — je Einheit genau zwei `random()`, in dieser Reihenfolge
 * (Fusspunkt zuerst, dann die Neigung).
 */
export function p_rake_random(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    // Stratifiziert statt global gleichverteilt: rein zufaellige Fusspunkte
    // liessen regelmaessig mehrere hundert mm breite Leerzonen entstehen
    // (sichtbar im Muster-Render, Feld 1). Jeder Halm wuerfelt jetzt nur
    // noch INNERHALB seiner Rapportzelle — Zufallscharakter und
    // Seed-Determinismus bleiben, die maximale Luecke ist ~2 Rapporte.
    const s0 = (i + y.rnd.random()) * st;
    const s1 = s0 + (y.rnd.random() - 0.35) * y.L * 0.22;
    y.seg(s0, 0.0, Math.max(0.0, Math.min(y.L, s1)), y.H, 'a');
  }
}

// ------------------------------------------------------------------ Muster 13
/**
 * Woven Bands — je Einheit zwei gegenlaeufige S-Boegen, die sich auf halber
 * Hoehe kreuzen; der Wechsel der Kanaele legt fest, welches Band vorne liegt.
 * (grasshopper/patterns.py:814-819)
 *
 * Kanaele: `a` (aufsteigendes Band), `b` (absteigendes Band).
 * Nicht zufaellig.
 */
export function p_weave_band(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    const s0 = i * st;
    y.bez([s0, 0.0], [s0 + st, y.H * 0.5], [s0, y.H * 0.5], [s0 + st, y.H], 'a');
    y.bez([s0, y.H], [s0 + st, y.H * 0.5], [s0, y.H * 0.5], [s0 + st, 0.0], 'b');
  }
}

// ------------------------------------------------------------------ Muster 14
/**
 * Grain Sheet — Laserblech mit unregelmaessig breiten, leicht ausgebauchten
 * Vertikalschlitzen (maserungsartig).
 * (grasshopper/patterns.py:822-847)
 *
 * Kanaele: `st` (genau ein Blech-Solid mit Aussenkontur + Loechern).
 * ZUFALLSMUSTER — je Einheit genau ein `random()`. Der Zug erfolgt VOR den
 * Steg-/Randdeckeln, also auch fuer Schlitze, die anschliessend verworfen
 * werden: die Verwerfung darf den Strom nicht verschieben.
 */
export function p_sheet_grain(y, rap, P) {
  const [n, st] = y.units(rap);
  const outer = [[0.0, 0.0], [y.L, 0.0], [y.L, y.H], [0.0, y.H]];
  const holes = [];
  for (let i = 0; i < n; i++) {
    let wl = st * (0.30 + y.rnd.random() * 0.35);
    const cs = st * (i + 0.5);
    // Steg- und Randpruefung auf die VOLLE Lochbreite inkl. Bulge
    // (Halbbreite = 0.5*wl + 0.22*wl = 0.72*wl). Vorher wurde nur die
    // nominelle Lochbreite gegen BLECH_STEG geprueft — zwei ausgebauchte
    // Nachbarloecher konnten sich auf ~8 mm Steg naehern, zur Feldkante
    // blieben im Extremfall 4 mm.
    wl = Math.min(wl, (st - P.BLECH_STEG) / 1.44);
    wl = Math.min(wl, (cs - P.BLECH_RAND) / 0.72, (y.L - cs - P.BLECH_RAND) / 0.72);
    if (wl < P.BLECH_STEG) {
      continue;
    }
    const k = 18;
    const left = [];
    const right = [];
    for (let j = 0; j <= k; j++) {
      const f = j / k;
      const t = P.BLECH_RAND + (y.H - 2 * P.BLECH_RAND) * f;
      const bulge = Math.sin(Math.PI * f) * wl * 0.22;
      left.push([cs - wl / 2.0 - bulge, t]);
      right.push([cs + wl / 2.0 + bulge, t]);
    }
    holes.push(left.concat(right.slice().reverse()));
  }
  y.plate([outer, ...holes], P.BLECH_D, 'st');
}

// ------------------------------------------------------------------ Muster 15
/**
 * Fine Crossings — schlanke Vertikalstaebe, davor kurze Diagonalkreuze.
 * (grasshopper/patterns.py:850-866)
 *
 * Kanaele: `a` (Vertikalstaebe), `b` (Diagonalen, um AUSLAGE vorgesetzt).
 * Nicht zufaellig.
 */
export function p_bar_cross_fine(y, rap, P) {
  const [n, st] = y.units(rap);
  for (let i = 0; i < n; i++) {
    y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a');
  }
  if (n === 1) {
    // Ein einzelner Stab ohne X widerspraeche dem Katalog ("Staebe mit
    // Diagonalkreuzungen") — ein Kreuz von Posten zu Posten.
    y.seg(0.0, 0.0, y.L, y.H, 'b', P.AUSLAGE);
    y.seg(y.L, 0.0, 0.0, y.H, 'b', P.AUSLAGE);
  }
  for (let i = 0; i < Math.max(n - 1, 0); i += 2) {
    // Bis n-1 statt n-2: mit n-2 blieb bei geradem n am Feldende eine
    // 1,5-Rapport-Zone ohne Diagonalkreuz (Render Feldende: nackte
    // Vertikalstaebe). Erst damit greift die min()-Klemme ueberhaupt —
    // das letzte X wird an den Posten gestaucht statt weggelassen.
    const s0 = st * (i + 0.5);
    y.seg(s0, 0.0, Math.min(s0 + 2 * st, y.L), y.H, 'b', P.AUSLAGE);
    y.seg(Math.min(s0 + 2 * st, y.L), 0.0, s0, y.H, 'b', P.AUSLAGE);
  }
}
