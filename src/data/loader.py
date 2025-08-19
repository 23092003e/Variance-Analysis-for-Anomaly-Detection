"""
Data loading and preprocessing for Excel files.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any

from config.settings import Settings
from data.models import FinancialData


class DataLoader:
    """Excel data loader and preprocessor."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
    
    def load_excel_file(self, file_path: str) -> FinancialData:
        """
        Load financial data from Excel file.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            FinancialData object containing loaded data
        """
        self.logger.info(f"Loading Excel file: {file_path}")
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            
            # Extract balance sheet and income statement
            balance_sheet = self._extract_balance_sheet(excel_data)
            income_statement = self._extract_income_statement(excel_data)
            
            # Extract periods and subsidiaries
            periods = self._extract_periods(balance_sheet, income_statement)
            subsidiaries = self._extract_subsidiaries(balance_sheet, income_statement)
            
            # Create metadata
            metadata = {
                'file_path': file_path,
                'sheets': list(excel_data.keys()),
                'load_timestamp': pd.Timestamp.now()
            }
            
            financial_data = FinancialData(
                balance_sheet=balance_sheet,
                income_statement=income_statement,
                periods=periods,
                subsidiaries=subsidiaries,
                metadata=metadata
            )
            
            self.logger.info(f"Successfully loaded data: {len(periods)} periods, "
                           f"{len(subsidiaries)} subsidiaries")
            
            return financial_data
            
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {str(e)}")
            raise
    
    def _extract_balance_sheet(self, excel_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract balance sheet data from Excel sheets."""
        bs_sheets = [name for name in excel_data.keys() 
                    if any(keyword in name.lower() for keyword in ['balance', 'bs', 'bảng cân đối'])]
        
        if not bs_sheets:
            # Try to find data in the first sheet
            first_sheet = list(excel_data.values())[0]
            if self._looks_like_balance_sheet(first_sheet):
                return self._standardize_dataframe(first_sheet, 'BS')
            raise ValueError("No balance sheet data found")
        
        # Use the first balance sheet found
        bs_data = excel_data[bs_sheets[0]]
        return self._standardize_dataframe(bs_data, 'BS')
    
    def _extract_income_statement(self, excel_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract income statement data from Excel sheets."""
        is_sheets = [name for name in excel_data.keys() 
                    if any(keyword in name.lower() for keyword in ['income', 'is', 'p&l', 'pl', 'kết quả'])]
        
        if not is_sheets:
            # Try to find IS data in combined sheet
            for sheet_name, sheet_data in excel_data.items():
                if self._looks_like_income_statement(sheet_data):
                    return self._standardize_dataframe(sheet_data, 'IS')
            raise ValueError("No income statement data found")
        
        # Use the first income statement found
        is_data = excel_data[is_sheets[0]]
        return self._standardize_dataframe(is_data, 'IS')
    
    def _standardize_dataframe(self, df: pd.DataFrame, statement_type: str) -> pd.DataFrame:
        """Standardize dataframe format."""
        df = df.copy()
        
        # Find account code and name columns
        account_col = self._find_account_column(df)
        name_col = self._find_name_column(df)
        
        if account_col is None:
            raise ValueError(f"No account code column found in {statement_type}")
        
        # Rename columns for consistency
        df = df.rename(columns={
            account_col: 'account_code',
            name_col: 'account_name' if name_col else 'account_name'
        })
        
        # Add account_name if missing
        if 'account_name' not in df.columns:
            df['account_name'] = df['account_code']
        
        # Clean account codes
        df['account_code'] = df['account_code'].astype(str).str.strip()
        df['account_name'] = df['account_name'].astype(str).str.strip()
        
        # Filter out empty rows
        df = df[df['account_code'].notna() & (df['account_code'] != '') & (df['account_code'] != 'nan')]
        
        # Add statement type
        df['statement_type'] = statement_type
        
        return df
    
    def _find_account_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the account code column."""
        possible_names = ['account', 'code', 'account_code', 'mã tài khoản', 'tài khoản']
        
        for col in df.columns:
            if any(name in str(col).lower() for name in possible_names):
                return col
        
        # Check first column if it looks like account codes
        first_col = df.columns[0]
        if df[first_col].astype(str).str.match(r'^\d+').sum() > len(df) * 0.5:
            return first_col
            
        return None
    
    def _find_name_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the account name column."""
        possible_names = ['name', 'description', 'account_name', 'tên tài khoản', 'diễn giải']
        
        for col in df.columns:
            if any(name in str(col).lower() for name in possible_names):
                return col
                
        return None
    
    def _looks_like_balance_sheet(self, df: pd.DataFrame) -> bool:
        """Check if dataframe looks like balance sheet."""
        text_content = ' '.join(df.astype(str).values.flatten()).lower()
        bs_keywords = ['assets', 'liabilities', 'equity', 'tài sản', 'nợ phải trả', 'vốn chủ sở hữu']
        return sum(keyword in text_content for keyword in bs_keywords) >= 2
    
    def _looks_like_income_statement(self, df: pd.DataFrame) -> bool:
        """Check if dataframe looks like income statement."""
        text_content = ' '.join(df.astype(str).values.flatten()).lower()
        is_keywords = ['revenue', 'expense', 'income', 'doanh thu', 'chi phí', 'lợi nhuận']
        return sum(keyword in text_content for keyword in is_keywords) >= 2
    
    def _extract_periods(self, bs_df: pd.DataFrame, is_df: pd.DataFrame) -> List[str]:
        """Extract time periods from data."""
        # Look for date columns
        date_columns = []
        for df in [bs_df, is_df]:
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in ['date', 'period', 'month', 'tháng', 'ngày']):
                    date_columns.append(col)
                # Check if column contains date-like values
                elif df[col].dtype == 'object':
                    sample_values = df[col].dropna().astype(str).head(10)
                    if sample_values.str.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}').sum() > 0:
                        date_columns.append(col)
        
        if date_columns:
            # Extract unique periods
            all_periods = set()
            for df in [bs_df, is_df]:
                for col in date_columns:
                    if col in df.columns:
                        periods = df[col].dropna().unique()
                        all_periods.update([str(p) for p in periods])
            return sorted(list(all_periods))
        
        # Default periods if none found
        return ['Current Period', 'Previous Period']
    
    def _extract_subsidiaries(self, bs_df: pd.DataFrame, is_df: pd.DataFrame) -> List[str]:
        """Extract subsidiaries from data."""
        # Look for subsidiary columns
        subsidiary_columns = []
        for df in [bs_df, is_df]:
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in 
                      ['subsidiary', 'company', 'entity', 'công ty', 'đơn vị']):
                    subsidiary_columns.append(col)
        
        if subsidiary_columns:
            all_subsidiaries = set()
            for df in [bs_df, is_df]:
                for col in subsidiary_columns:
                    if col in df.columns:
                        subsidiaries = df[col].dropna().unique()
                        all_subsidiaries.update([str(s) for s in subsidiaries])
            return sorted(list(all_subsidiaries))
        
        # Default subsidiary if none found
        return ['Main Entity']
    
    def validate_data(self, financial_data: FinancialData) -> bool:
        """Validate loaded financial data."""
        from data.validator import DataValidator
        validator = DataValidator(self.settings)
        return validator.validate(financial_data)