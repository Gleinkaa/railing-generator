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

"""Phase-14-Regression: alle 34 Muster durchfahren und haerter pruefen als
"0 Komponentenfehler".

Je Muster wird geprueft:
  1. keine Komponente in ERROR/WARNING (ausser dem bekannten Volvox-"Load")
  2. Solids == Mittellinien je Stabkanal — der 41x41-Sweepfehler war unsichtbar,
     solange nur die Stueckliste geprueft wurde
  3. freie Stabenden == 0 (K1 der Rework-Instructions)
  4. Kanaele, die etwas liefern MUESSEN, liefern auch etwas: ein Muster, das
     nichts baut, ist ein stiller Ausfall und kein gruener Lauf
"""
import json, os, sys, time
import bh, gh

HERE = os.path.dirname(os.path.abspath(__file__))
st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
MID = st["p14"]["engine"]
SLIDER = st["p14"]["sliders"]["Muster"]

VOL_FUELL = "9f12cb7d-14b3-4d89-9f4e-c36c8cd6db68"
VOL_DIAG = "7a5ee33f-96ae-4193-9bab-1768e92a6435"

# Erwartungshaltung je Muster: welche Kanaele MUESSEN belegt sein.
# Staggered Panels, Wide Slats, Diamond Lattice, Segmented Panels
NEEDS_HOLZ = {1, 5, 8, 10}
# Ellipse Sheet, Grain Sheet, Width Wave, Alternating Bars, Twisted Bars
NEEDS_STAHL = {11, 14, 19, 20, 31}
# rein aus Solids gebaut (Blech / Flachstahl / tordierte Staebe)
NO_STAB1 = {11, 14, 19, 20, 31}


def outs(cid):
    return {o.get("name"): o for o in gh.inspect("outputs", id=cid).get("outputs", [])}


def count(cid, name=None, idx=0):
    o = outs(cid)
    if name:
        assert name in o, f"{cid}: kein Ausgang {name}"
        v = o[name].get("count")
    else:
        v = list(o.values())[idx].get("count")
    assert v is not None, f"{cid}/{name}: kein count"
    return int(v)


def run(m):
    gh.canvas("set", id=SLIDER, value=str(m))
    # Zurueckgelesen statt geglaubt — und zwar ueber `get`, nicht `info`:
    # `info` meldet fuer einen Slider gar keinen Wert und lieferte still None.
    got = gh.canvas("get", id=SLIDER).get("value")
    assert got is not None and abs(float(got) - m) < 1e-6,         f"Regler Muster steht auf {got!r}, sollte {m} sein"
    # Der erste Durchlauf hat Muster 0 gemeldet und dabei noch Muster 30
    # gerechnet: die Ausgaben sind unmittelbar nach `recompute` gelegentlich
    # noch der vorige Stand. Also so lange nachrechnen, bis die Engine selbst
    # den erwarteten Index meldet — sonst faerbt eine Verzoegerung die
    # Regression gruen fuer Geometrie, die nie berechnet wurde.
    for attempt in range(4):
        gh.doc("recompute")
        chk = outs(MID).get("Check", {}).get("preview") or []
        if chk and chk[0].startswith("Muster %02d " % m):
            break
        time.sleep(0.4)
    else:
        raise AssertionError(f"Engine meldet {chk[:1]!r}, erwartet Muster {m:02d}")
    o = outs(MID)
    chk = o.get("Check", {}).get("preview") or []
    name = chk[0] if chk else "?"
    free, climb = -1, -1
    for line in chk:
        if line.startswith("freie Stabenden"):
            free = int(line.split(":")[1].split("(")[0].strip())
        if line.startswith("flach in Zone A"):
            climb = int(line.split(":")[1].split("Staebe")[0].strip())
    n1 = int(o["Stab1"].get("count") or 0)
    n2 = int(o["Stab2"].get("count") or 0)
    nst = int(o["Stahl"].get("count") or 0)
    nhz = int(o["Holz"].get("count") or 0)
    v1 = count(VOL_FUELL)
    v2 = count(VOL_DIAG)

    status = gh.inspect("status")
    bad = [c for c in status.get("components", [])
           if c.get("status") in ("ERROR", "WARNING") and c.get("name") != "Load"]

    errs = []
    if bad:
        errs.append("KOMPONENTEN " + "; ".join(
            f"{c.get('nickname') or c.get('name')}={c.get('message')}" for c in bad[:4]))
    if v1 != n1:
        errs.append(f"Fuellstab-Solids {v1} != Mittellinien {n1}")
    if v2 != n2:
        errs.append(f"Diagonal-Solids {v2} != Mittellinien {n2}")
    if free != 0:
        errs.append(f"freie Stabenden {free}")
    if m in NEEDS_HOLZ and nhz == 0:
        errs.append("Holz-Kanal leer, obwohl Holzmuster")
    if m in NEEDS_STAHL and nst == 0:
        errs.append("Stahl-Kanal leer, obwohl Blech/Flachstahl/tordiert")
    if m not in NO_STAB1 and n1 == 0 and n2 == 0:
        errs.append("kein einziger Stab gebaut")
    return name, (n1, n2, nst, nhz), errs, climb


bad_total = []
print(f"{'M':>3} {'Name':<24} {'Stab1':>6}{'Stab2':>6}{'Stahl':>6}{'Holz':>6}{'ZoneA':>6}  Befund")
for m in range(34):
    try:
        name, c, errs, climb = run(m)
    except Exception as exc:
        name, c, errs, climb = "?", (0, 0, 0, 0), [f"EXCEPTION {exc}"], -1
    flag = "OK" if not errs else " | ".join(errs)
    print(f"{m:>3} {name[:24]:<24} {c[0]:>6}{c[1]:>6}{c[2]:>6}{c[3]:>6}{climb:>6}  {flag}")
    if errs:
        bad_total.append((m, name, errs))

print()
if bad_total:
    print(f"FEHLGESCHLAGEN: {len(bad_total)}/34")
    sys.exit(1)
print("ALLE 34 MUSTER GRUEN")
print("ZoneA = Staebe, die zwischen 150 und 600 mm ueber Stufenvorderkante flacher")
print("       als 60 deg verlaufen (OIB-RL 4, Pkt. 4.2.3). Kein Fehler, sondern die")
print("       Liste der Muster, die ohne Zusatzmassnahme nicht genehmigungsfaehig sind.")
