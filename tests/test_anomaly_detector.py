"""
Unit tests for AnomalyDetector.
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import Settings
from analysis.anomaly_detector import AnomalyDetector, Anomaly, AnomalyType, AnomalySeverity
from analysis.variance_analyzer import VarianceResult
from analysis.correlation_engine import CorrelationResult, RelationshipType
from data.models import FinancialData
import pandas as pd


class TestAnomalyDetector:
    """Test cases for AnomalyDetector."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def detector(self, settings):
        """Create AnomalyDetector instance."""
        return AnomalyDetector(settings)
    
    @pytest.fixture
    def sample_variance_results(self):
        """Create sample variance results."""
        return [
            VarianceResult(
                account_code='217000001',
                account_name='Investment Properties',
                category='investment_properties',
                statement_type='BS',
                current_value=1200000,
                previous_value=1000000,
                variance_amount=200000,
                variance_percent=20.0,  # High variance
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            ),
            VarianceResult(
                account_code='632100001',
                account_name='Depreciation',
                category='depreciation',
                statement_type='IS',
                current_value=52000,
                previous_value=50000,
                variance_amount=2000,
                variance_percent=4.0,  # Below threshold
                is_significant=False,
                period_from='Apr_2025',
                period_to='May_2025'
            ),
            VarianceResult(
                account_code='641100001',
                account_name='FX Gain/Loss',
                category='fx_gain_loss',
                statement_type='IS',
                current_value=-15000,
                previous_value=10000,
                variance_amount=-25000,
                variance_percent=-250.0,  # Sign change
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            )
        ]
    
    @pytest.fixture
    def sample_correlation_results(self):
        """Create sample correlation results."""
        return [
            CorrelationResult(
                rule_id=1,
                rule_name='Investment Properties vs Depreciation',
                primary_account='217000001',
                correlated_account='632100001',
                primary_variance=20.0,
                correlated_variance=4.0,
                expected_relationship=RelationshipType.POSITIVE,
                is_violation=True,
                violation_description='Primary increased 20% but correlated increased only 4%',
                severity='high'
            )
        ]
    
    @pytest.fixture
    def sample_financial_data(self):
        """Create sample financial data."""
        return FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test Entity'],
            metadata={}
        )
    
    def test_detect_returns_anomalies(self, detector, sample_variance_results, 
                                    sample_correlation_results, sample_financial_data):
        """Test that detect returns list of anomalies."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        assert isinstance(anomalies, list)
        assert all(isinstance(a, Anomaly) for a in anomalies)
    
    def test_variance_anomaly_detection(self, detector, sample_variance_results,
                                      sample_correlation_results, sample_financial_data):
        """Test detection of variance-based anomalies."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        # Should detect anomaly for high variance (20%)
        variance_anomalies = [a for a in anomalies if a.type == AnomalyType.VARIANCE_ANOMALY]
        
        # Find the Investment Properties anomaly
        ip_anomalies = [a for a in variance_anomalies if a.account_code == '217000001']
        assert len(ip_anomalies) > 0
        
        ip_anomaly = ip_anomalies[0]
        assert ip_anomaly.severity in [AnomalySeverity.CRITICAL, AnomalySeverity.HIGH]
        assert '20.0%' in ip_anomaly.description
    
    def test_sign_change_detection(self, detector, sample_variance_results,
                                 sample_correlation_results, sample_financial_data):
        """Test detection of sign change anomalies."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        # Should detect sign change for FX Gain/Loss
        sign_change_anomalies = [a for a in anomalies if a.type == AnomalyType.SIGN_CHANGE]
        
        fx_anomalies = [a for a in sign_change_anomalies if a.account_code == '641100001']
        assert len(fx_anomalies) > 0
        
        fx_anomaly = fx_anomalies[0]
        assert fx_anomaly.severity == AnomalySeverity.HIGH
        assert 'positive' in fx_anomaly.description and 'negative' in fx_anomaly.description
    
    def test_correlation_anomaly_detection(self, detector, sample_variance_results,
                                         sample_correlation_results, sample_financial_data):
        """Test detection of correlation violation anomalies."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        # Should detect correlation violation
        correlation_anomalies = [a for a in anomalies if a.type == AnomalyType.CORRELATION_VIOLATION]
        assert len(correlation_anomalies) > 0
        
        corr_anomaly = correlation_anomalies[0]
        assert corr_anomaly.rule_violated == 'Investment Properties vs Depreciation'
        assert corr_anomaly.severity == AnomalySeverity.HIGH
    
    def test_severity_classification(self, detector):
        """Test anomaly severity classification."""
        # Create variance results with different severity levels
        variance_results = [
            VarianceResult(
                account_code='TEST001',
                account_name='Critical Test',
                category='test',
                statement_type='BS',
                current_value=120000,
                previous_value=100000,
                variance_amount=20000,
                variance_percent=25.0,  # Critical level
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            ),
            VarianceResult(
                account_code='TEST002',
                account_name='High Test',
                category='test',
                statement_type='BS',
                current_value=115000,
                previous_value=100000,
                variance_amount=15000,
                variance_percent=15.0,  # High level
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            ),
            VarianceResult(
                account_code='TEST003',
                account_name='Medium Test',
                category='test',
                statement_type='BS',
                current_value=107000,
                previous_value=100000,
                variance_amount=7000,
                variance_percent=7.0,  # Medium level
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            )
        ]
        
        financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        anomalies = detector.detect(variance_results, [], financial_data)
        
        # Check severity classification
        critical_anomalies = [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
        high_anomalies = [a for a in anomalies if a.severity == AnomalySeverity.HIGH]
        medium_anomalies = [a for a in anomalies if a.severity == AnomalySeverity.MEDIUM]
        
        assert len(critical_anomalies) > 0  # 25% variance should be critical
        assert len(high_anomalies) > 0     # 15% variance should be high
        assert len(medium_anomalies) > 0   # 7% variance should be medium
    
    def test_anomaly_prioritization(self, detector, sample_variance_results,
                                  sample_correlation_results, sample_financial_data):
        """Test that anomalies are properly prioritized."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        # Should be sorted by severity and magnitude
        if len(anomalies) > 1:
            severity_order = {
                AnomalySeverity.CRITICAL: 4,
                AnomalySeverity.HIGH: 3,
                AnomalySeverity.MEDIUM: 2,
                AnomalySeverity.LOW: 1
            }
            
            for i in range(len(anomalies) - 1):
                current_priority = severity_order[anomalies[i].severity]
                next_priority = severity_order[anomalies[i + 1].severity]
                assert current_priority >= next_priority
    
    def test_get_critical_anomalies(self, detector, sample_variance_results,
                                   sample_correlation_results, sample_financial_data):
        """Test filtering of critical anomalies."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        critical_anomalies = detector.get_critical_anomalies(anomalies)
        
        assert isinstance(critical_anomalies, list)
        assert all(a.severity == AnomalySeverity.CRITICAL for a in critical_anomalies)
    
    def test_get_anomalies_by_type(self, detector, sample_variance_results,
                                  sample_correlation_results, sample_financial_data):
        """Test filtering anomalies by type."""
        anomalies = detector.detect(
            sample_variance_results,
            sample_correlation_results,
            sample_financial_data
        )
        
        variance_anomalies = detector.get_anomalies_by_type(anomalies, AnomalyType.VARIANCE_ANOMALY)
        sign_change_anomalies = detector.get_anomalies_by_type(anomalies, AnomalyType.SIGN_CHANGE)
        
        assert all(a.type == AnomalyType.VARIANCE_ANOMALY for a in variance_anomalies)
        assert all(a.type == AnomalyType.SIGN_CHANGE for a in sign_change_anomalies)
    
    def test_recurring_account_detection(self, detector):
        """Test detection of recurring account anomalies."""
        # Create variance result for recurring account (depreciation)
        variance_results = [
            VarianceResult(
                account_code='632100001',  # Depreciation - recurring account
                account_name='Depreciation',
                category='depreciation',
                statement_type='IS',
                current_value=57000,
                previous_value=50000,
                variance_amount=7000,
                variance_percent=14.0,  # High variance for recurring account
                is_significant=True,
                period_from='Apr_2025',
                period_to='May_2025'
            )
        ]
        
        financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=['Apr_2025', 'May_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        anomalies = detector.detect(variance_results, [], financial_data)
        
        # Should detect both variance and recurring account anomalies
        recurring_anomalies = [a for a in anomalies if a.type == AnomalyType.RECURRING_ACCOUNT_SPIKE]
        assert len(recurring_anomalies) > 0
    
    def test_empty_inputs(self, detector):
        """Test handling of empty inputs."""
        financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=[],
            subsidiaries=[],
            metadata={}
        )
        
        anomalies = detector.detect([], [], financial_data)
        assert isinstance(anomalies, list)
        assert len(anomalies) == 0