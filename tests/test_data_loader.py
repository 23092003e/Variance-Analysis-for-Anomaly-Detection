"""
Unit tests for DataLoader.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import Settings
from data.loader import DataLoader
from data.models import FinancialData


class TestDataLoader:
    """Test cases for DataLoader."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def loader(self, settings):
        """Create DataLoader instance."""
        return DataLoader(settings)
    
    @pytest.fixture
    def sample_excel_data(self):
        """Create sample Excel data structure."""
        balance_sheet = pd.DataFrame({
            'Account Code': ['217000001', '112227001', '341160000'],
            'Account Name': ['Investment Properties', 'Cash Deposits', 'Borrowings'],
            'Mar_2025': [1000000, 500000, 800000],
            'Apr_2025': [1050000, 480000, 820000],
            'May_2025': [1100000, 520000, 840000]
        })
        
        income_statement = pd.DataFrame({
            'Account Code': ['632100001', '511100001', '635000005'],
            'Account Name': ['Depreciation', 'Revenue', 'Interest Expense'],
            'Mar_2025': [50000, 200000, 8000],
            'Apr_2025': [52000, 210000, 8200],
            'May_2025': [54000, 220000, 8400]
        })
        
        return {
            'Balance Sheet': balance_sheet,
            'Income Statement': income_statement
        }
    
    def test_standardize_dataframe(self, loader):
        """Test dataframe standardization."""
        df = pd.DataFrame({
            'Account Code': ['217000001', '112227001'],
            'Account Name': ['Investment Properties', 'Cash'],
            'Mar_2025': [1000000, 500000]
        })
        
        standardized = loader._standardize_dataframe(df, 'BS')
        
        assert 'account_code' in standardized.columns
        assert 'account_name' in standardized.columns
        assert 'statement_type' in standardized.columns
        assert standardized['statement_type'].iloc[0] == 'BS'
        
        # Check data cleaning
        assert standardized['account_code'].dtype == 'object'
        assert len(standardized) == 2
    
    def test_find_account_column(self, loader):
        """Test account column detection."""
        df1 = pd.DataFrame({'Account Code': [1, 2], 'Name': ['A', 'B']})
        df2 = pd.DataFrame({'Code': [1, 2], 'Description': ['A', 'B']})
        df3 = pd.DataFrame({'123456': [1, 2], 'Name': ['A', 'B']})  # Numeric codes as column name
        
        assert loader._find_account_column(df1) == 'Account Code'
        assert loader._find_account_column(df2) == 'Code'
        assert loader._find_account_column(df3) == '123456'
    
    def test_find_name_column(self, loader):
        """Test account name column detection."""
        df1 = pd.DataFrame({'Code': [1, 2], 'Account Name': ['A', 'B']})
        df2 = pd.DataFrame({'Code': [1, 2], 'Description': ['A', 'B']})
        df3 = pd.DataFrame({'Code': [1, 2], 'Name': ['A', 'B']})
        
        assert loader._find_name_column(df1) == 'Account Name'
        assert loader._find_name_column(df2) == 'Description'
        assert loader._find_name_column(df3) == 'Name'
    
    def test_looks_like_balance_sheet(self, loader):
        """Test balance sheet detection."""
        bs_df = pd.DataFrame({
            'Account': ['Assets', 'Cash', 'Liabilities', 'Equity'],
            'Value': [1000, 500, 600, 400]
        })
        
        is_df = pd.DataFrame({
            'Account': ['Revenue', 'Expenses', 'Income'],
            'Value': [1000, 800, 200]
        })
        
        assert loader._looks_like_balance_sheet(bs_df) == True
        assert loader._looks_like_balance_sheet(is_df) == False
    
    def test_looks_like_income_statement(self, loader):
        """Test income statement detection."""
        is_df = pd.DataFrame({
            'Account': ['Revenue', 'Expenses', 'Income'],
            'Value': [1000, 800, 200]
        })
        
        bs_df = pd.DataFrame({
            'Account': ['Assets', 'Cash', 'Liabilities'],
            'Value': [1000, 500, 600]
        })
        
        assert loader._looks_like_income_statement(is_df) == True
        assert loader._looks_like_income_statement(bs_df) == False
    
    def test_extract_periods(self, loader):
        """Test period extraction from data."""
        df = pd.DataFrame({
            'Account': ['A', 'B'],
            'Mar_2025': [100, 200],
            'Apr_2025': [110, 210],
            'May_2025': [120, 220]
        })
        
        periods = loader._extract_periods(df, df)
        
        # Should extract periods from column names
        assert len(periods) >= 2  # At least current and previous
        assert isinstance(periods, list)
    
    def test_extract_subsidiaries(self, loader):
        """Test subsidiary extraction from data."""
        df = pd.DataFrame({
            'Account': ['A', 'B'],
            'Company': ['Entity 1', 'Entity 2'],
            'Value': [100, 200]
        })
        
        subsidiaries = loader._extract_subsidiaries(df, df)
        
        assert isinstance(subsidiaries, list)
        assert len(subsidiaries) >= 1
    
    @patch('pandas.read_excel')
    def test_load_excel_file_success(self, mock_read_excel, loader, sample_excel_data):
        """Test successful Excel file loading."""
        mock_read_excel.return_value = sample_excel_data
        
        with patch('pathlib.Path.exists', return_value=True):
            financial_data = loader.load_excel_file('test.xlsx')
        
        assert isinstance(financial_data, FinancialData)
        assert not financial_data.balance_sheet.empty
        assert not financial_data.income_statement.empty
        assert len(financial_data.periods) > 0
        assert len(financial_data.subsidiaries) > 0
    
    def test_load_excel_file_not_found(self, loader):
        """Test handling of missing Excel file."""
        with pytest.raises(FileNotFoundError):
            loader.load_excel_file('nonexistent.xlsx')
    
    @patch('pandas.read_excel')
    def test_load_excel_file_no_balance_sheet(self, mock_read_excel, loader):
        """Test handling when no balance sheet is found."""
        mock_read_excel.return_value = {
            'Some Sheet': pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(ValueError, match="No balance sheet data found"):
                loader.load_excel_file('test.xlsx')
    
    @patch('pandas.read_excel')
    def test_load_excel_file_no_income_statement(self, mock_read_excel, loader):
        """Test handling when no income statement is found."""
        balance_sheet = pd.DataFrame({
            'Account Code': ['217000001'],
            'Account Name': ['Investment Properties'],
            'Mar_2025': [1000000]
        })
        
        mock_read_excel.return_value = {
            'Balance Sheet': balance_sheet
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(loader, '_looks_like_balance_sheet', return_value=True):
                with pytest.raises(ValueError, match="No income statement data found"):
                    loader.load_excel_file('test.xlsx')
    
    def test_validate_data_success(self, loader, settings):
        """Test data validation success."""
        balance_sheet = pd.DataFrame({
            'account_code': ['217000001', '112227001'],
            'account_name': ['Investment Properties', 'Cash'],
            'statement_type': ['BS', 'BS'],
            'Mar_2025': [1000000, 500000],
            'Apr_2025': [1050000, 480000]
        })
        
        income_statement = pd.DataFrame({
            'account_code': ['632100001', '511100001'],
            'account_name': ['Depreciation', 'Revenue'],
            'statement_type': ['IS', 'IS'],
            'Mar_2025': [50000, 200000],
            'Apr_2025': [52000, 210000]
        })
        
        financial_data = FinancialData(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            periods=['Mar_2025', 'Apr_2025'],
            subsidiaries=['Test Entity'],
            metadata={'file_path': 'test.xlsx'}
        )
        
        assert loader.validate_data(financial_data) == True
    
    def test_validate_data_empty_dataframes(self, loader):
        """Test data validation with empty dataframes."""
        financial_data = FinancialData(
            balance_sheet=pd.DataFrame(),
            income_statement=pd.DataFrame(),
            periods=[],
            subsidiaries=[],
            metadata={}
        )
        
        assert loader.validate_data(financial_data) == False
    
    def test_validate_data_missing_columns(self, loader):
        """Test data validation with missing required columns."""
        balance_sheet = pd.DataFrame({
            'account_code': ['217000001'],
            # Missing 'account_name' column
            'Mar_2025': [1000000]
        })
        
        income_statement = pd.DataFrame({
            'account_code': ['632100001'],
            'account_name': ['Depreciation'],
            'Mar_2025': [50000]
        })
        
        financial_data = FinancialData(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            periods=['Mar_2025'],
            subsidiaries=['Test'],
            metadata={}
        )
        
        assert loader.validate_data(financial_data) == False