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

"""Phase 11f — a switched-off infill style must weigh 0 kg, not one metre of stock.

Found while collecting the per-style BOM for the customer export.  `Fuellung-Stil`
culls one of the two infill fields with a Cull Pattern, and the culled branch then
carries NO data at all:

    Diagonal_Aktiv count=0  ->  _len_Diag count=0
    _sum_Diag      count=1, value null      (Mass Addition of an empty list)
    _m_Diag        count=1, value null
    kg_Diag        count=1, value 2.512     <- the kg/m, passed straight through

Grasshopper's arithmetic components treat a null operand as the identity, so
`null x 2.512 kg/m` came out as 2.512 kg — exactly one metre of the flat bar — and
nothing anywhere reported a warning, which is why the "0 component errors" regression
never saw it.  Stil 0 billed 2.512 kg of diagonals it does not have; Stil 2 billed
0.888 kg of vertical bars it does not have.

Fix: merge a constant 0 into the length list before the Mass Addition.  Adding 0 is a
no-op when bars exist and forces a real 0 when they do not, so the null never enters
the chain.  Applied to both culled roles.
"""

import gh
import bh
import json
import os

s = json.load(open("state.json"))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
gh.doc("snapshot", name="pre_p11f")
gh.doc("solver", enabled=False)

Y = 4200
for c in gh.canvas("list", limit=600)["components"]:
    if c.get("nickname") in (
        "_zeroLen",
        "_lenOr0_F",
        "_lenOr0_D",
        "_flatLen_F",
        "_flatLen_D",
    ):
        gh.canvas("delete", id=c["id"])

zero = bh.const(0, 150, Y, "_zeroLen")
new_ids = [zero]

for tag, length_nick, sum_nick in (
    ("F", "_len_Fuell", "_sum_Fuell"),
    ("D", "_len_Diag", "_sum_Diag"),
):
    ln, sm = bh.by_nick(length_nick), bh.by_nick(sum_nick)
    mrg = bh.addf("Merge", 330, Y + 40 * (tag == "D"), f"_lenOr0_{tag}")
    new_ids.append(mrg)
    bh.wire(ln, "Length", mrg, 0)
    bh.wire(zero, 0, mrg, 1)
    # Merge puts each input on its OWN branch, and Mass Addition sums per branch —
    # without flattening the guard produced two sums (the real one and the 0), which
    # duplicated every BOM row. Flatten so it stays a single list.
    flt = bh.addf("Flatten Tree", 510, Y + 40 * (tag == "D"), f"_flatLen_{tag}")
    new_ids.append(flt)
    bh.wire(mrg, 0, flt, 0)
    bh.clear_input(sm, "Input")
    bh.wire(flt, 0, sm, "Input")

gh.canvas("preview", ids=json.dumps(new_ids), enabled=False)
s["p11"]["bom_zero_guard"] = new_ids
json.dump(s, open("state.json", "w"), indent=1)

gh.doc("solver", enabled=True)
gh.doc("recompute")

# --- verification -----------------------------------------------------------------
bad = [
    c
    for c in gh.inspect("status").get("components", [])
    if c.get("status") not in ("OK", None) and c.get("name") != "Load"
]
print("NON-OK:", json.dumps(bad, ensure_ascii=False))
assert not bad, "components broke"

sl = bh.slider_id("Fuellung-Stil")


def bom():
    rows = gh.inspect("outputs", id=s["panel"]).get("outputs", [{}])[0].get("preview")
    return {r.split(":")[0]: float(r.split(":")[1].replace(" kg", "")) for r in rows}


EXPECT_ZERO = {0: "Diagonalen Flachstahl", 2: "Fuellstaebe Oe12"}
for style in (0, 1, 2):
    gh.canvas("set", id=sl, value=str(style))
    gh.doc("recompute")
    b = bom()
    print(f"Stil {style}: " + ", ".join(f"{k}={v:.3f}" for k, v in b.items()))
    if style in EXPECT_ZERO:
        got = b[EXPECT_ZERO[style]]
        assert got == 0.0, f"Stil {style}: {EXPECT_ZERO[style]} = {got}, expected 0"
    parts = sum(v for k, v in b.items() if k != "GESAMT")
    assert abs(parts - b["GESAMT"]) < 1e-6, (
        f"Stil {style}: parts {parts} != GESAMT {b['GESAMT']}"
    )

gh.canvas("set", id=sl, value="1")
gh.doc("recompute")
print(gh.doc("save", path=os.path.join(root, "Railing_Generator.gh")))
