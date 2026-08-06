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

"""Build helpers on top of gh.py: name-based wiring, safe add."""

import gh
import json

G = {
    "Point": "3581f42a-9592-4549-bd6b-1c0fc39d067b",
    "Line": "4c4e56eb-2f04-43f9-95a3-cc46a14f495a",
    "UnitZ": "9103c240-a6a9-4223-9b42-dbd19bf38e2b",
    "Move": "e9eb1dcf-92f6-4d4d-84ae-96222d60f56b",
    "Length": "c75b62fa-0a33-4da7-a5bd-03fd0068fd93",
    "Division": "9c85271f-89fa-4e9f-9f4a-d75802120ccc",
    "Multiplication": "ce46b74e-00c9-43c4-805a-193b69ea4a11",
    "Subtraction": "9c007a04-d0d9-48e4-9da3-9ba142bc4d46",
    "Round": "a50c4a3b-0177-4c91-8556-db95de6c56c8",
    "DivideCurve": "2162e72e-72fc-4bf8-9459-d4d82fa8aa14",
    "LineSDL": "4c619bc9-39fd-4717-82a6-1e07ea237bbe",
    "Shatter": "2ad2a4d4-3de1-42f6-a4b8-f71835f35710",
    "CullDup": "6eaffbb2-3392-441a-8556-2dc126aa8910",
    "Pipe": "c277f778-6fdf-4890-8f78-347efb23c406",
    "Rectangle": "d93100b6-d50b-40b2-831a-814659dc38e3",
    "PerpFrame": "69f3e5ee-4770-44b3-8851-ae10ae555398",
    "Extrude": "962034e9-cc27-4394-afc4-5c16e3447cf9",
    "ConstructDomain": "d1a28e95-cf96-4936-bf34-8bf142d731bf",
    "MassAddition": "5b850221-b527-4bd6-8c62-e94168cd6efa",
    "Concatenate": "2013e425-8713-42e2-a661-b57e78840337",
    "Panel": "59e0b89a-e487-49f8-bab8-b5bab16be14c",
}


def add(t, x, y, nick=None, **kw):
    r = gh.canvas(
        "add", type=G.get(t, t), x=x, y=y, **({"nickname": nick} if nick else {}), **kw
    )
    assert r.get("success"), f"ADD {t} failed: {r}"
    return r["id"]


def const(v, x, y, nick=None):
    r = gh.canvas(
        "constant", value=str(v), x=x, y=y, **({"nickname": nick} if nick else {})
    )
    assert r.get("success"), f"CONST {v} failed: {r}"
    return r["id"]


def slider(nick, mn, mx, val, dec, x, y):
    r = gh.canvas(
        "add",
        type="slider",
        x=x,
        y=y,
        nickname=nick,
        min=mn,
        max=mx,
        value=val,
        decimals=dec,
    )
    assert r.get("success"), f"SLIDER {nick} failed: {r}"
    return r["id"]


def io(cid):
    info = gh.canvas("info", id=cid)
    return info.get("inputs", []), info.get("outputs", [])


def _idx(ports, key):
    key = key.lower()
    for i, p in enumerate(ports):
        if p.get("nickname", "").lower() == key or p.get("name", "").lower() == key:
            return i
    for i, p in enumerate(ports):
        if key in p.get("name", "").lower() or key in p.get("nickname", "").lower():
            return i
    raise KeyError(f"port {key!r} not in {[p.get('name') for p in ports]}")


def wire(src, out_key, tgt, in_key):
    _, souts = io(src)
    tins, _ = io(tgt)
    # Params (sliders, panels) report an EMPTY output list, so a name like 'Result'
    # can never resolve against them — they expose exactly one output, at index 0.
    if isinstance(out_key, int):
        sp = out_key
    elif not souts:
        sp = 0
    else:
        sp = _idx(souts, out_key)
    tp = _idx(tins, in_key) if not isinstance(in_key, int) else in_key
    r = gh.wire("connect", sourceId=src, sourceParam=sp, targetId=tgt, targetParam=tp)
    if not r.get("success"):
        print("  WIRE FAIL", out_key, "->", in_key, r)
    return r


