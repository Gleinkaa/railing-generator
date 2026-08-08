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

/*
 * Packt die Web-App zu EINER Datei ohne jede Nachbarschaft: Stylesheet, alle
 * ES-Module und das vendored three.js wandern inline. Ergebnis ist eine HTML-
 * Datei, die per Doppelklick aus dem Dateisystem laeuft (file://) und die sich
 * dorthin haengen laesst, wo kein Webserver steht — Wiki-Anhang, USB-Stick,
 * gehostete Artefakt-Seite, Mail an den Fertiger.
 *
 * WARUM UEBERHAUPT EIN BUILD: Die App selbst bleibt build- und
 * abhaengigkeitsfrei; `web/` laeuft weiter direkt aus einem statischen Server.
 * Nur dieses Verpacken braucht einen Bundler, weil `file://` keine ES-Module
 * ueber relative Pfade laedt (CORS) und eine Artefakt-Seite keine
 * Nebendateien hat. esbuild ist deshalb bewusst NICHT in package.json
 * eingetragen — es wird nur fuer diesen einen Schritt geholt:
 *
 *   npx --yes esbuild@0.25 --version   # einmalig, holt den Bundler
 *   node tools/build-artifact.mjs      # schreibt dist/
 *
 * Ausgabe:
 *   dist/railing-generator.html            eigenstaendige Seite (file://-faehig)
 *   dist/railing-generator.artifact.html   Rumpf ohne <html>/<head>/<body>,
 *                                          fuer Hosts, die ein Grundgeruest
 *                                          selbst drumherumlegen.
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const WEB = join(ROOT, 'web');
const DIST = join(ROOT, 'dist');

// esbuild liegt nicht im Repository. Aufloesung in dieser Reihenfolge:
// lokale node_modules, dann der npx-Cache des Aufrufers via NODE_PATH.
async function ladeEsbuild() {
  const require = createRequire(import.meta.url);
  try {
    return await import(require.resolve('esbuild', { paths: [ROOT, process.cwd()] }));
  } catch {
    throw new Error(
      'esbuild nicht gefunden. Einmalig holen, dann erneut starten:\n' +
      '  npm i --no-save esbuild\n' +
      'Die App selbst braucht esbuild nicht — nur dieses Verpacken.',
    );
  }
}

// Der Rumpf von web/index.html ist die Quelle der Wahrheit fuer das Markup.
// Er wird herausgeschnitten statt kopiert, damit eine Aenderung am Panel nicht
// an zwei Stellen nachgezogen werden muss. Das <script type="module"> faellt
// raus — das Bundle tritt an seine Stelle.
async function rumpfAusIndex() {
  const html = await readFile(join(WEB, 'index.html'), 'utf8');
  const m = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  if (!m) throw new Error('web/index.html: kein <body> gefunden');
  return m[1].replace(/<script\b[\s\S]*?<\/script>/gi, '').trimEnd();
}

async function bundle(esbuild) {
  const out = await esbuild.build({
    entryPoints: [join(WEB, 'main.js')],
    bundle: true,
    format: 'iife',
    // Ziel bewusst modern: die App nutzt ohnehin ES-Module, optionale
    // Verkettung und `structuredClone`-freie, aber neue Array-Methoden.
    target: ['chrome110', 'firefox110', 'safari16'],
    minify: true,
    legalComments: 'none',
    write: false,
    // Der blosse Bezeichner `three` ist in web/index.html per Import-Map auf
    // das vendored Modul gelegt. Import-Maps gibt es beim Bundeln nicht,
    // also dieselbe Zuordnung noch einmal fuer esbuild.
    alias: { three: join(WEB, 'vendor', 'three.module.min.js') },
    logLevel: 'silent',
  });
  return out.outputFiles[0].text;
}

// `</script>` im Quelltext wuerde den umgebenden Script-Block vorzeitig
// schliessen — der HTML-Parser sieht die Zeichenkette, nicht das JavaScript.
const scriptSicher = (js) => js.replace(/<\/script/gi, '<\\/script');

function seite({ css, html, js, fragment }) {
  const kopf = fragment
    ? // Der Host liefert <html>/<head>/<body>. Die App will die volle
      // Viewport-Hoehe; ohne diese Zeilen kollabiert das 100%-Layout auf die
      // Inhaltshoehe und der Viewer bekommt eine Canvas von 0 Pixeln.
      `<title>Railing Generator — parametrischer Geländer-Generator</title>\n` +
      `<style>\n:root { color-scheme: dark; }\nhtml, body { height: 100%; overflow: hidden; }\n${css}</style>`
    : `<!DOCTYPE html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n` +
      `<meta name="viewport" content="width=device-width, initial-scale=1">\n` +
      `<title>Railing Generator — parametrischer Geländer-Generator</title>\n` +
      `<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='13' font-size='13'>🛠</text></svg>">\n` +
      `<style>\n:root { color-scheme: dark; }\n${css}</style>\n</head>\n<body>`;

  const fuss = fragment ? '' : '\n</body>\n</html>';
  return `${kopf}\n${html}\n<script>\n${scriptSicher(js)}\n</script>${fuss}\n`;
}

const esbuild = await ladeEsbuild();
const [css, html, js] = await Promise.all([
  readFile(join(WEB, 'style.css'), 'utf8'),
  rumpfAusIndex(),
  bundle(esbuild),
]);

await mkdir(DIST, { recursive: true });
for (const [name, fragment] of [['railing-generator.html', false], ['railing-generator.artifact.html', true]]) {
  const text = seite({ css, html, js, fragment });
  await writeFile(join(DIST, name), text);
  console.log(`dist/${name}  ${(Buffer.byteLength(text) / 1024).toFixed(0)} kB`);
}
