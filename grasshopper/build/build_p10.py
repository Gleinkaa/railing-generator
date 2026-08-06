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

"""Phase 10 — central control panel + clean final preview.

Two usability changes, no geometry changes:

1.  All 30 Number Sliders are collected into ONE labelled column on the left of the
    canvas, vertically centred on the definition, grouped by subsystem (Treppe /
    Gelaender / Profile / Montage / Fuellung / Intern). They were previously scattered
    over ~4300 px of canvas next to the components they feed, which made the model
    undriveable without hunting. Moving a slider changes nothing but its position, so
    the script asserts every value round-trips.

2.  Preview is switched OFF for every object and back ON for exactly the eight final
    solids (stairs, handrail, bottom rail, posts, vertical infill, diagonal infill,
    anchor plates, bolts). Grasshopper previews every geometry-producing component by default, so the
    viewport was showing the construction centrelines, section profiles, perp frames
    and bolt planes on top of the model.

The regression guard from Phase 8 is repeated here: assert solid count == centreline
count per role, because "0 component errors" alone did not catch the 41x41 sweep bug.
"""

import bh
import gh
import json
import os

s = json.load(open("state.json"))

# ---------------------------------------------------------------------------- backup
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(
    "backup:", gh.doc("save", path=os.path.join(root, "scratch", "backup_pre_p10.gh"))
)
gh.doc("snapshot", name="pre_p10")

# --------------------------------------------------------------- 1. control panel
# (nickname, section) in the order they should appear in the panel.
LAYOUT = [
    ("01 - TREPPE", "#8AA6C1", ["Stufenzahl", "Lauf", "Trittbreite", "Stufenstaerke"]),
    (
        "02 - GELAENDER",
        "#8FBF8F",
        ["Gelaenderhoehe", "Untergurt-Abstand", "Fuellstab-Abstand"],
    ),
    (
        "03 - PROFILE",
        "#D9B26F",
        [
            "Handlauf-Profil",
            "Untergurt-Profil",
            "Posten-Profil",
            "Fuellstab-Profil",
            "Diagonal-Profil",
        ],
    ),
    (
        "04 - MONTAGE",
        "#C98A8A",
        [
            "Montage-Typ",
            "Platte-Breite",
            "Platte-Hoehe",
            "Platte-Breite-Top",
            "Platte-Tiefe",
            "Platte-Dicke",
            "Bolzen-Durchmesser",
            "Bolzen-Laenge",
            "Bolzen-Offset-V",
            "Bolzen-Offset-XY",
            "Fascia-Offset",
        ],
    ),
    (
        "05 - FUELLUNG",
        "#A98FC1",
        ["Fuellung-Stil", "Diagonal-Seed", "Diagonal-Dichte", "Diagonal-Auslage"],
    ),
    ("06 - INTERN", "#B0B0B0", ["const2", "idx0", "Bolzen-Masse-kg"]),
]

PANEL_X = -900  # clear of the definition, whose left edge is x = -50
PANEL_Y = 850  # panel centre ends up near the vertical middle of the canvas
ROW = 32  # slider rows are ~20 px tall
GAP = 60  # between sections

sliders = {
    c["nickname"]: c
    for c in gh.canvas("list", typeFilter="Number Slider", limit=200)["components"]
}
# 30 since Phase 11b added Untergurt-Profil. Kept as a hard count rather than a
# >= check: a slider that exists but is missing from LAYOUT would be left stranded
# somewhere on the canvas, which is the exact problem this phase exists to fix.
assert len(sliders) == 30, f"expected 30 sliders, found {len(sliders)}"
placed = [n for _, _, names in LAYOUT for n in names]
missing = set(sliders) - set(placed)
assert not missing, f"sliders not covered by LAYOUT: {sorted(missing)}"

before = {n: gh.canvas("get", id=c["id"])["value"] for n, c in sliders.items()}

gh.doc("solver", enabled=False)

y = PANEL_Y
for title, color, names in LAYOUT:
    ids = []
    for n in names:
        cid = sliders[n]["id"]
        r = gh.canvas("move", id=cid, x=PANEL_X, y=y)
        assert r.get("success"), f"MOVE {n} failed: {r}"
        ids.append(cid)
        y += ROW
    g = gh.canvas("group_create", name=title, ids=json.dumps(ids), color=color)
    assert g.get("success"), f"GROUP {title} failed: {g}"
    y += GAP

