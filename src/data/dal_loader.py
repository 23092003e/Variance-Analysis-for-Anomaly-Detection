"""
Enhanced data loader specifically for DAL Excel file format.
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re

from config.settings import Settings
from data.models import FinancialData


class DALDataLoader:
    """Enhanced data loader for DAL-specific Excel format."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
    
    def load_dal_excel_file(self, file_path: str) -> FinancialData:
        """
        Load DAL-specific Excel file format.
        
        Args:
            file_path: Path to DAL Excel file
            
        Returns:
            FinancialData object containing loaded data
        """
        self.logger.info(f"Loading DAL Excel file: {file_path}")
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            
            # Extract balance sheet and income statement
            balance_sheet = self._extract_dal_balance_sheet(excel_data, file_path)
            income_statement = self._extract_dal_income_statement(excel_data, file_path)
            
            # Extract periods and subsidiaries
            periods = self._extract_dal_periods(balance_sheet, income_statement)
            subsidiaries = ['BW Industrial Development JSC']  # From the file header
            
            # Create metadata
            metadata = {
                'file_path': file_path,
                'sheets': list(excel_data.keys()),
                'load_timestamp': pd.Timestamp.now(),
                'file_format': 'DAL'
            }
            
            financial_data = FinancialData(
                balance_sheet=balance_sheet,
                income_statement=income_statement,
                periods=periods,
                subsidiaries=subsidiaries,
                metadata=metadata
            )
            
            self.logger.info(f"Successfully loaded DAL data: {len(periods)} periods, "
                           f"{len(subsidiaries)} subsidiaries")
            
            return financial_data
            
        except Exception as e:
            self.logger.error(f"Error loading DAL Excel file: {str(e)}")
            raise
    
    def _extract_dal_balance_sheet(self, excel_data: Dict[str, pd.DataFrame], file_path: str) -> pd.DataFrame:
        """Extract balance sheet data from DAL Excel format."""
        if 'BS' not in excel_data:
            raise ValueError("No Balance Sheet (BS) found in DAL file")
        
        bs_raw = excel_data['BS']
        
        # Find the data start row (look for "Financial Row" or similar)
        data_start_row = None
        for i, row in bs_raw.iterrows():
            if pd.notna(row.iloc[0]) and 'Financial Row' in str(row.iloc[0]):
                data_start_row = i
                break
        
        if data_start_row is None:
            # Alternative: look for first row with account structure
            for i, row in bs_raw.iterrows():
                if pd.notna(row.iloc[0]) and self._looks_like_account_entry(str(row.iloc[0])):
                    data_start_row = i - 1  # Take header row before first account
                    break
        
        if data_start_row is None:
            raise ValueError("Cannot find data start row in Balance Sheet")
        
        # Read from data start row
        bs_clean = pd.read_excel(
            file_path, 
            sheet_name='BS', 
            skiprows=data_start_row,
            engine='openpyxl'
        )
        
        return self._standardize_dal_dataframe(bs_clean, 'BS')
    
    def _extract_dal_income_statement(self, excel_data: Dict[str, pd.DataFrame], file_path: str) -> pd.DataFrame:
        """Extract income statement data from DAL Excel format."""
        # Try different possible sheet names for income statement
        is_sheet_names = ['PL Breakdown', 'IS', 'Income Statement', 'P&L']
        is_sheet = None
        
        for name in is_sheet_names:
            if name in excel_data:
                is_sheet = name
                break
        
        if is_sheet is None:
            # Create empty income statement if not found
            self.logger.warning("No Income Statement sheet found, creating empty structure")
            return pd.DataFrame({
                'account_code': [],
                'account_name': [],
                'statement_type': [],
                'current_period': [],
                'previous_period': []
            })
        
        is_raw = excel_data[is_sheet]
        
        # Find data start row similar to balance sheet
        data_start_row = 0
        for i, row in is_raw.iterrows():
            if pd.notna(row.iloc[0]) and ('Financial' in str(row.iloc[0]) or 
                                        self._looks_like_account_entry(str(row.iloc[0]))):
                data_start_row = max(0, i - 1)
                break
        
        # Read from data start row  
        is_clean = pd.read_excel(
            file_path, 
            sheet_name=is_sheet, 
            skiprows=data_start_row,
            engine='openpyxl'
        )
        
        return self._standardize_dal_dataframe(is_clean, 'IS')
    
    def _standardize_dal_dataframe(self, df: pd.DataFrame, statement_type: str) -> pd.DataFrame:
        """Standardize DAL dataframe format."""
        df = df.copy()
        
        # The first column usually contains account names with embedded codes
        account_name_col = df.columns[0]
        
        # Find period columns (look for numeric data columns)
        numeric_cols = []
        for col in df.columns[1:]:  # Skip first column (account names)
            if df[col].dtype in ['int64', 'float64'] or df[col].notna().any():
                # Check if column has mostly numeric values
                numeric_values = pd.to_numeric(df[col], errors='coerce').notna().sum()
                if numeric_values > len(df) * 0.1:  # At least 10% numeric values
                    numeric_cols.append(col)
        
        if len(numeric_cols) == 0:
            # Fallback: use columns that look like periods
            for col in df.columns[1:]:
                if any(keyword in str(col).lower() for keyword in 
                      ['period', 'balance', 'amount', 'value', 'may', 'apr', 'mar']):
                    numeric_cols.append(col)
        
        # Extract account codes and names
        account_codes = []
        account_names = []
        
        for _, row in df.iterrows():
            account_text = str(row[account_name_col])
            
            if pd.isna(row[account_name_col]) or account_text.strip() == '' or account_text == 'nan':
                continue
            
            # Extract account code and name
            code, name = self._extract_account_code_and_name(account_text)
            
            if code:  # Only include rows with account codes
                account_codes.append(code)
                account_names.append(name)
            
        # Create standardized dataframe
        result_data = {
            'account_code': account_codes,
            'account_name': account_names,
            'statement_type': [statement_type] * len(account_codes)
        }
        
        # Add period data
        for i, col in enumerate(numeric_cols[:3]):  # Limit to 3 periods
            period_name = f"Period_{i+1}" if 'Unnamed' in str(col) else str(col)
            result_data[period_name] = []
            
            for j, (_, row) in enumerate(df.iterrows()):
                if j < len(account_codes):
                    value = row[col] if pd.notna(row[col]) else 0.0
                    if isinstance(value, str):
                        value = pd.to_numeric(value, errors='coerce')
                        if pd.isna(value):
                            value = 0.0
                    result_data[period_name].append(float(value))
        
        result_df = pd.DataFrame(result_data)
        
        # Filter out empty rows
        result_df = result_df[result_df['account_code'].notna() & 
                            (result_df['account_code'] != '') & 
                            (result_df['account_code'] != 'nan')]
        
        self.logger.info(f"Extracted {len(result_df)} accounts for {statement_type}")
        
        return result_df
    
    def _extract_account_code_and_name(self, text: str) -> Tuple[str, str]:
        """Extract account code and name from text."""
        if not isinstance(text, str) or text.strip() == '':
            return '', ''
        
        # Look for patterns like "123456789 - Account Name" or "Account Name (123)"
        patterns = [
            r'^(\d{6,12})\s*[-:]\s*(.+)$',  # "123456789 - Account Name"
            r'^(.+?)\s*\((\d{6,12})\)$',     # "Account Name (123456789)"
            r'(\d{6,12})',                   # Just find any long number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                if len(match.groups()) == 2:
                    if pattern.startswith(r'^(\d'):  # Code first
                        code, name = match.groups()
                    else:  # Name first
                        name, code = match.groups()
                    return code.strip(), name.strip()
                else:  # Just the code
                    code = match.group(1)
                    name = text.replace(code, '').strip(' -:()')
                    return code.strip(), name.strip()
        
        # If no pattern matches but text looks like account name, generate a code
        if len(text.strip()) > 3 and not text.strip().isdigit():
            # Check if it's a section header or account name
            if any(keyword in text.lower() for keyword in 
                  ['asset', 'liability', 'equity', 'revenue', 'expense', 'total', 'current']):
                # Generate a pseudo account code based on the text
                code = str(abs(hash(text)) % 1000000000)[:9].zfill(9)
                return code, text.strip()
        
        return '', text.strip()
    
    def _looks_like_account_entry(self, text: str) -> bool:
        """Check if text looks like an account entry."""
        if not isinstance(text, str):
            return False
        
        # Look for account code patterns
        if re.search(r'\d{6,12}', text):
            return True
        
        # Look for accounting terminology
        accounting_terms = [
            'cash', 'bank', 'receivable', 'inventory', 'asset', 'liability',
            'equity', 'revenue', 'expense', 'depreciation', 'amortization'
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in accounting_terms)
    
    def _extract_dal_periods(self, bs_df: pd.DataFrame, is_df: pd.DataFrame) -> List[str]:
        """Extract time periods from DAL data."""
        periods = []
        
        # Extract from column names
        for df in [bs_df, is_df]:
            if not df.empty:
                for col in df.columns:
                    if col not in ['account_code', 'account_name', 'statement_type']:
                        periods.append(str(col))
        
        # Remove duplicates and sort
        periods = sorted(list(set(periods)))
        
        if not periods:
            periods = ['Current Period', 'Previous Period']
        
        return periods