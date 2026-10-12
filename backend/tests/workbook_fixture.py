from datetime import datetime
from io import BytesIO

from openpyxl import Workbook


def realistic_workbook(*, malformed: bool = False, months: tuple[str, ...] = ("August", "September")) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.modified = datetime(2026, 9, 30)
    for index, month in enumerate(months):
        sheet = workbook.create_sheet(month)
        sheet.append(
            [
                "Income",
                "Type",
                "Income Class",
                None,
                "Expense",
                "Type",
                "Category",
                "Expense Tag",
                None,
                "Wealth Flow",
                "Destination",
                "Flow Class",
                None,
                "Monthly Summary",
                "Amount",
            ]
        )
        for row in (
            [
                4200 + index * 100,
                "Primary paycheck",
                "Paycheck",
                None,
                1500,
                "Rent",
                "Housing",
                "",
                None,
                500,
                "401(k)",
                "Retirement Investment",
            ],
            [
                250,
                "Freelance project",
                "Side Income",
                None,
                85,
                "Client dinner",
                "Work Meals",
                "Work/Reimbursable",
                None,
                300,
                "Roth IRA",
                "Investment",
            ],
            [
                None,
                None,
                "",
                None,
                120,
                "Weekend trip",
                "Travel",
                "Personal Travel",
                None,
                1000,
                "Chase -> HYSA",
                "Internal Transfer",
            ],
            [
                None,
                None,
                "",
                None,
                300,
                "New desk",
                "Shopping & Home" if not malformed else "",
                "One-time",
                None,
                None,
                None,
                "",
            ],
            [
                None,
                None,
                "",
                None,
                160,
                "Groceries",
                "Groceries",
                "",
                None,
                None,
                None,
                "",
            ],
        ):
            sheet.append(row)
        for row_number in range(7, 20):
            sheet.cell(row_number, 3, "")
            sheet.cell(row_number, 7, "")
            sheet.cell(row_number, 12, "")
    net_worth = workbook.create_sheet("Networth")
    net_worth.append(
        [
            "Savings",
            None,
            None,
            "Investments",
            None,
            None,
            None,
            "This is as of 9/30/2026",
        ]
    )
    net_worth.append(["Checking", 4500, None, "Vanguard", 18000])
    net_worth.append(["Citi HYSA", 12000, None, "Roth IRA", 9000])
    net_worth.append([None, None, None, "401(k)", 22000])
    net_worth.append([None, None, None, "HSA", 3500])
    net_worth.append([])
    net_worth.append(["TOTAL SAVINGS", 16500, None, "TOTAL INVESTMENTS", 52500])
    workbook.create_sheet("Categories").append(["Category", "Definition"])
    workbook.create_sheet("Air BNB Paid").append(["Stay", "Amount"])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
