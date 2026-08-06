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

"""Steel-profile catalog for the railing generator — single source of truth for
switchable profiles and their BOM linear masses (kg/m).

Source: Research/profile_catalog.md (Wave-0 CatalogA). The 0-based row index within
each role list is the value the corresponding Grasshopper selector slider carries
(Handlauf-Profil / Posten-Profil / Fuellstab-Profil). Geometry and mass are pulled
from the SAME index so the swept solid and the BOM can never disagree.

section_type -> what the generator sweeps along the element centerline:
  'round' -> a Circle of diameter `dia`            (dx unused)
  'rect'  -> a Rectangle dx x dia (outer dims)      (SHS/RHS/square bar)
  'flat'  -> a Rectangle dx x dia                   (Flachstahl / flat bar)
`wall` affects kg/m only, never the drawn footprint (representative solids).

kg/m provenance (rho = 7850 kg/m^3):
  solids/flats: area_mm2 * 7.85e-6
  hollow:       sharp-corner/thin-wall value (reproduces anchors 1.993 / 2.386).
  NOTE: real EN 10219 nominal masses run ~3-5% lower (rounded corners). If the
  shop steel list quotes EN nominal masses, swap the kg_per_m column; geometry rows
  are unaffected. See Research/profile_catalog.md.

Each row: (name, section_type, dx, dia, wall, kg_per_m)  -- dx/wall may be None.
"""

# role -> ordered list of profile rows (index 0 = default / most common)
HANDRAIL = [
    ("Rundrohr 42.4x2.0", "round", None, 42.4, 2.0, 1.993),  # 0 default
    ("Rundrohr 33.7x2.0", "round", None, 33.7, 2.0, 1.564),  # 1
    ("Rundrohr 48.3x2.6", "round", None, 48.3, 2.6, 2.930),  # 2
    ("SHS 40x40x2.0",     "rect", 40,   40,   2.0, 2.386),   # 3
    ("RHS 40x20x2.0",     "rect", 40,   20,   2.0, 1.758),   # 4
    ("Flachstahl 40x10",  "flat", 40,   10,   None, 3.140),  # 5
    ("Flachstahl 50x10",  "flat", 50,   10,   None, 3.925),  # 6
]

POST = [
    ("SHS 40x40x2.0",     "rect", 40,   40,   2.0, 2.386),   # 0 default
    ("RHS 50x30x2.0",     "rect", 50,   30,   2.0, 2.386),   # 1
    ("SHS 50x50x2.0",     "rect", 50,   50,   2.0, 3.014),   # 2
    ("RHS 60x40x3.0",     "rect", 60,   40,   3.0, 4.427),   # 3
    ("Rundrohr 42.4x2.0", "round", None, 42.4, 2.0, 1.993),  # 4
    ("Flachstahl 50x10",  "flat", 50,   10,   None, 3.925),  # 5
    ("Flachstahl 60x10",  "flat", 60,   10,   None, 4.710),  # 6
    ("Flachstahl 80x10",  "flat", 80,   10,   None, 6.280),  # 7
]

INFILL = [
    ("Rundstahl 12",      "round", None, 12,   None, 0.888),  # 0 default
    ("Rundstahl 10",      "round", None, 10,   None, 0.617),  # 1
    ("Rundstahl 14",      "round", None, 14,   None, 1.208),  # 2
    ("Flachstahl 30x5",   "flat", 30,   5,    None, 1.178),   # 3
    ("Flachstahl 40x8",   "flat", 40,   8,    None, 2.512),   # 4 (diagonal bar)
    ("Vierkant 12x12",    "rect", 12,   12,   None, 1.130),   # 5
    ("RHS 40x20x2.0",     "rect", 40,   20,   2.0, 1.758),    # 6
]

# Untergurt = the bottom rail the vertical infill stands on. It is a structural chord,
# not a handrail, so the catalog leads with flat bar / SHS (the flat-bar look) rather
# than round tube. Same six columns as the other roles.
UNTERGURT = [
    ("Flachstahl 40x10",  "flat", 40,   10,   None, 3.140),   # 0 default
    ("Flachstahl 50x10",  "flat", 50,   10,   None, 3.925),   # 1
    ("Flachstahl 60x10",  "flat", 60,   10,   None, 4.710),   # 2
    ("SHS 40x40x2.0",     "rect", 40,   40,   2.0, 2.386),    # 3
    ("RHS 40x20x2.0",     "rect", 40,   20,   2.0, 1.758),    # 4
    ("Rundrohr 33.7x2.0", "round", None, 33.7, 2.0, 1.564),   # 5
    ("Rundstahl 12",      "round", None, 12,   None, 0.888),  # 6
]

ROLES = {"handrail": HANDRAIL, "post": POST, "infill": INFILL,
         "untergurt": UNTERGURT}

# index of the flat 40x8 bar in INFILL — the default decorative diagonal profile
DIAGONAL_INFILL_INDEX = 4


def _col(rows, i):
    return [r[i] for r in rows]

def section_flags(role):
    """Per-row int flag for the GH Stream Gate: 0=round, 1=rect/flat (rectangle)."""
    return [0 if r[1] == "round" else 1 for r in ROLES[role]]

def dx_list(role):
    """dim_x for the rectangle footprint; round rows fall back to dia (unused by gate)."""
    return [(r[2] if r[2] is not None else r[3]) for r in ROLES[role]]

def dia_list(role):
    """diameter (round) / dim_y (rect+flat)."""
    return _col(ROLES[role], 3)

def kgm_list(role):
    return _col(ROLES[role], 5)

def names(role):
    return _col(ROLES[role], 0)


if __name__ == "__main__":
    # sanity: print the parallel lists a build_p6 driver would feed into List Item
    for role in ROLES:
        print(f"[{role}] n={len(ROLES[role])}")
        print("  names  :", names(role))
        print("  secflag:", section_flags(role))
        print("  dx     :", dx_list(role))
        print("  dia    :", dia_list(role))
        print("  kg/m   :", kgm_list(role))