def ports(cid, label=""):
    ins, outs = io(cid)
    print(
        f"  {label}: IN {[p.get('name') for p in ins]} | OUT {[p.get('name') for p in outs]}"
    )


# ---------------------------------------------------------------- Phase 6+ helpers

_found = {}


def find(name):
    """Resolve a component display name -> GUID via the registry (cached).

    Never hard-code GUIDs for components outside G: the registry is the source of
    truth (Prompt1.md, build sequence rule 1). Prefers an exact case-insensitive
    name match over the first fuzzy search hit.
    """
    if name in G:
        return G[name]
    if name in _found:
        return _found[name]
    r = gh.canvas("search", query=name)
    # Cordyceps returns hits under 'components'; keep the other shapes as fallbacks.
    hits = r.get("components") or r.get("results") or (r if isinstance(r, list) else [])
    assert hits, f"SEARCH {name!r} returned nothing: {r}"
    # Never take a deprecated variant when a live one exists — GH ships deprecated
    # twins (e.g. Stream Filter) whose port layout differs from the current one.
    pool = [h for h in hits if not h.get("deprecated")] or hits
    exact = [h for h in pool if h.get("name", "").lower() == name.lower()]
    guid = (exact or pool)[0].get("guid")
    assert guid, f"SEARCH {name!r} gave no guid: {pool[:3]}"
    _found[name] = guid
    return guid


def addf(name, x, y, nick=None, **kw):
    """add() but resolving the type by display name through the registry."""
    return add(find(name), x, y, nick, **kw)


def sources(cid, in_key):
    """(source_id, source_param) pairs currently feeding an input.

    canvas 'info' reports only a sourceCount per input — never the source ids — so
    the connection list from gh_wire is the only way to actually see them. Reading
    'info' here silently returned "nothing connected" for every input, which made
    clear_input() a no-op (verified live 2026-07-25).
    """
    ins, _ = io(cid)
    p = ins[_idx(ins, in_key) if not isinstance(in_key, int) else in_key]
    want = (p.get("name") or "").lower()
    out = []
    for c in gh.wire("list", componentId=cid).get("connections", []):
        t = c.get("target", {})
        param = t.get("param")
        param = "" if param is None else str(param)
        if t.get("componentId") == cid and param.lower() == want:
            s = c.get("source", {})
            out.append((s.get("componentId"), s.get("param")))
    return out


def clear_input(cid, in_key):
    """Disconnect everything feeding an input, and verify it actually happened.

    Required whenever an existing input is being RE-pointed: gh_wire connect ADDS a
    source, it does not replace one. Wiring the catalog kg/m onto a Multiplication
    that still holds its hardcoded density constant would silently sum both.
    """
    src = sources(cid, in_key)
    ins, _ = io(cid)
    tp = _idx(ins, in_key) if not isinstance(in_key, int) else in_key
    if not src:
        print(f"  clear_input({in_key}): nothing connected")
        return 0
    for sid, sparam in src:
        _, souts = io(sid)
        try:
            # Params (Panel, slider, ...) report an empty output list — they expose a
            # single output, so index 0 is the only valid source param for them.
            sp = _idx(souts, sparam) if (sparam and souts) else 0
        except KeyError:
            sp = 0
        r = gh.wire(
            "disconnect", sourceId=sid, sourceParam=sp, targetId=cid, targetParam=tp
        )
        if not r.get("success"):
            print(f"  ! disconnect {sid}.{sparam} -> {in_key} failed: {r}")
    left = sources(cid, in_key)
    assert not left, f"clear_input({in_key}) on {cid}: still connected to {left}"
    print(f"  clear_input({in_key}): removed {len(src)}")
    return len(src)


