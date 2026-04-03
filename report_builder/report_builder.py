import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


DEFAULT_WORKBOOK = Path(r"C:\github\manapristine\db\2025-2026-INCOME-EXPENDITURE-ACCOUNT.xlsx")
DEFAULT_SHEET = "INCOME-EXPENSE-CYCLES"
DEFAULT_FLATS_JSON = Path(r"C:\github\manapristine\db\report_flats.json")
DEFAULT_MEMBERS_CSV = Path(r"C:\github\manapristine\db\members.csv")
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
        description="Generate flat-wise income and expense reports from the annual workbook."
    )
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--flats-json", type=Path, default=DEFAULT_FLATS_JSON)
    parser.add_argument("--members-csv", type=Path, default=DEFAULT_MEMBERS_CSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument(
        "-f",
        "--flat",
        action="append",
        dest="flat_filters",
        default=[],
        help="Optional flat filter. Can be passed multiple times.",
    )
    parser.add_argument(
        "--refresh-flats-json",
        action="store_true",
        help="Rebuild the flats JSON from members.csv before generating reports.",
    )
    parser.add_argument(
        "-a",
        "--all-flats",
        action="store_true",
        help="Generate JSON data for all flats in the flats JSON file.",
    )
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


def write_report_dataset(reports: list[dict[str, Any]], output_json: Path) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sheet": DEFAULT_SHEET,
        "report_count": len(reports),
        "reports": reports,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_flats_json_from_csv(members_csv: Path, flats_json: Path) -> list[dict[str, str]]:
    flats: list[dict[str, str]] = []
    with members_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            flat = normalize_flat(row.get("flat", ""))
            if not flat:
                continue
            flats.append(
                {
                    "flat": flat,
                    "owner_name": (row.get("name") or "").strip(),
                    "email": (row.get("email") or "").strip(),
                }
            )

    flats_json.parent.mkdir(parents=True, exist_ok=True)
    flats_json.write_text(json.dumps(flats, indent=2), encoding="utf-8")
    return flats


def load_flat_requests(flats_json: Path) -> list[dict[str, str]]:
    payload = json.loads(flats_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{flats_json} must contain a JSON array.")

    flat_requests: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Every flats JSON entry must be an object.")
        flat = normalize_flat(item.get("flat", ""))
        if not flat:
            continue
        flat_requests.append(
            {
                "flat": flat,
                "owner_name": (item.get("owner_name") or item.get("name") or "").strip(),
                "email": (item.get("email") or "").strip(),
            }
        )
    return flat_requests


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


def load_sheet_rows(workbook_path: Path, sheet_name: str) -> tuple[list[MonthlyBlock], SheetLayout, dict[str, tuple[Any, ...]]]:
    workbook = load_workbook(workbook_path, data_only=True, read_only=True)
    try:
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
        return monthly_blocks, sheet_layout, row_lookup
    finally:
        workbook.close()


def build_report(
    flat_request: dict[str, str],
    sheet_row: tuple[Any, ...],
    monthly_blocks: list[MonthlyBlock],
    sheet_layout: SheetLayout,
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
        "occupant": sheet_row[2] if len(sheet_row) > 2 else None,
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
    return report


def generate_reports(
    workbook_path: Path,
    sheet_name: str,
    flat_requests: list[dict[str, str]],
 ) -> tuple[list[dict[str, Any]], list[str]]:
    monthly_blocks, sheet_layout, row_lookup = load_sheet_rows(workbook_path, sheet_name)
    reports: list[dict[str, Any]] = []
    missing_flats: list[str] = []

    for flat_request in flat_requests:
        flat = flat_request["flat"]
        sheet_row = row_lookup.get(flat)
        if sheet_row is None:
            missing_flats.append(flat)
            continue
        report = build_report(flat_request, sheet_row, monthly_blocks, sheet_layout)
        reports.append(report)
    return reports, missing_flats


def main() -> int:
    args = parse_args()

    if args.refresh_flats_json or not args.flats_json.exists():
        write_flats_json_from_csv(args.members_csv, args.flats_json)

    flat_requests = load_flat_requests(args.flats_json)
    if not args.all_flats and args.flat_filters:
        wanted = {normalize_flat(flat) for flat in args.flat_filters}
        flat_requests = [entry for entry in flat_requests if entry["flat"] in wanted]

    reports, missing_flats = generate_reports(
        workbook_path=args.workbook,
        sheet_name=args.sheet,
        flat_requests=flat_requests,
    )
    write_report_dataset(reports, args.output_json)

    print(f"Generated JSON for {len(reports)} report(s) at {args.output_json}")
    if missing_flats:
        print("Missing flats in workbook:", ", ".join(sorted(missing_flats)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
