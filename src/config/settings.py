"""
Application settings and configuration management.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
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
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration containers
        self.thresholds = {}
        self.rules_config = {}
        self.account_mappings = {}
        
        # Load configuration files
        self._load_config()
        self._validate_config()
        
    def _load_config(self):
        """Load configuration from YAML files with error handling."""
        # Load thresholds
        self.thresholds = self._load_yaml_config(
            self.config_dir / "thresholds.yaml",
            self._default_thresholds,
            "thresholds"
        )
            
        # Load rules configuration
        self.rules_config = self._load_yaml_config(
            self.config_dir / "rules_config.yaml",
            self._default_rules_config,
            "rules configuration"
        )
            
        # Load account mappings
        self.account_mappings = self._load_yaml_config(
            self.config_dir / "account_mappings.yaml",
            self._default_account_mappings,
            "account mappings"
        )
        
    def _load_yaml_config(self, file_path: Path, default_func, config_name: str) -> Dict[str, Any]:
        """Load a YAML config file with fallback to defaults."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config is None:
                        self.logger.warning(f"Empty {config_name} file, using defaults")
                        return default_func()
                    self.logger.info(f"Loaded {config_name} from {file_path}")
                    return config
            else:
                self.logger.warning(f"{config_name} file not found at {file_path}, using defaults")
                return default_func()
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing {config_name} YAML: {e}, using defaults")
            return default_func()
        except Exception as e:
            self.logger.error(f"Error loading {config_name}: {e}, using defaults")
            return default_func()
            
    def _validate_config(self):
        """Validate loaded configuration."""
        try:
            # Validate thresholds
            self._validate_thresholds()
            
            # Validate rules configuration
            self._validate_rules_config()
            
            # Validate account mappings
            self._validate_account_mappings()
            
            self.logger.info("Configuration validation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
            
    def _validate_thresholds(self):
        """Validate thresholds configuration."""
        required_keys = ['variance_threshold', 'critical_threshold', 'recurring_accounts']
        for key in required_keys:
            if key not in self.thresholds:
                raise ValueError(f"Missing required threshold key: {key}")
                
        # Validate numeric thresholds
        numeric_thresholds = ['variance_threshold', 'critical_threshold']
        for key in numeric_thresholds:
            if not isinstance(self.thresholds[key], (int, float)):
                raise ValueError(f"Threshold {key} must be numeric")
                
    def _validate_rules_config(self):
        """Validate rules configuration."""
        if 'correlation_rules' not in self.rules_config:
            raise ValueError("Missing correlation_rules in rules configuration")
            
        rules = self.rules_config['correlation_rules']
        if not isinstance(rules, list):
            raise ValueError("correlation_rules must be a list")
            
        required_rule_keys = ['id', 'name', 'primary_account_category', 'correlated_account_category', 'relationship_type']
        for rule in rules:
            for key in required_rule_keys:
                if key not in rule:
                    raise ValueError(f"Missing required rule key: {key} in rule {rule.get('id', 'unknown')}")
                    
    def _validate_account_mappings(self):
        """Validate account mappings configuration."""
        required_sections = ['balance_sheet', 'income_statement']
        for section in required_sections:
            if section not in self.account_mappings:
                raise ValueError(f"Missing required section: {section} in account mappings")
    
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
        # Check account-specific thresholds first
        if account_category:
            # Check account tolerances
            account_tolerances = self.thresholds.get("account_tolerances", {})
            if account_category in account_tolerances:
                return account_tolerances[account_category]
                
            # Check recurring accounts
            recurring_accounts = self.thresholds.get("recurring_accounts", {})
            if account_category in recurring_accounts:
                return recurring_accounts[account_category]
                
        return self.thresholds.get("variance_threshold", 5.0)
        
    def get_critical_threshold(self) -> float:
        """Get critical threshold."""
        return self.thresholds.get("critical_threshold", 10.0)
        
    def get_correlation_threshold(self) -> float:
        """Get correlation threshold."""
        return self.thresholds.get("correlation_thresholds", {}).get("global_correlation_threshold", 5.0)
        
    def get_correlation_rules(self) -> List[Dict[str, Any]]:
        """Get correlation rules configuration."""
        return self.rules_config.get("correlation_rules", [])
        
    def get_account_codes_by_category(self, statement_type: str, category: str) -> List[str]:
        """Get account codes for a specific category."""
        return self.account_mappings.get(statement_type, {}).get(category, [])
        
    def get_recurring_account_codes(self) -> List[str]:
        """Get list of recurring account codes."""
        return self.account_mappings.get("analysis_categories", {}).get("recurring_accounts", [])
        
    def get_cyclical_account_codes(self) -> List[str]:
        """Get list of cyclical account codes."""
        return self.account_mappings.get("analysis_categories", {}).get("cyclical_accounts", [])
        
    def get_materiality_threshold(self, account_code: str) -> float:
        """Get materiality threshold for specific account."""
        materiality_config = self.account_mappings.get("materiality_thresholds", {})
        
        for level, config in materiality_config.items():
            if account_code in config.get("accounts", []):
                return config.get("threshold", 5.0)
                
        return 5.0  # Default threshold
        
    def get_severity_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get severity classification thresholds."""
        return self.thresholds.get("severity_levels", {
            "critical": {"variance_threshold": 20.0, "absolute_threshold": 1000000},
            "high": {"variance_threshold": 10.0, "absolute_threshold": 500000},
            "medium": {"variance_threshold": 5.0, "absolute_threshold": 100000}
        })
        
    def is_account_recurring(self, account_code: str) -> bool:
        """Check if account is marked as recurring."""
        recurring_accounts = self.get_recurring_account_codes()
        return account_code in recurring_accounts
        
    def is_account_cyclical(self, account_code: str) -> bool:
        """Check if account is marked as cyclical."""
        cyclical_accounts = self.get_cyclical_account_codes()
        return account_code in cyclical_accounts