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

// Tests fuer web/bay.js — die Portierung von `class Bay`
// (grasshopper/patterns.py:271-418).
//
// Zwei Referenz-Felder ziehen sich durch die ganze Datei:
//
//   FLAT    Untergurt waagrecht -> Xh, Yh, Nh sind ORTHONORMAL, P(s,t,off) ist
//           schlicht (s, off, t). Alles hier ist von Hand nachrechenbar.
//   STEIL   Untergurt (0,0,100) -> (1000,0,2100), also Steigung 2:1. Damit ist
//           Xh.Yh = 0.894427... und die Basis DEUTLICH schiefwinklig. Erwartete
//           Werte stammen entweder aus geschlossener Formel oder aus einer
//           unabhaengigen Python-Rechnung (im jeweiligen Kommentar vermerkt).
//
// Jede Toleranz steht ausgeschrieben am Assert. `0` heisst: exakte Gleichheit
// wird verlangt.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  Bay, PyRandom, TOL, pyRound,
  arc3, line, bezier, polyline,
  curveStart, curveEnd, curveLength, curvePointAt, curveTangentAt,
  polygonArea, solidVolume,
  sub3, dot3, cross3, len3, dist3, unit3,
} from '../bay.js';

// ------------------------------------------------------------------ Helfer
/** Vergleich mit AUSGESCHRIEBENER Toleranz — tol ist Pflichtparameter. */
function close(actual, expected, tol, msg) {
  assert.ok(Number.isFinite(actual), `${msg}: ${actual} ist keine Zahl`);
  assert.ok(Math.abs(actual - expected) <= tol,
    `${msg}: ${actual} != ${expected} (Toleranz ${tol}, Abweichung ${Math.abs(actual - expected)})`);
}

function closePt(actual, expected, tol, msg) {
  for (let i = 0; i < 3; i++) close(actual[i], expected[i], tol, `${msg}[${i}]`);
}

const flatBay = (seed = 1) =>
  new Bay({ a: [0, 0, 0], b: [1000, 0, 0] }, { a: [0, 0, 900], b: [1000, 0, 900] }, [0, 1, 0], seed);

// Steigung 2:1 -> L = 1000*sqrt(5), H = 1000, k = Xh.Yh = 2/sqrt(5)
const steepBay = (seed = 1) =>
  new Bay({ a: [0, 0, 100], b: [1000, 0, 2100] }, { a: [0, 0, 1100], b: [1000, 0, 3100] }, [0, 1, 0], seed);

const L_STEEP = 1000 * Math.sqrt(5);      // 2236.06797749979
const K_STEEP = 2 / Math.sqrt(5);         // 0.8944271909999159
const SIN_STEEP = Math.sqrt(1 - K_STEEP ** 2); // 1/sqrt(5) = 0.4472135954999579

/** Die FALSCHE Umkehrung: nacktes Skalarprodukt statt Gram-Inverse. */
const naiveStOf = (bay, p) => {
  const d = sub3(p, bay.O);
  return [dot3(d, bay.Xh), dot3(d, bay.Yh)];
};

// =========================================================== Feld und Basis
test('Konstruktor uebernimmt O, L, H und unitisiert Xh/Yh/Nh', () => {
  const y = steepBay();
  closePt(y.O, [0, 0, 100], 0, 'O ist der Startpunkt des Untergurts');
  close(y.L, L_STEEP, 1e-9, 'L = Laenge des Untergurt-Segments');
  close(y.H, 1000, 1e-12, 'H = Abstand Untergurt -> Handlauf');
  closePt(y.Xh, [1 / Math.sqrt(5), 0, 2 / Math.sqrt(5)], 1e-15, 'Xh folgt der Steigung');
  closePt(y.Yh, [0, 0, 1], 0, 'Yh ist lotrecht');
  closePt(y.Nh, [0, 1, 0], 0, 'Nh zeigt nach aussen');
  close(len3(y.Xh), 1, 1e-15, '|Xh|');
  close(len3(y.Yh), 1, 0, '|Yh|');
  // DAS ist der springende Punkt: die Basis ist schiefwinklig.
  close(dot3(y.Xh, y.Yh), K_STEEP, 1e-15, 'Xh.Yh darf NICHT 0 sein');
  assert.ok(Math.abs(dot3(y.Xh, y.Yh)) > 0.5,
    'Testfeld muss deutlich schiefwinklig sein, sonst hat der Round-Trip-Test keine Zaehne');
});

test('P() ist O + Xh*s + Yh*t + Nh*off', () => {
  const f = flatBay();
  // FLAT ist orthonormal: P(s,t,off) == (s, off, t), exakt.
  closePt(f.P(0, 0), [0, 0, 0], 0, 'P(0,0)');
  closePt(f.P(250, 400), [250, 0, 400], 0, 'P(250,400)');
  closePt(f.P(250, 400, 40), [250, 40, 400], 0, 'P mit Auslage');

  const y = steepBay();
  // Von Hand: O + Xh*500 + Yh*300 = (0,0,100) + (500/sqrt5)*(1,0,2) + (0,0,300)
  closePt(y.P(500, 300), [500 / Math.sqrt(5), 0, 100 + 1000 / Math.sqrt(5) + 300], 1e-9, 'P(500,300)');
  closePt(y.P(500, 300, 40), [500 / Math.sqrt(5), 40, 100 + 1000 / Math.sqrt(5) + 300], 1e-9,
    'Auslage laeuft rein entlang Nh');
});

