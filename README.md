# Railing Generator

Parametric generator for compliant steel railings — give it stair or landing geometry and it returns posts, handrail, bottom rail, an infill pattern, a bill of materials and a CAD export.

**▶ [Live-Demo](https://gleinkaa.github.io/railing-generator/)** — drag the sliders, pick one of 34 patterns, read the mass off the bill of materials. No install, no sign-up.

![Railing generated with pattern 32 `rake-uniform`, raytraced from the Grasshopper definition](reference/render_rake-uniform.png)

*Pattern 32 `rake-uniform`, raytraced from the Grasshopper definition. The browser app produces the same geometry live.*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

## What it does

- **34 infill patterns.** Vertical bars, uniform and random rakes, crossings, waves, chevrons, arches and loops, woven bands, timber panels and laser-cut sheet — each one a parameterised routine, not a fixed drawing. Bar count, spacing, angle and profile follow from the bay geometry.
- **Geometric pre-check against Austrian building rules.** Railing height, maximum clear opening, climbing aid ("Leiterwirkung") and gap-to-floor are checked against OIB Richtlinie 4 and ÖNORM B 5371, with warnings pointing at the specific bay that fails.
- **Bill of materials with real masses.** Every part is resolved against a steel-profile catalog (square and rectangular hollow sections, flats, rounds), so cut lengths, per-part mass and total mass come out of the profile data rather than an estimate.
- **CAD and data export.** STEP and OBJ from the Grasshopper side; OBJ, STL, CSV and JSON from the browser app.

Two implementations share one model: a Grasshopper/Rhino definition that produces real manufacturing geometry, and a dependency-free browser app that runs the same logic live with a 3D viewer.

## Why it exists

Infill patterns are normally shop-floor knowledge — a handful of layouts a fabricator has built before, redrawn by hand for each job. Here they are a dataset: each pattern is a function of the bay, so the same 34 patterns adapt to any opening instead of the opening being forced to fit the pattern.

The maths is not specific to stairs. Filling a rectangular or trapezoidal opening with a regular pattern under a clear-opening constraint is the same problem for fences, gates, balcony balustrades, privacy screens, facade cladding and perforated sheet, acoustic panels and furniture fronts. Railings are simply the case with the strictest rules, which makes it a good place to start.

## Quick start

The browser app has **no build step and no dependencies** — three.js is vendored in the repo.

```bash
git clone https://github.com/Gleinkaa/railing-generator.git
cd railing-generator
python -m http.server 8000
# then open http://localhost:8000/web/
```

Serve from the repository root, not from `web/` — the app resolves its vendored libraries by relative path.

Tests need Node ≥ 18:

```bash
node --test web/test/
```

## Repository layout

| Path | Contents |
| --- | --- |
| `web/` | Browser app — plain ES modules, vendored three.js, 3D viewer, BOM, compliance warnings, OBJ/STL/CSV/JSON export |
| `grasshopper/` | Rhino/Grasshopper Python engine, pattern implementations, profile handling, and the per-phase build scripts under `grasshopper/build/` |
| `docs/` | Specification, norms research, steel-profile catalog, architecture notes |
| `reference/` | Reference exports (OBJ/STEP/renders) and pinned masses used to catch regressions |

## The Grasshopper definition is not in this repository

**Known gap:** the `.gh` binary is deliberately not committed yet. What is committed is the code that builds it — the phased scripts in `grasshopper/build/`, which drive Grasshopper over a scripting bridge and lay out the definition component by component.

To reproduce the definition you need Rhino 8 with Grasshopper and a working scripting connection, then run the build scripts in phase order. This is not a one-click experience and it is not documented to the standard the browser app is. If you only want to see the generator work, use `web/`.

## Licensing

This project is released under the **GNU Affero General Public License v3.0 only** (see [`LICENSE`](LICENSE)). You may use, study, modify and redistribute it under those terms.

AGPL §13 adds one condition beyond the GPL: if you let users interact with a modified version over a network, you must offer those users the complete corresponding source of what you are running. For an internal tool or a personal project that is usually no obstacle. For a company that wants this as a configurator on its own website, it generally is — the obligation extends to the deployed stack, not just to this code.

For that case a **commercial licence** is available, which lifts the copyleft: embed and host it without publishing your source, and redistribute it inside a closed product. Details and contact: [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md).

### Für Betriebe in Österreich und Deutschland

Dieses Projekt ist quelloffen: Schlosser- und Metallbaubetriebe dürfen es einsetzen, anpassen und für ihre eigene Arbeitsvorbereitung verwenden — kostenlos, unter der AGPL. Wer den Generator aber als Konfigurator auf der eigenen Website betreiben möchte, ohne den eigenen Quellcode offenlegen zu müssen, braucht dafür eine kommerzielle Lizenz. Diese ist verfügbar und wird pro Betrieb vereinbart: siehe [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md) oder direkt gleinkaa@gmail.com.

## Standards note

The engine performs a **geometric** pre-check against OIB Richtlinie 4 and ÖNORM B 5371: heights, clear openings, gaps, climbing aid. That is all it does.

It performs **no structural analysis** — no handrail load case, no wind load, no fixing or anchor design, no verification of welds, sections or substrate. It is not certified, not approved by any authority, and it does not guarantee that a built railing complies with anything. Results are a design aid and must be reviewed and signed off by a qualified structural engineer or an accredited verification body before anything is fabricated or installed. Norm texts change; check the edition that applies to your project.

## Contributing

Bug reports, patterns and profile data are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) first — it covers the sign-off requirement and the contributor licence terms that the dual-licence model depends on.
