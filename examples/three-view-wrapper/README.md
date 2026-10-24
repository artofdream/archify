# Example: three-view wrapper (Current / Target / Gaps + step player)

> **This is an example, not a core Archify feature.** It lives under `examples/` in a fork as a holding place for own changes. Nothing in `archify/` is modified, and Archify itself renders one diagram per file and has no tabs or step playback.

## What it is

A small Python script (`build.py`, standard library only) that

1. validates and delivers **three separate Archify architecture renders** with the stock CLI (`sample/current|target|gaps.architecture.json`), then
2. embeds the three delivered HTML pages in one **hand-written wrapper page** (`out/three-view.html`) that adds:
   - tabs **Current / Target / Gaps** (deep links `#current`, `#target`, `#gaps`),
   - a step player (Prev / Play / Next / Restart / Clear, ← → and Space, `?step=N`) that highlights nodes and edges of a request path inside the active diagram,
   - chapter buttons (from `chapters.json`) that jump to a step and can open Archify's native Route view (`#route=a~b`) for that path,
   - a gap table (from `gap-table.json`) and a Dark / light toggle for the wrapper only.

The system shown is an **invented "notes service"**. All content is synthetic sample data.

## Files

| File | Purpose |
| --- | --- |
| `sample/*.architecture.json` | Three small architecture IRs (schema v1). Plain Archify input, usable on their own. |
| `story.json` | Steps for the player: node/edge ids to highlight, title, caption, status chip. |
| `chapters.json` | Chapter buttons per view: step ranges and the route to open in Archify. |
| `gap-table.json` | Rows of the gap table. |
| `build.py` | Validate + deliver the three views, then write `out/three-view.html`. |
| `verify.py` | Optional browser smoke test of the wrapper (Chrome + Playwright). |

`out/` and delivery/receipt files are git-ignored (see `.gitignore`).

## Prerequisites

- Archify **3.2.0** (this example was built and checked against the unmodified v3.2.0 tree), run from a checkout or any install that provides `archify/bin/archify.mjs`.
- Node.js 18 or newer and Python 3.
- `ARCHIFY_UPDATE_CHECK_DISABLED=1` for the CLI so no update check runs. `build.py` sets it for its own CLI calls; set it in your shell too if you run the CLI by hand.
- Only for `verify.py`: `pip install playwright` and a Chrome/Chromium binary (set `CHROME=/path/to/chrome` if it is not `/usr/bin/google-chrome`). Archify's own `browser-check` also needs Chrome.

## Build

From the repository root:

```bash
export ARCHIFY_UPDATE_CHECK_DISABLED=1
python3 examples/three-view-wrapper/build.py
# open examples/three-view-wrapper/out/three-view.html
```

To use a different Archify checkout: `ARCHIFY=/path/to/archify/bin/archify.mjs python3 examples/three-view-wrapper/build.py`.

`build.py` stops with a non-zero exit if `archify validate` or `archify deliver` fails for any view. Optional extras:

```bash
node archify/bin/archify.mjs check        examples/three-view-wrapper/out/current.architecture.html
node archify/bin/archify.mjs browser-check examples/three-view-wrapper/out/current.architecture.html --summary
python3 examples/three-view-wrapper/verify.py
```

## Use it for your own system

Replace the three files in `sample/` with your own IRs (keep component ids stable across views if you want the step highlight to match), then edit `story.json`, `chapters.json` and `gap-table.json` to your ids. The player only highlights ids that exist in the active view.

## Limits

- **Wrapper, not a feature.** The tabs, player, chapters and gap table are custom HTML and JavaScript in `build.py`; they are not produced or validated by Archify. `archify validate` / `deliver` cover only the three per-view IRs.
- **Relies on viewer internals.** Highlighting uses the delivered page's DOM hooks (`[data-node-id]`, `[data-edge-from|to]`, and `rect:not(.c-mask)`) and the wrapper reaches into the embedded page, which works because the page is embedded via `srcdoc` (same origin). A future Archify viewer may change these hooks. Checked only against 3.2.0.
- **Route button** sets `location.hash` of the embedded viewer; if that fails it silently does nothing.
- **Dark / light** themes the wrapper only, not the embedded diagrams.
- **Output size.** The combined page is about 2.7 MB because each view is a full self-contained Archify page.
- **Browser coverage.** `verify.py` and the manual check used Chrome only.
- The three diagrams are independent renders; Archify does not diff or link them. Consistency (same ids, positions) is up to the author. Use `archify compare architecture` if you want a real base/head diff.
- `meta.output` in the sample IRs names the delivered file; `build.py` passes its own output path, so the field is informational.
