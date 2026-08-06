# Railing Generator - parametric railing and infill-pattern engine
# Copyright (C) 2026 Gleinkaa
#
# SPDX-License-Identifier: AGPL-3.0-only
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU Affero General Public License for more details.
#
# A commercial licence without the copyleft obligation is available:
# see COMMERCIAL-LICENSE.md.

# -*- coding: utf-8 -*-
"""Export one `Muster` (0..33) as customer-facing 3D files.

    python export_models.py 30            # one pattern
    python export_models.py 1 11 30       # a selection
    python export_models.py --all         # all 34
    python export_models.py --help        # list all 34 patterns

Per pattern, into ../reference/:
  Stiegengelaender_Muster<NN>_<key>.3dm   Rhino native, layered (Stahl/Treppe/Holz)
  Stiegengelaender_Muster<NN>_<key>.stp   STEP AP214 — solids, opens in any CAD
  Stiegengelaender_Muster<NN>_<key>.obj   mesh, opens in anything incl. web viewers

This script used to drive the `Fuellung-Stil` slider (0/1/2). That slider is gone
since Phase 14 — the infill is selected by `Muster` (0..33), and that is what the
script sets now.

Grasshopper preview geometry is not real document geometry, so each pattern is baked,
exported and deleted again; the Rhino document is left as empty as it was found.

WARNING: drives the LIVE document over the MCP bridge.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gh  # noqa: E402

# One single source for the catalogue, the bake list and driving the engine —
# nothing here is a second copy that can drift:
#   KEYS            - the 34 (key, name) pairs read from patterns.py
#   STEEL/TREAD     - nicknames of the SWEPT channels (state.json p10.final)
#   FINAL           - nickname -> component id
#   SOLID           - the TWO Phase-14 solid channels (Brep params, Stahl/Holz)
#   LAYERS          - target layers incl. `Holz`, without which the solids get no material
#   REFERENZ_MUSTER - the pattern the document is left on (30 Vertical Bars)
#   select          - set the slider, read it back, recompute until the engine agrees
#   bake_param      - bake the Breps of a free-standing Brep parameter
#   _pruefe_solids  - reconcile against the engine: what it reports must have been baked
from render_muster import (  # noqa: E402
    KEYS,
    LAYERS,
    SOLID,
    STEEL,
    TREAD,
    FINAL,
    REFERENZ_MUSTER,
    bake_param,
    select,
    _pruefe_solids,
)

OUT = os.path.abspath(os.path.join(HERE, "..", "reference"))


def scene(action, **kw):
    return gh.call("rhino_scene", {"action": action, **kw})


def render(action, **kw):
    return gh.call("rhino_render", {"action": action, **kw})


def clear_scene():
    objs = scene("objects", limit=5000).get("objects", [])
    if objs:
        scene("delete", ids=json.dumps([o["id"] for o in objs]))
    # Counted from the object list, not from a `count` key: a missing key would
    # read as None and let the assert pass on an document that is not empty.
    left = scene("objects", limit=5000).get("objects", [])
    assert not left, f"{len(left)} objects left in the document"


def export_one(m):
    key, name = KEYS[m]
    clear_scene()

    # Set the slider, read it back (via `get` — `info` still reports None for
    # sliders) and recompute until the engine ITSELF reports the index. Without
    # this latch the previous pattern gets exported.
    chk = select(m)
    print("  engine:", chk[0] if chk else "?")

    for layer, color in LAYERS:
        scene("layer_create", name=layer, color=color)
    for layer, nicks in (("Stahl", STEEL), ("Treppe", TREAD)):
        for nick in nicks:
            r = gh.canvas("bake", id=FINAL[nick], layer=layer)
            assert r.get("success"), f"bake {nick} failed: {r}"

    # The engine has FOUR output channels, not two: besides the swept bar channels
    # geometry also comes out as SOLIDS (`plate`/`twisted` -> Stahl, `block` -> Holz).
    # Both hang off free-standing Brep parameters that `gh_canvas action='bake'`
    # cannot bake — hence bake_param(). An empty channel is legal; whether one is
    # MISSING is decided by the reconciliation with the engine, not by a list here.
    # Leaving these two out is exactly what once produced nine infill-less renders
    # (HANDOFF.md §6b) — an export would have been just as silently wrong.
    solids = {layer: bake_param(cid, layer) for layer, cid in SOLID.items()}
    _pruefe_solids(chk, solids)

    objs = scene("objects", limit=5000).get("objects", [])
    ids = {}
    for o in objs:
        ids.setdefault(o.get("layer"), []).append(o["id"])
    print(f"  baked {len(objs)} objects {({k: len(v) for k, v in ids.items()})}"
          f" solids={solids}")
    assert ids.get("Stahl"), "nothing baked on layer Stahl — an empty export looms"

    render(
        "material_create",
        name="Stahl_anthrazit",
        type="Metal",
        color="#4A5056",
        roughness=0.32,
        metallic=1.0,
    )
    render(
        "material_create", name="Eiche", type="Plastic", color="#B9884E", roughness=0.55
    )
    render("material_apply", ids=json.dumps(ids["Stahl"]), material="Stahl_anthrazit")
    for layer in ("Treppe", "Holz"):  # both in a wood look
        if ids.get(layer):
            render("material_apply", ids=json.dumps(ids[layer]), material="Eiche")

    base = os.path.join(OUT, f"Stiegengelaender_Muster{m:02d}_{key}")
    written = []
    for ext in ("3dm", "stp", "obj"):
        path = f"{base}.{ext}"
        if os.path.exists(path):
            os.remove(path)
        # `_-Export` is the command-line form: no dialogs, defaults accepted with
        # trailing _Enter. Overwrite prompts are avoided by deleting first.
        cmd = f'_SelAll _-Export "{path}" _Enter _Enter _Enter'
        r = scene("script", cmd=cmd)
        ok = os.path.exists(path)
        written.append((ext, ok, os.path.getsize(path) if ok else 0, r.get("success")))
        scene("deselect", all="true")
    for ext, ok, size, rpc in written:
        print(
            f"    {ext:4s} {'OK ' if ok else 'MISS'} {size / 1024:9.1f} kB  (rpc={rpc})"
        )
    assert all(w[1] for w in written), \
        f"Muster {m:02d} ({name}): some exports missing: {written}"

    clear_scene()
    return [f"{base}.{e}" for e in ("3dm", "stp", "obj")]


def _usage(fehler=""):
    """Usage plus the 34 valid indices.

    The name list comes from KEYS and therefore from `patterns.py` — no
    second table here that could drift away from the first one.
    """
    zeilen = []
    if fehler:
        zeilen += ["ERROR: " + fehler, ""]
    zeilen += [
        "    python export_models.py <Muster 0..%d> [<Muster> ...]" % (len(KEYS) - 1),
        "    python export_models.py --all",
        "",
        "Valid patterns (source: patterns.py, DESIGNS):",
    ]
    for i, (key, name) in enumerate(KEYS):
        zeilen.append("  %2d  %-16s %s" % (i, key, name))
    return "\n".join(zeilen)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(_usage("no pattern index given"))
        sys.exit(2)
    if args[0] in ("-h", "--help", "--list"):
        print(_usage())
        sys.exit(0)
    if args[0] == "--all":
        todo = list(range(len(KEYS)))
    else:
        try:
            todo = [int(a) for a in args]
        except ValueError:
            print(_usage("%r is not an integer" % args))
            sys.exit(2)
        out_of_range = [m for m in todo if not 0 <= m < len(KEYS)]
        if out_of_range:
            print(_usage("%r outside 0..%d" % (out_of_range, len(KEYS) - 1)))
            sys.exit(2)

    os.makedirs(OUT, exist_ok=True)
    try:
        for m in todo:
            print(f"-- Muster {m:02d} {KEYS[m][0]} ({KEYS[m][1]})")
            for p in export_one(m):
                print("   ", p)
    finally:
        # Leave the document as it was found — also when something blew up above.
        clear_scene()
        for layer, _ in LAYERS:
            scene("layer_delete", name=layer)
        select(REFERENZ_MUSTER)  # reads back and verifies, unlike a bare `set`
        print(f"Muster back on {REFERENZ_MUSTER}, document empty, helper layers gone. "
              f"The .gh was NOT saved.")
