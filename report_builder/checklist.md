# Monthly Report & Portal Update Checklist

This checklist outlines the end-to-end procedure for processing monthly society accounts, calculating water consumption and late fines, generating portal reports, and publishing them to the GitHub Pages dashboard.

---

## Prerequisites & Environment Setup

- [ ] **Activate Python Virtual Environment**:
  ```powershell
  # Windows PowerShell:
  .\.venv\Scripts\activate
  ```
- [ ] **Ensure Dependencies are Installed**:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] **Close Excel**: Ensure the active FY workbook in `db/accounts/` is **closed** in Microsoft Excel before running Python update scripts to avoid file lock and write permission errors.

---

## Step 1: Ingest Raw Input Files

- [ ] **Bank Statement**:
  - Download monthly bank statement (SBI TSV/XLS format).
  - Place in `db/bankstatements/<YYYY-YYYY>/<Month>-<YYYY>.xls` (e.g., `db/bankstatements/2026-2027/Sep-2026.xls`).
- [ ] **WaterOn Consumption Report**:
  - Download consumption report from WaterOn portal.
  - Place in `db/wateron/<YY-YY>/Consumption Report <Month>-<YYYY>.xlsx` (e.g., `db/wateron/26-27/Consumption Report Sep-2026.xlsx`).
- [ ] **WaterOn Bill / Invoice (Optional)**:
  - Save invoice PDF to `db/wateron/<YY-YY>/<Month>-<YYYY>-invoice.pdf`.
- [ ] **Update Member / Occupant Records (if roster changed)**:
  - If any owner or tenant changes occurred, update `db/members.csv` or `db/occupants.csv`.
  - If `db/members.csv` was updated, synchronize it to the active workbook:
    ```bash
    python report_builder/sync_members.py
    ```

---

## Step 2: Water Meter Verification & Consumption Update

- [ ] **Validate Water Meter Readings & Identify Anomalies**:
  - Run the validation script to update average tracking and detect meter/leak spikes (>50% variance from historical flat average):
    ```bash
    python report_builder/validate_water_meter_reading.py "db/wateron/26-27/Consumption Report <Month>-<YYYY>.xlsx"
    ```
  - Review any highlighted flats with high variance in `db/wateron/avg-water-usage.xlsx`.
- [ ] **Update Water Consumption in Main Workbook**:
  - Run the update script to populate the `WATER USED IN LTRS` column in the `{Month}{Year}-EXPENSE` sheet:
    ```bash
    python report_builder/update_water_consumption.py "db/wateron/26-27/Consumption Report <Month>-<YYYY>.xlsx"
    ```

---

## Step 3: Update Collections from Bank Statement

- [ ] **Generate Processing Report (Option 1)**:
  - Run the collection updater in interactive mode:
    ```bash
    python report_builder/update_collections.py db/bankstatements/<YYYY-YYYY>/<Month>-<YYYY>.xls
    ```
  - Select **Option 1** to parse bank credits and match transactions against flat owners/occupants.
- [ ] **Review Processing CSV**:
  - Open the generated `*_processing_report_*.csv`.
  - Inspect rows marked as `NOT MATCHED`.
  - Fill in the correct flat identifier (e.g. `F1`, `G12`, `S5`, `T16`) for valid maintenance payments.
  - Leave non-maintenance credits (e.g., interest, deposits) blank or remove them.
  - Save and close the CSV.
- [ ] **Update Workbook Collections (Option 2)**:
  - Re-run the script:
    ```bash
    python report_builder/update_collections.py db/bankstatements/<YYYY-YYYY>/<Month>-<YYYY>.xls
    ```
  - Select **Option 2** to inject payment amounts and transaction dates into the `{Month}{Year}-COLLECTION` sheet.
- [ ] **(Optional) Generate Payment Tracking Sheet for Audit**:
  ```bash
  python report_builder/track_payments.py db/bankstatements/<YYYY-YYYY>/<Month>-<YYYY>.xls
  ```
  - Produces `tracking_sheet.xlsx` for auditing payment dates, amounts, and flat-level reconciliation.

