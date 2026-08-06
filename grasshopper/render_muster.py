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
"""Alle 34 Muster als GERENDERTE Praesentationsbilder (Raytraced, Material, Sonne).

    python render_muster.py                     # alle 34
    python render_muster.py --only 30           # nur ein Muster (Kameratest)
    python render_muster.py --only 0,11,30      # Auswahl
    python render_muster.py --passes 60         # Rechenbudget je Bild
    python render_muster.py --no-treppe         # Treppe ausblenden

Ausgabe: `reference/renders_muster/m<NN>_<key>.png`.

Ausdruecklich NICHT fuer Katalogblaetter — das hier sind Ansichts- und
Pruefbilder in Dreiviertel-Perspektive.

Ablauf je Muster — die Reihenfolge ist nicht beliebig:
  1. Muster stellen und auf die Engine warten (`select`, siehe unten),
  2. nach Rhino BACKEN, und zwar ALLE VIER Ausgabekanaele der Engine — die zwei
     gesweepten Stabkanaele und die zwei Solid-Kanaele. Grasshopper-Preview
     erreicht den Renderer nicht, ungebackene Geometrie ergibt ein leeres Bild,
  3. Material zuweisen (die gebackenen Objekte sind je Durchlauf neu),
  4. Raytraced einschalten, `render` warten lassen,
  5. `capture_viewport` — `rhino_render action='render'` schreibt KEINE Datei,
     es akkumuliert nur Passes. Das Bild entsteht erst beim Capture,
  6. zurueck auf Shaded und alles Gebackene wieder loeschen.

Kamera fest, bewusst NICHT zoom-to-fit: die 34 Bilder muessen untereinander
vergleichbar bleiben (gleiche Regel wie `render_styles.py` und
`katalog/capture_muster.py`).

Am Ende wird der Zustand wiederhergestellt: Muster zurueck auf 30, Treppen-Preview
an, Anzeige auf Shaded, Dokument ohne gebackene Objekte, Hilfsebenen entfernt.
Muster und Treppen-Preview werden dabei zurueckgelesen und geprueft, nicht nur
gesetzt. Die .gh-Datei wird NICHT gespeichert.

`render_styles.py` faehrt inzwischen ebenfalls den `Muster`-Regler (0..33) und backt
alle vier Kanaele; Katalog, Backliste, `select` und `bake_param` importiert es von
hier statt sie zu kopieren. Es bleibt daneben bestehen, weil es etwas anderes macht:
EIN Bild in seiner eigenen Kamera, waehrend hier die Serie aller 34 entsteht.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gh  # noqa: E402

REPO = os.path.dirname(HERE)
OUT_DEFAULT = os.path.join(REPO, "reference", "renders_muster")

st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))
MID = st["p14"]["engine"]
SLIDER = st["p14"]["sliders"]["Muster"]
FINAL = st["p10"]["final"]

TREPPE_PREVIEW = "e3fc6b31-82cf-47bc-9aa0-653615722c72"  # Center Box "Treppe"
REFERENZ_MUSTER = 30                             # Vertical Bars, die Ausgangslage

STEEL = [
    "Handlauf_Volumen",
    "Untergurt_Volumen",
    "Posten_Volumen",
    "Fuellstab_Volumen",
    "Diagonal_Volumen",
    "Montage_Platten",
    "Montage_Bolzen",
]
TREAD = ["Treppe"]

# Die Engine hat VIER Ausgabekanaele, nicht zwei. Neben den beiden gesweepten
# Stabkanaelen (a -> Fuellstab, b -> Diagonal, beide oben im p10-Baum) faellt
# Geometrie auch als SOLID an: `plate`/`twisted` schreiben nach `st`, `block`
# nach `hz`. Diese beiden haengen an eigenen Brep-Parametern aus Phase 14.
#
# Sie fehlten hier zuerst, weil die Liste aus `render_styles.py` stammt und
# damit aus der Zeit VOR der Muster-Engine. Folge: neun Muster (01 Staggered
# Panels, 05 Wide Slats, 08 Diamond Lattice, 10 Segmented Panels, 11 Ellipse
# Sheet, 14 Grain Sheet, 19 Width Wave, 20 Alternating Bars, 31 Twisted Bars)
# wurden ohne jede Fuellung gerendert — Handlauf,
# Untergurt und Posten standen da, das Muster selbst fehlte. Nichts hat
# gewarnt: backen, rendern und aufraeumen liefen sauber durch, die Bilder sahen
# nur unauffaellig leer aus. Deshalb steht unten zusaetzlich `_pruefe_solids`.
SOLID = {"Stahl": st["p14"]["blech_param"], "Holz": st["p14"]["holz_param"]}

# Dreiviertelansicht: staerker angewinkelt als der Aufriss des Vergleichs-PDF,
# damit Tiefe, Auslage und vorgesetzte Baender ueberhaupt lesbar werden.
CAM = dict(location="7025,4419,3238", target="1906,-700,1700", lens=44)
PX = (1600, 1000)
PASSES = 120
DWELL = 12.0   # Mindestverweildauer im Raytraced-Modus, siehe shoot()

LAYERS = (("Stahl", "#3A3F44"), ("Treppe", "#8A5A2B"), ("Holz", "#8A5A2B"))

# Was die Engine selbst meldet: Check[3] lautet
#   'Staebe %d/%d, Stahl-Solids %d, Holz-Solids %d'
_SOLID_RE = re.compile(r"Stahl-Solids (\d+), Holz-Solids (\d+)")


def _keys():
    """Die 34 Muster-Keys aus der Engine-Quelle — Dateinamen sollen sprechen.

    Gelesen statt dupliziert: eine zweite Liste haette genau eine Aufgabe, naemlich
    irgendwann von der ersten abzuweichen.
    """
    src = open(os.path.join(HERE, "patterns.py"), encoding="utf-8").read()
    ks = re.findall(r"dict\(key='([a-z0-9-]+)', name='([^']+)'", src)
    assert len(ks) == 34, "patterns.py liefert %d Designs, erwartet 34" % len(ks)
    return ks


KEYS = _keys()


def render(action, timeout=180, **kw):
    return gh.call("rhino_render", {"action": action, **kw}, timeout=timeout)


def scene(action, **kw):
    return gh.call("rhino_scene", {"action": action, **kw})


def outs(cid):
    return {o.get("name"): o for o in gh.inspect("outputs", id=cid).get("outputs", [])}


def select(m):
    """Muster m stellen und warten, bis die Engine ihn auch WIRKLICH rechnet.

    Der Regler wird zurueckgelesen (ueber `get`, nicht `info` — `info` meldet fuer
    Slider still None) und danach so lange nachgerechnet, bis die Engine selbst den
    erwarteten Index meldet. Ohne diesen Riegel rendert man das vorige Muster: die
    Ausgaben sind direkt nach `recompute` gelegentlich noch der alte Stand, und das
    faellt bei 34 plausibel aussehenden Bildern niemandem auf.
    Uebernommen aus `katalog/capture_muster.py` / `regress_p14.py`.
    """
    gh.canvas("set", id=SLIDER, value=str(m))
    got = gh.canvas("get", id=SLIDER).get("value")
    assert got is not None and abs(float(got) - m) < 1e-6, \
        "Regler steht auf %r, erwartet %d" % (got, m)
    chk = []
    for _ in range(5):
        gh.doc("recompute")
        chk = outs(MID).get("Check", {}).get("preview") or []
        if chk and chk[0].startswith("Muster %02d " % m):
            return chk
        time.sleep(0.4)
    raise AssertionError("Engine meldet %r, erwartet Muster %02d" % (chk[:1], m))


def clear_baked():
    objs = scene("objects", limit=5000).get("objects", [])
    if objs:
        scene("delete", ids=json.dumps([o["id"] for o in objs]))
    return len(objs)


def setup_scene():
    """Material, Umgebung, Kamera — einmal je Lauf, nicht je Bild.

    Die gebackenen Objekte sind je Muster neu und brauchen die Zuweisung erneut
    (`apply_materials`), die Materialdefinitionen selbst aber nicht.
    """
    for name, color in LAYERS:
        scene("layer_create", name=name, color=color)
    render("material_create", name="Stahl_anthrazit", type="Metal",
           color="#4A5056", roughness=0.32, metallic=1.0)
    render("material_create", name="Eiche", type="Plastic",
           color="#B9884E", roughness=0.55)
    render("ground", groundEnabled="true", groundAltitude=0,
           material="Stahl_anthrazit", shadowOnly="true")
    render("skylight", skylightEnabled="true", intensity=1.0)
    render("sun", sunEnabled="true", sunAltitude=48, azimuth=225, intensity=1.1)
    render("settings", style="gradient", colorTop="#7C8AA0", colorBottom="#D8DDE4")
    render("camera", view="Perspective", **CAM)


# `gh_canvas action='bake'` kann die beiden Solid-Kanaele nicht backen: sie haengen
# an freistehenden Brep-Parametern, und die Bake-Aktion verlangt eine Komponente mit
# Ausgangsparametern ("Component has no bakeable outputs" — obwohl `gh_inspect
# action='outputs'` dieselben 64 Breps anstandslos meldet). Ein Selektor fuer einen
# einzelnen Ausgang existiert nicht, `bake` nimmt nur id/layer/name.
#
# Die Engine selbst zu backen waere der naheliegende Ausweg und ist trotzdem
# falsch: sie wuerde alle vier Kanaele auf EINE Ebene legen, womit die Holz-Solids
# das Stahlmaterial bekaemen — bei Staggered Panels, Wide Slats, Diamond Lattice
# und Segmented Panels genau das
# sichtbare Merkmal des Musters.
#
# Also derselbe Weg um die Tool-Oberflaeche herum, den `gh.preview_is_on` benutzt:
# ein Rhino-Kommandomakro startet IronPython, dort liegt Grasshoppers Objektmodell
# offen. ACHTUNG: das ist IronPython 2 und lehnt Nicht-ASCII-Quelltext mit einem
# MODALEN Dialog ab, der Rhino UND die Bruecke einfriert, bis ihn jemand wegklickt.
# Deshalb wird die Sonde als ASCII geschrieben — ein Sonderzeichen scheitert dann
# hier, statt Rhino zu blockieren.
_BAKE_PROBE = '''import json, System, clr
clr.AddReference("Grasshopper")
clr.AddReference("RhinoCommon")
clr.AddReference("System.Drawing")
import Grasshopper
import Rhino
import System.Drawing
out = {}
try:
    ghdoc = Grasshopper.Instances.ActiveCanvas.Document
    obj = ghdoc.FindObject(System.Guid("%(guid)s"), True) if ghdoc else None
    if obj is None:
        out["error"] = "param %(guid)s not found in the active document"
    else:
        rdoc = Rhino.RhinoDoc.ActiveDoc
        idx = rdoc.Layers.FindByFullPath("%(layer)s", -1)
        if idx < 0:
            idx = rdoc.Layers.Add("%(layer)s", System.Drawing.Color.Gray)
        att = Rhino.DocObjects.ObjectAttributes()
        att.LayerIndex = idx
        n = 0
        for goo in obj.VolatileData.AllData(True):
            geo = getattr(goo, "Value", None)
            if isinstance(geo, Rhino.Geometry.Brep):
                if rdoc.Objects.AddBrep(geo, att) != System.Guid.Empty:
                    n = n + 1
        out["count"] = n
except Exception as e:
    out["error"] = repr(e)
f = open("%(out)s", "w")
f.write(json.dumps(out))
f.close()
'''


def bake_param(param_id, layer):
    """Breps eines freistehenden Brep-Parameters auf `layer` ins Rhino-Dokument.

    Liefert die Zahl der erzeugten Objekte. Ein leerer Parameter ist gueltig und
    ergibt 0 — die meisten Muster bauen ueberhaupt keine Solids.
    """
    tmp = tempfile.mkdtemp(prefix="gh_bake_")
    try:
        probe = os.path.join(tmp, "probe.py").replace("\\", "/")
        out = os.path.join(tmp, "out.json").replace("\\", "/")
        with open(probe, "w", encoding="ascii") as f:
            f.write(_BAKE_PROBE % {"guid": param_id, "layer": layer, "out": out})
        r = gh.call("rhino_scene",
                    {"action": "script", "cmd": '_-RunPythonScript ("%s")' % probe})
        if not r.get("success"):
            raise RuntimeError("RunPythonScript fehlgeschlagen: %r" % (r,))
        if not os.path.exists(out):
            raise RuntimeError("Bake-Sonde hat nichts geschrieben (%s)" % param_id)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        if "count" not in data:
            raise RuntimeError("Bake-Sonde fehlgeschlagen fuer %s: %s"
                               % (param_id, data.get("error", data)))
        return data["count"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _pruefe_solids(chk, gebacken):
    """Abgleich gegen die Engine: was sie gebaut hat, muss auch gebacken sein.

    Der Riegel existiert, weil das Gegenteil GRUEN durchlaeuft. Fehlt ein Kanal in
    der Backliste, backt das Skript brav die uebrigen, rendert, raeumt auf und
    meldet Erfolg — nur ohne Fuellung im Bild. Ein Muster, dessen Geometrie
    vollstaendig in einem Solid-Kanal liegt (Width Wave, Alternating Bars,
    Ellipse Sheet, Grain Sheet, Twisted Bars), sieht dann aus wie ein Gelaender
    ohne Fuellstaebe, und
    das faellt bei 34 Bildern nur auf, wenn jemand genau hinsieht.
    Quelle der Sollzahlen ist die Engine selbst, nicht eine zweite Liste hier.
    """
    m = _SOLID_RE.search(" ".join(chk))
    if not m:      # aeltere Engine-Fassung ohne die Zeile — dann eben ungeprueft
        return
    for kanal, soll in (("Stahl", int(m.group(1))), ("Holz", int(m.group(2)))):
        ist = gebacken.get(kanal, 0)
        assert ist >= soll, (
            "Engine meldet %d %s-Solids, gebacken wurden %d — der Kanal erreicht "
            "den Renderer nicht, das Bild waere ohne Fuellung" % (soll, kanal, ist))


def bake_and_dress(with_treppe, chk=()):
    """Backen und Material zuweisen. Liefert die Objektzahl je Ebene."""
    groups = [("Stahl", STEEL)] + ([("Treppe", TREAD)] if with_treppe else [])
    for layer, nicks in groups:
        for nick in nicks:
            r = gh.canvas("bake", id=FINAL[nick], layer=layer)
            assert r.get("success"), "bake %s fehlgeschlagen: %r" % (nick, r)

    # Die Solid-Kanaele sind je nach Muster leer — die meisten Designs bauen
    # ausschliesslich Staebe. Ein leerer Parameter ist deshalb kein Fehler; ob
    # etwas fehlt, entscheidet der Abgleich mit der Engine weiter unten.
    solids = {layer: bake_param(cid, layer) for layer, cid in SOLID.items()}
    _pruefe_solids(chk, solids)

    ids = {}
    for o in scene("objects", limit=5000).get("objects", []):
        ids.setdefault(o.get("layer"), []).append(o["id"])
    assert ids.get("Stahl"), "nichts auf Ebene Stahl gebacken — leeres Bild droht"

    render("material_apply", ids=json.dumps(ids["Stahl"]), material="Stahl_anthrazit")
    for layer in ("Treppe", "Holz"):     # beide in Holzoptik
        if ids.get(layer):
            render("material_apply", ids=json.dumps(ids[layer]), material="Eiche")
    return {k: len(v) for k, v in ids.items()}


def shoot(path, passes, dwell=DWELL):
    """Raytraced rechnen lassen und das Ergebnis abgreifen.

    Zwei Riegel, beide notwendig:
      * `render` wartet nur auf Passes und schreibt SELBST KEINE Datei — das Bild
        entsteht erst durch `capture_viewport`,
      * der Passzaehler allein ist kein Beweis, dass das Bild fertig ist.
        Unmittelbar nach dem Umschalten auf Raytraced zeigt Rhino die Geometrie
        noch mit Standardmaterial (weiss statt Anthrazit) und der Zaehler laeuft
        in dieser Phase in Sekunden hoch. Ein Kameratest hat genau so ein weisses
        Bild produziert. Deshalb zusaetzlich eine Mindestverweildauer im
        Raytraced-Modus, bevor abgegriffen wird.
    """
    # Immer erst ALLES deselektieren: eine aktive Selektion (Bake-Reste oder
    # Nutzer-Klicks in der offenen Rhino-Session) rendert sonst als rote
    # Selektionskanten bzw. Gumball mit ins Bild — so sind das alte m07
    # (Selektionskanten) und m03 (Gumball) entstanden.
    scene("deselect")
    render("display", view="Perspective", mode="Raytraced")
    render("camera", view="Perspective", **CAM)
    t0 = time.time()
    # Der HTTP-Timeout muss ueber dem Tool-Timeout liegen, sonst gibt urlopen auf,
    # waehrend Rhino noch rechnet.
    budget = passes * 8 + 120
    r = render("render", view="Perspective", wait=passes, timeout=budget)
    while time.time() - t0 < dwell:
        time.sleep(0.5)
        r = render("render", view="Perspective", wait=passes, timeout=budget)
    got = gh.doc("capture_viewport", view="Perspective",
                 width=PX[0], height=PX[1], path=path)
    render("display", view="Perspective", mode="Shaded")
    assert got.get("filePath"), "keine Aufnahme geschrieben: %r" % got
    pas = r.get("currentPass", 0)
    assert pas >= passes, "nur %s Passes statt %d: %r" % (pas, passes, r)
    return pas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="Kommaliste von Muster-Indizes")
    ap.add_argument("--passes", type=int, default=PASSES)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--no-treppe", action="store_true")
    ap.add_argument("--cam", default="", help="Kameratest: 'x,y,z|x,y,z|lens'")
    a = ap.parse_args()

    if a.cam:  # nur zum Einrichten der Ansicht, der Lauf selbst nutzt CAM
        loc, tgt, lens = a.cam.split("|")
        CAM.update(location=loc, target=tgt, lens=float(lens))

    todo = ([int(x) for x in a.only.split(",")] if a.only else list(range(34)))
    assert all(0 <= m < 34 for m in todo), "Muster-Index ausserhalb 0..33"
    with_treppe = not a.no_treppe
    os.makedirs(a.out, exist_ok=True)

    pre = scene("objects", limit=5000).get("objects", [])
    assert not pre, ("Das Rhino-Dokument enthaelt bereits %d Objekte. Abbruch: dieses "
                     "Skript loescht am Ende alles Gebackene und wuerde die mitnehmen."
                     % len(pre))

    setup_scene()
    gh.canvas("preview", id=TREPPE_PREVIEW, enabled="true" if with_treppe else "false")

    # GH-Previews der Final-Komponenten fuer die Dauer des Renderns AUS: das
    # Bild entsteht aus den GEBACKENEN Objekten mit Material — eine sichtbare
    # Grasshopper-Preview legt sich in Shaded UND Raytraced als rotes Duplikat
    # darueber (so entstand der rot ueberzogene 11:36-Lauf vom 05.08.).
    # Vorher-Zustand wird je Komponente NACHGELESEN (gh.preview_is_on, die
    # preview-Aktion ist schreib-only) und im finally exakt wiederhergestellt —
    # die Vergleichs-Captures fotografieren naemlich genau diese Previews und
    # brauchen sie AN.
    preview_ids = list(FINAL.values()) + list(SOLID.values())
    preview_war = {}
    for pid in preview_ids:
        try:
            preview_war[pid] = gh.preview_is_on(pid)
        except RuntimeError:
            preview_war[pid] = None      # kein Preview-Objekt — nicht anfassen
        if preview_war[pid]:
            gh.canvas("preview", id=pid, enabled="false")

    t0 = time.time()
    done = []
    try:
        for m in todo:
            t = time.time()
            key, name = KEYS[m]
            chk = select(m)
            counts = bake_and_dress(with_treppe, chk)
            path = os.path.join(a.out, "m%02d_%s.png" % (m, key))
            pas = shoot(path.replace("\\", "/"), a.passes)
            clear_baked()
            done.append(path)
            print("%2d  %-12s %-28s %6.1fs  %4d Passes  %s" % (
                m, key, (chk[0] if chk else "?")[:28], time.time() - t, pas, counts),
                flush=True)
    finally:
        # Ausgangslage — auch wenn oben etwas geplatzt ist.
        render("display", view="Perspective", mode="Shaded")
        clear_baked()
        for layer, _ in LAYERS:
            scene("layer_delete", name=layer)
        select(REFERENZ_MUSTER)
        for pid, war in preview_war.items():
            if war:
                gh.canvas("preview", id=pid, enabled="true")
        gh.canvas("preview", id=TREPPE_PREVIEW, enabled="true")
        # Zurueckgelesen, nicht geglaubt. `preview` ist im MCP eine reine
        # Schreib-Aktion; ihre Antwort echot nur das mitgegebene Argument und
        # beweist nichts. Der einzige Beleg, dass die Treppe wieder sichtbar ist,
        # kommt aus dem Grasshopper-Objekt selbst (siehe gh.preview_is_on).
        # Ohne diesen Riegel war "Treppen-Preview an" die einzige Zusage des
        # Wiederherstellens, die niemand nachpruefen konnte.
        assert gh.preview_is_on(TREPPE_PREVIEW), \
            "Treppen-Preview blieb aus - das Dokument steht NICHT wie vorgefunden"

    print("\n%d Bilder in %.0fs -> %s" % (len(done), time.time() - t0, a.out))
    print("Muster zurueck auf %d, Treppen-Preview an (nachgelesen), Anzeige Shaded, "
          "Dokument leer. Die .gh wurde NICHT gespeichert." % REFERENZ_MUSTER)


if __name__ == "__main__":
    main()
