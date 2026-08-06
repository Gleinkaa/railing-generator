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

// bay.js — das feldlokale (s, t)-System und die Geometrie-Emitter,
// 1:1 portiert aus `grasshopper/patterns.py`, `class Bay` (Zeilen 271–418).
//
// ---------------------------------------------------------------------------
// Warum es dieses Modul gibt
// ---------------------------------------------------------------------------
// Die Grasshopper-Engine baut jedes Feld (Bay) in einem EIGENEN, schiefwinkligen
// Koordinatensystem:
//
//     O  = Startpunkt des Untergurt-Segments
//     Xh = Einheitsvektor entlang des Untergurts  (MIT der Steigung geneigt)
//     Yh = Einheitsvektor nach oben               (lotrecht)
//     Nh = Einheitsvektor nach aussen             (von der Treppe weg)
//     P(s, t, off) = O + Xh*s + Yh*t + Nh*off
//
// Xh und Yh sind ABSICHTLICH NICHT orthogonal: s laeuft als Bogenlaenge die
// Neigung entlang, t steht lotrecht — genau so, wie ein Gelaender gebaut wird.
// Die Umkehrung (Weltpunkt -> (s, t)) darf deshalb NICHT ueber das nackte
// Skalarprodukt laufen; sie braucht die Inverse der Gram-Matrix. Siehe
// `Bay.prototype.st_of` — dieser Fehler war schon einmal produktiv und hat jedes
// Stabende als "frei haengend" gemeldet, obwohl die Geometrie stimmte.
//
// ---------------------------------------------------------------------------
// Datenrepraesentation (Rhino-Ersatz)
// ---------------------------------------------------------------------------
// Rhino-Typen gibt es hier nicht. Statt dessen ausschliesslich JSON-faehige
// Klartext-Objekte — keine Klassen, keine Abhaengigkeiten, alles vergleichbar
// mit `assert.deepEqual`:
//
//   Punkt / Vektor   [x, y, z]                 (wie in model.js; mm)
//   Linie            { kind: 'line',     a, b }
//   Bogen            { kind: 'arc',      p0, pm, p1, center, radius, normal, angle }
//                    3-Punkte-Bogen (Start, Durchgangspunkt, Ende) wie rg.Arc.
//   Bezier           { kind: 'bezier',   pts: [p0, c0, c1, p1] }   kubisch
//   Polylinie        { kind: 'polyline', pts: [...], closed }
//   Blech / Platte   { kind: 'plate',    loops: [aussen, ...loecher], path, thick }
//   Loft (tordiert)  { kind: 'loft',     sections: [polyline...], capped: true }
//
// Kurvenabfragen sind freie Funktionen (`curveLength`, `curvePointAt`,
// `curveTangentAt`, `curveStart`, `curveEnd`), damit die Objekte reine Daten
// bleiben. `curvePointAt(c, u)` nimmt u in [0, 1] als NORMIERTEN Kurvenparameter
// — das entspricht `curve.Domain.ParameterAt(u)` in Rhino und ist damit fuer
// Linie/Bogen bogenlaengen-proportional, fuer Bezier und Polylinie aber NICHT
// (genau wie im Original, dessen Kletterhilfen-Pruefung ebenfalls ueber
// `Domain.ParameterAt` samplet).
//
// ---------------------------------------------------------------------------
// Invariante: knickfrei, NIE `join()`
// ---------------------------------------------------------------------------
// `poly()` und `part()` legen jedes knickfreie Stueck EINZELN ab. Im
// Grasshopper-Original liefert ein Sweep1 ueber eine geknickte Schiene je nach
// Knickwinkel zusaetzliche Koerper oder scheitert ganz. JavaScript hat kein
// Sweep1 — der Vertrag wird trotzdem eingehalten, damit beide Engines Stueck
// fuer Stueck dieselbe Liste liefern. Die Stueckliste haengt daran.

export const TOL = 0.001; // grasshopper/patterns.py:41

// ------------------------------------------------------------------ Vektoren
export const v3 = (x, y, z) => [x, y, z];
export const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub3 = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const mul3 = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
export const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross3 = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
export const len3 = (a) => Math.hypot(a[0], a[1], a[2]);
export const dist3 = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);

