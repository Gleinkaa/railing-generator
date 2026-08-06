# Steel Profile Catalog — Parametric Railing Generator

Austrian market, feeding a Grasshopper generator. An operator
selects a profile per element role via a **0-based integer index slider**. The
**row index is the selector value** — profiles are ordered default / most-common
first. The generator draws the profile's cross-section footprint and sweeps it
along the element centerline; the BOM multiplies each element's length by the
exact linear mass (`kg_per_m`) of the chosen profile.

## section_type → geometry mapping (what the generator draws)

The generator sweeps a **representative solid** along the centerline. Only the
outer footprint matters for the swept geometry — wall thickness affects mass
only, never the drawn shape.

| section_type | meaning | footprint the generator draws |
|---|---|---|
| `round` | circular tube **or** solid round bar | a **circle** of diameter `dim_y_or_dia_mm` |
| `rect`  | square/rectangular hollow section (SHS/RHS) **or** solid square bar | a **rectangle** `dim_x_mm × dim_y_or_dia_mm` (outer dims) |
| `flat`  | Flachstahl / flat bar (solid rectangular) | a **rectangle** `dim_x_mm × dim_y_or_dia_mm` |

For `round` rows `dim_x_mm` is unused (`null`); the diameter lives in
`dim_y_or_dia_mm`. For solid bars `wall_mm` is `null` (no wall).

## kg/m provenance

Two regimes, both at steel density **ρ = 7850 kg/m³**:

**Solid bars & flat bars** — computed directly:

```
kg_per_m = area_mm² × 7.85e-6         (= area_mm² × 1e-6 m²/mm² × 7850 kg/m³)
  round bar:   area = π/4 · d²
  square bar:  area = a²
  flat bar:    area = width · thickness
```

Verification (matches the brief):
- Ø12 round bar: π/4·12² = 113.10 mm² → 113.10e-6 × 7850 = **0.888 kg/m** ✓
- Flat 40×10: 400 mm² → 400e-6 × 7850 = **3.140 kg/m** ✓

**Hollow sections (SHS/RHS/round tube)** — thin-wall / sharp-corner catalog value:

```
round tube:  area = π · t · (D − t)
SHS/RHS:     area = (b·h) − ((b−2t)·(h−2t))
kg_per_m   = area_mm² × 7.85e-6
```

This convention reproduces the brief's anchor values exactly — Ø42.4×2.0 →
π·2·40.4 = 253.84 mm² → **1.993 kg/m**, and SHS 40×40×2.0 → 1600−1296 = 304 mm²
→ **2.386 kg/m**. Note: the true **EN 10219** nominal masses are ~3–5 % lower
because real cold-formed sections have rounded corners (e.g. EN nominal
SHS 40×40×2.0 ≈ 2.31, RHS 60×40×3.0 ≈ 4.20, RHS 50×30×2.0 ≈ 2.31 kg/m). The
sharp-corner value is used here so the mass is consistent with the sharp-cornered
representative solid the generator actually draws, and so the given anchors stay
exact. If the shop's steel list quotes EN nominal masses, substitute those in the
`kg_per_m` column — geometry rows are unaffected.

---

## Role 1 — HANDRAIL (Handlauf)

| index | name | section_type | dim_x_mm | dim_y_or_dia_mm | wall_mm | kg_per_m |
|---|---|---|---|---|---|---|
| 0 | Rundrohr 42.4x2.0 | round | — | 42.4 | 2.0 | 1.993 |
| 1 | Rundrohr 33.7x2.0 | round | — | 33.7 | 2.0 | 1.564 |
| 2 | Rundrohr 48.3x2.6 | round | — | 48.3 | 2.6 | 2.930 |
| 3 | SHS 40x40x2.0 | rect | 40 | 40 | 2.0 | 2.386 |
| 4 | RHS 40x20x2.0 | rect | 40 | 20 | 2.0 | 1.758 |
| 5 | Flachstahl 40x10 | flat | 40 | 10 | — | 3.140 |
| 6 | Flachstahl 50x10 | flat | 50 | 10 | — | 3.925 |

## Role 2 — POST (Pfosten/Posten)

| index | name | section_type | dim_x_mm | dim_y_or_dia_mm | wall_mm | kg_per_m |
|---|---|---|---|---|---|---|
| 0 | SHS 40x40x2.0 | rect | 40 | 40 | 2.0 | 2.386 |
| 1 | RHS 50x30x2.0 | rect | 50 | 30 | 2.0 | 2.386 |
| 2 | SHS 50x50x2.0 | rect | 50 | 50 | 2.0 | 3.014 |
| 3 | RHS 60x40x3.0 | rect | 60 | 40 | 3.0 | 4.427 |
| 4 | Rundrohr 42.4x2.0 | round | — | 42.4 | 2.0 | 1.993 |
| 5 | Flachstahl 50x10 | flat | 50 | 10 | — | 3.925 |
| 6 | Flachstahl 60x10 | flat | 60 | 10 | — | 4.710 |
| 7 | Flachstahl 80x10 | flat | 80 | 10 | — | 6.280 |

## Role 3 — INFILL (Füllstab)

| index | name | section_type | dim_x_mm | dim_y_or_dia_mm | wall_mm | kg_per_m |
|---|---|---|---|---|---|---|
| 0 | Rundstahl 12 | round | — | 12 | — | 0.888 |
| 1 | Rundstahl 10 | round | — | 10 | — | 0.617 |
| 2 | Rundstahl 14 | round | — | 14 | — | 1.208 |
| 3 | Flachstahl 30x5 | flat | 30 | 5 | — | 1.178 |
| 4 | Flachstahl 40x8 | flat | 40 | 8 | — | 2.512 |
| 5 | Vierkant 12x12 | rect | 12 | 12 | — | 1.130 |
| 6 | RHS 40x20x2.0 | rect | 40 | 20 | 2.0 | 1.758 |

