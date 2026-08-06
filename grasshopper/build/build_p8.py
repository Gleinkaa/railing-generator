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

"""Phase 8 — decorative diagonal infill, as a COMPLIANT overlay.

IMPORTANT — this phase deliberately departs from Research/subsystem_topology.md §4.

That section wired `Fuellung-Stil` as an either/or Stream Filter: vertical bars OR
diagonals. That is not code-compliant for a child-accessible guard. Per
Research/mounting_and_style.md §3 (OIB RL 4 / OeNORM B 5371):

  * openings must block a 120 mm sphere, and
  * in the 150-600 mm anti-climb band NO horizontal *or diagonal* member may sit,
    because a diagonal is a foothold (Leiterwirkung) — diagonals are named explicitly.

So a purely diagonal field cannot carry compliance on its own. Scheme A is implemented
instead: the random diagonals are DECORATIVE and ride outboard of a deterministic
vertical safety field that stays in place and carries the sphere test.

`Fuellung-Stil`:
  0 = vertical bars only                      (baseline, unchanged)
  1 = vertical field + decorative diagonals    (Scheme A — decorative overlay, child-safe)
  2 = diagonals only                           (Scheme B — industrial/adults only,
                                                NOT child-safe; verticals are culled)

Style 2 is offered because the research explicitly allows it where anti-climb does not
apply, but it must never be the default. Default is 0; 1 is the decorative style.
"""
import gh
import bh
import json
import profiles

s = json.load(open('state.json'))
gh.doc('snapshot', name='pre_p8')
gh.doc('solver', enabled=False)

Y = 2720
c1 = bh.const(1, 150, Y, '_1D')
c2 = bh.const(2, 150, Y + 30, '_2D')
c3 = bh.const(3, 150, Y + 60, '_3D')
cn1 = bh.const(-1, 150, Y + 90, '_-1D')
c0 = bh.const(0, 150, Y + 120, '_0D')

sty = bh.slider('Fuellung-Stil', 0, 2, 0, 0, 150, Y + 150)
seed = bh.slider('Diagonal-Seed', 0, 9999, 42, 0, 150, Y + 180)
# max node spacing along each rail. 120 - t_bar(8) = 112 is the hard cap; 100 = margin.
dens = bh.slider('Diagonal-Dichte', 50, 112, 100, 0, 150, Y + 210)
# Scheme A: keep the decorative layer outboard of the safety plane
ausl = bh.slider('Diagonal-Auslage', 0, 100, 40, 0, 150, Y + 240)

# --- per-bay node fields on both rails ----------------------------------------------
shatH = bh.add('Shatter', 510, Y, '_shatH')
bh.wire(s['handrail'], 'Geometry', shatH, 'Curve')
bh.wire(s['dc'], 'Parameters', shatH, 'Parameters')

segL = bh.add('Length', 690, Y, '_segLenD')
bh.wire(s['shat'], 'Segments', segL, 'Curve')
nCell = bh.add('Division', 870, Y, '_nCell')
bh.wire(segL, 'Length', nCell, 'A'); bh.wire(dens, 0, nCell, 'B')
nCeil = bh.add('Round', 1050, Y, '_nCeil')
bh.wire(nCell, 'Result', nCeil, 0)

divLo = bh.add('DivideCurve', 1230, Y, '_divLo')
bh.wire(s['shat'], 'Segments', divLo, 'Curve'); bh.wire(nCeil, 'Ceiling', divLo, 'Count')
divHi = bh.add('DivideCurve', 1230, Y + 60, '_divHi')
bh.wire(shatH, 'Segments', divHi, 'Curve'); bh.wire(nCeil, 'Ceiling', divHi, 'Count')

# --- seeded per-bay shear -----------------------------------------------------------
thd = bh.add('Division', 1050, Y + 120, '_third')
bh.wire(nCeil, 'Ceiling', thd, 'A'); bh.wire(c3, 0, thd, 'B')
thdN = bh.add('Multiplication', 1050, Y + 150, '_thirdN')
bh.wire(thd, 'Result', thdN, 'A'); bh.wire(cn1, 0, thdN, 'B')
shDom = bh.add('ConstructDomain', 1230, Y + 135, '_shiftDom')
bh.wire(thdN, 'Result', shDom, 0); bh.wire(thd, 'Result', shDom, 1)

