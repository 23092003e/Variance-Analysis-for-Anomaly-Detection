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
    
    def _analyze_statement(self, df: pd.DataFrame, statement_type: str) -> List[VarianceResult]:
        """Analyze variances for a single financial statement."""
        results = []
        
        # Get numeric columns (periods)
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) < 2:
            self.logger.warning(f"Not enough periods for variance analysis in {statement_type}")
            return results
        
        # Use last two periods for comparison
        current_period = numeric_cols[-1]
        previous_period = numeric_cols[-2]
        
        for _, row in df.iterrows():
            account_code = str(row['account_code'])
            account_name = str(row['account_name'])
            
            # Get account information
            account_info = self.account_mapper.get_account_info(account_code)
            category = account_info.category if account_info else 'unknown'
            
            # Get values
            current_value = row[current_period] if pd.notna(row[current_period]) else 0.0
            previous_value = row[previous_period] if pd.notna(row[previous_period]) else 0.0
            
            # Calculate variance
            variance_amount = current_value - previous_value
            
            # Calculate percentage variance
            if previous_value != 0:
                variance_percent = (variance_amount / abs(previous_value)) * 100
            else:
                variance_percent = 100.0 if current_value != 0 else 0.0
            
            # Determine if variance is significant
            threshold = self.settings.get_variance_threshold(category)
            is_significant = abs(variance_percent) >= threshold
            
            # Check for sign changes (always significant)
            if self._has_sign_change(current_value, previous_value):
                is_significant = True
            
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
        
        return results
    
    def _has_sign_change(self, current: float, previous: float) -> bool:
        """Check if there's a sign change between periods."""
        if previous == 0 and current != 0:
            return True
        if previous != 0 and current == 0:
            return True
        if previous > 0 and current < 0:
            return True
        if previous < 0 and current > 0:
            return True
        return False
    
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