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

"""Phase 14 — Musterkatalog in den Generator: 34 Fuellmuster statt 3 Stile.

Baut die Muster-Engine (patterns.py) als Python-3-Script-
Komponente ein und haengt die beiden bestehenden Stab-Zweige daran um:

    muster.Stab1 -> _frmI / _graftRail_I / _len_Fuell   (Profil "Fuellstab")
    muster.Stab2 -> _frmD / _graftRailD / _len_Diag     (Profil "Diagonal")

Neu dazu kommen zwei Materialzweige, die es im Modell noch nicht gab, weil
bisher alles ein Stab mit kg/m war:

    muster.Stahl -> Volumen * 7850 kg/m3   (Bleche, Flachstahl variabler
                                            Breite, tordierte Vierkantstaebe)
    muster.Holz  -> Volumen * Rohdichte    (Holzbloecke und -lamellen)

Die alte Erzeugerkette (Fuellstaebe / _diag*) bleibt in diesem Schritt stehen,
nur eben abgehaengt: erst wird der neue Pfad live geprueft, geloescht wird
danach (build_p14b.py). Reihenfolge bewusst so — die Rollbackpunkte
grasshopper/backup_pre_p14.gh und der GH-Snapshot "pre_p14" decken den Rest ab.
"""

import json
import os

import bh
import gh

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")

# --------------------------------------------------------------- Bestandsids
SHAT_UNTER = "5951c23f-c4b4-4bd5-b0ae-bd63d6023d82"  # Untergurt, je Feld
SHAT_HAND = "05b097b1-50f2-4581-83e3-aea7e6086141"   # Handlauf, je Feld
EDGE_N1 = "4692fe11-c2a6-40fe-a86f-7bcbb134f43e"     # Normale nach aussen
SEL_DIMX_I = "17cd2ad6-9e7b-491b-a947-d2b62fd99d34"  # Stabbreite Fuellprofil
SEED = "7ee4f409-a64e-4b18-9c82-51fe7f6e1661"
AUSLAGE = "acfd7378-1944-464d-89ab-06fe3d38baeb"

FRM_I = "d584c55e-6cdf-4888-bb48-fc794df66d9f"
GRAFT_RAIL_I = "ec33966b-2113-4060-a82a-30681bff7436"
LEN_FUELL = "bda989f8-7a7c-44b2-ae10-465114189e7b"
FRM_D = "de09e64d-5ec0-4732-9c77-296afc577681"
GRAFT_RAIL_D = "8bc55044-db05-4079-b6ce-f3d2bc9a005c"
LEN_DIAG = "c7461fd6-0057-49c1-bdc2-cbb115e471d7"

KG_GESAMT_ALL = "9577c736-81b9-4009-ad63-d9096e0fd1e3"
CA_T = "fe1b4065-ad55-403b-8221-99ed7a25f26c"        # "GESAMT: " + Wert

# Komponenten-GUIDs hart gepinnt statt ueber bh.find(): "Volume" gibt es auf
# dieser Installation dreimal (Kangaroo2-Goal, Surface-Analyse, Dendro) und die
# Namenssuche liefert das Kangaroo-Goal zuerst — das haette lautlos ein Ziel
# statt einer Volumenmessung eingebaut.
GUID_MERGE = "3cadddef-1e2b-4c09-9390-0e8f78f7609f"      # Sets > Tree
GUID_FLATTEN = "f80cfe18-9510-4b89-8301-8e58faf423bb"    # Sets > Tree
GUID_ADD = "a0d62394-a118-422d-abb3-6af115c75b25"        # Maths > Operators
GUID_VOLUME = "7c0523e8-79c9-45a2-8777-cf0d46bc5432"     # Surface > Analysis

MUSTER_X, MUSTER_Y = -380, 1450
COL_X, COL_Y = -900, 2150      # Fortsetzung der Regler-Spalte aus Phase 10
BOM_X, BOM_Y = 1000, 3050      # freies Band quer ueber die Leinwand

# Regler: (Nickname, min, max, default, Nachkommastellen, Ziel-Eingang)
# "Muster-Rapport-Faktor" ist ein dimensionsloser Multiplikator auf den nominellen
# Rapport des Musters (patterns.py: rap = D['rap'] * Dc): 1.00 = nominell,
# groesser = breiterer Rapport = WENIGER Elemente. Der Script-Eingang heisst aus
# Verdrahtungsgruenden weiterhin "Dc" — nur der Nickname wurde korrigiert, weil
# "Dichte" die Wirkrichtung genau verkehrt herum suggerierte.
SLIDERS = [
    ("Muster", 0, 33, 30, 0, "M"),
    ("Muster-Rapport-Faktor", 0.60, 1.80, 1.00, 2, "Dc"),
    ("Oeffnung-max", 60, 140, 120, 0, "Gmax"),
    ("Holz-Dicke", 15, 45, 30, 0, "Hd"),
    ("Holz-Luft", 0, 20, 8, 0, "Hl"),
    ("Holz-Auslage", 0, 40, 12, 0, "Ho"),
    ("Blech-Dicke", 2, 10, 4, 0, "Bd"),
    ("Blech-Steg", 10, 60, 25, 0, "Bs"),
    ("Blech-Rand", 10, 60, 30, 0, "Br"),
    ("Flach-Dicke", 4, 15, 8, 0, "Fd"),
    ("Vierkant-Breite", 10, 30, 16, 0, "Vw"),
]

