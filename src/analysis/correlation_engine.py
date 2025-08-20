"""
Correlation analysis engine implementing the 13 correlation rules.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from config.settings import Settings
from config.account_mapping import AccountMapper
from data.models import FinancialData
from analysis.variance_analyzer import VarianceResult
from utils.calculations import calculate_variance_percentage, CorrelationCalculator


class RelationshipType(Enum):
    """Types of correlation relationships."""
    POSITIVE = "positive"  # Both should move in same direction
    NEGATIVE = "negative"  # Should move in opposite directions
    QUARTERLY_CYCLE = "quarterly_cycle"  # Follows quarterly billing pattern
    CONDITIONAL = "conditional"  # Relationship depends on conditions


@dataclass
class CorrelationRule:
    """Definition of a correlation rule."""
    id: int
    name: str
    primary_account_category: any  # Can be str or list of str
    correlated_account_category: str
    relationship_type: RelationshipType
    description: str
    enabled: bool = True


@dataclass
class CorrelationResult:
    """Result of correlation rule analysis."""
    rule_id: int
    rule_name: str
    primary_account: str
    correlated_account: str
    primary_variance: float
    correlated_variance: float
    expected_relationship: RelationshipType
    is_violation: bool
    violation_description: str
    severity: str  # 'high', 'medium', 'low'


class CorrelationEngine:
    """Correlation analysis engine for the 13 key correlation rules."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.account_mapper = AccountMapper()
        self.logger = logging.getLogger(__name__)
        self.rules = self._load_rules_from_config()
        self.correlation_calculator = CorrelationCalculator()
    
    def _load_rules_from_config(self) -> List[CorrelationRule]:
        """Load correlation rules from YAML configuration."""
        rules = []
        
        rule_configs = self.settings.get_correlation_rules()
        
        for rule_config in rule_configs:
            # Load all rules (enabled and disabled) but preserve their enabled status
            
            # Map relationship type string to enum
            relationship_mapping = {
                'positive': RelationshipType.POSITIVE,
                'negative': RelationshipType.NEGATIVE,
                'quarterly_cycle': RelationshipType.QUARTERLY_CYCLE,
                'conditional': RelationshipType.CONDITIONAL
            }
            
            relationship_type = relationship_mapping.get(
                rule_config.get('relationship_type', 'positive'),
                RelationshipType.POSITIVE
            )
            
            rule = CorrelationRule(
                id=rule_config['id'],
                name=rule_config['name'],
                primary_account_category=rule_config['primary_account_category'],
                correlated_account_category=rule_config['correlated_account_category'],
                relationship_type=relationship_type,
                description=rule_config.get('description', ''),
                enabled=rule_config.get('enabled', True)
            )
            
            rules.append(rule)
            
        enabled_count = sum(1 for r in rules if r.enabled)
        self.logger.info(f"Loaded {len(rules)} correlation rules from configuration ({enabled_count} enabled)")
        return rules
    
    def analyze(self, financial_data: FinancialData) -> List[CorrelationResult]:
        """
        Analyze correlations based on the 13 rules.
        
        Args:
            financial_data: Financial data to analyze
            
        Returns:
            List of correlation analysis results
        """
        self.logger.info("Starting correlation analysis")
        
        results = []
        
        # Combine balance sheet and income statement data
        combined_data = self._combine_financial_data(financial_data)
        
        for rule in self.rules:
            if rule.enabled:  # Only process enabled rules
                rule_results = self._analyze_rule(rule, combined_data)
                results.extend(rule_results)
        
        self.logger.info(f"Correlation analysis completed: {len(results)} results")
        
        return results
    
    def _combine_financial_data(self, financial_data: FinancialData) -> pd.DataFrame:
        """Combine balance sheet and income statement data."""
        combined = pd.concat([
            financial_data.balance_sheet,
            financial_data.income_statement
        ], ignore_index=True)
        
        return combined
    
    def _analyze_rule(self, rule: CorrelationRule, data: pd.DataFrame) -> List[CorrelationResult]:
        """Analyze a specific correlation rule."""
        results = []
        
        # Get accounts for primary and correlated categories
        # Handle both single category and multiple categories
        if isinstance(rule.primary_account_category, list):
            primary_accounts = []
            for category in rule.primary_account_category:
                primary_accounts.extend(self._get_accounts_by_category(data, category))
        else:
            primary_accounts = self._get_accounts_by_category(data, rule.primary_account_category)
        
        correlated_accounts = self._get_accounts_by_category(data, rule.correlated_account_category)
        
        if not primary_accounts or not correlated_accounts:
            self.logger.debug(f"Rule {rule.id}: Missing accounts for analysis")
            return results
        
        # Calculate variances for each account pair
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) < 2:
            return results
        
        current_period = numeric_cols[-1]
        previous_period = numeric_cols[-2]
        
        for primary_account in primary_accounts:
            for correlated_account in correlated_accounts:
                primary_variance = self._calculate_variance(
                    data, primary_account, current_period, previous_period
                )
                correlated_variance = self._calculate_variance(
                    data, correlated_account, current_period, previous_period
                )
                
                if primary_variance is None or correlated_variance is None:
                    continue
                
                # Check for rule violation
                violation_result = self._check_rule_violation(
                    rule, primary_variance, correlated_variance
                )
                
                if violation_result:
                    result = CorrelationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        primary_account=primary_account,
                        correlated_account=correlated_account,
                        primary_variance=primary_variance,
                        correlated_variance=correlated_variance,
                        expected_relationship=rule.relationship_type,
                        is_violation=True,
                        violation_description=violation_result['description'],
                        severity=violation_result['severity']
                    )
                    results.append(result)
        
        return results
    
    def _get_accounts_by_category(self, data: pd.DataFrame, category: str) -> List[str]:
        """Get account codes matching a category."""
        account_codes = self.account_mapper.get_accounts_by_category(category)
        
        # Handle empty data
        if data.empty or 'account_code' not in data.columns:
            return []
        
        # Filter to only accounts present in data
        present_accounts = []
        for code in account_codes:
            if code in data['account_code'].astype(str).values:
                present_accounts.append(code)
        
        return present_accounts
    
    def _calculate_variance(self, data: pd.DataFrame, account_code: str, 
                          current_period: str, previous_period: str) -> Optional[float]:
        """Calculate variance percentage for an account."""
        account_row = data[data['account_code'].astype(str) == account_code]
        
        if account_row.empty:
            return None
        
        current_value = account_row[current_period].iloc[0] if pd.notna(account_row[current_period].iloc[0]) else 0.0
        previous_value = account_row[previous_period].iloc[0] if pd.notna(account_row[previous_period].iloc[0]) else 0.0
        
        # Use centralized calculation
        return calculate_variance_percentage(current_value, previous_value)
    
    def _check_rule_violation(self, rule: CorrelationRule, 
                            primary_variance: float, correlated_variance: float) -> Optional[Dict]:
        """Check if a correlation rule is violated."""
        
        if rule.relationship_type == RelationshipType.POSITIVE:
            return self._check_positive_relationship(rule, primary_variance, correlated_variance)
        
        elif rule.relationship_type == RelationshipType.NEGATIVE:
            return self._check_negative_relationship(rule, primary_variance, correlated_variance)
        
        elif rule.relationship_type == RelationshipType.QUARTERLY_CYCLE:
            return self._check_quarterly_cycle(rule, primary_variance, correlated_variance)
        
        elif rule.relationship_type == RelationshipType.CONDITIONAL:
            return self._check_conditional_relationship(rule, primary_variance, correlated_variance)
        
        return None
    
    def _check_positive_relationship(self, rule: CorrelationRule, 
                                   primary_var: float, correlated_var: float) -> Optional[Dict]:
        """Check positive correlation rule."""
        threshold = self.settings.get_correlation_threshold()  # Get threshold from config
        
        # Primary increased significantly but correlated didn't
        if primary_var > threshold and abs(correlated_var) < threshold:
            return {
                'description': f"Primary account increased {primary_var:.1f}% but correlated account changed only {correlated_var:.1f}%",
                'severity': 'high' if primary_var > 10 else 'medium'
            }
        
        # Primary decreased significantly but correlated didn't
        if primary_var < -threshold and abs(correlated_var) < threshold:
            return {
                'description': f"Primary account decreased {abs(primary_var):.1f}% but correlated account changed only {correlated_var:.1f}%",
                'severity': 'high' if abs(primary_var) > 10 else 'medium'
            }
        
        # Opposite directions
        if primary_var > threshold and correlated_var < -threshold:
            return {
                'description': f"Primary account increased {primary_var:.1f}% but correlated account decreased {abs(correlated_var):.1f}%",
                'severity': 'high'
            }
        
        if primary_var < -threshold and correlated_var > threshold:
            return {
                'description': f"Primary account decreased {abs(primary_var):.1f}% but correlated account increased {correlated_var:.1f}%",
                'severity': 'high'
            }
        
        return None
    
    def _check_negative_relationship(self, rule: CorrelationRule, 
                                   primary_var: float, correlated_var: float) -> Optional[Dict]:
        """Check negative correlation rule."""
        threshold = self.settings.get_correlation_threshold()
        
        # Same direction movements
        if primary_var > threshold and correlated_var > threshold:
            return {
                'description': f"Both accounts increased ({primary_var:.1f}%, {correlated_var:.1f}%) but should move oppositely",
                'severity': 'high'
            }
        
        if primary_var < -threshold and correlated_var < -threshold:
            return {
                'description': f"Both accounts decreased ({abs(primary_var):.1f}%, {abs(correlated_var):.1f}%) but should move oppositely",
                'severity': 'high'
            }
        
        return None
    
    def _check_quarterly_cycle(self, rule: CorrelationRule, 
                             primary_var: float, correlated_var: float) -> Optional[Dict]:
        """Check quarterly cycle patterns."""
        # This would require period information to determine quarter timing
        # For now, check if there are unusual patterns
        
        if abs(primary_var) > 20:  # Large movements in cyclical accounts
            return {
                'description': f"Large variance ({primary_var:.1f}%) in cyclical account - verify quarter timing",
                'severity': 'medium'
            }
        
        return None
    
    def _check_conditional_relationship(self, rule: CorrelationRule, 
                                      primary_var: float, correlated_var: float) -> Optional[Dict]:
        """Check conditional relationships (like FX)."""
        # If there's volatility in primary but no movement in correlated
        if abs(primary_var) > 10 and abs(correlated_var) < 2:
            return {
                'description': f"High volatility in primary ({primary_var:.1f}%) but minimal correlated response ({correlated_var:.1f}%)",
                'severity': 'medium'
            }
        
        return None
    
    def get_violations_by_severity(self, results: List[CorrelationResult], 
                                 severity: str) -> List[CorrelationResult]:
        """Filter correlation results by severity."""
        return [r for r in results if r.is_violation and r.severity == severity]
    
    def get_rule_violations(self, results: List[CorrelationResult], 
                          rule_id: int) -> List[CorrelationResult]:
        """Get violations for a specific rule."""
        return [r for r in results if r.rule_id == rule_id and r.is_violation]