import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


DEFAULT_SHEET = "INCOME-EXPENSE-CYCLES"
DEFAULT_MEMBERS_CSV = Path(r"C:\github\manapristine\db\members.csv")
DEFAULT_OCCUPANTS_CSV = Path(r"C:\github\manapristine\db\occupants.csv")
DEFAULT_OUTPUT_JSON = Path(r"C:\github\manapristine\docs\report-data.json")


@dataclass(frozen=True)
class MonthlyBlock:
    month_label: str
    collection_idx: int
    expense_idx: int
    late_fee_idx: int
    net_idx: int


@dataclass(frozen=True)
class SheetLayout:
    carry_over_idx: int | None
    total_collection_idx: int | None
    total_expense_idx: int | None
    total_late_fee_idx: int | None
    total_net_idx: int | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the combined maintenance statement dataset from the latest workbook and members CSV."
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="workbook",
        type=Path,
        required=True,
        help="Path to the income/expense workbook (.xlsx)",
    )
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--members-csv", type=Path, default=DEFAULT_MEMBERS_CSV)
    parser.add_argument("--occupants-csv", type=Path, default=DEFAULT_OCCUPANTS_CSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def normalize_flat(flat: str) -> str:
    return (flat or "").strip().upper()


def safe_number(value: Any) -> float | int:
    if value is None or value == "":
        return 0
    return value


def month_label(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%b %Y")
    return str(value).strip()


def derive_financial_year(monthly_blocks: list[MonthlyBlock]) -> str:
    """Derive financial year string like '2025-26' from monthly block headers."""
    if not monthly_blocks:
        return "Unknown"
    first = monthly_blocks[0].month_label   # e.g., "Apr 2025"
    last = monthly_blocks[-1].month_label   # e.g., "Mar 2026"
    start_year = first.split()[-1]
    end_year = last.split()[-1]
    if start_year == end_year:
        return start_year
    return f"{start_year}-{end_year[-2:]}"


def build_expense_sheet_map(
    monthly_blocks: list[MonthlyBlock], available_sheets: list[str]
) -> dict[str, str]:
    """Build month_label -> sheet_name map by matching available workbook sheets."""
    sheet_set = set(available_sheets)
    full_month = {
        "Jan": "January", "Feb": "February", "Mar": "March",
        "Apr": "April", "May": "May", "Jun": "June",
        "Jul": "July", "Aug": "August", "Sep": "September",
        "Oct": "October", "Nov": "November", "Dec": "December",
    }
    result: dict[str, str] = {}
    for block in monthly_blocks:
        parts = block.month_label.split()
        if len(parts) != 2:
            continue
        abbrev, year = parts
        candidates = [f"{abbrev}{year}-EXPENSE"]
        full = full_month.get(abbrev, "")
        if full and full != abbrev:
            candidates.append(f"{full}{year}-EXPENSE")
        for candidate in candidates:
            if candidate in sheet_set:
                result[block.month_label] = candidate
                break
    return result


def write_report_dataset(
    reports: list[dict[str, Any]],
    output_json: Path,
    financial_year: str,
    annual_expense_details: list[dict[str, Any]] | None = None,
) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "financial_year": financial_year,
        "sheet": DEFAULT_SHEET,
        "report_count": len(reports),
        "reports": reports,
    }
    if annual_expense_details is not None:
        payload["annual_expense_details"] = annual_expense_details
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_flat_requests(members_csv: Path) -> list[dict[str, str]]:
    """Load the list of flats and owner info directly from members.csv."""
    flat_requests: list[dict[str, str]] = []
    with members_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            flat = normalize_flat(row.get("flat", ""))
            if not flat:
                continue
            flat_requests.append(
                {
                    "flat": flat,
                    "owner_name": (row.get("name") or "").strip(),
                    "email": (row.get("email") or "").strip(),
                }
            )
    return flat_requests


def load_occupants(occupants_csv: Path) -> dict[str, str]:
    """Return a mapping of normalized flat -> occupant name from occupants.csv."""
    lookup: dict[str, str] = {}
    with occupants_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            flat = normalize_flat(row.get("flat", ""))
            if flat:
                lookup[flat] = (row.get("name") or "").strip()
    return lookup


def extract_monthly_blocks(header_row_1: tuple[Any, ...], header_row_2: tuple[Any, ...]) -> list[MonthlyBlock]:
    blocks: list[MonthlyBlock] = []
    for idx, cell_value in enumerate(header_row_1):
        if not isinstance(cell_value, datetime):
            continue
        if idx + 3 >= len(header_row_2):
            continue
        labels = [header_row_2[idx + offset] for offset in range(4)]
        if labels != ["COLLECTION", "EXPENSE", "LATE PAYMENT FEE", "COLLECTION - EXPENSE"]:
            continue
        blocks.append(
            MonthlyBlock(
                month_label=month_label(cell_value),
                collection_idx=idx,
                expense_idx=idx + 1,
                late_fee_idx=idx + 2,
                net_idx=idx + 3,
            )
        )
    return blocks


def extract_sheet_layout(header_row_1: tuple[Any, ...]) -> SheetLayout:
    normalized = [str(value).strip().replace("\n", " ") if value is not None else "" for value in header_row_1]
    carry_over_idx = next((idx for idx, value in enumerate(normalized) if "COLLECTION CARRY OVER" in value), None)
    total_collection_idx = next((idx for idx, value in enumerate(normalized) if value.startswith("TOTAL COLLECTION")), None)
    total_expense_idx = next((idx for idx, value in enumerate(normalized) if value.startswith("TOTAL EXPENSE")), None)
    total_late_fee_idx = next((idx for idx, value in enumerate(normalized) if value.startswith("TOTAL LATE FEE")), None)
    total_net_idx = next((idx for idx, value in enumerate(normalized) if value.startswith("TOTAL COLLECTION - EXPENSE")), None)
    return SheetLayout(
        carry_over_idx=carry_over_idx,
        total_collection_idx=total_collection_idx,
        total_expense_idx=total_expense_idx,
        total_late_fee_idx=total_late_fee_idx,
        total_net_idx=total_net_idx,
    )


def load_sheet_rows(workbook_path: Path, sheet_name: str) -> tuple[list[MonthlyBlock], SheetLayout, dict[str, tuple[Any, ...]], list[str]]:
    workbook = load_workbook(workbook_path, data_only=True, read_only=True)
    try:
        available_sheets = workbook.sheetnames
        sheet = workbook[sheet_name]
        header_row_1 = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        header_row_2 = next(sheet.iter_rows(min_row=2, max_row=2, values_only=True))
        monthly_blocks = extract_monthly_blocks(header_row_1, header_row_2)
        sheet_layout = extract_sheet_layout(header_row_1)

        row_lookup: dict[str, tuple[Any, ...]] = {}
        for row in sheet.iter_rows(min_row=3, values_only=True):
            flat = normalize_flat(row[0] if row else "")
            if flat:
                row_lookup[flat] = row
        return monthly_blocks, sheet_layout, row_lookup, available_sheets
    finally:
        workbook.close()


def load_expense_details(workbook_path: Path, expense_sheet_map: dict[str, str]) -> dict[str, dict[str, dict[str, float]]]:
    """Load per-flat, per-month expense breakdown from individual EXPENSE sheets.

    Returns: { flat: { month_label: { field: value, ... } } }
    """
    workbook = load_workbook(workbook_path, data_only=True, read_only=True)
    result: dict[str, dict[str, dict[str, float]]] = {}
    try:
        for month_label, sheet_name in expense_sheet_map.items():
            if sheet_name not in workbook.sheetnames:
                continue
            ws = workbook[sheet_name]
            for row in ws.iter_rows(min_row=3, values_only=True):
                flat = normalize_flat(row[0] if row else "")
                if not flat:
                    continue
                result.setdefault(flat, {})[month_label] = {
                    "water_used_litres": safe_number(row[2] if len(row) > 2 else 0),
                    "common_area_water_litres": safe_number(row[3] if len(row) > 3 else 0),
                    "total_fresh_water_consumed_litres": safe_number(row[4] if len(row) > 4 else 0),
                    "water_expense": safe_number(row[6] if len(row) > 6 else 0),
                    "num_meters": safe_number(row[7] if len(row) > 7 else 0),
                    "meter_rent": safe_number(row[8] if len(row) > 8 else 0),
                    "total_water_expense": safe_number(row[9] if len(row) > 9 else 0),
                    "fixed_expense": safe_number(row[10] if len(row) > 10 else 0),
                    "parking_fee": safe_number(row[11] if len(row) > 11 else 0),
                    "club_house_fee": safe_number(row[12] if len(row) > 12 else 0),
                    "shifting_fee": safe_number(row[13] if len(row) > 13 else 0),
                    "gym_usage_fee": safe_number(row[14] if len(row) > 14 else 0),
                    "total_expense": safe_number(row[17] if len(row) > 17 else 0),
                }
        return result
    finally:
        workbook.close()


def build_report(
    flat_request: dict[str, str],
    sheet_row: tuple[Any, ...],
    monthly_blocks: list[MonthlyBlock],
    sheet_layout: SheetLayout,
    expense_details: dict[str, dict[str, float]] | None = None,
    occupant_name: str | None = None,
) -> dict[str, Any]:
    carry_over = safe_number(sheet_row[sheet_layout.carry_over_idx] if sheet_layout.carry_over_idx is not None and len(sheet_row) > sheet_layout.carry_over_idx else 0)
    total_collection = safe_number(sheet_row[sheet_layout.total_collection_idx] if sheet_layout.total_collection_idx is not None and len(sheet_row) > sheet_layout.total_collection_idx else 0)
    total_expense = safe_number(sheet_row[sheet_layout.total_expense_idx] if sheet_layout.total_expense_idx is not None and len(sheet_row) > sheet_layout.total_expense_idx else 0)
    total_late_fee = safe_number(sheet_row[sheet_layout.total_late_fee_idx] if sheet_layout.total_late_fee_idx is not None and len(sheet_row) > sheet_layout.total_late_fee_idx else 0)
    total_net = safe_number(sheet_row[sheet_layout.total_net_idx] if sheet_layout.total_net_idx is not None and len(sheet_row) > sheet_layout.total_net_idx else 0)
    closing_balance = float(carry_over) + float(total_net)

    report = {
        "flat": flat_request["flat"],
        "owner_name": flat_request["owner_name"],
        "email": flat_request["email"],
        "sheet_email": (sheet_row[1] or "").strip() if len(sheet_row) > 1 and isinstance(sheet_row[1], str) else sheet_row[1],
        "occupant": occupant_name or None,
        "collection_carry_over_mar2013_mar2022": carry_over,
        "monthly": [],
        "totals": {
            "collection": total_collection,
            "expense": total_expense,
            "late_fee": total_late_fee,
            "net_collection_minus_expense": total_net,
            "closing_balance": closing_balance,
        },
    }

    expense_breakdown: list[dict[str, Any]] = []
    for block in monthly_blocks:
        report["monthly"].append(
            {
                "month": block.month_label,
                "collection": safe_number(sheet_row[block.collection_idx] if len(sheet_row) > block.collection_idx else 0),
                "expense": safe_number(sheet_row[block.expense_idx] if len(sheet_row) > block.expense_idx else 0),
                "late_fee": safe_number(sheet_row[block.late_fee_idx] if len(sheet_row) > block.late_fee_idx else 0),
                "net_collection_minus_expense": safe_number(sheet_row[block.net_idx] if len(sheet_row) > block.net_idx else 0),
            }
        )
        if expense_details and block.month_label in expense_details:
            expense_breakdown.append({"month": block.month_label, **expense_details[block.month_label]})
        else:
            expense_breakdown.append({"month": block.month_label})

    report["expense_breakdown"] = expense_breakdown
    return report


def generate_reports(
    workbook_path: Path,
    sheet_name: str,
    flat_requests: list[dict[str, str]],
    occupants: dict[str, str] | None = None,
 ) -> tuple[list[dict[str, Any]], list[str], str]:
    monthly_blocks, sheet_layout, row_lookup, available_sheets = load_sheet_rows(workbook_path, sheet_name)
    financial_year = derive_financial_year(monthly_blocks)
    expense_sheet_map = build_expense_sheet_map(monthly_blocks, available_sheets)
    all_expense_details = load_expense_details(workbook_path, expense_sheet_map)
    occupants = occupants or {}
    reports: list[dict[str, Any]] = []
    missing_flats: list[str] = []

    for flat_request in flat_requests:
        flat = flat_request["flat"]
        sheet_row = row_lookup.get(flat)
        if sheet_row is None:
            missing_flats.append(flat)
            continue
        flat_expenses = all_expense_details.get(flat)
        occupant = occupants.get(flat, "")
        report = build_report(flat_request, sheet_row, monthly_blocks, sheet_layout, flat_expenses, occupant)
        reports.append(report)
    return reports, missing_flats, financial_year


def load_annual_expense_details(workbook_path: Path) -> list[dict[str, Any]]:
    """Load the ANNUAL-EXPENSE-DETAILS sheet: per-month rows with individual expense line items and summary columns."""
    workbook = load_workbook(workbook_path, data_only=True, read_only=True)
    try:
        sheet_name = "ANNUAL-EXPENSE-DETAILS"
        if sheet_name not in workbook.sheetnames:
            return []
        ws = workbook[sheet_name]
        header_row_2 = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]

        # Build column name map from row 2 (line-item headers) for C1..C54
        col_names: list[str] = []
        for ci in range(len(header_row_2)):
            val = header_row_2[ci]
            if val and ci >= 1 and ci <= 54:
                name = str(val).strip().replace("\n", " ")
                col_names.append((ci, name))

        rows: list[dict[str, Any]] = []
        for row in ws.iter_rows(min_row=3, values_only=True):
            month_name = row[0] if row[0] else None
            if not month_name:
                continue
            month_str = str(month_name).strip()
            entry: dict[str, Any] = {"month": month_str}

            # Individual line items (only include non-zero)
            line_items: dict[str, float] = {}
            for ci, name in col_names:
                val = safe_number(row[ci] if len(row) > ci else 0)
                if val:
                    line_items[name] = val
            entry["line_items"] = line_items

            # Summary columns
            entry["gross_expense"] = safe_number(row[55] if len(row) > 55 else 0)
            entry["gross_variable_expense"] = safe_number(row[56] if len(row) > 56 else 0)
            entry["gross_fixed_expense"] = safe_number(row[57] if len(row) > 57 else 0)
            entry["water_meter_rent"] = safe_number(row[58] if len(row) > 58 else 0)
            entry["total_expense"] = safe_number(row[59] if len(row) > 59 else 0)

            rows.append(entry)
        return rows
    finally:
        workbook.close()


def main() -> int:
    args = parse_args()

    flat_requests = load_flat_requests(args.members_csv)
    occupants = load_occupants(args.occupants_csv)

    reports, missing_flats, financial_year = generate_reports(
        workbook_path=args.workbook,
        sheet_name=args.sheet,
        flat_requests=flat_requests,
        occupants=occupants,
    )
    annual_expense_details = load_annual_expense_details(args.workbook)
    write_report_dataset(reports, args.output_json, financial_year, annual_expense_details)

    print(f"Generated JSON for {len(reports)} report(s) at {args.output_json}")
    if missing_flats:
        print("Missing flats in workbook:", ", ".join(sorted(missing_flats)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
