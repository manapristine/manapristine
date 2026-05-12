# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mana Pristine is a housing society (apartment complex) financial management system. It generates per-flat maintenance statements from Excel workbooks and serves them via a static HTML dashboard hosted on GitHub Pages (`docs/`).

## Architecture

**Data flow:** Excel workbooks → Python report builder → JSON files → Static HTML dashboard

- `db/accounts/*.xlsx` — Source-of-truth Excel workbooks (one per FY) containing INCOME-EXPENSE-CYCLES, per-month COLLECTION/EXPENSE sheets, and ANNUAL-EXPENSE-DETAILS
- `db/workbooks.json` — Registry mapping FY keys (e.g. "2025-26") to workbook paths, cutoff dates, and portal password
- `db/members.csv` — Flat-to-owner mapping (flat, name, email, phone)
- `db/occupants.csv` — Flat-to-occupant mapping (current resident, may differ from owner)
- `db/collection.csv` — Flat-to-name collection reference
- `db/bankstatements/` — Raw bank statements (XLS/PDF) organized by FY
- `db/wateron/` — WaterOn consumption reports organized by FY
- `report_builder/report_builder.py` — Main report generator: reads workbooks, produces per-FY JSON datasets and a manifest
- `report_builder/update_collections.py` — Interactive: parses bank statements, matches transactions to flats via name/flat-number heuristics, generates a processing CSV, then updates COLLECTION sheets
- `report_builder/update_water_consumption.py` — Updates EXPENSE sheets with water usage from WaterOn reports
- `report_builder/new_fy.py` — Creates a new FY workbook from existing one (copies, renames sheets, updates refs, clears data, preserves all formulas)
- `report_builder/refresh_fy.py` — In-place refresh of a workbook for the next FY (renames sheets, shifts dates +1 year, zeroes data)
- `report_builder/compare_workbooks.py` — Validates formula integrity between baseline and candidate workbooks after FY transitions
- `report_builder/sync_members.py` — Syncs db/members.csv into the Members sheet of workbooks
- `docs/index.html` — Single-page dashboard (vanilla HTML/CSS/JS, no build step) that loads JSON data and renders flat statements, defaulters, excess payments, and aggregate views
- `docs/report-manifest.json` — Index of available FY data files, consumed by the dashboard
- `comm/` — Communication templates (markdown) for society notices

## Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate all report JSON files (run from project root)
python report_builder/report_builder.py

# Process a bank statement (interactive — prompts for option 1=create report, 2=update workbook)
python report_builder/update_collections.py db/bankstatements/2025-2026/March-2026.xls

# Update water consumption from WaterOn report
python report_builder/update_water_consumption.py db/wateron/26-27/Consumption\ Report\ April-2026.xlsx

# Create a new FY workbook from existing one
python report_builder/new_fy.py db/accounts/SOURCE-WORKBOOK.xlsx 2027-28

# In-place refresh workbook for next FY (creates backup by default)
python report_builder/refresh_fy.py db/accounts/WORKBOOK.xlsx

# Compare formulas between baseline and new FY workbook
python report_builder/compare_workbooks.py db/accounts/BASELINE.xlsx db/accounts/CANDIDATE.xlsx

# Sync members.csv into workbook Members sheet
python report_builder/sync_members.py
```

## Key Conventions

- Financial year runs April–March (e.g. FY 2025-26 = Apr 2025 to Mar 2026)
- Flat identifiers are normalized to uppercase (e.g. "F1", "F2") via `normalize_flat()`
- The Excel workbook sheet naming convention: `{Month}{Year}-EXPENSE`, `{Month}{Year}-COLLECTION`, `INCOME-EXPENSE-CYCLES`, `ANNUAL-EXPENSE-DETAILS`
- The dashboard (`docs/index.html`) is entirely self-contained — no framework, no bundler, just inline CSS and JS
- Output JSON goes to `docs/` for GitHub Pages serving; the manifest lists available FY files
- Python 3.11+ with type hints; dependencies are just `openpyxl` and `pandas`
- The society has 64 flats; expense formulas divide shared costs by 64

## Portal Security

Dashboard access is protected by a community password stored in `db/workbooks.json` as `portal_password`. During report generation, `report_builder.py` hashes it (SHA-256) and injects the hash into `docs/index.html`. The browser validates the hash client-side and stores a session token in `sessionStorage`.

## FY Transition Workflow

1. `new_fy.py` (preferred) or `refresh_fy.py` — create/refresh workbook for next FY
2. `compare_workbooks.py` — verify formulas are intact vs. the previous FY workbook
3. Update `db/workbooks.json` — register the new workbook path
4. Open workbook in Excel/Sheets and save to refresh formula cache
5. `python report_builder/report_builder.py` — regenerate all reports

## Report Builder Internals

The report builder handles two scenarios for reading INCOME-EXPENSE-CYCLES data:
- **Cached values present** (workbook saved from Excel): reads values directly from the summary sheet
- **No cached values** (formulas not evaluated): falls back to reading individual COLLECTION and EXPENSE sheets, computing totals via `fill_from_source_sheets()`

Expense calculation involves: water usage proportion (variable), fixed expense share (÷64), meter rent, parking, club house, shifting, gym, and membership fees — multiplied by a month-specific multiplier.

**EXPENSE sheet water calculation:** The `total_water` divisor must only sum column C for actual flat rows (F1-F16, G1-G16, S1-S16, T1-T16). Non-flat rows (CH, GYM, BSMT, MPFOWA, TOTAL) must be excluded — the TOTAL row contains a summary value that would double-count if included. This matches the workbook formula which uses a specific cell reference (`$C$70`) pointing to `=SUM(C6:C69)` (flat rows only).
