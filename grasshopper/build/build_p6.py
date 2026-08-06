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

"""Phase 6 — switchable steel profiles per element (shop adaptation).

Builds the profile-selector macro three times (Handlauf / Posten / Fuellstab) per
Research/subsystem_topology.md §2. Each role gets a `*-Profil` integer slider that
indexes the catalog in profiles.py; the SAME index drives both the swept section and
the kg/m fed to the Phase-5 BOM, so geometry and mass can never disagree.

Refactor: this phase REPLACES the three hardcoded Phase-4 solids (pipeH/pipeF/ext and
their supports) and the three hardcoded Phase-5 density constants.

Gate polarity (settled): profiles.section_flags() emits 0=round / 1=rect|flat, so the
Stream Filter is wired Stream 0 = Circle, Stream 1 = Rectangle. Asserted at runtime.
"""
import gh
import bh
import json
import profiles

s = json.load(open('state.json'))
gh.doc('snapshot', name='pre_p6')
gh.doc('solver', enabled=False)

# --- Stream Filter port contract ----------------------------------------------------
# Runs BEFORE anything destructive: a failed assert here must not leave the canvas
# with the Phase-4 solids already deleted and nothing built to replace them.
_probe = bh.addf('Stream Filter', 900, 1380, '_probeSF')
_pin, _ = bh.io(_probe)
print('Stream Filter inputs:', [p.get('name') for p in _pin])
assert len(_pin) >= 3, f'Stream Filter needs gate + >=2 streams, saw {len(_pin)}'
assert 'gate' in (_pin[0].get('name', '') + _pin[0].get('nickname', '')).lower(), \
    f'Stream Filter input 0 is {_pin[0].get("name")!r}, expected the Gate — recheck wiring plan'
gh.canvas('delete', id=_probe)

# --- retire the Phase-4 hardcoded solids -------------------------------------------
# Terminal components (the BOM taps the centerlines, not these), so deleting is safe.
for key in ('pipeH', 'pipeF', 'ext', 'dom', 'pf', 'rect', 'uzE', 'postsolid'):
    if key in s:
        gh.canvas('delete', id=s.pop(key))
print('retired Phase-4 solids')

# --- shared constants (Catalog band) -----------------------------------------------
c2, cp5, cn5 = bh.const(2, 150, 1420, '_2'), bh.const(0.5, 150, 1460, '_0p5'), bh.const(-0.5, 150, 1500, '_-0p5')
ct0 = bh.const(0, 150, 1540, '_t0P')

ROLES = [
    # role,      slider nick,        rail id,        rail port,   volume nick,          BOM mult
    ('handrail', 'Handlauf-Profil',  s['handrail'], 'Geometry',  'Handlauf_Volumen',   s['kgH']),
    ('post',     'Posten-Profil',    s['posts'],    'Line',      'Posten_Volumen',     s['kgP']),
    ('infill',   'Fuellstab-Profil', s['fill'],     'Line',      'Fuellstab_Volumen',  s['kgF']),
]

