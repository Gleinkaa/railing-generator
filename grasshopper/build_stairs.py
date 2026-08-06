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

"""Add a parametric stair (floating treads) under the existing railing. v2

Changes vs v1: no pinned min==max sliders (suspected crash source),
retry on transient connection errors, progress prints.
"""
import json, os, sys, time
import gh as g

# Cordyceps braucht ABSOLUTE Pfade — es laeuft in Rhino, nicht in diesem
# Prozess. Deshalb aus dem Skriptort abgeleitet statt fest verdrahtet.
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GH_FILE = os.path.join(REPO, "Railing_Generator.gh")
SHOT = os.path.join(REPO, "grasshopper", "viewport_stairs.png")

def call(name, arguments, tries=4):
    for i in range(tries):
        try:
            return g.call(name, arguments)
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after {type(e).__name__}")
            time.sleep(2)

def canvas(action, **kw):   return call("gh_canvas", {"action": action, **kw})
def wire(action, **kw):     return call("gh_wire", {"action": action, **kw})
def doc(action, **kw):      return call("gh_document", {"action": action, **kw})
def inspect_(action="status", **kw): return call("gh_inspect", {"action": action, **kw})

def search_guid(query):
    r = canvas("search", query=query)
    comps = r.get("components", []) if isinstance(r, dict) else []
    if not comps:
        raise RuntimeError(f"component not found: {query}")
    return comps[0]["guid"]

def add(guid_or_slider, x, y, nickname, **kw):
    r = canvas("add", type=guid_or_slider, x=x, y=y, nickname=nickname, **kw)
    if not isinstance(r, dict) or "id" not in r:
        raise RuntimeError(f"add failed for {nickname}: {r}")
    print(f"  + {nickname}")
    return r["id"]

def connect(src, sp, tgt, tp):
    r = wire("connect", sourceId=src, sourceParam=sp, targetId=tgt, targetParam=tp)
    if not (isinstance(r, dict) and r.get("success")):
        raise RuntimeError(f"wire failed {src}.{sp}->{tgt}.{tp}: {r}")

# ---------- find existing components ----------
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
print("Treppenbasislinie:", line_id, "| Run slider:", run_slider)
sys.stdout.flush()

doc("solver", enabled=False)

g_divide = search_guid("Divide Curve")
g_cull   = search_guid("Cull Index")
g_decon  = search_guid("Deconstruct Point")
g_div    = search_guid("Division")
g_sub    = search_guid("Subtraction")
g_cpt    = search_guid("Construct Point")
g_box    = search_guid("Center Box")
print("GUIDs ok"); sys.stdout.flush()

X0, Y0 = 300, -700
sN   = add("Slider", X0, Y0,     "Stufenzahl", min=1, max=40, value=13, decimals=0)
sW   = add("Slider", X0, Y0+80,  "Trittbreite", min=400, max=3000, value=1200, decimals=0)
sT   = add("Slider", X0, Y0+160, "Stufenstaerke", min=10, max=200, value=40, decimals=0)
sTwo = add("Slider", X0, Y0+240, "const2", min=0, max=4, value=2, decimals=0)

dc2  = add(g_divide, X0+220, Y0, "Stufenpunkte")
cull = add(g_cull,   X0+380, Y0, "ohne Fusspunkt")
dpt  = add(g_decon,  X0+540, Y0, "Nosing XYZ")

dDep  = add(g_div, X0+380, Y0+140, "Tritt = Lauf/N")
dDep2 = add(g_div, X0+540, Y0+220, "Tritt/2")
subX  = add(g_sub, X0+700, Y0+80,  "X - Tritt/2")
dW2   = add(g_div, X0+540, Y0+300, "Breite/2")
subY  = add(g_sub, X0+700, Y0+160, "Y - Breite/2")
dT2   = add(g_div, X0+540, Y0+380, "Staerke/2")
subZ  = add(g_sub, X0+700, Y0+240, "Z - Staerke/2")

cpt = add(g_cpt, X0+880,  Y0+80, "Tritt-Mitte")
box = add(g_box, X0+1060, Y0+80, "Treppe")
sZero = add("Slider", X0+380, Y0+60, "idx0", min=0, max=10, value=0, decimals=0)
print("components done"); sys.stdout.flush()

connect(line_id, 0, dc2, 0)
connect(sN, 0, dc2, 1)
connect(dc2, 0, cull, 0)
connect(sZero, 0, cull, 1)
connect(cull, 0, dpt, 0)

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

connect(cpt, 0, box, 0)
connect(dDep, 0, box, 1)
connect(sW, 0, box, 2)
connect(sT, 0, box, 3)
print("wires done"); sys.stdout.flush()

doc("solver", enabled=True)
doc("recompute")
time.sleep(1)

st = inspect_("status")
bad = [c for c in st.get("components", []) if c.get("status") != "OK"]
print("STATUS bad:", [(c.get("nickname"), c.get("status"), c.get("message", "")[:80]) for c in bad])

out = inspect_("outputs", id=box)
print("Treppe outputs:", json.dumps(out)[:600])

canvas("preview", ids=json.dumps([box]), enabled=True)
canvas("zoom")
doc("capture_viewport", path=SHOT)
doc("save", path=GH_FILE)
print("DONE")