def by_nick(nick):
    """Find a live component id by its canvas nickname (for re-pointing wires into
    components that earlier phases created without persisting their id).

    Falls back to the canvas listing because gh_inspect 'status' reports COMPONENTS
    only: Params — sliders, Panels, the constants the phase scripts scatter around —
    are invisible to it and would otherwise raise KeyError here.
    """
    for c in gh.inspect("status").get("components", []):
        if c.get("nickname") == nick or c.get("name") == nick:
            return c.get("id")
    hits = [
        c
        for c in gh.canvas("list", limit=1000).get("components", [])
        if c.get("nickname") == nick
    ]
    if len(hits) == 1:
        return hits[0]["id"]
    if hits:
        raise KeyError(
            f"{nick!r} is ambiguous: {len(hits)} objects carry that nickname"
        )
    raise KeyError(f"no component or param nicknamed {nick!r} on the canvas")


def slider_id(nick):
    """Id of the one Number Slider with this nickname.

    Deliberately narrower than by_nick(): a typo'd or duplicated slider nickname must
    fail here rather than silently resolve to some other object and get `set` to a
    value that drives unrelated geometry.
    """
    hits = [
        c
        for c in gh.canvas("list", typeFilter="Number Slider", limit=200).get(
            "components", []
        )
        if c.get("nickname") == nick
    ]
    if len(hits) != 1:
        raise KeyError(f"slider {nick!r}: expected exactly 1 match, found {len(hits)}")
    return hits[0]["id"]


def count(cid, out=0):
    """Item count of one output — raising rather than defaulting on anything missing.

    Deliberately NOT the tolerant .get() pattern used elsewhere: count() feeds
    `assert solids == centrelines` regression guards, and with a None fallback both
    sides collapse to None, the assert passes, and the guard silently goes green.
    That is the exact silent-failure class behind the clear_input no-op, the
    `souts == 0` collapse, the 41x41 sweep bug and the null-kg BOM bug. Fail loud.
    """
    r = gh.inspect("outputs", id=cid)
    outputs = r.get("outputs")
    if not outputs:
        raise AssertionError(f"count({cid!r}): no outputs in response: {r!r}")
    try:
        entry = outputs[out]
    except IndexError:
        raise AssertionError(
            f"count({cid!r}): output index {out} out of range (len={len(outputs)}): {r!r}"
        )
    value = entry.get("count")
    if value is None:
        raise AssertionError(
            f"count({cid!r}): output[{out}] has no count key: {entry!r}"
        )
    return int(value)


def catalog(columns, x, y, nick):
    """All catalog columns for one role as ONE component, each column a LIST output.

    Verified live 2026-07-25: a multiline Panel does NOT emit one item per line —
    it emits its whole text as a single string item, which would leave every
    downstream List Item indexing into a 1-item list. Cordyceps exposes no
    "Multiline Data" toggle, so the columns come from a Python 3 Script component
    with access='list' outputs instead. Emitting every column from one component
    also keeps the four columns row-aligned by construction.

    `columns` maps output name -> sequence of numbers. Returns the component id;
    wire columns out BY NAME (output 0 is the script's own `out` text stream).
    """
    cid = addf("Python 3 Script", x, y, nick)
    code = "#! python 3\n" + "".join(f"{k} = {list(v)!r}\n" for k, v in columns.items())
    r = gh.script(
        "configure",
        id=cid,
        inputs="[]",
        code=code,
        outputs=json.dumps(
            [{"name": k, "type": "double", "access": "list"} for k in columns]
        ),
    )
    # `configure` can time out while Rhino bootstraps its Python runtime and STILL
    # have applied, so confirm by reading the component back instead of trusting r.
    have = {o.get("name") for o in gh.script("info", id=cid).get("outputs", [])}
    missing = [k for k in columns if k not in have]
    assert not missing, (
        f"catalog {nick}: outputs {missing} missing (have {sorted(have)}), resp={r}"
    )
    return cid


def check_list(cid, out_name, n, label):
    """Assert a catalog column really emits n items (see catalog)."""
    outs = gh.inspect("outputs", id=cid).get("outputs", [])
    match = [o for o in outs if o.get("name") == out_name]
    if not match:
        raise AssertionError(
            f"{label}: no output named {out_name!r} (have {[o.get('name') for o in outs]})"
        )
    got = match[0].get("count")
    if got != n:
        raise AssertionError(
            f"{label}: expected {n} list items, got {got!r}. The script output is not "
            f'emitting a list — check access="list" survived on this output.'
        )
    print(f"  {label}: {got} items OK")