new = {}
for i, (role, snick, rail, rport, vnick, kgmult) in enumerate(ROLES):
    y = 1420 + i * 180
    rows = profiles.ROLES[role]
    n = len(rows)
    tag = role[0].upper()
    print(f'--- {role} ({n} profiles) ---')

    # catalog: one script component per role, one LIST output per column
    cat = bh.catalog({'gate': profiles.section_flags(role),
                      'dimx': profiles.dx_list(role),
                      'dimy': profiles.dia_list(role),
                      'kgm':  profiles.kgm_list(role)}, 330, y, f'cat_{tag}')

    # selector slider: index must stay inside [0, n-1]
    sl = bh.slider(snick, 0, n - 1, 0, 0, 510, y + 160)

    sel = {}
    for j, (lbl, col) in enumerate((('Gate', 'gate'), ('DimX', 'dimx'),
                                    ('DimY', 'dimy'), ('Kg', 'kgm'))):
        li = bh.addf('List Item', 690, y + j * 40, f'_sel{lbl}_{tag}')
        bh.wire(cat, col, li, 'List')   # by NAME: output 0 is the script's `out`
        bh.wire(sl, 0, li, 'Index')
        sel[lbl] = li

    # section frame at the start of the centerline
    frm = bh.addf('Perp Frame', 1000, y, f'_frm{tag}')
    bh.wire(rail, rport, frm, 'Curve')
    bh.wire(ct0, 0, frm, 'Parameter')

    # round branch: circle of radius dia/2
    half = bh.add('Division', 1180, y, f'_diaHalf_{tag}')
    bh.wire(sel['DimY'], 'Item', half, 'A')
    bh.wire(c2, 0, half, 'B')
    circ = bh.addf('Circle', 1360, y, f'_circ{tag}')
    bh.wire(frm, 'Frame', circ, 'Plane')
    bh.wire(half, 'Result', circ, 'Radius')

    # rect/flat branch: rectangle centered on the frame (domains -x/2..+x/2)
    doms = {}
    for k, (ax, src) in enumerate((('X', sel['DimX']), ('Y', sel['DimY']))):
        hp = bh.add('Multiplication', 1180, y + 40 + k * 60, f'_{ax}HalfP_{tag}')
        bh.wire(src, 'Item', hp, 'A'); bh.wire(cp5, 0, hp, 'B')
        hn = bh.add('Multiplication', 1180, y + 70 + k * 60, f'_{ax}HalfN_{tag}')
        bh.wire(src, 'Item', hn, 'A'); bh.wire(cn5, 0, hn, 'B')
        dm = bh.add('ConstructDomain', 1360, y + 55 + k * 60, f'_dom{ax}_{tag}')
        bh.wire(hn, 'Result', dm, 0); bh.wire(hp, 'Result', dm, 1)
        doms[ax] = dm
    rct = bh.add('Rectangle', 1540, y + 80, f'_rect{tag}')
    bh.wire(frm, 'Frame', rct, 'Plane')
    bh.wire(doms['X'], 0, rct, 'X Size')
    bh.wire(doms['Y'], 0, rct, 'Y Size')

    # gate: 0 -> Circle (stream 0), 1 -> Rectangle (stream 1)
    sf = bh.addf('Stream Filter', 1720, y + 40, f'_selSec_{tag}')
    bh.wire(sel['Gate'], 'Item', sf, 0)
    bh.wire(circ, 'Circle', sf, 1)
    bh.wire(rct, 'Rectangle', sf, 2)

    # one shared downstream for every section type.
    # Sweep1's Sections input is LIST access: N rails + N sections as one flat list
    # hands EVERY rail the whole section list, which fails outright (verified live:
    # 5 branches / 0 breps on the posts). Graft both sides so branch i carries
    # exactly rail i and the section built on rail i's own frame.
    gr = bh.addf('Graft Tree', 1870, y, f'_graftRail_{tag}')
    bh.wire(rail, rport, gr, 0)
    gs = bh.addf('Graft Tree', 1870, y + 80, f'_graftSec_{tag}')
    bh.wire(sf, 0, gs, 0)

    sw = bh.addf('Sweep1', 2020, y + 40, f'_sweep{tag}')
    bh.wire(gr, 0, sw, 'Rail')
    bh.wire(gs, 0, sw, 'Sections')
    cap = bh.addf('Cap Holes', 2170, y + 40, vnick)
    bh.wire(sw, 'Brep', cap, 'Brep')

    # BOM: catalog kg/m replaces the hardcoded density constant
    bh.clear_input(kgmult, 'B')
    bh.wire(sel['Kg'], 'Item', kgmult, 'B')

    new[role] = dict(catalog=cat, slider=sl, frame=frm, circle=circ, rect=rct,
                     filt=sf, graft_rail=gr, graft_sec=gs, sweep=sw, vol=cap,
                     sel={k: v for k, v in sel.items()})

s['p6'] = new
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')

# --- verification -------------------------------------------------------------------
st = gh.inspect('status')
bad = [c for c in st.get('components', []) if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))

for role, d in new.items():
    n = len(profiles.ROLES[role])
    for lbl in ('gate', 'dimx', 'dimy', 'kgm'):
        bh.check_list(d['catalog'], lbl, n, f'{role}.{lbl}')
    g = (gh.inspect('geometry', id=d['vol']).get('outputs') or [{}])[0]
    items = g.get('items') or [{}]
    print(role, 'vol count=', g.get('count'), 'type=', json.dumps(items[0])[:120])
    print(role, 'kg/m selected=', gh.inspect('outputs', id=d['sel']['Kg']).get('outputs', [{}])[0].get('preview'))
