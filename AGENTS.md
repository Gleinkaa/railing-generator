# AGENTS.md — railing-generator

## What this repo is

A parametric generator for compliant steel railings: give it stair or landing geometry and
it returns posts, handrail, bottom rail, an infill pattern, a bill of materials and a CAD
export. Two implementations share one model — a Rhino/Grasshopper engine (`grasshopper/`)
and a dependency-free browser app (`web/`) that runs the same logic live with a 3D viewer.
The engine performs a **geometric pre-check** against OIB Richtlinie 4 and ÖNORM B 5371
(heights, clear openings, climbing aid) and **no structural analysis at all**. Licensed
AGPL-3.0-only, with a commercial licence available.

## Layout (real paths)

```
web/                     browser app: bay.js, catalog.js, geometry.js, main.js, model.js,
                         patterns.js, viewer.js, style.css, index.html, README.md (German)
web/patterns/            the pattern routines: formed.js (00-09), organic.js (10-15),
                         rhythm.js (16-24), lines.js (25-33), params.js, shared.js
web/test/                bay.test.mjs, model.test.mjs — the engine contract
web/vendor/              vendored three.js + OBJ/STL/OrbitControls exporters
grasshopper/gh.py        raw Cordyceps MCP driver (JSON-RPC over HTTP)
grasshopper/bh.py        build helpers: name-based wiring, `G` component GUID registry
grasshopper/patterns.py, profiles.py   pattern + steel-profile catalog logic
grasshopper/build/       phased build scripts build_p01.py … build_p14f.py
grasshopper/definitions/ the .gh binaries (+ README.md on their provenance)
grasshopper/state.json, object_ids.json   live canvas id maps from a build run
grasshopper/build_stairs.py, build_stairs_staged.py, check_reachability.py,
                         export_models.py, regress_p14.py, render_muster.py, render_styles.py
docs/SPEC.md             the master build spec (phased build against Cordyceps)
docs/architecture.md     paper design: profile selector, mounting, diagonal infill
docs/patterns-and-code.md, docs/profiles.md
reference/               pinned STEP/OBJ/MTL exports + 3 renders (the regression contract)
index.html               root redirect to web/ for the Pages deploy
netlify.toml, vercel.json
.github/workflows/ci.yml     Node 20 web tests + `python -m compileall -q grasshopper`
.github/workflows/pages.yml  GitHub Pages deploy of the whole repository
CONTRIBUTING.md, LICENSE (AGPL), COMMERCIAL-LICENSE.md
```

## Run / test

```bash
python -m http.server 8000            # from the repository ROOT, then open /web/
node --test web/test/                 # needs Node >= 18; CI uses Node 20
python -m compileall -q grasshopper   # the engine syntax gate CI runs
```

Serve from the repo root, not from `web/` — the app resolves its vendored libraries by
relative path (the Pages workflow publishes the whole repo for the same reason).

The Grasshopper side only runs for real against **Rhino 8 + Grasshopper with the Cordyceps
MCP server** at `http://127.0.0.1:26929/mcp`. The scripts in `grasshopper/build/` are run in
phase order against a live, empty GH document; none of that was exercised in this audit.

## Conventions observed in the code

- **The pattern index is the contract.** Pattern 30 in the web app is pattern 30 on the
  Grasshopper slider; reordering `DESIGNS` in `web/patterns.js` breaks both engines and the
  pinned reference masses.
- **Units are millimetres.** Every numeric literal in `docs/SPEC.md` depends on it; BOM
  densities are kg/m, so every mass path divides by 1000.
- **A profile's 0-based row index drives both the swept section and its kg/m**, so geometry
  and mass can never disagree (`grasshopper/profiles.py`, ported as `web/catalog.js`).
  Section flags are `0 = round, 1 = rect/flat`, wired as Stream 0 = Circle,
  Stream 1 = Rectangle.
- **Never invent a GUID.** Components not in `bh.G` are added by Grasshopper display name
  after `gh_canvas action=search`; ports are addressed by human name and probed with
  `gh_canvas info` before wiring.
- Build discipline: solver OFF while building, solver ON + `recompute` after each phase,
  then `gh_inspect action=status`; snapshot before each phase.
- Python files carry the AGPL SPDX header; German is used for shop-facing docs
  (`web/README.md`, parts of `docs/`, build-script docstrings).

## Gotchas and do-not-touch

- **Live-system hazard.** `grasshopper/gh.py` drives a running Rhino through Cordyceps, and
  `gh_document action=clear` is effectively irreversible. Do not run build or render scripts
  against someone else's Rhino session or an unsaved document.
- `grasshopper/state.json` and `grasshopper/object_ids.json` are id maps captured from a
  live canvas. They are not stable identifiers — re-read them after a rebuild instead of
  trusting stale values.
- `reference/` is deliberately versioned: the STEP/OBJ exports and the three renders are the
  pinned contract the regression tests hang on. Do not regenerate or delete them.
  `reference/renders_muster/` and `grasshopper/viewport_stairs.png` are the generated
  counterparts and are gitignored.
- The `.gh` binaries in `grasshopper/definitions/` came from the archived
  `StiegengelaenderGeneratorGH` repo; the `grasshopper/build/` scripts are the newer,
  AGPL-headed route. Do not hand-edit the binaries.
- **Do not claim compliance.** The engine checks geometry only — no handrail load case, no
  wind load, no fixing, weld or section verification. Results are a design aid that a
  qualified engineer must sign off before anything is fabricated.
- **Dual licence.** AGPL-3.0-only plus a commercial option, which is why `CONTRIBUTING.md`
  asks for a contributor sign-off. Do not relicense code or drop the SPDX headers.
- `docs/SPEC.md` is the master prompt for an agent driving a live Rhino — treat it as spec,
  not as runnable CI.

## Definition of done

- `node --test web/test/` green and `python -m compileall -q grasshopper` clean.
- New or changed pattern: the index in `web/patterns.js` `DESIGNS` and the Grasshopper
  slider agree, and the pinned `reference/` masses still hold.
- Profile-catalog change: `docs/profiles.md`, `grasshopper/profiles.py` and the catalog rows
  in `web/catalog.js` agree.
- Any doc making a compliance claim says "geometric pre-check", not "compliant".
- Report which side was actually exercised — a web-only change must not be described as
  verified in Rhino.
