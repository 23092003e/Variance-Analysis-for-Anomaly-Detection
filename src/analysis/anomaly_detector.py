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
from data.models import FinancialData
from analysis.variance_analyzer import VarianceResult
from analysis.correlation_engine import CorrelationResult
from analysis.rule_violations import (
    get_rule_violation, get_variance_rule_for_category, 
    get_correlation_rule_id, get_materiality_rule_for_threshold
)
from utils.calculations import has_sign_change


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
    rule_violated: Optional[str]  # Kept for backward compatibility
    recommended_action: str
    period: str
    logic_trigger: Optional[str] = None  # Explanation of why anomaly was flagged
    rule_violation_id: Optional[str] = None  # Unique rule ID (e.g., "VT002", "CR001")
    rule_violation_name: Optional[str] = None  # Rule name for display
    rule_violation_description: Optional[str] = None  # Brief rule description  # Explanation of why anomaly was flagged


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
            
            # Determine severity based on BOTH percentage AND absolute amount thresholds (AND logic)
            severity_thresholds = self.settings.get_severity_thresholds()
            abs_amount = abs(result.variance_amount)
            abs_percent = abs(result.variance_percent)
            
            # Critical: variance ≥ 20% AND absolute amount ≥ 1,000,000
            if (abs_percent >= severity_thresholds['critical']['variance_threshold'] and 
                abs_amount >= severity_thresholds['critical']['absolute_threshold']):
                severity = AnomalySeverity.CRITICAL
            # High: variance ≥ 10% AND absolute amount ≥ 500,000    
            elif (abs_percent >= severity_thresholds['high']['variance_threshold'] and 
                  abs_amount >= severity_thresholds['high']['absolute_threshold']):
                severity = AnomalySeverity.HIGH
            # Medium: variance ≥ 5% AND absolute amount ≥ 100,000
            elif (abs_percent >= severity_thresholds['medium']['variance_threshold'] and 
                  abs_amount >= severity_thresholds['medium']['absolute_threshold']):
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW
            
            # Get rule violation information
            rule_id = get_variance_rule_for_category(result.category)
            rule_violation = get_rule_violation(rule_id)
            
            # Check for materiality-specific rules
            materiality_config = self.settings.account_mappings.get("materiality_thresholds", {})
            account_has_specific_materiality = any(
                result.account_code in config.get("accounts", [])
                for config in materiality_config.values()
            )
            
            if account_has_specific_materiality:
                materiality_threshold = self.settings.get_materiality_threshold(result.account_code)
                materiality_rule_id = get_materiality_rule_for_threshold(materiality_threshold)
                materiality_rule = get_rule_violation(materiality_rule_id)
                if materiality_rule:
                    rule_violation = materiality_rule
                    rule_id = materiality_rule_id
            
            # Generate description
            direction = "increased" if result.variance_amount > 0 else "decreased"
            description = (f"Account {direction} by {abs_percent:.1f}% "
                         f"({result.variance_amount:,.0f})")
            
            # Determine suggested reason based on anomaly characteristics
            suggested_reason = self._get_suggested_reason(result)
            
            # Generate logic trigger explanation
            logic_trigger = self._get_logic_trigger(result, severity, abs_percent, abs_amount, severity_thresholds)
            
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
                rule_violated=rule_violation.rule_name if rule_violation else "Variance Threshold",
                recommended_action=suggested_reason,
                period=result.period_to,
                logic_trigger=logic_trigger,
                rule_violation_id=rule_id,
                rule_violation_name=rule_violation.rule_name if rule_violation else "Variance Threshold",
                rule_violation_description=rule_violation.description if rule_violation else "Account variance exceeds threshold"
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
            
            # Get correlation rule violation information
            correlation_rule_id = get_correlation_rule_id(result.rule_id)
            rule_violation = get_rule_violation(correlation_rule_id)
            
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
                recommended_action="Operational changes or accounting adjustments",
                period="Current",
                logic_trigger=f"Correlation rule violation: {result.rule_name}",
                rule_violation_id=correlation_rule_id,
                rule_violation_name=rule_violation.rule_name if rule_violation else result.rule_name,
                rule_violation_description=rule_violation.description if rule_violation else result.violation_description
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_sign_changes(self, results: List[VarianceResult]) -> List[Anomaly]:
        """Detect accounts with sign changes."""
        anomalies = []
        
        for result in results:
            if not has_sign_change(result.current_value, result.previous_value):
                continue
            
            # Sign changes are always significant
            severity = AnomalySeverity.HIGH
            
            # Determine which sign change rule applies
            if result.previous_value != 0 and result.current_value == 0:
                rule_id = "SC002"  # Zero balance change
            elif result.previous_value == 0 and result.current_value != 0:
                rule_id = "SC002"  # Zero balance change
            else:
                rule_id = "SC001"  # Sign change
            
            rule_violation = get_rule_violation(rule_id)
            
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
                rule_violated=rule_violation.rule_name if rule_violation else "Sign Change Detection",
                recommended_action="Account sign change - verify data accuracy and business events",
                period=result.period_to,
                logic_trigger="Sign change detected",
                rule_violation_id=rule_id,
                rule_violation_name=rule_violation.rule_name if rule_violation else "Sign Change Detection",
                rule_violation_description=rule_violation.description if rule_violation else "Account sign changed unexpectedly"
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_recurring_account_anomalies(self, results: List[VarianceResult]) -> List[Anomaly]:
        """Detect anomalies in recurring accounts (should be stable)."""
        anomalies = []
        
        recurring_accounts = self.settings.get_recurring_account_codes()
        
        for result in results:
            if result.account_code not in recurring_accounts:
                continue
            
            # Get recurring account threshold from config (±5% as defined)
            recurring_threshold = self.settings.get_variance_threshold('recurring')
            if abs(result.variance_percent) >= recurring_threshold:
                
                # Use configured thresholds for severity
                severity_thresholds = self.settings.get_severity_thresholds()
                abs_amount = abs(result.variance_amount)
                abs_percent = abs(result.variance_percent)
                
                # Apply AND logic for severity classification
                if (abs_percent >= severity_thresholds['critical']['variance_threshold'] and 
                    abs_amount >= severity_thresholds['critical']['absolute_threshold']):
                    severity = AnomalySeverity.CRITICAL
                elif (abs_percent >= severity_thresholds['high']['variance_threshold'] and 
                      abs_amount >= severity_thresholds['high']['absolute_threshold']):
                    severity = AnomalySeverity.HIGH
                elif (abs_percent >= severity_thresholds['medium']['variance_threshold'] and 
                      abs_amount >= severity_thresholds['medium']['absolute_threshold']):
                    severity = AnomalySeverity.MEDIUM
                else:
                    severity = AnomalySeverity.LOW
                
                # Get recurring account rule violation information
                rule_id = "RA001"
                rule_violation = get_rule_violation(rule_id)
                
                description = (f"Recurring account showed {abs_percent:.1f}% variance "
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
                    rule_violated=rule_violation.rule_name if rule_violation else "Recurring Account Stability",
                    recommended_action="Operational changes or accounting adjustments",
                    period=result.period_to,
                    logic_trigger=f"Recurring account exceeds {recurring_threshold}% stability threshold ({abs_percent:.1f}%)",
                    rule_violation_id=rule_id,
                    rule_violation_name=rule_violation.rule_name if rule_violation else "Recurring Account Stability",
                    rule_violation_description=rule_violation.description if rule_violation else "Recurring account exceeded stability threshold"
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_quarterly_pattern_breaks(self, results: List[VarianceResult], 
                                       financial_data: FinancialData) -> List[Anomaly]:
        """Detect breaks in expected quarterly patterns."""
        anomalies = []
        
        # Get cyclical accounts from configuration
        cyclical_accounts = self.settings.get_cyclical_account_codes()
        
        for result in results:
            if result.account_code not in cyclical_accounts:
                continue
            
            # Get quarterly pattern threshold from config
            quarterly_config = self.settings.thresholds.get('quarterly_patterns', {})
            pattern_threshold = quarterly_config.get(result.category, {}).get('end_quarter_peak', 30.0)
            
            if abs(result.variance_percent) > pattern_threshold:
                
                # Apply consistent severity classification
                severity_thresholds = self.settings.get_severity_thresholds()
                abs_amount = abs(result.variance_amount)
                abs_percent = abs(result.variance_percent)
                
                if (abs_percent >= severity_thresholds['critical']['variance_threshold'] and 
                    abs_amount >= severity_thresholds['critical']['absolute_threshold']):
                    severity = AnomalySeverity.CRITICAL
                elif (abs_percent >= severity_thresholds['high']['variance_threshold'] and 
                      abs_amount >= severity_thresholds['high']['absolute_threshold']):
                    severity = AnomalySeverity.HIGH
                elif (abs_percent >= severity_thresholds['medium']['variance_threshold'] and 
                      abs_amount >= severity_thresholds['medium']['absolute_threshold']):
                    severity = AnomalySeverity.MEDIUM
                else:
                    severity = AnomalySeverity.LOW
                
                # Determine specific quarterly rule based on account category
                if result.category in ['trade_receivables']:
                    rule_id = "QP001"  # Quarterly billing cycle
                else:
                    rule_id = "QP002"  # General cyclical pattern
                
                rule_violation = get_rule_violation(rule_id)
                
                anomaly = Anomaly(
                    id=f"QUART_{result.account_code}_{result.period_to}",
                    type=AnomalyType.QUARTERLY_PATTERN_BREAK,
                    severity=severity,
                    account_code=result.account_code,
                    account_name=result.account_name,
                    category=result.category,
                    description=f"Quarterly account showed unusual variance of {abs_percent:.1f}%",
                    current_value=result.current_value,
                    previous_value=result.previous_value,
                    variance_percent=result.variance_percent,
                    rule_violated=rule_violation.rule_name if rule_violation else "Quarterly Pattern Check",
                    recommended_action="Deviation from expected quarterly pattern - check billing cycles",
                    period=result.period_to,
                    logic_trigger=f"Cyclical account exceeds quarterly pattern threshold ({abs_percent:.1f}% > {pattern_threshold}%)",
                    rule_violation_id=rule_id,
                    rule_violation_name=rule_violation.rule_name if rule_violation else "Quarterly Pattern Check",
                    rule_violation_description=rule_violation.description if rule_violation else "Account deviated from expected quarterly pattern"
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    # Removed _has_sign_change method - now using centralized function from utils.calculations
    
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

    
    def _get_suggested_reason(self, result: VarianceResult) -> str:
        """Get suggested reason based on anomaly characteristics."""
        from utils.calculations import has_sign_change
        
        # Check for sign change first
        if has_sign_change(result.current_value, result.previous_value):
            return "Account sign change - verify data accuracy and business events"
        
        # Check if it's a cyclical account
        cyclical_accounts = self.settings.get_cyclical_account_codes()
        if result.account_code in cyclical_accounts:
            return "Deviation from expected quarterly pattern - check billing cycles"
        
        # General variance reason
        return "Operational changes or accounting adjustments"
    
    def _get_logic_trigger(self, result: VarianceResult, severity: AnomalySeverity, 
                          abs_percent: float, abs_amount: float, severity_thresholds: dict) -> str:
        """Generate logic trigger explanation for why anomaly was flagged."""
        from utils.calculations import has_sign_change
        
        # Check for sign change
        if has_sign_change(result.current_value, result.previous_value):
            return "Sign change detected"
        
        # Check specific account thresholds
        account_threshold = self.settings.get_variance_threshold(result.category)
        if abs_percent >= account_threshold:
            trigger_parts = []
            
            # Add threshold trigger
            if result.category in ['opex', 'staff_costs', 'other_expenses']:  # G&A accounts
                trigger_parts.append(f"G&A account exceeds 10% threshold ({abs_percent:.1f}%)")
            elif result.category == 'borrowings':
                trigger_parts.append(f"Borrowings exceeds 2% threshold ({abs_percent:.1f}%)")
            elif result.category in ['depreciation']:
                trigger_parts.append(f"Recurring account exceeds 5% threshold ({abs_percent:.1f}%)")
            else:
                trigger_parts.append(f"Exceeds {account_threshold}% threshold ({abs_percent:.1f}%)")
            
            # Add severity classification
            if severity != AnomalySeverity.LOW:
                sev_config = severity_thresholds[severity.value.lower()]
                trigger_parts.append(f"Meets {severity.value.lower()} criteria: ≥{sev_config['variance_threshold']}% and ≥{sev_config['absolute_threshold']:,}")
            
            return " + ".join(trigger_parts)
        
        return f"Variance threshold exceeded ({abs_percent:.1f}%)"
    
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