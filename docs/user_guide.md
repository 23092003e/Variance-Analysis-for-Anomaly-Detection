# Variance Analysis for Anomaly Detection - User Guide

## Overview

The Variance Analysis for Anomaly Detection system automatically analyzes financial statements to identify unusual patterns and potential anomalies in financial data. It combines variance analysis with correlation rule validation to provide comprehensive anomaly detection for management review.

## Key Features

- **Automated Variance Analysis**: Period-over-period comparison with configurable thresholds
- **13 Correlation Rules**: Built-in financial logic validation rules
- **Anomaly Classification**: Severity-based classification (Critical, High, Medium, Low)
- **Excel Integration**: Direct Excel file processing with formatted output
- **Configurable Thresholds**: Customizable variance and correlation thresholds
- **Comprehensive Reporting**: Multiple output sheets with conditional formatting

## Quick Start

### Installation

1. Clone or download the project
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Basic Usage

#### Command Line Interface

```bash
# Process a single file
python src/main.py -i data/raw/financial_data.xlsx -o data/output/analysis_report.xlsx

# Use default paths
python src/main.py
```

#### Batch Processing

```bash
# Process all Excel files in a directory
python scripts/run_analysis.py -d data/raw/

# Process with custom output directory
python scripts/run_analysis.py -d data/raw/ -o data/output/

# Process specific file pattern
python scripts/run_analysis.py -d data/raw/ --pattern "DAL_*.xlsx"
```

## Input Data Requirements

### Excel File Structure

The system expects Excel files with the following structure:

#### Balance Sheet Data
- **Required Columns**: Account Code, Account Name, Period columns (e.g., Mar_2025, Apr_2025)
- **Sheet Names**: Should contain "Balance", "BS", or "Bảng cân đối" (Vietnamese)
- **Account Codes**: Numeric codes following Vietnamese chart of accounts

#### Income Statement Data
- **Required Columns**: Account Code, Account Name, Period columns
- **Sheet Names**: Should contain "Income", "IS", "P&L", or "Kết quả" (Vietnamese)
- **Account Codes**: Numeric codes following Vietnamese chart of accounts

### Supported Account Categories

#### Balance Sheet Accounts
- **Investment Properties**: 217000001, 217000006, etc.
- **Cash Deposits**: 112227001, 112227002, etc.
- **Trade Receivables**: 131100001
- **Borrowings**: 341160000, 341160001, etc.
- **Unearned Revenue**: 213100001

#### Income Statement Accounts
- **Revenue**: 511100001, 511100002
- **Depreciation**: 632100001, 632100002
- **Interest Expense**: 635000005, 635000006
- **Interest Income**: 515100001
- **Operating Expenses**: 622000001, 622000002

## Analysis Process

### 1. Data Loading and Validation
- Loads Excel file and identifies Balance Sheet/Income Statement data
- Validates data structure and completeness
- Checks balance sheet equation (Assets = Liabilities + Equity)

### 2. Variance Analysis
- Calculates period-over-period variance for all accounts
- Identifies significant variances based on configurable thresholds
- Detects sign changes (positive to negative or vice versa)

### 3. Correlation Rule Analysis
The system applies 13 key correlation rules:

1. **Investment Properties ↔ Depreciation**: Asset increases should correlate with depreciation increases
2. **Loan Balance ↔ Interest Expense**: Higher loans should increase interest costs
3. **Cash Deposits ↔ Interest Income**: More cash should generate more interest income
4. **Trade Receivables ↔ Quarterly Cycle**: Receivables spike at quarter start
5. **Unbilled Revenue ↔ Quarter Timing**: Peaks at quarter-end
6. **Unearned Revenue ↔ Advance Collection**: Increases at quarter start
7. **Investment Properties ↔ VAT Deductible**: Capital spending increases VAT deductions
8. **Occupancy Rate ↔ Revenue**: Higher occupancy increases rental income
9. **Maintenance Expenses ↔ OPEX**: Maintenance spikes affect operating expenses
10. **Asset Disposal ↔ Depreciation**: Disposals reduce depreciation
11. **New Leases ↔ Revenue**: New tenants increase income
12. **Lease Termination ↔ Revenue**: Terminations reduce income
13. **FX Rate Changes ↔ FX Gain/Loss**: Currency fluctuations create FX impacts

### 4. Anomaly Detection
- Combines variance and correlation analysis results
- Classifies anomalies by severity:
  - **Critical**: >20% variance or major rule violations
  - **High**: 10-20% variance or significant violations
  - **Medium**: 5-10% variance or notable patterns
  - **Low**: <5% variance but worth reviewing

