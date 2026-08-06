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

import gh, json

G = {
 'Point':'3581f42a-9592-4549-bd6b-1c0fc39d067b',
 'Line':'4c4e56eb-2f04-43f9-95a3-cc46a14f495a',
 'UnitZ':'9103c240-a6a9-4223-9b42-dbd19bf38e2b',
 'Move':'e9eb1dcf-92f6-4d4d-84ae-96222d60f56b',
}

def add(t, x, y, nick=None, **kw):
    r = gh.canvas('add', type=G.get(t,t), x=x, y=y, **({'nickname':nick} if nick else {}), **kw)
    assert r.get('success'), f'ADD {t} failed: {r}'
    return r['id']

def const(v, x, y, nick=None):
    r = gh.canvas('constant', value=str(v), x=x, y=y, **({'nickname':nick} if nick else {}))
    assert r.get('success'), f'CONST {v} failed: {r}'
    return r['id']

def slider(nick, mn, mx, val, dec, x, y):
    r = gh.canvas('add', type='slider', x=x, y=y, nickname=nick, min=mn, max=mx, value=val, decimals=dec)
    assert r.get('success'), f'SLIDER {nick} failed: {r}'
    return r['id']

def w(s, sp, t, tp):
    r = gh.wire('connect', sourceId=s, sourceParam=sp, targetId=t, targetParam=tp)
    if not r.get('success'): print('  WIRE FAIL', sp, tp, r)

gh.doc('solver', enabled=False)

# --- Phase 0: base line ---
c0    = const(0,    -50, 300)
cRun  = const(4000, -50, 360)
cRise = const(2000, -50, 420)
ptA = add('Point', 130, 300, '_ptA')
ptB = add('Point', 130, 420, '_ptB')
for tp in (0,1,2): w(c0,0,ptA,tp)              # A = {0,0,0}
w(cRun,0,ptB,0); w(c0,0,ptB,1); w(cRise,0,ptB,2)  # B = {4000,0,2000}
line = add('Line', 320, 360, 'Treppenbasislinie')
w(ptA,0,line,0); w(ptB,0,line,1)

# --- Phase 1: height sliders + moves ---
gel = slider('Gelaenderhoehe', 800, 1400, 1000, 0, 300, 520)
unt = slider('Untergurt-Abstand', 0, 300, 100, 0, 300, 580)
uz1 = add('UnitZ', 500, 520, '_uzHand')
uz2 = add('UnitZ', 500, 580, '_uzUnter')
w(gel,0,uz1,0); w(unt,0,uz2,0)
mv1 = add('Move', 680, 360, 'Handlauflinie')
mv2 = add('Move', 680, 460, 'Untergurtlinie')
w(line,0,mv1,0); w(uz1,0,mv1,1)
w(line,0,mv2,0); w(uz2,0,mv2,1)

state = dict(c0=c0, cRun=cRun, cRise=cRise, ptA=ptA, ptB=ptB, line=line,
             gel=gel, unt=unt, uz1=uz1, uz2=uz2, handrail=mv1, untergurt=mv2)
json.dump(state, open('state.json','w'), indent=1)

gh.doc('solver', enabled=True)
gh.doc('recompute')

st = gh.inspect('status')
comps = st.get('components', st) if isinstance(st, dict) else st
bad = [c for c in comps if c.get('status','OK') not in ('OK', None)] if isinstance(comps, list) else comps
print('STATE:', json.dumps(state, indent=1))
print('NON-OK:', json.dumps(bad, ensure_ascii=False, indent=1))
# verify handrail Z translation
gi = gh.canvas('get', id=mv1)
print('HANDRAIL get:', json.dumps(gi, ensure_ascii=False)[:600])
