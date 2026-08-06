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

// 3D-Vorschau (three.js) + Szenenaufbau aus dem Modell + Export (OBJ/STL/PNG).
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { OBJExporter } from './vendor/OBJExporter.js';
import { STLExporter } from './vendor/STLExporter.js';
import { sweepGeometry, plateGeometry, loftGeometry, DEFAULT_UP } from './geometry.js';

const MAT = {
  stahl: new THREE.MeshStandardMaterial({ color: 0x23262b, metalness: 0.75, roughness: 0.45 }),
  diagonale: new THREE.MeshStandardMaterial({ color: 0x1b1d21, metalness: 0.8, roughness: 0.4 }),
  platte: new THREE.MeshStandardMaterial({ color: 0x3a3f46, metalness: 0.7, roughness: 0.55 }),
  bolzen: new THREE.MeshStandardMaterial({ color: 0x8a919b, metalness: 0.9, roughness: 0.35 }),
  stufe: new THREE.MeshStandardMaterial({ color: 0xcf9046, roughness: 0.85 }),
  // Muster-Solids: Stahlblech dunkler und matter als die Ankerplatte, damit
  // Laserteil und Montageplatte im Bild unterscheidbar bleiben; Holz in der
  // Farbfamilie der Stufen, aber heller — Stahl vs. Holz muss auf einen Blick
  // erkennbar sein.
  blech: new THREE.MeshStandardMaterial({ color: 0x2e333a, metalness: 0.7, roughness: 0.5 }),
  holz: new THREE.MeshStandardMaterial({ color: 0xb8834a, metalness: 0.0, roughness: 0.8 }),
};

const Y = new THREE.Vector3(0, 1, 0);

// Gerades Stabelement a->b mit Katalogquerschnitt; Orientierungskonvention je Rolle
// (Flachstahl-Diagonalen: breite Seite nach außen).
function memberMesh(m) {
  const a = new THREE.Vector3(...m.a), b = new THREE.Vector3(...m.b);
  const axis = b.clone().sub(a);
  const len = axis.length();
  axis.normalize();
  const mid = a.clone().add(b).multiplyScalar(0.5);
  let geo;
  if (m.profile.section === 'round') {
    geo = new THREE.CylinderGeometry(m.profile.dia / 2, m.profile.dia / 2, len, 20);
    const q = new THREE.Quaternion().setFromUnitVectors(Y, axis);
    geo.applyQuaternion(q);
  } else {
    const dx = m.profile.dx, dy = m.profile.dia;
    let u, v; // u trägt dx, v trägt dy
    if (m.role === 'handlauf' || m.role === 'untergurt') {
      u = new THREE.Vector3(0, 1, 0);                    // Breite quer
      v = axis.clone().cross(Y).normalize();             // Dicke "vertikal" zur Neigung
    } else if (m.role === 'diagonale') {
      // Y x axis, NICHT axis x Y: sonst ist (u, v, axis) linkshändig, makeBasis
      // spiegelt die Box und das Stück wird auf links gedreht gerendert
      // (Normalen nach innen, Vorderseiten weggeschnitten). Gleiche Gerade,
      // gleiche Silhouette — der symmetrische Querschnitt merkt den
      // Richtungswechsel nicht.
      u = Y.clone().cross(axis).normalize();             // Breite in der Geländerebene
      v = new THREE.Vector3(0, 1, 0);                    // Dicke nach außen
    } else {                                             // Posten, Füllstäbe (vertikal)
      u = new THREE.Vector3(1, 0, 0);
      v = new THREE.Vector3(0, 1, 0);
    }
    geo = new THREE.BoxGeometry(dx, dy, len);
    const mtx = new THREE.Matrix4().makeBasis(u, v, axis);
    geo.applyMatrix4(mtx);
  }
  geo.translate(mid.x, mid.y, mid.z);
  const mesh = new THREE.Mesh(geo, m.role === 'diagonale' ? MAT.diagonale : MAT.stahl);
  mesh.name = m.role;
  mesh.castShadow = mesh.receiveShadow = true;
  return mesh;
}

// --------------------------------------------------------------- Muster-Meshes
// Die Muster-Engine (bay.js/patterns.js) liefert Kurven statt Punktpaaren und
// zusätzlich Solids (Laserblech, tordierter Stab). Der Geometriebau steht in
// geometry.js; hier kommen nur Material, Name und Schattenflags dazu.

// Kanal 'a' = Füllstab-Profil, Kanal 'b' = Diagonal-Profil — dieselbe
// Farbtrennung wie bei den Konstruktionsstäben.
const CHANNEL_MAT = { a: MAT.stahl, b: MAT.diagonale };
const SOLID_MAT = { steel: MAT.blech, stahl: MAT.blech, wood: MAT.holz, holz: MAT.holz };

function finish(geo, material, name) {
  if (!geo) return null;
  const mesh = new THREE.Mesh(geo, material);
  mesh.name = name;
  mesh.castShadow = mesh.receiveShadow = true;
  return mesh;
}

/** Profil entlang einer Musterkurve (line | arc | bezier | polyline). */
export function sweepMesh(curve, profile, channel = 'a', up = DEFAULT_UP) {
  return finish(sweepGeometry(curve, profile, up),
    CHANNEL_MAT[channel] || MAT.stahl, `muster-${channel}`);
}

/** Laserblech mit Aussparungen. */
export function plateMesh(plate, material = 'steel') {
  return finish(plateGeometry(plate), SOLID_MAT[material] || MAT.blech, 'muster-blech');
}

