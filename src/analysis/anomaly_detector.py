"""
Anomaly detection engine that combines variance and correlation analysis.
"""

import logging
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from config.settings import Settings
from config.account_mapping import AccountMapper
from data.loader import FinancialData
from analysis.variance_analyzer import VarianceResult
from analysis.correlation_engine import CorrelationResult


class AnomalyType(Enum):
    """Types of anomalies detected."""
    VARIANCE_ANOMALY = "variance"
    CORRELATION_VIOLATION = "correlation"
    SIGN_CHANGE = "sign_change"
    RECURRING_ACCOUNT_SPIKE = "recurring_spike"
    QUARTERLY_PATTERN_BREAK = "quarterly_pattern"


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""
    CRITICAL = "critical"  # > 10% variance or major rule violations
    HIGH = "high"         # 5-10% variance or significant rule violations
    MEDIUM = "medium"     # Notable patterns worth reviewing
    LOW = "low"           # Minor variances within acceptable range


@dataclass
class Anomaly:
    """Detected anomaly with details."""
    id: str
    type: AnomalyType
    severity: AnomalySeverity
    account_code: str
    account_name: str
    category: str
    description: str
    current_value: float
    previous_value: Optional[float]
    variance_percent: Optional[float]
    rule_violated: Optional[str]
    recommended_action: str
    period: str


