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

"""Phase 12b — the second diagonal family was drawing vertical bars, not counter-diagonals.

Caught by measuring the line endpoints once Phase 12 made the field sparse enough to
read:

    _diagFwd  dx = +250.0  dz = 1025.0     <- a real diagonal
    _diagBwd  dx =    0.0  dz =  900.0     <- perfectly vertical

Phase 8 built the crossing pattern by shifting the UPPER rail's node list twice, once by
+s and once by -s. Phase 11d then turned `Wrap` off to stop the bay-spanning bars, and
that quietly broke the -s branch: Grasshopper's non-wrapping Shift List takes elements
from the START of the list for a negative offset, so shifting by -s returns
`hi[0 .. n-s-1]`. The following Shortest List trims the lower rail to the same length,
and `lo[i]` ends up paired with `hi[i]` — the same parameter on both rails, i.e. a
vertical line. Only the +s branch ever produced a diagonal.

It hid for two phases because at `Diagonal-Dichte` = 100 the genuine diagonals were
themselves nearly vertical, so a field of verticals looked the same; and every guard in
place (0 component errors, solids == centrelines) stayed green, because the bars WERE
being built, just in the wrong direction. Nothing counted their slope.

Fix: get the second direction by shifting the LOWER rail forward instead of the upper
rail backward. `lo[i+s] -> hi[i]` leans the other way and only ever uses the
well-behaved positive-offset semantics, so both families are built the same way:

    forward   lo[i]   -> hi[i+s]      dx = +s * spacing
    backward  lo[i+s] -> hi[i]        dx = -s * spacing

`_shiftIntN` (the x -1 multiplication that produced the negative offset) becomes dead
and is removed.
"""

import gh
import bh
import json
import os

s = json.load(open("state.json"))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
gh.doc("snapshot", name="pre_p12b")
gh.doc("solver", enabled=False)

divLo = s["p8"]["divLo"]
divHi = s["p8"]["divHi"]
smag = s["p12"]["shift_mag"]

shift1 = bh.by_nick("_hiShift1")          # currently shifts the UPPER rail by -s
pair1 = bh.by_nick("_slPair1")
bwd = bh.by_nick("_diagBwd")

# --- re-aim the second family at the LOWER rail, with a positive offset --------------
gh.canvas("rename", id=shift1, nickname="_loShift1")
bh.clear_input(shift1, "List")
bh.wire(divLo, "Points", shift1, "List")
bh.clear_input(shift1, "Shift")
bh.wire(smag, "Result", shift1, "Shift")

# Shortest List trims both sides from the start, so with A = the unshifted UPPER rail
# and B = the shifted LOWER rail the pairing becomes lo[i+s] -> hi[i].
bh.clear_input(pair1, 0)
bh.clear_input(pair1, 1)
bh.wire(divHi, "Points", pair1, 0)
bh.wire(shift1, "List", pair1, 1)

bh.clear_input(bwd, "Start")
bh.clear_input(bwd, "End")
bh.wire(pair1, 1, bwd, "Start")           # shifted lower-rail node
bh.wire(pair1, 0, bwd, "End")             # upper-rail node

# --- drop the now-dead negation -------------------------------------------------------
dead = bh.by_nick("_shiftIntN")
left = gh.wire("list", componentId=dead).get("connections", [])
downstream = [c for c in left if c.get("source", {}).get("componentId") == dead]
assert not downstream, f"_shiftIntN still feeds {downstream}"
gh.canvas("delete", id=dead)

s["p12"]["loShift"] = shift1
json.dump(s, open("state.json", "w"), indent=1)

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- verification ---------------------------------------------------------------------
bad = [c for c in gh.inspect("status").get("components", [])
       if c.get("status") not in ("OK", None) and c.get("name") != "Load"]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"


def slopes(nick, n=4):
    """(dx, dz) of the first n lines — the check that was missing all along."""
    g = gh.inspect("geometry", id=bh.by_nick(nick)).get("outputs", [{}])[0]
    out = []
    for it in (g.get("items") or [])[:n]:
        p = [float(x) for x in it.get("value", "").split(",")]
        out.append((p[3] - p[0], p[5] - p[2]))
    return out


for nick, sign in (("_diagFwd", +1), ("_diagBwd", -1)):
    sl = slopes(nick)
    print(f"{nick}: " + "  ".join(f"dx={dx:+8.1f} dz={dz:7.1f}" for dx, dz in sl))
    assert sl, f"{nick} produced no lines"
    for dx, _dz in sl:
        assert dx * sign > 0, f"{nick}: dx={dx} does not lean {'+' if sign > 0 else '-'}"
print("both families lean opposite ways  OK")

sty = bh.slider_id("Fuellung-Stil")
dichte = bh.slider_id("Diagonal-Dichte")
FINAL = s["p10"]["final"]
for style, dial in ((1, 300), (1, 80), (2, 300), (2, 80)):
    gh.canvas("set", id=sty, value=str(style))
    gh.canvas("set", id=dichte, value=str(dial))
    gh.doc("recompute")
    nd, nl = bh.count(FINAL["Diagonal_Volumen"]), bh.count(s["p8"]["dAktiv"])
    fwd, bwd_s = slopes("_diagFwd", 1), slopes("_diagBwd", 1)
    print(f"Stil {style} Dichte={dial:3d}: diagonals={nd:4d}  "
          f"fwd dx={fwd[0][0]:+7.1f}  bwd dx={bwd_s[0][0]:+7.1f}")
    assert nd == nl, f"{nd} solids vs {nl} centrelines"
    assert fwd[0][0] > 0 > bwd_s[0][0], "families no longer cross"

gh.canvas("set", id=sty, value="1")
gh.canvas("set", id=dichte, value="300")
gh.doc("recompute")
print("BOM:", json.dumps(
    gh.inspect("outputs", id=s["panel"]).get("outputs", [{}])[0].get("preview"),
    indent=1, ensure_ascii=False))
print(gh.doc("save", path=os.path.join(root, "Railing_Generator.gh")))