// ================================================== DIE Falle: Gram-Inverse
test('st_of() invertiert die schiefwinklige Basis exakt (Gram-Inverse)', () => {
  const y = steepBay();
  const probes = [[500, 300], [0, 0], [y.L, y.H], [1234.5, 777.25], [-50, 1000], [y.L, 0]];
  for (const [s, t] of probes) {
    const [s2, t2] = y.st_of(y.P(s, t));
    close(s2, s, 1e-9, `Round-Trip s bei (${s}, ${t})`);
    close(t2, t, 1e-9, `Round-Trip t bei (${s}, ${t})`);
  }
});

test('st_of() erfuellt die Gram-Gleichung [dx, dy] = [[1,k],[k,1]] * [s, t]', () => {
  const y = steepBay();
  const k = dot3(y.Xh, y.Yh);
  const [s, t] = [1234.5, 777.25];
  const d = sub3(y.P(s, t), y.O);
  close(dot3(d, y.Xh), s + k * t, 1e-9, 'd.Xh == s + k*t (NICHT s)');
  close(dot3(d, y.Yh), k * s + t, 1e-9, 'd.Yh == k*s + t (NICHT t)');
});

test('ZAEHNE: die naive Skalarprodukt-Umkehrung faellt beim selben Round-Trip durch', () => {
  const y = steepBay();
  const probes = [[500, 300], [1234.5, 777.25], [y.L, y.H]];
  const worst = (inverse) => {
    let e = 0;
    for (const [s, t] of probes) {
      const [s2, t2] = inverse(y, y.P(s, t));
      e = Math.max(e, Math.abs(s2 - s), Math.abs(t2 - t));
    }
    return e;
  };
  const gram = worst((b, p) => b.st_of(p));
  const naive = worst(naiveStOf);
  close(gram, 0, 1e-9, 'Gram-Inverse: Round-Trip-Fehler');
  assert.ok(naive > 200,
    `Naive Inverse muss deutlich danebenliegen, ist aber nur ${naive} mm daneben — ` +
    'dann haette dieser Test keine Zaehne');
  // Konkret nachrechenbar: bei (500, 300) ist s_naiv = 500 + 300*k.
  const [sN, tN] = naiveStOf(y, y.P(500, 300));
  close(sN, 500 + 300 * K_STEEP, 1e-9, 'naives s = s + k*t');
  close(tN, 300 + 500 * K_STEEP, 1e-9, 'naives t = t + k*s');

  // Gegenprobe: auf einem WAAGRECHTEN Feld (k = 0) waere die naive Umkehrung
  // richtig — der Fehler zeigt sich nur bei geneigter Basis. Genau deshalb ist
  // er im Viewport unsichtbar geblieben.
  const f = flatBay();
  const [sf, tf] = naiveStOf(f, f.P(500, 300));
  close(sf, 500, 1e-9, 'naiv auf orthogonaler Basis: s stimmt');
  close(tf, 300, 1e-9, 'naiv auf orthogonaler Basis: t stimmt');
});

test('ZAEHNE 2: mit naiver Umkehrung meldet die Anschlusspruefung jedes Stabende als frei', () => {
  // Reproduktion des Originalfehlers: ein lotrechter Fuellstab von t=0 bis t=H.
  // Zulaessig ist t≈0, t≈H, s≈0 oder s≈L (grasshopper/patterns.py:956-957, ATOL 1.5).
  const y = steepBay();
  const ATOL = 1.5;
  y.seg(1000, 0, 1000, y.H, 'a');
  const bar = y.a[0];
  const freeEnds = (inverse) => {
    let bad = 0;
    for (const p of [curveStart(bar), curveEnd(bar)]) {
      const [s, t] = inverse(y, p);
      const attached = Math.abs(t) <= ATOL || Math.abs(t - y.H) <= ATOL
        || Math.abs(s) <= ATOL || Math.abs(s - y.L) <= ATOL;
      if (!attached) bad++;
    }
    return bad;
  };
  assert.equal(freeEnds((b, p) => b.st_of(p)), 0,
    'Gram-Inverse: beide Enden haengen an Untergurt bzw. Handlauf');
  assert.equal(freeEnds(naiveStOf), 2,
    'Naive Inverse: BEIDE Enden werden als frei haengend gemeldet — der gemeldete Bug');
});

test('st_of() ignoriert die Auslage entlang Nh (Nh steht senkrecht auf der Feldebene)', () => {
  const y = steepBay();
  const [s, t] = y.st_of(y.P(500, 300, 40));
  close(s, 500, 1e-9, 's bleibt trotz Auslage');
  close(t, 300, 1e-9, 't bleibt trotz Auslage');
});

