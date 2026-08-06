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

"""Phase 14f — Info-Ausgang reparieren und die zwei fehlenden BOM-Zeilen bauen.

Zwei Befunde aus der Schlusskontrolle:

1. `Info` lieferte genau EIN Element, und das war null. Beim Einbau der
   Normpruefung wurde der Dateirest ab "free = sum(...)" ersetzt — und der
   Info-Block stand darin. GH meldet eine nicht zugewiesene Ausgangsvariable
   nicht als Fehler, sondern schiebt still einen Null-Eintrag raus.

2. Die Stueckliste hatte keine Zeilen fuer Blech und Holz, obwohl `GESAMT` sie
   schon mitrechnete. Bei einem Holzmuster stand damit eine Summe da, die
   groesser war als die Summe der aufgefuehrten Posten — die gleiche stille
   Klasse wie die Null aus der Mass Addition, nur andersherum.
"""
import json, os
import bh, gh

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_BOM = "72f35682-ea93-49bb-b010-1866807b272d"
PANEL_UNIT = "b0519074-1ff4-4ba8-9e1c-1bd54e57a9a2"   # gemeinsames " kg" der Zeilen

st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
p14 = st["p14"]

gh.doc("solver", enabled="false")
try:
    gh.script("configure", id=p14["engine"],
              code=open(os.path.join(HERE, "patterns.py"),
                        encoding="utf-8").read())

    # Das Einheiten-Panel aus einer bestehenden Zeile holen statt es zu raten.
    unit = None
    for c in gh.wire("list", componentId="1ca230d1-3938-4bd8-82fa-dd3a999fc0c7"
                     ).get("connections", []):
        t = c.get("target", {})
        if str(t.get("param", "")).lower().endswith("b") and t.get("name") == "Concatenate":
            unit = c["source"]["componentId"]
    assert unit, "Einheiten-Panel der bestehenden BOM-Zeilen nicht gefunden"

    rows = [("Blech/Laserteile: ", p14["kg_stahl"], 3600),
            ("Holzfuellung: ", p14["kg_holz"], 3680)]
    made = []
    for label, kg_src, y in rows:
        lab = bh.add("Panel", 2400, y, "_lbl" + label[:5].strip(": "))
        gh.canvas("set", id=lab, value=label)
        a = bh.add("Concatenate", 2550, y, "_cAB_" + label[:3])
        bh.wire(lab, 0, a, "Fragment A")
        bh.wire(kg_src, "Result", a, "Fragment B")
        b = bh.add("Concatenate", 2700, y, "_cBB_" + label[:3])
        bh.wire(a, "Result", b, "Fragment A")
        bh.wire(unit, 0, b, "Fragment B")
        bh.wire(b, "Result", PANEL_BOM, 0)
        made.append(b)
finally:
    gh.doc("solver", enabled="true")
gh.doc("recompute")

p14["bom_rows"] = made
json.dump(st, open(os.path.join(HERE, "state.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

o = {x.get("name"): x for x in gh.inspect("outputs", id=p14["engine"]).get("outputs", [])}
print("Info:", o.get("Info", {}).get("count"), (o.get("Info", {}).get("preview") or [None])[0])
print("STATUS:", gh.inspect("status").get("summary"))
