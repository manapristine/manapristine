"""
Payment Tracking Script for Mana Pristine

Overview:
---------
This script parses a bank statement (e.g., TSV/Excel export from SBI), matches credit
transactions against flat owners (members.csv) and occupants/tenants (occupants.csv)
using fuzzy matching rules copied and enhanced from report_builder/update_collections.py,
and generates an Excel tracking sheet ('tracking_sheet.xlsx') marking how much amount
and when each flat has paid.

Usage:
------
python report_builder/track_payments.py <path_to_bank_statement> [-o tracking_sheet.xlsx]

Example:
--------
python report_builder/track_payments.py "C:\\github\\manapristine\\db\\bankstatements\\2026-2027\\aug26\\aug-2026.xls"
"""

import os
import sys
import re
import csv
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Ensure stdout and stderr handle utf-8 safely in Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass



def resolve_file_path(path_str, default_subpath):
    """Resolve file path from user input, project root, or current directory."""
    if path_str and Path(path_str).exists():
        return Path(path_str).resolve()

    project_root = Path(__file__).resolve().parent.parent
    candidate1 = project_root / default_subpath
    if candidate1.exists():
        return candidate1.resolve()

    candidate2 = Path.cwd() / default_subpath
    if candidate2.exists():
        return candidate2.resolve()

    if path_str:
        return Path(path_str).resolve()
    return candidate1


