# Margin of Error (MOE)

A browser-based Australian election prediction and live-count analysis MVP.

## What this build includes
- Modular repository layout for future migration to React/FastAPI.
- Streamlit frontend for non-technical users.
- Config-driven contest metadata (not hard-coded to one election).
- Data ingestion for CSV/XLSX loaders.
- Live count tracker with close-count indicators.
- Prediction engine with poll weighting + Monte Carlo simulation.
- Preference modelling with user-adjustable assumptions.
- Scenario testing controls (swing, turnout, postal lean).
- Booth map, intelligence table, commentary feed, and simulcast ticker.
- Exports to CSV/XLSX/HTML.
- Tests for core calculations and ingestion.

## Repository structure

```text
frontend/
backend/
data/
notebooks/
docs/
tests/
scripts/
```

## Quick start

1. Create a virtual environment.
2. Install dependencies.
3. Run the app.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py
```

Or:

```bash
./scripts/run_moe.sh
```

## Sample data included
Under `data/sample/`:
- sample electorate + booth coordinates
- sample candidates and parties
- sample live count
- sample declaration votes
- sample scenario defaults
- sample commentary and intelligence rows

## Key docs
- `docs/data_sources.md`
- `docs/modelling_assumptions.md`
- `docs/live_count_workflow.md`
- `docs/adding_new_election.md`
- `docs/scenario_testing.md`

## Notes
- This MVP uses file-based loaders rather than live scraping.
- A placeholder OSINT/media module is included in the UI as manual-safe input only.
- Political colours are configurable in `backend/config/contest_config.yaml`.

## Target repository
https://github.com/MusicOfScience/moe
