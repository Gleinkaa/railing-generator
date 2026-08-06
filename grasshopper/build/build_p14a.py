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

"""Phase 14a — Fix: die Muster-Engine lief fuenfmal.

_edgeN1 liefert EINEN Vektor JE POSTEN (5 Stueck). Am item-Eingang `N` haengt
das den ganzen Solver in eine Schleife: 5 Laeufe, jeder mit der vollstaendigen
Feldliste -> 200 statt 40 Fuellstaeben, fuenffach uebereinander.

Der Fehler war an KEINER Komponente sichtbar: 0 Fehler, 0 Warnungen, und die
Stueckliste stimmt sogar in sich (sie zaehlt dieselbe verfuenffachte Liste).
Genau dieselbe Klasse wie der 41x41-Sweep und die Nullen in der Mass Addition —
Zaehlungen pruefen, nicht nur Statusfarben.

Fix: List Item(0) davor. Die Normalen sind an allen Posten gleich (gerader
Lauf), und die Engine baut ihr Feldsystem ohnehin selbst — sie braucht nur die
Richtung "nach aussen".
"""
import json, os
import bh, gh

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE_N1 = "4692fe11-c2a6-40fe-a86f-7bcbb134f43e"
GUID_LISTITEM = None

st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
MID = st["p14"]["engine"]

hits = gh.canvas("search", query="List Item").get("components") or []
pool = [h for h in hits if h.get("name") == "List Item" and not h.get("deprecated")]
assert pool, f"List Item nicht gefunden: {hits[:3]}"
GUID_LISTITEM = pool[0]["guid"]
print("List Item:", GUID_LISTITEM)

gh.doc("solver", enabled="false")
try:
    li = bh.add(GUID_LISTITEM, -560, 1560, "_nrmOne")
    bh.wire(EDGE_N1, 0, li, "List")
    idx0 = bh.const(0, -560, 1620, "_nrmIdx")
    bh.wire(idx0, 0, li, "Index")
    bh.clear_input(MID, "N")
    bh.wire(li, "Item", MID, "N")
finally:
    gh.doc("solver", enabled="true")
gh.doc("recompute")

st["p14"]["nrm_one"] = li
json.dump(st, open(os.path.join(HERE, "state.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

r = gh.inspect("outputs", id=MID)
for o in r.get("outputs", []):
    print(f"  {o.get('name')}: count={o.get('count')} branches={o.get('branches')}")
