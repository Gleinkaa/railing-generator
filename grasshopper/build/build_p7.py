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

"""Phase 7 — switchable mounting: fascia (side) plate vs top-mount base plate.

Per Research/subsystem_topology.md §3 and Research/mounting_and_style.md. At every post
base point both mounting styles are built, and `Montage-Typ` (0=fascia, 1=top) selects one
into the visible output via Stream Filter — so the unused style contributes no geometry.

Plate/bolt orientation is derived, never hardcoded: Cross(tangent, UnitZ) gives the
horizontal slab-edge normal, so the mounting stays correct at any rake angle.

Deviation from the topology doc: a dedicated `Platte-Breite-Top` slider is added so the
researched fascia default (100x220x10) and top-plate default (120x120x10) can both be
active at once; the doc had a single shared width slider that could only satisfy one.
"""
import gh
import bh
import json

s = json.load(open('state.json'))
gh.doc('snapshot', name='pre_p7')
gh.doc('solver', enabled=False)

Y = 2050
cp5 = bh.const(0.5, 150, Y, '_0p5M')
c1 = bh.const(1, 150, Y + 30, '_1M')
cn1 = bh.const(-1, 150, Y + 60, '_-1M')

def half(src, x, y, nick, port='Result'):
    """0.5 x value — Center Box X/Y/Z inputs are half-extents, not full sizes."""
    m = bh.add('Multiplication', x, y, nick)
    bh.wire(src, port, m, 'A'); bh.wire(cp5, 0, m, 'B')
    return m

# --- sliders (defaults from Research/mounting_and_style.md) --------------------------
sld = {}
for i, (nick, mn, mx, val) in enumerate([
        ('Montage-Typ',         0,  1,  0),    # 0 = fascia, 1 = top-mount
        ('Platte-Breite',     60, 300, 100),   # fascia: along the slab edge
        ('Platte-Hoehe',     100, 400, 220),   # fascia: vertical
        ('Platte-Breite-Top', 60, 300, 120),   # top plate: along the edge
        ('Platte-Tiefe',      60, 300, 120),   # top plate: across the edge
        ('Platte-Dicke',       6,  20,  10),
        ('Bolzen-Durchmesser', 8,  20,  12),   # M12
        ('Bolzen-Laenge',     50, 200, 100),
        ('Bolzen-Offset-V',   40, 150,  75),   # fascia: half of 150 mm bolt spacing
        ('Bolzen-Offset-XY',  15,  60,  20),   # top: corner inset -> 80 mm pitch
        ('Fascia-Offset',      0, 200,   0)]):
    sld[nick] = bh.slider(nick, mn, mx, val, 0, 150, Y + 100 + i * 30)

# --- outward slab-edge normal (rake-safe) -------------------------------------------
ev = bh.addf('Evaluate Curve', 510, Y, '_evalBase')
bh.wire(s['untergurt'], 'Geometry', ev, 'Curve')
bh.wire(s['dc'], 'Parameters', ev, 'Parameter')
uz = bh.add('UnitZ', 510, Y + 60, '_zM')
bh.wire(c1, 0, uz, 'Factor')
crs = bh.addf('Cross Product', 690, Y + 30, '_edgeNrm')
bh.wire(ev, 'Tangent', crs, 'A'); bh.wire(uz, 'Unit vector', crs, 'B')
n1 = bh.addf('Unit Vector', 870, Y + 30, '_edgeN1')   # Cross output is NOT unitized
bh.wire(crs, 'Vector', n1, 'Vector')

# ============================ FASCIA branch (Montage-Typ = 0) =======================
amp = bh.addf('Amplitude', 1050, Y, '_fascVec')
bh.wire(n1, 'Vector', amp, 'Vector'); bh.wire(sld['Fascia-Offset'], 0, amp, 'Amplitude')
fpt = bh.add('Move', 1230, Y, '_fascPt')
bh.wire(s['dc'], 'Points', fpt, 'Geometry'); bh.wire(amp, 'Vector', fpt, 'Motion')

# plane X = run tangent (width), Y = world Z (height) => normal = outward slab normal
fpln = bh.addf('Construct Plane', 1410, Y, '_fascPln')
bh.wire(fpt, 'Geometry', fpln, 'Origin')
bh.wire(ev, 'Tangent', fpln, 'X-Axis')
bh.wire(uz, 'Unit vector', fpln, 'Y-Axis')
fbox = bh.addf('Center Box', 1770, Y, '_fascPlate')
bh.wire(fpln, 'Plane', fbox, 'Base')
bh.wire(half(sld['Platte-Breite'], 1590, Y, '_fW'), 'Result', fbox, 'X')
bh.wire(half(sld['Platte-Hoehe'], 1590, Y + 30, '_fH'), 'Result', fbox, 'Y')
bh.wire(half(sld['Platte-Dicke'], 1590, Y + 60, '_fT'), 'Result', fbox, 'Z')

