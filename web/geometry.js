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

// geometry.js — Mesh-Bau für die Geometrie der Muster-Engine.
//
// bay.js liefert reine Daten (Linie, Bogen, Bezier, Polylinie, Blech, Loft).
// Dieses Modul macht daraus three.js-Geometrien; Materialien und Szene bleiben
// in viewer.js. Kein DOM, keine Renderer-Abhängigkeit — dadurch ist die Datei
// unter Node testbar.
//
// ---------------------------------------------------------------------------
// Bezugsrahmen: FESTE Bezugsrichtung, kein mitlaufendes Frenet-System
// ---------------------------------------------------------------------------
// Ein Flachstahl im Geländer steht IMMER mit der breiten Seite nach außen —
// über den ganzen Stab, egal wie sich die Schiene krümmt. Genau das leistet ein
// mitlaufendes Kurvensystem NICHT: die Frenet-Normale kippt an jedem
// Wendepunkt um 180°, und auch die drallminimierten Rahmen von
// THREE.TubeGeometry / ExtrudeGeometry (computeFrenetFrames) drehen den
// Querschnitt entlang der Kurve mit. Bei den Wellen- und Schlaufenmustern ist
// das sofort sichtbar — der Stab verwindet sich, obwohl er in Wirklichkeit
// eben gebogen ist.
//
// Deshalb: eine FESTE Bezugsrichtung N (die Feld-Außennormale, Default
// [0, 1, 0] = quer zum Lauf) und je Stützpunkt
//
//     W = normiert(N x T)     Breitenrichtung, liegt in der Geländerebene
//     U = normiert(T x W)     Dickenrichtung, zeigt nach außen (≈ N)
//
// (W, U, T) ist rechtshändig, also haben Boxen und Ringe positive Determinante
// und damit außen liegende Normalen. Nur wo die Tangente parallel zu N läuft
// (im Geländer nicht vorgesehen) greift eine Ersatzrichtung.
//
// Der Preis: bei einer Tangente, die stark aus der Feldebene kippt, wird der
// Querschnitt in der Projektion schmaler statt sich mitzudrehen. Das ist bei
// ebenen Feldmustern gewollt — der Werkstattstab verhält sich genauso.

import * as THREE from 'three';
import {
  curveLength, curvePointAt, curveTangentAt,
  polygonAreaVector, add3, sub3, mul3, cross3, dot3, unit3, len3,
} from './bay.js';

// Abtastung: ein Stützpunkt je SAMPLE_MM Bogenlänge, nach unten und oben
// geklemmt (kurze Bögen brauchen trotzdem Form, lange Kurven dürfen den
// Speicher nicht sprengen).
export const SAMPLE_MM = 15;
export const MIN_SEGMENTS = 8;
export const MAX_SEGMENTS = 240;
// Rundprofile: dieselbe Facettenzahl wie CylinderGeometry(..., 20) beim geraden
// Stab, damit gerade und gebogene Rundstäbe dieselbe Silhouette haben.
export const ROUND_SEGMENTS = 20;

export const DEFAULT_UP = [0, 1, 0];
const EPS = 1e-9;
const Y_AXIS = new THREE.Vector3(0, 1, 0);

// ------------------------------------------------------------------ Abtastung
function segCount(length) {
  const n = Math.ceil(length / SAMPLE_MM);
  return Math.min(MAX_SEGMENTS, Math.max(MIN_SEGMENTS, Number.isFinite(n) ? n : MIN_SEGMENTS));
}

/**
 * Kurve in Stützpunkte + (nicht normierte) Tangenten zerlegen.
 * Punkt und Tangente kommen aus `curvePointAt` / `curveTangentAt` von bay.js —
 * die Kurvenauswertung wird hier bewusst NICHT nachgebaut.
 */