test('st_of() faellt bei entarteter Basis (|det| < 1e-9) auf die Skalarprodukte zurueck', () => {
  // Xh == Yh: k = 1, det = 0 — der Fallback aus grasshopper/patterns.py:313-314.
  const y = new Bay({ a: [0, 0, 0], b: [0, 0, 500] }, { a: [0, 0, 800], b: [0, 0, 900] }, [0, 1, 0], 1);
  closePt(y.Xh, [0, 0, 1], 0, 'Xh');
  closePt(y.Yh, [0, 0, 1], 0, 'Yh');
  const p = [0, 0, 700];
  assert.deepEqual(y.st_of(p), [700, 700],
    'entartet: Rueckgabe sind die rohen Skalarprodukte, kein NaN/Infinity');
});

test('unit3() laesst den Nullvektor unveraendert (wie Vector3d.Unitize)', () => {
  assert.deepEqual(unit3([0, 0, 0]), [0, 0, 0], 'kein NaN aus 0/0');
  closePt(unit3([0, 0, 5]), [0, 0, 1], 0, 'Normierung');
});

// ================================================== pyRound / units(rapport)
test('pyRound() rundet wie Python zur geraden Zahl (Referenzwerte aus Python 3.14)', () => {
  // python: [(0.5,0),(1.5,2),(2.5,2),(3.5,4),(-0.5,0),(2.4999999,2),(2.5000001,3)]
  const table = [[0.5, 0], [1.5, 2], [2.5, 2], [3.5, 4], [-0.5, 0], [-1.5, -2], [-2.5, -2],
    [2.4999999, 2], [2.5000001, 3], [18.6339, 19]];
  for (const [x, want] of table) {
    assert.equal(pyRound(x), want, `pyRound(${x}) — exakte Gleichheit verlangt`);
  }
  assert.notEqual(pyRound(2.5), Math.round(2.5),
    'Math.round(2.5) = 3 waere die falsche Einheitenzahl');
});

test('units() liefert Einheitenzahl und gedehnten Rapport (Rest wird verteilt)', () => {
  const y = steepBay();
  const [n, st] = y.units(120);
  assert.equal(n, 19, 'round(2236.068 / 120) = round(18.63) = 19');
  close(st, y.L / 19, 1e-12, 'gedehnter Rapport = L / n');
  close(n * st, y.L, 1e-9, 'n Einheiten fuellen das Feld exakt — kein Reststueck');

  // Genau auf .5: Python rundet zur geraden Zahl, JS-Math.round nicht.
  const half = new Bay({ a: [0, 0, 0], b: [250, 0, 0] }, { a: [0, 0, 900], b: [250, 0, 900] }, [0, 1, 0], 1);
  assert.equal(half.units(100)[0], 2, '250/100 = 2.5 -> Python-round -> 2 (nicht 3)');

  assert.equal(half.units(0.2)[0], 250, 'rap wird auf mindestens 1.0 geklemmt');
  assert.equal(half.units(10000)[0], 1, 'n < 1 wird auf 1 angehoben');
  close(half.units(10000)[1], 250, 1e-12, 'bei n = 1 ist der Rapport die ganze Feldbreite');
});

// ============================================================ Emitter: seg
test('seg() legt eine Gerade im gewaehlten Kanal ab', () => {
  const f = flatBay();
  f.seg(0, 0, 0, 900, 'a');
  assert.equal(f.a.length, 1, 'genau ein Stueck');
  assert.equal(f.a[0].kind, 'line');
  closePt(f.a[0].a, [0, 0, 0], 0, 'Startpunkt');
  closePt(f.a[0].b, [0, 0, 900], 0, 'Endpunkt');
  close(curveLength(f.a[0]), 900, 0, 'Laenge des lotrechten Stabs');
  assert.deepEqual([f.b, f.st, f.hz], [[], [], []], 'kein anderer Kanal wird beruehrt');

  f.seg(100, 0, 100, 900, 'b', 40);
  assert.equal(f.b.length, 1, 'Kanal b');
  closePt(f.b[0].a, [100, 40, 0], 0, 'Auslage 40 laeuft entlang Nh');
});

test('seg() verwirft Stuecke <= TOL (0.001 mm), behaelt alles darueber', () => {
  const f = flatBay();
  f.seg(0, 0, 0, 0.0005, 'a');
  assert.equal(f.a.length, 0, `Laenge 0.0005 <= TOL (${TOL}) wird verworfen`);
  f.seg(0, 0, 0, 0.002, 'a');
  assert.equal(f.a.length, 1, 'Laenge 0.002 > TOL bleibt');
  f.seg(500, 400, 500, 400, 'a');
  assert.equal(f.a.length, 1, 'Nulllaenge wird verworfen');
});

