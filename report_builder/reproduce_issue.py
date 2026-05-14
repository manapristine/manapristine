import os
import openpyxl
from update_water_consumption import load_wateron_data, update_workbook, normalize_flat
from pathlib import Path

def create_mock_wateron(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Apartment', 'Total'])
    ws.append(['A101', 100])
    ws.append(['A102', 200])
    ws.append(['TOTAL', 300])
    wb.save(path)

def create_mock_workbook(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Apr2026-EXPENSE"
    ws.append(['FLAT', 'OTHER', 'WATER USED IN LTRS']) # Row 1
    ws.append(['FLAT', 'OTHER', 'WATER USED IN LTRS']) # Row 2 (Header row according to script)
    ws.append(['A101', '', 0])
    ws.append(['A102', '', 0])
    ws.append(['TOTAL', '', 0])
    wb.save(path)

def test_total_issue():
    wateron_path = Path("mock_wateron.xlsx")
    workbook_path = Path("mock_workbook.xlsx")
    
    create_mock_wateron(wateron_path)
    create_mock_workbook(workbook_path)
    
    print("Testing load_wateron_data...")
    water_data = load_wateron_data(wateron_path)
    print(f"Water data keys: {list(water_data.keys())}")
    
    print("\nTesting update_workbook...")
    update_workbook(workbook_path, 4, 2026, water_data)
    
    # Cleanup
    if wateron_path.exists(): wateron_path.unlink()
    if workbook_path.exists(): workbook_path.unlink()

if __name__ == "__main__":
    test_total_issue()