// Rhino: Vector3d.Unitize() laesst den Nullvektor unveraendert und meldet false.
export function unit3(a) {
  const l = len3(a);
  return l > 0 ? [a[0] / l, a[1] / l, a[2] / l] : [a[0], a[1], a[2]];
}

// Python `round()` rundet zur GERADEN Zahl (banker's rounding), JS `Math.round`
// immer auf. `units()` haengt daran: L/rap == 2.5 gibt in Python 2, in JS 3.
export function pyRound(x) {
  const f = Math.floor(x);
  const d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// ------------------------------------------------------------------- Zufall
// Portierung von CPython `random.Random` (Mersenne-Twister MT19937 + der
// CPython-Seeding-Variante `init_by_array`). Ein eigener PRNG (mulberry32 o. ae.)
// wuerde bei den fuenf Zufallsmustern (01 Staggered Panels, 10 Segmented
// Panels, 12 Random Rake, 14 Grain Sheet, 22 Crossed Rakes) stillschweigend
// eine andere Geometrie liefern als Grasshopper.
//
// Die Python-Vorlage sprach hier von VIER Mustern und liess das Laserblech
// (14) aus; nachgezaehlt sind es fuenf — jedes Muster mit gesetztem Feld
// `zufall` zieht auch wirklich aus dem Strom. Massgeblich ist das Feld, nicht
// diese Aufzaehlung.
const N = 624;
const M = 397;
const MATRIX_A = 0x9908b0df;
const UPPER_MASK = 0x80000000;
const LOWER_MASK = 0x7fffffff;

export class PyRandom {
  constructor(seed = 0) {
    this.mt = new Uint32Array(N);
    this.mti = N + 1;
    this.seed(seed);
  }

  /** CPython: seed(int) benutzt abs(seed), in 32-Bit-Woerter zerlegt. */
  seed(s) {
    let n = Math.abs(Math.trunc(Number(s)));
    if (!Number.isSafeInteger(n)) throw new RangeError('Seed muss ein sicherer Integer sein');
    const key = [];
    if (n === 0) key.push(0);
    while (n > 0) {
      key.push(n >>> 0);
      n = Math.floor(n / 4294967296);
    }
    this._initByArray(key);
  }

  _initGenrand(s) {
    this.mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = (Math.imul(1812433253, prev) + i) >>> 0;
    }
    this.mti = N;
  }

  _initByArray(key) {
    this._initGenrand(19650218);
    let i = 1;
    let j = 0;
    for (let k = Math.max(N, key.length); k > 0; k--) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = ((this.mt[i] ^ Math.imul(prev, 1664525)) + key[j] + j) >>> 0;
      i++; j++;
      if (i >= N) { this.mt[0] = this.mt[N - 1]; i = 1; }
      if (j >= key.length) j = 0;
    }
    for (let k = N - 1; k > 0; k--) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = ((this.mt[i] ^ Math.imul(prev, 1566083941)) - i) >>> 0;
      i++;
      if (i >= N) { this.mt[0] = this.mt[N - 1]; i = 1; }
    }
    this.mt[0] = UPPER_MASK;
  }

  genrandUint32() {
    if (this.mti >= N) {
      for (let k = 0; k < N; k++) {
        const y = (this.mt[k] & UPPER_MASK) | (this.mt[(k + 1) % N] & LOWER_MASK);
        this.mt[k] = (this.mt[(k + M) % N] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0)) >>> 0;
      }
      this.mti = 0;
    }
    let y = this.mt[this.mti++];
    y ^= y >>> 11;
    y = (y ^ ((y << 7) & 0x9d2c5680)) >>> 0;
    y = (y ^ ((y << 15) & 0xefc60000)) >>> 0;
    y ^= y >>> 18;
    return y >>> 0;
  }

  /** CPython `genrand_res53`: 53 Zufallsbits aus zwei 32-Bit-Zuegen. */
  random() {
    const a = this.genrandUint32() >>> 5;
    const b = this.genrandUint32() >>> 6;
    return (a * 67108864 + b) / 9007199254740992;
  }

  /** getrandbits(k) fuer 1 <= k <= 32 (mehr braucht die Muster-Engine nicht). */
  getrandbits(k) {
    if (k <= 0 || k > 32) throw new RangeError('getrandbits: 1..32 unterstuetzt');
    return this.genrandUint32() >>> (32 - k);
  }

  /**
   * randrange(stop) ueber CPython `_randbelow_with_getrandbits` — inklusive
   * Verwurfschleife. Die Schleife MUSS mit portiert werden: sie verbraucht
   * Zufallszahlen und verschiebt damit alle folgenden Werte.
   */
  randrange(stop) {
    const n = Math.trunc(stop);
    if (n <= 0) throw new RangeError('randrange: leerer Bereich');
    const bits = 32 - Math.clz32(n); // n.bit_length() fuer 1 <= n < 2^31
    let r = this.getrandbits(bits);
    while (r >= n) r = this.getrandbits(bits);
    return r;
  }
}

