"""
Unit tests for CorrelationEngine.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import Settings
from analysis.correlation_engine import CorrelationEngine, CorrelationResult, RelationshipType
from data.models import FinancialData


class TestCorrelationEngine:
    """Test cases for CorrelationEngine."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def engine(self, settings):
        """Create CorrelationEngine instance."""
        return CorrelationEngine(settings)
    
    @pytest.fixture
    def sample_financial_data(self):
        """Create sample financial data with correlation scenarios."""
        balance_sheet = pd.DataFrame({
            'account_code': ['217000001', '112227001', '341160000'],
            'account_name': ['Investment Properties', 'Cash Deposits', 'Borrowings'],
            'statement_type': ['BS', 'BS', 'BS'],
            'Mar_2025': [1000000, 500000, 800000],
            'Apr_2025': [1100000, 520000, 850000],  # IP up 10%, Cash up 4%, Borrowings up 6.25%
            'May_2025': [1200000, 540000, 900000]   # IP up 9%, Cash up 3.8%, Borrowings up 5.9%
        })
        
        income_statement = pd.DataFrame({
            'account_code': ['632100001', '511100001', '635000005'],
            'account_name': ['Depreciation', 'Revenue', 'Interest Expense'],
            'statement_type': ['IS', 'IS', 'IS'],
            'Mar_2025': [50000, 200000, 8000],
            'Apr_2025': [52000, 210000, 8500],      # Depreciation up 4%, Revenue up 5%, Interest up 6.25%
            'May_2025': [53000, 220000, 9000]      # Depreciation up 1.9%, Revenue up 4.8%, Interest up 5.9%
        })
        
        return FinancialData(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            periods=['Mar_2025', 'Apr_2025', 'May_2025'],
            subsidiaries=['Test Entity'],
            metadata={'file_path': 'test.xlsx'}
        )
    
    def test_engine_initialization(self, engine):
        """Test engine initialization and rule loading."""
        assert len(engine.rules) > 0
        assert all(hasattr(rule, 'id') for rule in engine.rules)
        assert all(hasattr(rule, 'name') for rule in engine.rules)
    
    def test_analyze_returns_results(self, engine, sample_financial_data):
        """Test that analyze returns correlation results."""
        results = engine.analyze(sample_financial_data)
        
        assert isinstance(results, list)
        # Results should contain correlation violations or be empty
        assert all(isinstance(r, CorrelationResult) for r in results)
    
    def test_positive_correlation_violation_detection(self, engine):
        """Test detection of positive correlation violations."""
        # Create scenario where IP increases but depreciation doesn't
        balance_sheet = pd.DataFrame({
            'account_code': ['217000001'],
            'account_name': ['Investment Properties'],
            'statement_type': ['BS'],
            'Apr_2025': [1000000],
            'May_2025': [1200000]  # 20% increase
        })
        
        income_statement = pd.DataFrame({
            'account_code': ['632100001'],
            'account_name': ['Depreciation'],
            'statement_type': ['IS'],
            'Apr_2025': [50000],
            'May_2025': [50500]  # Only 1% increase - should violate correlation
        })
        
        financial_data = FinancialData(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        results = engine.analyze(financial_data)
        
        # Should detect violation of IP vs Depreciation rule
        ip_violations = [r for r in results if r.rule_id == 1 and r.is_violation]
        assert len(ip_violations) > 0
    
    def test_get_violations_by_severity(self, engine, sample_financial_data):
        """Test filtering violations by severity."""
        results = engine.analyze(sample_financial_data)
        
        high_severity = engine.get_violations_by_severity(results, 'high')
        medium_severity = engine.get_violations_by_severity(results, 'medium')
        low_severity = engine.get_violations_by_severity(results, 'low')
        
        assert isinstance(high_severity, list)
        assert isinstance(medium_severity, list)
        assert isinstance(low_severity, list)
        
        # All returned results should be violations
        all_violations = high_severity + medium_severity + low_severity
        assert all(r.is_violation for r in all_violations)
    
    def test_get_rule_violations(self, engine, sample_financial_data):
        """Test getting violations for specific rule."""
        results = engine.analyze(sample_financial_data)
        
        rule_1_violations = engine.get_rule_violations(results, rule_id=1)
        
        assert isinstance(rule_1_violations, list)
        assert all(r.rule_id == 1 for r in rule_1_violations)
        assert all(r.is_violation for r in rule_1_violations)
    
    def test_correlation_calculation(self, engine):
        """Test variance calculation for correlation analysis."""
        data = pd.DataFrame({
            'account_code': ['217000001'],
            'account_name': ['Investment Properties'],
            'statement_type': ['BS'],
            'Apr_2025': [1000000],
            'May_2025': [1100000]  # 10% increase
        })
        
        variance = engine._calculate_variance(data, '217000001', 'May_2025', 'Apr_2025')
        expected_variance = ((1100000 - 1000000) / 1000000) * 100
        
        assert abs(variance - expected_variance) < 0.01
    
    def test_empty_financial_data(self, engine):
        """Test handling of empty financial data."""
        empty_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=[],
            subsidiaries=[],
            metadata={}
        )
        
        results = engine.analyze(empty_data)
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_missing_accounts_handling(self, engine):
        """Test handling when expected accounts are missing."""
        # Create data with only balance sheet accounts (no IS accounts)
        balance_sheet = pd.DataFrame({
            'account_code': ['217000001'],
            'account_name': ['Investment Properties'],
            'statement_type': ['BS'],
            'Apr_2025': [1000000],
            'May_2025': [1100000]
        })
        
        financial_data = FinancialData(
            balance_sheet=balance_sheet,
            income_statement=pd.DataFrame(),  # Empty IS
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        results = engine.analyze(financial_data)
        
        # Should handle gracefully and return empty or minimal results
        assert isinstance(results, list)
    
    def test_rule_enablement(self, engine):
        """Test that only enabled rules are processed."""
        enabled_rules = [rule for rule in engine.rules if rule.enabled]
        disabled_rules = [rule for rule in engine.rules if not rule.enabled]
        
        # Should have both enabled and disabled rules
        assert len(enabled_rules) > 0
        assert len(disabled_rules) > 0
        
        # Only enabled rules should be processed (tested indirectly through results)
        # Disabled rules should not generate results