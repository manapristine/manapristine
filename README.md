# Mana Pristine - Portal Report Generation Guide

This repository contains the backend processing and frontend static dashboard for the Mana Pristine housing society financial management system. 

Follow the steps below to process raw monthly statements, update the source-of-truth Excel workbooks, and generate the final report for the portal.

---

## Steps to Generate the Final Portal Report

### 1. Setup Environment
Ensure you have the virtual environment activated and dependencies installed:
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Update Water Consumption (Optional/Monthly)
If you have a monthly WaterOn report, run the script to update the water consumption values in the EXPENSE sheets:
```bash
python report_builder/update_water_consumption.py <path_to_water_consumption_report.xlsx>
```

### 3. Update Bank Collections
To update monthly flat collections from a bank statement, use the interactive `update_collections.py` script:
```bash
python report_builder/update_collections.py <path_to_bank_statement.xls>
```

When prompted:
1. **Choose Option `1` (Create processing report):** This parses the statement, performs heuristic mapping to match transactions to flat numbers, and outputs a `*_processing_report_*.csv` file.
2. **Review the CSV:** Open the generated processing report CSV in the statement's folder and manually fill in the correct flat numbers for any `NOT MATCHED` rows.
3. **Choose Option `2` (Update Excel from latest processing report):** Run the command again, choose Option `2`, and the script will write the transaction dates and amounts into the appropriate month's COLLECTION sheet in the active workbook.

### 4. Recalculate Formulas (Crucial)
Open the updated Excel workbook (e.g., `db/accounts/2026-2027-INCOME-EXPENDITURE-ACCOUNT-*.xlsx`) in Excel, LibreOffice, or Google Sheets to trigger the calculation of formulas, then **save the file**. 

> [!IMPORTANT]
> The report builder relies on cached formula evaluation results inside the workbook. Saving the workbook in Excel or Sheets is necessary to refresh these cached values before generating the portal report.

### 5. Generate Portal JSON Datasets
Run the main report builder to read the workbook data and compile the JSON datasets for the dashboard:
```bash
python report_builder/report_builder.py
```
This generates/updates the JSON files and the manifest under the `docs/` folder (which serves as the source of truth for the frontend portal).

### 6. Commit and Publish to GitHub Pages
To publish the updated portal to the web, commit the modified Excel workbooks and generated JSON assets, then push them to GitHub:
```bash
# Stage the modified accounts and generated docs
git add db/accounts/ docs/

# Commit and push
git commit -m "Update portal report with latest month collections and expenses"
git push origin main
```
The static site will deploy automatically via GitHub Pages.