// -------------------------------------------------------------------- Kurven
export function line(a, b) {
  return { kind: 'line', a: [...a], b: [...b] };
}

export function bezier(p0, c0, c1, p1) {
  return { kind: 'bezier', pts: [[...p0], [...c0], [...c1], [...p1]] };
}

export function polyline(pts, closed = false) {
  return { kind: 'polyline', pts: pts.map((p) => [...p]), closed };
}

const samePoint = (a, b) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];

/**
 * 3-Punkte-Bogen wie `rg.Arc(start, durchgang, ende)`.
 * Gibt `null` zurueck, wo Rhino `Arc.IsValid == false` melden wuerde
 * (zusammenfallende oder kollineare Punkte). Rhinos genaues Kriterium ist nicht
 * dokumentiert; hier wird relativ geprueft (Flaeche des Dreiecks gegen die
 * Kantenlaengen), damit der Test skalenunabhaengig ist.
 */
export function arc3(p0, pm, p1) {
  const v1 = sub3(pm, p0);
  const v2 = sub3(p1, p0);
  const n = cross3(v1, v2);
  const nl = len3(n);
  const scale = len3(v1) * len3(v2);
  if (scale <= 0 || nl <= 1e-12 * scale) return null;
  const n2 = nl * nl;
  // Umkreismittelpunkt: C = A + ((|v1|^2 * v2 - |v2|^2 * v1) x n) / (2|n|^2)
  const c = add3(
    p0,
    mul3(cross3(sub3(mul3(v2, dot3(v1, v1)), mul3(v1, dot3(v2, v2))), n), 1 / (2 * n2)),
  );
  const normal = mul3(n, 1 / nl); // p0 -> pm -> p1 dreht positiv um `normal`
  const radius = dist3(p0, c);
  const angle = arcSweep(c, normal, p0, p1);
  return { kind: 'arc', p0: [...p0], pm: [...pm], p1: [...p1], center: c, radius, normal, angle };
}

function arcSweep(center, normal, p0, p1) {
  const u = unit3(sub3(p0, center));
  const w = cross3(normal, u); // Rechtssystem: Drehung um `normal` geht u -> w
  const d = sub3(p1, center);
  let a = Math.atan2(dot3(d, w), dot3(d, u));
  if (a <= 0) a += 2 * Math.PI;
  return a;
}

export function curveStart(c) {
  if (Array.isArray(c)) return [...c[0]];
  switch (c.kind) {
    case 'line': return [...c.a];
    case 'arc': return [...c.p0];
    case 'bezier': return [...c.pts[0]];
    case 'polyline': return [...c.pts[0]];
    default: return [...c.a];
  }
}

export function curveEnd(c) {
  if (Array.isArray(c)) return [...c[c.length - 1]];
  switch (c.kind) {
    case 'line': return [...c.b];
    case 'arc': return [...c.p1];
    case 'bezier': return [...c.pts[3]];
    case 'polyline': return [...c.pts[c.pts.length - 1]];
    default: return [...c.b];
  }
}

// 5-Punkt-Gauss-Legendre, zusammengesetzt: exakt genug fuer Bogenlaengen
// kubischer Bezier (relativer Fehler < 1e-12 bei den hier vorkommenden Kurven).
const GL_X = [0, -0.5384693101056831, 0.5384693101056831, -0.906179845938664, 0.906179845938664];
const GL_W = [0.5688888888888889, 0.4786286704993665, 0.4786286704993665,
  0.2369268850561891, 0.2369268850561891];