# two bolts, offset +/- vertically, driven horizontally INTO the slab.
# Construct Plane(X=UnitZ, Y=tangent) => normal = Z x tangent = -outward = into slab.
rBolt = bh.add('Division', 1590, Y + 90, '_rBolt')
bh.wire(sld['Bolzen-Durchmesser'], 0, rBolt, 'A'); bh.wire(bh.const(2, 150, Y + 90, '_2M'), 0, rBolt, 'B')
fbolts = []
for k, sign in ((0, 1), (1, -1)):
    zoff = bh.add('UnitZ', 1230, Y + 120 + k * 60, f'_vOff{k}')
    mul = bh.add('Multiplication', 1050, Y + 120 + k * 60, f'_vAmt{k}')
    bh.wire(sld['Bolzen-Offset-V'], 0, mul, 'A')
    bh.wire(c1 if sign > 0 else cn1, 0, mul, 'B')
    bh.wire(mul, 'Result', zoff, 'Factor')
    bpt = bh.add('Move', 1410, Y + 120 + k * 60, f'_boltPt{k}')
    bh.wire(fpt, 'Geometry', bpt, 'Geometry'); bh.wire(zoff, 'Unit vector', bpt, 'Motion')
    bpl = bh.addf('Construct Plane', 1590, Y + 120 + k * 60, f'_boltPln{k}')
    bh.wire(bpt, 'Geometry', bpl, 'Origin')
    bh.wire(uz, 'Unit vector', bpl, 'X-Axis')
    bh.wire(ev, 'Tangent', bpl, 'Y-Axis')
    cyl = bh.addf('Cylinder', 1770, Y + 120 + k * 60, f'_fascBolt{k}')
    bh.wire(bpl, 'Plane', cyl, 'Base')
    bh.wire(rBolt, 'Result', cyl, 'Radius')
    bh.wire(sld['Bolzen-Laenge'], 0, cyl, 'Length')
    fbolts.append(cyl)

fmrg = bh.addf('Merge', 1950, Y + 150, '_fascBolts')
bh.wire(fbolts[0], 'Cylinder', fmrg, 0); bh.wire(fbolts[1], 'Cylinder', fmrg, 1)

# ============================ TOP branch (Montage-Typ = 1) ==========================
Y2 = Y + 300
# Horizontal run direction = the raked tangent projected into plan (UnitZ x outward
# normal). The top plate lies flat, so BOTH its axes and the bolt corner offsets must
# be horizontal: offsetting along the raked 3D tangent pushed the corner bolts out of
# the plate plane (verified live — corner z drifted to 117.9 / 82.1 off a 100 mm base).
# Deriving the axes this way also keeps the plate aligned to the run, which a plain
# XY Plane only happened to do while the run was parallel to world X.
thc = bh.addf('Cross Product', 1050, Y2 - 60, '_tanHorizX')
bh.wire(uz, 'Unit vector', thc, 'A'); bh.wire(n1, 'Vector', thc, 'B')
th = bh.addf('Unit Vector', 1230, Y2 - 60, '_tanHoriz')
bh.wire(thc, 'Vector', th, 'Vector')

tpln = bh.addf('Construct Plane', 1410, Y2, '_topPln')
bh.wire(s['dc'], 'Points', tpln, 'Origin')
bh.wire(th, 'Vector', tpln, 'X-Axis')
bh.wire(n1, 'Vector', tpln, 'Y-Axis')
tbox = bh.addf('Center Box', 1770, Y2, '_topPlate')
bh.wire(tpln, 'Plane', tbox, 'Base')
bh.wire(half(sld['Platte-Breite-Top'], 1590, Y2, '_tW'), 'Result', tbox, 'X')
bh.wire(half(sld['Platte-Tiefe'], 1590, Y2 + 30, '_tD'), 'Result', tbox, 'Y')
bh.wire(half(sld['Platte-Dicke'], 1590, Y2 + 60, '_tT'), 'Result', tbox, 'Z')

# corner offset magnitude = half plate dim - inset, per axis
def inset(dim_slider, x, y, nick):
    h = half(dim_slider, x, y, nick + '_h')
    sub = bh.add('Subtraction', x + 120, y, nick)
    bh.wire(h, 'Result', sub, 'A'); bh.wire(sld['Bolzen-Offset-XY'], 0, sub, 'B')
    return sub
aW = inset(sld['Platte-Breite-Top'], 1050, Y2 + 90, '_insW')
aD = inset(sld['Platte-Tiefe'], 1050, Y2 + 120, '_insD')

