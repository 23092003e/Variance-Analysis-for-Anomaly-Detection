"""
Data loader factory pattern for handling different project types and file formats.
Provides intelligent loader selection and fallback mechanisms.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Union
import pandas as pd

try:
    from .loader import DataLoader
    from .dal_loader import DALDataLoader
    from .project_detector import ProjectDetector, ProjectType
    from .models import FinancialData
    from ..config.settings import Settings
except ImportError:
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from data.loader import DataLoader
    from data.dal_loader import DALDataLoader
    from data.project_detector import ProjectDetector, ProjectType
    from data.models import FinancialData
    from config.settings import Settings

logger = logging.getLogger(__name__)


class LoaderStrategy(ABC):
    """Abstract base class for data loading strategies."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_handle(self, file_path: str, project_info: Dict[str, Any]) -> bool:
        """Check if this loader can handle the given file."""
        pass
    
    @abstractmethod
    def load(self, file_path: str, project_info: Optional[Dict[str, Any]] = None) -> FinancialData:
        """Load financial data from file."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get loader priority (higher = more specific, tried first)."""
        pass


class DALLoaderStrategy(LoaderStrategy):
    """Strategy for loading DAL project files."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.dal_loader = DALDataLoader(settings)
    
    def can_handle(self, file_path: str, project_info: Dict[str, Any]) -> bool:
        """Check if file appears to be DAL format."""
        try:
            project_type = ProjectType(project_info.get('project_type', 'UNKNOWN'))
            return project_type == ProjectType.DAL
        except:
            return False
    
    def load(self, file_path: str, project_info: Optional[Dict[str, Any]] = None) -> FinancialData:
        """Load using DAL-specific loader."""
        self.logger.info(f"Loading {file_path} using DAL loader strategy")
        return self.dal_loader.load_dal_excel_file(file_path)
    
    def get_priority(self) -> int:
        return 100  # High priority for DAL files


class StandardLoaderStrategy(LoaderStrategy):
    """Strategy for loading standard format files."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.standard_loader = DataLoader(settings)
    
    def can_handle(self, file_path: str, project_info: Dict[str, Any]) -> bool:
        """Standard loader can handle most file formats."""
        return True  # Fallback loader
    
    def load(self, file_path: str, project_info: Optional[Dict[str, Any]] = None) -> FinancialData:
        """Load using standard loader."""
        self.logger.info(f"Loading {file_path} using standard loader strategy")
        return self.standard_loader.load_excel_file(file_path)
    
    def get_priority(self) -> int:
        return 10  # Low priority - fallback option


