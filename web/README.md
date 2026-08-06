# Railing Generator — Web-App

Portierung der Grasshopper-Engine als eigenständige, einbettbare Webseite:
gleiche Modelllogik, gleiche Stückliste, **alle 34 Muster**. Kein Build-Schritt,
keine externen Abhängigkeiten — three.js liegt vendored in `vendor/`.

Die fachliche Wahrheit steht in [`docs/SPEC.md`](../docs/SPEC.md); die
CAD-Seite in [`grasshopper/`](../grasshopper/). Der Vertrag zwischen beiden
Implementierungen sind die Regressionstests in `test/` — sie pinnen die
Web-App auf die Referenzwerte aus [`reference/README.md`](../reference/README.md).

## Wie die Muster-Engine aufgebaut ist

Die 34 Muster sind kein Katalog von Zeichnungen, sondern 34 Funktionen über
dem Feld (Bay). Der Aufbau spiegelt die Grasshopper-Engine Datei für Datei:

| Datei | Inhalt |
|---|---|
| `bay.js` | Das feldlokale **(s, t)-System** und die Geometrie-Emitter — 1:1-Portierung von `class Bay` aus `grasshopper/patterns.py`. Enthält außerdem eine Portierung von CPythons `random.Random` (MT19937), damit die Zufallsmuster bei gleichem Seed **dieselbe** Geometrie liefern wie Rhino. |
| `patterns.js` | Die Tabelle `DESIGNS` (34 Einträge, **Index = Reglerwert 0–33**), die Zuordnung Schlüssel → Bauroutine, die Rapport-Deckelung und der Seed-Aufbau. |
| `patterns/` | Die Bauroutinen selbst, nach Familie getrennt: `formed.js` (00–09), `organic.js` (10–15), `rhythm.js` (16–24), `lines.js` (25–33). Dazu `params.js` (Fertigungsmaße) und `shared.js`. |

**Der Index ist der Vertrag.** Muster 30 in dieser App ist Muster 30 am
Grasshopper-Regler. Wer die Reihenfolge umsortiert, bricht die
Vergleichbarkeit beider Engines und die gepinnten Referenzmassen.

Warum `s`/`t` und nicht x/y: `s` läuft als Bogenlänge die Steigung entlang,
`t` steht lotrecht — genau so, wie ein Geländer gebaut wird. Die beiden Achsen
sind deshalb **absichtlich nicht orthogonal**; die Details stehen im
Kopfkommentar von `bay.js`.

## Funktionen

* **34 Muster** — nach Familie gruppiert (Formed · Organic · Rhythm · Lines),
  mit Dichte-Regler (Rapport-Faktor) und Seed für die fünf Zufallsmuster.
  Der Rapport wird automatisch gedeckelt, damit die lichte Weite die Grenze
  nicht überschreitet; die App weist darauf hin, wenn der Deckel greift.
* **Parametrik** — Lauflänge/Steigung, Geländerhöhe, Untergurt-Abstand,
  Pfostenteilung automatisch ≤ 1200 mm (Eurocode-Holmdruck).
* **Profile** — kompletter Katalog (`docs/profiles.md`) für Handlauf,
  Untergurt, Posten sowie die beiden Musterkanäle; Querschnitt und kg/m kommen
  aus derselben Katalogzeile, Geometrie und Masse können also nie
  auseinanderlaufen.
* **Montage** — seitlich (Fascia-Ankerplatte) oder aufgesetzt (Fußplatte),
  Plattenmaße live in der Stückliste.
* **Stückliste** live, inklusive der Muster, die als Blech oder Holz statt als
  Stabwerk anfallen (diese werden über Volumen × Dichte verwogen).
* **Compliance-Hinweise** (OIB RL 4 / ÖNORM B 5371) live.
* **Export** — OBJ, STL (binär), Stückliste als CSV (`;`-getrennt,
  Excel-tauglich), Konfiguration als JSON (wieder ladbar), Ansicht als PNG.

## Lokal starten

ES-Module brauchen einen HTTP-Server (`file://` funktioniert nicht). Aus dem
**Repository-Wurzelverzeichnis**, nicht aus `web/`:

```sh
python -m http.server 8080
```

Dann `http://localhost:8080/web/` öffnen.

Tests (Node ≥ 18):

```sh
node --test web/test/
```

## In eine Webseite einbetten

Das Repository auf einen beliebigen statischen Host legen (GitHub Pages,
Netlify, Vercel, eigener Server). Der Workflow `.github/workflows/pages.yml`
deployt automatisch auf GitHub Pages, sobald unter *Settings → Pages* als
Source „GitHub Actions" gewählt ist. Dann per iframe einbetten:

```html
<iframe
  src="https://gleinkaa.github.io/railing-generator/"
  style="width: 100%; height: 720px; border: 0; border-radius: 8px;"
  title="Railing Generator"
  loading="lazy"></iframe>
```

Die Seite ist responsiv (unter 760 px wandert das Panel unter die 3D-Ansicht)
und hat keine externen Abhängigkeiten — funktioniert daher auch hinter
strikter CSP, solange das iframe von derselben Quelle geladen werden darf.

> **Lizenzhinweis:** Das Einbetten auf einer öffentlich erreichbaren Website
> ist Netzwerknutzung im Sinne von **AGPL § 13**. Wer das ohne Offenlegung des
> eigenen Stacks tun möchte, braucht eine kommerzielle Lizenz — siehe
> [`COMMERCIAL-LICENSE.md`](../COMMERCIAL-LICENSE.md).

## Übrige Dateien

| Datei | Inhalt |
|---|---|
| `catalog.js` | Profilkatalog (Portierung von `grasshopper/profiles.py`) |
| `model.js` | Parametrisches Modell + Stückliste + Compliance (reine Logik, ohne Rendering) |
| `viewer.js` | three.js-Szene, Meshaufbau, OBJ/STL/PNG-Export |
| `main.js` | UI-Regler, Stücklisten-Anzeige, Export-Verdrahtung |
| `test/` | Regression gegen die Grasshopper-Referenzwerte |
| `vendor/` | three.js (Modul, OrbitControls, OBJ/STL-Exporter) |

## Hinweise

Alle Maße in Millimetern.

Stabwerk wird über die Katalog-Metergewichte verwogen, Bleche und Holz über
Volumen × Dichte. Die **Holzdichte ist eine Annahme** (Eiche, ~700 kg/m³) und
kein aus der Engine übernommener Referenzwert — für andere Holzarten anpassen.

Die Prüfung ist **geometrisch**: Höhen, lichte Weiten, Spalte, Leiterwirkung.
Sie ersetzt keine Statik — Holmlast, Wind, Verankerung und Befestigungsuntergrund
sind nicht gerechnet. Ergebnisse sind eine Planungshilfe und vor der Fertigung
fachlich zu prüfen.