function sampleCurve(c) {
  const out = [];
  if (c.kind === 'polyline') {
    // Polylinien segmentweise: gleichmäßiges u würde die Knicke verrunden,
    // weil `curvePointAt` die Ecken nicht knotentreu trifft.
    const pts = c.pts;
    for (let i = 0; i + 1 < pts.length; i++) {
      const d = sub3(pts[i + 1], pts[i]);
      const l = len3(d);
      if (l <= EPS) continue;
      const n = Math.min(MAX_SEGMENTS, Math.max(1, Math.ceil(l / SAMPLE_MM)));
      for (let k = 0; k < n; k++) out.push({ p: add3(pts[i], mul3(d, k / n)), t: d });
    }
    if (out.length) {
      out.push({ p: [...pts[pts.length - 1]], t: out[out.length - 1].t });
    }
  } else {
    const segs = segCount(curveLength(c));
    for (let i = 0; i <= segs; i++) {
      const u = i / segs;
      out.push({ p: curvePointAt(c, u), t: curveTangentAt(c, u) });
    }
  }
  // Aufeinanderfolgende Dubletten raus (Bezier mit zusammenfallenden
  // Kontrollpunkten liefert sonst Ringe mit Tangente 0).
  const clean = [];
  for (const s of out) {
    if (!clean.length || len3(sub3(s.p, clean[clean.length - 1].p)) > 1e-7) clean.push(s);
  }
  return clean;
}

/** Feste Bezugsrichtung -> orthonormaler Rahmen (W, U, T) je Stützpunkt. */
function frames(samples, up) {
  const N = unit3(up);
  const M = samples.length;
  return samples.map((s, i) => {
    let T = unit3(s.t);
    if (len3(T) < 0.5) { // entartete Tangente: aus den Nachbarpunkten ersetzen
      T = unit3(sub3(samples[Math.min(i + 1, M - 1)].p, samples[Math.max(i - 1, 0)].p));
    }
    let W = cross3(N, T);
    if (len3(W) < 1e-6) W = cross3([0, 0, 1], T); // Tangente parallel zur Bezugsrichtung
    if (len3(W) < 1e-6) W = cross3([1, 0, 0], T);
    W = unit3(W);
    return { p: s.p, T, W, U: unit3(cross3(T, W)) };
  });
}

// ------------------------------------------------------------------ Querschnitt
/**
 * Querschnitt in (W, U)-Koordinaten.
 *   corners  Eckpunkte der geschlossenen Kontur (gegen den Uhrzeigersinn),
 *            für die Deckel.
 *   cols     Mantelspalten: Punkt + Normale. Rund = eine Spalte je Eckpunkt
 *            (gemeinsame Normalen -> weiche Schattierung); Rechteck = zwei
 *            Spalten je Fläche (eigene Flächennormale -> scharfe Kanten).
 *   quads    Spaltenpaare, die den Mantel aufspannen.
 */
function sectionFor(profile) {
  if (!profile) return null;
  if (profile.section === 'round') {
    const r = (profile.dia || 0) / 2;
    if (!(r > 0)) return null;
    const corners = [];
    const cols = [];
    const quads = [];
    for (let k = 0; k < ROUND_SEGMENTS; k++) {
      const a = (2 * Math.PI * k) / ROUND_SEGMENTS;
      const dir = [Math.cos(a), Math.sin(a)];
      corners.push([dir[0] * r, dir[1] * r]);
      cols.push({ c: [dir[0] * r, dir[1] * r], n: dir });
      quads.push([k, (k + 1) % ROUND_SEGMENTS]);
    }
    return { corners, cols, quads };
  }
  // 'rect' / 'flat': dx quer in der Geländerebene, dia in Dickenrichtung —
  // die BREITE Seite zeigt damit nach außen (Konvention der Flachstahl-
  // Diagonalen, siehe memberMesh in viewer.js).
  const w = (profile.dx ?? profile.dia) / 2;
  const h = (profile.dia ?? profile.dx) / 2;
  if (!(w > 0) || !(h > 0)) return null;
  const corners = [[-w, -h], [w, -h], [w, h], [-w, h]];
  const cols = [];
  const quads = [];
  for (let k = 0; k < 4; k++) {
    const a = corners[k];
    const b = corners[(k + 1) % 4];
    const ex = b[0] - a[0];
    const ey = b[1] - a[1];
    const el = Math.hypot(ex, ey);
    const n = [ey / el, -ex / el]; // Rechtsnormale einer CCW-Kontur zeigt nach außen
    cols.push({ c: a, n }, { c: b, n });
    quads.push([2 * k, 2 * k + 1]);
  }
  return { corners, cols, quads };
}