class FlexibleLoaderStrategy(LoaderStrategy):
    """Flexible loader that adapts to different column formats."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.standard_loader = DataLoader(settings)
        self.column_mappings = self._init_column_mappings()
    
    def _init_column_mappings(self) -> Dict[str, List[str]]:
        """Initialize flexible column mapping patterns."""
        return {
            'account_code': [
                'account code', 'account_code', 'accountcode', 
                'mã tài khoản', 'ma tai khoan', 'code', 'mã',
                'account number', 'account_number', 'accountnumber',
                'account_id', 'id'
            ],
            'account_name': [
                'account name', 'account_name', 'accountname',
                'tên tài khoản', 'ten tai khoan', 'name', 'tên',
                'description', 'account description', 'desc',
                'account_desc', 'account_description'
            ],
            'balance_sheet_keywords': [
                'balance', 'bs', 'bảng cân đối', 'bang can doi',
                'balance sheet', 'balancesheet', 'statement of position'
            ],
            'income_statement_keywords': [
                'income', 'is', 'p&l', 'profit', 'loss',
                'kết quả', 'ket qua', 'kinh doanh',
                'income statement', 'profit and loss', 'pnl'
            ]
        }
    
    def can_handle(self, file_path: str, project_info: Dict[str, Any]) -> bool:
        """Check if flexible loading might work."""
        try:
            # Try to read basic Excel info
            xl_file = pd.ExcelFile(file_path)
            return len(xl_file.sheet_names) > 0
        except:
            return False
    
    def load(self, file_path: str, project_info: Optional[Dict[str, Any]] = None) -> FinancialData:
        """Load using flexible column detection with strict validation."""
        self.logger.info(f"Loading {file_path} using flexible loader strategy")
        
        try:
            # First, try standard loader
            return self.standard_loader.load_excel_file(file_path)
            
        except Exception as e:
            self.logger.warning(f"Standard loader failed: {e}, trying flexible approach")
            
            # Try flexible loading with strict validation
            try:
                result = self._flexible_load(file_path, project_info)
                
                # Strict validation: ensure we have meaningful account data
                if not self._validate_flexible_result(result, file_path):
                    raise ValueError(f"Flexible loading failed validation for {file_path}")
                
                return result
                
            except Exception as flex_error:
                self.logger.error(f"Flexible loading failed for {file_path}: {flex_error}")
                raise ValueError(f"Unable to process {file_path}: No suitable loading strategy succeeded")

    def _validate_flexible_result(self, financial_data: FinancialData, file_path: str) -> bool:
        """Validate flexible loading results to ensure data quality."""
        try:
            # Check if we have any meaningful data
            has_bs = financial_data.balance_sheet is not None and not financial_data.balance_sheet.empty
            has_is = financial_data.income_statement is not None and not financial_data.income_statement.empty
            
            if not has_bs and not has_is:
                self.logger.warning(f"No meaningful financial data found in {file_path}")
                return False
            
            # Check account code columns
            for sheet_name, df in [("Balance Sheet", financial_data.balance_sheet), 
                                 ("Income Statement", financial_data.income_statement)]:
                if df is not None and not df.empty:
                    if 'account_code' not in df.columns:
                        self.logger.warning(f"No account_code column in {sheet_name} for {file_path}")
                        return False
                    
                    # Check if account codes are meaningful (not all empty/nan)
                    valid_codes = df['account_code'].dropna()
                    valid_codes = valid_codes[valid_codes.astype(str).str.strip() != '']
                    
                    if len(valid_codes) < 3:  # Need at least 3 valid account codes
                        self.logger.warning(f"Insufficient valid account codes in {sheet_name} for {file_path} ({len(valid_codes)} found)")
                        return False
            
            # Check periods
            if len(financial_data.periods) < 2:
                self.logger.warning(f"Insufficient periods for analysis in {file_path} ({len(financial_data.periods)} found)")
                return False
            
            self.logger.info(f"Flexible loading validation passed for {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating flexible result for {file_path}: {e}")
            return False
    
    def _flexible_load(self, file_path: str, project_info: Optional[Dict[str, Any]]) -> FinancialData:
        """Attempt flexible loading with column detection."""
        xl_file = pd.ExcelFile(file_path)
        
        # Find balance sheet and income statement sheets
        bs_sheet = self._find_sheet_by_keywords(xl_file.sheet_names, 'balance_sheet_keywords')
        is_sheet = self._find_sheet_by_keywords(xl_file.sheet_names, 'income_statement_keywords')
        
        if not bs_sheet and not is_sheet:
            raise ValueError("Could not identify balance sheet or income statement sheets")
        
        # Load and process sheets
        balance_sheet_data = None
        income_statement_data = None
        
        if bs_sheet:
            balance_sheet_data = self._flexible_sheet_load(file_path, bs_sheet)
            if balance_sheet_data is not None and not balance_sheet_data.empty:
                self.logger.info(f"Loaded balance sheet with {len(balance_sheet_data)} rows")
        
        if is_sheet:
            income_statement_data = self._flexible_sheet_load(file_path, is_sheet)
            if income_statement_data is not None and not income_statement_data.empty:
                self.logger.info(f"Loaded income statement with {len(income_statement_data)} rows")
        
        # Check if we have any data
        if (balance_sheet_data is None or balance_sheet_data.empty) and \
           (income_statement_data is None or income_statement_data.empty):
            raise ValueError("No financial data could be extracted from any sheets")
        
        # Extract periods and subsidiaries
        data_for_periods = balance_sheet_data if balance_sheet_data is not None and not balance_sheet_data.empty else income_statement_data
        periods = self._extract_flexible_periods(data_for_periods)
        subsidiaries = ["Consolidated"]  # Default for flexible loading
        
        # Ensure we have periods
        if not periods:
            periods = ["Current Period"]  # Default fallback
        
        return FinancialData(
            balance_sheet=balance_sheet_data,
            income_statement=income_statement_data,
            periods=periods,
            subsidiaries=subsidiaries,
            metadata={
                'loader_type': 'flexible',
                'source_file': file_path,
                'sheets_processed': {
                    'balance_sheet': bs_sheet,
                    'income_statement': is_sheet
                }
            }
        )
    
    def _find_sheet_by_keywords(self, sheet_names: List[str], keyword_type: str) -> Optional[str]:
        """Find sheet matching keyword patterns."""
        keywords = self.column_mappings[keyword_type]
        
        for sheet_name in sheet_names:
            sheet_lower = sheet_name.lower()
            for keyword in keywords:
                if keyword.lower() in sheet_lower:
                    return sheet_name
        
        return None
    
    def _flexible_sheet_load(self, file_path: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """Load sheet with flexible column detection and smart data cleaning."""
        try:
            # Try different approaches to find the data
            df = None
            account_col = None
            
            # Approach 1: Try reading from top with different skip rows
            for skip_rows in [0, 3, 5, 7, 10, 15, 20]:
                try:
                    temp_df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows, nrows=50)
                    
                    if temp_df.empty or len(temp_df.columns) < 2:
                        continue
                    
                    # Check if this section has account-like data
                    potential_account_col = self._find_account_column_in_df(temp_df)
                    
                    if potential_account_col:
                        df = temp_df
                        account_col = potential_account_col
                        self.logger.info(f"Found data starting at row {skip_rows} in {sheet_name}")
                        break
                        
                except Exception as e:
                    self.logger.debug(f"Failed to read with skiprows={skip_rows}: {e}")
                    continue
            
            if df is None or account_col is None:
                self.logger.warning(f"No account code column found in {sheet_name}")
                return None
            
            # Find account name column
            name_col = self._find_column_by_keywords(df.columns, 'account_name')
            
            # Standardize column names
            column_mapping = {account_col: 'account_code'}
            if name_col:
                column_mapping[name_col] = 'account_name'
            
            df = df.rename(columns=column_mapping)
            
            # Enhanced data cleaning for financial data
            if 'account_code' in df.columns:
                initial_rows = len(df)
                
                # Remove rows where account code is NaN or empty
                df = df[df['account_code'].notna()]
                df = df[df['account_code'].astype(str).str.strip() != '']
                df = df[df['account_code'].astype(str).str.strip() != 'nan']
                
                # Remove header-like rows with text patterns
                header_patterns = [
                    'account', 'code', 'total', 'sum', 'entity', 
                    'as of', 'period', 'date', 'month', 'year',
                    'số cuối kỳ', 'mã số', 'line'
                ]
                
                for pattern in header_patterns:
                    mask = df['account_code'].astype(str).str.lower().str.contains(pattern, na=False)
                    df = df[~mask]
                
                # Keep only rows where account_code looks like actual account codes
                # (numeric or starts with numbers)
                numeric_mask = df['account_code'].astype(str).str.match(r'^\d', na=False)
                df = df[numeric_mask]
                
                # Clean period columns - convert to numeric and filter rows
                period_columns = [col for col in df.columns if col not in ['account_code', 'account_name']]
                
                for col in period_columns:
                    # Convert to numeric, keeping only numeric values
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Remove rows where ALL period columns are NaN
                if period_columns:
                    df = df.dropna(subset=period_columns, how='all')
                
                self.logger.info(f"Data cleaning: {initial_rows} → {len(df)} rows (removed {initial_rows - len(df)} header/invalid rows)")
                
                if len(df) > 0:
                    self.logger.info(f"Successfully loaded {len(df)} clean data rows from {sheet_name}")
                    
                    # Log sample of cleaned data
                    sample_codes = df['account_code'].head(3).tolist()
                    self.logger.info(f"Sample account codes: {sample_codes}")
                    
                    return df
                else:
                    self.logger.warning(f"No valid account data found after cleaning in {sheet_name}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in flexible sheet loading: {e}")
            return None
    
    def _find_account_column_in_df(self, df: pd.DataFrame) -> Optional[str]:
        """Find account column in a dataframe using multiple strategies."""
        # Strategy 1: Look for columns with keyword matches
        account_col = self._find_column_by_keywords(df.columns, 'account_code')
        if account_col:
            return account_col
        
        # Strategy 2: Look for columns with numeric patterns that look like account codes
        for col in df.columns:
            try:
                # Convert column to string and check patterns
                col_values = df[col].dropna().astype(str)
                
                if len(col_values) == 0:
                    continue
                
                # Check for account code patterns
                numeric_pattern = col_values.str.match(r'^\d{4,9}$').sum()
                mixed_pattern = col_values.str.match(r'^[A-Z]{1,4}\d+$').sum()
                
                # If more than 30% look like account codes, it's probably an account column
                if numeric_pattern > len(col_values) * 0.3 or mixed_pattern > len(col_values) * 0.3:
                    self.logger.info(f"Found account column by pattern: {col} ({numeric_pattern + mixed_pattern}/{len(col_values)} matches)")
                    return col
                    
            except Exception as e:
                self.logger.debug(f"Error checking column {col}: {e}")
                continue
        
        # Strategy 3: Check first few columns for numeric data
        for i, col in enumerate(df.columns[:5]):
            try:
                col_values = df[col].dropna().astype(str)
                
                # Look for columns that start with numbers
                numeric_starts = col_values.str.match(r'^\d').sum()
                
                if numeric_starts > len(col_values) * 0.5 and len(col_values) > 3:
                    self.logger.info(f"Using column {col} as account code (position-based)")
                    return col
                    
            except:
                continue
        
        return None
    
    def _find_column_by_keywords(self, columns: List[str], keyword_type: str) -> Optional[str]:
        """Find column matching keyword patterns."""
        keywords = self.column_mappings[keyword_type]
        
        for col in columns:
            col_lower = str(col).lower().strip()
            for keyword in keywords:
                if keyword.lower() in col_lower:
                    return col
        
        return None
    
    def _extract_flexible_periods(self, df: Optional[pd.DataFrame]) -> List[str]:
        """Extract period information from column names."""
        if df is None:
            return []
        
        periods = []
        excluded_cols = ['account_code', 'account_name', 'unnamed: 0', 'unnamed: 1', 'unnamed: 2']
        
        for col in df.columns:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            
            # Skip account info columns
            if any(excl in col_lower for excl in excluded_cols):
                continue
            
            # Check for various date/period patterns
            date_patterns = [
                # Month names
                'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                # Years
                '2024', '2025', '2026', '2023', '2022',
                # Common period formats
                'q1', 'q2', 'q3', 'q4',
                # Vietnamese months
                'tháng', 'thang'
            ]
            
            # Look for numeric columns that might be amounts (periods)
            if any(pattern in col_lower for pattern in date_patterns):
                periods.append(col_str)
                self.logger.debug(f"Found period column by pattern: {col_str}")
            elif col_str.startswith(('Unnamed:', 'Column')) and col_str not in excluded_cols:
                # For unnamed columns, check if they contain numeric data (could be periods)
                try:
                    # Sample the column to see if it contains numeric financial data
                    sample_values = df[col].dropna().head(10)
                    if len(sample_values) > 0:
                        # Check if values look like financial amounts
                        numeric_count = 0
                        for val in sample_values:
                            try:
                                float_val = float(val)
                                if abs(float_val) > 1:  # Likely financial amounts
                                    numeric_count += 1
                            except:
                                pass
                        
                        if numeric_count > len(sample_values) * 0.5:
                            periods.append(col_str)
                            self.logger.debug(f"Found period column by numeric content: {col_str}")
                except:
                    pass
        
        # If no periods found through patterns, try to identify numeric columns
        if not periods:
            self.logger.info("No period columns found by pattern, using numeric columns")
            for col in df.columns:
                col_str = str(col).strip()
                col_lower = col_str.lower()
                
                # Skip known non-period columns
                if any(excl in col_lower for excl in excluded_cols):
                    continue
                
                try:
                    # Check if column contains mostly numeric data
                    sample_values = df[col].dropna().head(20)
                    if len(sample_values) > 5:
                        numeric_count = 0
                        for val in sample_values:
                            try:
                                float(val)
                                numeric_count += 1
                            except:
                                pass
                        
                        if numeric_count > len(sample_values) * 0.7:  # 70% numeric
                            periods.append(col_str)
                            self.logger.info(f"Added numeric column as period: {col_str}")
                except:
                    pass
        
        # Ensure we have at least some periods for analysis
        if not periods and len(df.columns) > 2:
            # As last resort, use columns beyond account code and name
            for col in df.columns[2:]:
                if str(col).lower() not in excluded_cols:
                    periods.append(str(col))
                    if len(periods) >= 3:  # Don't take too many
                        break
            self.logger.info(f"Using fallback columns as periods: {periods}")
        
        self.logger.info(f"Extracted {len(periods)} periods: {periods}")
        return periods
    
    def get_priority(self) -> int:
        return 50  # Medium priority


class LoaderFactory:
    """Factory for creating appropriate data loaders based on file type and content."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.project_detector = ProjectDetector()
        
        # Initialize available strategies
        self.strategies: List[LoaderStrategy] = [
            DALLoaderStrategy(settings),
            FlexibleLoaderStrategy(settings),
            StandardLoaderStrategy(settings)  # Always last as fallback
        ]
        
        # Sort strategies by priority (highest first)
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)
    
    def create_loader(self, file_path: str, force_type: Optional[str] = None) -> FinancialData:
        """
        Create appropriate loader and load data from file.
        
        Args:
            file_path: Path to Excel file
            force_type: Optional forced loader type ('dal', 'standard', 'flexible')
            
        Returns:
            FinancialData object
            
        Raises:
            ValueError: If no suitable loader can handle the file
        """
        try:
            self.logger.info(f"Creating loader for {file_path}")
            
            # Detect project type if not forced
            if force_type:
                project_info = {'recommended_loader': force_type}
                self.logger.info(f"Forcing loader type: {force_type}")
            else:
                project_type, project_details = self.project_detector.detect_project_type(file_path)
                project_info = self.project_detector.get_project_profile(project_type, project_details)
                self.logger.info(f"Detected project type: {project_type.value}, "
                               f"recommended loader: {project_info.get('recommended_loader')}")
            
            # Try strategies in priority order
            last_error = None
            
            for strategy in self.strategies:
                try:
                    # Check if strategy can handle this file
                    if force_type:
                        # For forced type, check if strategy matches
                        strategy_name = strategy.__class__.__name__.lower()
                        if force_type in strategy_name or (force_type == 'standard' and 'standard' in strategy_name):
                            can_handle = True
                        elif force_type == 'dal' and 'dal' in strategy_name:
                            can_handle = True
                        elif force_type == 'flexible' and 'flexible' in strategy_name:
                            can_handle = True
                        else:
                            can_handle = False
                    else:
                        can_handle = strategy.can_handle(file_path, project_info)
                    
                    if can_handle:
                        self.logger.info(f"Trying {strategy.__class__.__name__}")
                        financial_data = strategy.load(file_path, project_info)
                        
                        # Validate loaded data
                        if self._validate_loaded_data(financial_data):
                            self.logger.info(f"Successfully loaded {file_path} using {strategy.__class__.__name__}")
                            return financial_data
                        else:
                            self.logger.warning(f"{strategy.__class__.__name__} loaded data but validation failed")
                            
                except Exception as e:
                    self.logger.warning(f"{strategy.__class__.__name__} failed: {e}")
                    last_error = e
                    continue
            
            # If all strategies failed
            error_msg = f"No loader could successfully process {file_path}"
            if last_error:
                error_msg += f". Last error: {last_error}"
            
            raise ValueError(error_msg)
            
        except Exception as e:
            self.logger.error(f"Error creating loader for {file_path}: {e}")
            raise
    
    def _validate_loaded_data(self, financial_data: FinancialData) -> bool:
        """Validate that loaded data is usable."""
        try:
            # Check if we have at least some data
            if (financial_data.balance_sheet is None or financial_data.balance_sheet.empty) and \
               (financial_data.income_statement is None or financial_data.income_statement.empty):
                self.logger.warning("No balance sheet or income statement data found")
                return False
            
            # Check for periods
            if not financial_data.periods:
                self.logger.warning("No periods found in financial data")
                return False
            
            # Check for meaningful data in at least one sheet
            has_data = False
            
            if financial_data.balance_sheet is not None and not financial_data.balance_sheet.empty:
                if len(financial_data.balance_sheet) > 0:
                    has_data = True
                    self.logger.debug(f"Balance sheet has {len(financial_data.balance_sheet)} rows")
            
            if financial_data.income_statement is not None and not financial_data.income_statement.empty:
                if len(financial_data.income_statement) > 0:
                    has_data = True
                    self.logger.debug(f"Income statement has {len(financial_data.income_statement)} rows")
            
            if has_data:
                self.logger.debug(f"Data validation passed - Periods: {financial_data.periods}")
            
            return has_data
            
        except Exception as e:
            self.logger.warning(f"Error validating loaded data: {e}")
            return False
    
    def get_supported_loaders(self) -> List[str]:
        """Get list of supported loader types."""
        return ['auto', 'dal', 'standard', 'flexible']
    
    def get_loader_info(self) -> Dict[str, Any]:
        """Get information about available loaders."""
        info = {
            'strategies': [],
            'project_detector_available': True
        }
        
        for strategy in self.strategies:
            info['strategies'].append({
                'name': strategy.__class__.__name__,
                'priority': strategy.get_priority(),
                'description': strategy.__class__.__doc__ or 'No description'
            })
        
        return info