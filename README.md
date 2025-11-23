# TrackNarrator

Turns Toyota GR Cup telemetry into coach-ready post-session reports.

## 1. Overview

TrackNarrator focuses on Driver Training & Insights with strong overlap into Post-Event Analysis. It uses a unified SessionBundle schema (v0.1.2) aligned to the TRD 2025 "Hack the Track" Barber dataset. It computes:

- Lap and section deltas vs a reference
- Robust outlier events (mistakes, gains, risk patterns)
- A scalar "coach score" with badge-style feedback
- Narrative summaries suitable for driver debriefs

All schema and mapping details are documented in docs/SPEC-schema-v0.1.2.md.

## 2. For Hack the Track judges

There are two main ways to interact with TrackNarrator:

- Static demo viewer (in docs/) – recommended first contact.
- Local backend plus demo data.

The static viewer uses a pre-generated SessionBundle from the Barber Motorsports Park dataset, bundled as fixtures/bundle_sample_barber.json.

Once GitHub Pages is enabled for the docs/ folder, this section will be updated with the public demo URL.

## 3. Quick local demo (using bundled Barber sample)

This path does NOT require downloading the official TRD dataset. It uses the pre-generated demo bundle fixtures/bundle_sample_barber.json.

Clone the repo:
```
git clone https://github.com/sofus-deng/tracknarrator
cd tracknarrator
```

(Optional) create and activate a Python environment.

Install backend dependencies:
```
cd backend
uv sync    (or the equivalent command already documented in backend/README.md)
cd ..
```

Generate demo exports (summary JSON, export pack, docs demo data):
```
./demo/run_demo.sh
```

After running "demo/run_demo.sh", you can open "docs/index.html" directly (file://) or via GitHub Pages once it is configured.

See "backend/README.md" for detailed API and backend information.

## 4. Full Barber ingestion (using official TRD dataset)

If you have access to the official Barber dataset from the Hack the Track portal, you can regenerate the demo bundle from scratch.

Create a folder:
```
mkdir -p data/barber
```

Download the Barber dataset zip from the hackathon portal.

Unzip it into data/barber/.

### Option A: Quick ingestion (if you already have canonical CSVs)

If you already have the canonical CSV files (telemetry.csv, weather.csv, sections.csv), you can run:

```
./scripts/ingest_barber_demo.sh
```

### Option B: Complete workflow from raw TRD files

**Step 0: Extract raw dataset**
```
mkdir -p data/barber/raw
```

Download the Barber dataset zip from the hackathon portal and unzip it into `data/barber/raw/`.

**Step 1: Prepare canonical CSVs**
```
./scripts/prepare_barber_from_raw.sh
```

This script:
- Reads raw TRD files from `data/barber/raw/`
- Converts them to canonical formats expected by the ingestion script
- Outputs: `data/barber/telemetry.csv`, `data/barber/weather.csv`, `data/barber/sections.csv`

**Step 2: Ingest canonical CSVs**
```
./scripts/ingest_barber_demo.sh
```

This script:
- Reads the TRD CSVs from data/barber/
- Maps them into the unified SessionBundle schema (v0.1.2)
- Regenerates fixtures/bundle_sample_barber.json, which is then used by the demo and docs flows.

The schema and mappings are described in docs/SPEC-schema-v0.1.2.md.

## 5. Demo viewer (docs/)

The docs/ folder contains a static HTML/JS viewer for a single session:
- docs/index.html – one-page viewer
- docs/app.js – front-end logic
- docs/styles.css – styling

Once demo data has been generated (via demo/run_demo.sh or the ingestion script), the viewer can:
- Plot lap and section deltas
- Show detected key events and coaching comments
- Display a coach score and a short narrative

### GitHub Pages (recommended)

The repository is designed so that GitHub Pages can serve the viewer directly from the docs/ folder.

Suggested configuration: GitHub Pages source = "docs/" folder on the main branch.

Live demo: https://sofus-deng.github.io/tracknarrator/ (update once Pages is enabled)

## 6. Tests and quality gates

TrackNarrator includes unit tests and shell-based acceptance checks.

Run backend tests:
```
cd backend
make test
```

From the repo root, run selected acceptance scripts:
```
cd ..
./scripts/accept_step14.sh
(cd backend && ./scripts/accept_step16.sh)
./scripts/accept_step17.sh
```

A single "scripts/accept_all.sh" entry point may be added later to run all steps 3–19 used in CI.

## 7. Documentation

Key documents with relative paths:
- Unified schema and TRD mapping: docs/SPEC-schema-v0.1.2.md
- Backend details (API, storage, internal modules): backend/README.md
- Hack the Track submission draft: docs/submit/devpost_template.md

Judges or collaborators should start with the schema spec and backend README if they want deeper implementation details.