test('seg() im geneigten Feld: Laenge folgt der schiefwinkligen Metrik', () => {
  const y = steepBay();
  y.seg(0, 0, y.L, y.H, 'a');
  // Weltversatz = (1000,0,2000) + (0,0,1000) = (1000,0,3000) -> sqrt(1e7)
  close(curveLength(y.a[0]), Math.sqrt(1e7), 1e-9,
    'sqrt(L^2 + H^2 + 2*L*H*k) = sqrt(1e7) = 3162.2776601683795');
  assert.notEqual(Math.round(curveLength(y.a[0])), Math.round(Math.hypot(y.L, y.H)),
    'orthogonal gerechnet (Pythagoras ohne Mischterm) kaeme etwas anderes heraus');
});

// =========================================================== Emitter: poly
test('poly() erzeugt AUSSCHLIESSLICH einzelne Geraden — nie Boegen, nie gejoint', () => {
  const y = flatBay();
  // Raute wie in `ray-diamond` (02): geschlossener Ring aus 5 Punkten
  // (letzter == erster). Genau dieser Fall liess in Grasshopper einen Sweep1
  // scheitern — deshalb wird er hier als Einzelgeraden abgelegt.
  const cs = 500; const ct = 450; const rx = 170; const ry = 450;
  y.poly([[cs - rx, ct], [cs, ct + ry], [cs + rx, ct], [cs, ct - ry], [cs - rx, ct]], 'a');
  assert.equal(y.a.length, 4, 'geschlossener Ring -> 4 gerade Stuecke (KEINE Bogenzerlegung)');
  for (const c of y.a) assert.equal(c.kind, 'line', 'jedes Stueck ist eine Gerade');
  // Die Stuecke stossen exakt aneinander, bleiben aber getrennte Objekte.
  for (let i = 0; i + 1 < y.a.length; i++) {
    closePt(curveEnd(y.a[i]), curveStart(y.a[i + 1]), 0, `Stueck ${i} stoesst an ${i + 1}`);
  }
  closePt(curveEnd(y.a[3]), curveStart(y.a[0]), 0, 'Ring schliesst sich');
  assert.equal(new Set(y.a).size, 4, 'vier eigenstaendige Objekte, kein Polycurve');
  // Von Hand: halbe Diagonalen 170 und 450 -> Umfang = 4*sqrt(170^2+450^2)
  const u = y.a.reduce((s, c) => s + curveLength(c), 0);
  close(u, 4 * Math.hypot(170, 450), 1e-9, 'Umfang der Raute');
});

test('poly() wirft entartete Zwischensegmente weg (seg-Regel gilt weiter)', () => {
  const f = flatBay();
  f.poly([[0, 0], [0, 0], [0, 500], [0, 500], [200, 500]], 'a');
  assert.equal(f.a.length, 2, 'die beiden Nullsegmente fallen raus');
  close(curveLength(f.a[0]), 500, 0, 'erstes Stueck');
  close(curveLength(f.a[1]), 200, 0, 'zweites Stueck');
});

// ============================================================ Emitter: arc
test('arc3(): Halbkreis auf orthonormaler Basis ist von Hand nachrechenbar', () => {
  const f = flatBay();
  f.arc([600, 0], [500, 100], [400, 0], 'a');
  assert.equal(f.a.length, 1, 'ein Bogen');
  const c = f.a[0];
  assert.equal(c.kind, 'arc');
  closePt(c.center, [500, 0, 0], 1e-9, 'Mittelpunkt = (s,t) = (500, 0)');
  close(c.radius, 100, 1e-9, 'Radius');
  close(c.angle, Math.PI, 1e-9, 'Halbkreis');
  close(curveLength(c), 100 * Math.PI, 1e-9, 'Bogenlaenge = pi*r = 314.159265...');
  closePt(curvePointAt(c, 0), [600, 0, 0], 1e-9, 'PointAt(0) = Startpunkt');
  closePt(curvePointAt(c, 1), [400, 0, 0], 1e-9, 'PointAt(1) = Endpunkt');
  closePt(curvePointAt(c, 0.5), [500, 0, 100], 1e-9, 'PointAt(0.5) = Durchgangspunkt');
  // Tangente im Scheitel zeigt entgegen der s-Richtung
  const tg = unit3(curveTangentAt(c, 0.5));
  closePt(tg, [-1, 0, 0], 1e-9, 'Tangente im Scheitel');
});