# downward bolt axis: Construct Plane(X=UnitX, Y=-UnitY) => normal = -Z
ux = bh.addf('Unit X', 1230, Y2 + 150, '_uX')
bh.wire(c1, 0, ux, 'Factor')
uyn = bh.addf('Unit Y', 1230, Y2 + 180, '_uYneg')
bh.wire(cn1, 0, uyn, 'Factor')

tbolts = []
for k, (sw, sd) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
    yk = Y2 + 210 + k * 60
    vecs = []
    for lbl, base, mag, sign in (('t', th, aW, sw), ('n', n1, aD, sd)):
        m = bh.add('Multiplication', 1050, yk + (0 if lbl == 't' else 25), f'_amt{lbl}{k}')
        bh.wire(mag, 'Result', m, 'A'); bh.wire(c1 if sign > 0 else cn1, 0, m, 'B')
        a = bh.addf('Amplitude', 1230, yk + (0 if lbl == 't' else 25), f'_vec{lbl}{k}')
        bh.wire(base, 'Vector', a, 'Vector')
        bh.wire(m, 'Result', a, 'Amplitude')
        vecs.append(a)
    add = bh.add(bh.find('Addition'), 1410, yk, f'_corner{k}')
    bh.wire(vecs[0], 'Vector', add, 'A'); bh.wire(vecs[1], 'Vector', add, 'B')
    cpt = bh.add('Move', 1590, yk, f'_topBoltPt{k}')
    bh.wire(s['dc'], 'Points', cpt, 'Geometry'); bh.wire(add, 'Result', cpt, 'Motion')
    cpl = bh.addf('Construct Plane', 1770, yk, f'_topBoltPln{k}')
    bh.wire(cpt, 'Geometry', cpl, 'Origin')
    bh.wire(ux, 'Unit vector', cpl, 'X-Axis')
    bh.wire(uyn, 'Unit vector', cpl, 'Y-Axis')
    cyl = bh.addf('Cylinder', 1950, yk, f'_topBolt{k}')
    bh.wire(cpl, 'Plane', cyl, 'Base')
    bh.wire(rBolt, 'Result', cyl, 'Radius')
    bh.wire(sld['Bolzen-Laenge'], 0, cyl, 'Length')
    tbolts.append(cyl)

# Merge takes 2 inputs by default -> chain rather than assume variable inputs
m1 = bh.addf('Merge', 2130, Y2 + 240, '_topB12')
bh.wire(tbolts[0], 'Cylinder', m1, 0); bh.wire(tbolts[1], 'Cylinder', m1, 1)
m2 = bh.addf('Merge', 2130, Y2 + 300, '_topB34')
bh.wire(tbolts[2], 'Cylinder', m2, 0); bh.wire(tbolts[3], 'Cylinder', m2, 1)
tmrg = bh.addf('Merge', 2310, Y2 + 270, '_topBolts')
bh.wire(m1, 0, tmrg, 0); bh.wire(m2, 0, tmrg, 1)

# ============================ mode select ===========================================
selP = bh.addf('Stream Filter', 2490, Y + 150, 'Montage_Platten')
bh.wire(sld['Montage-Typ'], 0, selP, 0)
bh.wire(fbox, 'Box', selP, 1)
bh.wire(tbox, 'Box', selP, 2)

selB = bh.addf('Stream Filter', 2490, Y + 250, 'Montage_Bolzen')
bh.wire(sld['Montage-Typ'], 0, selB, 0)
bh.wire(fmrg, 0, selB, 1)
bh.wire(tmrg, 0, selB, 2)

s['p7'] = dict(sliders=sld, evalBase=ev, edgeN1=n1, fascPlate=fbox, fascBolts=fmrg,
               topPlate=tbox, topBolts=tmrg, platten=selP, bolzen=selB)
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')

# --- verification -------------------------------------------------------------------
st = gh.inspect('status')
bad = [c for c in st.get('components', []) if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))

npost = gh.inspect('outputs', id=s['dc']).get('outputs', [{}])[0].get('count')
print('post base points:', npost)
for nick, cid, per in (('Montage_Platten', selP, 1), ('Montage_Bolzen', selB, None)):
    g = gh.inspect('geometry', id=cid).get('outputs', [{}])[0]
    print(nick, 'count=', g.get('count'), 'item0=', json.dumps(g.get('items', [{}])[0])[:140])
print('EXPECT: plates == %s ; bolts == %s (fascia, Typ=0) or %s (top, Typ=1)'
      % (npost, (npost or 0) * 2, (npost or 0) * 4))
print('VISUAL CHECK: fascia bolts must run INTO the slab and top bolts DOWNWARD. '
      'If mirrored, the outward sign of _edgeN1 is flipped for this run direction.')
