"""
Variance analysis engine for period-over-period comparison.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from config.settings import Settings
from config.account_mapping import AccountMapper
from data.models import FinancialData
from utils.calculations import has_sign_change, calculate_variance_percentage, calculate_variance_amount


@dataclass
class VarianceResult:
    """Container for variance analysis results."""
    account_code: str
    account_name: str
    category: str
    statement_type: str
    current_value: float
    previous_value: float
    variance_amount: float
    variance_percent: float
    is_significant: bool
    period_from: str
    period_to: str


class VarianceAnalyzer:
    """Period-over-period variance analysis."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.account_mapper = AccountMapper()
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, financial_data: FinancialData) -> List[VarianceResult]:
        """
        Perform variance analysis on financial data.
        
        Args:
            financial_data: Financial data to analyze
            
        Returns:
            List of variance analysis results
        """
        self.logger.info("Starting variance analysis")
        
        all_results = []
        
        # Analyze balance sheet variances
        bs_results = self._analyze_statement(
            financial_data.balance_sheet, 
            'BS'
        )
        all_results.extend(bs_results)
        
        # Analyze income statement variances
        is_results = self._analyze_statement(
            financial_data.income_statement, 
            'IS'
        )
        all_results.extend(is_results)
        
        self.logger.info(f"Variance analysis completed: {len(all_results)} results")
        
        return all_results
    
    def _analyze_statement(self, df: Optional[pd.DataFrame], statement_type: str) -> List[VarianceResult]:
        """Analyze variances for a single financial statement."""
        results = []
        
        # Check if dataframe is valid
        if df is None or df.empty:
            self.logger.warning(f"No data available for {statement_type} analysis")
            return results
        
        # Check required columns
        required_cols = ['account_code', 'account_name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            self.logger.warning(f"Missing required columns for {statement_type}: {missing_cols}")
            return results
        
        # Get numeric columns (periods)
        try:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        except Exception as e:
            self.logger.error(f"Error detecting numeric columns in {statement_type}: {e}")
            return results
        
        if len(numeric_cols) < 2:
            self.logger.warning(f"Not enough numeric periods for variance analysis in {statement_type} (found {len(numeric_cols)})")
            # Try to convert columns that might be numeric
            potential_numeric_cols = []
            for col in df.columns:
                if col not in required_cols:
                    try:
                        # Try to convert column to numeric
                        numeric_series = pd.to_numeric(df[col], errors='coerce')
                        if not numeric_series.isna().all():  # If at least some values are numeric
                            potential_numeric_cols.append(col)
                    except:
                        continue
            
            if len(potential_numeric_cols) < 2:
                self.logger.warning(f"Still not enough numeric columns after conversion attempt in {statement_type}")
                return results
            
            # Use converted columns
            numeric_cols = potential_numeric_cols
            self.logger.info(f"Using converted numeric columns for {statement_type}: {numeric_cols}")
        
        # Use last two periods for comparison
        current_period = numeric_cols[-1]
        previous_period = numeric_cols[-2]
        
        self.logger.info(f"Analyzing {statement_type}: {previous_period} vs {current_period}")
        
        for _, row in df.iterrows():
            try:
                account_code = str(row.get('account_code', ''))
                account_name = str(row.get('account_name', ''))
                
                if not account_code or account_code in ['nan', 'None']:
                    continue
                
                # Get account information
                account_info = self.account_mapper.get_account_info(account_code)
                category = account_info.category if account_info else 'unknown'
                
                # Get values - handle both numeric and string columns
                current_value = self._get_numeric_value(row, current_period)
                previous_value = self._get_numeric_value(row, previous_period)
                
                # Calculate variance using centralized functions
                variance_amount = calculate_variance_amount(current_value, previous_value)
                variance_percent = calculate_variance_percentage(current_value, previous_value)
                
                # Determine if variance is significant
                is_significant = self._is_variance_significant(
                    current_value, previous_value, variance_percent, category
                )
                
                result = VarianceResult(
                    account_code=account_code,
                    account_name=account_name,
                    category=category,
                    statement_type=statement_type,
                    current_value=current_value,
                    previous_value=previous_value,
                    variance_amount=variance_amount,
                    variance_percent=variance_percent,
                    is_significant=is_significant,
                    period_from=previous_period,
                    period_to=current_period
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error analyzing row in {statement_type}: {e}")
                continue
        
        self.logger.info(f"Completed {statement_type} analysis: {len(results)} results")
        return results
    
    def _get_numeric_value(self, row: pd.Series, column: str) -> float:
        """Safely extract numeric value from row."""
        try:
            value = row.get(column, 0)
            if pd.isna(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _is_variance_significant(self, current_value: float, previous_value: float, 
                               variance_percent: float, category: str) -> bool:
        """Determine if variance is significant based on thresholds."""
        # Check for sign changes (always significant)
        if has_sign_change(current_value, previous_value):
            return True
        
        # Get account-specific threshold
        threshold = self.settings.get_variance_threshold(category)
        
        # Category-specific thresholds
        category_thresholds = {
            'opex': 10.0,
            'staff_costs': 10.0,
            'other_expenses': 10.0,
            'borrowings': 2.0,
            'depreciation': 5.0
        }
        
        if category in category_thresholds:
            threshold = category_thresholds[category]
        
        # Check percentage threshold
        if abs(variance_percent) >= threshold:
            return True
        
        # Check materiality threshold if configured for this account
        # Note: This would need account_code access, skipping for now
        return False
    
    # Removed _has_sign_change method - now using centralized function from utils.calculations
    
    def get_significant_variances(self, results: List[VarianceResult]) -> List[VarianceResult]:
        """Filter results to only significant variances."""
        return [result for result in results if result.is_significant]
    
    def get_variances_by_category(self, results: List[VarianceResult], category: str) -> List[VarianceResult]:
        """Filter results by account category."""
        return [result for result in results if result.category == category]
    
    def get_top_variances(self, results: List[VarianceResult], n: int = 10, by: str = 'percent') -> List[VarianceResult]:
        """
        Get top N variances by amount or percentage.
        
        Args:
            results: Variance results
            n: Number of top results to return
            by: Sort by 'percent' or 'amount'
            
        Returns:
            Top N variance results
        """
        if by == 'percent':
            sorted_results = sorted(results, key=lambda x: abs(x.variance_percent), reverse=True)
        else:
            sorted_results = sorted(results, key=lambda x: abs(x.variance_amount), reverse=True)
        
        return sorted_results[:n]
    
    def get_recurring_account_variances(self, results: List[VarianceResult]) -> List[VarianceResult]:
        """Get variances for recurring accounts only."""
        recurring_accounts = self.account_mapper.get_recurring_accounts()
        return [result for result in results if result.account_code in recurring_accounts]
    
    def calculate_summary_stats(self, results: List[VarianceResult]) -> Dict:
        """Calculate summary statistics for variance results."""
        if not results:
            return {}
        
        variance_percents = [abs(r.variance_percent) for r in results]
        significant_count = sum(1 for r in results if r.is_significant)
        
        return {
            'total_accounts': len(results),
            'significant_variances': significant_count,
            'significant_percentage': (significant_count / len(results)) * 100,
            'avg_variance_percent': np.mean(variance_percents),
            'median_variance_percent': np.median(variance_percents),
            'max_variance_percent': max(variance_percents) if variance_percents else 0,
            'min_variance_percent': min(variance_percents) if variance_percents else 0
        }