// ------------------------------------------------------------------ Mantelbau
/** Rahmenkette + Querschnitt -> geschlossener Körper (Mantel + beide Deckel). */
function sweptSolid(fr, sec) {
  const M = fr.length;
  const C = sec.cols.length;
  const R = sec.corners.length;
  const pos = [];
  const nor = [];
  const idx = [];

  const at = (f, w, u) => [
    f.p[0] + f.W[0] * w + f.U[0] * u,
    f.p[1] + f.W[1] * w + f.U[1] * u,
    f.p[2] + f.W[2] * w + f.U[2] * u,
  ];

  for (const f of fr) {
    for (const col of sec.cols) {
      pos.push(...at(f, col.c[0], col.c[1]));
      nor.push(...unit3(add3(mul3(f.W, col.n[0]), mul3(f.U, col.n[1]))));
    }
  }
  for (let i = 0; i + 1 < M; i++) {
    for (const [a, b] of sec.quads) {
      const v00 = i * C + a;
      const v01 = i * C + b;
      const v10 = (i + 1) * C + a;
      const v11 = (i + 1) * C + b;
      idx.push(v00, v01, v11, v00, v11, v10);
    }
  }

  // Deckel: Fächer um den Querschnittsschwerpunkt (die Querschnitte sind
  // konvex — Kreis und Rechteck).
  let cw = 0;
  let cu = 0;
  for (const [w, u] of sec.corners) { cw += w / R; cu += u / R; }
  for (const [end, sgn] of [[0, -1], [M - 1, 1]]) {
    const f = fr[end];
    const base = pos.length / 3;
    const nrm = mul3(f.T, sgn);
    for (const [w, u] of sec.corners) { pos.push(...at(f, w, u)); nor.push(...nrm); }
    pos.push(...at(f, cw, cu));
    nor.push(...nrm);
    const mid = base + R;
    for (let j = 0; j < R; j++) {
      const a = base + j;
      const b = base + ((j + 1) % R);
      if (sgn > 0) idx.push(mid, a, b); else idx.push(mid, b, a);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  geo.setIndex(idx);
  return orientOutward(geo);
}

/**
 * Gerades Stück — bewusst dieselbe Bauart wie `memberMesh` in viewer.js
 * (CylinderGeometry mit 20 Segmenten bzw. BoxGeometry + makeBasis), damit
 * gerade Musterstäbe exakt aussehen wie die Konstruktionsstäbe.
 */
function straightGeometry(a, b, profile, up) {
  const A = new THREE.Vector3(...a);
  const B = new THREE.Vector3(...b);
  const axis = B.clone().sub(A);
  const len = axis.length();
  if (len <= EPS) return null;
  axis.normalize();
  const mid = A.clone().add(B).multiplyScalar(0.5);
  let geo;
  if (profile.section === 'round') {
    const r = (profile.dia || 0) / 2;
    if (!(r > 0)) return null;
    geo = new THREE.CylinderGeometry(r, r, len, ROUND_SEGMENTS);
    geo.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(Y_AXIS, axis));
  } else {
    const dx = profile.dx ?? profile.dia;
    const dy = profile.dia ?? profile.dx;
    if (!(dx > 0) || !(dy > 0)) return null;
    const t = [axis.x, axis.y, axis.z];
    let W = cross3(unit3(up), t);
    if (len3(W) < 1e-6) W = cross3([0, 0, 1], t);
    if (len3(W) < 1e-6) W = cross3([1, 0, 0], t);
    W = unit3(W);
    const U = unit3(cross3(t, W)); // Dicke nach außen -> breite Seite außen
    geo = new THREE.BoxGeometry(dx, dy, len);
    geo.applyMatrix4(new THREE.Matrix4().makeBasis(
      new THREE.Vector3(...W), new THREE.Vector3(...U), axis,
    ));
  }
  geo.translate(mid.x, mid.y, mid.z);
  return geo;
}

/**
 * Profil entlang einer beliebigen Kurve (line | arc | bezier | polyline).
 * @returns {THREE.BufferGeometry|null} null, wo nichts Sinnvolles entsteht.
 */
export function sweepGeometry(curve, profile, up = DEFAULT_UP) {
  if (!curve || !profile) return null;
  const sec = sectionFor(profile);
  if (!sec) return null;
  if (curve.kind === 'line') return straightGeometry(curve.a, curve.b, profile, up);
  const samples = sampleCurve(curve);
  if (samples.length < 2) return null;
  return sweptSolid(frames(samples, up), sec);
}

// ------------------------------------------------------------------ Blech
/** Ring einer Platte/eines Lofts als offene Punktliste (Schlusspunkt weg). */
function ringPts(loop) {
  const src = Array.isArray(loop) ? loop : (loop && loop.pts);
  if (!src) return [];
  const pts = src.map((p) => [...p]);
  while (pts.length > 1 && len3(sub3(pts[0], pts[pts.length - 1])) <= 1e-9) pts.pop();
  return pts;
}

const signedArea2 = (v) => {
  let s = 0;
  for (let i = 0; i < v.length; i++) {
    const a = v[i];
    const b = v[(i + 1) % v.length];
    s += a.x * b.y - b.x * a.y;
  }
  return s / 2;
};

/**
 * Laserblech: Außenkontur + Aussparungen, entlang `path` extrudiert.
 *
 * Die Ringe sind ebene Weltpolygone. Sie werden in ihre eigene Ebene projiziert
 * (Basis e1, e2 aus der Ringnormalen), dort als THREE.Shape mit THREE.Path-
 * Löchern aufgebaut, mit Tiefe 1 extrudiert und anschließend mit
 * makeBasis(e1, e2, path) zurücktransformiert. Weil `path` NICHT parallel zur
 * Ringnormalen sein muss, ist das Ergebnis ein SCHIEFES Prisma — genau das
 * Volumenmodell von `solidVolume` in bay.js (Fläche x |path·n|).
 *
 * Wicklung: Löcher müssen entgegen der Außenkontur laufen, sonst schneiden sie
 * nicht. Das wird hier explizit erzwungen (nicht auf die interne Korrektur von
 * ExtrudeGeometry vertraut) und über das Volumen nachgewiesen.
 */
export function plateGeometry(plate) {
  const rings = (plate && plate.loops ? plate.loops : []).map(ringPts)
    .filter((r) => r.length >= 3);
  if (!rings.length) return null;
  const [outer, ...holes] = rings;

  const av = polygonAreaVector(outer);
  const area = len3(av);
  if (area <= EPS) return null;
  const n = mul3(av, 1 / area);
  const path = plate.path && len3(plate.path) > EPS ? plate.path : mul3(n, plate.thick || 0);
  if (len3(path) <= EPS) return null;

  // Erste nicht entartete, in der Ebene liegende Kante als 1. Basisrichtung.
  let e1 = null;
  for (let i = 1; i < outer.length && !e1; i++) {
    const d = sub3(outer[i], outer[0]);
    const perp = sub3(d, mul3(n, dot3(d, n)));
    if (len3(perp) > EPS) e1 = unit3(perp);
  }
  if (!e1) return null;
  // Zeigt `path` gegen die Ringnormale, wird e2 gespiegelt: nur so bleibt die
  // Determinante von makeBasis(e1, e2, path) positiv und das Blech behält seine
  // Außenseite außen.
  const flip = dot3(path, n) < 0;
  const e2 = flip ? cross3(e1, n) : cross3(n, e1);
  const o = outer[0];
  const to2 = (p) => {
    const d = sub3(p, o);
    return new THREE.Vector2(dot3(d, e1), dot3(d, e2));
  };

  const outer2 = outer.map(to2);
  const shape = new THREE.Shape(outer2);
  const sOuter = Math.sign(signedArea2(outer2));
  for (const h of holes) {
    const h2 = h.map(to2);
    const sh = Math.sign(signedArea2(h2));
    if (sh === 0) continue;
    if (sh === sOuter) h2.reverse(); // gleiche Wicklung wie außen = kein Loch
    shape.holes.push(new THREE.Path(h2));
  }

  const geo = new THREE.ExtrudeGeometry(shape, { depth: 1, bevelEnabled: false, steps: 1 });
  const m = new THREE.Matrix4().makeBasis(
    new THREE.Vector3(...e1), new THREE.Vector3(...e2), new THREE.Vector3(...path),
  );
  m.setPosition(o[0], o[1], o[2]);
  geo.applyMatrix4(m);
  return orientOutward(geo);
}

// ------------------------------------------------------------------ Loft
/**
 * Tordierter Stab: zwischen aufeinanderfolgenden Querschnitten vernäht,
 * beide Enden gedeckelt.
 *
 * Die Ringe MÜSSEN gleich viele Punkte haben und in gleicher Reihenfolge
 * laufen — `Bay.twisted` erzeugt sie genau so. Ein Versatz um eins ergäbe
 * einen sichtbar verscherten Stab, deshalb wird die Bedingung hart geprüft
 * statt still zu reparieren.
 *
 * Dreieckszahl = (Sektionen - 1) * Ringpunkte * 2 + 2 * Ringpunkte
 * (Mantel + zwei Schwerpunktfächer).
 */
export function loftGeometry(loft) {
  const rings = (loft && loft.sections ? loft.sections : []).map(ringPts);
  if (rings.length < 2) return null;
  const R = rings[0].length;
  if (R < 3) return null;
  for (const r of rings) {
    if (r.length !== R) {
      throw new TypeError(`loftGeometry: Sektionen mit ${R} und ${r.length} Punkten — `
        + 'die Querschnitte eines Lofts müssen punktweise korrespondieren');
    }
  }
  const S = rings.length;
  const pos = [];
  const tri = (a, b, c) => { pos.push(...a, ...b, ...c); };

  for (let i = 0; i + 1 < S; i++) {
    for (let j = 0; j < R; j++) {
      const jn = (j + 1) % R;
      const A = rings[i][j];
      const B = rings[i][jn];
      const C = rings[i + 1][jn];
      const D = rings[i + 1][j];
      tri(A, B, C);
      tri(A, C, D);
    }
  }
  for (const [i, sgn] of [[0, -1], [S - 1, 1]]) {
    const ring = rings[i];
    let c = [0, 0, 0];
    for (const p of ring) c = add3(c, mul3(p, 1 / R));
    for (let j = 0; j < R; j++) {
      const a = ring[j];
      const b = ring[(j + 1) % R];
      if (sgn > 0) tri(c, a, b); else tri(c, b, a);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals(); // nicht indiziert -> Flächennormalen, scharfe Kanten
  return orientOutward(geo);
}

/** Solid nach `kind` bauen. Unbekannte Arten liefern null (kein stiller Ersatz). */
export function solidGeometry(solid) {
  if (!solid) return null;
  if (solid.kind === 'plate') return plateGeometry(solid);
  if (solid.kind === 'loft') return loftGeometry(solid);
  return null;
}

// ------------------------------------------------------------------ Prüfhilfen
/**
 * Vorzeichenbehaftetes Volumen über den Divergenzsatz: V = 1/6 * sum a·(b x c).
 * Für einen geschlossenen Körper mit außen liegenden Normalen positiv und
 * gleich dem echten Volumen — damit prüfbar gegen `solidVolume` aus bay.js.
 */
export function signedVolume(geo) {
  const pos = geo.getAttribute('position');
  const index = geo.getIndex();
  const count = index ? index.count : pos.count;
  const gi = (k) => (index ? index.getX(k) : k);
  let v = 0;
  for (let k = 0; k + 2 < count; k += 3) {
    const a = gi(k);
    const b = gi(k + 1);
    const c = gi(k + 2);
    const ax = pos.getX(a); const ay = pos.getY(a); const az = pos.getZ(a);
    const bx = pos.getX(b); const by = pos.getY(b); const bz = pos.getZ(b);
    const cx = pos.getX(c); const cy = pos.getY(c); const cz = pos.getZ(c);
    v += (ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)) / 6;
  }
  return v;
}

function swapItems(attr, i, j) {
  const n = attr.itemSize;
  const arr = attr.array;
  for (let k = 0; k < n; k++) {
    const t = arr[i * n + k];
    arr[i * n + k] = arr[j * n + k];
    arr[j * n + k] = t;
  }
}

/**
 * Umlaufsinn nachziehen: ist das vorzeichenbehaftete Volumen negativ, liegt der
 * Körper auf links (Normalen nach innen, Rückseiten zur Kamera). Dann werden
 * alle Dreiecke gedreht und die Normalen umgekehrt.
 */
export function orientOutward(geo) {
  if (signedVolume(geo) >= 0) return geo;
  const index = geo.getIndex();
  if (index) {
    const a = index.array;
    for (let i = 0; i + 2 < a.length; i += 3) {
      const t = a[i + 1]; a[i + 1] = a[i + 2]; a[i + 2] = t;
    }
    index.needsUpdate = true;
  } else {
    for (const attr of Object.values(geo.attributes)) {
      for (let i = 0; i + 2 < attr.count; i += 3) swapItems(attr, i + 1, i + 2);
      attr.needsUpdate = true;
    }
  }
  const nrm = geo.getAttribute('normal');
  if (nrm) {
    const a = nrm.array;
    for (let i = 0; i < a.length; i++) a[i] = -a[i];
    nrm.needsUpdate = true;
  }
  return geo;
}
