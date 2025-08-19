"""
Data models for the variance analysis system.
"""

import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class FinancialData:
    """Container for financial data."""
    balance_sheet: pd.DataFrame
    income_statement: pd.DataFrame
    periods: List[str]
    subsidiaries: List[str]
    metadata: Dict[str, Any]