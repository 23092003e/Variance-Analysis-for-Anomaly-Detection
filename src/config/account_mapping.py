"""
Account code mapping and categorization.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AccountInfo:
    """Account information structure."""
    code: str
    name: str
    category: str
    statement_type: str  # 'BS' for Balance Sheet, 'IS' for Income Statement
    is_recurring: bool = False


class AccountMapper:
    """Account code mapping and categorization manager."""
    
    def __init__(self):
        self.accounts = self._initialize_accounts()
        self.code_to_info = {acc.code: acc for acc in self.accounts}
        self.category_to_codes = self._build_category_mapping()
    
    def _initialize_accounts(self) -> List[AccountInfo]:
        """Initialize predefined account information."""
        return [
            # Balance Sheet - Assets
            AccountInfo("217000001", "Investment Properties: Land Use Rights", "investment_properties", "BS"),
            AccountInfo("217000006", "Investment Properties: Office Building", "investment_properties", "BS"),
            AccountInfo("112227001", "ACB: Current Account USD - HCM", "cash_deposits", "BS"),
            AccountInfo("112227002", "ACB: Current Account USD - HCM 2", "cash_deposits", "BS"),
            AccountInfo("131100001", "Trade Receivable: Tenant", "trade_receivables", "BS"),
            AccountInfo("138900003", "Unbilled Revenue Receivables", "unbilled_revenue", "BS"),
            AccountInfo("133100001", "VAT Deductible", "vat_deductible", "BS"),
            AccountInfo("138820000", "LT: Other Receivables: Subsidiaries/Parents - SHL", "lending", "BS"),
            AccountInfo("138821001", "LT: Other Receivables: Subsidiaries/Parents - SHL 2", "lending", "BS"),
            
            # Balance Sheet - Liabilities
            AccountInfo("341160000", "LT: Borrowings: Subsidiaries/Parents", "borrowings", "BS"),
            AccountInfo("341160001", "LT: Borrowings: Subsidiaries/Parents 2", "borrowings", "BS"),
            AccountInfo("213100001", "Unearned Revenue", "unearned_revenue", "BS"),
            
            # Income Statement - Revenue
            AccountInfo("511100001", "Rental Revenue", "revenue", "IS", True),
            AccountInfo("511100002", "Service Revenue", "revenue", "IS", True),
            AccountInfo("515100001", "Financial Income: Interest", "interest_income", "IS", True),
            AccountInfo("515600000", "Financial Income: BCC Interest", "interest_income_shl", "IS", True),
            
            # Income Statement - Expenses
            AccountInfo("632100001", "Expense Amortization: Land Use Rights", "depreciation", "IS", True),
            AccountInfo("632100002", "Expense Amortization: Building", "depreciation", "IS", True),
            AccountInfo("635000005", "Financial Expenses: Loan Interest - Parent/Subsi", "interest_expense", "IS", True),
            AccountInfo("635000006", "Financial Expenses: Loan Interest - Bank", "interest_expense", "IS", True),
            AccountInfo("622000001", "Operating Expenses: Insurance", "opex", "IS", True),
            AccountInfo("622000002", "Operating Expenses: Utilities", "opex", "IS", True),
            AccountInfo("622000003", "Operating Expenses: R&M", "opex", "IS", True),
            AccountInfo("641100001", "FX Gain/Loss", "fx_gain_loss", "IS"),
        ]
    
    def _build_category_mapping(self) -> Dict[str, List[str]]:
        """Build mapping from category to account codes."""
        mapping = {}
        for account in self.accounts:
            if account.category not in mapping:
                mapping[account.category] = []
            mapping[account.category].append(account.code)
        return mapping
    
    def get_account_info(self, account_code: str) -> Optional[AccountInfo]:
        """Get account information by code."""
        return self.code_to_info.get(account_code)
    
    def get_accounts_by_category(self, category: str) -> List[str]:
        """Get account codes by category."""
        return self.category_to_codes.get(category, [])
    
    def get_recurring_accounts(self) -> List[str]:
        """Get all recurring account codes."""
        return [acc.code for acc in self.accounts if acc.is_recurring]
    
    def is_balance_sheet_account(self, account_code: str) -> bool:
        """Check if account is a balance sheet account."""
        info = self.get_account_info(account_code)
        return info is not None and info.statement_type == "BS"
    
    def is_income_statement_account(self, account_code: str) -> bool:
        """Check if account is an income statement account."""
        info = self.get_account_info(account_code)
        return info is not None and info.statement_type == "IS"
    
    def get_correlated_accounts(self, account_code: str) -> List[str]:
        """Get accounts that should correlate with the given account."""
        info = self.get_account_info(account_code)
        if not info:
            return []
            
        correlations = {
            "investment_properties": self.get_accounts_by_category("depreciation"),
            "borrowings": self.get_accounts_by_category("interest_expense"),
            "cash_deposits": self.get_accounts_by_category("interest_income"),
            "lending": self.get_accounts_by_category("interest_income_shl"),
            "depreciation": self.get_accounts_by_category("investment_properties"),
            "interest_expense": self.get_accounts_by_category("borrowings"),
            "interest_income": self.get_accounts_by_category("cash_deposits"),
        }
        
        return correlations.get(info.category, [])