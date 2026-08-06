# Contributing

Thanks for your interest. Bug reports, new infill patterns, profile catalog data and corrections to the norm checks are all welcome.

## Before you start

- For anything larger than a bug fix, open an issue first and describe what you intend to change. That avoids duplicated work and lets us agree on the approach.
- For bugs, the more precise the input geometry and parameters, the faster it gets fixed. Include the pattern, the bay dimensions and what you expected.

## Development

The browser app has no build step and no dependencies — three.js is vendored.

```bash
python -m http.server 8000     # from the repository root
# open http://localhost:8000/web/
```

Tests require Node ≥ 18:

```bash
node --test web/test/
```

The Grasshopper side is Python and needs Rhino 8 + Grasshopper to run for real. A syntax gate runs in CI (`python -m compileall -q grasshopper`), but geometry changes there can only be verified against Rhino.

## Guidelines

- Keep the browser app dependency-free. No build step, no package manager, no framework.
- The web app and the Grasshopper engine implement the same model. If you change pattern logic or geometry rules in one, change it in the other, or say explicitly in the PR why it applies to only one side.
- Keep changes focused; one topic per pull request.
- Follow the style of the surrounding code rather than reformatting files.
- If your change affects generated geometry or masses, check it against `reference/` and explain any intentional differences in the pull request.

## Commit sign-off (DCO)

Every commit must carry a `Signed-off-by` line, certifying that you wrote the contribution or otherwise have the right to submit it under the terms below (the [Developer Certificate of Origin](https://developercertificate.org/)).

Git adds the line for you:

```bash
git commit -s -m "Your message"
```

## Contributor licence terms

By submitting a contribution to this project you agree to both of the following:

1. Your contribution is released under the **GNU Affero General Public License v3.0 only**, the same licence as the rest of the project.
2. You grant **Gleinkaa** (the project author and copyright holder) a perpetual, worldwide, irrevocable, royalty-free, non-exclusive licence to use, reproduce, modify, distribute, sublicense and **relicense** your contribution, including under the terms of the commercial licence described in [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md).

You retain the copyright in your contribution; this is a licence grant, not an assignment.

The second point exists for a concrete reason: the commercial licence can only be offered over code the author is permitted to relicense. Without this grant, any contributed code would have to be excluded from commercially licensed builds, or the commercial option would have to be dropped altogether. If you cannot make this grant — for example because your employer holds the rights to your work — please say so in the issue or pull request before contributing code, and we will find another way (a bug report or a written description of the fix is still very useful).
