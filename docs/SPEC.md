# Master Prompt: Parametric Stair Railing Generator

You are a Lead Computational Designer and expert in algorithmic structural engineering as well as Austrian building regulations, specifically the OIB Guideline 4 and ÖNORM B 5371. Your task is to build a fully parametric, legally compliant stair railing generator in Grasshopper (Rhino 8.21+) using the Cordyceps MCP server. The goal is a vertical steel railing with an automatically generated Bill of Materials (BOM) for the ERP system.

Global Execution Doctrine (Phased State Machine): The construction of this graph is highly complex and error-prone regarding data trees. Therefore, a "zero-shot" attempt is strictly prohibited. You will build the graph sequentially in phases. Mandatory Rule: After EACH phase, you must verify the construction progress by calling `gh_inspect` (action `status`). You must analyze the generated values, list lengths, and data trees of the most recently created components. If the inspection reveals data tree mismatches (e.g., lists of lists instead of a flattened list) or if the strict mathematical constraints of the Austrian standards have been violated, you must immediately correct the error via `gh_wire` (rewiring, adding Flatten/Graft) or `gh_canvas`. Confirm your status and findings to me in the chat after each review step, and do not wait for me; proceed autonomously to the next phase after successful self-correction. Before each phase call `gh_document action=snapshot name="phaseN"` to create a real named restore point (this server supports `snapshot`/`revert`/`undo`/`redo`); at the end of each phase call `gh_document action=capture_canvas` (and `capture_viewport` for geometry phases) for a visual record. Note: `capture_viewport` has no zoom-extents option, so the camera may not be framed on the geometry — rely on `gh_inspect action=geometry`/`outputs` (exact coordinates, brep solidity, counts) as the authoritative verification, not the screenshot. `gh_document action=clear` wipes everything (irreversible-ish; prefer `revert` to a snapshot).

