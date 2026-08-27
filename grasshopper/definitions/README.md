# grasshopper/definitions/

The Grasshopper binaries for the railing generator. These existed only in
`StiegengelaenderGeneratorGH` before 2026-08-27; that repo is now archived, so
they live here with the rest of the product.

| File | Notes |
|---|---|
| `Stiegengelaender_Generator.gh` | the main definition |
| `Stiegengelaender_Generator_v2.gh` | v2, largest and most recent |
| `Stiegengelaender_Generator_alt.gh` | was `Stiegengelaender_Generator(1).gh` |

The Python driver scripts in `../build/` are the newer, AGPL-headed versions -
they supersede the `scratch/` copies in the archived repo, which reference the
pre-rename `muster_component.py` instead of `patterns.py`.

Not migrated: the KUKA welding-cell project (`kuka_schweisszelle.gh`/`.3dm` and
its three handoffs). Different domain, still in the archived repo's history.