test('arc3(): schiefwinkliges Feld gegen unabhaengige Python-Rechnung', () => {
  const y = steepBay();
  y.arc([200, 0], [400, 300], [600, 0], 'a');
  const c = y.a[0];
  // Python (Umkreis ueber die 3 Weltpunkte, siehe Ableitung im Bericht):
  closePt(c.center, [12.218771533316428, 0.0, 541.1042097332997], 1e-9, 'Mittelpunkt (Python)');
  close(c.radius, 273.35365778094547, 1e-9, 'Radius (Python)');
  close(c.angle, 4.641698148870935, 1e-9, 'Oeffnungswinkel (Python) — der GROSSE Bogen');
  close(curveLength(c), 1268.8251673089137, 1e-9, 'Bogenlaenge (Python)');
  // Alle drei Stuetzpunkte liegen auf dem Kreis ...
  for (const [nm, p] of [['p0', c.p0], ['pm', c.pm], ['p1', c.p1]]) {
    close(dist3(p, c.center), c.radius, 1e-9, `${nm} liegt auf dem Kreis`);
  }
  // ... und der Durchgangspunkt liegt ZWISCHEN Start und Ende auf dem Bogen.
  const u = unit3(sub3(c.p0, c.center));
  const w = cross3(c.normal, u);
  const d = sub3(c.pm, c.center);
  let am = Math.atan2(dot3(d, w), dot3(d, u));
  if (am <= 0) am += 2 * Math.PI;
  assert.ok(am > 0 && am < c.angle, `Durchgangspunkt liegt im Bogen (${am} in (0, ${c.angle}))`);
  closePt(curvePointAt(c, am / c.angle), c.pm, 1e-9, 'Bogen laeuft durch den Durchgangspunkt');
});

test('arc3(): kollineare oder zusammenfallende Punkte ergeben keinen Bogen (Arc.IsValid)', () => {
  const f = flatBay();
  f.arc([0, 0], [0, 450], [0, 900], 'a');
  assert.equal(f.a.length, 0, 'kollinear -> verworfen');
  f.arc([100, 100], [100, 100], [500, 100], 'a');
  assert.equal(f.a.length, 0, 'doppelter Punkt -> verworfen');
  assert.equal(arc3([0, 0, 0], [1, 0, 0], [2, 0, 0]), null, 'arc3 gibt null zurueck');
});

// ============================================================ Emitter: bez
test('bez(): Bezier mit kollinearen Kontrollpunkten ist exakt eine Gerade', () => {
  const f = flatBay();
  // Kontrollpunkte bei 1/3 und 2/3 -> gleichfoermige Parametrisierung
  f.bez([0, 0], [300, 300], [600, 600], [900, 900], 'a');
  const c = f.a[0];
  assert.equal(c.kind, 'bezier');
  close(curveLength(c), Math.hypot(900, 900), 1e-9, 'Laenge = |p1 - p0| = 1272.7922...');
  closePt(curvePointAt(c, 0.5), [450, 0, 450], 1e-12, 'Mitte');
  closePt(curvePointAt(c, 0.25), [225, 0, 225], 1e-12, 'Viertelpunkt');
  closePt(curvePointAt(c, 0), [0, 0, 0], 0, 'Start');
  closePt(curvePointAt(c, 1), [900, 0, 900], 1e-9, 'Ende');
});

test('bez(): gekruemmter Bezier gegen unabhaengige Python-Integration', () => {
  const y = steepBay();
  y.bez([0, 0], [300, 400], [-300, 600], [0, 1000], 'a');
  const c = y.a[0];
  // Python, Simpson mit 200 000 Intervallen: 1016.6425005666944
  close(curveLength(c), 1016.6425005666944, 1e-6, 'Bogenlaenge (Python-Simpson)');
  // Symmetrischer Bezier -> Mitte bei (s,t) = (0, 500) -> Weltpunkt (0,0,600)
  closePt(curvePointAt(c, 0.5), [0, 0, 600], 1e-9, 'Mitte (von Hand: P(0,500))');
  // Python: bp(0.25) = (37.733647120308945, 0.0, 444.2172942406179)
  closePt(curvePointAt(c, 0.25), [37.733647120308945, 0, 444.2172942406179], 1e-9,
    'Viertelpunkt (Python)');
});

test('bez() legt IMMER ab — auch entartet, ohne Laengenpruefung (wie im Original)', () => {
  const f = flatBay();
  f.bez([100, 100], [100, 100], [100, 100], [100, 100], 'b');
  assert.equal(f.b.length, 1, 'kein TOL-Filter in bez() — bewusst 1:1 portiert');
  close(curveLength(f.b[0]), 0, 1e-12, 'Laenge 0');
});

// =========================================================== Emitter: part
test('part() filtert null und Stuecke <= TOL, joint aber NIE', () => {
  const f = flatBay();
  const pieces = [
    line(f.P(0, 100), f.P(0, 800)),                 // 700 mm
    null,                                            // wie eine fehlgeschlagene Rhino-Kurve
    line(f.P(0, 800), f.P(0, 800.0004)),            // 0.0004 mm <= TOL
    arc3(f.P(0, 800), f.P(50, 850), f.P(100, 800)), // Bogen
  ];
  f.part(pieces, 'a');
  assert.equal(f.a.length, 2, 'zwei Stuecke ueberleben');
  assert.equal(f.a[0], pieces[0], 'Reihenfolge und Identitaet bleiben erhalten');
  assert.equal(f.a[1], pieces[3], 'der Bogen bleibt ein eigenes Objekt');
  assert.equal(f.a[0].kind, 'line');
  assert.equal(f.a[1].kind, 'arc');
  // Knickfrei-Invariante: die Stuecke stossen aneinander, sind aber getrennt.
  closePt(curveEnd(f.a[0]), curveStart(f.a[1]), 1e-9, 'Stuecke stossen exakt aneinander');
});

