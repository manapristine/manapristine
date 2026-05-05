# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mana Pristine is a housing society (apartment complex) financial management system. It generates per-flat maintenance statements from Excel workbooks and serves them via a static HTML dashboard hosted on GitHub Pages (`docs/`).

## Architecture

**Data flow:** Excel workbooks → Python report builder → JSON files → Static HTML dashboard

- `db/accounts/*.xlsx` — Source-of-truth Excel workbooks containing INCOME-EXPENSE-CYCLES sheets (one per financial year), plus per-month COLLECTION and EXPENSE sheets
- `db/workbooks.json` — Registry mapping financial year keys (e.g. "2025-26") to workbook paths and cutoff dates
- `db/members.csv` — Flat-to-owner mapping (flat, name, email, phone)
- `db/occupants.csv` — Flat-to-occupant mapping (current resident, may differ from owner)
- `db/collection.csv` — Flat-to-name collection reference
- `db/bankstatements/` — Raw bank statements (XLS/PDF) organized by FY
- `report_builder/report_builder.py` — Main report generator: reads workbooks, produces per-FY JSON datasets and a manifest
- `report_builder/update_collections.py` — Parses bank statements, matches transactions to flats via name/flat-number heuristics, updates COLLECTION sheets in the workbook
- `report_builder/refresh_fy.py` — Prepares a workbook for the next financial year (renames sheets, shifts dates +1 year, zeroes data cells while preserving formulas)
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

# Process a bank statement and update collection in the workbook
python report_builder/update_collections.py db/bankstatements/2025-2026/March-2026.xls

# Refresh a workbook for the next financial year
python report_builder/refresh_fy.py db/accounts/WORKBOOK.xlsx
```

## Key Conventions

- Financial year runs April–March (e.g. FY 2025-26 = Apr 2025 to Mar 2026)
- Flat identifiers are normalized to uppercase (e.g. "F1", "F2") via `normalize_flat()`
- The Excel workbook sheet naming convention: `{Month}{Year}-EXPENSE`, `{Month}{Year}-COLLECTION`, `INCOME-EXPENSE-CYCLES`, `ANNUAL-EXPENSE-DETAILS`
- The dashboard (`docs/index.html`) is entirely self-contained — no framework, no bundler, just inline CSS and JS
- Output JSON goes to `docs/` for GitHub Pages serving; the manifest lists available FY files
- Python 3.11+ with type hints; dependencies are just `openpyxl` and `pandas`