# Exactly ONE shear value per bay. Feeding nCeil into Number asked for a shift per
# NODE, so Shift List replicated each bay's node list once per shift value and blew
# the diagonals up 12x (verified live: 1248 lines where 104 are intended).
# The seed is offset by the bay index because Random restarts from the seed on every
# iteration: a single shared seed would hand every bay an identical shear, silently
# turning the "per-bay" shear into one global value.
nBay = bh.addf('List Length', 1050, Y + 175, '_nBays')
bh.wire(s['shat'], 'Segments', nBay, 'List')
bayIdx = bh.addf('Series', 1230, Y + 175, '_bayIdx')
bh.wire(c0, 0, bayIdx, 'Start'); bh.wire(c1, 0, bayIdx, 'Step')
bh.wire(nBay, 'Length', bayIdx, 'Count')
seedB = bh.addf('Addition', 1230, Y + 205, '_seedBay')
bh.wire(seed, 0, seedB, 'A'); bh.wire(bayIdx, 'Series', seedB, 'B')

rnd = bh.addf('Random', 1410, Y + 135, '_rndShift')
bh.wire(shDom, 0, rnd, 'Range')
bh.wire(c1, 0, rnd, 'Number')
bh.wire(seedB, 'Result', rnd, 'Seed')
shI = bh.add('Round', 1590, Y + 135, '_shiftInt')
bh.wire(rnd, 0, shI, 0)
shIn = bh.add('Multiplication', 1590, Y + 175, '_shiftIntN')
bh.wire(shI, 'Nearest', shIn, 'A'); bh.wire(cn1, 0, shIn, 'B')

# --- crossing diagonals: every bar starts and ends on a rail node --------------------
diag = []
for k, (shift, port) in enumerate(((shI, 'Nearest'), (shIn, 'Result'))):
    sl = bh.addf('Shift List', 1770, Y + k * 60, f'_hiShift{k}')
    bh.wire(divHi, 'Points', sl, 'List')
    bh.wire(shift, port, sl, 'Shift')
    bh.wire(bh.const('true', 1770, Y + 30 + k * 60, f'_wrap{k}'), 0, sl, 'Wrap')
    ln = bh.add('Line', 1950, Y + k * 60, f'_diag{"Fwd" if k == 0 else "Bwd"}')
    bh.wire(divLo, 'Points', ln, 'Start')
    bh.wire(sl, 'List', ln, 'End')
    diag.append(ln)

dmrg = bh.addf('Merge', 2130, Y + 30, '_diagLines')
bh.wire(diag[0], 'Line', dmrg, 0); bh.wire(diag[1], 'Line', dmrg, 1)
dflat = bh.addf('Flatten Tree', 2310, Y + 30, '_diagFlat')
bh.wire(dmrg, 0, dflat, 'Tree')

# Scheme A: push the decorative layer outboard of the vertical safety plane
oamp = bh.addf('Amplitude', 2310, Y + 90, '_auslVec')
bh.wire(s['p7']['edgeN1'], 'Vector', oamp, 'Vector')
bh.wire(ausl, 0, oamp, 'Amplitude')
dmov = bh.add('Move', 2490, Y + 30, '_diagOut')
bh.wire(dflat, 'Tree', dmov, 'Geometry'); bh.wire(oamp, 'Vector', dmov, 'Motion')

# --- style gating: verticals ON for 0/1, diagonals ON for 1/2 -----------------------
vOn = bh.addf('Smaller Than', 690, Y + 210, '_vertOn')     # style < 2
bh.wire(sty, 0, vOn, 'A'); bh.wire(c2, 0, vOn, 'B')
dOn = bh.addf('Larger Than', 690, Y + 250, '_diagOn')      # style > 0
bh.wire(sty, 0, dOn, 'A'); bh.wire(c0, 0, dOn, 'B')

vAkt = bh.addf('Cull Pattern', 870, Y + 210, 'Vertikal_Aktiv')
bh.wire(s['fill'], 'Line', vAkt, 'List'); bh.wire(vOn, 0, vAkt, 'Pattern')
dAkt = bh.addf('Cull Pattern', 2670, Y + 30, 'Diagonal_Aktiv')
bh.wire(dmov, 'Geometry', dAkt, 'List'); bh.wire(dOn, 0, dAkt, 'Pattern')

# --- re-point the Phase-6 vertical sweep and the Phase-5 BOM at the gated set --------
# Re-point the GRAFT that feeds the sweep — NOT the sweep's Rail input directly.
# Phase 6 put a Graft Tree on the rail so each bar pairs with its own section.
# Wiring the gated set straight into Sweep1.Rail bypasses that graft and leaves an
# ungrafted rail list against a grafted section list, so GH crosses every bar with
# every section: 41 x 41 = 1681 solids, with bars visibly running below the stairs.
graftF = s['p6']['infill']['graft_rail']
bh.clear_input(graftF, 0)
bh.wire(vAkt, 0, graftF, 0)
lenF = bh.by_nick('_len_Fuell')
bh.clear_input(lenF, 'Curve')
bh.wire(vAkt, 0, lenF, 'Curve')

# --- decorative diagonal solids: flat bar swept along the diagonal centerlines -------
dprof = bh.slider('Diagonal-Profil', 0, len(profiles.INFILL) - 1,
                  profiles.DIAGONAL_INFILL_INDEX, 0, 2670, Y + 250)
