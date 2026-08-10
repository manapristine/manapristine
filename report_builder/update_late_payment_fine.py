"""
Late Payment Fine Update Script

Overview:
---------
This script automates the calculation and application of late payment fines in society
financial workbooks. It inspects flat-wise maintenance payments in the immediately preceding
month collection sheet ('<prev_month>-COLLECTION') and updates the 'LATE PAYMENT FINE' column in
the current month expense sheet ('<curr_month>-EXPENSE').

It also verifies and updates the Excel formula in the 'TOTAL EXPENSE TO BE PAID' column across
all expense sub-sheets so that 'LATE PAYMENT FINE' is fully included alongside all other expense heads.

Rule & Policy:
--------------
- 1-Month Look Back Only: The late payment fee for a given month is NOT cumulative across
  multiple past months. It considers ONLY the immediately preceding month.
- Fixed Fine: If payment was missed (Total is null / 0) in the previous month's COLLECTION sheet,
  a fine of Rs 1,000 (or configured fine amount) is applied in the current month's EXPENSE sheet.
- On-Time Payment: If payment was received in the previous month, the fine in the current month is Rs 0.

Pre-conditions:
---------------
1. Workbook Structure:
   The target society financial workbook MUST exist and contain paired monthly collection and
   expense sheets (e.g., 'Apr2026-COLLECTION' and 'May2026-EXPENSE').

2. Collection Sheet Structure:
   Each '<month>-COLLECTION' sheet MUST contain flat numbers in Column A (1) and payment amount cells
   (Columns 3, 5, 7, 9) / 'Total' column indicating the total maintenance received for that flat in that month.

3. Expense Sheet Structure:
   Each '<month>-EXPENSE' sheet header row (Row 2) MUST contain a column named 'LATE PAYMENT FINE'
   and a column named 'TOTAL EXPENSE TO BE PAID'.

4. File Lock / Write Access:
   The target society financial workbook MUST NOT be open in Microsoft Excel or locked by another application.

Key Configurations & Assumptions:
---------------------------------
- DEFAULT_FINE_PER_MONTH: Rs 1,000 per month of non-payment.
- Unpaid Determination: A flat is considered unpaid in a collection month if its 'Total' cell value
  and payment amount cells (Columns C, E, G, I) are None, empty, or 0.

CLI Usage:
----------
1. Basic Usage (uses default active workbook from db/workbooks.json):
   python report_builder/update_late_payment_fine.py

2. Explicit Workbook Path:
   python report_builder/update_late_payment_fine.py "db/accounts/2026-2027-INCOME-EXPENDITURE-ACCOUNT-8.10.26-gold.xlsx"

3. Custom Fine Amount (e.g. Rs 500 per month):
   python report_builder/update_late_payment_fine.py "path/to/workbook.xlsx" --fine 500

4. Help Menu:
   python report_builder/update_late_payment_fine.py --help

Exit Codes:
-----------
  0: Success (workbook updated successfully)
  1: Failure (missing file, missing sheet/column, permission error)
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import openpyxl
from openpyxl.utils import get_column_letter

# Project Root and Default Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKBOOKS_JSON = PROJECT_ROOT / "db" / "workbooks.json"
DEFAULT_FINE_PER_MONTH = 1000  # Rs 1,000 flat fine for missed payment in previous month

def normalize_flat(flat):
    """Normalize flat identifiers to consistent uppercase standard (e.g. F1, G16, CH)."""
    if flat is None:
        return ""
    flat = str(flat).strip().upper()
    mapping = {
        'C H': 'CH',
        'C GYM': 'GYM',
        'CBR': 'BSMT'
    }
    flat = mapping.get(flat, flat.replace(" ", ""))
    flat = re.sub(r'^([A-Z])0+(\d+)$', r'\1\2', flat)
    return flat

def get_active_workbook_path():
    """Retrieve default active financial workbook path from db/workbooks.json."""
    if not WORKBOOKS_JSON.exists():
        print(f"Error: workbooks.json not found at {WORKBOOKS_JSON}")
        return None
    with open(WORKBOOKS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for fy_key in ["2026-27", "2025-26"]:
        if fy_key in data and "workbook" in data[fy_key]:
            wb_rel = data[fy_key]["workbook"]
            wb_path = PROJECT_ROOT / wb_rel
            if wb_path.exists():
                return wb_path
    
    for fy_key, cfg in data.items():
        if isinstance(cfg, dict) and "workbook" in cfg:
            wb_path = PROJECT_ROOT / cfg["workbook"]
            if wb_path.exists():
                return wb_path
    return None

def find_sheet(wb, candidates):
    """Find sheet name in workbook matching candidate list."""
    for cand in candidates:
        if cand in wb.sheetnames:
            return cand
    return None

def parse_fy_months_from_sheetnames(sheetnames):
    """Detect start year and return full 12-month FY sequence (April to March) as (month, year) tuples."""
    years = sorted({int(y) for s in sheetnames for y in re.findall(r'\d{4}', s)})
    if not years:
        start_year = datetime.now().year
    else:
        start_year = years[0]
    
    seq = [(m, start_year) for m in range(4, 13)] + [(m, start_year + 1) for m in range(1, 4)]
    return seq

def is_flat_paid_in_collection_row(ws_c, row_idx, total_col_idx):
    """Determine if maintenance payment was received for flat in collection sheet row."""
    total_val = ws_c.cell(row=row_idx, column=total_col_idx).value
    
    # 1. Check direct numeric total cell value if available
    if isinstance(total_val, (int, float)):
        return total_val > 0

    # 2. If Total cell contains formula string or None, inspect payment amount columns (3, 5, 7, 9)
    pmt_sum = 0.0
    for col_idx in (3, 5, 7, 9):
        val = ws_c.cell(row=row_idx, column=col_idx).value
        if isinstance(val, (int, float)) and val > 0:
            pmt_sum += float(val)
        elif isinstance(val, str):
            clean_str = re.sub(r'[^0-9.]', '', val.strip())
            if clean_str:
                try:
                    num = float(clean_str)
                    if num > 0:
                        pmt_sum += num
                except ValueError:
                    pass
    
    return pmt_sum > 0

def ensure_total_expense_formulas(wb):
    """
    Ensure the formula in 'TOTAL EXPENSE TO BE PAID' column includes all expense heads
    (from Column 10/J up to the LATE PAYMENT FINE column) across all EXPENSE sheets.

    :param wb: openpyxl Workbook object
    :return: int number of formula cells updated
    """
    formula_updates = 0
    non_flat_ids = {"TOTAL", "CH", "GYM", "BSMT", "MPFOWA"}

    for s in wb.sheetnames:
        if 'EXPENSE' in s and s != 'ANNUAL-EXPENSE-DETAILS':
            ws = wb[s]
            headers = [ws.cell(2, c).value for c in range(1, ws.max_column + 1)]
            
            total_col_idx = None
            for idx, h in enumerate(headers, start=1):
                if h and 'TOTAL EXPENSE TO BE PAID' in str(h).upper():
                    total_col_idx = idx
                    break
            
            if total_col_idx and total_col_idx > 10:
                last_head_col_letter = get_column_letter(total_col_idx - 1)
                
                for r in range(3, ws.max_row + 1):
                    flat_val = ws.cell(r, 1).value
                    flat_id = normalize_flat(flat_val)
                    if not flat_id or flat_id in non_flat_ids:
                        continue

                    # Build Excel sum formula: =SUM(J{r}:{last_head_col_letter}{r})*$B$2
                    target_formula = f"=SUM(J{r}:{last_head_col_letter}{r})*$B$2"
                    curr_formula = ws.cell(r, total_col_idx).value

                    if curr_formula != target_formula:
                        ws.cell(r, total_col_idx).value = target_formula
                        formula_updates += 1

    return formula_updates

def update_late_payment_fines(workbook_path, fine_per_month=DEFAULT_FINE_PER_MONTH):
    """
    Inspect immediately preceding month collection sheet and update LATE PAYMENT FINE in expense sheets.
    Also ensures formulas in TOTAL EXPENSE TO BE PAID include LATE PAYMENT FINE across all expense sub-sheets.

    :param workbook_path: Path to Excel financial workbook.
    :param fine_per_month: Late fee for missed payment in previous month (default: Rs 1000).
    :return: bool success
    """
    wb_path = Path(workbook_path)
    if not wb_path.exists() and not wb_path.is_absolute():
        alt_path = PROJECT_ROOT / workbook_path
        if alt_path.exists():
            wb_path = alt_path

    if not wb_path.exists():
        print(f"Error: Workbook file not found: {wb_path}")
        return False

    print(f"Opening workbook: {wb_path.name}")
    try:
        wb = openpyxl.load_workbook(wb_path)
    except PermissionError:
        print(f"Error: Permission denied opening '{wb_path.name}'. Ensure file is closed in Excel.")
        return False

    month_seq = parse_fy_months_from_sheetnames(wb.sheetnames)
    updates_total = 0
    sheet_summaries = []
    non_flat_ids = {"TOTAL", "CH", "GYM", "BSMT", "MPFOWA"}

    try:
        # 1. Update Late Payment Fines
        for idx in range(1, len(month_seq)):
            prev_m, prev_yr = month_seq[idx - 1]
            curr_m, curr_yr = month_seq[idx]

            prev_abbr = datetime(prev_yr, prev_m, 1).strftime('%b')
            prev_full = datetime(prev_yr, prev_m, 1).strftime('%B')
            curr_abbr = datetime(curr_yr, curr_m, 1).strftime('%b')
            curr_full = datetime(curr_yr, curr_m, 1).strftime('%B')

            collection_sheet_name = find_sheet(wb, [f"{prev_abbr}{prev_yr}-COLLECTION", f"{prev_full}{prev_yr}-COLLECTION"])
            expense_sheet_name = find_sheet(wb, [f"{curr_abbr}{curr_yr}-EXPENSE", f"{curr_full}{curr_yr}-EXPENSE"])

            if not expense_sheet_name:
                continue

            # Read previous month collection status (1-month look back)
            prev_month_missed = {}
            if collection_sheet_name:
                ws_c = wb[collection_sheet_name]
                total_col_idx = 11  # Column K is default Total column
                header_c = [str(ws_c.cell(1, col).value).strip().upper() if ws_c.cell(1, col).value else "" for col in range(1, ws_c.max_column + 1)]
                if "TOTAL" in header_c:
                    total_col_idx = header_c.index("TOTAL") + 1

                for r in range(2, ws_c.max_row + 1):
                    flat_val = ws_c.cell(row=r, column=1).value
                    flat_id = normalize_flat(flat_val)
                    if not flat_id or flat_id in non_flat_ids:
                        continue

                    paid = is_flat_paid_in_collection_row(ws_c, r, total_col_idx)
                    prev_month_missed[flat_id] = not paid

            # Update current month expense sheet
            ws_e = wb[expense_sheet_name]
            header_e = [str(ws_e.cell(2, col).value).strip().upper() if ws_e.cell(2, col).value else "" for col in range(1, ws_e.max_column + 1)]
            
            if "LATE PAYMENT FINE" not in header_e:
                print(f"Warning: 'LATE PAYMENT FINE' column not found in '{expense_sheet_name}'. Skipping.")
                continue

            fine_col_idx = header_e.index("LATE PAYMENT FINE") + 1
            sheet_updates = 0
            flagged_in_sheet = []

            for r in range(3, ws_e.max_row + 1):
                flat_val = ws_e.cell(row=r, column=1).value
                flat_id = normalize_flat(flat_val)
                if not flat_id or flat_id in non_flat_ids:
                    continue

                missed = prev_month_missed.get(flat_id, False)
                fine_amount = fine_per_month if missed else 0
                fine_cell = ws_e.cell(row=r, column=fine_col_idx)
                
                existing_val = fine_cell.value
                try:
                    clean_str = re.sub(r'[^0-9.]', '', str(existing_val)) if existing_val is not None else ""
                    existing_num = float(clean_str) if clean_str else 0.0
                except (ValueError, TypeError):
                    existing_num = -1.0

                if existing_num != float(fine_amount):
                    fine_cell.value = fine_amount
                    sheet_updates += 1
                    updates_total += 1

                if fine_amount > 0:
                    flagged_in_sheet.append((flat_id, fine_amount))

            sheet_summaries.append((expense_sheet_name, collection_sheet_name, sheet_updates, flagged_in_sheet))

        # 2. Ensure all TOTAL EXPENSE TO BE PAID formulas include LATE PAYMENT FINE
        formula_updates = ensure_total_expense_formulas(wb)

        if updates_total > 0 or formula_updates > 0 or sheet_summaries:
            try:
                wb.save(wb_path)
                print(f"\nSuccessfully saved updated workbook: '{wb_path.name}'")
                print(f"Total Late Payment Fine updates applied: {updates_total}")
                print(f"Total EXPENSE formula updates applied: {formula_updates}\n")

                for sheet_name, col_name, count, flagged in sheet_summaries:
                    print(f"--- Sheet: {sheet_name} (Based on {col_name or 'N/A'}) ---")
                    if flagged:
                        print(f"  {'Flat':<8} | {'Previous Month Payment Status':<30} | {'Late Payment Fine (Rs)':<22}")
                        print("  " + "-" * 65)
                        for fid, fine in flagged:
                            print(f"  {fid:<8} | {'MISSED':<30} | Rs {fine:<20,d}")
                    else:
                        print("  No late payment fines applicable (All flats paid on time in previous month).")
                    print()
                return True
            except PermissionError:
                print(f"Error: Could not save '{wb_path.name}'. File is locked/open in Excel.")
                return False
        else:
            print("\nNo updates were required.")
            return True
    finally:
        wb.close()

def main():
    parser = argparse.ArgumentParser(description="Update LATE PAYMENT FINE column in expense sheets based on 1-month lookback collection status.")
    parser.add_argument(
        "accounts_file",
        nargs="?",
        default=None,
        help="Path to the society financial accounts Excel workbook file."
    )
    parser.add_argument(
        "--fine", "-f",
        type=int,
        default=DEFAULT_FINE_PER_MONTH,
        help=f"Late payment fine amount for missed payment in previous month in Rupees (default: Rs {DEFAULT_FINE_PER_MONTH})."
    )
    args = parser.parse_args()

    wb_path = args.accounts_file
    if wb_path is None:
        wb_path = get_active_workbook_path()
        if wb_path is None:
            print("Error: Could not resolve default workbook path from db/workbooks.json")
            sys.exit(1)

    success = update_late_payment_fines(wb_path, fine_per_month=args.fine)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
