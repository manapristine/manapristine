# GEMINI.md

## Project Overview
Mana Pristine is a financial management system for a housing society (apartment complex). It manages income and expenditure by using Excel workbooks as the source of truth, processing them with Python to generate JSON datasets, and displaying the results via a static HTML dashboard hosted on GitHub Pages.

## Architecture & Data Flow
**Excel Workbooks** (`db/accounts/*.xlsx`) → **Python Scripts** (`report_builder/`) → **JSON Data** (`docs/*.json`) → **Static Dashboard** (`docs/index.html`)

### Core Components
- **Source Data (`db/`):**
    - `accounts/`: Excel workbooks containing financial records (one per FY).
    - `bankstatements/`: Raw bank statements used for updating collections.
    - `members.csv` & `occupants.csv`: Mappings for flats, owners, and residents.
    - `workbooks.json`: Configuration mapping financial years to their respective workbook files.
- **Processing Logic (`report_builder/`):**
    - `report_builder.py`: Main engine that reads Excel data and produces JSON datasets for the dashboard.
    - `update_collections.py`: Automates the update of collection sheets in Excel by parsing bank statements.
    - `refresh_fy.py` & `new_fy.py`: Utilities for transitioning between financial years.
    - `sync_members.py`: Synchronizes member data.
    - `update_water_consumption.py`: Processes water consumption reports.
- **Frontend (`docs/`):**
    - `index.html`: A self-contained dashboard (Vanilla JS/CSS) that visualizes the processed financial data.
    - `report-manifest.json`: Index of generated report files.

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
  python report_builder/update_collections.py db/bankstatements/2025-2026/March-2026.xls
  ```
- **Prepare Next FY:** Sets up a new workbook for the upcoming financial year.
  ```bash
  python report_builder/refresh_fy.py db/accounts/OLD_WORKBOOK.xlsx
  ```

## Project Conventions
- **Financial Year:** April 1st to March 31st (e.g., "2025-26").
- **Flat Normalization:** Flat numbers are always normalized to uppercase (e.g., "A101").
- **Workbook Naming:** Sheets follow specific patterns: `{Month}{Year}-EXPENSE`, `{Month}{Year}-COLLECTION`, `INCOME-EXPENSE-CYCLES`.
- **JSON Output:** All generated data must be stored in the `docs/` directory to be accessible by the dashboard.
- **No Build Step:** The frontend (`docs/index.html`) is designed to be served directly without any transpilation or bundling.

## Security
- **Portal Password:** Access to the dashboard is protected by a community password.
    - The plain-text password is stored in `db/workbooks.json` as `portal_password`.
    - `report_builder.py` hashes this password (SHA-256) and injects the hash into `docs/index.html` during the report generation process.
    - Residents enter the password on a "Community Access" screen; the browser validates the hash and stores a session token in `sessionStorage`.

## Report Builder Internals

**EXPENSE sheet water calculation:** When computing `total_water` (the divisor for water percentage), only sum column C for actual flat rows (F1-F16, G1-G16, S1-S16, T1-T16). Non-flat rows (CH, GYM, BSMT, MPFOWA, TOTAL) must be excluded — the TOTAL row contains a summary value that would double-count if included. This matches the workbook formula which uses a specific cell reference (`$C$70`) pointing to `=SUM(C6:C69)` (flat rows only).