inf = s['p6']['infill']
# Phase 6 emits all four infill columns from ONE catalog script component, so these
# tap it by output NAME rather than the per-column component ids the draft assumed.
cat = inf['catalog']
selDX = bh.addf('List Item', 2850, Y + 150, '_selDimX_D')
bh.wire(cat, 'dimx', selDX, 'List'); bh.wire(dprof, 0, selDX, 'Index')
selDY = bh.addf('List Item', 2850, Y + 190, '_selDimY_D')
bh.wire(cat, 'dimy', selDY, 'List'); bh.wire(dprof, 0, selDY, 'Index')
selDK = bh.addf('List Item', 2850, Y + 230, '_selKg_D')
bh.wire(cat, 'kgm', selDK, 'List'); bh.wire(dprof, 0, selDK, 'Index')

frmD = bh.addf('Perp Frame', 2850, Y + 30, '_frmD')
bh.wire(dAkt, 0, frmD, 'Curve'); bh.wire(c0, 0, frmD, 'Parameter')
cp5 = bh.const(0.5, 2850, Y + 70, '_0p5D'); cn5 = bh.const(-0.5, 2850, Y + 110, '_-0p5D')
domsD = {}
for k, (ax, src) in enumerate((('X', selDX), ('Y', selDY))):
    hp = bh.add('Multiplication', 3030, Y + 150 + k * 60, f'_D{ax}HalfP')
    bh.wire(src, 'Item', hp, 'A'); bh.wire(cp5, 0, hp, 'B')
    hn = bh.add('Multiplication', 3030, Y + 180 + k * 60, f'_D{ax}HalfN')
    bh.wire(src, 'Item', hn, 'A'); bh.wire(cn5, 0, hn, 'B')
    dm = bh.add('ConstructDomain', 3210, Y + 165 + k * 60, f'_Ddom{ax}')
    bh.wire(hn, 'Result', dm, 0); bh.wire(hp, 'Result', dm, 1)
    domsD[ax] = dm
rctD = bh.add('Rectangle', 3390, Y + 180, '_rectD')
bh.wire(frmD, 'Frame', rctD, 'Plane')
bh.wire(domsD['X'], 0, rctD, 'X Size'); bh.wire(domsD['Y'], 0, rctD, 'Y Size')
# Same list-access trap as Phase 6: Sweep1's Sections input would hand every diagonal
# the whole section list. Graft both sides so each diagonal gets its own section.
grD = bh.addf('Graft Tree', 3390, Y + 90, '_graftRailD')
bh.wire(dAkt, 0, grD, 0)
gsD = bh.addf('Graft Tree', 3390, Y + 130, '_graftSecD')
bh.wire(rctD, 'Rectangle', gsD, 0)
swD = bh.addf('Sweep1', 3570, Y + 30, '_sweepD')
bh.wire(grD, 0, swD, 'Rail'); bh.wire(gsD, 0, swD, 'Sections')
volD = bh.addf('Cap Holes', 3750, Y + 30, 'Diagonal_Volumen')
bh.wire(swD, 'Brep', volD, 'Brep')

s['p8'] = dict(style=sty, seed=seed, dichte=dens, auslage=ausl, profil=dprof,
               divLo=divLo, divHi=divHi, nCeil=nCeil, diagFlat=dflat,
               vAktiv=vAkt, dAktiv=dAkt, vol=volD, kgm=selDK)
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')

# --- verification -------------------------------------------------------------------
st = gh.inspect('status')
bad = [c for c in st.get('components', []) if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))

lo = gh.inspect('outputs', id=divLo).get('outputs', [{}])[0]
hi = gh.inspect('outputs', id=divHi).get('outputs', [{}])[0]
print('rail nodes lo/hi:', lo.get('count'), hi.get('count'), '(must be equal — rails triangulate)')
print('segment lengths :', gh.inspect('outputs', id=segL).get('outputs', [{}])[0].get('preview'))
print('nodes per bay   :', gh.inspect('outputs', id=nCeil).get('outputs', [{}])[0].get('preview'))
print('CHECK max node spacing p = segLen/Ceiling must be < 120 - t_bar '
      '(t_bar = Diagonal-Profil dim_y, 8 mm for Flachstahl 40x8)')
# At the default style 0 the diagonals are culled, so an EMPTY result here is correct.
g = (gh.inspect('geometry', id=volD).get('outputs') or [{}])[0]
items = g.get('items') or [{}]
print('Diagonal_Volumen count=', g.get('count'), 'item0=', json.dumps(items[0])[:140])
print('SWITCH TEST: Fuellung-Stil 0 -> verticals only, diagonals empty; '
      '1 -> both present; 2 -> diagonals only (NOT child-safe).')
