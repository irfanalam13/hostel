"""The default Chart of Accounts seeded per workspace.

A standard hostel-oriented chart following the 1000/2000/3000/4000/5000
convention (assets/liabilities/equity/income/expenses). Group nodes roll up
their children; leaf nodes carry postings. Seeding is idempotent (``get_or_create``
by code) so workspaces can extend it freely without a re-seed clobbering edits.

Certain leaf accounts are *anchors* the engine posts to automatically (retained
earnings, opening-balance equity, current-year earnings). They're looked up by
these stable codes.
"""
from apps.accounting.models import Account, AccountType

# Anchor account codes the engine relies on.
RETAINED_EARNINGS_CODE = "3200"
CURRENT_YEAR_EARNINGS_CODE = "3300"
OPENING_BALANCE_EQUITY_CODE = "3900"

# (code, name, type, subtype, parent_code, is_group, is_system)
DEFAULT_ACCOUNTS = [
    # Assets ----------------------------------------------------------------
    ("1000", "Assets", AccountType.ASSET, "", None, True, True),
    ("1100", "Current Assets", AccountType.ASSET, "current_asset", "1000", True, True),
    ("1110", "Cash", AccountType.ASSET, "cash", "1100", False, True),
    ("1120", "Petty Cash", AccountType.ASSET, "cash", "1100", False, True),
    ("1130", "Bank", AccountType.ASSET, "bank", "1100", False, True),
    ("1140", "Accounts Receivable", AccountType.ASSET, "receivable", "1100", False, True),
    ("1150", "Inventory", AccountType.ASSET, "inventory", "1100", False, True),
    ("1160", "Prepaid Expenses", AccountType.ASSET, "current_asset", "1100", False, False),
    ("1170", "Tax Receivable", AccountType.ASSET, "tax", "1100", False, True),
    ("1500", "Fixed Assets", AccountType.ASSET, "fixed_asset", "1000", True, True),
    ("1510", "Buildings", AccountType.ASSET, "fixed_asset", "1500", False, True),
    ("1520", "Furniture & Fixtures", AccountType.ASSET, "fixed_asset", "1500", False, True),
    ("1530", "Computers & Equipment", AccountType.ASSET, "fixed_asset", "1500", False, True),
    ("1540", "Vehicles", AccountType.ASSET, "fixed_asset", "1500", False, True),
    ("1590", "Accumulated Depreciation", AccountType.ASSET, "contra_asset", "1500", False, True),
    # Liabilities -----------------------------------------------------------
    ("2000", "Liabilities", AccountType.LIABILITY, "", None, True, True),
    ("2100", "Current Liabilities", AccountType.LIABILITY, "current_liability", "2000", True, True),
    ("2110", "Accounts Payable", AccountType.LIABILITY, "payable", "2100", False, True),
    ("2120", "Salaries Payable", AccountType.LIABILITY, "payable", "2100", False, True),
    ("2130", "Taxes Payable", AccountType.LIABILITY, "tax", "2100", False, True),
    ("2140", "Security Deposits Held", AccountType.LIABILITY, "deposit", "2100", False, True),
    ("2200", "Long-Term Liabilities", AccountType.LIABILITY, "long_term", "2000", True, True),
    ("2210", "Loans Payable", AccountType.LIABILITY, "loan", "2200", False, True),
    # Equity ----------------------------------------------------------------
    ("3000", "Equity", AccountType.EQUITY, "", None, True, True),
    ("3100", "Owner Capital", AccountType.EQUITY, "capital", "3000", False, True),
    (RETAINED_EARNINGS_CODE, "Retained Earnings", AccountType.EQUITY, "retained", "3000", False, True),
    (CURRENT_YEAR_EARNINGS_CODE, "Current Year Earnings", AccountType.EQUITY, "retained", "3000", False, True),
    (OPENING_BALANCE_EQUITY_CODE, "Opening Balance Equity", AccountType.EQUITY, "opening", "3000", False, True),
    # Income ----------------------------------------------------------------
    ("4000", "Income", AccountType.INCOME, "", None, True, True),
    ("4100", "Student Fees", AccountType.INCOME, "operating", "4000", False, True),
    ("4110", "Room Income", AccountType.INCOME, "operating", "4000", False, True),
    ("4120", "Hostel Fees", AccountType.INCOME, "operating", "4000", False, True),
    ("4130", "Laundry Income", AccountType.INCOME, "operating", "4000", False, True),
    ("4140", "Internet Income", AccountType.INCOME, "operating", "4000", False, True),
    ("4150", "Transportation Income", AccountType.INCOME, "operating", "4000", False, True),
    ("4160", "Cafeteria Income", AccountType.INCOME, "operating", "4000", False, True),
    ("4900", "Other Income", AccountType.INCOME, "other", "4000", False, True),
    # Expenses --------------------------------------------------------------
    ("5000", "Expenses", AccountType.EXPENSE, "", None, True, True),
    ("5100", "Salaries & Wages", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5110", "Electricity", AccountType.EXPENSE, "utility", "5000", False, True),
    ("5120", "Water", AccountType.EXPENSE, "utility", "5000", False, True),
    ("5130", "Food & Kitchen", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5140", "Internet", AccountType.EXPENSE, "utility", "5000", False, True),
    ("5150", "Repairs & Maintenance", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5160", "Marketing", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5170", "Rent", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5180", "Office Expenses", AccountType.EXPENSE, "operating", "5000", False, True),
    ("5190", "Depreciation Expense", AccountType.EXPENSE, "non_cash", "5000", False, True),
    ("5900", "Miscellaneous Expense", AccountType.EXPENSE, "other", "5000", False, True),
]


def seed_default_accounts(hostel) -> int:
    """Idempotently create the default chart of accounts for a workspace.
    Returns the number of accounts created. Parents are created before
    children (the list is ordered so), and linked in a second pass."""
    created = 0
    by_code: dict[str, Account] = {}
    # Pass 1: create every account without the parent link.
    for code, name, type_, subtype, _parent, is_group, is_system in DEFAULT_ACCOUNTS:
        obj, was_created = Account.objects.get_or_create(
            hostel=hostel,
            code=code,
            defaults={
                "name": name,
                "type": type_,
                "subtype": subtype,
                "is_group": is_group,
                "is_system": is_system,
            },
        )
        by_code[code] = obj
        created += int(was_created)
    # Pass 2: wire parent links.
    for code, _n, _t, _s, parent_code, _g, _sys in DEFAULT_ACCOUNTS:
        if parent_code:
            acc = by_code[code]
            parent = by_code.get(parent_code)
            if parent and acc.parent_id != parent.id:
                acc.parent = parent
                acc.save(update_fields=["parent", "updated_at"])
    return created
