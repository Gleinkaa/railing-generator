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

"""Phase 9 — BOM extension (mounting hardware + diagonals) and save/export.

Adds four lines to the Phase-5 Stueckliste: decorative diagonals, anchor plates, bolt
assemblies, and a corrected grand total. Plate mass is computed from the LIVE plate
sliders (W x H x T x 7.85e-6 kg/mm3) rather than the 1.73 / 1.13 kg figures quoted in
the research, so the BOM follows the geometry when the plate is resized.

The Phase-5 'GESAMT:' line is re-pointed at the new grand total — leaving it on the old
three-group sum would under-report the assembly while still looking plausible.
"""
import gh, bh, json, os

s = json.load(open('state.json'))
gh.doc('snapshot', name='pre_p9')
gh.doc('solver', enabled=False)

ADD = 'a0d62394-a118-422d-abb3-6af115c75b25'
Y = 3400
sld = s['p7']['sliders']

rho_mm = bh.const(7.85e-06, 150, Y, '_rho_mm3')      # kg per mm^3, S235
c1000 = bh.const(1000, 150, Y + 30, '_1000B')
boltkg = bh.slider('Bolzen-Masse-kg', 0.05, 0.30, 0.12, 2, 150, Y + 60)  # M12 + nut + washer

def mul(a, ap, b, bp, x, y, nick):
    m = bh.add('Multiplication', x, y, nick)
    bh.wire(a, ap, m, 'A'); bh.wire(b, bp, m, 'B')
    return m

# --- decorative diagonals ------------------------------------------------------------
lenD = bh.add('Length', 510, Y, '_len_Diag')
bh.wire(s['p8']['dAktiv'], 0, lenD, 'Curve')
sumD = bh.add('MassAddition', 690, Y, '_sum_Diag')
bh.wire(lenD, 'Length', sumD, 'Input')
mD = bh.add('Division', 870, Y, '_m_Diag')
bh.wire(sumD, 'Result', mD, 'A'); bh.wire(c1000, 0, mD, 'B')
kgD = mul(mD, 'Result', s['p8']['kgm'], 'Item', 1050, Y, 'kg_Diag')

# --- anchor plates: mode-dependent footprint x thickness x density -------------------
aF = mul(sld['Platte-Breite'], 0, sld['Platte-Hoehe'], 0, 510, Y + 60, '_areaFasc')
aT = mul(sld['Platte-Breite-Top'], 0, sld['Platte-Tiefe'], 0, 510, Y + 100, '_areaTop')
aSel = bh.addf('Stream Filter', 690, Y + 80, '_areaPlatte')
bh.wire(sld['Montage-Typ'], 0, aSel, 0)
bh.wire(aF, 'Result', aSel, 1)
bh.wire(aT, 'Result', aSel, 2)
volP = mul(aSel, 0, sld['Platte-Dicke'], 0, 870, Y + 80, '_volPlatte')
kg1P = mul(volP, 'Result', rho_mm, 0, 1050, Y + 80, '_kgProPlatte')

nP = bh.addf('List Length', 690, Y + 130, '_nPlatten')
bh.wire(s['p7']['platten'], 0, nP, 'List')
kgP2 = mul(kg1P, 'Result', nP, 'Length', 1230, Y + 80, 'kg_Platten')

# --- bolt assemblies -----------------------------------------------------------------
nB = bh.addf('List Length', 690, Y + 180, '_nBolzen')
bh.wire(s['p7']['bolzen'], 0, nB, 'List')
kgB = mul(nB, 'Length', boltkg, 0, 1050, Y + 180, 'kg_Bolzen')

# --- corrected grand total: old 3-group sum + diagonals + plates + bolts -------------
t1 = bh.add(ADD, 1410, Y + 40, '_addTD')
bh.wire(s['total'], 'Result', t1, 'A'); bh.wire(kgD, 'Result', t1, 'B')
t2 = bh.add(ADD, 1590, Y + 80, '_addTP')
bh.wire(t1, 'Result', t2, 'A'); bh.wire(kgP2, 'Result', t2, 'B')
tot = bh.add(ADD, 1770, Y + 120, 'kg_GESAMT_ALL')
bh.wire(t2, 'Result', tot, 'A'); bh.wire(kgB, 'Result', tot, 'B')

# --- panel lines ---------------------------------------------------------------------
unit = bh.const(' kg', 1950, Y + 260, '_unitB')
def line(nick, lbl, kgid, y):
    lb = bh.const(lbl, 1950, y + 30, '_lblB_' + nick)
    c1 = bh.add('Concatenate', 2130, y, '_cAB_' + nick)
    bh.wire(lb, 0, c1, 'Fragment A'); bh.wire(kgid, 'Result', c1, 'Fragment B')
    c2 = bh.add('Concatenate', 2310, y, '_cBB_' + nick)
    bh.wire(c1, 'Result', c2, 'Fragment A'); bh.wire(unit, 0, c2, 'Fragment B')
    return c2

lD = line('D', 'Diagonalen Flachstahl: ', kgD, Y)
lP = line('P', 'Ankerplatten: ', kgP2, Y + 80)
lB = line('B', 'Bolzen M12: ', kgB, Y + 160)
for src in (lD, lP, lB):
    bh.wire(src, 'Result', s['panel'], 0)

# the Phase-5 GESAMT line must now report the full assembly
gesamt = bh.by_nick('_cA_T')
bh.clear_input(gesamt, 'Fragment B')
bh.wire(tot, 'Result', gesamt, 'Fragment B')

s['p9'] = dict(kgD=kgD, kgPlatten=kgP2, kgBolzen=kgB, total_all=tot)
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')

# --- verification + save -------------------------------------------------------------
st = gh.inspect('status')
bad = [c for c in st.get('components', []) if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))

for nm, cid in (('plates', nP), ('bolts', nB), ('kg_Diag', kgD),
                ('kg_Platten', kgP2), ('kg_Bolzen', kgB), ('GESAMT_ALL', tot)):
    print(nm, '=', gh.inspect('outputs', id=cid).get('outputs', [{}])[0].get('preview'))
print('SANITY: totals in tens of kg, not tens of thousands (mm->m conversion intact).')
print('PANEL:', json.dumps(gh.inspect('outputs', id=s['panel']), ensure_ascii=False)[:800])

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print(gh.doc('save', path=os.path.join(root, 'Railing_Generator.gh')))
gh.doc('capture_canvas', path=os.path.join(root, 'scratch', 'canvas_p9.png'), fit=True)
gh.doc('capture_viewport', path=os.path.join(root, 'scratch', 'view_p9.png'))
