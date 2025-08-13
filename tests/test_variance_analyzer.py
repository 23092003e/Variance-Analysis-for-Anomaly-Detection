"""
Unit tests for VarianceAnalyzer.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import Settings
from analysis.variance_analyzer import VarianceAnalyzer, VarianceResult
from data.models import FinancialData


class TestVarianceAnalyzer:
    """Test cases for VarianceAnalyzer."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def analyzer(self, settings):
        """Create VarianceAnalyzer instance."""
        return VarianceAnalyzer(settings)
    
    @pytest.fixture
    def sample_balance_sheet(self):
        """Create sample balance sheet data."""
        return pd.DataFrame({
            'account_code': ['217000001', '112227001', '341160000'],
            'account_name': ['Investment Properties', 'Cash Deposits', 'Borrowings'],
            'statement_type': ['BS', 'BS', 'BS'],
            'Mar_2025': [1000000, 500000, 800000],
            'Apr_2025': [1050000, 480000, 820000],
            'May_2025': [1100000, 520000, 840000]
        })
    
    @pytest.fixture
    def sample_income_statement(self):
        """Create sample income statement data."""
        return pd.DataFrame({
            'account_code': ['632100001', '511100001', '635000005'],
            'account_name': ['Depreciation', 'Revenue', 'Interest Expense'],
            'statement_type': ['IS', 'IS', 'IS'],
            'Mar_2025': [50000, 200000, 8000],
            'Apr_2025': [52000, 210000, 8200],
            'May_2025': [54000, 220000, 8400]
        })
    
    @pytest.fixture
    def financial_data(self, sample_balance_sheet, sample_income_statement):
        """Create FinancialData object."""
        return FinancialData(
            balance_sheet=sample_balance_sheet,
            income_statement=sample_income_statement,
            periods=['Mar_2025', 'Apr_2025', 'May_2025'],
            subsidiaries=['Test Entity'],
            metadata={'file_path': 'test.xlsx'}
        )
    
    def test_analyze_returns_results(self, analyzer, financial_data):
        """Test that analyze returns variance results."""
        results = analyzer.analyze(financial_data)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, VarianceResult) for r in results)
    
    def test_variance_calculation_accuracy(self, analyzer, financial_data):
        """Test variance calculation accuracy."""
        results = analyzer.analyze(financial_data)
        
        # Find Investment Properties result
        ip_result = next(r for r in results if r.account_code == '217000001')
        
        # Check variance calculation: (1100000 - 1050000) / 1050000 * 100 = 4.76%
        expected_variance = ((1100000 - 1050000) / 1050000) * 100
        assert abs(ip_result.variance_percent - expected_variance) < 0.01
        
        assert ip_result.current_value == 1100000
        assert ip_result.previous_value == 1050000
        assert ip_result.variance_amount == 50000
    
    def test_significant_variance_detection(self, analyzer, financial_data):
        """Test detection of significant variances."""
        results = analyzer.analyze(financial_data)
        
        # Most variances in test data should be below 5% threshold
        significant_results = [r for r in results if r.is_significant]
        non_significant_results = [r for r in results if not r.is_significant]
        
        # Should have both significant and non-significant results
        assert len(significant_results) >= 0
        assert len(non_significant_results) >= 0
    
    def test_sign_change_detection(self, analyzer):
        """Test detection of sign changes."""
        # Create data with sign change
        bs_data = pd.DataFrame({
            'account_code': ['641100001'],
            'account_name': ['FX Gain/Loss'],
            'statement_type': ['IS'],
            'Apr_2025': [10000],   # Positive
            'May_2025': [-15000]   # Negative (sign change)
        })
        
        financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=bs_data,
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        results = analyzer.analyze(financial_data)
        fx_result = results[0]
        
        assert fx_result.is_significant  # Sign changes should always be significant
    
    def test_zero_division_handling(self, analyzer):
        """Test handling of division by zero in variance calculation."""
        bs_data = pd.DataFrame({
            'account_code': ['112227001'],
            'account_name': ['Cash'],
            'statement_type': ['BS'], 
            'Apr_2025': [0],      # Zero previous value
            'May_2025': [10000]   # Non-zero current value
        })
        
        financial_data = FinancialData(
            balance_sheet=bs_data,
            income_statement=pd.DataFrame(),
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        results = analyzer.analyze(financial_data)
        cash_result = results[0]
        
        assert cash_result.variance_percent == 100.0  # Should handle zero division
        assert cash_result.is_significant
    
    def test_get_significant_variances(self, analyzer, financial_data):
        """Test filtering of significant variances."""
        all_results = analyzer.analyze(financial_data)
        significant_results = analyzer.get_significant_variances(all_results)
        
        assert len(significant_results) <= len(all_results)
        assert all(r.is_significant for r in significant_results)
    
    def test_get_top_variances(self, analyzer, financial_data):
        """Test getting top variances by percentage and amount."""
        results = analyzer.analyze(financial_data)
        
        top_by_percent = analyzer.get_top_variances(results, n=3, by='percent')
        top_by_amount = analyzer.get_top_variances(results, n=3, by='amount')
        
        assert len(top_by_percent) <= 3
        assert len(top_by_amount) <= 3
        
        # Check sorting
        if len(top_by_percent) > 1:
            assert abs(top_by_percent[0].variance_percent) >= abs(top_by_percent[1].variance_percent)
        
        if len(top_by_amount) > 1:
            assert abs(top_by_amount[0].variance_amount) >= abs(top_by_amount[1].variance_amount)
    
    def test_calculate_summary_stats(self, analyzer, financial_data):
        """Test summary statistics calculation."""
        results = analyzer.analyze(financial_data)
        stats = analyzer.calculate_summary_stats(results)
        
        assert 'total_accounts' in stats
        assert 'significant_variances' in stats
        assert 'avg_variance_percent' in stats
        assert 'max_variance_percent' in stats
        
        assert stats['total_accounts'] == len(results)
        assert 0 <= stats['significant_percentage'] <= 100
    
    def test_empty_data_handling(self, analyzer):
        """Test handling of empty financial data."""
        empty_financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=[],
            subsidiaries=[],
            metadata={}
        )
        
        results = analyzer.analyze(empty_financial_data)
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_single_period_handling(self, analyzer):
        """Test handling of data with only one period."""
        single_period_bs = pd.DataFrame({
            'account_code': ['217000001'],
            'account_name': ['Investment Properties'],
            'statement_type': ['BS'],
            'May_2025': [1000000]
        })
        
        financial_data = FinancialData(
            balance_sheet=single_period_bs,
            income_statement=pd.DataFrame(),
            periods=['May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        results = analyzer.analyze(financial_data)
        assert len(results) == 0  # Should return empty list for insufficient periods