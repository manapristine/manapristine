---
name: excel-source-of-truth
description: Enforces Excel workbooks as the absolute single source of truth without dynamic fallback calculations in Python scripts.
---

# Excel Source of Truth Policy

When writing or modifying Python scripts in `report_builder/` or reading Excel financial workbooks:

1. **Excel as Single Source of Truth**:
   - Always treat Excel workbooks (`db/accounts/*.xlsx`) as the sole authority for both raw input values and computed formula values.
   - Use `openpyxl.load_workbook(..., data_only=True)` to read evaluated formula results.

2. **Pre-Read All Formula Values Upfront**:
   - Always load and read ALL required formula cell values with `data_only=True` into memory BEFORE making any cell modifications or calling `wb.save()`.
   - Modifying and saving a workbook with `openpyxl` strips cached formula values (`<v>` XML tags), causing subsequent `data_only=True` reads on the modified workbook to return `None`.

3. **No Dynamic Fallback Calculations**:
   - Never implement fallback logic in Python to dynamically recalculate formula values (e.g. summing expense columns if a formula cell evaluates to `None`).

4. **Strict Exception Handling**:
   - If a required cell value or cached formula result is `None` or non-numeric, raise a clear `ValueError` asking the user to open the Excel workbook, save it, close it, and re-run.