// ================================================== Emitter: plate / block
test('block(): orthonormales Feld -> Flaeche und Volumen exakt von Hand', () => {
  const f = flatBay();
  f.block(100, 200, 500, 900, 30); // Default-Kanal ist hz
  assert.equal(f.hz.length, 1, 'Holzblock landet im Kanal hz');
  assert.equal(f.st.length, 0, 'nicht im Stahlkanal');
  const s = f.hz[0];
  assert.equal(s.kind, 'plate');
  assert.equal(s.loops.length, 1, 'nur die Aussenkontur');
  assert.equal(s.loops[0].pts.length, 5, 'Ring wird geschlossen (4 Ecken + Wiederholung)');
  closePt(s.loops[0].pts[0], s.loops[0].pts[4], 0, 'erster == letzter Punkt');
  assert.equal(s.loops[0].closed, true);
  closePt(s.path, [0, 30, 0], 0, 'Extrusion laeuft entlang Nh * thick');
  close(polygonArea(s.loops[0].pts), 400 * 700, 1e-9, 'Flaeche = 400 x 700');
  close(solidVolume(s), 400 * 700 * 30, 1e-6, 'Volumen = Flaeche * Dicke = 8 400 000 mm^3');
});

test('block(): im geneigten Feld ist die Flaeche um sin(Basiswinkel) geschert', () => {
  const y = steepBay();
  y.block(100, 200, 500, 900, 30, 'hz', 12);
  const s = y.hz[0];
  // Von Hand: A = ds * dt * |Xh x Yh| = 400*700*sqrt(1-k^2) = 280000/sqrt(5)
  close(polygonArea(s.loops[0].pts), 400 * 700 * SIN_STEEP, 1e-6,
    'geschert: 125219.80673998826 statt 280000');
  // Python (unabhaengig gerechnet): 3756594.202199647
  close(solidVolume(s), 3756594.202199647, 1e-3, 'Volumen (Python)');
  close(solidVolume(s), 400 * 700 * SIN_STEEP * 30, 1e-6, 'identisch zur Handformel');
  closePt(s.loops[0].pts[0], y.P(100, 200, 12), 0, 'Auslage 12 mm steckt in den Punkten');
});

test('plate(): Aussparungen werden vom Volumen abgezogen, loops[0] ist die Aussenkontur', () => {
  const f = flatBay();
  const outer = [[0, 0], [f.L, 0], [f.L, f.H], [0, f.H]];
  const hole = [[400, 300], [600, 300], [600, 600], [400, 600]];
  f.plate([outer, hole], 4); // Default-Kanal ist st
  assert.equal(f.st.length, 1, 'Blech landet im Kanal st');
  const s = f.st[0];
  assert.equal(s.loops.length, 2, 'Aussenkontur + 1 Loch');
  close(polygonArea(s.loops[0].pts), 1000 * 900, 1e-6, 'Aussenflaeche');
  close(polygonArea(s.loops[1].pts), 200 * 300, 1e-9, 'Lochflaeche');
  close(solidVolume(s), (1000 * 900 - 200 * 300) * 4, 1e-6,
    'Volumen = (900000 - 60000) * 4 = 3 360 000 mm^3');
});

test('plate(): ein bereits geschlossener Ring wird NICHT ein zweites Mal geschlossen', () => {
  const f = flatBay();
  const openLoop = [[0, 0], [400, 0], [400, 700], [0, 700]];
  f.plate([openLoop], 4, 'st');
  f.plate([[...openLoop, [0, 0]]], 4, 'st'); // derselbe Ring, schon geschlossen
  assert.equal(f.st[0].loops[0].pts.length, 5, 'offener Ring bekommt den Schlusspunkt angehaengt');
  assert.equal(f.st[1].loops[0].pts.length, 5, 'geschlossener Ring bleibt bei 5 Punkten');
  assert.deepEqual(f.st[1].loops[0].pts, f.st[0].loops[0].pts,
    'beide Schreibweisen liefern denselben Ring (exakte Gleichheit)');
});

test('plate(): entartete oder leere Konturen erzeugen kein Solid', () => {
  const f = flatBay();
  f.plate([], 4);
  f.plate([[[0, 0], [100, 0], [200, 0], [300, 0]]], 4); // Flaeche 0
  assert.equal(f.st.length, 0, 'Rhino liefert hier ebenfalls kein Brep');
});