class AnomalyDetector:
    """Comprehensive anomaly detection engine."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.account_mapper = AccountMapper()
        self.logger = logging.getLogger(__name__)
    
    def detect(self, variance_results: List[VarianceResult], 
              correlation_results: List[CorrelationResult],
              financial_data: FinancialData) -> List[Anomaly]:
        """
        Detect anomalies from variance and correlation analysis.
        
        Args:
            variance_results: Results from variance analysis
            correlation_results: Results from correlation analysis
            financial_data: Original financial data
            
        Returns:
            List of detected anomalies
        """
        self.logger.info("Starting anomaly detection")
        
        anomalies = []
        
        # Detect variance-based anomalies
        variance_anomalies = self._detect_variance_anomalies(variance_results)
        anomalies.extend(variance_anomalies)
        
        # Detect correlation violations
        correlation_anomalies = self._detect_correlation_anomalies(correlation_results)
        anomalies.extend(correlation_anomalies)
        
        # Detect sign changes
        sign_change_anomalies = self._detect_sign_changes(variance_results)
        anomalies.extend(sign_change_anomalies)
        
        # Detect recurring account anomalies
        recurring_anomalies = self._detect_recurring_account_anomalies(variance_results)
        anomalies.extend(recurring_anomalies)
        
        # Detect quarterly pattern breaks
        quarterly_anomalies = self._detect_quarterly_pattern_breaks(variance_results, financial_data)
        anomalies.extend(quarterly_anomalies)
        
        # Sort by severity and variance magnitude
        anomalies = self._prioritize_anomalies(anomalies)
        
        self.logger.info(f"Anomaly detection completed: {len(anomalies)} anomalies found")
        
        return anomalies
    
    def _detect_variance_anomalies(self, results: List[VarianceResult]) -> List[Anomaly]:
        """Detect anomalies based on variance thresholds."""
        anomalies = []
        
        for result in results:
            if not result.is_significant:
                continue
            
            # Determine severity based on variance percentage
            if abs(result.variance_percent) >= 20:
                severity = AnomalySeverity.CRITICAL
            elif abs(result.variance_percent) >= 10:
                severity = AnomalySeverity.HIGH
            elif abs(result.variance_percent) >= 5:
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            # Generate description
            direction = "increased" if result.variance_amount > 0 else "decreased"
            description = (f"Account {direction} by {abs(result.variance_percent):.1f}% "
                         f"({result.variance_amount:,.0f})")
            
            # Recommend action based on account type and severity
            action = self._recommend_action_for_variance(result, severity)
            
            anomaly = Anomaly(
                id=f"VAR_{result.account_code}_{result.period_to}",
                type=AnomalyType.VARIANCE_ANOMALY,
                severity=severity,
                account_code=result.account_code,
                account_name=result.account_name,
                category=result.category,
                description=description,
                current_value=result.current_value,
                previous_value=result.previous_value,
                variance_percent=result.variance_percent,
                rule_violated=None,
                recommended_action=action,
                period=result.period_to
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_correlation_anomalies(self, results: List[CorrelationResult]) -> List[Anomaly]:
        """Detect anomalies from correlation rule violations."""
        anomalies = []
        
        for result in results:
            if not result.is_violation:
                continue
            
            # Map severity from correlation result
            if result.severity == 'high':
                severity = AnomalySeverity.HIGH
            elif result.severity == 'medium':
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            # Get account information
            account_info = self.account_mapper.get_account_info(result.primary_account)
            account_name = account_info.name if account_info else result.primary_account
            category = account_info.category if account_info else 'unknown'
            
            anomaly = Anomaly(
                id=f"CORR_{result.rule_id}_{result.primary_account}",
                type=AnomalyType.CORRELATION_VIOLATION,
                severity=severity,
                account_code=result.primary_account,
                account_name=account_name,
                category=category,
                description=f"Rule violation: {result.rule_name}. {result.violation_description}",
                current_value=0.0,  # Not directly applicable
                previous_value=None,
                variance_percent=result.primary_variance,
                rule_violated=result.rule_name,
                recommended_action=self._recommend_action_for_correlation(result),
                period="Current"
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_sign_changes(self, results: List[VarianceResult]) -> List[Anomaly]:
        """Detect accounts with sign changes."""
        anomalies = []
        
        for result in results:
            if not self._has_sign_change(result.current_value, result.previous_value):
                continue
            
            # Sign changes are always significant
            severity = AnomalySeverity.HIGH
            
            # Describe the sign change
            if result.previous_value > 0 and result.current_value < 0:
                description = f"Account changed from positive ({result.previous_value:,.0f}) to negative ({result.current_value:,.0f})"
            elif result.previous_value < 0 and result.current_value > 0:
                description = f"Account changed from negative ({result.previous_value:,.0f}) to positive ({result.current_value:,.0f})"
            elif result.previous_value != 0 and result.current_value == 0:
                description = f"Account changed from {result.previous_value:,.0f} to zero"
            else:
                description = f"Account changed from zero to {result.current_value:,.0f}"
            
            anomaly = Anomaly(
                id=f"SIGN_{result.account_code}_{result.period_to}",
                type=AnomalyType.SIGN_CHANGE,
                severity=severity,
                account_code=result.account_code,
                account_name=result.account_name,
                category=result.category,
                description=description,
                current_value=result.current_value,
                previous_value=result.previous_value,
                variance_percent=result.variance_percent,
                rule_violated=None,
                recommended_action="Investigate the cause of sign change - possible data error or significant business event",
                period=result.period_to
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_recurring_account_anomalies(self, results: List[VarianceResult]) -> List[Anomaly]:
        """Detect anomalies in recurring accounts (should be stable)."""
        anomalies = []
        
        recurring_accounts = self.account_mapper.get_recurring_accounts()
        
        for result in results:
            if result.account_code not in recurring_accounts:
                continue
            
            # Recurring accounts should be stable - lower thresholds
            if abs(result.variance_percent) >= 5:  # 5% threshold for recurring accounts
                
                severity = AnomalySeverity.HIGH if abs(result.variance_percent) >= 10 else AnomalySeverity.MEDIUM
                
                description = (f"Recurring account showed {abs(result.variance_percent):.1f}% variance "
                             f"(expected to be stable)")
                
                anomaly = Anomaly(
                    id=f"RECUR_{result.account_code}_{result.period_to}",
                    type=AnomalyType.RECURRING_ACCOUNT_SPIKE,
                    severity=severity,
                    account_code=result.account_code,
                    account_name=result.account_name,
                    category=result.category,
                    description=description,
                    current_value=result.current_value,
                    previous_value=result.previous_value,
                    variance_percent=result.variance_percent,
                    rule_violated=None,
                    recommended_action=self._recommend_action_for_recurring(result),
                    period=result.period_to
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_quarterly_pattern_breaks(self, results: List[VarianceResult], 
                                       financial_data: FinancialData) -> List[Anomaly]:
        """Detect breaks in expected quarterly patterns."""
        anomalies = []
        
        # Accounts that should follow quarterly patterns
        quarterly_accounts = ['trade_receivables', 'unbilled_revenue', 'unearned_revenue']
        
        for result in results:
            if result.category not in quarterly_accounts:
                continue
            
            # Check if the pattern seems unusual (simplified check)
            if abs(result.variance_percent) > 30:  # Large swings in quarterly accounts
                
                anomaly = Anomaly(
                    id=f"QUART_{result.account_code}_{result.period_to}",
                    type=AnomalyType.QUARTERLY_PATTERN_BREAK,
                    severity=AnomalySeverity.MEDIUM,
                    account_code=result.account_code,
                    account_name=result.account_name,
                    category=result.category,
                    description=f"Quarterly account showed unusual variance of {result.variance_percent:.1f}%",
                    current_value=result.current_value,
                    previous_value=result.previous_value,
                    variance_percent=result.variance_percent,
                    rule_violated=None,
                    recommended_action="Verify quarterly billing timing and collection patterns",
                    period=result.period_to
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
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
    
    def _recommend_action_for_variance(self, result: VarianceResult, severity: AnomalySeverity) -> str:
        """Recommend action for variance anomalies."""
        if severity == AnomalySeverity.CRITICAL:
            return f"URGENT: Investigate {result.account_name} - verify data accuracy and underlying business reasons"
        elif severity == AnomalySeverity.HIGH:
            return f"Review {result.account_name} - check supporting documentation and business events"
        else:
            return f"Monitor {result.account_name} - document explanation for variance"
    
    def _recommend_action_for_correlation(self, result: CorrelationResult) -> str:
        """Recommend action for correlation violations."""
        return f"Review correlation between {result.primary_account} and {result.correlated_account} - verify business logic"
    
    def _recommend_action_for_recurring(self, result: VarianceResult) -> str:
        """Recommend action for recurring account anomalies."""
        if result.category == 'depreciation':
            return "Check for asset additions, disposals, or changes in depreciation method"
        elif result.category == 'revenue':
            return "Verify lease agreements, occupancy changes, or billing timing"
        elif result.category == 'opex':
            return "Review operating expense categories for unusual items or timing differences"
        else:
            return "Investigate the cause of variance in this normally stable account"
    
    def _prioritize_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Sort anomalies by priority (severity and magnitude)."""
        severity_order = {
            AnomalySeverity.CRITICAL: 4,
            AnomalySeverity.HIGH: 3,
            AnomalySeverity.MEDIUM: 2,
            AnomalySeverity.LOW: 1
        }
        
        return sorted(anomalies, key=lambda x: (
            severity_order[x.severity],
            abs(x.variance_percent) if x.variance_percent else 0
        ), reverse=True)
    
    def get_critical_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Get only critical severity anomalies."""
        return [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
    
    def get_anomalies_by_type(self, anomalies: List[Anomaly], anomaly_type: AnomalyType) -> List[Anomaly]:
        """Filter anomalies by type."""
        return [a for a in anomalies if a.type == anomaly_type]