## MCP Execution Protocol (Cordyceps — read before ANY build action)
The Cordyceps MCP server exposes exactly four tools, each dispatched by an `action` argument. Endpoint: `http://127.0.0.1:26929/mcp` (JSON-RPC 2.0). Do not invent actions outside this list:
- `gh_canvas`: `add` (create a component — pass a **GUID** as `type`, plus `x`,`y`,`nickname`; for a slider use `type="Slider"` with `min`,`max`,`value`,`decimals`), `delete` (`id`), `search` (`query` → returns `{name,category,subcategory,guid}`), `info` (`id` → inputs/outputs/status), `preview` (`ids`,`enabled`), `zoom`.
- `gh_wire`: `connect`/`disconnect` with `sourceId`,`sourceParam`,`targetId`,`targetParam`. **Param indices are 0-based integers.**
- `gh_document`: `info`, `save`(`path`), `clear`, `solver` (`enabled` bool), `recompute`, `snapshot`/`revert`(`name`)/`snapshots`, `undo`/`redo`, `capture_viewport`(`path`,`view`), `capture_canvas`(`path`,`fit`).
- `gh_inspect`: `status` (all component OK/Warning/Error), `outputs`(`id` → actual output values), `geometry`(`id` → bbox/counts/validity/solid), `trace`, `disconnected`, `docs`. Use `outputs`/`geometry` to verify values — NOT `gh_canvas get` (that reads a slider/panel's own persistent content, not incoming data).

**Non-negotiable build sequence for every phase:**
1. **Resolve GUIDs by name** — before adding any component, `gh_canvas action=search query="<component name>"` to obtain its GUID. Never hard-code GUIDs; the registry is the source of truth. (Sliders are the only exception — added via `type="Slider"`.)
2. **Solver OFF while building** — `gh_document action=solver enabled=false` at the start of construction. Building with the solver live recomputes on every single wire (10–100× slower) and throws transient errors that would resolve after full wiring.
3. **Probe before wiring** — for each component whose inputs you will wire, `gh_canvas action=info id=<id>` and read the actual 0-based input/output indices from the response. Do NOT assume index order (e.g. do not assume Line SDL's Length is index 2 — verify).
4. **Build all components + wires** for the phase.
5. **Solver ON + recompute** — `gh_document action=solver enabled=true` then `gh_document action=recompute`.
6. **Inspect** — `gh_inspect action=status`, filter for any component whose status ≠ `OK`, and self-correct.
7. **Data-tree hygiene:** when mapping one flat list onto N targets, **Flatten before Graft** — mismatched branch counts silently break downstream components.

---

## How to run this generator
This file is the master prompt for an agent that builds the Grasshopper graph live via the **Cordyceps MCP server**. To kick it off:
1. Start Rhino 8.21+ with an **empty Grasshopper document** open, document units set to **millimeters**, and the Cordyceps MCP server connected.
2. Paste this entire file to the driving agent as its task and let it run autonomously through Phase 0 → Phase 9. It will self-inspect and self-correct after every phase and report findings in chat.
3. When it finishes, the generator is fully parametric: drag the sliders ('Geländerhöhe', 'Untergurt-Abstand', 'Fuellstab-Abstand') or re-reference `Treppenbasislinie` to a real stair-nosing polyline, and the geometry + BOM update automatically.
4. Phases 6–9 add three switchable subsystems on top of that baseline: switchable steel profiles per element ('Handlauf-Profil', 'Posten-Profil', 'Fuellstab-Profil'), switchable mounting ('Montage-Typ': fascia vs top-mount base plate, with anchor plates and bolts), and the decorative random-diagonal flat-bar infill overlay ('Fuellung-Stil'). Reference build drivers for these phases live in `grasshopper/build/build_p6.py` … `build_p9.py`.

## Assumptions & Conventions (read before building)
- **Document units are millimeters.** All literals depend on this.
- **Geometry vs. BOM material model:** The `Pipe`/`Extrude` volumes are *representative solids* for visualization and clash checking. The BOM weights use catalog **linear masses of the real hollow profiles** (Ø42.4×2.0 handrail, Ø12 solid bar, 40×40×2.0 SHS post). This is intentional — weight comes from the catalog, not from the solid volume. Do not try to reconcile them by hollowing the pipes.
- **Coordinate convention:** `Treppenbasislinie` is the rake line through the stair nosings. Heights are applied as pure vertical (Unit Z) offsets, which is how ÖNORM measures guard height (vertically above the nosing).
- **Naming:** every slider and key output param must be named as specified so the graph is legible and re-tunable.
- **Profile catalog (Phase 6+):** `grasshopper/profiles.py` is the single source of truth for the switchable sections and their linear masses. The 0-based row index in each role list IS the value carried by that role's `*-Profil` slider, and the **same index** drives both the swept section and the kg/m fed to the BOM — geometry and mass can therefore never disagree. Section flags are **0 = round, 1 = rect/flat**; the Stream Filter is wired **Stream 0 = Circle, Stream 1 = Rectangle** to match. Hollow-section kg/m use the sharp-corner convention and run ~3–5 % above EN 10219 nominal; swap the `kg_per_m` column if the shop steel list differs.
- **Compliance ownership (Phase 8):** the decorative diagonals never carry code compliance. A deterministic vertical bar field does. See Phase 8 — this is a legal constraint, not a stylistic preference.

## Phase 0: Environment & Default Input
**Action:**
1. Confirm the Grasshopper document is empty and the Rhino document unit is millimeters (see Precondition in Phase 1). If not, stop and report. Then set the solver OFF per the MCP Execution Protocol.
2. **Build the default base line from components — do NOT try to "internalize" curve geometry** (Cordyceps `gh_canvas add` has no documented way to set persistent geometry on a Curve param; the reliable path is to construct it). Add two `Construct Point` components (search the GUID) at `{0,0,0}` and `{4000,0,2000}` — feed their X/Y/Z from a small set of Number Sliders or Panel-fed number values — then add a `Line` (2-point) component wired A=first point, B=second point. Give this Line the nickname `Treppenbasislinie`. This is a straight rake line (4 m run / 2 m rise flight, slope length ≈ 4472 mm), which yields ~4 post segments and a full infill field — enough to exercise every downstream branch.
3. Note to the user that for a real project they replace this constructed default by wiring a `Curve` param (referenced to the actual stair-nosing edge(s) in Rhino) into the same downstream network in place of `Treppenbasislinie`; everything recomputes automatically.
**Review Step 0:** Turn the solver ON, recompute, then `gh_inspect action=status` on the `Line`/`Treppenbasislinie` component — confirm status `OK` and that it outputs exactly one valid curve of non-zero length before proceeding. Leave the solver OFF again if you continue building immediately.

## Phase 1: Parametric Basis and Normative Guide Curves
**Precondition — Units:** Before placing any component, verify the Rhino document unit system is **millimeters**. Every numeric literal in this graph (1000, 100, radius 21.2, density multipliers in kg/m) assumes mm. If the document is in m or cm, either switch the document to mm or abort and report — do not silently continue, as the entire dimensional and BOM logic depends on it.
**Action:**
1. Use the `Treppenbasislinie` Line component built in Phase 0 (the default rake line simulating the stair nosings/edges). All downstream references to "the base curve" mean this component's output.
2. Add a Number Slider (Name: 'Geländerhöhe', Value: 1000). ÖNORM B 5371 mandates 100 cm as the standard fall protection height. Note: this value is the **handrail system line** (pipe centerline). The finished top-of-rail sits ~21 mm higher due to the pipe radius (Phase 4), which keeps the assembly compliantly at or above 1000 mm.
3. Create a Move component. Construct a vector in the Z direction (Unit Z) using the value from 'Geländerhöhe' and move the 'Treppenbasislinie' upwards. The resulting geometry is our exact handrail system line.
4. Create a second Number Slider (Name: 'Untergurt-Abstand', Value: 100). Move the original base curve with another Unit Z vector by this value. This keeps the bottom gap (floor/nosing line to lower chord) at 100 mm < 120 mm, so the **120 mm test sphere** required by OIB RL 4 cannot pass beneath the railing. (OIB RL 4 uses a sphere, not a cube.)
**Review Step 1 (Mandatory Inspection):** Run `gh_inspect` on both Move components. Are they generating valid curves? Is the Z-translation of the handrail line exactly 1000? Are there any warnings (Red/Orange Flags) on the canvas? Correct any errors. If error-free, briefly document and start Phase 2.

## Phase 2: Structural Main Posts for Horizontal Load (Holmdruck)
**Action:**
1. According to Eurocode 1, we must place main posts to bear horizontal loads up to 3.0 kN/m. The maximum distance between posts is 1200 mm.
2. Connect the generated lower chord line ('Untergurt') to a Curve Length component.
3. Pass the calculated length into a Division component and divide it by the fixed value of 1200.
4. Pass the division result into a Round component. Attention: You must strictly use the **Ceiling** output (round up) to evaluate the minimum number of required segments. (The GH Round component exposes Nearest/Floor/Ceiling outputs — wire only Ceiling.) Ceiling of a positive quotient is always ≥ 1, so short railings still yield at least one segment (posts at both ends).
5. Use this Ceiling integer as the 'N' (segment count) input for a Divide Curve component, which divides the lower chord line. Note that N segments yield N+1 points, i.e. posts at both endpoints plus interior points — this is intended.
6. Generate vertical lines from these resulting division points using Line SDL. The direction is a Unit Z vector. The length must be calculated live via a Subtraction component: 'Geländerhöhe' minus 'Untergurt-Abstand' (= 900 with the default values). Do NOT hard-code 900 — wire the two sliders into the Subtraction so the post height stays parametric. These posts start on the lower chord (base + 100) and terminate exactly on the handrail system line (base + 1000).
**Review Step 2 (Mandatory Inspection):** Run `gh_inspect` on the Divide Curve and Line SDL components. Check the list lengths: Does the number of output lines exactly match the number of points? If the Grasshopper engine draws the lines at the origin due to missing data matching, use `gh_wire` to harmonize the lists (e.g., using Flatten).

## Phase 3: Uncompromising Implementation of Child Safety (12 cm Rule)
**Action:**
1. Anti-climbing protection (Leitereffekt) forbids horizontal elements between 15 cm and 60 cm. Therefore, we generate strictly vertical infill bars. The **clear** distance between two adjacent bar surfaces MUST be under 120 mm. Correct relationship: clear gap = (center-to-center spacing) − (bar diameter 12 mm). The legal maximum center spacing is therefore 120 + 12 = 132 mm.
2. Split the lower chord line exactly at the positions of the main posts determined in Phase 2 into individual segments (Use the Shatter component in combination with the 't' parameters from the previous Divide Curve).
3. Connect the newly created, shattered curve segments to a new Curve Length component.
4. Divide these measured lengths by a target center spacing of **115 mm** (deliberately conservative vs. the 132 mm legal max: clear gap becomes 115 − 12 = 103 mm, a comfortable safety margin). Expose this 115 as a named Number Slider 'Fuellstab-Abstand' so it can be relaxed toward 130 to save steel if the client accepts a tighter margin — do not bury it as a hidden constant.
5. Use Round again and strictly take the Ceiling output to round up the number of divisions for each individual segment.
6. Use another Divide Curve component. Input 'C' is the shattered lower chord segments, input 'N' is the rounded up values from the Ceiling output.
7. **De-duplicate before drawing bars.** Divide Curve returns both segment endpoints, so the points at every post location are produced twice (once per adjacent segment) and also coincide with the Phase-2 main posts. Flatten the per-segment point tree and pass it through a **Cull Duplicates** component (tolerance ~0.1 mm) so no infill bar is drawn inside a post or doubled at a boundary. This matters for both geometry and the BOM count in Phase 5.
8. From this cleaned point cloud, generate vertical system lines again using Line SDL (analogous to Phase 2), same parametric length ('Geländerhöhe' − 'Untergurt-Abstand'), up to the handrail line.
**Review Step 3 (Mandatory Inspection):** This is the most error-prone step! Run `gh_inspect`. You are operating here with branches of curve lists. Verify the data structure of the points AND confirm Cull Duplicates actually removed the boundary/post coincidences (compare point count before vs. after). Check if the Line SDL component outputs valid lines or if there are warnings regarding "Data tree length mismatch". If so, configure the correct Graft or Flatten of the inputs via `gh_wire`.

## Phase 4: Volumetric Transformation (Sweep & Pipe)
**Action:**
1. Transform the abstract lines into producible 3D steel volumes.
2. Add a Pipe component for the handrail line. Set the radius to 21.2 (results in a 42.4 mm round tube). Set the pipe **Caps to "Flat"** (Cap type 1) so the result is a Closed Brep — Review Step 4 checks for this.
3. Add a second Pipe component for all vertical infill bars (from Phase 3). Set the radius to 6 (results in Ø 12 mm round steel). Caps = Flat.
4. Generate square profiles for the main posts (from Phase 2). Create a Rectangle (Domain from -20 to 20 for X and Y). Align the rectangles with Perp Frame at the **start point of each post line**, then Extrude the rectangle by a vector equal to the post direction × length (Unit Z × 900, or reuse the post line's end−start vector) to generate 40x40 mm tubes. Cap the extrusion so it closes into a solid.
**Review Step 4 (Mandatory Inspection):** Run `gh_inspect` on the volume outputs. Are the results of type "Closed Brep" (not merely open "Brep" / "Surface")? If any are open, you forgot to cap a Pipe or the Extrusion. Are there red errors on the rectangle extrusions (e.g. Perp Frame count not matching the rectangle count)? Resolve them autonomously.

## Phase 5: Extraction of the Bill of Materials (BOM) and Logistics Data
**Action:**
1. Extract the length data to calculate the tonnages. Use the **de-duplicated** infill bars from Phase 3 (step 7) so the count is not inflated by post/boundary coincidences.
2. Connect the abstract system lines of the vertical infill bars (Phase 3) to a Curve Length component.
3. Sum these lengths with the Mass Addition component. IMPORTANT: Send a `gh_wire` command to "flatten" the input of the Mass Addition so that the data tree collapses into a single sum.
4. **UNIT CONVERSION — do not skip.** Curve Length returns millimeters (document units), but the density figures are kg/**m**. Divide the summed length by 1000 (mm → m) BEFORE multiplying. Then multiply the length-in-metres by the specific mass of 0.888 kg/m (Ø12 round bar). Omitting the ÷1000 makes the BOM exactly 1000× too heavy — a value that looks plausible on inspection but is wrong.
5. Repeat this summation, ÷1000 conversion, and multiplication process for the handrail (Multiplier: 1.993 kg/m for 42.4×2.0 tube) and the main posts (Multiplier: 2.386 kg/m for 40×40×2.0 SHS). Sanity-check magnitudes: a typical stair run should total on the order of tens of kilograms per element type, not tens of thousands — if you see five-/six-digit kg values, the ÷1000 is missing.
6. Optionally round each kg result to 1 decimal (Round → Nearest, or a Format/expression) before display.
7. Use the Concatenate component to create formatted text strings (Example: "Füllstäbe Ø12: [Wert] kg"). Also emit a total-weight line summing all three element groups.
8. Merge all strings into a Text Panel.
**Review Step 5 (Final Inspection):** Run `gh_inspect` on the Text Panel. Check the content on TWO axes: (a) Have the values been added to a total sum, or does the panel list hundreds of individual weights? If individual weights are listed, you forgot the Flatten on the Mass Addition. (b) Are the magnitudes physically sane (tens of kg, not tens of thousands)? If they are ~1000× too large, you forgot the mm→m conversion in steps 4/5. Correct either immediately.

---

# Switchable Profiles, Mounting and Decorative Infill (Phases 6–9)

Phases 0–5 produce a compliant baseline railing with one fixed profile per element, no mounting hardware, and vertical infill only. Phases 6–9 make three things switchable on top of that: any catalog profile per element, the fixing detail, and a decorative diagonal flat-bar overlay — without ever losing the Phase 3 safety guarantees.

**Canvas discipline:** the Phase 0–5 graph occupies x −50…4640, y 300…1300. Place **all** new components at **y ≥ 1420** in the bands given in `docs/architecture.md` §1, so the existing graph stays readable.

**The one-of-many idiom used throughout:** build BOTH candidate geometries, then select one with a **`Stream Filter`** (gate = input 0, data streams = inputs 1…N, one output). Do **not** substitute `Stream Gate` — that is the opposite topology (one input → many outputs). Probe every Stream Filter with `gh_canvas action=info` before wiring to confirm the gate really is input 0.

## Phase 6: Switchable Steel Profiles per Element
**Action:**
1. Build the profile catalog as parallel lists — one component per column, four columns per role (`cat_gate`, `cat_dimx`, `cat_dimy`, `cat_kgm`), values taken from `grasshopper/profiles.py`. **Verify each column emits a list of N items, not one concatenated string** (`gh_inspect action=outputs` → count == row count). A panel that collapses to a single string breaks every `List Item` downstream while still looking correct on the canvas.
2. Add one integer Number Slider per role — 'Handlauf-Profil', 'Posten-Profil', 'Fuellstab-Profil' — with **max = row count − 1** so the index can never leave the catalog.
3. Feed each slider into four `List Item` components (one per column). This single index is what keeps section and mass in sync.
4. Build the section curve **both ways** at a `Perp Frame` on the element centerline: a `Circle` of radius `cat_dimy`/2, and a `Rectangle` whose X/Y Sizes are **centered `Construct Domain`s** (−dim/2 … +dim/2). Feeding a bare number to Rectangle yields an un-centered `0…n` domain — the profile would sit off-axis.
5. Select one with a `Stream Filter`: gate = `cat_gate` Item, **Stream 0 = Circle, Stream 1 = Rectangle**. `flat` and `rect` are the same construction (only catalog dimensions differ), so the gate only ever needs two streams.
6. Sweep the selected section along the centerline with `Sweep1` (**input order is Rail then Section — reversing them silently produces garbage**) and close it with `Cap Holes`. Nickname the results `Handlauf_Volumen`, `Posten_Volumen`, `Fuellstab_Volumen`.
7. **Refactor, do not accumulate:** delete the three hardcoded Phase-4 solids (`Pipe` ×2, `Extrude` and their support components) — the new sweeps replace them. Then re-point each Phase-5 `Multiplication` B input from its hardcoded density constant to the matching `cat_kgm` `List Item`. **Disconnect the old constant first** — `gh_wire connect` ADDS a source rather than replacing it, so a leftover constant would be silently summed into the density.
**Review Step 6 (Mandatory Inspection):** `gh_inspect action=geometry` on each `*_Volumen` → type must be **Closed Brep**, count == centerline count. Then step each `*-Profil` slider through **every** row: no red components, Circle for round rows, Rectangle for rect/flat rows, and the BOM total must shift when the profile changes (proving mass tracks geometry). If mass does not move, step 7's re-point failed.

## Phase 7: Switchable Mounting (Fascia vs Top-Mount)
**Action:**
1. Derive the outward slab-edge normal — never hardcode it: `Evaluate Curve` on the lower chord at the `Divide Curve` **Parameters** gives the tangent at each post base; `Cross Product`(tangent, Unit Z) gives the horizontal vector perpendicular to the run at any rake angle. The cross product is **not unitized** — pass it through `Unit Vector` before using it as a direction.
2. Add the mounting sliders: 'Montage-Typ' (0 = fascia, 1 = top), 'Platte-Breite' (100), 'Platte-Hoehe' (220), 'Platte-Breite-Top' (120), 'Platte-Tiefe' (120), 'Platte-Dicke' (10), 'Bolzen-Durchmesser' (12), 'Bolzen-Laenge' (100), 'Bolzen-Offset-V' (75), 'Bolzen-Offset-XY' (20), 'Fascia-Offset' (0).
3. **Fascia branch:** a `Construct Plane` with X-Axis = run tangent and Y-Axis = Unit Z makes the plate a tall vertical fin parallel to the slab edge (its normal is the outward slab normal). Build it with `Center Box` — **the X/Y/Z inputs are half-extents, not full sizes**, so halve every plate dimension. Two M12 bolts stack vertically at ±'Bolzen-Offset-V' (150 mm spacing). A `Cylinder` extrudes along its **base plane's normal**, so orient each bolt plane with X-Axis = Unit Z, Y-Axis = tangent — that normal points *into* the slab.
4. **Top branch:** an `XY Plane` at each post base point carries a horizontal `Center Box` plate. Four corner bolt points are `Move`s by (±(½width − inset) along tangent) + (±(½depth − inset) along the edge normal), built with `Amplitude` + vector `Addition`. For downward bolts, orient the plane with X-Axis = Unit X and Y-Axis = Unit Y × −1 → normal = −Z.
5. Select with two `Stream Filter`s gated by 'Montage-Typ': `Montage_Platten` and `Montage_Bolzen`. `Merge` takes two inputs by default — **chain** merges for the four top bolts rather than assuming the component accepts variable inputs.
**Review Step 7 (Mandatory Inspection):** Plates must equal the post count; bolts must equal post count × 2 (fascia) or × 4 (top). `gh_inspect action=geometry` → Closed Brep on both outputs. Toggle 'Montage-Typ' and confirm exactly one style appears and the other stream is empty. **Visually verify the direction signs**: fascia bolts must run *into* the slab and top bolts *downward*. If either is mirrored, the outward sign of the edge normal is flipped for this run direction — negate it. Finally re-check with a different rake ('cRise'): the plates must stay parallel to the edge.

## Phase 8: Decorative Diagonal Infill over a Compliant Safety Field
> **Superseded by Phase 14.** `Fuellung-Stil` and the whole Line-SDL / Shift-List diagonal
> machinery described here were removed once the 34-pattern catalog went in; the
> `Muster` slider replaces them and Vertical Bars (30) / Scattered Diagonals (23) /
> Uniform Rake (32) are the catalog entries that correspond to the old styles 0 / 1 / 2.
> The compliance reasoning below still holds and is now enforced geometrically —
> read it, then read Phase 14.
**This phase carries a legal constraint. Read it before wiring.** A purely random diagonal field is **not compliant** for a child-accessible guard, for two independent reasons (OIB RL 4, aligned with ÖNORM B 5371):
- **120 mm sphere:** random triangles between crossing diagonals easily open wider than 120 mm.
- **Anti-climb (Leiterwirkung):** in the band **150–600 mm** above the tread nose, no horizontal **or diagonal** member may be arranged unless vertical openings there are ≤ 20 mm. Diagonals are named explicitly — a diagonal in this band is a foothold, which is exactly what the rule forbids.

Therefore the diagonals are **decorative only** and compliance is carried by a separate deterministic **vertical safety field** (Scheme A — see `docs/architecture.md` §4). Do **not** implement 'Fuellung-Stil' as a straight either/or swap of verticals for diagonals.

**Action:**
1. Add 'Fuellung-Stil': **0 = vertical bars only** (baseline, the default), **1 = vertical field + decorative diagonals** (child-safe), **2 = diagonals only** (Scheme B — industrial / adults-only, **not** child-safe; offer it, never default to it).
2. Gate the two layers independently instead of swapping them: verticals ON when style < 2, diagonals ON when style > 0. Use `Smaller Than` / `Larger Than` into a `Cull Pattern` on each layer — a false pattern culls the whole list to a clean empty output.
3. Generate the diagonals so every bar **starts and ends on a rail node**: `Shatter` the handrail at the post parameters to get upper bays matching the existing lower bays, divide **both** rails at the same `Round`→**Ceiling** count. Per-bay shear is `max(abs(round(Random(-n/3..n/3))), 1)` — the absolute value with a floor of 1 guarantees both families lean opposite ways regardless of node count. The forward family connects `lo[i] → hi[i+s]` (shift upper rail); the backward family connects `lo[i+s] → hi[i]` (shift lower rail forward). Both use positive-offset semantics with `Wrap` = False (wrapping was turned off in Phase 11d to stop bay-spanning bars, and positive-only shifts cooperate with non-wrapping `Shift List` semantics). Sliders: 'Diagonal-Seed' (42) and 'Diagonal-Dichte' (300, range 50–400).
4. **The spacing cap is conditional, not slider-enforced.** `Diagonal-Dichte` runs 50–400 mm (default 300). In Stil 2 the effective spacing is `min(Dichte, 112)` because the diagonals-alone field must hold the 120 mm sphere: `p < 120 − t_bar` = 112 mm for Flachstahl 40×8. In Stil 0/1 the vertical safety field at 115 mm centres (103 mm clear) already carries the rule, so the decorative diagonal spacing is free. The clamp is a **derived** `Stream Filter + Minimum` rather than a slider range restriction — dragging to 400 and then switching to Stil 2 silently re-tightens to 112, so compliance can never depend on the operator remembering to move a slider back.
5. Keep the decorative layer **outboard of the safety plane**: `Move` the diagonal centerlines along the Phase-7 edge normal by 'Diagonal-Auslage' (40), so the diagonals are not a reachable foothold on the fall side.
6. Sweep the diagonals with the **flat** section (`Diagonal-Profil`, default Flachstahl 40×8 = INFILL row 4) into `Diagonal_Volumen`, and re-point the Phase-6 vertical sweep **and** the Phase-5 infill `Length` tap at the gated vertical output so geometry and BOM both follow the style switch.
**Review Step 8 (Mandatory Inspection):** Confirm lower and upper rail node counts are **equal** per bay (unpaired nodes mean bars that miss a rail), that `p < 120 − t_bar` holds for the longest bay, and that every bay carries at least one forward and one backward bar. `Diagonal_Volumen` must be **Closed Brep**. Then switch-test all three styles: 0 → verticals only, 1 → both layers present, 2 → diagonals only. Changing 'Diagonal-Seed' must reshuffle the pattern while all of the above still holds. If the vertical field ever disappears in style 1, stop — the railing is no longer compliant.

## Phase 9: Extended BOM (Mounting Hardware + Diagonals) and Save
**Action:**
1. Add a BOM line for the decorative diagonals exactly as in Phase 5 — `Length` → `Mass Addition` → **÷1000** → × the catalog kg/m of the selected diagonal profile.
2. Compute plate mass from the **live sliders**, not the researched constants: W × H × T × 7.85e-6 kg/mm³, with a `Stream Filter` on 'Montage-Typ' picking the fascia footprint (Breite × Höhe) or the top footprint (Breite-Top × Tiefe). Multiply by the plate count from a `List Length` on `Montage_Platten`. Sanity anchors: 100×220×10 ≈ 1.73 kg, 120×120×10 ≈ 1.13 kg.
3. Bolt mass = `List Length` of `Montage_Bolzen` × 'Bolzen-Masse-kg' (0.12 kg for an M12 anchor + nut + washer).
4. **Re-point the existing 'GESAMT:' line** at a new grand total that includes diagonals, plates and bolts. Leaving it on the old three-group sum under-reports the assembly while still looking plausible — disconnect the old source first.
5. Append the new lines to the `Stueckliste_BOM` panel, then `gh_document action=save` to `Railing_Generator.gh` and capture the canvas and viewport for the record.
**Review Step 9 (Final Inspection):** Read the panel and check on three axes: (a) plate and bolt **counts** match the Phase-7 expectation for the active mounting mode; (b) magnitudes are physically sane — tens of kg, not tens of thousands (the ÷1000 is intact); (c) the total actually changes when 'Montage-Typ' or any `*-Profil` slider moves. Run one final switch-through — every `*-Profil` row, both mounting modes, all three infill styles — and confirm no component turns red in any combination.

---

# Pattern Catalog Adaptation (Phase 14)

## Phase 14: The 34 Catalog Patterns Replace the Three Infill Styles
The 34 patterns are this project's own set, indexed 0–33; the index order is the engine's
contract (regression tests, the `Muster` slider, the reference masses).
Construction and norm data behind the numbers: `docs/patterns-and-code.md`.

**The one architectural decision.** All 34 patterns live in a single Python 3 Script
component (`muster`, source of record `grasshopper/patterns.py`), not in 34 wired
sub-graphs. A pattern is a function from a bay's local `(s, t)` frame to curves and
solids; expressing that as native components would mean roughly a thousand of them, and
every pattern would have to re-derive the same frame. The component emits four channels
and everything downstream is the machinery that already existed:

| Channel | Feeds | BOM |
|---|---|---|
| `Stab1` | `_frmI` / `_graftRail_I` / `_len_Fuell` | length × kg/m of `Fuellstab-Profil` |
| `Stab2` | `_frmD` / `_graftRailD` / `_len_Diag` | length × kg/m of `Diagonal-Profil` |
| `Stahl` | `Blech_Volumen` | volume × 7850 kg/m³ |
| `Holz`  | `Holz_Volumen`  | volume × `Holz-Rohdichte` |

`Stahl` and `Holz` are new: the model had no way to weigh anything that was not a bar
with a kg/m. Laser panels, variable-width flats and twisted square bars are weighed by
volume instead.

**The local frame is the whole trick.** Per bay: `O` = start of the Untergurt segment,
`Xh` = unit vector along it (so `s` runs *with* the stair pitch as arc length), `Yh` =
plumb, `Nh` = outward. `P(s,t) = O + Xh·s + Yh·t`. A bar at constant `s` is therefore
plumb, not normal to the rake — which is how a railing is actually built. **`Xh` and
`Yh` are not orthogonal.** Inverting `P` needs the Gram matrix, not a dot product; the
naive version reported every single bar end as unattached while the geometry was fine.

**Action:**
1. Build the engine with `Lo` ← `_ShatterUnter.Segments` and `Hi` ← `_shatH.Segments`
   (same post parameters, so bay *i* pairs correctly), plus `N` ← **`List Item(0)` of**
   `_edgeN1`. That List Item is not cosmetic: `_edgeN1` emits one vector per post, and
   an item-access input fed a 5-item list runs the whole engine five times over the full
   bay list — 200 bars instead of 40, stacked on each other, with zero errors reported.
2. Re-point **frame and rail together** for both bar channels. `_frmI` used to hang off
   the ungated Line SDL while `_graftRail_I` hung off the gated one; that only worked
   because the Cull never dropped anything. Sections and rails must come from one list
   or the sweep pairs bay *i*'s rail with bay *j*'s section.
3. Give every solid channel a null guard before `Mass Addition`: merge a constant 0 into
   the volume list and **flatten**. `Mass Addition` over an empty list emits null, GH
   treats null as the additive identity, and an unselected material bills as if it were
   1 m³ — with no warning anywhere.
4. Rapport, not bar count. Each design declares its repeat unit in **mm**; the engine
   rounds `bay_length / rapport` to whole units and stretches the rapport to fit, so the
   remainder is distributed instead of leaving a runt at the post.
5. Designs whose opening is set *by* the rapport carry `gap=True` and get their rapport
   capped at `Oeffnung-max + bar width`, derived rather than slider-enforced — same
   reasoning as the old conditional `Diagonal-Dichte` clamp in **Phase 8, step 4**
   (built by `grasshopper/build/build_p12.py`; there is no Phase 12 section in this document).
   Designs whose opening comes from the *shape*
   (arches, diamonds, loops) carry `gap=False`; capping the rapport there would do
   nothing, so they are classified in the `norm` field instead of silently "fixed".
6. Sweep rails must be **kink-free**. Emit each straight/arc/bezier piece separately;
   never join a bent bar into one polycurve and never emit a closed loop. A kinked rail
   makes `Sweep1` return several breps (Stacked Arches: 56 rails → 84 bodies) or fail
   outright (Ray Diamond's closed rhombus: "Sweep could not be created"). Both break the
   solids == centerlines invariant, which is the only guard against a silent sweep bug.
7. Turn the engine's own preview **off** — it carries centerlines and solids on one
   component — and give `Holz` and `Stahl` their own Brep params as previewed finals.
   Otherwise the only thing visible in the viewport is the centroid dots of the `Volume`
   components, and the wood looks like it was never built when in fact it weighs 27.6 kg.

**Norm check (OIB-Richtlinie 4, Ausgabe Mai 2023, verified verbatim).**
- **Pkt. 4.2.4** — openings must be ≤ **12 cm in at least one direction**. Austria uses a
  *direction* condition, **not** Germany's 120 mm sphere: a 40 × 700 mm slot is compliant.
  This is why `Oeffnung-max` defaults to **120**, not 100.
- **Pkt. 4.2.3** — between **15 cm and 60 cm** above the tread nose there may be no
  horizontal or inclined member, unless it projects ≤ 3 cm, vertical openings there are
  ≤ 2 cm, mesh perimeter ≤ 16 cm, perforated-sheet holes ≤ 4 cm, or the top edge
  overhangs inward ≥ 15 cm. The Richtlinie deliberately names **no limiting angle**, so
  the engine takes one from the `Kletterwinkel-Grenze` slider (60° = expert practice,
  75° = conservative) and measures against **true horizontal**, not the stair pitch — a
  member parallel to the flight is a ramp and is climbable.
- The engine samples every bar's tangent inside that band and reports the count on the
  `Norm` output. It is a **geometric pre-check, not a proof**: line load, wind, railing
  height and the statics of rails and panels are all out of scope.

**Review Step 14 (Mandatory Inspection):** Run `grasshopper/regress_p14.py`. It sweeps all
34 patterns and asserts, per pattern: no component in ERROR/WARNING (bar the known
disconnected Volvox `Load`); `Fuellstab_Volumen` count == `Stab1` count and
`Diagonal_Volumen` count == `Stab2` count; **zero free bar ends** (rule K1 — every end
on a rail, a post, or another member of the same bay); and that a channel a pattern
*must* fill is not empty. Read the slider value back with `gh_canvas action='get'`
(`info` reports no value for a slider and silently returns None) and re-run `recompute`
until the engine reports the expected pattern index — the outputs are occasionally still
the previous state right after a recompute, which once turned an entire green run into a
lie. Then **look at the viewport** for at least one bar pattern, one wood pattern and one
sheet pattern. Every defect in this phase that the numeric guards missed was visible in a
screenshot.

---

End the process with a final success message and present the status of the Text Panel to me.
