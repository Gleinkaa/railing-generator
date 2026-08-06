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

"""Phase 11c — make the mounting hardware buildable.

Reported by the user from the Rhino viewport: "the mounts are also weird".  Four
distinct defects, all confirmed live before this phase:

1. `_edgeN1` points INTO the stair, not out of it.  The treads run from y = -Trittbreite
   to y = 0 and the railing sits on the y = 0 edge, so outward is +Y — but
   Cross(tangent, UnitZ) evaluated to {0,-1,0}.  build_p7.py flagged exactly this
   ("If mirrored, the outward sign of _edgeN1 is flipped for this run direction") and
   the sign was never checked against the built stair.  Consequences: the fascia bolts
   drove outward into thin air instead of into the slab, and Phase 8's
   `Diagonal-Auslage` pushed the decorative diagonals INBOARD, over the treads.
   Fixed by swapping the Cross Product inputs -> Cross(UnitZ, tangent) = +Y.
   `_tanHorizX` is swapped to match, which also repairs `_topPln`'s normal (it pointed
   DOWN — carried as a known low-severity finding since the f463e0c review).

2. The fascia plate was rotated by the stair rake, because its plane took the raked
   3D tangent as X-Axis.  A fascia plate is a flat vertical rectangle bolted to a
   vertical face; only the plate ROW follows the rake, never the plate itself.  X-Axis
   now comes from `_tanHoriz` (the tangent projected into plan), so Platte-Breite is
   horizontal and Platte-Hoehe is vertical.

3. The plate was centred on the y = 0 edge plane, i.e. half buried in the structure,
   and centred on the post base point, i.e. sticking up above the walking surface.
   It now hangs BELOW the nosing datum (top edge flush with it, Platte-Hoehe down) and
   sits ON the outside face (offset outward by Platte-Dicke/2 + Fascia-Offset), which
   is what a side-mounted plate actually does.

4. The bolts started on the plate mid-plane and ran outward.  They now start on the
   plate's outer face and run inward, through the plate and into the structure.  The
   top-mount bolts likewise start on the top plate's upper face and run down.

Only wiring and a handful of vector helpers change; no slider gets a new meaning.
"""

import gh
import bh
import json

s = json.load(open("state.json"))
gh.doc("snapshot", name="pre_p11c")
gh.doc("solver", enabled=False)

Y = 3900
new_ids = []
MINE = {
    "_fascAmt",
    "_fHneg",
    "_fDropVec",
    "_fascMove",
    "_fThickVec",
    "_boltBase",
    "_topLiftVec",
    "_topPt",
    "_topBoltLift",
    "_topBoltBase",
}
for c in gh.canvas("list", limit=600)["components"]:
    if c.get("nickname") in MINE:
        gh.canvas("delete", id=c["id"])


def keep(cid):
    new_ids.append(cid)
    return cid


sld = bh.slider_id


def repoint(cid, port, src, src_port):
    bh.clear_input(cid, port)
    bh.wire(src, src_port, cid, port)


N = bh.by_nick  # resolves Params too — the Phase-7 constants are Panels

uz = N("_zM")  # UnitZ(1)
ev = N("_evalBase")  # Point / Tangent along the rail
n1 = N("_edgeN1")  # unitised slab-edge normal
th = N("_tanHoriz")  # ... projected into plan
fT = N("_fT")  # Platte-Dicke / 2
fH = N("_fH")  # Platte-Hoehe / 2
tT = N("_tT")  # Platte-Dicke / 2 (top branch)
cn1 = N("_-1M")  # constant -1 from Phase 7

# --- 1. outward normal, and the plan tangent derived from it --------------------------
print("-- flip _edgeNrm to Cross(UnitZ, tangent)")
crs = N("_edgeNrm")
bh.clear_input(crs, "Vector A")
bh.clear_input(crs, "Vector B")
bh.wire(uz, "Unit vector", crs, "Vector A")
bh.wire(ev, "Tangent", crs, "Vector B")

print("-- flip _tanHorizX to Cross(outward, UnitZ)")
thx = N("_tanHorizX")
bh.clear_input(thx, "Vector A")
bh.clear_input(thx, "Vector B")
bh.wire(n1, "Vector", thx, "Vector A")
bh.wire(uz, "Unit vector", thx, "Vector B")

# --- 2. un-rake the fascia plate -------------------------------------------------------
print("-- _fascPln.X-Axis: raked tangent -> plan tangent")
repoint(N("_fascPln"), "X-Axis", th, "Vector")

# --- 3. seat the plate on the outside face, hanging below the datum --------------------
print("-- _fascVec.Amplitude: Fascia-Offset + Platte-Dicke/2")
amt = keep(bh.addf("Addition", 330, Y, "_fascAmt"))
bh.wire(sld("Fascia-Offset"), 0, amt, "A")
bh.wire(fT, "Result", amt, "B")
repoint(N("_fascVec"), "Amplitude", amt, "Result")