IN_SPEC = [
    ("Lo", "Curve", "list"), ("Hi", "Curve", "list"),
    ("M", "int", "item"), ("Dc", "double", "item"), ("S", "int", "item"),
    ("N", "Vector3d", "item"), ("A", "double", "item"),
    ("Gmax", "double", "item"), ("Bw", "double", "item"),
    ("Hd", "double", "item"), ("Hl", "double", "item"), ("Ho", "double", "item"),
    ("Bd", "double", "item"), ("Bs", "double", "item"), ("Br", "double", "item"),
    ("Fd", "double", "item"), ("Vw", "double", "item"),
]
OUT_SPEC = ["Stab1", "Stab2", "Stahl", "Holz", "Info"]


def load_state():
    with open(STATE, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(st):
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1, ensure_ascii=False)


def build_engine():
    """Muster-Engine anlegen und bestuecken."""
    src = os.path.join(HERE, "patterns.py")
    with open(src, encoding="utf-8") as fh:
        code = fh.read()
    cid = bh.addf("Python 3 Script", MUSTER_X, MUSTER_Y, "muster")
    gh.script(
        "configure",
        id=cid,
        inputs=json.dumps([{"name": n, "type": t, "access": a}
                           for n, t, a in IN_SPEC]),
        outputs=json.dumps([{"name": n, "type": "Generic Data", "access": "list"}
                            for n in OUT_SPEC]),
        code=code,
    )
    # configure kann waehrend des Python-Bootstraps in einen Timeout laufen und
    # TROTZDEM angewandt worden sein — deshalb wird die Komponente zurueckgelesen
    # statt der Antwort geglaubt (gleiche Falle wie bei bh.catalog).
    info = gh.script("info", id=cid)
    have_in = {p.get("name") for p in info.get("inputs", [])}
    have_out = {p.get("name") for p in info.get("outputs", [])}
    missing_in = [n for n, _, _ in IN_SPEC if n not in have_in]
    missing_out = [n for n in OUT_SPEC if n not in have_out]
    assert not missing_in, f"muster: Eingaenge fehlen {missing_in} (da: {sorted(have_in)})"
    assert not missing_out, f"muster: Ausgaenge fehlen {missing_out} (da: {sorted(have_out)})"
    print(f"  muster {cid} angelegt: {len(have_in)} IN / {len(have_out)} OUT")
    return cid


def build_sliders(cid):
    ids = {}
    y = COL_Y
    for nick, mn, mx, val, dec, port in SLIDERS:
        sid = bh.slider(nick, mn, mx, val, dec, COL_X, y)
        bh.wire(sid, 0, cid, port)
        ids[nick] = sid
        y += 52
    print(f"  {len(ids)} Regler angelegt und verdrahtet")
    return ids, y


def wire_engine(cid):
    bh.wire(SHAT_UNTER, "Segments", cid, "Lo")
    bh.wire(SHAT_HAND, "Segments", cid, "Hi")
    bh.wire(EDGE_N1, 0, cid, "N")
    bh.wire(SEED, 0, cid, "S")
    bh.wire(AUSLAGE, 0, cid, "A")
    bh.wire(SEL_DIMX_I, "Item", cid, "Bw")
    print("  Feld- und Parametereingaenge verdrahtet")


def repoint(cid):
    """Beide Stabzweige auf die Engine umhaengen.

    Rahmen UND Schiene muessen umgehaengt werden: _frmI hing bisher an der
    ungefilterten Line-SDL-Liste, waehrend _graftRail_I an der gefilterten hing.
    Solange der Cull nichts wegwarf, passten die Anzahlen zufaellig zusammen —
    mit den Mustern tun sie das nicht mehr. 1:1 wird erzwungen, indem beide
    Seiten aus derselben Liste kommen.
    """
    for tgt, port, out in (
        (FRM_I, "Curve", "Stab1"), (GRAFT_RAIL_I, "Tree", "Stab1"),
        (LEN_FUELL, "Curve", "Stab1"),
        (FRM_D, "Curve", "Stab2"), (GRAFT_RAIL_D, "Tree", "Stab2"),
        (LEN_DIAG, "Curve", "Stab2"),
    ):
        bh.clear_input(tgt, port)
        bh.wire(cid, out, tgt, port)
    print("  Stab1/Stab2 auf Rahmen, Schienen und Laengen umgehaengt")