---

## Step 4: Expense Entry & Excel Formula Recalculation

- [ ] **Enter Incurred Expenses in Excel**:
  - Open the active FY workbook (e.g. `db/accounts/2026-2027-INCOME-EXPENDITURE-ACCOUNT-*.xlsx`) in Microsoft Excel.
  - Go to the current `{Month}{Year}-EXPENSE` sheet.
  - Enter the monthly expense line items (Electricity/BESCOM, Water Tankers, Security, Housekeeping, Waste Management, STP/DG, Repairs, etc.).
  - Verify formulas in the expense sheet (shared expense ÷ 64, total expenses).
- [ ] **Save in Excel to Refresh Formula Cache (CRITICAL)**:
  - Press <kbd>Ctrl</kbd> + <kbd>S</kbd> in Microsoft Excel to evaluate and cache all formula values (`<v>` XML tags).
  - Close Microsoft Excel.
  > [!IMPORTANT]
  > Python scripts only read cached formula values evaluated by Excel (`data_only=True`). If you don't save in Excel first, scripts will fail with missing formula value errors.

---

## Step 5: Late Payment Fine Calculation

- [ ] **Apply Late Payment Fines**:
  - Run the late fine script to evaluate the previous month's payment status, check cumulative dues, and apply fines:
    ```bash
    python report_builder/update_late_payment_fine.py
    ```
  - *Note: To customize the fine amount (default is Rs 1,000), use `--fine <amount>`.*
- [ ] **Save in Excel Again**:
  - Open the workbook in Microsoft Excel to inspect the applied fines and updated summary formulas.
  - Press <kbd>Ctrl</kbd> + <kbd>S</kbd> and close Microsoft Excel to persist updated formula caches.

---

## Step 6: Configure Workbooks Registry & Generate Reports

- [ ] **Update `db/workbooks.json`**:
  - Update `"cutoff-date-for-collection"` to the last day of the reporting month (e.g., `"2026-10-31"`).
  - Confirm the `"workbook"` path matches the current active workbook.
- [ ] **Generate JSON Reports for Dashboard**:
  - Run the main report generator from project root or `report_builder/`:
    ```bash
    python report_builder/report_builder.py
    ```
  - Verify terminal output shows 64 reports generated for each FY and manifest updated:
    ```text
    FY 2025-26: generated 64 report(s) at ...\docs\report-data-2025-26.json
    FY 2026-27: generated 64 report(s) at ...\docs\report-data-2026-27.json
    Manifest written to ...\docs\report-manifest.json
    Portal password hash is already up to date.
    ```

---

## Step 7: Local Quality Assurance & Portal Verification

- [ ] **Open Portal Locally**:
  - Open `docs/index.html` in your web browser (or run `python -m http.server 8000 --directory docs` and visit `http://localhost:8000`).
- [ ] **Verify Authentication**:
  - Log in using the community password defined in `db/workbooks.json`.
- [ ] **Review Dashboard Metrics**:
  - Verify the new month appears in the month selection dropdown.
  - Cross-check society totals (Total Income, Total Expenses, Society Balance) with the Excel workbook summary.
  - Review Defaulters and Excess Payments tabs to ensure figures match expected balances.
  - Spot-check 2–3 individual flat statements (e.g. `F1`, `G10`, `T16`) for accurate water charges, fixed expense split, late fines, and payments.

---

## Step 8: Deploy to GitHub Pages

- [ ] **Review Git Status**:
  ```bash
  git status
  ```
- [ ] **Stage & Commit Changes**:
  ```bash
  git add db/ docs/ report_builder/
  git commit -m "Update <Month> <YYYY> accounts and portal reports"
  ```
- [ ] **Push to Remote**:
  ```bash
  git push origin main
  ```
- [ ] **Verify Live Portal**:
  - Navigate to the GitHub Pages URL: `https://<org_or_username>.github.io/manapristine/`
  - Confirm the live portal reflects the newly published data and statements.
