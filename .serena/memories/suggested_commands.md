# Suggested Commands

## Development Commands
- **Run analysis**: `python src/main.py -i data/raw/financial_data.xlsx -o data/output/report.xlsx`
- **Default run**: `python src/main.py`
- **Batch processing**: `python scripts/run_analysis.py -d data/raw/ -o data/output/`

## Testing
- **Run all tests**: `pytest tests/`
- **Specific tests**: `pytest tests/test_variance_analyzer.py`
- **With coverage**: `pytest tests/ --cov=src --cov-report=html`

## Code Quality
- **Format**: `black src/ tests/`
- **Lint**: `flake8 src/ tests/`

## Windows System Commands
- **List files**: `dir` or `ls` (if available)
- **Find files**: `where filename` or `findstr pattern file`
- **Git**: Standard git commands work on Windows
- **Python**: `python` (not `python3` on Windows)

## Project Structure
```
src/
├── main.py              # Entry point
├── config/              # Settings and configurations
├── data/                # Data loading (DAL-specific and generic)
├── analysis/            # Core analysis engines
├── reports/             # Excel generation
└── utils/               # Utilities
```