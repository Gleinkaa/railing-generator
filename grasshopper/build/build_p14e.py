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

"""Phase 14e — die alte Erzeugerkette abraeumen.

`Fuellung-Stil` (0/1/2) ist durch `Muster` (0..33) ersetzt. Die alte Kette —
Line-SDL-Fuellstaebe, die komplette Diagonalen-Maschinerie aus Phase 8/11/12
und die beiden Cull-Pattern-Tore — rechnet seither ins Leere.

Geloescht wird NICHT nach Liste, sondern nach Abhaengigkeit: in jeder Runde
faellt nur weg, was (a) im Kandidatensatz steht UND (b) keinen einzigen
Empfaenger mehr hat. Damit kann nichts geloescht werden, das noch irgendwo
haengt — auch dann nicht, wenn ich den Kandidatensatz zu weit gefasst habe.
Die Kette schaelt sich so von hinten nach vorne ab.
"""
import json, os
import gh

HERE = os.path.dirname(os.path.abspath(__file__))

# Alles, was ausschliesslich die alten drei Stile bedient hat.
CANDIDATES = {
    # Vertikalzweig
    "_Seg/Abstand", "_Round3", "_TeilerFuell", "_Flatten", "_CullDup",
    "_ZdirFuell", "Fuellstaebe", "Vertikal_Aktiv", "_vertOn", "Fuellstab-Abstand",
    # Diagonalzweig
    "_segLenD", "_nCell", "_nCeil", "_divLo", "_divHi", "_third", "_thirdN",
    "_shiftDom", "_nBays", "_bayIdx", "_seedBay", "_rndShift", "_shiftInt",
    "_hiShift0", "_diagFwd", "_loShift1", "_diagBwd", "_diagLines", "_diagFlat",
    "_auslVec", "_diagOut", "_diagOn", "Diagonal_Aktiv", "_slPair0", "_slPair1",
    "_shiftAbs", "_shiftMag",
    # Stil-Umschaltung samt abgeleitetem Deckel aus Phase 12
    "Fuellung-Stil", "_dichteSafe", "_isStil2", "_dichteEff",
}


def index():
    by_id = {}
    for c in gh.canvas("list", limit=1000).get("components", []):
        by_id[c["id"]] = c.get("nickname") or c.get("name") or ""
    return by_id


def recipients(cid):
    n = 0
    for c in gh.wire("list", componentId=cid).get("connections", []):
        if c.get("source", {}).get("componentId") == cid:
            n += 1
    return n


gh.doc("solver", enabled="false")
removed, rounds = [], 0
try:
    while True:
        rounds += 1
        by_id = index()
        targets = [cid for cid, nick in by_id.items()
                   if nick in CANDIDATES and recipients(cid) == 0]
        if not targets:
            break
        for cid in targets:
            nick = by_id[cid]
            r = gh.canvas("delete", ids=json.dumps([cid]))
            if r.get("success"):
                removed.append(nick)
            else:
                print(f"  ! {nick} nicht geloescht: {r}")
finally:
    gh.doc("solver", enabled="true")
gh.doc("recompute")

by_id = index()
left = sorted(n for n in by_id.values() if n in CANDIDATES)
print(f"  {len(removed)} Objekte in {rounds} Runden entfernt")
print("  entfernt:", ", ".join(sorted(removed)))
if left:
    print("  ABSICHTLICH STEHEN GEBLIEBEN (haben noch Empfaenger):", ", ".join(left))

s = gh.inspect("status")
print("  STATUS:", s.get("summary"))
bad = [c for c in s.get("components", [])
       if c.get("status") in ("ERROR", "WARNING") and c.get("name") != "Load"]
for c in bad:
    print(f"  !! {c.get('nickname') or c.get('name')}: {c.get('message')}")
d = gh.inspect("disconnected")
print("  disconnected:", d.get("count", d))
