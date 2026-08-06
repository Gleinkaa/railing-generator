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

"""Phase 11b — give the Untergurt a real solid, a profile selector and a BOM row.

Reported by the user from the Rhino viewport: "shouldn't there be another rail on the
down side?".  Correct — there wasn't one.  `Untergurtlinie` existed only as a
construction centreline: it positioned the infill bars and got shattered into bays, but
nothing was ever swept along it, so the bottom chord was missing from the model AND
from the mass total.  Confirmed live before this phase: sweeps were _sweepH/_sweepP/
_sweepI/_sweepD only, and the kg panel had no Untergurt row.

This mirrors the Phase-6 profile-selector macro exactly (catalog script -> List Item
-> Circle | Rectangle -> Stream Filter -> graft both sides -> Sweep1 -> Cap Holes), so
the Untergurt behaves like every other role: one `Untergurt-Profil` index drives both
the swept section and the kg/m that reaches the BOM.

The rail is swept along the WHOLE untergurt line rather than per bay: it is a
continuous chord that the posts pass through, which is how it is fabricated.
"""
import gh
import bh
import json
import os
import profiles

s = json.load(open('state.json'))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
gh.doc('snapshot', name='pre_p11b')
gh.doc('solver', enabled=False)

Y = 3600
ROLE = 'untergurt'
rows = profiles.ROLES[ROLE]
n = len(rows)
new_ids = []

# --- drop anything a half-applied earlier run left behind -----------------------------
# (a timed-out MCP call can still have been applied, so this must run before adding)
MINE = {'_t0U', '_2U', '_0p5U', '_-0p5U', '_1000U', 'cat_U', 'Untergurt-Profil',
        '_selGate_U', '_selDimX_U', '_selDimY_U', '_selKg_U', '_frmU', '_diaHalf_U',
        '_circU', '_XHalfP_U', '_XHalfN_U', '_domX_U', '_YHalfP_U', '_YHalfN_U',
        '_domY_U', '_rectU', '_selSec_U', '_graftRail_U', '_graftSec_U', '_sweepU',
        'Untergurt_Volumen', '_m_Unter', 'kg_Unter', '_addPU', '_lblU', '_unitU',
        '_cAB_U', '_cBB_U'}
stale = [c for c in gh.canvas('list', limit=600)['components'] if c.get('nickname') in MINE]
for c in stale:
    gh.canvas('delete', id=c['id'])
print('cleaned stale:', sorted(c['nickname'] for c in stale))


def keep(cid):
    new_ids.append(cid)
    return cid


# --- shared constants ----------------------------------------------------------------
c0 = keep(bh.const(0, 150, Y, '_t0U'))
c2 = keep(bh.const(2, 150, Y + 30, '_2U'))
cp5 = keep(bh.const(0.5, 150, Y + 60, '_0p5U'))
cn5 = keep(bh.const(-0.5, 150, Y + 90, '_-0p5U'))
c1000 = keep(bh.const(1000, 150, Y + 120, '_1000U'))

# --- catalog + selector ---------------------------------------------------------------
cat = keep(bh.catalog({'gate': profiles.section_flags(ROLE),
                       'dimx': profiles.dx_list(ROLE),
                       'dimy': profiles.dia_list(ROLE),
                       'kgm':  profiles.kgm_list(ROLE)}, 330, Y, 'cat_U'))
sl = keep(bh.slider('Untergurt-Profil', 0, n - 1, 0, 0, 510, Y + 160))

sel = {}
for j, (lbl, col) in enumerate((('Gate', 'gate'), ('DimX', 'dimx'),
                                ('DimY', 'dimy'), ('Kg', 'kgm'))):
    li = keep(bh.addf('List Item', 690, Y + j * 40, f'_sel{lbl}_U'))
    bh.wire(cat, col, li, 'List')      # by NAME: output 0 is the script's own `out`
    bh.wire(sl, 0, li, 'Index')
    sel[lbl] = li

# --- section on the start frame of the untergurt line ----------------------------------
frm = keep(bh.addf('Perp Frame', 1000, Y, '_frmU'))
bh.wire(s['untergurt'], 'Geometry', frm, 'Curve')
bh.wire(c0, 0, frm, 'Parameter')

half = keep(bh.add('Division', 1180, Y, '_diaHalf_U'))
bh.wire(sel['DimY'], 'Item', half, 'A')
bh.wire(c2, 0, half, 'B')
circ = keep(bh.addf('Circle', 1360, Y, '_circU'))
bh.wire(frm, 'Frame', circ, 'Plane')
bh.wire(half, 'Result', circ, 'Radius')

doms = {}
for k, (ax, src) in enumerate((('X', sel['DimX']), ('Y', sel['DimY']))):
    hp = keep(bh.add('Multiplication', 1180, Y + 40 + k * 60, f'_{ax}HalfP_U'))
    bh.wire(src, 'Item', hp, 'A')
    bh.wire(cp5, 0, hp, 'B')
    hn = keep(bh.add('Multiplication', 1180, Y + 70 + k * 60, f'_{ax}HalfN_U'))
    bh.wire(src, 'Item', hn, 'A')
    bh.wire(cn5, 0, hn, 'B')
    dm = keep(bh.add('ConstructDomain', 1360, Y + 55 + k * 60, f'_dom{ax}_U'))
    bh.wire(hn, 'Result', dm, 0)
    bh.wire(hp, 'Result', dm, 1)
    doms[ax] = dm
