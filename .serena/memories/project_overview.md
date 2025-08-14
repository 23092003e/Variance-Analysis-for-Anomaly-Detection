# Variance Analysis for Anomaly Detection - Project Overview

## Purpose
A comprehensive financial analysis system that automatically detects anomalies in financial statements using variance analysis and correlation rule validation for property management and real estate companies.

## Current Architecture (Single Project)
The system is currently designed for single DAL project analysis with:
- Balance Sheet and Income Statement analysis
- 13 correlation rules for financial logic validation
- Variance analysis with configurable thresholds
- Anomaly detection and severity classification
- Excel report generation

## Tech Stack
- **Language**: Python 3.8+
- **Data Processing**: pandas, numpy, scipy
- **Excel**: openpyxl, xlsxwriter
- **Config**: PyYAML, python-dotenv
- **Testing**: pytest, pytest-cov
- **Code Quality**: black, flake8
- **OS**: Windows

## Current Limitations (Single Project Design)
1. **Hard-coded single project assumption**: Settings class assumes one project with fixed paths
2. **Single data file processing**: Main function processes one input/output file at a time
3. **Global configuration**: All thresholds and rules are global, not project-specific
4. **Fixed account mappings**: Account codes are globally defined, not per-project
5. **Single DAL loader**: Specialized for one DAL project structure
6. **Static reporting**: Output assumes single project analysis

## Key Components for Refactoring
- `Settings` class: Currently loads single global config
- `FinancialData` model: Has `subsidiaries` field but not used for multi-project
- `DALDataLoader`: Project-specific but single project focused
- Main execution flow: Single file in/out processing
- Account mappings: Global YAML configuration