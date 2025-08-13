#!/usr/bin/env python3
"""
Create sample financial data for testing the variance analysis system.
"""

import pandas as pd
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def create_sample_data():
    """Create sample financial data Excel file."""
    
    # Sample Balance Sheet Data
    balance_sheet_data = {
        'Account Code': [
            '217000001', '217000006', '112227001', '112227002', 
            '131100001', '138900003', '133100001', '341160000', 
            '341160001', '213100001'
        ],
        'Account Name': [
            'Investment Properties: Land Use Rights',
            'Investment Properties: Office Building', 
            'ACB: Current Account USD - HCM',
            'ACB: Current Account USD - HCM 2',
            'Trade Receivable: Tenant',
            'Unbilled Revenue Receivables',
            'VAT Deductible',
            'LT: Borrowings: Subsidiaries/Parents',
            'LT: Borrowings: Subsidiaries/Parents 2',
            'Unearned Revenue'
        ],
        'Mar_2025': [
            50000000000, 30000000000, 15000000000, 5000000000,
            8000000000, 2000000000, 1500000000, 25000000000,
            15000000000, 3000000000
        ],
        'Apr_2025': [
            52000000000, 31000000000, 14000000000, 5200000000,
            8500000000, 2200000000, 1600000000, 25500000000,
            15300000000, 3200000000
        ],
        'May_2025': [
            55000000000, 32000000000, 16000000000, 4800000000,
            7500000000, 2500000000, 1800000000, 26000000000,
            15500000000, 3500000000
        ]
    }
    
    # Sample Income Statement Data  
    income_statement_data = {
        'Account Code': [
            '511100001', '511100002', '515100001', '515600000',
            '632100001', '632100002', '635000005', '635000006',
            '622000001', '622000002', '641100001'
        ],
        'Account Name': [
            'Rental Revenue',
            'Service Revenue', 
            'Financial Income: Interest',
            'Financial Income: BCC Interest',
            'Expense Amortization: Land Use Rights',
            'Expense Amortization: Building',
            'Financial Expenses: Loan Interest - Parent/Subsi',
            'Financial Expenses: Loan Interest - Bank',
            'Operating Expenses: Insurance',
            'Operating Expenses: Utilities',
            'FX Gain/Loss'
        ],
        'Mar_2025': [
            5000000000, 1500000000, 150000000, 100000000,
            500000000, 300000000, 250000000, 180000000,
            200000000, 350000000, 50000000
        ],
        'Apr_2025': [
            5200000000, 1600000000, 140000000, 105000000,
            520000000, 310000000, 255000000, 185000000,
            210000000, 360000000, -25000000
        ],
        'May_2025': [
            5500000000, 1700000000, 160000000, 110000000,
            525000000, 315000000, 260000000, 190000000,
            220000000, 380000000, -75000000
        ]
    }
    
    # Create DataFrames
    bs_df = pd.DataFrame(balance_sheet_data)
    is_df = pd.DataFrame(income_statement_data)
    
    # Create Excel file
    output_path = Path(__file__).parent.parent / "data" / "raw" / "sample_financial_data.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        bs_df.to_excel(writer, sheet_name='Balance Sheet', index=False)
        is_df.to_excel(writer, sheet_name='Income Statement', index=False)
    
    print(f"Sample data created: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    create_sample_data()