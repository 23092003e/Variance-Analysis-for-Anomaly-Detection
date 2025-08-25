#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import sys
import json

def main():
    try:
        # Read GL sheet
        file_path = r"C:\Users\ADMIN\Desktop\Variance-Analysis-for-Anomaly-Detection\data\raw\DAL_May'25_example.xlsx"
        
        print("Reading GL sheet...")
        gl_data = pd.read_excel(file_path, sheet_name='GL', header=None, nrows=10)
        
        print("GL Sheet raw data (first 10 rows):")
        print(gl_data)
        
        print("\nLooking for header row...")
        # Try to find where the actual headers are
        for idx, row in gl_data.iterrows():
            row_values = row.dropna().astype(str).str.lower()
            if any('account' in val or 'code' in val for val in row_values):
                print(f"Potential header row at index {idx}: {list(row.dropna())}")
            if any('subsidiary' in val or 'entity' in val or 'company' in val for val in row_values):
                print(f"Found subsidiary-related headers at row {idx}: {list(row.dropna())}")
        
        print("\nReading TB sheet...")
        tb_data = pd.read_excel(file_path, sheet_name='TB', header=None, nrows=10)
        
        print("\nTB Sheet raw data:")
        print(tb_data)
        
        print("\nLooking for TB header row...")
        for idx, row in tb_data.iterrows():
            row_values = row.dropna().astype(str).str.lower()
            if any('account' in val or 'code' in val for val in row_values):
                print(f"Potential header row at index {idx}: {list(row.dropna())}")
            if any('subsidiary' in val or 'entity' in val or 'company' in val for val in row_values):
                print(f"Found subsidiary-related headers at row {idx}: {list(row.dropna())}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()