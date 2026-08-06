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

"""Direct driver for the Cordyceps Grasshopper MCP (JSON-RPC over HTTP).
Scratch tooling — not part of the deliverable. See Prompt1.md for the build spec.
"""
import urllib.request
import json
import os
import shutil
import sys
import tempfile

URL = "http://127.0.0.1:26929/mcp"
_id = 0

def call(name, arguments, timeout=180):
    global _id
    _id += 1
    payload = {"jsonrpc": "2.0", "method": "tools/call",
               "params": {"name": name, "arguments": arguments}, "id": _id}
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    # 180 s, not 60: the FIRST touch of a Python 3 Script component blocks Rhino for
    # ~2 min while the CPython runtime bootstraps, and a timed-out call may still have
    # been applied — which is far messier to recover from than simply waiting.
    # Raise `timeout` for calls that legitimately block longer (a raytraced render
    # waiting on passes) — the HTTP timeout must exceed the tool's own `timeout`,
    # otherwise urlopen gives up while Rhino is still happily rendering.
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = json.loads(res.read().decode("utf-8"))
    if "error" in data:
        return {"_rpc_error": data["error"]}
    result = data.get("result", {})
    content = result.get("content", [])
    if content and "text" in content[0]:
        text = content[0]["text"]
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = text
        if result.get("isError"):
            return {"_isError": True, "content": parsed}
        return parsed
    return result

# convenience wrappers
def canvas(action, **kw):   return call("gh_canvas", {"action": action, **kw})
def wire(action, **kw):     return call("gh_wire", {"action": action, **kw})
def doc(action, **kw):      return call("gh_document", {"action": action, **kw})
def inspect(action="status", **kw): return call("gh_inspect", {"action": action, **kw})
def script(action, **kw):   return call("gh_script", {"action": action, **kw})


# --- reading a component's preview state -------------------------------------
# The MCP surface can only WRITE it: gh_canvas action='preview' is set-only, and
# 'info', 'get' and 'list' report no hidden/preview flag (checked 2026-08-05,
# including every gh_canvas action='help' entry and all gh://docs resources).
# So the read goes around the tool surface: rhino_scene action='script' runs a
# Rhino command macro, and -_RunPythonScript gets us into RhinoCommon, from where
# Grasshopper's own object model is one assembly reference away. The probe hands
# its answer back through a temp file, because a command macro has no return value.
#
# The probe body must stay pure ASCII. -_RunPythonScript runs IronPython 2, which
# refuses a source file with non-ASCII bytes and no encoding line — and it refuses it
# with a MODAL dialog, which freezes Rhino AND the MCP bridge until someone clicks OK.
# A single em dash in a comment cost 10 minutes that way. The write below therefore
# encodes as ASCII on purpose: better a local UnicodeEncodeError than a frozen Rhino.
_PREVIEW_PROBE = '''import json, System, clr
clr.AddReference("Grasshopper")
import Grasshopper
out = {}
try:
    doc = Grasshopper.Instances.ActiveCanvas.Document
    obj = doc.FindObject(System.Guid("%(guid)s"), True) if doc else None
    if obj is None:
        out["error"] = "component %(guid)s not found in the active document"
    else:
        out["nickname"] = str(obj.NickName)
        # IGH_PreviewObject.Hidden - raises for objects without a preview
        # (sliders, panels), which is reported rather than silently answered.
        out["hidden"] = bool(obj.Hidden)
except Exception as e:
    out["error"] = repr(e)
f = open("%(out)s", "w")
f.write(json.dumps(out))
f.close()
'''


def preview_is_on(component_id, timeout=180):
    """True when the component's Grasshopper preview is VISIBLE.

    Note the polarity: Grasshopper stores the inverse (`IGH_PreviewObject.Hidden`,
    where True means preview OFF). This function returns the un-inverted answer, so
    it can be compared directly against the `enabled` argument of
    gh_canvas action='preview'.

    Raises RuntimeError if the component is missing or has no preview at all —
    a component whose state cannot be read must not silently look like "off".
    """
    tmp = tempfile.mkdtemp(prefix="gh_preview_")
    try:
        # Forward slashes throughout: the path is pasted into both a Rhino command
        # macro and a Python string literal, and backslashes would be eaten by one
        # or the other.
        probe = os.path.join(tmp, "probe.py").replace("\\", "/")
        out = os.path.join(tmp, "out.json").replace("\\", "/")
        with open(probe, "w", encoding="ascii") as f:
            f.write(_PREVIEW_PROBE % {"guid": component_id, "out": out})
        r = call("rhino_scene",
                 {"action": "script", "cmd": '_-RunPythonScript ("%s")' % probe},
                 timeout=timeout)
        if not r.get("success"):
            raise RuntimeError("RunPythonScript failed: %r" % (r,))
        if not os.path.exists(out):
            # The macro ran but the probe never got to write: Grasshopper not
            # loaded, or no document open.
            raise RuntimeError("preview probe produced no answer for %s" % component_id)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        if "hidden" not in data:
            raise RuntimeError("preview probe failed for %s: %s"
                               % (component_id, data.get("error", data)))
        return not data["hidden"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    # ad-hoc: python gh.py <tool> <action> [json-args]
    tool = sys.argv[1] if len(sys.argv) > 1 else "gh_canvas"
    action = sys.argv[2] if len(sys.argv) > 2 else "list"
    extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    print(json.dumps(call(tool, {"action": action, **extra}), indent=2, ensure_ascii=False)[:4000])
