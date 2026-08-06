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

import gh, bh, json
s = json.load(open('state.json'))
ADD='a0d62394-a118-422d-abb3-6af115c75b25'
gh.doc('solver', enabled=False)

c1000 = bh.const(1000, 3300, 1150, '_1000')
def group(nick, src_id, src_out, dens, y):
    L = bh.add('Length', 3300, y, '_len_'+nick)
    bh.wire(src_id, src_out, L, 'Curve')
    M = bh.add('MassAddition', 3460, y, '_sum_'+nick)
    bh.wire(L, 'Length', M, 'Input')
    D = bh.add('Division', 3620, y, '_m_'+nick)
    bh.wire(M, 'Result', D, 'A'); bh.wire(c1000, 0, D, 'B')
    dc = bh.const(dens, 3620, y+40, '_rho_'+nick)
    X = bh.add('Multiplication', 3780, y, 'kg_'+nick)
    bh.wire(D, 'Result', X, 'A'); bh.wire(dc, 0, X, 'B')
    return X

kgF = group('Fuell', s['fill'], 'Line',      0.888, 300+1000)   # y offset handled below
# place groups at sane y
gh.canvas('move', id=kgF, x=3780, y=980)

kgH = group('Hand',  s['handrail'], 'Geometry', 1.993, 1120)
kgP = group('Post',  s['posts'], 'Line',      2.386, 1260)

# grand total
a1 = bh.add(ADD, 3940, 1080, '_addFH'); bh.wire(kgF,'Result',a1,'A'); bh.wire(kgH,'Result',a1,'B')
a2 = bh.add(ADD, 4100, 1120, 'kg_GESAMT'); bh.wire(a1,'Result',a2,'A'); bh.wire(kgP,'Result',a2,'B')

# labels + concat
unit = bh.const(' kg', 4100, 1300, '_unit')
def line(nick, lbl, kgid, y):
    Lb = bh.const(lbl, 4100, y+40, '_lbl_'+nick)
    c1 = bh.add('Concatenate', 4280, y, '_cA_'+nick); bh.wire(Lb,0,c1,'Fragment A'); bh.wire(kgid,'Result',c1,'Fragment B')
    c2 = bh.add('Concatenate', 4440, y, '_cB_'+nick); bh.wire(c1,'Result',c2,'Fragment A'); bh.wire(unit,0,c2,'Fragment B')
    return c2
lF = line('F','Fuellstaebe Oe12: ', kgF, 980)
lH = line('H','Handlauf Oe42.4: ',  kgH, 1080)
lP = line('P','Posten 40x40: ',      kgP, 1180)
lT = line('T','GESAMT: ',            a2,  1280)

panel = bh.add('Panel', 4640, 1080, 'Stueckliste_BOM')
for src in (lF,lH,lP,lT): bh.wire(src,'Result', panel, 0)

s.update(kgF=kgF,kgH=kgH,kgP=kgP,total=a2,panel=panel)
json.dump(s, open('state.json','w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')
st=gh.inspect('status'); bad=[c for c in st.get('components',[]) if c.get('status') not in ('OK',None) and c.get('name')!='Load']
print('NON-OK(mine):', json.dumps(bad, ensure_ascii=False))
for nm,cid in [('kgF',kgF),('kgH',kgH),('kgP',kgP),('GESAMT',a2)]:
    print(nm, gh.inspect('outputs', id=cid).get('outputs',[{}])[0].get('preview'))
print('PANEL:', json.dumps(gh.inspect('outputs', id=panel), ensure_ascii=False)[:600])
