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

"""Staged stair build — solver ON after each stage, save after each stage.
Finds which stage crashes Rhino (if any).
"""
import json, os, sys, time
import gh as g

# Cordyceps braucht ABSOLUTE Pfade — es laeuft in Rhino, nicht in diesem
# Prozess. Deshalb aus dem Skriptort abgeleitet statt fest verdrahtet.
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GH_FILE = os.path.join(REPO, "Railing_Generator.gh")
SHOT = os.path.join(REPO, "grasshopper", "viewport_stairs.png")

def call(name, arguments, tries=3):
    for i in range(tries):
        try:
            return g.call(name, arguments)
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after {type(e).__name__}", flush=True)
            time.sleep(2)

def canvas(action, **kw):   return call("gh_canvas", {"action": action, **kw})
def wire(action, **kw):     return call("gh_wire", {"action": action, **kw})
def doc(action, **kw):      return call("gh_document", {"action": action, **kw})
def inspect_(action="status", **kw): return call("gh_inspect", {"action": action, **kw})

def add(t, x, y, nick, **kw):
    r = canvas("add", type=t, x=x, y=y, nickname=nick, **kw)
    assert isinstance(r, dict) and "id" in r, f"add failed {nick}: {r}"
    print(f"  + {nick} ({r['id'][:8]})", flush=True)
    return r["id"]

def connect(s, sp, t, tp):
    r = wire("connect", sourceId=s, sourceParam=sp, targetId=t, targetParam=tp)
    assert isinstance(r, dict) and r.get("success"), f"wire failed {s}.{sp}->{t}.{tp}: {r}"

def solve_and_check(stage):
    doc("solver", enabled=True)
    doc("recompute")
    time.sleep(0.5)
    st = inspect_("status")
    bad = [c for c in st.get("components", []) if c.get("status") != "OK"]
    print(f"STAGE {stage} OK — bad: {[(c.get('nickname'), c.get('status')) for c in bad]}", flush=True)
    doc("save", path=GH_FILE)
    doc("solver", enabled=False)
    return bad

# snapshot first
try:
    print("snapshot:", doc("snapshot", name="before_stairs"), flush=True)
except Exception as e:
    print("snapshot failed:", e, flush=True)

lst = canvas("list")
comps = lst["components"] if isinstance(lst, dict) and "components" in lst else lst
line_id = run_slider = None
for c in comps:
    nick = (c.get("nickname") or "").lower()
    name = (c.get("name") or "").lower()
    if "treppenbasislinie" in nick:
        line_id = c["id"]
    if "number slider" in name and ("run" in nick or "lauf" in nick):
        run_slider = c["id"]
if not line_id:
    for c in comps:
        if c.get("name") == "Line":
            line_id = c["id"]
print("line:", line_id, "run slider:", run_slider, flush=True)

def guid(q):
    r = canvas("search", query=q)
    cs = r.get("components", [])
    exact = [c for c in cs if c["name"].lower() == q.lower()]
    pick = exact[0] if exact else cs[0]
    print(f"  search '{q}' -> {pick['name']} {pick['guid']}", flush=True)
    return pick["guid"]

doc("solver", enabled=False)

stage = sys.argv[1] if len(sys.argv) > 1 else "all"
X0, Y0 = 300, -700

if stage in ("A", "all"):
    g_divide = guid("Divide Curve")
    sN = add("Slider", X0, Y0, "Stufenzahl", min=1, max=40, value=13, decimals=0)
    dc2 = add(g_divide, X0+220, Y0, "Stufenpunkte")
    connect(line_id, 0, dc2, 0)
    connect(sN, 0, dc2, 1)
    solve_and_check("A")

