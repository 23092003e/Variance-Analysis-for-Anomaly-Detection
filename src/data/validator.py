"""
Data validation for financial data integrity.
"""

import logging
import pandas as pd
from typing import List, Dict, Tuple
from config.settings import Settings
from data.models import FinancialData


class DataValidator:
    """Financial data validator."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
    
    def validate(self, financial_data: FinancialData) -> bool:
        """
        Validate financial data integrity.
        
        Args:
            financial_data: Financial data to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        self.logger.info("Starting data validation")
        
        validation_results = []
        
        # Basic structure validation
        validation_results.append(self._validate_structure(financial_data))
        
        # Balance sheet equation validation
        validation_results.append(self._validate_balance_sheet_equation(financial_data))
        
        # Account code validation
        validation_results.append(self._validate_account_codes(financial_data))
        
        # Data consistency validation
        validation_results.append(self._validate_data_consistency(financial_data))
        
        # Numeric data validation
        validation_results.append(self._validate_numeric_data(financial_data))
        
        all_passed = all(validation_results)
        
        if all_passed:
            self.logger.info("Data validation passed")
        else:
            self.logger.error("Data validation failed")
            
        return all_passed
    
    def _validate_structure(self, financial_data: FinancialData) -> bool:
        """Validate basic data structure."""
        try:
            # Check if dataframes are not empty
            if financial_data.balance_sheet.empty:
                self.logger.error("Balance sheet is empty")
                return False
                
            if financial_data.income_statement.empty:
                self.logger.error("Income statement is empty")
                return False
            
            # Check required columns
            required_cols = ['account_code', 'account_name']
            
            for col in required_cols:
                if col not in financial_data.balance_sheet.columns:
                    self.logger.error(f"Missing column in balance sheet: {col}")
                    return False
                    
                if col not in financial_data.income_statement.columns:
                    self.logger.error(f"Missing column in income statement: {col}")
                    return False
            
            self.logger.info("Structure validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Structure validation error: {str(e)}")
            return False
    
    def _validate_balance_sheet_equation(self, financial_data: FinancialData) -> bool:
        """Validate balance sheet equation: Assets = Liabilities + Equity."""
        try:
            bs = financial_data.balance_sheet
            
            # Find numeric columns (likely period data)
            numeric_cols = bs.select_dtypes(include=['number']).columns.tolist()
            
            if not numeric_cols:
                self.logger.warning("No numeric columns found for balance sheet validation")
                return True  # Skip validation if no numeric data
            
            # Define account patterns for balance sheet sections
            asset_patterns = ['1', '11', '12', '13', '14', '15']
            liability_patterns = ['2', '21', '22', '31', '32', '33', '34']
            equity_patterns = ['41', '42', '43']
            
            for col in numeric_cols:
                assets_total = self._sum_accounts_by_pattern(bs, col, asset_patterns)
                liabilities_total = self._sum_accounts_by_pattern(bs, col, liability_patterns)
                equity_total = self._sum_accounts_by_pattern(bs, col, equity_patterns)
                
                total_liab_equity = liabilities_total + equity_total
                
                # Allow for small rounding differences
                tolerance = abs(assets_total) * 0.01 if assets_total != 0 else 1000
                
                if abs(assets_total - total_liab_equity) > tolerance:
                    self.logger.warning(
                        f"Balance sheet equation imbalance in {col}: "
                        f"Assets={assets_total:,.2f}, Liab+Equity={total_liab_equity:,.2f}, "
                        f"Difference={assets_total - total_liab_equity:,.2f}"
                    )
                    # Log warning but don't fail validation
                    
            self.logger.info("Balance sheet equation validation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Balance sheet equation validation error: {str(e)}")
            return False
    
    def _sum_accounts_by_pattern(self, df: pd.DataFrame, value_col: str, patterns: List[str]) -> float:
        """Sum account values matching patterns."""
        total = 0.0
        for pattern in patterns:
            mask = df['account_code'].astype(str).str.startswith(pattern)
            values = df.loc[mask, value_col].fillna(0)
            total += values.sum()
        return total
    
    def _validate_account_codes(self, financial_data: FinancialData) -> bool:
        """Validate account codes format and uniqueness."""
        try:
            all_passed = True
            
            for name, df in [('Balance Sheet', financial_data.balance_sheet),
                           ('Income Statement', financial_data.income_statement)]:
                
                # Check for duplicate account codes
                duplicates = df['account_code'].duplicated().sum()
                if duplicates > 0:
                    self.logger.warning(f"{name} has {duplicates} duplicate account codes")
                
                # Check account code format
                invalid_codes = df[~df['account_code'].astype(str).str.match(r'^\\d+$')]['account_code']
                if len(invalid_codes) > 0:
                    self.logger.warning(f"{name} has invalid account codes: {invalid_codes.tolist()[:5]}")
                
                # Check for empty account names
                empty_names = df['account_name'].isna().sum()
                if empty_names > 0:
                    self.logger.warning(f"{name} has {empty_names} empty account names")
            
            self.logger.info("Account code validation completed")
            return all_passed
            
        except Exception as e:
            self.logger.error(f"Account code validation error: {str(e)}")
            return False
    
    def _validate_data_consistency(self, financial_data: FinancialData) -> bool:
        """Validate data consistency across periods and statements."""
        try:
            # Check if periods match between statements
            bs_numeric_cols = financial_data.balance_sheet.select_dtypes(include=['number']).columns
            is_numeric_cols = financial_data.income_statement.select_dtypes(include=['number']).columns
            
            if len(bs_numeric_cols) != len(is_numeric_cols):
                self.logger.warning(
                    f"Period count mismatch: BS has {len(bs_numeric_cols)} periods, "
                    f"IS has {len(is_numeric_cols)} periods"
                )
            
            self.logger.info("Data consistency validation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Data consistency validation error: {str(e)}")
            return False
    
    def _validate_numeric_data(self, financial_data: FinancialData) -> bool:
        """Validate numeric data quality."""
        try:
            for name, df in [('Balance Sheet', financial_data.balance_sheet),
                           ('Income Statement', financial_data.income_statement)]:
                
                numeric_cols = df.select_dtypes(include=['number']).columns
                
                for col in numeric_cols:
                    # Check for infinite values
                    inf_count = df[col].isin([float('inf'), float('-inf')]).sum()
                    if inf_count > 0:
                        self.logger.warning(f"{name} column {col} has {inf_count} infinite values")
                    
                    # Check for extremely large values (potential data errors)
                    large_values = (abs(df[col]) > 1e12).sum()
                    if large_values > 0:
                        self.logger.warning(f"{name} column {col} has {large_values} extremely large values")
            
            self.logger.info("Numeric data validation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Numeric data validation error: {str(e)}")
            return False