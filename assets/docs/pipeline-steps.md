1. download the statement and name it mmm-yyyy xls
2. copy the last account statement and make a new copy for the current month.
3. update the workbooks.json entry for the current financial year only.
4. download water meter readings
5. update the wateron readings for expense sheet
6. update bank account collection amount by running report_builder.py with bank statement as argument and run option 1
7. review the processing report in the same folder as the bank statement.
8. after removing non matched items, run step 6 again for option 2
9. run update_late_payment_file.py 
10. check late payment fine is correctly updated.
11. update all the expenses in the total monthly expense tab
12. run report_builder.py 
13. export red register into excel and pdf.