print("-- _fascPt.Motion: outward offset + drop of Platte-Hoehe/2")
fHn = keep(bh.add("Multiplication", 330, Y + 40, "_fHneg"))
bh.wire(fH, "Result", fHn, "A")
bh.wire(cn1, 0, fHn, "B")
drop = keep(bh.add("UnitZ", 510, Y + 40, "_fDropVec"))
bh.wire(fHn, "Result", drop, "Factor")
mv = keep(bh.addf("Addition", 690, Y + 20, "_fascMove"))
bh.wire(N("_fascVec"), "Vector", mv, "A")
bh.wire(drop, "Unit vector", mv, "B")
repoint(N("_fascPt"), "Motion", mv, "Result")

# --- 4. bolts: start on the plate face, drive inward -----------------------------------
print("-- fascia bolt origin -> plate outer face")
tvec = keep(bh.addf("Amplitude", 330, Y + 80, "_fThickVec"))
bh.wire(n1, "Vector", tvec, "Vector")
bh.wire(fT, "Result", tvec, "Amplitude")
bbase = keep(bh.add("Move", 510, Y + 80, "_boltBase"))
bh.wire(N("_fascPt"), "Geometry", bbase, "Geometry")
bh.wire(tvec, "Vector", bbase, "Motion")
for k in (0, 1):
    repoint(N(f"_boltPt{k}"), "Geometry", bbase, "Geometry")
    # Construct Plane(X = plan tangent, Y = UnitZ) => normal = X x Y = -outward
    pln = N(f"_boltPln{k}")
    bh.clear_input(pln, "X-Axis")
    bh.clear_input(pln, "Y-Axis")
    bh.wire(th, "Vector", pln, "X-Axis")
    bh.wire(uz, "Unit vector", pln, "Y-Axis")

# --- 5. top mount: plate sits ON the datum, bolts start on its upper face --------------
print("-- top plate on top of the datum plane")
lift = keep(bh.add("UnitZ", 330, Y + 120, "_topLiftVec"))
bh.wire(tT, "Result", lift, "Factor")
tpt = keep(bh.add("Move", 510, Y + 120, "_topPt"))
bh.wire(s["dc"], "Points", tpt, "Geometry")
bh.wire(lift, "Unit vector", tpt, "Motion")
repoint(N("_topPln"), "Origin", tpt, "Geometry")

blift = keep(bh.add("UnitZ", 330, Y + 160, "_topBoltLift"))
bh.wire(sld("Platte-Dicke"), 0, blift, "Factor")
tbb = keep(bh.add("Move", 510, Y + 160, "_topBoltBase"))
bh.wire(s["dc"], "Points", tbb, "Geometry")
bh.wire(blift, "Unit vector", tbb, "Motion")
for k in range(4):
    repoint(N(f"_topBoltPt{k}"), "Geometry", tbb, "Geometry")

# --- preview hygiene -------------------------------------------------------------------
gh.canvas("preview", ids=json.dumps(new_ids), enabled=False)
for cid in new_ids:
    gh.canvas("preview", id=cid, enabled=False)

s["p11"]["mount"] = dict(
    fascAmt=amt, fascMove=mv, boltBase=bbase, topPt=tpt, topBoltBase=tbb
)
json.dump(s, open("state.json", "w"), indent=1)

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- verification -----------------------------------------------------------------------
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


checks = {
    "_edgeN1 (outward, must be +Y)": (n1, "{0,1,0}"),
    "_tanHoriz (run in plan, +X)": (th, "{1,0,0}"),
}
for label, (cid, want) in checks.items():
    got = prev(cid)[0]
    print(f"{label:32s} {got}")
    assert got == want, f"{label}: got {got}, expected {want}"

for label, cid, want_z in (
    ("_fascPln (plate)", N("_fascPln"), "Z(0.00,-1.00,0.00)"),
    ("_boltPln0 (into slab)", N("_boltPln0"), "Z(0.00,-1.00,0.00)"),
    ("_topPln (plate up)", N("_topPln"), "Z(0.00,0.00,1.00)"),
):
    got = prev(cid)[0]
    print(f"{label:22s} {got}")
    assert want_z in got, f"{label}: {got} does not carry {want_z}"

print("post base   :", prev(s["dc"])[:2])
print("plate centre:", prev(N("_fascPt"))[:2])
print("bolt origin :", prev(N("_boltBase"))[:2])
print("top plate   :", prev(N("_topPt"))[:2])
for nick in ("Montage_Platten", "Montage_Bolzen"):
    g = (gh.inspect("geometry", id=N(nick)).get("outputs") or [{}])[0]
    print(f"{nick:16s} count={g.get('count')}")
