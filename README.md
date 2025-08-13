# Variance Analysis for Anomaly Detection

A comprehensive financial analysis system that automatically detects anomalies in financial statements using variance analysis and correlation rule validation.

## 🎯 Purpose

This system implements **Use Case 2: Variance Analysis for Anomaly Detection** to:

- **Review key financial metrics** across periods (depreciation, revenue, OPEX)
- **Identify anomalies** through variance analysis and correlation rules
- **Generate "Anomalies Summary" sheet** for management review
- **Enable quick focus** on critical financial issues

## 🚀 Key Features

### 🔍 Comprehensive Anomaly Detection
- **Variance Analysis**: Period-over-period comparison with configurable thresholds
- **13 Correlation Rules**: Built-in financial logic validation (IP↔Depreciation, Loans↔Interest, etc.)
- **Sign Change Detection**: Identifies accounts switching from positive to negative
- **Recurring Account Monitoring**: Flags unusual changes in normally stable accounts
- **Quarterly Pattern Analysis**: Validates expected seasonal patterns

### 📊 Intelligent Classification
- **4 Severity Levels**: Critical (>20%), High (10-20%), Medium (5-10%), Low (<5%)
- **5 Anomaly Types**: Variance, Correlation Violation, Sign Change, Recurring Spike, Quarterly Pattern
- **Priority Scoring**: Automatically ranks anomalies by severity and impact

### 📈 Professional Excel Reports
- **Anomalies Summary**: Main management dashboard with conditional formatting
- **Detailed Analysis**: Comprehensive variance calculations and explanations
- **Correlation Violations**: Rule-based anomaly details
- **Dashboard View**: High-level statistics and top variances
- **Original Data**: Reference sheets for verification

## 🏗️ System Architecture

```
src/
├── config/          # Settings and account mappings
├── data/            # Data loading and validation
├── analysis/        # Core analysis engines
│   ├── variance_analyzer.py     # Period-over-period analysis
│   ├── correlation_engine.py    # 13-rule correlation validation  
│   └── anomaly_detector.py      # Comprehensive anomaly detection
├── reports/         # Excel generation and formatting
└── utils/           # Utilities and calculations

config/
├── thresholds.yaml      # Variance thresholds and tolerances
├── rules_config.yaml    # Correlation rules definition
└── account_mappings.yaml # Account categorization and mappings
```

## ⚡ Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd Variance-Analysis-for-Anomaly-Detection

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```bash
# Process single file
python src/main.py -i data/raw/financial_data.xlsx -o data/output/report.xlsx

# Use default paths
python src/main.py

# Batch processing
python scripts/run_analysis.py -d data/raw/ -o data/output/
```

## 📋 The 13 Correlation Rules

| # | Rule | Expected Relationship | Business Logic |
|---|------|---------------------|----------------|
| 1 | Investment Properties ↔ Depreciation | ↑ IP → ↑ Depreciation | More assets = more depreciation |
| 2 | Loan Balance ↔ Interest Expense | ↑ Loans → ↑ Interest | Higher debt = higher interest cost |
| 3 | Cash Deposits ↔ Interest Income | ↑ Cash → ↑ Interest Income | More cash = more interest earned |
| 4 | Trade Receivables ↔ Quarterly Cycle | Spike at quarter start | Quarterly billing pattern |
| 5 | Unbilled Revenue ↔ Quarter Timing | Peak at quarter end | Revenue recognition timing |
| 6 | Unearned Revenue ↔ Advance Collection | Increase at quarter start | Advance payment pattern |
| 7 | Investment Properties ↔ VAT Deductible | ↑ CapEx → ↑ VAT | Capital spending creates VAT |
| 8 | Occupancy Rate ↔ Revenue | ↑ Occupancy → ↑ Revenue | More tenants = more income |
| 9 | Maintenance ↔ OPEX | ↑ Maintenance → ↑ OPEX | Maintenance drives operating costs |
| 10 | Asset Disposal ↔ Depreciation | ↑ Disposal → ↓ Depreciation | Less assets = less depreciation |
| 11 | New Leases ↔ Revenue | ↑ New Leases → ↑ Revenue | New tenants increase income |
| 12 | Lease Termination ↔ Revenue | ↑ Terminations → ↓ Revenue | Lost tenants reduce income |
| 13 | FX Volatility ↔ FX Gain/Loss | ↑ Volatility → ↑ FX Impact | Currency changes affect FX |

## 📊 Input Data Format

