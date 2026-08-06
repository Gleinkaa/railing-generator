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

# components
Lp   = bh.add('Length', 900, 460, '_UntLen')
c1200= bh.const(1200, 900, 520, '_1200')
div  = bh.add('Division', 1080, 480, '_L/1200')
rnd  = bh.add('Round', 1240, 480, '_Round')
sub  = bh.add('Subtraction', 1080, 600, '_Posthoehe')
dc   = bh.add('DivideCurve', 1420, 460, '_TeilerPosten')
uzp  = bh.add('UnitZ', 1420, 600, '_ZdirPost')
posts= bh.add('LineSDL', 1620, 460, 'Posten')

for cid,lbl in [(Lp,'Length'),(div,'Division'),(rnd,'Round'),(sub,'Sub'),
                (dc,'DivideCurve'),(uzp,'UnitZ'),(posts,'LineSDL')]:
    bh.ports(cid, lbl)

# wiring
bh.wire(s['untergurt'],'Geometry', Lp,'Curve')
bh.wire(Lp,'Length', div,'A')
bh.wire(c1200,0, div,'B')
bh.wire(div,'Result', rnd,0)
bh.wire(s['untergurt'],'Geometry', dc,'Curve')
bh.wire(rnd,'Ceiling', dc,'Count')
bh.wire(s['gel'],0, sub,'A')
bh.wire(s['unt'],0, sub,'B')
bh.wire(dc,'Points', posts,'Start')
bh.wire(uzp,'Unit vector', posts,'Direction')
bh.wire(sub,'Result', posts,'Length')

s['Lp']=Lp; s['div']=div; s['rnd']=rnd; s['sub']=sub; s['dc']=dc; s['uzp']=uzp; s['posts']=posts
json.dump(s, open('state.json','w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')
st = gh.inspect('status'); comps = st.get('components',[])
bad = [c for c in comps if c.get('status') not in ('OK',None) and c.get('name')!='Load']
print('NON-OK(mine):', json.dumps(bad, ensure_ascii=False))
print('div  :', json.dumps(gh.inspect('outputs', id=div), ensure_ascii=False)[:200])
print('round:', json.dumps(gh.inspect('outputs', id=rnd), ensure_ascii=False)[:300])
print('sub  :', json.dumps(gh.inspect('outputs', id=sub), ensure_ascii=False)[:200])
print('posts:', json.dumps(gh.inspect('geometry', id=posts), ensure_ascii=False)[:600])