export function curveLength(c) {
  switch (c.kind) {
    case 'line':
      return dist3(c.a, c.b);
    case 'arc':
      return c.radius * c.angle;
    case 'polyline': {
      let s = 0;
      for (let i = 0; i + 1 < c.pts.length; i++) s += dist3(c.pts[i], c.pts[i + 1]);
      return s;
    }
    case 'bezier': {
      const sub = 8;
      let total = 0;
      for (let i = 0; i < sub; i++) {
        const a = i / sub;
        const b = (i + 1) / sub;
        const half = (b - a) / 2;
        const mid = (a + b) / 2;
        let s = 0;
        for (let g = 0; g < GL_X.length; g++) {
          s += GL_W[g] * len3(bezierDerivative(c.pts, mid + half * GL_X[g]));
        }
        total += s * half;
      }
      return total;
    }
    default:
      throw new TypeError(`curveLength: unbekannte Kurve ${c && c.kind}`);
  }
}

function bezierPoint(P, u) {
  const m = 1 - u;
  const w0 = m * m * m;
  const w1 = 3 * m * m * u;
  const w2 = 3 * m * u * u;
  const w3 = u * u * u;
  return [0, 1, 2].map((i) => w0 * P[0][i] + w1 * P[1][i] + w2 * P[2][i] + w3 * P[3][i]);
}

function bezierDerivative(P, u) {
  const m = 1 - u;
  const w0 = 3 * m * m;
  const w1 = 6 * m * u;
  const w2 = 3 * u * u;
  return [0, 1, 2].map((i) => w0 * (P[1][i] - P[0][i])
    + w1 * (P[2][i] - P[1][i]) + w2 * (P[3][i] - P[2][i]));
}

/** Punkt bei normiertem Kurvenparameter u in [0, 1] (= Domain.ParameterAt(u)). */
export function curvePointAt(c, u) {
  switch (c.kind) {
    case 'line':
      return add3(c.a, mul3(sub3(c.b, c.a), u));
    case 'arc': {
      const ang = c.angle * u;
      const r = sub3(c.p0, c.center);
      const w = cross3(c.normal, r);
      return add3(c.center, add3(mul3(r, Math.cos(ang)), mul3(w, Math.sin(ang))));
    }
    case 'bezier':
      return bezierPoint(c.pts, u);
    case 'polyline': {
      const segs = c.pts.length - 1;
      const f = u * segs;
      const i = Math.min(Math.max(Math.floor(f), 0), segs - 1);
      return add3(c.pts[i], mul3(sub3(c.pts[i + 1], c.pts[i]), f - i));
    }
    default:
      throw new TypeError(`curvePointAt: unbekannte Kurve ${c && c.kind}`);
  }
}

/** Nicht normierte Tangente (Ableitung) bei normiertem Parameter u. */
export function curveTangentAt(c, u) {
  switch (c.kind) {
    case 'line':
      return sub3(c.b, c.a);
    case 'arc': {
      const ang = c.angle * u;
      const r = sub3(c.p0, c.center);
      const w = cross3(c.normal, r);
      return mul3(add3(mul3(r, -Math.sin(ang)), mul3(w, Math.cos(ang))), c.angle);
    }
    case 'bezier':
      return bezierDerivative(c.pts, u);
    case 'polyline': {
      const segs = c.pts.length - 1;
      const i = Math.min(Math.max(Math.floor(u * segs), 0), segs - 1);
      return mul3(sub3(c.pts[i + 1], c.pts[i]), segs);
    }
    default:
      throw new TypeError(`curveTangentAt: unbekannte Kurve ${c && c.kind}`);
  }
}

// -------------------------------------------------------------------- Flaeche
/** Vektorflaeche eines ebenen Polygons: 1/2 * sum(p_i x p_i+1). Laenge = Flaeche. */
export function polygonAreaVector(pts) {
  let s = [0, 0, 0];
  for (let i = 0; i < pts.length; i++) {
    s = add3(s, cross3(pts[i], pts[(i + 1) % pts.length]));
  }
  return mul3(s, 0.5);
}

export const polygonArea = (pts) => len3(polygonAreaVector(pts));

