# Devpost Submission Template

## Project Name
TrackNarrator — Deterministic Racing Story from Telemetry

## Elevator Pitch (≤120 words)
TrackNarrator turns raw racing telemetry into ranked events, shareable cards, deterministic narratives, and coaching tips — all exportable as a single JSON pack. It's reproducible (one command), multilingual (zh-Hant/en), and CI-verified.

## What it does
Importers (TRD long / RaceChrono / GPX) → Events (robust-Z) → Share Cards → Narrative (deterministic, ai_native on/off) → Coaching Tips → Export Pack (JSON).

## How we built it
Python + FastAPI, uv toolchain, unit tests and acceptance scripts (coverage ≥79%). Deterministic algorithms. Demo kit: make demo. One-page reader: docs/index.html.

## Challenges
Normalizing messy sources, preserving determinism with useful insights, test isolation for seeded sessions.

## Accomplishments
E2E pipeline, judge-ready demo/export, CI (GitHub Actions), one-page showcase.

## What's next
Lap delta visualizations, per-track tuning, sharing links, integrations with series timing.

## How to run
make demo
# outputs -> backend/demo/export/summary.json, export_zh.zip, export_en.zip
# open docs/index.html then click "Load summary.json"

## Links (fill at submission)
- Demo video:
- Repository:
- Live page (optional):