# ------------------------------------------------------------------ 2. preview flags
FINAL = {
    "Treppe": "e3fc6b31-82cf-47bc-9aa0-653615722c72",
    "Handlauf_Volumen": "3127391b-7e86-4d01-9ad4-0892a78bb530",
    "Untergurt_Volumen": "99fb334a-7783-4c0f-97e5-43e91c234eda",
    "Posten_Volumen": "1cd6c339-5d60-4b79-9fdf-bc756305a91c",
    "Fuellstab_Volumen": "9f12cb7d-14b3-4d89-9f4e-c36c8cd6db68",
    "Diagonal_Volumen": "7a5ee33f-96ae-4193-9bab-1768e92a6435",
    "Montage_Platten": "086ace7d-0f7f-44bd-baa3-e2b7a31a589b",
    "Montage_Bolzen": "9633428f-6ffa-42e3-84bb-d98b0e4ae2f1",
}
# the ids are pinned rather than looked up by nickname so a rename can never silently
# leave an intermediate previewing instead of a final solid.
by_id = {c["id"]: c for c in gh.canvas("list", limit=500)["components"]}
for nm, cid in FINAL.items():
    assert by_id.get(cid, {}).get("nickname") == nm, f"{nm} id no longer matches canvas"

all_ids = list(by_id)
for i in range(0, len(all_ids), 50):
    chunk = all_ids[i : i + 50]
    r = gh.canvas("preview", ids=json.dumps(chunk), enabled=False)
    if not r.get("success"):
        # sliders/panels have no preview flag; retry singly so one refusal cannot
        # leave the other 49 components in the chunk still previewing.
        for cid in chunk:
            gh.canvas("preview", id=cid, enabled=False)
r = gh.canvas("preview", ids=json.dumps(list(FINAL.values())), enabled=True)
assert r.get("success"), f"PREVIEW on failed: {r}"

gh.doc("solver", enabled=True)
gh.doc("recompute")

# ------------------------------------------------------------------- verification
after = {n: gh.canvas("get", id=c["id"])["value"] for n, c in sliders.items()}
drift = {n: (before[n], after[n]) for n in before if before[n] != after[n]}
assert not drift, f"slider values changed while moving: {drift}"
print(f"sliders: {len(sliders)} moved, all values unchanged")

st = gh.inspect("status")
bad = [
    c
    for c in st.get("components", [])
    if c.get("status") not in ("OK", None) and c.get("name") != "Load"
]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"


count = bh.count


PAIRS = [  # (role, solid, centreline)
    ("Handlauf", FINAL["Handlauf_Volumen"], "b3238fc0-5c0e-43d0-9f3c-e82a11990f16"),
    ("Untergurt", FINAL["Untergurt_Volumen"], "eed8edf1-f4ec-40e8-b926-8f128f5ba5ed"),
    ("Posten", FINAL["Posten_Volumen"], "33d4cf75-2359-4405-a1dd-96262aacd802"),
    ("Fuellstab", FINAL["Fuellstab_Volumen"], "2acb6771-e680-4e61-bcc0-0abf44f7685e"),
    ("Diagonal", FINAL["Diagonal_Volumen"], "bfb4241f-4221-4bdb-ab55-aeb5c6e5a9c2"),
]
for role, solid, line in PAIRS:
    ns, nl = count(solid), count(line)
    print(f"{role:10s} solids={ns:5d} centrelines={nl:5d}")
    assert ns == nl, f"{role}: {ns} solids vs {nl} centrelines"

print("groups:", json.dumps(gh.canvas("group_list"), ensure_ascii=False)[:400])

s["p10"] = dict(panel_x=PANEL_X, panel_y=PANEL_Y, final=FINAL)
json.dump(s, open("state.json", "w"), indent=1)

print(gh.doc("save", path=os.path.join(root, "Railing_Generator.gh")))
gh.canvas("zoom", padding=60)
gh.doc("capture_canvas", path=os.path.join(root, "scratch", "canvas_p10.png"), fit=True)