/** Tordierter Stab (Loft über gedrehte Querschnitte). */
export function loftMesh(loft, material = 'steel') {
  return finish(loftGeometry(loft), SOLID_MAT[material] || MAT.blech, 'muster-loft');
}

/** Dispatch nach `kind`; unbekannte Arten werden übersprungen, nicht ersetzt. */
export function solidMesh(solid, material) {
  if (!solid) return null;
  if (solid.kind === 'plate') return plateMesh(solid, material);
  if (solid.kind === 'loft') return loftMesh(solid, material);
  return null;
}

export class Viewer {
  constructor(container) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xdde3ea);
    this.scene.fog = new THREE.Fog(0xdde3ea, 18000, 45000);

    this.camera = new THREE.PerspectiveCamera(45, 1, 10, 200000);
    this.camera.position.set(-3500, -4500, 3200);
    this.camera.up.set(0, 0, 1); // z ist oben (mm-Koordinaten des Modells)

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(2000, 600, 1500);
    this.controls.enableDamping = true;

    const hemi = new THREE.HemisphereLight(0xffffff, 0x668899, 0.9);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(-4000, -6000, 9000);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const s = 7000;
    Object.assign(sun.shadow.camera, { left: -s, right: s, top: s, bottom: -s, far: 40000 });
    sun.target.position.set(2000, 600, 0);
    this.scene.add(sun, sun.target);

    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(30000, 48),
      new THREE.MeshStandardMaterial({ color: 0xc9cfd6, roughness: 1 }),
    );
    ground.position.z = -40;
    ground.receiveShadow = true;
    this.scene.add(ground);

    this.group = new THREE.Group(); // das exportierbare Geländer
    this.stairsGroup = new THREE.Group();
    this.scene.add(this.group, this.stairsGroup);

    new ResizeObserver(() => this.resize()).observe(container);
    this.resize();
    this.renderer.setAnimationLoop(() => {
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    });
  }

  resize() {
    const w = this.container.clientWidth || 1, h = this.container.clientHeight || 1;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  update(model) {
    // Alle Geometrien beider Gruppen freigeben — das gilt auch für die
    // Muster-Meshes, weil die unten in `this.group` landen. Materialien bleiben
    // absichtlich stehen: MAT.* wird von allen Meshes geteilt und über die
    // ganze Sitzung wiederverwendet.
    for (const g of [this.group, this.stairsGroup]) {
      g.traverse((o) => o.geometry?.dispose());
      g.clear();
    }
    for (const m of model.members) this.group.add(memberMesh(m));
    // Muster-Geometrie, falls das Modell sie liefert. Fehlt `model.pattern`
    // (Modellschicht noch ohne Musteranbindung), bleibt es beim bisherigen
    // Verhalten statt einer Ausnahme.
    const pattern = model.pattern;
    if (pattern) {
      const up = pattern.normal || DEFAULT_UP;
      for (const s of pattern.sweeps || []) {
        const mesh = sweepMesh(s.curve, s.profile, s.channel, up);
        if (mesh) this.group.add(mesh);
      }
      for (const s of pattern.solids || []) {
        const mesh = solidMesh(s.solid, s.material);
        if (mesh) this.group.add(mesh);
      }
    }
    for (const pl of model.plates) {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(...pl.size), MAT.platte);
      mesh.position.set(...pl.center);
      mesh.name = 'ankerplatte';
      mesh.castShadow = mesh.receiveShadow = true;
      this.group.add(mesh);
    }
    for (const b of model.bolts) {
      const a = new THREE.Vector3(...b.a), bb = new THREE.Vector3(...b.b);
      const axis = bb.clone().sub(a), len = axis.length();
      const geo = new THREE.CylinderGeometry(b.dia / 2, b.dia / 2, len, 12);
      geo.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(Y, axis.normalize()));
      const mesh = new THREE.Mesh(geo, MAT.bolzen);
      mesh.position.copy(a.add(bb).multiplyScalar(0.5));
      mesh.name = 'bolzen';
      this.group.add(mesh);
    }
    for (const st of model.steps) {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(...st.size), MAT.stufe);
      mesh.position.set(...st.center);
      mesh.castShadow = mesh.receiveShadow = true;
      this.stairsGroup.add(mesh);
    }
  }

  frame(model) {
    const mid = new THREE.Vector3(model.params.lauflaenge / 2, 400,
      model.params.steigung / 2 + model.params.gelaenderhoehe / 2);
    this.controls.target.copy(mid);
    const d = Math.max(model.slopeLen, 2500);
    this.camera.position.set(mid.x - d * 0.55, mid.y - d * 1.05, mid.z + d * 0.5);
  }

  // Gruppen für den Export vorübergehend in eine Wurzel umhängen (Exporter lesen
  // matrixWorld), danach zurück in die Szene.
  _withExportRoot(withStairs, fn) {
    const tmp = new THREE.Group();
    tmp.add(this.group);
    if (withStairs) tmp.add(this.stairsGroup);
    tmp.updateMatrixWorld(true);
    try {
      return fn(tmp);
    } finally {
      this.scene.add(this.group, this.stairsGroup);
    }
  }

  exportOBJ(withStairs) {
    return this._withExportRoot(withStairs, (tmp) => new OBJExporter().parse(tmp));
  }

  exportSTL(withStairs) {
    return this._withExportRoot(withStairs, (tmp) =>
      new STLExporter().parse(tmp, { binary: true }));
  }

  screenshotPNG() {
    this.renderer.render(this.scene, this.camera);
    return this.renderer.domElement.toDataURL('image/png');
  }
}