def load_mappings(members_path=None, occupants_path=None):
    """
    Load flat-to-owner and flat-to-occupant mappings from CSV files.
    Constructs name parts, full names, and search lookup tables.
    """
    members_file = resolve_file_path(members_path, Path("db") / "members.csv")
    occupants_file = resolve_file_path(occupants_path, Path("db") / "occupants.csv")

    if not members_file.exists():
        raise FileNotFoundError(f"Members mapping file not found: {members_file}")

    flat_to_names = defaultdict(set)
    name_part_to_flats = defaultdict(set)
    flat_to_name_parts = defaultdict(list)
    flat_to_member, flat_to_occupant = {}, {}
    owner_names = defaultdict(set)
    occupant_names = defaultdict(set)
    all_flats_ordered = []

    def process_csv(path, target_map=None, role_names=None, track_order=False):
        if not path.exists():
            return
        with open(path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flat_raw = row.get("flat", "").strip()
                name = row.get("name", "").strip()
                if not flat_raw:
                    continue
                flat = flat_raw.lower()
                if track_order and flat.upper() not in all_flats_ordered:
                    all_flats_ordered.append(flat.upper())

                if not name:
                    continue
                if target_map is not None:
                    target_map[flat] = name

                sub_names = [n.strip() for n in re.split(r"/|&", name)]
                for sn in sub_names:
                    if not sn:
                        continue
                    norm_full = re.sub(r"[^a-z0-9]", "", sn.lower())
                    if norm_full:
                        flat_to_names[flat].add(norm_full)
                        if role_names is not None:
                            role_names[flat].add(norm_full)
                    parts = [re.sub(r"[^a-z0-9]", "", p.lower()) for p in sn.split()]
                    parts = [p for p in parts if p]
                    if parts:
                        flat_to_name_parts[flat].append(parts)
                        for p in parts:
                            if len(p) >= 3:
                                name_part_to_flats[p].add(flat)

    process_csv(members_file, flat_to_member, owner_names, track_order=True)
    if occupants_file.exists():
        process_csv(occupants_file, flat_to_occupant, occupant_names, track_order=False)

    # Fallback flat ordering if members file didn't define full list
    if not all_flats_ordered:
        for prefix in ["F", "G", "S", "T"]:
            for num in range(1, 17):
                all_flats_ordered.append(f"{prefix}{num}")

    return {
        "flat_to_names": flat_to_names,
        "name_part_to_flats": name_part_to_flats,
        "flat_to_name_parts": flat_to_name_parts,
        "flat_to_member": flat_to_member,
        "flat_to_occupant": flat_to_occupant,
        "owner_names": owner_names,
        "occupant_names": occupant_names,
        "all_flats": all_flats_ordered,
    }


def parse_bank_statement(filepath):
    """
    Parse bank statement into pandas DataFrame.
    Supports tab-separated text/CSV (SBI .xls exports), standard CSV, and Excel formats.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Bank statement file not found: {path}")

    header_row = -1
    is_text = True
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                line_lower = line.lower()
                if (
                    ("txn date" in line_lower or "date" in line_lower)
                    and ("description" in line_lower or "particulars" in line_lower or "narration" in line_lower)
                    and ("credit" in line_lower or "deposit" in line_lower or "cr" in line_lower)
                ):
                    header_row = i
                    break
    except Exception:
        is_text = False

    if is_text and header_row != -1:
        try:
            df = pd.read_csv(path, sep="\t", skiprows=header_row, encoding="utf-8", on_bad_lines="skip")
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception:
            pass

    try:
        skip = header_row if header_row != -1 else 0
        df = pd.read_csv(path, skiprows=skip, encoding="utf-8", on_bad_lines="skip")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        pass

    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        raise ValueError(f"Failed to parse bank statement file {path.name}: {e}")


def find_flat_in_description(description, mappings):
    """
    Match transaction description against flats, owner names, or occupant names.
    Returns (matched_flat_str, match_reason) or (None, 'Unmatched').
    """
    flat_to_names = mappings["flat_to_names"]
    name_part_to_flats = mappings["name_part_to_flats"]
    flat_to_name_parts = mappings["flat_to_name_parts"]
    known_flats = set(flat_to_names.keys())
    owner_names = mappings.get("owner_names", {})
    occupant_names = mappings.get("occupant_names", {})

    description_lower = description.lower()
    sorted_flats = sorted(known_flats, key=len, reverse=True)

    # Helper to check if match belongs to owner or occupant
    def get_role_match_type(flat):
        norm_desc = re.sub(r"[^a-z0-9]", "", description_lower)
        desc_words = {w for w in re.split(r"[^a-z0-9]", description_lower) if w}

        if flat in owner_names:
            for on in owner_names[flat]:
                if len(on) >= 4 and (on in norm_desc or any(len(p) >= 4 and p in desc_words for p in on.split())):
                    return "Owner Name match"
        if flat in occupant_names:
            for ocn in occupant_names[flat]:
                if len(ocn) >= 4 and (ocn in norm_desc or any(len(p) >= 4 and p in desc_words for p in ocn.split())):
                    return "Occupant Name match"
        return "Name match"

    # 1. Flat Matching in Description
    for f in sorted_flats:
        if re.search(r"(?i)(?:^|[^a-z0-9]|flat)" + re.escape(f) + r"(?:[^a-z0-9]|$)", description_lower):
            return f, "Flat # in description"
        if len(f) >= 2 and f[0].isalpha() and f[1:].isdigit():
            if re.search(r"(?i)(?:^|[^a-z0-9]|flat)" + re.escape(f) + r"(?:[^0-9]|$)", description_lower):
                return f, "Flat # in description"

    # 2. Name Matching
    norm_desc = re.sub(r"[^a-z0-9]", "", description_lower)
    desc_words = {w for w in re.split(r"[^a-z0-9]", description_lower) if w}

    # A. Full name match
    all_full_names = []
    for flat, names in flat_to_names.items():
        for n in names:
            all_full_names.append((n, flat))
    all_full_names.sort(key=lambda x: len(x[0]), reverse=True)
    for fn, f in all_full_names:
        if len(fn) >= 6 and fn in norm_desc:
            return f, get_role_match_type(f)

    # B. Part-based match with Conflict Resolution
    potential_flats = defaultdict(float)
    for word in desc_words:
        if len(word) < 4:
            continue
        if word in name_part_to_flats:
            for f in name_part_to_flats[word]:
                potential_flats[f] = max(potential_flats[f], 1.0)
        for part, flats in name_part_to_flats.items():
            if (len(word) >= 4 and part.startswith(word)) or (len(part) >= 4 and word.startswith(part)):
                for f in flats:
                    potential_flats[f] = max(potential_flats[f], 0.8)

    if potential_flats:
        matched = sorted(potential_flats.items(), key=lambda x: x[1], reverse=True)
        top_score = matched[0][1]
        candidates = [f for f, s in matched if s == top_score]
        if len(candidates) == 1:
            return candidates[0], get_role_match_type(candidates[0])

        # Resolve Conflicts
        best_matches = []
        max_score = -1
        for f in candidates:
            for parts in flat_to_name_parts[f]:
                score = sum(
                    1
                    for p in parts
                    if any(
                        p == dw
                        or (len(dw) >= 3 and p.startswith(dw))
                        or (len(p) >= 4 and dw.startswith(p))
                        for dw in desc_words
                    )
                )
                if score > max_score:
                    max_score, best_matches = score, [(f, parts, score)]
                elif score == max_score:
                    best_matches.append((f, parts, score))

        if len(best_matches) == 1:
            return best_matches[0][0], get_role_match_type(best_matches[0][0])
        unique_names = {" ".join(m[1]) for m in best_matches}
        if len(unique_names) == 1:
            return best_matches[0][0], get_role_match_type(best_matches[0][0])
        else:
            return None, "Ambiguous Name match"

    # 3. Fallback
    if "@" not in description_lower:
        for f in sorted_flats:
            if f[0].isalpha() and f in description_lower and len(f) >= 2 and f[1:].isdigit():
                return f, "Fallback flat match"

    return None, "Unmatched"


def create_tracking_workbook(transactions, mappings, output_path):
    """
    Generate Excel workbook with Payment Tracking, All Transactions, and Unmatched sheets.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    font_family = "Segoe UI"
    title_font = Font(name=font_family, size=14, bold=True, color="1F4E78")
    subtitle_font = Font(name=font_family, size=10, italic=True, color="595959")
    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    data_font = Font(name=font_family, size=10)
    bold_data_font = Font(name=font_family, size=10, bold=True)
    summary_font = Font(name=font_family, size=11, bold=True, color="1F4E78")

    paid_status_font = Font(name=font_family, size=10, bold=True, color="0E6251")
    pending_status_font = Font(name=font_family, size=10, bold=True, color="922B21")

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    subtotal_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    paid_fill = PatternFill(start_color="D4EFDF", end_color="D4EFDF", fill_type="solid")
    pending_fill = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    double_bottom_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="1F4E78"),
        bottom=Side(style="double", color="1F4E78"),
    )

    currency_format = "#,##0.00"

    # Organize payments by flat
    flat_payments = defaultdict(list)
    for txn in transactions:
        if txn["flat"]:
            flat_payments[txn["flat"].upper()].append(txn)

    # Determine max payments for any flat (at least 3 pairs)
    max_payments = max([len(v) for v in flat_payments.values()] + [3])

    # ----------------------------------------------------
    # SHEET 1: Payment Tracking
    # ----------------------------------------------------
    ws_track = wb.create_sheet(title="Payment Tracking")
    ws_track.views.sheetView[0].showGridLines = True

    # Title block
    ws_track.merge_cells("A1:K1")
    ws_track["A1"] = "MANA PRISTINE - FLAT-WISE MAINTENANCE PAYMENT TRACKING"
    ws_track["A1"].font = title_font
    ws_track["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws_track.merge_cells("A2:K2")
    ws_track["A2"] = f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} | Source: Bank Statement"
    ws_track["A2"].font = subtitle_font
    ws_track["A2"].alignment = Alignment(horizontal="left", vertical="center")

    # Table Headers
    base_headers = [
        "Flat #",
        "Owner Name (Member)",
        "Occupant Name (Tenant)",
        "Status",
        "Total Paid (Rs.)",
        "Payments Count",
    ]
    payment_headers = []
    for i in range(1, max_payments + 1):
        payment_headers.extend([f"Payment {i} Amount (Rs.)", f"Payment {i} Date"])

    all_track_headers = base_headers + payment_headers
    header_row_idx = 4

    for col_idx, h_text in enumerate(all_track_headers, start=1):
        cell = ws_track.cell(row=header_row_idx, column=col_idx, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_track.row_dimensions[header_row_idx].height = 28

    current_row = header_row_idx + 1
    flats_order = mappings["all_flats"]
    flat_to_member = mappings["flat_to_member"]
    flat_to_occupant = mappings["flat_to_occupant"]

    total_amount_collected = 0.0
    paid_count = 0
    pending_count = 0

    for flat_code in flats_order:
        flat_key = flat_code.lower()
        owner = flat_to_member.get(flat_key, "")
        occupant = flat_to_occupant.get(flat_key, "")
        pmts = flat_payments.get(flat_code, [])

        flat_total = sum(p["amount"] for p in pmts)
        total_amount_collected += flat_total
        p_count = len(pmts)

        is_paid = flat_total > 0
        if is_paid:
            paid_count += 1
            status_text = "PAID"
        else:
            pending_count += 1
            status_text = "PENDING"

        row_cells = [
            flat_code,
            owner,
            occupant,
            status_text,
            flat_total,
            p_count,
        ]

        # Populate payments
        for i in range(max_payments):
            if i < len(pmts):
                row_cells.extend([pmts[i]["amount"], pmts[i]["date"]])
            else:
                row_cells.extend(["", ""])

        is_zebra = (current_row % 2 == 0)
        for col_idx, val in enumerate(row_cells, start=1):
            cell = ws_track.cell(row=current_row, column=col_idx, value=val)
            cell.font = data_font
            cell.border = thin_border
            if is_zebra:
                cell.fill = zebra_fill

            # Alignments & formats
            if col_idx == 1:  # Flat #
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = bold_data_font
            elif col_idx in [2, 3]:  # Names
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_idx == 4:  # Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if is_paid:
                    cell.font = paid_status_font
                    cell.fill = paid_fill
                else:
                    cell.font = pending_status_font
                    cell.fill = pending_fill
            elif col_idx == 5:  # Total Paid
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = currency_format
                cell.font = bold_data_font
            elif col_idx == 6:  # Count
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif (col_idx - 7) % 2 == 0:  # Payment Amount cols
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(val, (int, float)):
                    cell.number_format = currency_format
            elif (col_idx - 7) % 2 == 1:  # Payment Date cols
                cell.alignment = Alignment(horizontal="center", vertical="center")

        ws_track.row_dimensions[current_row].height = 20
        current_row += 1

    # Total Summary Row
    summary_row = current_row
    ws_track.merge_cells(f"A{summary_row}:C{summary_row}")
    cell_total_label = ws_track.cell(row=summary_row, column=1, value="TOTAL SUMMARY")
    cell_total_label.font = summary_font
    cell_total_label.alignment = Alignment(horizontal="center", vertical="center")

    cell_status_summary = ws_track.cell(
        row=summary_row, column=4, value=f"{paid_count} Paid / {pending_count} Pending"
    )
    cell_status_summary.font = bold_data_font
    cell_status_summary.alignment = Alignment(horizontal="center", vertical="center")

    cell_total_amt = ws_track.cell(
        row=summary_row, column=5, value=f"=SUM(E{header_row_idx + 1}:E{summary_row - 1})"
    )
    cell_total_amt.font = summary_font
    cell_total_amt.alignment = Alignment(horizontal="right", vertical="center")
    cell_total_amt.number_format = currency_format

    cell_total_count = ws_track.cell(
        row=summary_row, column=6, value=f"=SUM(F{header_row_idx + 1}:F{summary_row - 1})"
    )
    cell_total_count.font = summary_font
    cell_total_count.alignment = Alignment(horizontal="center", vertical="center")

    for col in range(1, len(all_track_headers) + 1):
        c = ws_track.cell(row=summary_row, column=col)
        c.border = double_bottom_border
        c.fill = subtotal_fill

    ws_track.row_dimensions[summary_row].height = 24

    # ----------------------------------------------------
    # SHEET 2: All Transactions (Statement Credit Log)
    # ----------------------------------------------------
    ws_txns = wb.create_sheet(title="All Transactions")
    ws_txns.views.sheetView[0].showGridLines = True

    # Title block
    ws_txns.merge_cells("A1:J1")
    ws_txns["A1"] = "BANK STATEMENT CREDIT TRANSACTIONS LOG"
    ws_txns["A1"].font = title_font
    ws_txns["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws_txns.merge_cells("A2:J2")
    ws_txns["A2"] = (
        f"Total Credit Transactions: {len(transactions)} | "
        f"Total Credits: Rs. {sum(t['amount'] for t in transactions):,.2f}"
    )
    ws_txns["A2"].font = subtitle_font
    ws_txns["A2"].alignment = Alignment(horizontal="left", vertical="center")

    txn_headers = [
        "#",
        "Txn Date",
        "Value Date",
        "Amount (Rs.)",
        "Matched Flat",
        "Owner Name",
        "Occupant Name",
        "Match Method",
        "Status",
        "Ref No. / Cheque No.",
        "Description",
    ]
    t_header_row = 4
    for col_idx, h_text in enumerate(txn_headers, start=1):
        cell = ws_txns.cell(row=t_header_row, column=col_idx, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_txns.row_dimensions[t_header_row].height = 28

    t_current_row = t_header_row + 1
    for idx, txn in enumerate(transactions, start=1):
        is_matched = bool(txn["flat"])
        flat_str = txn["flat"].upper() if is_matched else "NOT MATCHED"
        owner_name = txn["owner"]
        occupant_name = txn["occupant"]
        status_label = "MATCHED" if is_matched else "UNMATCHED"

        t_row = [
            idx,
            txn["date"],
            txn.get("value_date", ""),
            txn["amount"],
            flat_str,
            owner_name,
            occupant_name,
            txn["match_reason"],
            status_label,
            txn.get("ref_no", ""),
            txn["description"],
        ]

        is_zebra = (t_current_row % 2 == 0)
        for col_idx, val in enumerate(t_row, start=1):
            cell = ws_txns.cell(row=t_current_row, column=col_idx, value=val)
            cell.font = data_font
            cell.border = thin_border
            if is_zebra:
                cell.fill = zebra_fill

            if col_idx == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [2, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 4:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = currency_format
                cell.font = bold_data_font
            elif col_idx == 5:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = bold_data_font
            elif col_idx == 9:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if is_matched:
                    cell.font = paid_status_font
                    cell.fill = paid_fill
                else:
                    cell.font = pending_status_font
                    cell.fill = pending_fill
            elif col_idx == 11:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws_txns.row_dimensions[t_current_row].height = 20
        t_current_row += 1

    # Total row for transactions
    t_summary_row = t_current_row
    ws_txns.merge_cells(f"A{t_summary_row}:C{t_summary_row}")
    cell_tx_total_label = ws_txns.cell(row=t_summary_row, column=1, value="TOTAL")
    cell_tx_total_label.font = summary_font
    cell_tx_total_label.alignment = Alignment(horizontal="center", vertical="center")

    cell_tx_total_amt = ws_txns.cell(
        row=t_summary_row, column=4, value=f"=SUM(D{t_header_row + 1}:D{t_summary_row - 1})"
    )
    cell_tx_total_amt.font = summary_font
    cell_tx_total_amt.alignment = Alignment(horizontal="right", vertical="center")
    cell_tx_total_amt.number_format = currency_format

    for col in range(1, len(txn_headers) + 1):
        c = ws_txns.cell(row=t_summary_row, column=col)
        c.border = double_bottom_border
        c.fill = subtotal_fill

    ws_txns.row_dimensions[t_summary_row].height = 24

    # ----------------------------------------------------
    # SHEET 3: Unmatched Transactions (if any)
    # ----------------------------------------------------
    unmatched_txns = [t for t in transactions if not t["flat"]]
    if unmatched_txns:
        ws_unm = wb.create_sheet(title="Unmatched Transactions")
        ws_unm.views.sheetView[0].showGridLines = True

        ws_unm.merge_cells("A1:G1")
        ws_unm["A1"] = "UNMATCHED CREDIT TRANSACTIONS"
        ws_unm["A1"].font = title_font
        ws_unm["A1"].alignment = Alignment(horizontal="left", vertical="center")

        ws_unm.merge_cells("A2:G2")
        ws_unm["A2"] = (
            f"{len(unmatched_txns)} transactions could not be mapped to any flat automatically. "
            "Please review descriptions."
        )
        ws_unm["A2"].font = subtitle_font
        ws_unm["A2"].alignment = Alignment(horizontal="left", vertical="center")

        unm_headers = [
            "#",
            "Txn Date",
            "Amount (Rs.)",
            "Match Status",
            "Ref No. / Cheque No.",
            "Description",
            "Suggested Manual Flat #",
        ]
        u_header_row = 4
        for col_idx, h_text in enumerate(unm_headers, start=1):
            cell = ws_unm.cell(row=u_header_row, column=col_idx, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws_unm.row_dimensions[u_header_row].height = 28

        u_row_idx = u_header_row + 1
        for idx, ut in enumerate(unmatched_txns, start=1):
            u_row = [
                idx,
                ut["date"],
                ut["amount"],
                ut["match_reason"],
                ut.get("ref_no", ""),
                ut["description"],
                "",  # User can fill manual flat # here
            ]
            for col_idx, val in enumerate(u_row, start=1):
                cell = ws_unm.cell(row=u_row_idx, column=col_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                if col_idx == 3:
                    cell.number_format = currency_format
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif col_idx in [1, 2, 4]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

            ws_unm.row_dimensions[u_row_idx].height = 20
            u_row_idx += 1

        # Auto-adjust column widths for unmatched sheet
        for col in ws_unm.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_unm.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Auto-adjust column widths for Sheet 1 & Sheet 2
    for sheet in [ws_track, ws_txns]:
        for col in sheet.columns:
            col_letter = get_column_letter(col[0].column)
            # Find max length of cell contents ignoring title rows 1 & 2
            lengths = [len(str(cell.value or "")) for cell in col[2:]]
            max_len = max(lengths) if lengths else 10
            # Set minimum width and cap at 60 for long descriptions
            adjusted_width = min(max(max_len + 3, 12), 65)
            sheet.column_dimensions[col_letter].width = adjusted_width

    # Save workbook
    output_file = Path(output_path).resolve()
    wb.save(output_file)
    return output_file


def track_payments(statement_file, output_path=None, members_path=None, occupants_path=None):
    """
    Main processing workflow:
    1. Load mappings from db/members.csv and db/occupants.csv
    2. Parse bank statement credit transactions
    3. Match descriptions using rule-based and fuzzy logic
    4. Generate formatted Excel tracking_sheet.xlsx in the statement's directory
    """
    statement_path = Path(statement_file).resolve()
    if not statement_path.exists():
        raise FileNotFoundError(f"Bank statement file not found: {statement_file}")

    if not output_path:
        resolved_output = statement_path.parent / "tracking_sheet.xlsx"
    else:
        resolved_output = Path(output_path).resolve()

    print(f"\n=======================================================")
    print(f" Mana Pristine - Bank Statement Payment Tracker")
    print(f"=======================================================")
    print(f"Bank Statement File: {statement_path}")
    print(f"Output Target File : {resolved_output}")

    # 1. Load Mappings
    mappings = load_mappings(members_path, occupants_path)
    print(f"Loaded {len(mappings['all_flats'])} flats from directory.")
    print(f"Loaded {len(mappings['flat_to_member'])} owners and {len(mappings['flat_to_occupant'])} occupants.")

    # 2. Parse Bank Statement
    df = parse_bank_statement(statement_file)
    print(f"Parsed {len(df)} total statement rows.")

    def match_column(candidates):
        for c in df.columns:
            cleaned = str(c).lower().strip()
            if cleaned in candidates:
                return c
        for c in df.columns:
            cleaned = str(c).lower().strip()
            for cand in candidates:
                if cand in cleaned:
                    return c
        return None

    credit_col = match_column(["credit", "deposit", "cr", "cr.", "credit amount", "cr amount"])
    desc_col = match_column(["description", "particulars", "narration", "remarks", "transaction details"])
    date_col = match_column(["txn date", "transaction date", "date", "tx date"])
    val_date_col = match_column(["value date", "val date", "booking date"])
    ref_col = match_column(["ref no./cheque no.", "ref no", "reference no", "cheque no", "chq no", "utr"])

    if not credit_col:
        raise ValueError(
            f"Could not find 'Credit' column in bank statement. Available columns: {list(df.columns)}"
        )

    # 3. Process and Match Credit Transactions
    transactions = []
    total_credit_amount = 0.0
    matched_count = 0
    unmatched_count = 0

    flat_to_member = mappings["flat_to_member"]
    flat_to_occupant = mappings["flat_to_occupant"]

    for _, row in df.iterrows():
        c_val = row.get(credit_col)
        if pd.isna(c_val) or not str(c_val).strip():
            continue

        try:
            amount = float(str(c_val).replace(",", "").strip())
        except ValueError:
            continue

        if amount <= 0:
            continue

        total_credit_amount += amount
        desc = str(row.get(desc_col, "")).strip() if desc_col else ""
        tx_dt = str(row.get(date_col, "")).strip() if date_col else ""
        val_dt = str(row.get(val_date_col, "")).strip() if val_date_col else ""
        ref_no = str(row.get(ref_col, "")).strip() if ref_col else ""

        matched_flat, match_reason = find_flat_in_description(desc, mappings)
        if not matched_flat and ref_no:
            matched_flat, match_reason = find_flat_in_description(ref_no, mappings)
            if matched_flat:
                match_reason = f"{match_reason} (in Ref No)"

        if matched_flat:
            matched_count += 1
            flat_upper = matched_flat.upper()
            owner_name = flat_to_member.get(matched_flat.lower(), "")
            occupant_name = flat_to_occupant.get(matched_flat.lower(), "")
        else:
            unmatched_count += 1
            flat_upper = None
            owner_name = ""
            occupant_name = ""

        transactions.append(
            {
                "date": tx_dt,
                "value_date": val_dt,
                "amount": amount,
                "flat": flat_upper,
                "owner": owner_name,
                "occupant": occupant_name,
                "match_reason": match_reason,
                "description": desc,
                "ref_no": ref_no,
            }
        )

    # 4. Generate Output Excel
    try:
        saved_path = create_tracking_workbook(transactions, mappings, resolved_output)
    except PermissionError:
        print(f"\n[ERROR] Permission denied: Unable to write to '{resolved_output}'.")
        print("The file appears to be open in Microsoft Excel. Please close it and rerun.\n")
        raise

    # Compute Statistics
    flats_paid = len({t["flat"] for t in transactions if t["flat"]})
    flats_total = len(mappings["all_flats"])
    flats_pending = flats_total - flats_paid

    print(f"\n-------------------------------------------------------")
    print(f" Summary Results:")
    print(f"-------------------------------------------------------")
    print(f"Total Credit Transactions : {len(transactions)}")
    print(f"Total Amount Collected    : Rs. {total_credit_amount:,.2f}")
    print(f"Matched Transactions      : {matched_count} ({(matched_count / len(transactions) * 100):.1f}%)" if transactions else "0")
    print(f"Unmatched Transactions    : {unmatched_count}")
    print(f"Flats Paid                : {flats_paid} / {flats_total}")
    print(f"Flats Pending             : {flats_pending} / {flats_total}")
    print(f"\n--> Output successfully saved to:\n    {saved_path}")
    print(f"=======================================================\n")

    return saved_path


def main():
    parser = argparse.ArgumentParser(
        description="Parse bank statement and create flat-wise payment tracking sheet (tracking_sheet.xlsx)."
    )
    parser.add_argument(
        "statement_file",
        help="Path to bank statement (.xls / .tsv / .csv) file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output Excel file path (default: tracking_sheet.xlsx in the statement's folder)",
    )
    parser.add_argument(
        "--members",
        default=None,
        help="Optional path to members.csv (default: db/members.csv)",
    )
    parser.add_argument(
        "--occupants",
        default=None,
        help="Optional path to occupants.csv (default: db/occupants.csv)",
    )

    args = parser.parse_args()
    try:
        track_payments(
            statement_file=args.statement_file,
            output_path=args.output,
            members_path=args.members,
            occupants_path=args.occupants,
        )
    except PermissionError:
        sys.exit(1)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[ERROR] {e}\n", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