if stage in ("B", "all"):
    g_cull = guid("Cull Index")
    g_decon = guid("Deconstruct Point")
    sZero = add("Slider", X0+380, Y0+60, "idx0", min=0, max=10, value=0, decimals=0)
    cull = add(g_cull, X0+380, Y0, "ohne Fusspunkt")
    dpt = add(g_decon, X0+540, Y0, "Nosing XYZ")
    lst2 = canvas("list")
    dc2 = [c["id"] for c in (lst2["components"] if "components" in lst2 else lst2) if c.get("nickname") == "Stufenpunkte"][0]
    connect(dc2, 0, cull, 0)
    connect(sZero, 0, cull, 1)
    connect(cull, 0, dpt, 0)
    solve_and_check("B")

if stage in ("C", "all"):
    g_div = guid("Division")
    g_sub = guid("Subtraction")
    g_cpt = guid("Construct Point")
    sW = add("Slider", X0, Y0+80, "Trittbreite", min=400, max=3000, value=1200, decimals=0)
    sT = add("Slider", X0, Y0+160, "Stufenstaerke", min=10, max=200, value=40, decimals=0)
    sTwo = add("Slider", X0, Y0+240, "const2", min=0, max=4, value=2, decimals=0)
    dDep = add(g_div, X0+380, Y0+140, "Tritt = Lauf/N")
    dDep2 = add(g_div, X0+540, Y0+220, "Tritt/2")
    subX = add(g_sub, X0+700, Y0+80, "X - Tritt/2")
    dW2 = add(g_div, X0+540, Y0+300, "Breite/2")
    subY = add(g_sub, X0+700, Y0+160, "Y - Breite/2")
    dT2 = add(g_div, X0+540, Y0+380, "Staerke/2")
    subZ = add(g_sub, X0+700, Y0+240, "Z - Staerke/2")
    cpt = add(g_cpt, X0+880, Y0+80, "Tritt-Mitte")

    lst2 = canvas("list")
    cl = lst2["components"] if "components" in lst2 else lst2
    bynick = {c.get("nickname"): c["id"] for c in cl}
    sN = bynick["Stufenzahl"]; dpt = bynick["Nosing XYZ"]
    if run_slider:
        connect(run_slider, 0, dDep, 0)
    else:
        sRun = add("Slider", X0+220, Y0+140, "Lauf", min=500, max=20000, value=4000, decimals=0)
        connect(sRun, 0, dDep, 0)
    connect(sN, 0, dDep, 1)
    connect(dDep, 0, dDep2, 0)
    connect(sTwo, 0, dDep2, 1)
    connect(dpt, 0, subX, 0)
    connect(dDep2, 0, subX, 1)
    connect(sW, 0, dW2, 0)
    connect(sTwo, 0, dW2, 1)
    connect(dpt, 1, subY, 0)
    connect(dW2, 0, subY, 1)
    connect(sT, 0, dT2, 0)
    connect(sTwo, 0, dT2, 1)
    connect(dpt, 2, subZ, 0)
    connect(dT2, 0, subZ, 1)
    connect(subX, 0, cpt, 0)
    connect(subY, 0, cpt, 1)
    connect(subZ, 0, cpt, 2)
    solve_and_check("C")

if stage in ("D", "all"):
    g_box = guid("Center Box")
    box = add(g_box, X0+1060, Y0+80, "Treppe")
    lst2 = canvas("list")
    cl = lst2["components"] if "components" in lst2 else lst2
    bynick = {c.get("nickname"): c["id"] for c in cl}
    connect(bynick["Tritt-Mitte"], 0, box, 0)
    connect(bynick["Tritt = Lauf/N"], 0, box, 1)
    connect(bynick["Trittbreite"], 0, box, 2)
    connect(bynick["Stufenstaerke"], 0, box, 3)
    bad = solve_and_check("D")
    out = inspect_("outputs", id=box)
    print("Treppe outputs:", json.dumps(out)[:500], flush=True)
    canvas("preview", ids=json.dumps([box]), enabled=True)
    doc("solver", enabled=True)
    doc("capture_viewport", path=SHOT)
    doc("save", path=GH_FILE)
    print("DONE", flush=True)
