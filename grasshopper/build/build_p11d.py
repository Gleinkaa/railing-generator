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

"""Phase 11d — stop the decorative diagonals wrapping around each bay.

Phase 8 builds the crossing diagonals by shifting the upper rail's node list against
the lower rail's and drawing lines between the two, with `Wrap = true` on the Shift
List.  Wrap makes node i pair with node (i+s) mod n, so the last s nodes of every bay
pair back with the FIRST nodes of the same bay: s bay-spanning, near-horizontal bars
per direction per bay.  Those are the long shallow lines crossing the panel in the
viewport, and a near-horizontal member is exactly what the anti-climb reasoning in
build_p8.py's header is trying to avoid.

Fix: Wrap = false, and a Shortest List trims the lower-rail node list to match the
shortened shifted list so the two sides stay index-aligned.  Without that trim the Line
component would pad the shorter list by repeating its last item, fanning s bars onto a
single node — the same silent list-length trap as the Sweep1 section bug.
"""
import gh
import bh
import json

s = json.load(open('state.json'))
gh.doc('snapshot', name='pre_p11d')

divLo = s['p8']['divLo']
before = gh.inspect('outputs', id=s['p8']['dAktiv']).get('outputs', [{}])[0].get('count')
print('diagonals before:', before)

gh.doc('solver', enabled=False)

for c in gh.canvas('list', limit=600)['components']:
    if c.get('nickname') in ('_slPair0', '_slPair1'):
        gh.canvas('delete', id=c['id'])

new_ids = []
for k, nick in ((0, '_diagFwd'), (1, '_diagBwd')):
    wrap = [c for c in gh.canvas('list', limit=600)['components']
            if c.get('nickname') == f'_wrap{k}'][0]['id']
    r = gh.canvas('set', id=wrap, value='false')
    assert r.get('success'), f'_wrap{k} -> false failed: {r}'

    sl = bh.by_nick(f'_hiShift{k}')
    ln = bh.by_nick(nick)
    pair = bh.addf('Shortest List', 1860, 2720 + k * 60, f'_slPair{k}')
    new_ids.append(pair)
    bh.wire(divLo, 'Points', pair, 0)
    bh.wire(sl, 'List', pair, 1)
    bh.clear_input(ln, 'Start')
    bh.clear_input(ln, 'End')
    bh.wire(pair, 0, ln, 'Start')
    bh.wire(pair, 1, ln, 'End')

gh.canvas('preview', ids=json.dumps(new_ids), enabled=False)

s['p11']['diag_pairs'] = new_ids
json.dump(s, open('state.json', 'w'), indent=1)

gh.doc('solver', enabled=True)
gh.doc('recompute')

st = gh.inspect('status')
bad = [c for c in st.get('components', [])
       if c.get('status') not in ('OK', None) and c.get('name') != 'Load']
print('NON-OK:', json.dumps(bad, ensure_ascii=False))
assert not bad, 'components broke'

after = gh.inspect('outputs', id=s['p8']['dAktiv']).get('outputs', [{}])[0].get('count')
print('diagonals after :', after)
assert after and after < before, f'expected fewer diagonals, {before} -> {after}'

nd = gh.inspect('outputs', id=s['p8']['vol']).get('outputs', [{}])[0].get('count')
print('Diagonal_Volumen:', nd)
assert nd == after, f'{nd} solids vs {after} centrelines'