test('plate(): schiefe Auslagerichtung -> Volumen ueber die SENKRECHTE Hoehe', () => {
  // Nh steht hier NICHT senkrecht auf der Feldebene (Nh = (0,1,1)/sqrt(2)).
  // Rhinos CreateExtrusion baut dann ein schiefes Prisma: V = A * |path . n|.
  const y = new Bay({ a: [0, 0, 0], b: [1000, 0, 0] }, { a: [0, 0, 900], b: [1000, 0, 900] },
    [0, 1, 1], 1);
  closePt(y.Nh, [0, 1 / Math.sqrt(2), 1 / Math.sqrt(2)], 1e-15, 'Nh ist unitisiert, aber schief');
  y.block(0, 0, 400, 700, 30, 'hz');
  const s = y.hz[0];
  close(polygonArea(s.loops[0].pts), 400 * 700, 1e-9, 'Grundflaeche unveraendert');
  close(solidVolume(s), 400 * 700 * 30 / Math.sqrt(2), 1e-6,
    'V = 8 400 000 / sqrt(2) = 5 939 696.96 mm^3, NICHT 8 400 000');

  // Gleiche Konsequenz auf der Umkehrabbildung — und zwar identisch zum Python:
  // st_of() kennt nur Xh und Yh, eine schiefe Auslage schlaegt also auf t durch.
  const [sv, tv] = y.st_of(y.P(100, 200, 50));
  close(sv, 100, 1e-9, 's bleibt (Nh steht senkrecht auf Xh)');
  close(tv, 200 + 50 / Math.sqrt(2), 1e-9,
    't wandert um 35.355 mm — bekannte, 1:1 uebernommene Eigenschaft von st_of()');
});

// ======================================================== Emitter: twisted
test('twisted(): Sektionen liegen exakt auf den gedrehten Quadratecken', () => {
  const f = flatBay();
  f.twisted(500, 0, 800, 16, 1.0, 9);
  assert.equal(f.st.length, 1, 'ein Loft-Solid im Kanal st');
  const s = f.st[0];
  assert.equal(s.kind, 'loft');
  assert.equal(s.capped, true, 'CapPlanarHoles');
  assert.equal(s.sections.length, 9, 'steps = 9 Sektionen');
  for (const sec of s.sections) {
    assert.equal(sec.pts.length, 5, 'Quadrat als geschlossener 5-Punkte-Zug');
    closePt(sec.pts[0], sec.pts[4], 1e-12, 'Ring geschlossen');
  }
  // f = 0: keine Drehung -> Ecken bei (s +- 8, t0, +- 8)
  closePt(s.sections[0].pts[0], f.P(500 - 8, 0, -8), 0, 'Ecke 1 der Startsektion');
  closePt(s.sections[0].pts[1], f.P(500 + 8, 0, -8), 0, 'Ecke 2');
  closePt(s.sections[0].pts[2], f.P(500 + 8, 0, 8), 0, 'Ecke 3');
  closePt(s.sections[0].pts[3], f.P(500 - 8, 0, 8), 0, 'Ecke 4');
  // f = 1 und turns = 1.0 -> ang = pi (HALBE Umdrehung, nicht ganze):
  // die Ecken sind punktgespiegelt, das Quadrat deckt sich wieder.
  closePt(s.sections[8].pts[0], f.P(500 + 8, 800, 8), 1e-12, 'Endsektion um 180 deg gedreht');
  closePt(s.sections[8].pts[2], f.P(500 - 8, 800, -8), 1e-12, 'gegenueberliegende Ecke');
  // Mittlere Sektion (f = 0.5) ist um 90 deg gedreht -> Ecke liegt auf der Achse
  closePt(s.sections[4].pts[0], f.P(500 + 8, 400, -8), 1e-9, 'Mittelsektion um 90 deg');
});

test('twisted(): Volumen — ungedreht von Hand, gedreht gegen Python', () => {
  const y = steepBay();
  y.twisted(800, 0, 1000, 16, 0.0, 9); // turns = 0 -> gerades Prisma
  // Von Hand: Querschnitt 16x16 in der (Xh, Nh)-Ebene, Achse laeuft entlang Yh.
  // Die Sektion steht SCHIEF zur Achse -> V = w^2 * dt * |Yh . n| = 256*1000/sqrt(5)
  close(solidVolume(y.st[0]), 256 * 1000 * SIN_STEEP, 1e-6,
    'ungedreht: 114486.68044798926 mm^3 (Python: 114486.68044798917)');

  const y2 = steepBay();
  y2.twisted(800, 0, 1000, 16, 1.0, 9);
  // Python, feine Scheiben (2000 Simpson-Schritte je Sektionspaar): 111581.75390234515
  close(solidVolume(y2.st[0]), 111581.75390234515, 1e-6, 'gedreht (Python)');
  assert.ok(solidVolume(y2.st[0]) < solidVolume(y.st[0]),
    'die Torsion schnuert den Stab leicht ein');
});

// ============================================================== Kanaele/API
test('Kanaele a/b/st/hz starten leer und sind die einzigen Senken', () => {
  const f = flatBay();
  assert.deepEqual([f.a, f.b, f.st, f.hz], [[], [], [], []], 'alle vier Kanaele leer');
  f.seg(0, 0, 0, 900, 'a');
  f.seg(100, 0, 100, 900, 'b');
  f.plate([[[0, 0], [100, 0], [100, 100], [0, 100]]], 4, 'st');
  f.block(200, 0, 300, 100, 20, 'hz');
  assert.deepEqual([f.a.length, f.b.length, f.st.length, f.hz.length], [1, 1, 1, 1],
    'jeder Emitter trifft genau seinen Kanal');
});

