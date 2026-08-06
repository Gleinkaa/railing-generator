# Subsystem Topology Design — Profile Selector, Mounting, Diagonal Infill

Design document for three new subsystems extending the parametric steel-railing
generator. This is a **paper design**: a later serial build phase follows it exactly
using the `gh` / `bh` driver helpers (name-based `bh.wire`, `bh.add`, `bh.const`,
`bh.slider`). Nothing here is built live.

Conventions honored from the existing build:
- Solver OFF while building; after each phase: solver ON → `recompute` → `gh_inspect status`;
  fix any non-OK component; snapshot before each phase.
- Ports are addressed **by human name** (`bh.wire` auto-resolves name→index via `gh_canvas info`).
- Components NOT in `bh.G` are added by their **Grasshopper display name**; the build phase
  resolves them at build time via `gh_canvas action=search query="<name>"`. Do **not** invent GUIDs.
- All lengths are in **mm** (document units). BOM densities are kg/**m** → every mass path must ÷1000.

---

## 0. Existing graph — anchor points this design wires into

State keys (from `state.json`) and their **output port names** used as wiring sources:

| state key | component | output port to tap | meaning |
|---|---|---|---|
| `treppenbasislinie` / `line` | Line | `Line` | base rake line A→B (0,0,0)→(4000,0,2000) |
| `handrail` | Move | `Geometry` | handrail centerline (base + Z·1000) |
| `untergurt` | Move | `Geometry` | lower chord centerline (base + Z·100) |
| `sub` | Subtraction | `Result` | post height = 900 |
| `dc` | DivideCurve (on untergurt) | `Points`, `Parameters` | post base points (N+1) and their t-values |
| `posts` | LineSDL | `Line` | vertical post centerlines |
| `fill` | LineSDL | `Line` | vertical infill-bar centerlines (CullDup-cleaned) |
| `shat` | Shatter (on untergurt) | `Segments` | per-bay lower-chord segments |
| `kgF/kgH/kgP` | Multiplication | `Result` | per-group kg (density const currently on input B) |

**Refactor targets:** the three hardcoded Phase-4 solids (`pipeH`, `pipeF`, `ext` + supports
`dom`,`pf`,`rect`,`uzE`) are **replaced** by three instances of the Subsystem-1 macro. The three
Phase-5 density constants (0.888 / 1.993 / 2.386) are **replaced** by the catalog `kg_per_m`
List-Item outputs (Subsystem 1) so geometry and mass share one index.

### Compliance invariants (from `docs/SPEC.md` / OIB RL 4)
- Vertical infill: clear gap between adjacent bar **surfaces** < 120 mm. For Ø12 bar → max
  center spacing 132 mm (existing `Fuellstab-Abstand` slider caps at 132).
- The **120 mm test sphere** must not pass through the field or beneath the lower chord
  (lower chord kept at +100 mm < 120).
- Diagonal mode must preserve the same "no 120 mm sphere passes" guarantee by construction.

---

## 1. Canvas layout (no overlap with existing x=−50..4640, y=300..1300)

Existing graph occupies y≈300..1300 across the width (Phase-4 solids x2300..2840 y300..820;
Phase-5 BOM x3300..4640 y980..1300). **Everything below y=1400 is free across the full width.**
New work is placed in three horizontal bands:

| Band | Subsystem | x range | y range |
|---|---|---|---|
| Catalog data | shared profile catalog (parallel lists) | 150 .. 900 | 1420 .. 1900 |
| A | Profile-selector macro (3 roles + Sweep/Cap) | 1000 .. 3600 | 1420 .. 1980 |
| B | Mounting subsystem | 150 .. 3600 | 2050 .. 2650 |
| C | Diagonal infill | 150 .. 3600 | 2720 .. 3300 |

Rule for the builder: keep new components at **y ≥ 1420**. Within a band, advance x by ~180
per column (matches existing spacing). Sliders sit ~60 px below the component they drive.

---

## 2. Subsystem 1 — Profile-selector macro ("sweep a chosen section along a centerline")

### 2.1 Design decision & justification

**Chosen routing: build BOTH a Circle and a Rectangle at the section frame, then use a
`Stream Filter` (gate = section flag) to pass exactly ONE section curve into a SINGLE `Sweep1`,
then `Cap Holes` → Closed Brep.**

Why this over the alternatives:
- One unified downstream (`Sweep1` → `Cap Holes`) for round/rect/flat means the geometry output,
  the display, and the BOM-length tap are identical across section types — no per-type branching
  to keep in sync.
- Rejected: "approximate a circle with a filleted/degenerate rectangle" — inaccurate diameter,
  wrong mass, fragile at the fillet limit. Not acceptable for a legal/ERP model.
- Rejected: keeping round on `Pipe` and rect on `Sweep1` — two solid streams to merge and two
  cap conventions; more wiring, more failure modes. `Sweep1` of a closed circle is exact, so
  there is no reason to keep `Pipe` except speed (irrelevant here).
- `flat` vs `rect` are the **same construction** (a `Rectangle` with X=dim_x, Y=dim_y); only the
  catalog dimensions differ. So the gate only needs **round vs non-round** (2 streams).

**BOM coupling:** the `kg_per_m` value for a role is pulled by the **same `List Item` index**
that drives its geometry. That List-Item output wires into the Phase-5 `Multiplication` B input,
replacing the hardcoded density constant. Geometry and mass therefore can never disagree.

### 2.2 Shared catalog (built once, in the Catalog band x150..900)

The companion agent supplies the catalog as **parallel lists**, one value per row, same order:

| catalog list (nickname) | contents | used as |
|---|---|---|
| `cat_gate` | int per row: **0 = round, 1 = rect/flat** | Stream Filter gate |
| `cat_dimx` | dim_x_mm | Rectangle X size |
| `cat_dimy` | dim_y_or_dia_mm | Rectangle Y size **and** circle diameter |
| `cat_wall` | wall_mm | (reserved; hollow-section mass only) |
| `cat_kgm` | kg_per_m | BOM multiplier |

Build each list as a **Panel** (multiline, one value per line) feeding a `Merge`/`List` — or, if
the companion delivers them as a comma string, a `Text Split`. Simplest robust form: one
**multiline Panel per list** with "Multiline Data" enabled (each line = one list item). Flag: the
builder must verify each Panel emits a **list of N items**, not one concatenated string
(`gh_inspect outputs` → count == row count).

> If the companion instead exposes `section_type` as **text** {round,rect,flat}, derive `cat_gate`
> with `Equality` (Text) vs constant `"round"` → Boolean → the gate reads False=0 (non-round=rect
> stream) / True=1... which is inverted from the table above. To avoid sign confusion, prefer a
> numeric `cat_gate` list from the catalog; if only text is available, wire the Equality result so
> that **round → stream index that carries the Circle** (see 2.4 note) and probe once.

### 2.3 Component list — ONE role (Handlauf / handrail), Band A ~x1000..1900 y1420

| # | display name | tab / panel | nickname | notes |
|---|---|---|---|---|
| 1 | Number Slider | Params | `Handlauf-Profil` | int, min 0, max N−1, val = handrail row |
| 2 | List Item | Sets ▸ List | `_selGate_H` | List=`cat_gate`, Index=slider |
| 3 | List Item | Sets ▸ List | `_selDimX_H` | List=`cat_dimx`, Index=slider |
| 4 | List Item | Sets ▸ List | `_selDimY_H` | List=`cat_dimy`, Index=slider |
| 5 | List Item | Sets ▸ List | `_selKg_H` | List=`cat_kgm`, Index=slider |
| 6 | Perp Frame | Curve ▸ Analysis (`PerpFrame` in G) | `_frmH` | Curve=handrail `Geometry`, Parameter=0 |
| 7 | Division | Maths (`Division` in G) | `_diaHalf_H` | A=`_selDimY_H` Item, B=2 → radius |
| 8 | Circle | Curve ▸ Primitive | `_circH` | Plane=`_frmH`, Radius=`_diaHalf_H` |
| 9 | Multiplication | Maths (`Multiplication` in G) | `_xHalfP_H` | A=`_selDimX_H`, B=0.5 |
| 10 | Multiplication | Maths | `_xHalfN_H` | A=`_selDimX_H`, B=−0.5 |
| 11 | Construct Domain | Maths ▸ Domain (`ConstructDomain` in G) | `_domX_H` | A=`_xHalfN_H`, B=`_xHalfP_H` |
| 12 | Multiplication | Maths | `_yHalfP_H` | A=`_selDimY_H`, B=0.5 |
| 13 | Multiplication | Maths | `_yHalfN_H` | A=`_selDimY_H`, B=−0.5 |
| 14 | Construct Domain | Maths ▸ Domain | `_domY_H` | A=`_yHalfN_H`, B=`_yHalfP_H` |
| 15 | Rectangle | Curve ▸ Primitive (`Rectangle` in G) | `_rectH` | Plane=`_frmH`, X Size=`_domX_H`, Y Size=`_domY_H` |
| 16 | Stream Filter | Sets ▸ List | `_selSec_H` | Gate=`_selGate_H`, Stream 0=Rectangle, Stream 1=Circle |
| 17 | Sweep1 | Surface ▸ Freeform | `_sweepH` | Rail=handrail `Geometry`, Section=`_selSec_H` |
| 18 | Cap Holes | Surface ▸ Util | `Handlauf_Volumen` | Brep=`_sweepH` Brep |

Constants `2`, `0.5`, `−0.5` are shared `bh.const` values placed once in Band A and reused.

### 2.4 Wiring table — ONE role (handrail)

| source (nick.port) | → | target (nick.port) |
|---|---|---|
| `Handlauf-Profil` .0 | → | `_selGate_H` . Index |
| `Handlauf-Profil` .0 | → | `_selDimX_H` . Index |
| `Handlauf-Profil` .0 | → | `_selDimY_H` . Index |
| `Handlauf-Profil` .0 | → | `_selKg_H` . Index |
| `cat_gate` . (list out) | → | `_selGate_H` . List |
| `cat_dimx` . (list out) | → | `_selDimX_H` . List |
| `cat_dimy` . (list out) | → | `_selDimY_H` . List |
| `cat_kgm` . (list out) | → | `_selKg_H` . List |
| `handrail` . Geometry | → | `_frmH` . Curve |
| const 0 | → | `_frmH` . Parameter |
| `_selDimY_H` . Item | → | `_diaHalf_H` . A |
| const 2 | → | `_diaHalf_H` . B |
| `_frmH` . Frame | → | `_circH` . Plane |
| `_diaHalf_H` . Result | → | `_circH` . Radius |
| `_selDimX_H` . Item | → | `_xHalfP_H` . A ; `_xHalfN_H` . A |
| const 0.5 | → | `_xHalfP_H` . B ; `_yHalfP_H` . B |
| const −0.5 | → | `_xHalfN_H` . B ; `_yHalfN_H` . B |
| `_selDimY_H` . Item | → | `_yHalfP_H` . A ; `_yHalfN_H` . A |
| `_xHalfN_H` . Result | → | `_domX_H` . (Domain start / A) |
| `_xHalfP_H` . Result | → | `_domX_H` . (Domain end / B) |
| `_yHalfN_H` . Result | → | `_domY_H` . A |
| `_yHalfP_H` . Result | → | `_domY_H` . B |
| `_frmH` . Frame | → | `_rectH` . Plane |
| `_domX_H` . Domain | → | `_rectH` . X Size |
| `_domY_H` . Domain | → | `_rectH` . Y Size |
| `_selGate_H` . Item | → | `_selSec_H` . Gate |
| `_circH` . Circle | → | `_selSec_H` . Stream 0 |
| `_rectH` . Rectangle | → | `_selSec_H` . Stream 1 |
| `handrail` . Geometry | → | `_sweepH` . Rail |
| `_selSec_H` . Stream (out) | → | `_sweepH` . Section(s) |
| `_sweepH` . Brep | → | `Handlauf_Volumen` . Brep |
| `_selKg_H` . Item | → | `kgH` . B  *(replaces density const 1.993)* |

> **Gate index note (RESOLVED 2026-07-25):** the convention conflict flagged here is settled in
> favour of the **catalog**: `profiles.section_flags()` emits **0 = round, 1 = rect/flat** (already
> committed code), so the wiring is **Stream 0 = Circle, Stream 1 = Rectangle**. Gate value 0 then
> selects the Circle. Do not invert `section_flags`; invert nothing — wire the streams in this order.
> The build phase must still confirm with `gh_canvas info` that gate is input **0** and streams are
> inputs **1..N** before wiring; `grasshopper/build/build_p6.py` asserts this at runtime.

### 2.5 The other two roles

Instantiate the identical 18-component block twice more, changing only:

| role | slider nick | centerline source | Cap-Holes nick | BOM target | y offset |
|---|---|---|---|---|---|
| Posten (post) | `Posten-Profil` | `posts` . Line | `Posten_Volumen` | `kgP` . B (was 2.386) | Band A +180 |
| Füllstab (infill) | `Fuellstab-Profil` | **Subsystem-3 selected infill** (see §4) . Line | `Fuellstab_Volumen` | `kgF` . B (was 0.888) | Band A +360 |

The infill role's **Rail** is NOT `fill` directly — it is the `Fuellung-Stil` Stream-Filter output
(§4), so the same Sweep serves both vertical and diagonal modes. The infill role's **flat** section
(the Rectangle branch) is the one reused by the diagonal bars in §4.

### 2.6 Acceptance checks (Subsystem 1)
- `gh_inspect geometry` on each `*_Volumen` Cap-Holes output → type is **Closed Brep** (not Brep/Surface), count == centerline count.
- Toggle each `*-Profil` slider across all rows → no red components; Circle appears for round rows, Rectangle for rect/flat rows.
- `_selKg_H/P/F` Item value matches the catalog row of the slider; BOM total shifts when the slider changes (mass tracks geometry).
- Sweep twist sanity: on the straight rails here, section stays perpendicular; if a rail is later curved, re-check `Sweep1` for flips.

---

## 3. Subsystem 2 — Mounting (fascia vs top-mount) at each post base point

### 3.1 Outward slab-edge normal (works for raked runs)

| # | display name | tab | nickname | wiring |
|---|---|---|---|---|
| 1 | Evaluate Curve | Curve ▸ Analysis | `_evalBase` | Curve=`untergurt` Geometry, Parameter=`dc` Parameters |
| 2 | Unit Z | Vector (`UnitZ` in G) | `_zM` | Factor=1 |
| 3 | Cross Product | Vector ▸ Vector | `_edgeNrm` | A=`_evalBase` Tangent, B=`_zM` Unit vector |
| 4 | Unit Vector | Vector ▸ Vector | `_edgeN1` | Vector=`_edgeNrm` Vector |

Rationale: `Cross(tangent, Z)` yields the horizontal vector perpendicular to the run direction and
lying in the horizontal plane. For the default run (tangent in the X–Z plane, y=0) this resolves to
a ±Y horizontal vector — the true slab-edge outward normal — regardless of rake angle. `Unit Vector`
normalizes it so downstream offsets are exact lengths. (If the sign points inward for a given run,
negate with a `×−1` on the offset amplitude — flag for visual check.)

### 3.2 Sliders (parametric; companion agent finalizes values)

`Platte-Breite` (plate width along edge), `Platte-Hoehe` (fascia height), `Platte-Tiefe`
(top-mount depth), `Platte-Dicke` (thickness t), `Bolzen-Durchmesser` (bolt dia),
`Bolzen-Laenge` (embedment), `Bolzen-Offset-V` (fascia vertical bolt spacing),
`Bolzen-Offset-XY` (top-mount corner inset), `Fascia-Offset` (outward offset to slab face),
plus the mode selector `Montage-Typ` (int 0=fascia, 1=top).

### 3.3 FASCIA branch (mode 0) — vertical plate parallel to slab edge + 2 horizontal bolts

| # | display name | tab | nickname | wiring |
|---|---|---|---|---|
| 5 | Amplitude | Vector ▸ Vector | `_fascVec` | Vector=`_edgeN1`, Amplitude=`Fascia-Offset` |
| 6 | Move | Transform (`Move` in G) | `_fascPt` | Geometry=`dc` Points, Motion=`_fascVec` |
| 7 | Construct Plane | Vector ▸ Plane | `_fascPln` | Origin=`_fascPt` Geometry, X-Axis=`_evalBase` Tangent, Y-Axis=`_zM` Unit vector |
| 8 | Center Box | Surface ▸ Primitive | `_fascPlate` | Base=`_fascPln`, X=½`Platte-Breite`, Y=½`Platte-Hoehe`, Z=½`Platte-Dicke` |
| 9 | Unit Vector | Vector ▸ Vector | `_intoSlab` | Vector = `_edgeN1` × −1 (into slab); or Amplitude −`Bolzen-Laenge` |
| 10 | (Move ×2) | Transform | `_boltPtLo/_boltPtHi` | `_fascPt` moved ±`Bolzen-Offset-V` along Z |
| 11 | Construct Plane ×2 | Vector ▸ Plane | `_boltPln*` | Origin=bolt pt, Z-normal = `_intoSlab` |
| 12 | Cylinder ×2 | Surface ▸ Primitive | `_fascBolt*` | Base=`_boltPln*`, Radius=½`Bolzen-Durchmesser`, Length=`Bolzen-Laenge` |
| 13 | Merge | Sets ▸ Tree | `_fascBolts` | D1=`_fascBoltLo`, D2=`_fascBoltHi` |

Plate axes: plane X = run tangent (width along edge), plane Y = world Z (height), plane **normal =
outward slab normal** (thickness) — so the plate is a **tall vertical fin parallel to the slab edge**,
offset outward to the slab face. Bolts extrude **horizontally into the slab** along `_intoSlab`.

### 3.4 TOP branch (mode 1) — horizontal base plate + 4 downward corner bolts

| # | display name | tab | nickname | wiring |
|---|---|---|---|---|
| 14 | XY Plane | Vector ▸ Plane | `_topPln` | Origin=`dc` Points (world-XY oriented, horizontal) |
| 15 | Center Box | Surface ▸ Primitive | `_topPlate` | Base=`_topPln`, X=½`Platte-Breite`, Y=½`Platte-Tiefe`, Z=½`Platte-Dicke` |
| 16 | corner offsets | Vector | `_c1.._c4` | four vectors: (±½W along tangent) + (±½D along `_edgeN1`), inset by `Bolzen-Offset-XY` |
| 17 | Move ×4 | Transform | `_topBoltPt1..4` | `dc` Points moved by each corner vector |
| 18 | Unit Z ×(−1) | Vector | `_down` | Z × −1 → downward bolt axis |
| 19 | Construct Plane ×4 | Vector ▸ Plane | `_topBoltPln1..4` | Origin=corner pt, Z-normal=`_down` |
| 20 | Cylinder ×4 | Surface ▸ Primitive | `_topBolt1..4` | Radius=½`Bolzen-Durchmesser`, Length=`Bolzen-Laenge` |
| 21 | Merge | Sets ▸ Tree | `_topBolts` | D1..D4 = the four cylinders |

Corner vectors are built as `Vector Addition` (registry `Addition` GUID works on vectors) of a
tangent-scaled and a normal-scaled component (use `Amplitude` to set each to ½W−inset / ½D−inset);
the four sign combinations give the four corners.

### 3.5 Mode select (only the chosen mode's solids appear)

Use **Stream Filter** (gate = `Montage-Typ`) — one output, gate picks the input. Two filters:

| # | display name | nickname | Gate | Stream 0 (fascia) | Stream 1 (top) | output |
|---|---|---|---|---|---|---|
| 22 | Stream Filter | `Montage_Platten` | `Montage-Typ` | `_fascPlate` Box | `_topPlate` Box | selected plates |
| 23 | Stream Filter | `Montage_Bolzen` | `Montage-Typ` | `_fascBolts` (merged) | `_topBolts` (merged) | selected bolts |

> Prompt said "Stream Gate"; note **Stream Gate = one input → many outputs** (routes to output[gate],
> others empty). For "pass exactly one of two streams into a single downstream," the correct part is
> **Stream Filter** (many inputs → one output, gate selects). We use Stream Filter. The build must
> confirm gate is input 0 via `gh_canvas info`.

### 3.6 Counts & acceptance checks (Subsystem 2)
- Plates = **post count** (= `dc` Points count = N+1). Bolts = post count × (**2** fascia | **4** top).
- `gh_inspect geometry` on `Montage_Platten` → **Closed Brep**, count == post count.
- `gh_inspect geometry` on `Montage_Bolzen` → Closed Brep, count == post count × 2 (mode 0) or ×4 (mode 1).
- Toggle `Montage-Typ`: exactly one plate style and its bolt count appear; the other stream is empty.
- Visual: fascia plate normal points outward (bolts go into slab); top plate lies flat at base level, bolts point down. If mirrored, negate `_edgeN1`.
- Raked-run check: rotate the base line (change `cRise`) → normals stay horizontal-perpendicular (Cross-Product test), plates still parallel to edge.

---

## 4. Subsystem 3 — Diagonal infill style (selectable)

> **SUPERSEDED on compliance grounds (2026-07-25).** This section originally specified an
> either/or swap — vertical bars **or** diagonals — with §4.3 arguing the diagonal field is
> self-compliant by construction. That argument covers only the 120 mm sphere; it ignores the
> **anti-climb rule**, which forbids horizontal *and diagonal* members in the 150–600 mm band
> outright (OIB RL 4 / ÖNORM B 5371 — see `docs/patterns-and-code.md` §2, which quotes Pkt. 4.2.3
> verbatim; inclined members are named explicitly). A diagonal-only guard is therefore not
> compliant for child-accessible use no matter how dense it is, so the swap must not be built.
>
> **Built instead (Scheme A):** the diagonals are decorative and ride *outboard of* a
> deterministic vertical safety field that stays in place. `Fuellung-Stil` becomes
> **0 = verticals only** (default), **1 = verticals + decorative diagonals** (child-safe),
> **2 = diagonals only** (Scheme B, industrial/adults-only, never the default).
> The two layers are gated **independently** with `Smaller Than`/`Larger Than` → `Cull Pattern`
> rather than swapped through one Stream Filter. The diagonal *generation* geometry in §4.1 and
> the spacing cap in §4.3 remain correct and are used as-is. See `docs/SPEC.md` Phase 8 and
> `grasshopper/build/build_p8.py` for the built design.

`Fuellung-Stil` int slider: **0 = vertical bars (existing `fill`, untouched)**, **1 = diagonal chaotic flat bars**.

### 4.1 Per-bay diagonal generation, Band C

Reuses `shat` `Segments` (lower-chord bays) and the same bay parameters on the handrail.

| # | display name | tab | nickname | wiring |
|---|---|---|---|---|
| 1 | Shatter | Curve ▸ Util (`Shatter` in G) | `_shatH` | Curve=`handrail` Geometry, Parameters=`dc` Parameters → upper bays |
| 2 | Slider | Params | `Diagonal-Seed` | int, min 0, max 9999, val 42 |
| 3 | Slider | Params | `Diagonal-Dichte` | max clear spacing, min 50, max 108, val 100 |
| 4 | Length | Curve ▸ Analysis (`Length` in G) | `_segLenD` | Curve=`shat` Segments |
| 5 | Division | Maths | `_nCell` | A=`_segLenD` Length, B=`Diagonal-Dichte` |
| 6 | Round | Maths (`Round` in G) | `_nCeil` | value=`_nCell` → use **Ceiling** output |
| 7 | Divide Curve | Curve ▸ Division (`DivideCurve` in G) | `_divLo` | Curve=`shat` Segments, Count=`_nCeil` Ceiling → lower rail points (per-bay branch) |
| 8 | Divide Curve | Curve ▸ Division | `_divHi` | Curve=`_shatH` Segments, Count=`_nCeil` Ceiling → upper rail points |
| 9 | Random | Sets ▸ Sequence | `_rndShift` | Range=`_shiftDom`, Number=`_nCeil` Ceiling (per bay), Seed=`Diagonal-Seed` |
| 10 | Construct Domain | Maths ▸ Domain | `_shiftDom` | A=−`_nCeil`·⅓, B=+`_nCeil`·⅓ (bounded shear) |
| 11 | Round | Maths | `_shiftInt` | `_rndShift` → Nearest (integer offsets) |
| 12 | Shift List | Sets ▸ List | `_hiShift` | List=`_divHi` Points, Shift=`_shiftInt`, Wrap=True |
| 13 | Line | Curve ▸ Primitive (`Line` in G) | `_diagFwd` | Start=`_divLo` Points, End=`_hiShift` List |
| 14 | Shift List | Sets ▸ List | `_hiShiftB` | List=`_divHi` Points, Shift=`_shiftInt`×−1, Wrap=True |
| 15 | Line | Curve ▸ Primitive | `_diagBwd` | Start=`_divLo` Points, End=`_hiShiftB` List |
| 16 | Merge | Sets ▸ Tree | `_diagLines` | D1=`_diagFwd`, D2=`_diagBwd` → crossing diagonal field |
| 17 | Flatten | (raw GUID `f80cfe18…`) | `_diagFlat` | Tree=`_diagLines` → single centerline list |

Two shifted families (`_diagFwd` forward, `_diagBwd` backward) produce the crossing "chaotic"
cross-hatch; the per-bay random integer shift (seeded by `Diagonal-Seed`) makes each bay's pattern
differ while every diagonal still starts/ends on a rail node whose neighbors are < 120 mm apart.

### 4.2 Style select — feeds the SAME Sweep + BOM

| # | display name | nickname | Gate | Stream 0 | Stream 1 | output |
|---|---|---|---|---|---|---|
| 18 | Stream Filter | `Fuellung_Aktiv` | `Fuellung-Stil` | `fill` Line (vertical) | `_diagFlat` (diagonal) | active infill centerlines |

`Fuellung_Aktiv` output is the **Rail** for the Subsystem-1 Füllstab role (§2.5) and the **Curve**
for the Phase-5 `kgF` Length tap. Both modes therefore share one Sweep and one BOM path; the
diagonal bars use the **flat** section (Rectangle branch, e.g. 40×8) of the profile selector.

### 4.3 Exact 120 mm max-opening check (the build's `gh_inspect` must verify)

Construction guarantee: choose divide spacing `p ≤ 120 − t_bar` (with 40×8 flat, t along the
opening plane = 8 → `Diagonal-Dichte ≤ 112`; default 100 gives margin). Because both rails are
divided at the same `Ceiling` count, every rail node carries at least one forward and one backward
diagonal, so the largest inscribed opening in the field is bounded by the rail node spacing `p`.

`gh_inspect` acceptance (mode 1):
1. Per bay, `p = segLen / Ceiling`. Assert **max(p) < 120 − t_bar** (measure via distance between
   consecutive `_divLo` points, or `_segLenD / _nCeil Ceiling`).
2. Assert `_divLo` count == `_divHi` count per bay (rails triangulate; no unpaired node).
3. Assert every bay has ≥ 1 forward and ≥ 1 backward bar (Merge branch count == 2 × bay count).
4. Diagonal bars terminate exactly on both rails (endpoint deviation from rail curve ≈ 0 within tol).
   Together (1)+(3)+(4) ⇒ **no Ø120 sphere passes** — the crossing bars cap both horizontal (≤p) and
   diagonal openings below 120.

### 4.4 Acceptance checks (Subsystem 3)
- `Fuellung-Stil`=0 → `Fuellung_Aktiv` == existing vertical `fill` lines, count unchanged; BOM matches Phase-5 baseline.
- `Fuellung-Stil`=1 → diagonal lines only; Closed-Brep bars after the shared Sweep+Cap; BOM recomputes to the diagonal total.
- Sweep of flat section on diagonal rails yields **Closed Brep** (Cap Holes), count == `_diagFlat` count.
- Changing `Diagonal-Seed` reshuffles the pattern but keeps checks §4.3 (1)–(4) passing.

---

## 5. Components to resolve at build time via `gh_canvas action=search`

Not in `bh.G` — search by these exact display names (tab in parentheses):

`List Item` (Sets▸List), `Stream Filter` (Sets▸List), `Stream Gate` (Sets▸List — only if the
one-in/many-out behavior is wanted; **not** used here), `Circle` (Curve▸Primitive),
`Sweep1` (Surface▸Freeform), `Cap Holes` (Surface▸Util), `Evaluate Curve` (Curve▸Analysis),
`Cross Product` (Vector▸Vector), `Unit Vector` (Vector▸Vector), `Amplitude` (Vector▸Vector),
`Construct Plane` (Vector▸Plane), `XY Plane` (Vector▸Plane), `Center Box` (Surface▸Primitive),
`Cylinder` (Surface▸Primitive), `Merge` (Sets▸Tree), `Random` (Sets▸Sequence),
`Shift List` (Sets▸List), `Construct Domain` (in G already), `Equality` (Maths▸Operators — only if
catalog gate arrives as text).

---

## 6. Ports the builder MUST probe with `gh_canvas info` before wiring (non-obvious)

- **Stream Filter** — Gate is input **0**; data streams are inputs 1..N, selected by 0-based index.
  Confirm which stream index carries Circle vs Rectangle (§2.4 gate note) and fascia vs top (§3.5).
- **Stream Gate vs Stream Filter** — opposite topologies. This design uses **Stream Filter**
  everywhere it selects one-of-many into one downstream. Do not substitute Stream Gate.
- **Sweep1** — input order is **Rail** then **Section(s)**; wiring them backwards silently produces
  garbage or nothing. Rail = centerline, Section = closed profile curve. Also watch for section
  flips/twist on non-straight rails.
- **Center Box** — `Base` is a **Plane**; X/Y/Z numeric inputs are **half-extents (radii)**, not full
  sizes — hence the ½ multipliers. Confirm before wiring plate dimensions.
- **Cylinder** — `Base` is a **Plane**; the cylinder extrudes along the plane **normal (Z)**. Bolt
  direction is set by the base-plane normal (into slab / downward), not by a separate direction port.
  Confirm sign; use `Length` positive with a correctly-oriented plane, or negate.
- **Cross Product** — output vector is **not unitized**; must pass through `Unit Vector` before use
  as a direction, and through `Amplitude` to set an offset length.
- **Evaluate Curve** — `Parameter` is a **curve parameter** (matches `dc` Parameters, which are real
  params on `untergurt`); `Tangent` output is unit-length. Do not feed normalized 0–1 unless the
  curve is reparameterized.
- **List Item** — main output is **Item**; keep `Wrap` off; index must stay in `[0, N−1]` (clamp the
  `*-Profil` slider max to catalog row count − 1).
- **Rectangle** — `X Size` / `Y Size` are **Domains**; a bare number becomes `0..n` (un-centered).
  Feed the centered `Construct Domain` (−½..+½) so the profile is centered on the frame.
- **Random** — outputs floats within the `Range` domain; for integer list shifts, pass through
  `Round` (Nearest). `Number` is the count per branch; `Seed` drives repeatability.
- **Shift List** — `Shift` is a signed integer; `Wrap` should be **True** so endpoints stay on-rail.
- **Round** — has separate `Nearest` / `Floor` / `Ceiling` outputs; the divide-count paths use
  **Ceiling** (round up) exactly as the existing Phase-2/3 spacing logic does.
