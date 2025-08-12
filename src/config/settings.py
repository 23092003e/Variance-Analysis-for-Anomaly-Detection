"""
Application settings and configuration management.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"
        self.output_dir = self.data_dir / "output"
        
        # Load configuration files
        self._load_config()
        
    def _load_config(self):
        """Load configuration from YAML files."""
        # Load thresholds
        thresholds_file = self.config_dir / "thresholds.yaml"
        if thresholds_file.exists():
            with open(thresholds_file, 'r') as f:
                self.thresholds = yaml.safe_load(f)
        else:
            self.thresholds = self._default_thresholds()
            
        # Load rules configuration
        rules_file = self.config_dir / "rules_config.yaml"
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                self.rules_config = yaml.safe_load(f)
        else:
            self.rules_config = self._default_rules_config()
            
        # Load account mappings
        mappings_file = self.config_dir / "account_mappings.yaml"
        if mappings_file.exists():
            with open(mappings_file, 'r') as f:
                self.account_mappings = yaml.safe_load(f)
        else:
            self.account_mappings = self._default_account_mappings()
    
    def _default_thresholds(self) -> Dict[str, Any]:
        """Default variance thresholds."""
        return {
            "variance_threshold": float(os.getenv("VARIANCE_THRESHOLD", "5.0")),
            "critical_threshold": float(os.getenv("CRITICAL_THRESHOLD", "10.0")),
            "recurring_accounts": {
                "depreciation": 5.0,
                "revenue": 5.0,
                "opex": 5.0,
                "interest_expense": 5.0,
                "interest_income": 5.0
            }
        }
    
    def _default_rules_config(self) -> Dict[str, Any]:
        """Default correlation rules configuration."""
        return {
            "correlation_rules": [
                {
                    "id": 1,
                    "name": "Investment Properties vs Depreciation",
                    "primary_account": "investment_properties",
                    "correlated_account": "depreciation",
                    "relationship": "positive",
                    "enabled": True
                },
                {
                    "id": 2,
                    "name": "Loan Balance vs Interest Expense",
                    "primary_account": "borrowings",
                    "correlated_account": "interest_expense",
                    "relationship": "positive",
                    "enabled": True
                },
                {
                    "id": 3,
                    "name": "Cash Deposits vs Interest Income",
                    "primary_account": "cash_deposits",
                    "correlated_account": "interest_income",
                    "relationship": "positive",
                    "enabled": True
                }
            ]
        }
    
    def _default_account_mappings(self) -> Dict[str, Any]:
        """Default account code mappings."""
        return {
            "balance_sheet": {
                "investment_properties": ["217000001", "217000006"],
                "borrowings": ["341160000", "341160001"],
                "cash_deposits": ["112227001", "112227002"],
                "trade_receivables": ["131100001"],
                "unbilled_revenue": ["138900003"],
                "vat_deductible": ["133100001"]
            },
            "income_statement": {
                "depreciation": ["632100001", "632100002"],
                "interest_expense": ["635000005", "635000006"],
                "interest_income": ["515100001"],
                "revenue": ["511100001", "511100002"],
                "opex": ["622000001", "622000002"]
            }
        }
    
    @property
    def default_input_file(self) -> str:
        """Default input file path."""
        return str(self.data_dir / "raw" / "DAL_May'25_example.xlsx")
    
    @property
    def default_output_file(self) -> str:
        """Default output file path."""
        return str(self.output_dir / "variance_analysis_report.xlsx")
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return os.getenv("LOG_LEVEL", "INFO")
    
    def get_account_codes(self, account_type: str, category: str) -> List[str]:
        """Get account codes for specific category."""
        return self.account_mappings.get(account_type, {}).get(category, [])
    
    def get_variance_threshold(self, account_category: str = None) -> float:
        """Get variance threshold for account category."""
        if account_category and account_category in self.thresholds.get("recurring_accounts", {}):
            return self.thresholds["recurring_accounts"][account_category]
        return self.thresholds["variance_threshold"]