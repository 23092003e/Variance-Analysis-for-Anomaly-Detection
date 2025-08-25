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
            
            # Log all available sheets
            available_sheets = list(excel_data.keys())
            self.logger.info(f"Found {len(available_sheets)} sheets: {available_sheets}")
            
            # Log sheet sizes
            for sheet_name, sheet_data in excel_data.items():
                rows, cols = sheet_data.shape
                self.logger.debug(f"Sheet '{sheet_name}': {rows} rows x {cols} columns")
            
            # Extract balance sheet and income statement
            balance_sheet = self._extract_balance_sheet(excel_data)
            income_statement = self._extract_income_statement(excel_data)
            
            # Extract periods and subsidiaries
            periods = self._extract_periods(balance_sheet, income_statement)
            subsidiaries = self._extract_subsidiaries(balance_sheet, income_statement)
            
            # Create metadata with consistent source_file field
            metadata = {
                'file_path': file_path,
                'source_file': file_path,  # Consistent field for Excel generator
                'sheets': available_sheets,
                'load_timestamp': pd.Timestamp.now()
            }
            
            financial_data = FinancialData(
                balance_sheet=balance_sheet,
                income_statement=income_statement,
                periods=periods,
                subsidiaries=subsidiaries,
                metadata=metadata
            )
            
            # Log final summary
            bs_rows = len(balance_sheet) if not balance_sheet.empty else 0
            pl_rows = len(income_statement) if not income_statement.empty else 0
            self.logger.info(f"Successfully loaded data: {bs_rows} BS records, {pl_rows} PL records, "
                           f"{len(periods)} periods, {len(subsidiaries)} subsidiaries")
            self.logger.info(f"Periods found: {periods}")
            self.logger.info(f"Subsidiaries found: {subsidiaries}")
            
            return financial_data
            
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {str(e)}")
            raise
    
    def _extract_balance_sheet(self, excel_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract balance sheet data from BS breakdown and BS sheets."""
        self.logger.info("Extracting balance sheet data from BS breakdown and BS sheets")
        
        balance_sheet_data = []
        total_rows = 0
        
        # Find BS breakdown sheet (try different variations)
        bs_breakdown_sheet = None
        for sheet_name in excel_data.keys():
            sheet_lower = sheet_name.lower().replace(' ', '').replace('_', '')
            if sheet_lower in ['bsbreakdown', 'balancesheetbreakdown']:
                bs_breakdown_sheet = sheet_name
                break
        
        if bs_breakdown_sheet:
            bs_breakdown = self._standardize_dataframe(excel_data[bs_breakdown_sheet], 'balance_sheet')
            balance_sheet_data.append(bs_breakdown)
            rows_count = len(bs_breakdown)
            total_rows += rows_count
            self.logger.info(f"Found BS breakdown sheet '{bs_breakdown_sheet}' with {rows_count} rows (after standardization)")
        else:
            self.logger.warning("BS breakdown sheet not found (tried variations: 'BS breakdown', 'BSbreakdown', 'BS Breakdown')")
        
        # Find BS sheet
        bs_sheet = None
        for sheet_name in excel_data.keys():
            if sheet_name.upper() == 'BS':
                bs_sheet = sheet_name
                break
        
        if bs_sheet:
            bs_data = self._standardize_dataframe(excel_data[bs_sheet], 'balance_sheet')
            balance_sheet_data.append(bs_data)
            rows_count = len(bs_data)
            total_rows += rows_count
            self.logger.info(f"Found BS sheet '{bs_sheet}' with {rows_count} rows (after standardization)")
        else:
            self.logger.warning("BS sheet not found")
        
        if not balance_sheet_data:
            available_sheets = list(excel_data.keys())
            self.logger.error(f"No balance sheet data found. Available sheets: {available_sheets}")
            raise ValueError("No balance sheet data found. Expected 'BS breakdown', 'BSbreakdown', 'BS Breakdown', or 'BS' sheets.")
        
        # Combine all balance sheet data
        combined_bs = pd.concat(balance_sheet_data, ignore_index=True)
        final_rows = len(combined_bs)
        self.logger.info(f"Combined balance sheet data: {total_rows} total rows -> {final_rows} final rows")
        
        return combined_bs
    
    def _extract_income_statement(self, excel_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract income statement data from PL breakdown sheet."""
        self.logger.info("Extracting income statement data from PL breakdown sheet")
        
        # Find PL breakdown sheet (try different variations)
        pl_breakdown_sheet = None
        for sheet_name in excel_data.keys():
            sheet_lower = sheet_name.lower().replace(' ', '').replace('_', '')
            if sheet_lower in ['plbreakdown', 'profitlossbreakdown']:
                pl_breakdown_sheet = sheet_name
                break
        
        if not pl_breakdown_sheet:
            available_sheets = list(excel_data.keys())
            self.logger.error(f"PL breakdown sheet not found. Available sheets: {available_sheets}")
            self.logger.error("Tried variations: 'PL breakdown', 'PLbreakdown', 'PL Breakdown', 'Profit Loss Breakdown'")
            raise ValueError("No income statement data found. Expected 'PL breakdown', 'PLbreakdown', or 'PL Breakdown' sheet.")
        
        pl_breakdown = self._standardize_dataframe(excel_data[pl_breakdown_sheet], 'income_statement')
        rows_count = len(pl_breakdown)
        self.logger.info(f"Found PL breakdown sheet '{pl_breakdown_sheet}' with {rows_count} rows (after standardization)")
        
        # Log sample of account codes from PL breakdown
        if not pl_breakdown.empty and 'account_code' in pl_breakdown.columns:
            sample_codes = pl_breakdown['account_code'].head(5).tolist()
            self.logger.debug(f"Sample account codes from PL breakdown: {sample_codes}")
        
        return pl_breakdown
    
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
        """Find the account code column with enhanced detection."""
        # Extended list of possible column names
        possible_names = [
            'account', 'code', 'account_code', 'accountcode', 'account_number', 'accountnumber',
            'mã tài khoản', 'ma tai khoan', 'tài khoản', 'tai khoan', 'mã', 'ma',
            'account_id', 'id', 'acc_code', 'acccode', 'acc', 'a/c'
        ]
        
        # First, check for exact or partial matches
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            # Check exact matches first
            if col_lower in possible_names:
                self.logger.info(f"Found account column by exact match: {col}")
                return col
                
            # Check partial matches
            for name in possible_names:
                if name in col_lower:
                    self.logger.info(f"Found account column by partial match: {col} (contains '{name}')")
                    return col
        
        # Second, check column content patterns
        for col in df.columns:
            try:
                # Convert to string and check for numeric patterns
                col_values = df[col].dropna().astype(str)
                
                if len(col_values) == 0:
                    continue
                
                # Check for account-like patterns
                numeric_pattern_count = col_values.str.match(r'^\d{4,9}$').sum()
                mixed_pattern_count = col_values.str.match(r'^[A-Z]{1,4}\d+$').sum()
                
                # If majority of values look like account codes
                if numeric_pattern_count > len(col_values) * 0.6:
                    self.logger.info(f"Found account column by numeric pattern: {col} ({numeric_pattern_count}/{len(col_values)} matches)")
                    return col
                elif mixed_pattern_count > len(col_values) * 0.6:
                    self.logger.info(f"Found account column by mixed pattern: {col} ({mixed_pattern_count}/{len(col_values)} matches)")
                    return col
                    
            except Exception as e:
                self.logger.debug(f"Error checking column {col} for patterns: {e}")
                continue
        
        # Third, check positional heuristics (first column)
        if len(df.columns) > 0:
            first_col = df.columns[0]
            try:
                first_col_values = df[first_col].dropna().astype(str)
                if len(first_col_values) > 0:
                    # Check if first column looks like codes
                    code_like_count = first_col_values.str.match(r'^\d+').sum()
                    if code_like_count > len(first_col_values) * 0.5:
                        self.logger.info(f"Using first column as account column: {first_col}")
                        return first_col
            except:
                pass
        
        self.logger.warning("Could not identify account code column")
        return None
    
    def _find_name_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the account name column."""
        possible_names = ['name', 'description', 'account_name', 'tên tài khoản', 'diễn giải']
        
        for col in df.columns:
            if any(name in str(col).lower() for name in possible_names):
                return col
                
        return None
    
    def _looks_like_balance_sheet(self, sheet_name: str) -> bool:
        """Check if sheet name indicates balance sheet data."""
        sheet_lower = sheet_name.lower().replace(' ', '').replace('_', '')
        return sheet_lower in ['bs', 'bsbreakdown', 'balancesheet', 'balancesheetbreakdown', 'bs breakdown']
    
    def _looks_like_income_statement(self, sheet_name: str) -> bool:
        """Check if sheet name indicates income statement data."""
        sheet_lower = sheet_name.lower().replace(' ', '').replace('_', '')
        return sheet_lower in ['plbreakdown', 'profitandloss', 'incomestatement', 'profitlossbreakdown', 'pl breakdown']
    
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