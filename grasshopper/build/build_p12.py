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

"""Phase 12 — let the decorative diagonals go sparse without losing compliance.

The renders of the three `Fuellung-Stil` variants showed Stil 1 and Stil 2 as very
nearly the same picture: a dense, almost vertical picket mesh. The decorative diagonal
signature the whole adaptation is for — a loose diagonal zigzag — never appeared.

Cause: `Diagonal-Dichte` (max node spacing along each rail) was capped at 112 mm,
because 120 mm sphere - 8 mm bar = 112 mm is what a diagonals-ONLY field has to hold on
its own. But that cap only has to bind in Stil 2. In Stil 1 the vertical safety field
(`Fuellstab-Abstand` = 115 mm, 103 mm clear) already carries the sphere test and the
diagonals are purely decorative, so there the spacing can be whatever looks right.

So the cap becomes conditional instead of hardcoded into the slider range:

    Diagonal-Dichte     50 .. 400 mm   (was 50 .. 112)
    effective spacing = Stil 2 ? min(Dichte, 112) : Dichte

The clamp is derived, not left to the operator: dragging the slider to 400 and then
switching to Stil 2 silently re-tightens the field to 112 rather than shipping a
non-compliant guard. Compliance can therefore never depend on remembering to move a
slider back.

Second fix, which only became visible once the node counts got small: the per-bay shear
was `Round(Random(-n/3 .. n/3))` and fed the two Shift Lists as +s and -s. With n = 12
a 0 was unlikely; with n = 4 it is common, and s = 0 makes BOTH directions draw the same
perfectly vertical bars — a doubled-up picket instead of a cross. The sign was always
redundant anyway (both directions are drawn regardless), so the shear is now
`max(abs(round(...)), 1)`: still seeded and still per-bay, but guaranteed to be a real
crossing.
"""

import gh
import bh
import json
import os

s = json.load(open("state.json"))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print("backup:", gh.doc("save", path=os.path.join(root, "scratch", "backup_pre_p12.gh")))
gh.doc("snapshot", name="pre_p12")
gh.doc("solver", enabled=False)

Y = 4400
MINE = {"_capD", "_2S", "_1S", "_dichteSafe", "_isStil2", "_dichteEff",
        "_shiftAbs", "_shiftMag"}
for c in gh.canvas("list", limit=700)["components"]:
    if c.get("nickname") in MINE:
        gh.canvas("delete", id=c["id"])

new_ids = []


def keep(cid):
    new_ids.append(cid)
    return cid


# --- 1. conditional compliance clamp on the node spacing -----------------------------
dichte = bh.slider_id("Diagonal-Dichte")
# `canvas set` only assigns a value and validates it against the CURRENT range, so
# widening the range needs `canvas config` first — otherwise 300 is rejected as
# "out of range [50, 112]".
r = gh.canvas("config", id=dichte, min=50, max=400, value=300)
assert r.get("success"), f"widening Diagonal-Dichte failed: {r}"
assert gh.canvas("get", id=dichte)["value"] == 300.0, "Diagonal-Dichte did not take 300"

capD = keep(bh.const(112, 150, Y, "_capD"))
c2 = keep(bh.const(2, 150, Y + 30, "_2S"))

safe = keep(bh.addf("Minimum", 330, Y, "_dichteSafe"))
bh.wire(dichte, 0, safe, "A")
bh.wire(capD, 0, safe, "B")

is2 = keep(bh.addf("Equality", 330, Y + 40, "_isStil2"))
bh.wire(bh.slider_id("Fuellung-Stil"), 0, is2, "First Number")
bh.wire(c2, 0, is2, "Second Number")

eff = keep(bh.addf("Stream Filter", 510, Y + 20, "_dichteEff"))
bh.wire(is2, "Equality", eff, 0)      # gate: false -> stream 0, true -> stream 1
bh.wire(dichte, 0, eff, 1)            # Stil 0/1: decorative, spacing as dialled
bh.wire(safe, "Result", eff, 2)       # Stil 2: load-bearing, clamped to 112

bh.clear_input(bh.by_nick("_nCell"), "B")
bh.wire(eff, 0, bh.by_nick("_nCell"), "B")

# --- 2. the per-bay shear must always cross --------------------------------------
c1 = keep(bh.const(1, 150, Y + 60, "_1S"))
shInt = bh.by_nick("_shiftInt")
sabs = keep(bh.addf("Absolute", 330, Y + 90, "_shiftAbs"))
bh.wire(shInt, "Nearest", sabs, "Value")
smag = keep(bh.addf("Maximum", 510, Y + 90, "_shiftMag"))
bh.wire(sabs, "Result", smag, "A")
bh.wire(c1, 0, smag, "B")

for target, port in ((bh.by_nick("_hiShift0"), "Shift"), (bh.by_nick("_shiftIntN"), "A")):
    bh.clear_input(target, port)
    bh.wire(smag, "Result", target, port)

gh.canvas("preview", ids=json.dumps(new_ids), enabled=False)
for cid in new_ids:
    gh.canvas("preview", id=cid, enabled=False)

s["p12"] = dict(cap=capD, safe=safe, is_stil2=is2, eff=eff, shift_mag=smag)
json.dump(s, open("state.json", "w"), indent=1)

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- verification --------------------------------------------------------------------
bad = [c for c in gh.inspect("status").get("components", [])
       if c.get("status") not in ("OK", None) and c.get("name") != "Load"]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"


def prev(cid, out=0):
    return gh.inspect("outputs", id=cid).get("outputs", [{}])[out].get("preview")


sty = bh.slider_id("Fuellung-Stil")
FINAL = s["p10"]["final"]

for style, dial, want_eff in ((1, 300, 300.0), (1, 80, 80.0), (2, 300, 112.0), (2, 80, 80.0)):
    gh.canvas("set", id=sty, value=str(style))
    gh.canvas("set", id=dichte, value=str(dial))
    gh.doc("recompute")
    got = float(prev(eff)[0])
    shifts = prev(smag)
    ndiag = bh.count(FINAL["Diagonal_Volumen"])
    nline = bh.count(s["p8"]["dAktiv"])
    print(f"Stil {style}  Dichte={dial:3d} -> effective {got:6.1f}  "
          f"shear={shifts}  diagonals={ndiag}")
    assert got == want_eff, f"Stil {style} @ {dial}: effective {got}, expected {want_eff}"
    assert all(float(x) >= 1 for x in shifts), f"shear dropped to 0: {shifts}"
    assert ndiag == nline, f"{ndiag} solids vs {nline} centrelines"

# Stil 2 must never exceed the sphere cap however the slider is dragged
gh.canvas("set", id=sty, value="2")
for dial in (50, 112, 250, 400):
    gh.canvas("set", id=dichte, value=str(dial))
    gh.doc("recompute")
    got = float(prev(eff)[0])
    assert got <= 112.0, f"Stil 2 @ Dichte={dial}: effective {got} exceeds the 112 mm cap"
print("Stil 2 stays <= 112 mm across the whole slider range  OK")

gh.canvas("set", id=sty, value="1")
gh.canvas("set", id=dichte, value="300")
gh.doc("recompute")
print("BOM:", json.dumps(
    gh.inspect("outputs", id=s["panel"]).get("outputs", [{}])[0].get("preview"),
    indent=1, ensure_ascii=False))
print(gh.doc("save", path=os.path.join(root, "Railing_Generator.gh")))
