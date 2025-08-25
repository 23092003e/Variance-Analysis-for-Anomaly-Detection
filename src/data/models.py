"""
Data models for the variance analysis system.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class FinancialData:
    """Container for financial data."""
    balance_sheet: Optional[pd.DataFrame]
    income_statement: Optional[pd.DataFrame]
    periods: List[str]
    subsidiaries: List[str]
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Ensure DataFrames don't have conflicting metadata attributes
        if self.balance_sheet is not None and hasattr(self.balance_sheet, 'metadata'):
            delattr(self.balance_sheet, 'metadata')
        if self.income_statement is not None and hasattr(self.income_statement, 'metadata'):
            delattr(self.income_statement, 'metadata')
        
        # Store processing info
        self.metadata['processed_at'] = pd.Timestamp.now()
        self.metadata['data_shape'] = {
            'balance_sheet_rows': len(self.balance_sheet) if self.balance_sheet is not None else 0,
            'income_statement_rows': len(self.income_statement) if self.income_statement is not None else 0,
            'periods_count': len(self.periods)
        }