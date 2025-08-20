"""
Rule violation definitions for variance analysis anomaly detection.

This module defines all rule types, IDs, and descriptions to provide clear
traceability for why each anomaly was flagged.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RuleCategory(Enum):
    """Categories of rule violations."""
    VARIANCE_THRESHOLD = "variance_threshold"
    CORRELATION_VIOLATION = "correlation_violation"
    SIGN_CHANGE = "sign_change"
    RECURRING_ACCOUNT = "recurring_account"
    QUARTERLY_PATTERN = "quarterly_pattern"
    MATERIALITY = "materiality"


@dataclass
class RuleViolation:
    """Details of a rule violation."""
    rule_id: str
    rule_name: str
    category: RuleCategory
    description: str
    threshold_value: Optional[float] = None
    severity_impact: Optional[str] = None


# Variance Threshold Rules
VARIANCE_RULES = {
    "VT001": RuleViolation(
        rule_id="VT001",
        rule_name="General Variance Threshold",
        category=RuleCategory.VARIANCE_THRESHOLD,
        description="Account variance exceeds default 5% threshold",
        threshold_value=5.0
    ),
    "VT002": RuleViolation(
        rule_id="VT002",
        rule_name="G&A Account Variance Threshold",
        category=RuleCategory.VARIANCE_THRESHOLD,
        description="General & Administrative account variance exceeds 10% threshold",
        threshold_value=10.0
    ),
    "VT003": RuleViolation(
        rule_id="VT003",
        rule_name="Borrowings Strict Threshold",
        category=RuleCategory.VARIANCE_THRESHOLD,
        description="Borrowings account variance exceeds strict 2% threshold",
        threshold_value=2.0,
        severity_impact="High materiality due to financial impact"
    ),
    "VT004": RuleViolation(
        rule_id="VT004",
        rule_name="Recurring Account Stability Threshold",
        category=RuleCategory.VARIANCE_THRESHOLD,
        description="Recurring account variance exceeds 5% stability threshold",
        threshold_value=5.0,
        severity_impact="Expected to be stable period-over-period"
    ),
    "VT005": RuleViolation(
        rule_id="VT005",
        rule_name="Depreciation Stability Threshold",
        category=RuleCategory.VARIANCE_THRESHOLD,
        description="Depreciation account variance exceeds 5% stability threshold",
        threshold_value=5.0,
        severity_impact="Should be predictable based on asset base"
    ),
}

# Sign Change Rules
SIGN_CHANGE_RULES = {
    "SC001": RuleViolation(
        rule_id="SC001",
        rule_name="Account Sign Change Detection",
        category=RuleCategory.SIGN_CHANGE,
        description="Account changed from positive to negative or vice versa",
        severity_impact="Indicates potential data error or significant business event"
    ),
    "SC002": RuleViolation(
        rule_id="SC002",
        rule_name="Zero Balance Change Detection",
        category=RuleCategory.SIGN_CHANGE,
        description="Account changed from zero to non-zero or vice versa",
        severity_impact="May indicate account activation/deactivation"
    ),
}

# Recurring Account Rules
RECURRING_RULES = {
    "RA001": RuleViolation(
        rule_id="RA001",
        rule_name="Recurring Account Anomaly",
        category=RuleCategory.RECURRING_ACCOUNT,
        description="Unusual variance in normally stable recurring account",
        severity_impact="Requires investigation for operational changes"
    ),
}

# Quarterly Pattern Rules
QUARTERLY_RULES = {
    "QP001": RuleViolation(
        rule_id="QP001",
        rule_name="Quarterly Billing Cycle Deviation",
        category=RuleCategory.QUARTERLY_PATTERN,
        description="Deviation from expected quarterly billing pattern",
        severity_impact="May affect revenue recognition timing"
    ),
    "QP002": RuleViolation(
        rule_id="QP002",
        rule_name="Cyclical Account Pattern Break",
        category=RuleCategory.QUARTERLY_PATTERN,
        description="Break in expected cyclical account behavior",
        severity_impact="Check billing cycles and collection patterns"
    ),
}

# Materiality Rules
MATERIALITY_RULES = {
    "MT001": RuleViolation(
        rule_id="MT001",
        rule_name="High Materiality Account Variance",
        category=RuleCategory.MATERIALITY,
        description="High materiality account exceeds specific variance threshold",
        severity_impact="Significant financial statement impact"
    ),
    "MT002": RuleViolation(
        rule_id="MT002",
        rule_name="Medium Materiality Account Variance",
        category=RuleCategory.MATERIALITY,
        description="Medium materiality account exceeds variance threshold",
        severity_impact="Moderate financial statement impact"
    ),
    "MT003": RuleViolation(
        rule_id="MT003",
        rule_name="Low Materiality Account Variance",
        category=RuleCategory.MATERIALITY,
        description="Low materiality account exceeds variance threshold",
        severity_impact="Limited financial statement impact"
    ),
}

# Correlation Rules (CR001-CR013 match the 13 correlation rules in config)
CORRELATION_RULES = {
    "CR001": RuleViolation(
        rule_id="CR001",
        rule_name="Investment Properties vs Depreciation Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Investment Properties and Depreciation should move together",
        severity_impact="Asset base changes should reflect in depreciation"
    ),
    "CR002": RuleViolation(
        rule_id="CR002",
        rule_name="Loan Balance vs Interest Expenses Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Loan principal and interest costs should correlate",
        severity_impact="Debt changes should reflect in interest expense"
    ),
    "CR003": RuleViolation(
        rule_id="CR003",
        rule_name="Cash Deposits vs Bank Interest Income Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Cash deposits and interest income should correlate",
        severity_impact="Cash levels should generate proportional interest"
    ),
    "CR004": RuleViolation(
        rule_id="CR004",
        rule_name="Trade Receivables Quarterly Billing Cycle",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Trade receivables should follow quarterly billing patterns",
        severity_impact="Billing cycle timing affects receivables levels"
    ),
    "CR005": RuleViolation(
        rule_id="CR005",
        rule_name="Unbilled Revenue Quarterly Recognition Pattern",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Unbilled revenue should follow quarterly recognition patterns",
        severity_impact="Revenue recognition timing and advance collections"
    ),
    "CR006": RuleViolation(
        rule_id="CR006",
        rule_name="Unearned Revenue vs Advance Collection Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Unearned revenue should correlate with advance collections",
        severity_impact="Advance payments affect unearned revenue levels"
    ),
    "CR007": RuleViolation(
        rule_id="CR007",
        rule_name="Capital Expenditure vs VAT Deductible Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Capital expenditures should correlate with VAT deductible",
        severity_impact="CapEx activities generate deductible VAT"
    ),
    "CR008": RuleViolation(
        rule_id="CR008",
        rule_name="Occupancy Rate vs Revenue Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Occupancy rates should correlate with rental revenue",
        severity_impact="Occupancy changes directly affect revenue"
    ),
    "CR009": RuleViolation(
        rule_id="CR009",
        rule_name="Maintenance Expenses vs OPEX Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Maintenance expenses should correlate with operating expenses",
        severity_impact="Maintenance activities drive OPEX fluctuations"
    ),
    "CR010": RuleViolation(
        rule_id="CR010",
        rule_name="Asset Disposal vs Depreciation Negative Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Asset disposals should reduce depreciation base",
        severity_impact="Asset sales should decrease future depreciation"
    ),
    "CR011": RuleViolation(
        rule_id="CR011",
        rule_name="New Lease Contracts vs Revenue Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="New leases should correlate with revenue increases",
        severity_impact="New tenants should increase rental income"
    ),
    "CR012": RuleViolation(
        rule_id="CR012",
        rule_name="Lease Termination vs Revenue Negative Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="Lease terminations should correlate with revenue decreases",
        severity_impact="Tenant departures should reduce rental income"
    ),
    "CR013": RuleViolation(
        rule_id="CR013",
        rule_name="FX Rate vs FX Gain/Loss Correlation",
        category=RuleCategory.CORRELATION_VIOLATION,
        description="FX rate changes should correlate with FX gain/loss",
        severity_impact="Currency fluctuations affect FX-related accounts"
    ),
}

# Combined rule dictionary for easy lookup
ALL_RULES = {
    **VARIANCE_RULES,
    **SIGN_CHANGE_RULES,
    **RECURRING_RULES,
    **QUARTERLY_RULES,
    **MATERIALITY_RULES,
    **CORRELATION_RULES,
}


def get_rule_violation(rule_id: str) -> Optional[RuleViolation]:
    """Get rule violation details by ID."""
    return ALL_RULES.get(rule_id)


def get_variance_rule_for_category(category: str) -> str:
    """Get appropriate variance rule ID for account category."""
    if category in ['opex', 'staff_costs', 'other_expenses']:
        return "VT002"  # G&A threshold
    elif category == 'borrowings':
        return "VT003"  # Strict borrowings threshold
    elif category == 'depreciation':
        return "VT005"  # Depreciation stability
    else:
        return "VT001"  # General threshold


def get_correlation_rule_id(correlation_rule_id: int) -> str:
    """Convert correlation rule ID to standardized format."""
    return f"CR{correlation_rule_id:03d}"


def get_materiality_rule_for_threshold(threshold: float) -> str:
    """Get materiality rule based on threshold level."""
    if threshold <= 3.0:
        return "MT001"  # High materiality
    elif threshold <= 5.0:
        return "MT002"  # Medium materiality
    else:
        return "MT003"  # Low materiality