/**
 * Volumen eines Solids aus `plate()` / `twisted()`.
 *
 * plate: schiefes Prisma — Grundflaeche x SENKRECHTER Hoehe, also
 *        A * |path . n|. Bei orthogonalem Nh (Regelfall) ist das A * |thick|.
 * loft:  zwischen zwei linear verbundenen, parallelen Sektionen ist der
 *        Querschnitt quadratisch in der Hoehe -> die Prismatoid-Formel
 *        h/6 * (A1 + 4*Am + A2) ist EXAKT, keine Naeherung.
 */
export function solidVolume(solid) {
  if (solid.kind === 'plate') {
    const [outer, ...holes] = solid.loops;
    const av = polygonAreaVector(outer.pts);
    const a = len3(av);
    if (a === 0) return 0;
    const n = mul3(av, 1 / a);
    const area = Math.max(0, a - holes.reduce((s, h) => s + polygonArea(h.pts), 0));
    return area * Math.abs(dot3(solid.path, n));
  }
  if (solid.kind === 'loft') {
    let v = 0;
    for (let i = 0; i + 1 < solid.sections.length; i++) {
      const p = solid.sections[i].pts;
      const q = solid.sections[i + 1].pts;
      const av = polygonAreaVector(p);
      const al = len3(av);
      if (al === 0) continue;
      const n = mul3(av, 1 / al);
      const mid = p.map((pt, j) => mul3(add3(pt, q[j]), 0.5));
      const h = Math.abs(dot3(sub3(q[0], p[0]), n));
      v += (h / 6) * (al + 4 * polygonArea(mid) + polygonArea(q));
    }
    return v;
  }
  throw new TypeError(`solidVolume: unbekannter Solid ${solid && solid.kind}`);
}

// ----------------------------------------------------------------------- Bay
export class Bay {
  /**
   * @param {object} lo  Untergurt-Segment des Feldes (Kurve oder {a, b})
   * @param {object} hi  Handlauf-Segment des Feldes (nur Startpunkt wird genutzt)
   * @param {number[]} nrm  Aussennormale (wird unitisiert)
   * @param {number} seed   Seed fuer `this.rnd`
   */
  constructor(lo, hi, nrm, seed) {
    this.O = curveStart(lo);
    const d = sub3(curveEnd(lo), this.O);
    this.L = len3(d);
    this.Xh = unit3(d);
    const up = sub3(curveStart(hi), this.O);
    this.H = len3(up);
    this.Yh = unit3(up);
    this.Nh = unit3(nrm);
    this.rnd = new PyRandom(seed);
    this.a = [];  // Staebe, Profil Fuellstab
    this.b = [];  // Staebe, Profil Diagonal
    this.st = []; // Stahl-Solids
    this.hz = []; // Holz-Solids
  }

  // -- Abbildung ------------------------------------------------------------
  /** P(s, t, off) = O + Xh*s + Yh*t + Nh*off   (grasshopper/patterns.py:296-297) */
  P(s, t, off = 0) {
    return [
      this.O[0] + this.Xh[0] * s + this.Yh[0] * t + this.Nh[0] * off,
      this.O[1] + this.Xh[1] * s + this.Yh[1] * t + this.Nh[1] * off,
      this.O[2] + this.Xh[2] * s + this.Yh[2] * t + this.Nh[2] * off,
    ];
  }

  /**
   * Umkehrung von P(): Weltpunkt -> [s, t].   (grasshopper/patterns.py:299-315)
   *
   * Xh und Yh sind NICHT orthogonal (Xh folgt der Steigung, Yh ist lotrecht),
   * deshalb ist d.Xh NICHT s. Geloest wird ueber die Gram-Matrix
   * G = [[1, k], [k, 1]] mit k = Xh.Yh:  [dx, dy] = G [s, t]  =>
   * [s, t] = 1/(1-k^2) * [[1, -k], [-k, 1]] [dx, dy].
   *
   * Vorher stand hier das nackte Skalarprodukt — die Anschlusspruefung hat damit
   * JEDES Stabende als "frei" gemeldet, obwohl die Geometrie stimmte. Der Fehler
   * ist in der Ansicht unsichtbar; nur diese Rechnung faengt ihn.
   */
  st_of(p) {
    const d = sub3(p, this.O);
    const k = dot3(this.Xh, this.Yh);
    const dx = dot3(d, this.Xh);
    const dy = dot3(d, this.Yh);
    const det = 1.0 - k * k;
    if (Math.abs(det) < 1e-9) return [dx, dy];
    return [(dx - k * dy) / det, (dy - k * dx) / det];
  }

