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

"""Phase 14c — Normpruefung anschliessen (OIB-RL 4, Pkt. 4.2.3/4.2.4).

Zwei neue Eingaenge und ein neuer Ausgang an der Muster-Engine:
  Ug   Untergurt-Abstand (bestehender Regler) — verschiebt das Fenster
       150..600 mm ueber Stufenvorderkante in das lokale Feldsystem
  Kw   Grenzwinkel "begehbar". Die Richtlinie nennt bewusst KEINEN Winkel,
       nur den 3-cm-Vorsprung. 60 deg ist Sachverstaendigenpraxis, 75 deg die
       konservative Auslegung — deshalb ein Regler und keine Konstante.
  Norm Ausgabe fuer das Angebot/Datenblatt.
"""
import json, os
import bh, gh

HERE = os.path.dirname(os.path.abspath(__file__))
UNTERGURT_SLIDER = "a77c58f3-0379-43ef-9d2e-04980537e76b"

st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
MID = st["p14"]["engine"]

IN_SPEC = [
    ("Lo", "Curve", "list"), ("Hi", "Curve", "list"),
    ("M", "int", "item"), ("Dc", "double", "item"), ("S", "int", "item"),
    ("N", "Vector3d", "item"), ("A", "double", "item"),
    ("Gmax", "double", "item"), ("Bw", "double", "item"),
    ("Hd", "double", "item"), ("Hl", "double", "item"), ("Ho", "double", "item"),
    ("Bd", "double", "item"), ("Bs", "double", "item"), ("Br", "double", "item"),
    ("Fd", "double", "item"), ("Vw", "double", "item"),
    ("Ug", "double", "item"), ("Kw", "double", "item"),
]
OUT = ["Stab1", "Stab2", "Stahl", "Holz", "Info", "Check", "Norm"]

gh.doc("solver", enabled="false")
try:
    r = gh.script("configure", id=MID,
                  inputs=json.dumps([{"name": n, "type": t, "access": a}
                                     for n, t, a in IN_SPEC]),
                  outputs=json.dumps([{"name": n, "type": "Generic Data",
                                       "access": "list"} for n in OUT]),
                  code=open(os.path.join(HERE, "patterns.py"),
                            encoding="utf-8").read())
    lost = r.get("lostConnections")
    if lost:
        # Ports, die namensgleich bleiben, behalten ihre Draehte; alles andere
        # meldet Cordyceps hier und laesst es sich direkt zurueckstecken.
        gh.wire("connect", connections=json.dumps(lost) if not isinstance(lost, str) else lost)
        print("  Verbindungen wiederhergestellt:", lost)

    info = gh.script("info", id=MID)
    have_in = {p.get("name") for p in info.get("inputs", [])}
    have_out = {p.get("name") for p in info.get("outputs", [])}
    assert not [n for n, _, _ in IN_SPEC if n not in have_in], sorted(have_in)
    assert not [n for n in OUT if n not in have_out], sorted(have_out)

    bh.wire(UNTERGURT_SLIDER, 0, MID, "Ug")
    kw = bh.slider("Kletterwinkel-Grenze", 45, 80, 60, 0, -900, 2202 + 52)
    bh.wire(kw, 0, MID, "Kw")
    npan = bh.add("Panel", -380 + 260, 1450 + 260, "Muster_Norm")
    bh.wire(MID, "Norm", npan, 0)
finally:
    gh.doc("solver", enabled="true")
gh.doc("recompute")

st["p14"]["kletterwinkel"] = kw
st["p14"]["norm_panel"] = npan
json.dump(st, open(os.path.join(HERE, "state.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

o = {x.get("name"): x for x in gh.inspect("outputs", id=MID).get("outputs", [])}
for line in (o.get("Norm", {}).get("preview") or []):
    print("  ", line)
print("  Stab1:", o.get("Stab1", {}).get("count"), " branches:", o.get("Stab1", {}).get("branches"))