---

## Per-row mass check (solids & flat bars)

| name | area_mm² | ×7.85e-6 | kg_per_m |
|---|---|---|---|
| Rundstahl 12 | π/4·12² = 113.10 | | 0.888 |
| Rundstahl 10 | π/4·10² = 78.54 | | 0.617 |
| Rundstahl 14 | π/4·14² = 153.94 | | 1.208 |
| Vierkant 12x12 | 144 | | 1.130 |
| Flachstahl 30x5 | 150 | | 1.178 |
| Flachstahl 40x8 | 320 | | 2.512 |
| Flachstahl 40x10 | 400 | | 3.140 |
| Flachstahl 50x10 | 500 | | 3.925 |
| Flachstahl 60x10 | 600 | | 4.710 |
| Flachstahl 80x10 | 800 | | 6.280 |

Hollow-section masses (sharp-corner): Ø42.4×2.0 = 1.993, Ø33.7×2.0 = 1.564,
Ø48.3×2.6 = 2.930, SHS 40×40×2.0 = 2.386, RHS 40×20×2.0 = 1.758,
RHS 50×30×2.0 = 2.386, SHS 50×50×2.0 = 3.014, RHS 60×40×3.0 = 4.427.

---

```json
[
  { "index": 0, "role": "handrail", "name": "Rundrohr 42.4x2.0", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 42.4, "wall_mm": 2.0, "kg_per_m": 1.993 },
  { "index": 1, "role": "handrail", "name": "Rundrohr 33.7x2.0", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 33.7, "wall_mm": 2.0, "kg_per_m": 1.564 },
  { "index": 2, "role": "handrail", "name": "Rundrohr 48.3x2.6", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 48.3, "wall_mm": 2.6, "kg_per_m": 2.930 },
  { "index": 3, "role": "handrail", "name": "SHS 40x40x2.0", "section_type": "rect", "dim_x_mm": 40, "dim_y_or_dia_mm": 40, "wall_mm": 2.0, "kg_per_m": 2.386 },
  { "index": 4, "role": "handrail", "name": "RHS 40x20x2.0", "section_type": "rect", "dim_x_mm": 40, "dim_y_or_dia_mm": 20, "wall_mm": 2.0, "kg_per_m": 1.758 },
  { "index": 5, "role": "handrail", "name": "Flachstahl 40x10", "section_type": "flat", "dim_x_mm": 40, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 3.140 },
  { "index": 6, "role": "handrail", "name": "Flachstahl 50x10", "section_type": "flat", "dim_x_mm": 50, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 3.925 },

  { "index": 0, "role": "post", "name": "SHS 40x40x2.0", "section_type": "rect", "dim_x_mm": 40, "dim_y_or_dia_mm": 40, "wall_mm": 2.0, "kg_per_m": 2.386 },
  { "index": 1, "role": "post", "name": "RHS 50x30x2.0", "section_type": "rect", "dim_x_mm": 50, "dim_y_or_dia_mm": 30, "wall_mm": 2.0, "kg_per_m": 2.386 },
  { "index": 2, "role": "post", "name": "SHS 50x50x2.0", "section_type": "rect", "dim_x_mm": 50, "dim_y_or_dia_mm": 50, "wall_mm": 2.0, "kg_per_m": 3.014 },
  { "index": 3, "role": "post", "name": "RHS 60x40x3.0", "section_type": "rect", "dim_x_mm": 60, "dim_y_or_dia_mm": 40, "wall_mm": 3.0, "kg_per_m": 4.427 },
  { "index": 4, "role": "post", "name": "Rundrohr 42.4x2.0", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 42.4, "wall_mm": 2.0, "kg_per_m": 1.993 },
  { "index": 5, "role": "post", "name": "Flachstahl 50x10", "section_type": "flat", "dim_x_mm": 50, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 3.925 },
  { "index": 6, "role": "post", "name": "Flachstahl 60x10", "section_type": "flat", "dim_x_mm": 60, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 4.710 },
  { "index": 7, "role": "post", "name": "Flachstahl 80x10", "section_type": "flat", "dim_x_mm": 80, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 6.280 },

  { "index": 0, "role": "infill", "name": "Rundstahl 12", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 12, "wall_mm": null, "kg_per_m": 0.888 },
  { "index": 1, "role": "infill", "name": "Rundstahl 10", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 10, "wall_mm": null, "kg_per_m": 0.617 },
  { "index": 2, "role": "infill", "name": "Rundstahl 14", "section_type": "round", "dim_x_mm": null, "dim_y_or_dia_mm": 14, "wall_mm": null, "kg_per_m": 1.208 },
  { "index": 3, "role": "infill", "name": "Flachstahl 30x5", "section_type": "flat", "dim_x_mm": 30, "dim_y_or_dia_mm": 5, "wall_mm": null, "kg_per_m": 1.178 },
  { "index": 4, "role": "infill", "name": "Flachstahl 40x8", "section_type": "flat", "dim_x_mm": 40, "dim_y_or_dia_mm": 8, "wall_mm": null, "kg_per_m": 2.512 },
  { "index": 5, "role": "infill", "name": "Vierkant 12x12", "section_type": "rect", "dim_x_mm": 12, "dim_y_or_dia_mm": 12, "wall_mm": null, "kg_per_m": 1.130 },
  { "index": 6, "role": "infill", "name": "RHS 40x20x2.0", "section_type": "rect", "dim_x_mm": 40, "dim_y_or_dia_mm": 20, "wall_mm": 2.0, "kg_per_m": 1.758 }
]
```
