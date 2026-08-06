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

"""Phase 11a — put the railing on the NOSING line instead of the back-corner line.

Root cause of "the bars poke out under the treads" and of the handrail sitting too low.

`Treppenbasislinie` runs ptA(0,0,0) -> ptB(Lauf, 0, Steigung) and is divided into
`Stufenzahl` points; tread i is then built spanning x in [x(i-1), x(i)] with its TOP
face at z(i).  So the base line passes through the BACK-top corner of every tread and
lies one full riser BELOW the nosing line (the line through the front-top corners).

Every railing height was measured off that low line:
  * Untergurt-Abstand = 100 put the bottom rail 100 - 153.8 = -53.8 mm relative to the
    nosings, i.e. INSIDE / below the 24 mm treads -> infill bars visibly sticking out
    under the stair (confirmed live: untergurt line z 100..2100, tread tops 153.8..2000).
  * Gelaenderhoehe was likewise measured from the wrong datum, so a nominal 1000 mm
    handrail was really 1000 - 153.8 = 846 mm over the nosings -> below the OIB RL 4 /
    OeNORM B 5371 minimum of 1000 mm.  Prompt1.md pins that minimum as an invariant.

Fix: build `Nosinglinie` = base line + UnitZ(Steigung / Stufenzahl) and hang the
handrail line, the untergurt line and the post base points off THAT.  Heights now mean
what their names say: measured from the walking surface.

Post length changes with the datum: posts used to start on the untergurt line, so their
length was Gelaenderhoehe - Untergurt-Abstand.  They now start on the nosing line, so
the length is Gelaenderhoehe.  The infill bars still start on the untergurt line and
keep the old (Gelaenderhoehe - Untergurt-Abstand) length -- `_Posthoehe` is therefore
kept alive for them, only the posts are re-pointed.
"""

import gh
import bh
import json
import os

s = json.load(open("state.json"))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(
    "backup:", gh.doc("save", path=os.path.join(root, "scratch", "backup_pre_p11.gh"))
)
gh.doc("snapshot", name="pre_p11")
gh.doc("solver", enabled=False)

Y = 3400


sld = bh.slider_id

# --- clean up a half-applied earlier run ---------------------------------------------
for c in gh.canvas("list", limit=500)["components"]:
    if c.get("nickname") in ("_Steigung/N", "_uzNosing", "Nosinglinie"):
        print("deleting stale", c["nickname"], gh.canvas("delete", id=c["id"]))

# --- the nosing datum ----------------------------------------------------------------
riser = bh.add("Division", 330, Y, "_Steigung/N")
bh.wire(s["cRise"], 0, riser, "A")
bh.wire(sld("Stufenzahl"), 0, riser, "B")
uzN = bh.add("UnitZ", 510, Y, "_uzNosing")
bh.wire(riser, "Result", uzN, "Factor")
nos = bh.add("Move", 690, Y, "Nosinglinie")
bh.wire(s["line"], "Line", nos, "Geometry")
bh.wire(uzN, "Unit vector", nos, "Motion")

# --- re-hang everything that measured off the old datum ------------------------------
for label, cid, port in (
    ("Handlauflinie", s["handrail"], "Geometry"),
    ("Untergurtlinie", s["untergurt"], "Geometry"),
    ("_TeilerPosten", s["dc"], "Curve"),
):
    print(f"-- {label}.{port}")
    bh.clear_input(cid, port)
    bh.wire(nos, "Geometry", cid, port)

# posts now stand on the nosing line, so their full length is Gelaenderhoehe
print("-- Posten.Length")
bh.clear_input(s["posts"], "Length")
bh.wire(sld("Gelaenderhoehe"), 0, s["posts"], "Length")

# OIB RL 4 minimum is 1000 mm over the nosing; the slider had been dragged to 875 while
# the datum was still wrong.  With the datum fixed, 875 would be a genuine 875 mm rail.
gh.canvas("set", id=sld("Gelaenderhoehe"), value="1000")

s["p11"] = dict(riser=riser, nosing=nos)
json.dump(s, open("state.json", "w"), indent=1)

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- verification ---------------------------------------------------------------------
st = gh.inspect("status")
bad = [
    c
    for c in st.get("components", [])
    if c.get("status") not in ("OK", None) and c.get("name") != "Load"
]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"


def prev(cid, out=0):
    return gh.inspect("outputs", id=cid).get("outputs", [{}])[out].get("preview")


riser_mm = float(prev(riser)[0])
print("riser         :", riser_mm)
print("Nosinglinie   :", prev(nos))
print("Untergurtlinie:", prev(s["untergurt"]))
print("Handlauflinie :", prev(s["handrail"]))
print("Postenbasis   :", prev(s["dc"]))
print("Posten laenge :", prev(sld("Gelaenderhoehe")))

# the first tread's top face sits at exactly one riser; the untergurt must clear it
g = gh.inspect("geometry", id=s["untergurt"]).get("outputs", [{}])[0]
line = g.get("items", [{}])[0].get("value", "")
print("untergurt line:", line)
z0 = float(line.split(",")[2])
assert abs(z0 - (riser_mm + 100)) < 1e-6, (
    f"untergurt starts at z={z0}, expected {riser_mm + 100}"
)
print(
    f"OK: untergurt starts {z0 - riser_mm:.1f} mm above the nosing line "
    f"(tread top of step 1 is z={riser_mm:.1f})"
)