### 5. Report Generation
Creates comprehensive Excel report with multiple sheets:
- **Anomalies Summary**: Main findings for management review
- **Variance Analysis**: Detailed variance calculations
- **Correlation Violations**: Rule violation details
- **Dashboard**: High-level summary statistics
- **Original Data**: Reference sheets with source data

## Configuration

### Threshold Configuration (`config/thresholds.yaml`)

```yaml
# General thresholds
variance_threshold: 5.0        # Default significance threshold
critical_threshold: 10.0       # Critical anomaly threshold

# Account-specific thresholds
recurring_accounts:
  depreciation: 5.0            # Lower tolerance for stable accounts
  revenue: 5.0
  opex: 5.0
```

### Account Mapping Configuration (`config/account_mappings.yaml`)

```yaml
balance_sheet:
  investment_properties:
    - "217000001"              # Land Use Rights
    - "217000006"              # Office Building
  cash_deposits:
    - "112227001"              # USD Account
    - "112227002"              # USD Account 2
```

### Rules Configuration (`config/rules_config.yaml`)

```yaml
correlation_rules:
  - id: 1
    name: "Investment Properties vs Depreciation"
    primary_account_category: "investment_properties"
    correlated_account_category: "depreciation"
    relationship_type: "positive"
    enabled: true
```

## Output Report Structure

### Anomalies Summary Sheet
The main output sheet contains:
- **Severity**: Critical/High/Medium/Low classification
- **Type**: Variance/Correlation/Sign Change/Recurring/Quarterly
- **Account Information**: Code, name, category
- **Description**: Detailed explanation of the anomaly
- **Values**: Current/previous values and variance percentage
- **Recommended Action**: Suggested follow-up steps

### Conditional Formatting
- **Red**: Critical anomalies requiring immediate attention
- **Orange**: High priority anomalies for review
- **Yellow**: Medium priority items worth investigating
- **Green**: Low priority or normal variances

## Best Practices

### Data Preparation
1. Ensure consistent account coding across periods
2. Verify balance sheet equation balances
3. Include at least 2-3 periods for meaningful variance analysis
4. Use consistent period naming (e.g., Mar_2025, Apr_2025)

### Analysis Workflow
1. **Initial Review**: Start with Anomalies Summary sheet
2. **Priority Focus**: Address Critical and High severity items first
3. **Root Cause Analysis**: Use variance details to understand changes
4. **Documentation**: Record explanations for significant variances
5. **Follow-up**: Track resolution of identified issues

### Threshold Tuning
- **Conservative Approach**: Lower thresholds (3-5%) for more sensitive detection
- **Balanced Approach**: Standard thresholds (5-10%) for normal operations
- **Focused Approach**: Higher thresholds (10-15%) for high-volatility environments

## Troubleshooting

### Common Issues

#### File Loading Errors
- **Symptom**: "No balance sheet data found"
- **Solution**: Ensure sheet names contain keywords like "Balance" or "BS"

#### Data Validation Failures
- **Symptom**: "Balance sheet equation imbalance"
- **Solution**: Check that Assets = Liabilities + Equity within tolerance

#### Missing Account Codes
- **Symptom**: Accounts not categorized properly
- **Solution**: Update account mappings in `config/account_mappings.yaml`

#### No Anomalies Detected
- **Symptom**: Empty anomalies summary
- **Solution**: Check variance thresholds - may be too high for your data

### Performance Optimization
- Use `.xlsx` files rather than `.xls` for better performance
- Limit data to relevant periods (avoid loading unnecessary historical data)
- Consider processing large files in batches

## Advanced Features

### Custom Rules
Create custom correlation rules by adding to `config/rules_config.yaml`:

```yaml
- id: 14
  name: "Custom Rule Name"
  primary_account_category: "primary_category"
  correlated_account_category: "correlated_category"
  relationship_type: "positive"
  enabled: true
```

### Batch Processing
Use the batch processing script for multiple files:

```bash
python scripts/run_analysis.py -d /path/to/files --summary
```

### Logging Configuration
Control logging detail with environment variables:

```bash
export LOG_LEVEL=DEBUG
export LOG_FILE=logs/analysis.log
python src/main.py
```

## Support and Maintenance

### Regular Maintenance Tasks
1. **Review Thresholds**: Adjust based on business changes
2. **Update Account Mappings**: Add new accounts as chart of accounts evolves
3. **Validate Rules**: Ensure correlation rules remain relevant
4. **Archive Reports**: Organize output files by period

### System Requirements
- Python 3.8 or higher
- 4GB+ RAM for large datasets
- Excel 2016 or higher for optimal report viewing

For technical support or feature requests, refer to the project documentation or contact the development team.