rct = keep(bh.add('Rectangle', 1540, Y + 80, '_rectU'))
bh.wire(frm, 'Frame', rct, 'Plane')
bh.wire(doms['X'], 0, rct, 'X Size')
bh.wire(doms['Y'], 0, rct, 'Y Size')

sf = keep(bh.addf('Stream Filter', 1720, Y + 40, '_selSec_U'))
bh.wire(sel['Gate'], 'Item', sf, 0)
bh.wire(circ, 'Circle', sf, 1)
bh.wire(rct, 'Rectangle', sf, 2)

# Graft both sides: Sweep1's Sections input is list-access (see build_p6.py).
gr = keep(bh.addf('Graft Tree', 1870, Y, '_graftRail_U'))
bh.wire(s['untergurt'], 'Geometry', gr, 0)
gs = keep(bh.addf('Graft Tree', 1870, Y + 80, '_graftSec_U'))
bh.wire(sf, 0, gs, 0)
sw = keep(bh.addf('Sweep1', 2020, Y + 40, '_sweepU'))
bh.wire(gr, 0, sw, 'Rail')
bh.wire(gs, 0, sw, 'Sections')
vol = keep(bh.addf('Cap Holes', 2170, Y + 40, 'Untergurt_Volumen'))
bh.wire(sw, 'Brep', vol, 'Brep')

# --- BOM --------------------------------------------------------------------------------
# `_UntLen` is the existing Length of the untergurt line (it drives the post count).
# BOM lengths are in mm and must be divided by 1000 before x kg/m -- Prompt1.md.
mU = keep(bh.add('Division', 2020, Y + 140, '_m_Unter'))
bh.wire(bh.by_nick('_UntLen'), 'Length', mU, 'A')
bh.wire(c1000, 0, mU, 'B')
kgU = keep(bh.add('Multiplication', 2200, Y + 140, 'kg_Unter'))
bh.wire(mU, 'Result', kgU, 'A')
bh.wire(sel['Kg'], 'Item', kgU, 'B')

# splice into the running total: kg_GESAMT.B currently reads kg_Post directly
kgPost = s['kgP']
kgGes = s['total']
tgt_port = None
for c in gh.wire('list', componentId=kgGes).get('connections', []):
    t, src = c.get('target', {}), c.get('source', {})
    if t.get('componentId') == kgGes and src.get('componentId') == kgPost:
        tgt_port = t.get('param')
if not tgt_port:
    # a previous run already spliced _addPU in here and the cleanup above removed it,
    # leaving the port empty — that is the only acceptable reason for kg_Post to be gone
    assert not bh.sources(kgGes, 'B'), \
        'kg_Post does not feed kg_GESAMT and B is occupied — BOM wiring changed'
    tgt_port = 'B'
addPU = keep(bh.addf('Addition', 2380, Y + 140, '_addPU'))
bh.wire(kgPost, 'Result', addPU, 'A')
bh.wire(kgU, 'Result', addPU, 'B')
bh.clear_input(kgGes, tgt_port)
bh.wire(addPU, 'Result', kgGes, tgt_port)

# BOM text row, same two-Concatenate shape the other roles use
lblU = keep(bh.const('Untergurt: ', 2380, Y + 180, '_lblU'))
unitU = keep(bh.const(' kg', 2380, Y + 210, '_unitU'))
cA = keep(bh.addf('Concatenate', 2560, Y + 180, '_cAB_U'))
bh.wire(lblU, 0, cA, 'Fragment A')
bh.wire(kgU, 'Result', cA, 'Fragment B')
cB = keep(bh.addf('Concatenate', 2740, Y + 180, '_cBB_U'))
bh.wire(cA, 'Result', cB, 'Fragment A')
bh.wire(unitU, 0, cB, 'Fragment B')
bh.wire(cB, 'Result', s['panel'], 0)

# --- preview hygiene (Phase 10 rule: only the final solids preview) --------------------
gh.canvas('preview', ids=json.dumps(new_ids), enabled=False)
for cid in new_ids:                       # params refuse the batch call
    gh.canvas('preview', id=cid, enabled=False)
r = gh.canvas('preview', id=vol, enabled=True)
assert r.get('success'), f'preview on Untergurt_Volumen failed: {r}'

s['p11']['untergurt'] = dict(catalog=cat, slider=sl, frame=frm, filt=sf, sweep=sw,
                             vol=vol, kg=kgU, sel=sel)
s['p10']['final']['Untergurt_Volumen'] = vol
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True)
gh.doc('recompute')

# --- verification -----------------------------------------------------------------------
st = gh.inspect('status')
bad = [c for c in st.get('components', [])
       if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))
assert not bad, 'components broke'

for col in ('gate', 'dimx', 'dimy', 'kgm'):
    bh.check_list(cat, col, n, f'untergurt.{col}')

g = (gh.inspect('geometry', id=vol).get('outputs') or [{}])[0]
print('Untergurt_Volumen:', g.get('count'), json.dumps((g.get('items') or [{}])[0])[:140])
assert g.get('count') == 1, f'expected 1 bottom rail solid, got {g.get("count")}'
assert (g.get('items') or [{}])[0].get('solid') is True, 'bottom rail is not a closed brep'

print('kg_Unter :', gh.inspect('outputs', id=kgU).get('outputs', [{}])[0].get('preview'))
print('BOM panel:', json.dumps(
    gh.inspect('outputs', id=s['panel']).get('outputs', [{}])[0].get('preview'),
    indent=1, ensure_ascii=False))
