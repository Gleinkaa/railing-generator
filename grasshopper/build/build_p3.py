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
FLAT='f80cfe18-9510-4b89-8301-8e58faf423bb'
gh.doc('solver', enabled=False)

shat = bh.add('Shatter', 900, 780, '_ShatterUnter')
Lseg = bh.add('Length', 1080, 780, '_SegLen')
fsl  = bh.slider('Fuellstab-Abstand', 50, 132, 115, 0, 900, 900)
div3 = bh.add('Division', 1240, 800, '_Seg/Abstand')
rnd3 = bh.add('Round', 1400, 800, '_Round3')
dc3  = bh.add('DivideCurve', 1560, 780, '_TeilerFuell')
flat = bh.add(FLAT, 1740, 780, '_Flatten')
ctol = bh.const(0.1, 1740, 860, '_tol')
cull = bh.add('CullDup', 1900, 780, '_CullDup')
uzf  = bh.add('UnitZ', 1900, 900, '_ZdirFuell')
fill = bh.add('LineSDL', 2080, 780, 'Fuellstaebe')

bh.wire(s['untergurt'],'Geometry', shat,'Curve')
bh.wire(s['dc'],'Parameters', shat,'Parameters')
bh.wire(shat,'Segments', Lseg,'Curve')
bh.wire(Lseg,'Length', div3,'A')
bh.wire(fsl,0, div3,'B')
bh.wire(div3,'Result', rnd3,0)
bh.wire(shat,'Segments', dc3,'Curve')
bh.wire(rnd3,'Ceiling', dc3,'Count')
bh.wire(dc3,'Points', flat,'Tree')
bh.wire(flat,'Tree', cull,'Points')
bh.wire(ctol,0, cull,'Tolerance')
bh.wire(cull,'Points', fill,'Start')
bh.wire(uzf,'Unit vector', fill,'Direction')
bh.wire(s['sub'],'Result', fill,'Length')

s.update(shat=shat, Lseg=Lseg, fsl=fsl, div3=div3, rnd3=rnd3, dc3=dc3, flat=flat, cull=cull, uzf=uzf, fill=fill)
json.dump(s, open('state.json','w'), indent=1)

gh.doc('solver', enabled=True); gh.doc('recompute')
st = gh.inspect('status'); comps = st.get('components',[])
bad = [c for c in comps if c.get('status') not in ('OK',None) and c.get('name')!='Load']
print('NON-OK(mine):', json.dumps(bad, ensure_ascii=False))
print('seg lengths:', json.dumps(gh.inspect('outputs', id=Lseg), ensure_ascii=False)[:300])
print('round3 ceil:', json.dumps(gh.inspect('outputs', id=rnd3), ensure_ascii=False)[:260])
fo = gh.inspect('geometry', id=fill)
outs = fo.get('outputs',[{}])[0]
print('fill count:', outs.get('count'))
dco = gh.inspect('outputs', id=dc3).get('outputs',[{}])[0]
print('pre-cull points count:', dco.get('count'), 'branches:', dco.get('branches'))
cu = gh.inspect('outputs', id=cull).get('outputs',[{}])[0]
print('post-cull points count:', cu.get('count'))
