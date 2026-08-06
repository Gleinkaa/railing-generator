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
gh.doc('solver', enabled=False)

# radii + caps
r1 = bh.const(21.2, 2300, 300, '_rHand')
r2 = bh.const(6,    2300, 820, '_rFuell')
cap= bh.const(1,    2300, 380, '_capFlat')
pipeH = bh.add('Pipe', 2480, 340, 'Rohr_Handlauf')
pipeF = bh.add('Pipe', 2480, 800, 'Rohr_Fuellstaebe')
bh.wire(s['handrail'],'Geometry', pipeH,'Curve'); bh.wire(r1,0,pipeH,'Radius'); bh.wire(cap,0,pipeH,'Caps')
bh.wire(s['fill'],'Line', pipeF,'Curve');        bh.wire(r2,0,pipeF,'Radius'); bh.wire(cap,0,pipeF,'Caps')

# posts: perp frame -> rectangle -> extrude
cm20=bh.const(-20,2300,560,'_-20'); cp20=bh.const(20,2300,620,'_20')
dom = bh.add('ConstructDomain', 2480, 590, '_dom40')
bh.wire(cm20,0,dom,0); bh.wire(cp20,0,dom,1)
c0p = bh.const(0, 2300, 500, '_t0')
pf  = bh.add('PerpFrame', 2480, 460, '_PostFrame')
bh.wire(s['posts'],'Line', pf,'Curve'); bh.wire(c0p,0, pf,'Parameter')
rect= bh.add('Rectangle', 2660, 490, '_PostProfil')
bh.wire(pf,'Frame', rect,'Plane'); bh.wire(dom,0, rect,'X Size'); bh.wire(dom,0, rect,'Y Size')
uzE = bh.add('UnitZ', 2660, 620, '_ZExtr')
bh.wire(s['sub'],'Result', uzE,'Factor')
ext = bh.add('Extrude', 2840, 500, 'Posten_Volumen')
bh.wire(rect,'Rectangle', ext,'Base'); bh.wire(uzE,'Unit vector', ext,'Direction')

s.update(pipeH=pipeH, pipeF=pipeF, dom=dom, pf=pf, rect=rect, uzE=uzE, ext=ext)
json.dump(s, open('state.json','w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')
st = gh.inspect('status'); comps = st.get('components',[])
bad = [c for c in comps if c.get('status') not in ('OK',None) and c.get('name')!='Load']
print('NON-OK(mine):', json.dumps(bad, ensure_ascii=False))
for nm,cid in [('pipeH',pipeH),('pipeF',pipeF),('ext',ext)]:
    g = gh.inspect('geometry', id=cid).get('outputs',[{}])[0]
    print(nm, 'count=', g.get('count'), 'items0=', json.dumps(g.get('items',[{}])[0])[:160])