  /** Einheitenzahl und gedehnter Rapport (grasshopper/patterns.py:317-323). */
  units(rap) {
    let n = Math.trunc(pyRound(this.L / Math.max(rap, 1.0)));
    if (n < 1) n = 1;
    return [n, this.L / n];
  }

  // -- Kurven ---------------------------------------------------------------
  /** Gerade; wird wie im Original nur abgelegt, wenn sie laenger als TOL ist. */
  seg(s0, t0, s1, t1, ch = 'a', off = 0) {
    const c = line(this.P(s0, t0, off), this.P(s1, t1, off));
    if (curveLength(c) > TOL) this[ch].push(c);
  }

  /**
   * Polygonzug — aber als EINZELNE Geraden (grasshopper/patterns.py:331-344).
   * Es entstehen NUR Geraden: geschlossene Ringe werden NICHT in Boegen
   * zerlegt (Soleils Raute ergibt 4 gerade Stuecke). Boegen gibt es
   * ausschliesslich dort, wo ein Muster explizit `arc()` ruft.
   */
  poly(pts, ch = 'a', off = 0) {
    for (let i = 0; i < pts.length - 1; i++) {
      this.seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], ch, off);
    }
  }

  /** 3-Punkte-Bogen; ungueltige Boegen werden verworfen (wie `Arc.IsValid`). */
  arc(p0, pm, p1, ch = 'a', off = 0) {
    const a = arc3(this.P(p0[0], p0[1], off), this.P(pm[0], pm[1], off),
      this.P(p1[0], p1[1], off));
    if (a) this[ch].push(a);
  }

  /** Kubischer Bezier; im Original ohne Laengenpruefung abgelegt. */
  bez(p0, c0, c1, p1, ch = 'a', off = 0) {
    this[ch].push(bezier(this.P(p0[0], p0[1], off), this.P(c0[0], c0[1], off),
      this.P(c1[0], c1[1], off), this.P(p1[0], p1[1], off)));
  }

  /**
   * Bogen durch drei (s,t)-Punkte — als Bezier IM FELDSYSTEM, nicht als
   * Welt-Kreis. Gegenstueck zu `Bay.bow` der Python-Engine.
   *
   * Ein Welt-Kreisbogen ist im geneigten Feld kein Bogen im Feldsystem mehr:
   * Xh folgt der Steigung, Yh ist lotrecht, das System ist schiefwinklig, und
   * der Kreis beult einseitig aus. Ein Bezier ist affin-invariant
   * (Kontrollpunkte abbilden == Kurve abbilden) und bleibt in der konvexen
   * Huelle seiner Kontrollpunkte, also im Feld.
   *
   * Kontrollpunkte: Enden + (4/3)*(Scheitel - Sehnenmitte). Die Kurve laeuft
   * bei u=0.5 exakt durch pm, die Endtangenten sind scheitelparallel — gerade
   * Schenkel schliessen knickfrei an. Abweichung vom Kreisbogen max. ~6 % des
   * Bogenradius, dafuer stimmt die Form in JEDER Feldneigung.
   */
  bow(p0, pm, p1, ch = 'a', off = 0) {
    const vs = (pm[0] - (p0[0] + p1[0]) / 2) * 4 / 3;
    const vt = (pm[1] - (p0[1] + p1[1]) / 2) * 4 / 3;
    this.bez(p0, [p0[0] + vs, p0[1] + vt], [p1[0] + vs, p1[1] + vt], p1, ch, off);
  }

  /**
   * Flacher Bogen durch drei (s,t)-Punkte. Gegenstueck zu `Bay.arc3` der
   * Python-Engine — hier bewusst NICHT `arc3` genannt, weil oben schon eine
   * freie Funktion `arc3(p0,pm,p1)` steht, die einen echten Welt-Kreisbogen
   * baut (und von `arc()` benutzt wird). Ein vertippter Aufruf soll knallen,
   * nicht still den falschen Bogen liefern.
   *
   * Wie `bow()`, aber fuer Boegen, deren Stichhoehe klein gegen die Sehne ist:
   * dort muessen die Endtangenten sehnennah bleiben, nicht scheitelparallel.
   * Kontrollpunkte p + (4/3)*(pm - p): trifft pm bei u=0.5, und die Kurve
   * bleibt beweisbar im Kasten Sehne x Stichhoehe.
   */
  bowFlat(p0, pm, p1, ch = 'a', off = 0) {
    this.bez(
      p0,
      [p0[0] + (pm[0] - p0[0]) * 4 / 3, p0[1] + (pm[1] - p0[1]) * 4 / 3],
      [p1[0] + (pm[0] - p1[0]) * 4 / 3, p1[1] + (pm[1] - p1[1]) * 4 / 3],
      p1, ch, off,
    );
  }

  /**
   * Ein gebogenes Bauteil als seine knickfreien Stuecke ablegen.
   * Bewusst NICHT gejoint (grasshopper/patterns.py:357-367).
   */
  part(curves, ch = 'a') {
    for (const c of curves) {
      if (c && curveLength(c) > TOL) this[ch].push(c);
    }
  }

  // -- Solids ---------------------------------------------------------------
  /** (s,t)-Ringe -> geschlossene Weltpolylinien (grasshopper/patterns.py:370-377). */
  _loops(loops, off) {
    return loops.map((lp) => {
      const pts = lp.map(([s, t]) => this.P(s, t, off));
      // rg.Polyline.IsClosed: mindestens 4 Punkte und erster == letzter.
      const closed = pts.length >= 4 && samePoint(pts[0], pts[pts.length - 1]);
      if (!closed) pts.push([...pts[0]]);
      return polyline(pts, true);
    });
  }

  /**
   * Ebene Platte (Aussenkontur + beliebig viele Aussparungen), nach aussen
   * extrudiert (grasshopper/patterns.py:379-390). loops[0] ist die Aussenkontur.
   *
   * Abweichung vom Original, bewusst und geprueft: `Brep.CreatePlanarBreps`
   * kann bei GETRENNTEN Aussenkonturen mehrere Breps liefern; alle 34 Muster
   * uebergeben aber genau eine Aussenkontur, also entsteht hier genau ein Solid.
   */
  plate(loops, thick, ch = 'st', off = 0) {
    if (!loops || loops.length === 0) return;
    const crvs = this._loops(loops, off);
    if (polygonArea(crvs[0].pts) <= TOL) return; // Rhino liefert hier kein Brep
    this[ch].push({
      kind: 'plate',
      loops: crvs,
      path: mul3(this.Nh, thick),
      thick,
    });
  }

  /** Quader in der Feldebene (grasshopper/patterns.py:392-394). */
  block(s0, t0, s1, t1, thick, ch = 'hz', off = 0) {
    this.plate([[[s0, t0], [s1, t0], [s1, t1], [s0, t1]]], thick, ch, off);
  }

  /**
   * Tordierter Vierkantstab: gedrehte Querschnitte, gerade dazwischen gelooft
   * (grasshopper/patterns.py:396-418). `turns = 1.0` entspricht einer HALBEN
   * Umdrehung (ang = turns * pi * f), nicht einer vollen — so steht es im
   * Original.
   */
  twisted(s, t0, t1, w, turns = 1.0, steps = 9, ch = 'st') {
    const secs = [];
    const h = w / 2.0;
    for (let i = 0; i < steps; i++) {
      const f = i / (steps - 1);
      const ang = turns * Math.PI * f;
      const ca = Math.cos(ang);
      const sa = Math.sin(ang);
      const t = t0 + (t1 - t0) * f;
      const pts = [];
      for (const [dx, dn] of [[-h, -h], [h, -h], [h, h], [-h, h], [-h, -h]]) {
        const rx = dx * ca - dn * sa;
        const rn = dx * sa + dn * ca;
        pts.push(this.P(s + rx, t, rn));
      }
      secs.push(polyline(pts, true));
    }
    this[ch].push({ kind: 'loft', sections: secs, capped: true });
  }
}

export default Bay;