test('Alle Ausgaben sind reine Daten (JSON-rundreisefaehig, keine Rhino-Objekte)', () => {
  const y = steepBay();
  y.seg(0, 0, 0, y.H, 'a');
  y.arc([200, 0], [400, 300], [600, 0], 'a');
  y.bez([0, 0], [300, 400], [-300, 600], [0, 1000], 'b');
  y.block(100, 200, 500, 900, 30);
  y.twisted(800, 0, 1000, 16);
  for (const ch of ['a', 'b', 'st', 'hz']) {
    for (const o of y[ch]) {
      assert.deepEqual(JSON.parse(JSON.stringify(o)), o, `${ch}: ${o.kind} ist serialisierbar`);
    }
  }
});

// =================================================================== Zufall
test('PyRandom.random() reproduziert CPython bitgenau (Referenz: Python 3.14)', () => {
  const expected = {
    0: [0.8444218515250481, 0.7579544029403025, 0.420571580830845, 0.25891675029296335],
    1: [0.13436424411240122, 0.8474337369372327, 0.763774618976614, 0.2550690257394217],
    42: [0.6394267984578837, 0.025010755222666936, 0.27502931836911926, 0.22321073814882275],
    1234567: [0.9631432476096223, 0.23573288372003576, 0.5814831206063004, 0.226719849335687],
  };
  for (const [seed, want] of Object.entries(expected)) {
    const g = new PyRandom(Number(seed));
    const got = want.map(() => g.random());
    assert.deepEqual(got, want, `Seed ${seed} — exakte Gleichheit (identische IEEE-Doubles)`);
  }
});

test('PyRandom.getrandbits()/randrange() reproduzieren CPython (inkl. Verwurfschleife)', () => {
  // python: random.Random(7); [g.getrandbits(k) for k in (1,2,8,32,32)]
  const g = new PyRandom(7);
  assert.deepEqual([1, 2, 8, 32, 32].map((k) => g.getrandbits(k)),
    [0, 3, 38, 1695753998, 2795742288], 'getrandbits — exakte Gleichheit');
  // python: g=Random(5); g.random(), g.randrange(2), g.randrange(2), g.random(), g.randrange(2)
  const h = new PyRandom(5);
  assert.equal(h.random(), 0.6229016948897019, 'random()');
  assert.equal(h.randrange(2), 1, 'randrange');
  assert.equal(h.randrange(2), 0, 'randrange');
  assert.equal(h.random(), 0.8403481205226678, 'random() nach randrange — Strom bleibt synchron');
  assert.equal(h.randrange(2), 0, 'randrange');
});

test('Bay.rnd haengt am Seed: gleicher Seed -> gleiche Folge, anderer Seed -> andere', () => {
  const a = steepBay(42);
  const b = steepBay(42);
  const c = steepBay(43);
  const draw = (y) => [y.rnd.random(), y.rnd.random(), y.rnd.random()];
  assert.deepEqual(draw(a), draw(b), 'reproduzierbar');
  assert.notDeepEqual(draw(steepBay(42)), draw(c), 'Seed wirkt');
  assert.equal(new PyRandom(42).random(), 0.6394267984578837,
    'Bay-Seed geht unveraendert an random.Random(seed)');
});

// ============================================== Kurvenabfragen (Querschnitt)
test('curveStart/curveEnd/curvePointAt sind fuer alle Kurventypen konsistent', () => {
  const f = flatBay();
  const l = line(f.P(0, 0), f.P(0, 900));
  const a = arc3(f.P(600, 0), f.P(500, 100), f.P(400, 0));
  const b = bezier(f.P(0, 0), f.P(300, 300), f.P(600, 600), f.P(900, 900));
  const p = polyline([f.P(0, 0), f.P(0, 400), f.P(300, 400)]);
  for (const [nm, c] of [['line', l], ['arc', a], ['bezier', b], ['polyline', p]]) {
    closePt(curvePointAt(c, 0), curveStart(c), 1e-9, `${nm}: PointAt(0) == Start`);
    closePt(curvePointAt(c, 1), curveEnd(c), 1e-9, `${nm}: PointAt(1) == Ende`);
    assert.ok(len3(curveTangentAt(c, 0.5)) > 0, `${nm}: Tangente in der Mitte ist nicht null`);
  }
  close(curveLength(p), 400 + 300, 1e-9, 'Polylinienlaenge = Summe der Abschnitte');
  // Polylinien-Parameter ist abschnittsweise (wie PolylineCurve), NICHT bogenlaengen-proportional
  closePt(curvePointAt(p, 0.5), f.P(0, 400), 1e-9,
    'u = 0.5 trifft den Knick, obwohl die Abschnitte ungleich lang sind');
});
