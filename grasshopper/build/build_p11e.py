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

"""Phase 11e — re-apply the Phase-10 housekeeping and run the full regression.

Phases 11a-11d added components, and Grasshopper previews every geometry-producing
component by default — `Nosinglinie` and the new mount helper vectors would otherwise
show up in the viewport on top of the model.  So the Phase-10 rule is re-applied from
scratch: preview OFF for everything, ON for exactly the final solids (now EIGHT, with
`Untergurt_Volumen` joining them), and the new `Untergurt-Profil` slider is docked in
the 03 - PROFILE group of the control panel.

The regression guard is the Phase-8/10 one: solid count == centreline count per role,
because "0 component errors" alone never caught the 41x41 sweep bug.
"""

import gh
import bh
import json
import os

s = json.load(open("state.json"))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FINAL = dict(s["p10"]["final"])
by_id = {c["id"]: c for c in gh.canvas("list", limit=600)["components"]}
for nm, cid in FINAL.items():
    assert by_id.get(cid, {}).get("nickname") == nm, f"{nm} id no longer matches canvas"
assert "Untergurt_Volumen" in FINAL, "Phase 11b did not register the bottom rail"
print("final solids:", sorted(FINAL))

gh.doc("solver", enabled=False)

# --- dock the new slider under 03 - PROFILE -------------------------------------------
prof = [
    c
    for c in gh.canvas("list", typeFilter="Number Slider", limit=200)["components"]
    if c.get("nickname")
    in ("Handlauf-Profil", "Posten-Profil", "Fuellstab-Profil", "Diagonal-Profil")
]
anchor = max(prof, key=lambda c: c["y"])
usl = [
    c
    for c in gh.canvas("list", typeFilter="Number Slider", limit=200)["components"]
    if c.get("nickname") == "Untergurt-Profil"
][0]
gh.canvas("move", id=usl["id"], x=anchor["x"], y=anchor["y"] + 32)
g = [
    x
    for x in gh.canvas("group_list").get("groups", [])
    if "03" in (x.get("name") or "")
]
if g:
    gh.canvas("group_add", id=g[0].get("id"), ids=json.dumps([usl["id"]]))
print("Untergurt-Profil docked at", anchor["x"], anchor["y"] + 32)

# --- preview: off for all, on for the finals -----------------------------------------
all_ids = list(by_id)
for i in range(0, len(all_ids), 50):
    chunk = all_ids[i : i + 50]
    if not gh.canvas("preview", ids=json.dumps(chunk), enabled=False).get("success"):
        for cid in chunk:  # params refuse the batch call
            gh.canvas("preview", id=cid, enabled=False)
r = gh.canvas("preview", ids=json.dumps(list(FINAL.values())), enabled=True)
assert r.get("success"), f"PREVIEW on failed: {r}"

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- regression -----------------------------------------------------------------------
st = gh.inspect("status")
bad = [
    c
    for c in st.get("components", [])
    if c.get("status") not in ("OK", None) and c.get("name") != "Load"
]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"


count = bh.count


PAIRS = [
    ("Handlauf", FINAL["Handlauf_Volumen"], s["handrail"]),
    ("Untergurt", FINAL["Untergurt_Volumen"], s["untergurt"]),
    ("Posten", FINAL["Posten_Volumen"], s["posts"]),
    ("Fuellstab", FINAL["Fuellstab_Volumen"], s["p8"]["vAktiv"]),
    ("Diagonal", FINAL["Diagonal_Volumen"], s["p8"]["dAktiv"]),
]
for role, solid, line in PAIRS:
    ns, nl = count(solid), count(line)
    print(f"{role:10s} solids={ns:5d} centrelines={nl:5d}")
    assert ns == nl, f"{role}: {ns} solids vs {nl} centrelines"

print("plates/bolts:", count(FINAL["Montage_Platten"]), count(FINAL["Montage_Bolzen"]))
assert count(FINAL["Montage_Bolzen"]) == 2 * count(FINAL["Montage_Platten"]), (
    "fascia mode must give 2 bolts per plate"
)

print(
    "BOM:",
    json.dumps(
        gh.inspect("outputs", id=s["panel"]).get("outputs", [{}])[0].get("preview"),
        indent=1,
        ensure_ascii=False,
    ),
)

json.dump(s, open("state.json", "w"), indent=1)
print(gh.doc("save", path=os.path.join(root, "Railing_Generator.gh")))
gh.canvas("zoom", padding=60)
gh.doc("capture_canvas", path=os.path.join(root, "scratch", "canvas_p11.png"), fit=True)
