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

# -*- coding: utf-8 -*-
"""Bake + render EIN Muster (0..33) als Praesentationsbild.

    python render_styles.py <Muster 0..33> [out.png]
    python render_styles.py --help          # Liste aller 34 Muster

Grasshopper-Preview erreicht den Renderer nicht. Deshalb wird je Lauf nach Rhino
gebacken, gerendert und danach alles Gebackene wieder geloescht — das Rhino-
Dokument bleibt so leer, wie es vorgefunden wurde. Material, Boden, Sonne und
Kamera werden jedes Mal neu gesetzt, damit die Bilder untereinander vergleichbar
bleiben. Die Kamera ist bewusst FEST und NICHT zoom-to-fit.

Frueher fuhr dieses Skript den Regler `Fuellung-Stil` (0/1/2). Den gibt es seit
Phase 14 nicht mehr; die Fuellung waehlt jetzt `Muster` (0..33). Das Skript
bedient nun diesen Regler.

Verhaeltnis zu `render_muster.py`: dort entsteht die vollstaendige Serie fuer
`reference/renders_muster/` (Dreiviertel-Perspektive, eigene Kamera). Hier bleibt es
bei EINEM Bild in der urspruenglichen Ansicht dieses Skripts. Alles, was den
Musterkatalog beschreibt oder die Engine bedient, wird von dort IMPORTIERT und
nicht kopiert: genau eine zweite, mitgeschleppte Liste hat neun Bilder ohne
Fuellung produziert (HANDOFF.md §6b).

ACHTUNG: faehrt das LIVE-Dokument ueber die MCP-Bruecke.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gh  # noqa: E402

# Eine einzige Quelle fuer Katalog, Backliste und Engine-Bedienung:
#   KEYS          - die 34 (key, name) aus patterns.py, gelesen statt dupliziert
#   STEEL/TREAD   - die Nicknames der gesweepten Kanaele aus state.json p10.final
#   FINAL         - Nickname -> Komponenten-Id
#   SOLID         - die ZWEI Solid-Kanaele aus Phase 14 (Brep-Parameter, Stahl/Holz)
#   LAYERS        - Zielebenen inkl. `Holz`, ohne die die Solids kein Material bekaemen
#   select        - Regler setzen, zuruecklesen, nachrechnen (siehe unten)
#   bake_param    - Breps eines freistehenden Brep-Parameters backen
#   _pruefe_solids- Abgleich gegen die Engine: was sie meldet, muss gebacken sein
from render_muster import (  # noqa: E402
    KEYS,
    LAYERS,
    SOLID,
    STEEL,
    TREAD,
    FINAL,
    bake_param,
    select,
    _pruefe_solids,
)

PASSES = 120
CAM = dict(location="6000,7000,3350", target="1950,-450,1700", lens=44)


def render(action, timeout=180, **kw):
    # `timeout` ist der HTTP-Timeout, KEIN Tool-Argument: er muss ueber der
    # Rechenzeit des Renderers liegen, sonst gibt urlopen auf, waehrend Rhino
    # noch rechnet. Selbe Signatur wie in render_muster.py.
    return gh.call("rhino_render", {"action": action, **kw}, timeout=timeout)


def scene(action, **kw):
    return gh.call("rhino_scene", {"action": action, **kw})


def clear_scene():
    objs = scene("objects", limit=5000).get("objects", [])
    if objs:
        r = scene("delete", ids=json.dumps([o["id"] for o in objs]))
        print("  cleared", len(objs), "objects", r.get("success"))


def main(m, out):
    clear_scene()

    # Regler setzen, zuruecklesen (ueber `get` — `info` meldet fuer Slider still
    # None) und so lange nachrechnen, bis die Engine SELBST den Index meldet.
    # Ohne diesen Riegel rendert man das vorige Muster.
    chk = select(m)
    print("  engine:", chk[0] if chk else "?")

    # --- bake ---------------------------------------------------------------------
    for layer, color in LAYERS:
        scene("layer_create", name=layer, color=color)
    baked = {}
    for layer, nicks in (("Stahl", STEEL), ("Treppe", TREAD)):
        for nick in nicks:
            r = gh.canvas("bake", id=FINAL[nick], layer=layer)
            assert r.get("success"), f"bake {nick} failed: {r}"
            baked[nick] = r.get("count", r.get("ids"))

    # Die Engine hat VIER Ausgabekanaele, nicht zwei: neben den gesweepten
    # Stabkanaelen faellt Geometrie auch als Solid an (`plate`/`twisted` -> Stahl,
    # `block` -> Holz). Beide haengen an freistehenden Brep-Parametern, die
    # `gh_canvas action='bake'` nicht backen kann — daher bake_param(). Ein leerer
    # Kanal ist gueltig; ob etwas FEHLT, entscheidet der Abgleich mit der Engine.
    solids = {layer: bake_param(cid, layer) for layer, cid in SOLID.items()}
    _pruefe_solids(chk, solids)
    baked.update(("Solid_" + k, v) for k, v in solids.items())
    print("  baked:", json.dumps(baked)[:200])

    ids_by_layer = {name: [] for name, _ in LAYERS}
    for o in scene("objects", limit=5000).get("objects", []):
        ids_by_layer.setdefault(o.get("layer"), []).append(o["id"])
    print("  scene:", {k: len(v) for k, v in ids_by_layer.items()})
    assert ids_by_layer.get("Stahl"), "nichts auf Ebene Stahl gebacken — leeres Bild droht"

    # --- materials ----------------------------------------------------------------
    render(
        "material_create",
        name="Stahl_anthrazit",
        type="Metal",
        color="#4A5056",
        roughness=0.32,
        metallic=1.0,
    )
    render(
        "material_create", name="Eiche", type="Plastic", color="#B9884E", roughness=0.55
    )
    render(
        "material_apply",
        ids=json.dumps(ids_by_layer["Stahl"]),
        material="Stahl_anthrazit",
    )
    for layer in ("Treppe", "Holz"):  # beide in Holzoptik
        if ids_by_layer.get(layer):
            render("material_apply", ids=json.dumps(ids_by_layer[layer]), material="Eiche")

    # --- environment --------------------------------------------------------------
    render(
        "ground",
        groundEnabled="true",
        groundAltitude=0,
        material="Stahl_anthrazit",
        shadowOnly="true",
    )
    render("skylight", skylightEnabled="true", intensity=1.0)
    render("sun", sunEnabled="true", sunAltitude=48, azimuth=225, intensity=1.1)
    # Fixed camera, deliberately NOT zoom-to-fit: the variants must be framed
    # identically to be comparable, and the patterns change the bounding box.
    render("camera", view="Perspective", **CAM)

    # --- render -------------------------------------------------------------------
    # `rhino_render action='render'` does NOT write a file — it only waits for
    # raytraced passes. The image comes from capturing the Raytraced viewport once
    # enough passes have accumulated.
    render("settings", style="gradient", colorTop="#7C8AA0", colorBottom="#D8DDE4")
    render("display", view="Perspective", mode="Raytraced")
    r = render("render", view="Perspective", wait=PASSES, timeout=PASSES * 8 + 120)
    print("  passes:", json.dumps(r, ensure_ascii=False)[:220])
    print(
        " ",
        gh.doc(
            "capture_viewport", view="Perspective", width=1600, height=1000, path=out
        ),
    )
    render("display", view="Perspective", mode="Shaded")

    clear_scene()
    print("Muster %02d (%s) -> %s" % (m, KEYS[m][1], out))


def _usage(fehler=""):
    """Aufrufhilfe samt der 34 gueltigen Indizes.

    Die Namensliste kommt aus KEYS und damit aus `patterns.py` — hier
    steht keine zweite Tabelle, die irgendwann abweichen kann.
    """
    zeilen = []
    if fehler:
        zeilen += ["FEHLER: " + fehler, ""]
    zeilen += [
        "    python render_styles.py <Muster 0..%d> [out.png]" % (len(KEYS) - 1),
        "",
        "Gueltige Muster (Quelle: patterns.py, DESIGNS):",
    ]
    for i, (key, name) in enumerate(KEYS):
        zeilen.append("  %2d  %-16s %s" % (i, key, name))
    return "\n".join(zeilen)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(_usage("kein Muster-Index angegeben"))
        sys.exit(2)
    if sys.argv[1] in ("-h", "--help", "--list"):
        print(_usage())
        sys.exit(0)
    try:
        muster = int(sys.argv[1])
    except ValueError:
        print(_usage("%r ist keine ganze Zahl" % sys.argv[1]))
        sys.exit(2)
    if not 0 <= muster < len(KEYS):
        print(_usage("Muster %d liegt ausserhalb 0..%d" % (muster, len(KEYS) - 1)))
        sys.exit(2)

    ziel = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.path.join(HERE, "muster%02d_%s.png" % (muster, KEYS[muster][0]))
    )
    main(muster, ziel.replace("\\", "/"))