### Excel File Structure
```
Sheet: "Balance Sheet" or "BS"
├── Account Code     (217000001, 112227001, ...)
├── Account Name     (Investment Properties, Cash, ...)
├── Mar_2025        (Current period values)
├── Apr_2025        (Previous period values)
└── May_2025        (Earlier period values)

Sheet: "Income Statement" or "IS"  
├── Account Code     (632100001, 511100001, ...)
├── Account Name     (Depreciation, Revenue, ...)
├── Mar_2025        (Current period values)
├── Apr_2025        (Previous period values)
└── May_2025        (Earlier period values)
```

### Supported Account Categories
- **Investment Properties**: 217000001, 217000006
- **Cash Deposits**: 112227001, 112227002
- **Borrowings**: 341160000, 341160001
- **Revenue**: 511100001, 511100002
- **Depreciation**: 632100001, 632100002
- **Interest Expense**: 635000005, 635000006

## 🎛️ Configuration

### Variance Thresholds (`config/thresholds.yaml`)
```yaml
variance_threshold: 5.0        # Default significance threshold
critical_threshold: 10.0       # Critical anomaly threshold

recurring_accounts:
  depreciation: 5.0            # Stable account thresholds
  revenue: 5.0
  opex: 5.0
```

### Account Mappings (`config/account_mappings.yaml`)
```yaml
balance_sheet:
  investment_properties:
    - "217000001"              # Land Use Rights
    - "217000006"              # Office Building
  cash_deposits:
    - "112227001"              # USD Account
```

## 📈 Sample Output

### Anomalies Summary Sheet
| Severity | Type | Account Code | Account Name | Description | Variance % | Action |
|----------|------|--------------|--------------|-------------|------------|--------|
| **CRITICAL** | Variance | 217000001 | Investment Properties | Account increased by 25.3% (250M) | 25.3% | URGENT: Investigate asset additions |
| **HIGH** | Correlation | 632100001 | Depreciation | IP increased 25% but depreciation only 2% | 2.0% | Review depreciation calculation |
| **HIGH** | Sign Change | 641100001 | FX Gain/Loss | Changed from positive (10M) to negative (-15M) | -250% | Investigate FX exposure |

### Dashboard Statistics
- **Total Accounts Analyzed**: 45
- **Significant Variances**: 12 (27%)
- **Critical Anomalies**: 3
- **Rule Violations**: 5

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_variance_analyzer.py
pytest tests/test_correlation_engine.py
pytest tests/test_anomaly_detector.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📁 Project Structure

```
Variance-Analysis-for-Anomaly-Detection/
├── README.md                    # This file
├── requirements.txt             # Dependencies
├── setup.py                    # Package setup
├── .gitignore                  # Git ignore rules
├── .env.example               # Environment template
│
├── src/                       # Source code
│   ├── main.py               # Application entry point
│   ├── config/               # Configuration management
│   ├── data/                 # Data loading and validation
│   ├── analysis/             # Core analysis engines
│   ├── reports/              # Excel generation
│   └── utils/                # Utilities
│
├── config/                    # Configuration files
│   ├── thresholds.yaml       # Variance thresholds
│   ├── rules_config.yaml     # Correlation rules
│   └── account_mappings.yaml # Account mappings
│
├── data/                      # Data directories
│   ├── raw/                  # Input Excel files
│   ├── processed/            # Intermediate data
│   └── output/               # Generated reports
│
├── tests/                     # Test suite
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
└── logic/                     # Business logic documentation
```

## 🛠️ Development

### Adding New Correlation Rules
1. Define rule in `config/rules_config.yaml`
2. Add account mappings in `config/account_mappings.yaml`
3. Update correlation engine if needed
4. Add tests for the new rule

### Customizing Thresholds
1. Modify `config/thresholds.yaml` for global changes
2. Update account-specific tolerances
3. Test with sample data to validate sensitivity

### Extending Account Support
1. Add new account codes to `config/account_mappings.yaml`
2. Update account categories in `config/account_mapping.py`
3. Test with data containing new accounts

## 📚 Documentation

- **[User Guide](docs/user_guide.md)**: Comprehensive usage instructions
- **[Business Rules](logic/)**: Detailed rule explanations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Based on real-world financial analysis requirements
- Implements Vietnamese Chart of Accounts standards
- Designed for property management and real estate companies
- Built with Python, pandas, and Excel integration

---

**Made with ❤️ for financial analysts who want to focus on insights, not data processing.**

