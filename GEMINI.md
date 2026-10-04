# GEMINI.md

## Project Overview
Mana Pristine is a financial management system for a housing society (apartment complex of 64 flats). It manages income and expenditure by using Excel workbooks as the source of truth, processing them with Python to generate JSON datasets, and displaying the results via a static HTML dashboard hosted on GitHub Pages.

## Architecture & Data Flow
**Excel Workbooks** (`db/accounts/*.xlsx`) → **Python Scripts** (`report_builder/`) → **JSON Data** (`docs/*.json`) → **Static Dashboard** (`docs/index.html`)

### Core Components
- **Source Data (`db/`):**
    - `accounts/`: Excel workbooks containing financial records (one per FY) with monthly `COLLECTION`/`EXPENSE` sheets, `INCOME-EXPENSE-CYCLES`, and `ANNUAL-EXPENSE-DETAILS`.
    - `bankstatements/`: Raw bank statements (TSV/XLS/PDF) organized by FY used for updating collections and tracking payments.
    - `wateron/`: WaterOn consumption reports and `avg-water-usage.xlsx` for water billing and variance tracking.
    - `members.csv`: Flat-to-owner mapping (flat, name, email, phone).
    - `occupants.csv`: Flat-to-occupant mapping (current resident/tenant).
    - `collection.csv`: Flat-to-name collection reference.
    - `workbooks.json`: Configuration mapping financial years to workbook files, cutoff dates, and the portal password.
- **Processing Logic (`report_builder/`):**
    - `report_builder.py`: Main engine that reads Excel data and produces JSON datasets and manifest for the dashboard.
    - `update_collections.py`: Automates updating collection sheets by parsing bank statements.
    - `update_water_consumption.py`: Updates EXPENSE sheets with water usage from WaterOn reports.
    - `validate_water_meter_reading.py`: Parses WaterOn reports, maps flat consumption, updates `db/wateron/avg-water-usage.xlsx`, and highlights high-variance flats (>50%).
    - `update_late_payment_fine.py`: Evaluates payment status from prior month, checks net dues, applies late fines in the current EXPENSE sheet, and updates summary formulas.
    - `track_payments.py`: Parses bank statements, matches payments against members/occupants, and generates a formatted Excel tracking sheet (`tracking_sheet.xlsx`).
    - `new_fy.py`: Creates a new FY workbook from an existing one (copies, renames sheets, updates refs, clears data, preserves all formulas).
    - `refresh_fy.py`: In-place refresh of a workbook for the next FY (shifts dates +1 year, zeroes data).
    - `compare_workbooks.py`: Validates formula integrity between baseline and candidate workbooks after FY transitions.
    - `sync_members.py`: Synchronizes `db/members.csv` into the Members sheet of workbooks.
- **Frontend (`docs/`):**
    - `index.html`: A self-contained dashboard (Vanilla JS/CSS, no build step) that visualizes flat statements, defaulters, excess payments, and society-level financials.
    - `report-manifest.json`: Index of generated report files.
- **Communications (`comm/`):**
    - Society notices and communication templates in Markdown.

## Technical Stack
- **Backend:** Python 3.11+
- **Libraries:** `pandas`, `openpyxl`
- **Frontend:** Vanilla HTML, CSS, and JavaScript (No build system or frameworks)
- **Deployment:** GitHub Pages (serving the `docs/` directory)

## Development Workflow

### Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Key Commands
- **Generate Reports:** Processes all configured workbooks and updates JSON files in `docs/`.
  ```bash
  python report_builder/report_builder.py
  ```
- **Update Collections:** Parses a bank statement and updates the corresponding workbook.
  ```bash
  python report_builder/update_collections.py db/bankstatements/2026-2027/Sep-2026.xls
  ```
- **Track Payments:** Generates a payment tracking Excel sheet from a bank statement.
  ```bash
  python report_builder/track_payments.py db/bankstatements/2026-2027/Sep-2026.xls
  ```
- **Update Water Consumption:** Updates EXPENSE sheets with water usage from a WaterOn consumption report.
  ```bash
  python report_builder/update_water_consumption.py "db/wateron/26-27/Consumption Report Sep-2026.xlsx"
  ```
- **Validate Water Meter Readings:** Updates average water usage and highlights anomalies.
  ```bash
  python report_builder/validate_water_meter_reading.py "db/wateron/26-27/Consumption Report Sep-2026.xlsx"
  ```
- **Update Late Payment Fines:** Evaluates missed payments from prior month and applies fines.
  ```bash
  python report_builder/update_late_payment_fine.py
  ```
- **Prepare Next FY Workbook:**
  ```bash
  python report_builder/new_fy.py db/accounts/CURRENT_WORKBOOK.xlsx 2027-28
  ```
- **Compare Workbooks:** Validates formula integrity between two workbooks.
  ```bash
  python report_builder/compare_workbooks.py db/accounts/BASELINE.xlsx db/accounts/CANDIDATE.xlsx
  ```
- **Sync Members:** Updates the Members sheet in the active workbook from `members.csv`.
  ```bash
  python report_builder/sync_members.py
  ```

## Project Conventions
- **Financial Year:** April 1st to March 31st (e.g., "2025-26", "2026-27").
- **Flats:** 64 flats in total (F1-F16, G1-G16, S1-S16, T1-T16). Flat identifiers are always normalized to uppercase.
- **Workbook Naming:** Sheets follow specific patterns: `{Month}{Year}-EXPENSE`, `{Month}{Year}-COLLECTION`, `INCOME-EXPENSE-CYCLES`, `ANNUAL-EXPENSE-DETAILS`.
- **JSON Output:** All generated data must be stored in the `docs/` directory to be accessible by the dashboard.
- **No Build Step:** The frontend (`docs/index.html`) is designed to be served directly without any transpilation or bundling.

## Security
- **Portal Password:** Access to the dashboard is protected by a community password.
    - The plain-text password is stored in `db/workbooks.json` as `portal_password`.
    - `report_builder.py` hashes this password (SHA-256) and injects the hash into `docs/index.html` during the report generation process.
    - Residents enter the password on a "Community Access" screen; the browser validates the hash and stores a session token in `sessionStorage`.

## Report Builder Internals & Source of Truth

**EXPENSE sheet water calculation:** When computing `total_water` (the divisor for water percentage), only sum column C for actual flat rows (F1-F16, G1-G16, S1-S16, T1-T16). Non-flat rows (CH, GYM, BSMT, MPFOWA, TOTAL) must be excluded — the TOTAL row contains a summary value that would double-count if included. This matches the workbook formula which uses a specific cell reference (`$C$70`) pointing to `=SUM(C6:C69)` (flat rows only).

**Excel as Single Source of Truth:**
- Excel workbooks (`db/accounts/*.xlsx`) are the absolute single source of truth for both raw cell values and computed formula results.
- Scripts MUST ONLY read cached formula values evaluated and saved by Excel (`openpyxl.load_workbook(..., data_only=True)`).
- **Pre-Read Upfront**: Always pre-read ALL required formula values with `data_only=True` into memory BEFORE making any cell modifications or saving the workbook. Saving a workbook with `openpyxl` strips cached formula values (`<v>` XML tags), causing subsequent `data_only=True` reads to return `None`.
- NEVER dynamically calculate or estimate formula values in Python as fallbacks when a cell value is `None` or missing.
- If a required cached formula value is missing or `None`, raise a `ValueError` instructing the user to open, save, and close the Excel workbook.


