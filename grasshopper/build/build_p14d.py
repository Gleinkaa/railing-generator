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

"""Phase 14d — Vorschau und Gruppierung fuer die neuen Materialkanaele.

Die Muster-Engine fuehrt Mittellinien UND Solids auf einer Komponente, ihre
Vorschau muss deshalb aus sein — sonst haengen die Fuellstab-Mittellinien als
Drahtgitter im Modell. Damit hatten Holz und Blech aber ueberhaupt keine
Vorschauquelle mehr, und im Viewport blieben nur die Schwerpunkt-Punkte der
Volume-Komponenten uebrig (im Bild: eine Wolke roter Punkte statt Holzbloecken).
Die Geometrie war die ganze Zeit korrekt — 27,6 kg Holz aus 44 Bloecken —
sichtbar war sie nicht.

Also bekommen die beiden Solid-Kanaele eigene Brep-Parameter als Endstufen,
genau wie die sieben Endstufen aus Phase 10, und alles neu Gebaute, das keine
Endstufe ist, wird auf preview=off gesetzt.
"""
import json, os
import bh, gh

HERE = os.path.dirname(os.path.abspath(__file__))
GUID_BREP_PARAM = "919e146f-30ae-4aae-be34-4d72f555e7da"

st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
p14 = st["p14"]
MID = p14["engine"]

gh.doc("solver", enabled="false")
try:
    holz = bh.add(GUID_BREP_PARAM, -80, 1450, "Holz_Volumen")
    bh.wire(MID, "Holz", holz, 0)
    blech = bh.add(GUID_BREP_PARAM, -80, 1520, "Blech_Volumen")
    bh.wire(MID, "Stahl", blech, 0)

    # Alles, was Phase 14 sonst noch angelegt hat, ist Rechenweg und darf nicht
    # in den Viewport zeichnen. Die Volume-Komponenten sind die eigentlichen
    # Uebeltaeter — sie zeigen ihren Schwerpunkt als Punkt.
    quiet = [MID]
    for key in ("kg_stahl", "kg_holz", "add_sh", "total", "nrm_one"):
        if p14.get(key):
            quiet.append(p14[key])
    for c in gh.canvas("list", limit=1000).get("components", []):
        nick = c.get("nickname") or ""
        if (nick.startswith(("_vol", "_sumVol", "_m3", "_null", "_nrm"))
                or nick in ("kg_Stahl", "kg_Holz", "_addSH", "kg_GESAMT_MAT")):
            quiet.append(c["id"])
    for cid in set(quiet):
        gh.canvas("preview", id=cid, enabled="false")
    for cid in (holz, blech):
        gh.canvas("preview", id=cid, enabled="true")

    # Regler in eine eigene Gruppe, passend zur Spalte aus Phase 10.
    members = list(p14["sliders"].values()) + [p14.get("kletterwinkel"),
                                               p14.get("rho_holz")]
    members = [m for m in members if m]
    g = gh.canvas("group_create", ids=json.dumps(members),
                  name="07 - MUSTER", color="#7FB3C8")
    print("  Gruppe:", g.get("success"), len(members), "Regler")
finally:
    gh.doc("solver", enabled="true")
gh.doc("recompute")

p14["holz_param"] = holz
p14["blech_param"] = blech
json.dump(st, open(os.path.join(HERE, "state.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

s = gh.inspect("status").get("summary", {})
print("  STATUS:", s)
print("  Holz_Volumen:", bh.count(holz), " Blech_Volumen:", bh.count(blech))