def mass_branch(cid, out_name, label, x, y, rho_src):
    """Volumen -> Masse fuer einen Solid-Kanal.

    Der Null-Wachhund ist Pflicht: Mass Addition ueber eine LEERE Liste liefert
    null, und GH rechnet mit null als neutralem Element weiter — ein
    abgewaehltes Muster wuerde sonst 1 m3 Stahl in die Stueckliste schreiben,
    ohne dass irgendeine Komponente eine Warnung zeigt. Konstante 0 dazu mergen
    und flatten (Merge legt jeden Eingang auf einen eigenen Zweig, Mass Addition
    summiert je Zweig -> ohne Flatten gaebe es doppelte Zeilen).
    """
    vol = bh.add(GUID_VOLUME, x, y, f"_vol{label}")
    bh.wire(cid, out_name, vol, "Geometry")
    zero = bh.const(0, x, y + 60, f"_null{label}")
    mrg = bh.add(GUID_MERGE, x + 150, y, f"_volOr0{label}")
    bh.wire(zero, 0, mrg, 0)
    bh.wire(vol, "Volume", mrg, 1)
    flat = bh.add(GUID_FLATTEN, x + 300, y, f"_volFlat{label}")
    bh.wire(mrg, 0, flat, 0)
    summ = bh.add("MassAddition", x + 450, y, f"_sumVol{label}")
    bh.wire(flat, 0, summ, 0)
    mm3 = bh.const(1e9, x + 450, y + 60, f"_mm3{label}")   # mm3 -> m3
    m3 = bh.add("Division", x + 600, y, f"_m3{label}")
    bh.wire(summ, "Result", m3, "A")
    bh.wire(mm3, 0, m3, "B")
    kg = bh.add("Multiplication", x + 750, y, f"kg_{label}")
    bh.wire(m3, "Result", kg, "A")
    bh.wire(rho_src, 0, kg, "B")
    print(f"  Massezweig {label}: Volumen -> m3 -> kg")
    return kg


def build_masses(cid, col_y):
    rho_stahl = bh.const(7850, BOM_X - 200, BOM_Y + 60, "_rhoStahl")
    rho_holz = bh.slider("Holz-Rohdichte", 350, 900, 600, 0, COL_X, col_y)
    kg_st = mass_branch(cid, "Stahl", "Stahl", BOM_X, BOM_Y, rho_stahl)
    kg_hz = mass_branch(cid, "Holz", "Holz", BOM_X, BOM_Y + 260, rho_holz)

    add_sh = bh.add(GUID_ADD, BOM_X + 950, BOM_Y + 130, "_addSH")
    bh.wire(kg_st, "Result", add_sh, "A")
    bh.wire(kg_hz, "Result", add_sh, "B")
    total = bh.add(GUID_ADD, BOM_X + 1100, BOM_Y + 130, "kg_GESAMT_MAT")
    bh.wire(KG_GESAMT_ALL, "Result", total, "A")
    bh.wire(add_sh, "Result", total, "B")
    # Die Stuecklisten-Zeile "GESAMT" muss jetzt die Materialsumme zeigen,
    # sonst faellt Holz/Blech lautlos aus der Kalkulation.
    bh.clear_input(CA_T, "Fragment B")
    bh.wire(total, "Result", CA_T, "Fragment B")
    print("  kg_GESAMT_MAT = kg_GESAMT_ALL + Stahl-Solids + Holz")
    return dict(kg_stahl=kg_st, kg_holz=kg_hz, rho_holz=rho_holz,
                add_sh=add_sh, total=total)


def info_panel(cid):
    pid = bh.add("Panel", MUSTER_X + 260, MUSTER_Y, "Muster_Info")
    bh.wire(cid, "Info", pid, 0)
    return pid


def main():
    st = load_state()
    gh.doc("solver", enabled="false")
    try:
        cid = build_engine()
        sliders, col_y = build_sliders(cid)
        wire_engine(cid)
        repoint(cid)
        masses = build_masses(cid, col_y)
        pid = info_panel(cid)
    finally:
        gh.doc("solver", enabled="true")
    gh.doc("recompute")

    st["p14"] = dict(engine=cid, info=pid, sliders=sliders,
                     **{k: v for k, v in masses.items()})
    save_state(st)
    print("state.json aktualisiert")

    status = gh.inspect("status")
    s = status.get("summary", {})
    bad = [c for c in status.get("components", [])
           if c.get("status") in ("ERROR", "WARNING") and c.get("name") != "Load"]
    print(f"STATUS: {s}")
    for c in bad:
        print(f"  !! {c.get('nickname') or c.get('name')}: {c.get('message')}")


if __name__ == "__main__":
    main()
