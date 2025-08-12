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
from data.loader import FinancialData
from analysis.variance_analyzer import VarianceResult


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
    primary_account_category: str
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
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[CorrelationRule]:
        """Initialize the 13 correlation rules."""
        return [
            CorrelationRule(
                id=1,
                name="Investment Properties vs Depreciation",
                primary_account_category="investment_properties",
                correlated_account_category="depreciation",
                relationship_type=RelationshipType.POSITIVE,
                description="As Investment Properties increase, Depreciation should increase proportionally"
            ),
            CorrelationRule(
                id=2,
                name="Loan Balance vs Interest Expenses",
                primary_account_category="borrowings",
                correlated_account_category="interest_expense",
                relationship_type=RelationshipType.POSITIVE,
                description="Higher loan balance should lead to higher interest costs"
            ),
            CorrelationRule(
                id=3,
                name="Cash Deposits vs Bank Interest Income",
                primary_account_category="cash_deposits",
                correlated_account_category="interest_income",
                relationship_type=RelationshipType.POSITIVE,
                description="More cash in bank should earn more interest income"
            ),
            CorrelationRule(
                id=4,
                name="Trade Receivables vs Quarterly Billing",
                primary_account_category="trade_receivables",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.QUARTERLY_CYCLE,
                description="Receivables spike at start of quarter due to quarterly billing"
            ),
            CorrelationRule(
                id=5,
                name="Unbilled Revenue vs Quarter Timing",
                primary_account_category="unbilled_revenue",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.QUARTERLY_CYCLE,
                description="Unbilled revenue peaks at quarter-end due to straight-lining"
            ),
            CorrelationRule(
                id=6,
                name="Unearned Revenue vs Advance Collection",
                primary_account_category="unearned_revenue",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.QUARTERLY_CYCLE,
                description="Unearned revenue increases at start of quarter from advance collection"
            ),
            CorrelationRule(
                id=7,
                name="Construction in Progress + IP vs VAT Deductible",
                primary_account_category="investment_properties",
                correlated_account_category="vat_deductible",
                relationship_type=RelationshipType.POSITIVE,
                description="Capital expenditures increase deductible VAT"
            ),
            CorrelationRule(
                id=8,
                name="Occupancy Rate vs Revenue",
                primary_account_category="occupancy_rate",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.POSITIVE,
                description="Higher occupancy should lead to more rental income"
            ),
            CorrelationRule(
                id=9,
                name="Maintenance Expenses vs OPEX",
                primary_account_category="maintenance_expense",
                correlated_account_category="opex",
                relationship_type=RelationshipType.POSITIVE,
                description="Maintenance spikes drive up operating expenses"
            ),
            CorrelationRule(
                id=10,
                name="Asset Disposal vs Depreciation",
                primary_account_category="asset_disposal",
                correlated_account_category="depreciation",
                relationship_type=RelationshipType.NEGATIVE,
                description="Disposal of assets should reduce depreciation base"
            ),
            CorrelationRule(
                id=11,
                name="New Lease Contracts vs Revenue",
                primary_account_category="new_leases",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.POSITIVE,
                description="New tenants should increase rental income"
            ),
            CorrelationRule(
                id=12,
                name="Lease Termination vs Revenue",
                primary_account_category="lease_termination",
                correlated_account_category="revenue",
                relationship_type=RelationshipType.NEGATIVE,
                description="Terminations should reduce rental income"
            ),
            CorrelationRule(
                id=13,
                name="FX Rate Changes vs FX Gain/Loss",
                primary_account_category="fx_volatility",
                correlated_account_category="fx_gain_loss",
                relationship_type=RelationshipType.CONDITIONAL,
                description="Currency fluctuations should reflect in FX gains/losses"
            )
        ]
    
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
            if not rule.enabled:
                continue
                
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
        
        if previous_value != 0:
            return ((current_value - previous_value) / abs(previous_value)) * 100
        else:
            return 100.0 if current_value != 0 else 0.0
    
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
        threshold = 5.0  # 5% threshold for significance
        
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
        threshold = 5.0
        
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