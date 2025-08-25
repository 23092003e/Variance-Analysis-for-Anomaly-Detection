import pandas as pd
import re
import sys
from typing import List, Tuple, Dict, Any

class ExcelValidator:
    def __init__(self, file_path: str, sheet_name: str = "Anomalies Summary"):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.required_columns = [
            "Subsidiary", "Account", "Period", "Pct Change", 
            "Absolute Change (VND)", "Trigger(s)", "Suggested likely cause", 
            "Status", "Notes"
        ]
        self.errors = []
        self.warnings = []
        
    def validate_excel(self) -> Dict[str, Any]:
        """Main validation method that runs all checks"""
        results = {
            "file_path": self.file_path,
            "sheet_name": self.sheet_name,
            "column_errors": [],
            "subsidiary_errors": [],
            "filtered_accounts": [],
            "duplicate_records": [],
            "total_rows": 0,
            "valid_rows": 0
        }
        
        try:
            # Load Excel file
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            results["total_rows"] = len(df)
            
            # 1. Validate columns
            column_errors = self._validate_columns(df)
            results["column_errors"] = column_errors
            
            if column_errors:
                return results
            
            # 2. Validate Subsidiary values
            subsidiary_errors = self._validate_subsidiary(df)
            results["subsidiary_errors"] = subsidiary_errors
            
            # 3. Filter invalid rows
            filtered_df, filtered_accounts = self._filter_invalid_rows(df)
            results["filtered_accounts"] = filtered_accounts
            results["valid_rows"] = len(filtered_df)
            
            # 4. Check for duplicates
            duplicates = self._check_duplicates(filtered_df)
            results["duplicate_records"] = duplicates
            
            return results
            
        except FileNotFoundError:
            results["column_errors"].append(f"File not found: {self.file_path}")
            return results
        except Exception as e:
            results["column_errors"].append(f"Error reading file: {str(e)}")
            return results
    
    def _validate_columns(self, df: pd.DataFrame) -> List[str]:
        """Validate column names and order"""
        errors = []
        
        if list(df.columns) != self.required_columns:
            errors.append("Column structure mismatch")
            errors.append(f"Expected: {self.required_columns}")
            errors.append(f"Found: {list(df.columns)}")
            
            # Check missing columns
            missing = set(self.required_columns) - set(df.columns)
            if missing:
                errors.append(f"Missing columns: {list(missing)}")
            
            # Check extra columns
            extra = set(df.columns) - set(self.required_columns)
            if extra:
                errors.append(f"Extra columns: {list(extra)}")
                
        return errors
    
    def _validate_subsidiary(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Validate Subsidiary column - all values must be 'DAL'"""
        errors = []
        
        if "Subsidiary" not in df.columns:
            return errors
            
        invalid_subsidiaries = df[df["Subsidiary"] != "DAL"]
        
        for idx, row in invalid_subsidiaries.iterrows():
            errors.append({
                "row": idx + 2,  # Excel row number (1-indexed + header)
                "account": row.get("Account", "N/A"),
                "period": row.get("Period", "N/A"),
                "subsidiary_value": row["Subsidiary"]
            })
            
        return errors
    
    def _filter_invalid_rows(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Filter out invalid rows based on Account patterns"""
        filtered_accounts = []
        
        if "Account" not in df.columns:
            return df, filtered_accounts
        
        def is_invalid_account(account_value):
            if pd.isna(account_value):
                return False
                
            account_str = str(account_value).strip()
            
            # Check for pure Roman numerals at the beginning followed by dot and space/end
            # Examples: "I.", "II.", "III.", "IV.", "V.", "VI.", etc.
            roman_pattern = r'^(I{1,3}V?|IV|V|VI{0,3}|IX|X{1,3}L?|XL|L|LX{0,3}|XC|C{1,3}D?|CD|D|DC{0,3}|CM|M+)\.'
            if re.match(roman_pattern, account_str, re.IGNORECASE):
                return True
            
            # Check for single capital letters followed by space, dot, dash, or end (A, B, C, D, E, etc.)
            # But NOT if it's part of a longer word like "G&A:"
            single_letter_pattern = r'^[A-Z](\s|-\s|$)'
            if re.match(single_letter_pattern, account_str) and not re.match(r'^[A-Z]&', account_str):
                return True
            
            # Check for section markers like "A - SOMETHING", "B - SOMETHING", etc.
            section_pattern = r'^[A-Z]\s*-\s*[A-Z][A-Z\s]+$'
            if re.match(section_pattern, account_str, re.IGNORECASE):
                return True
            
            # Check for subtotal/total patterns
            subtotal_patterns = [
                r'\btotal\b', r'\bsubtotal\b', r'\bsum\b', r'\bgrand total\b'
            ]
            for pattern in subtotal_patterns:
                if re.search(pattern, account_str, re.IGNORECASE):
                    return True
            
            return False
        
        # Identify invalid rows
        invalid_mask = df["Account"].apply(is_invalid_account)
        invalid_rows = df[invalid_mask]
        
        # Record filtered accounts
        for idx, row in invalid_rows.iterrows():
            filtered_accounts.append({
                "row": idx + 2,  # Excel row number
                "account": row["Account"],
                "period": row.get("Period", "N/A"),
                "reason": self._get_filter_reason(str(row["Account"]).strip())
            })
        
        # Return filtered dataframe
        valid_df = df[~invalid_mask].copy()
        return valid_df, filtered_accounts
    
    def _get_filter_reason(self, account: str) -> str:
        """Determine why an account was filtered"""
        # Check for pure Roman numerals at the beginning followed by dot
        roman_pattern = r'^(I{1,3}V?|IV|V|VI{0,3}|IX|X{1,3}L?|XL|L|LX{0,3}|XC|C{1,3}D?|CD|D|DC{0,3}|CM|M+)\.'
        if re.match(roman_pattern, account, re.IGNORECASE):
            return "Roman numeral pattern"
        elif re.match(r'^[A-Z](\s|-\s|$)', account) and not re.match(r'^[A-Z]&', account):
            return "Single capital letter"
        elif re.match(r'^[A-Z]\s*-\s*[A-Z][A-Z\s]+$', account, re.IGNORECASE):
            return "Section marker pattern"
        elif any(re.search(pattern, account, re.IGNORECASE) for pattern in 
                [r'\btotal\b', r'\bsubtotal\b', r'\bsum\b', r'\bgrand total\b']):
            return "Subtotal/Total pattern"
        else:
            return "Other pattern"
    
    def _check_duplicates(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check for duplicate records based on Subsidiary, Account, Period"""
        duplicates = []
        
        if len(df) == 0:
            return duplicates
        
        key_columns = ["Subsidiary", "Account", "Period"]
        
        # Check if all key columns exist
        missing_cols = [col for col in key_columns if col not in df.columns]
        if missing_cols:
            return duplicates
        
        # Find duplicates
        duplicate_mask = df.duplicated(subset=key_columns, keep=False)
        duplicate_rows = df[duplicate_mask]
        
        if len(duplicate_rows) > 0:
            # Group duplicates
            grouped = duplicate_rows.groupby(key_columns)
            
            for (subsidiary, account, period), group in grouped:
                duplicate_info = {
                    "subsidiary": subsidiary,
                    "account": account,
                    "period": period,
                    "occurrences": len(group),
                    "rows": [idx + 2 for idx in group.index]  # Excel row numbers
                }
                duplicates.append(duplicate_info)
        
        return duplicates
    
    def print_report(self, results: Dict[str, Any]):
        """Print comprehensive validation report"""
        print("=" * 60)
        print(f"EXCEL VALIDATION REPORT")
        print("=" * 60)
        print(f"File: {results['file_path']}")
        print(f"Sheet: {results['sheet_name']}")
        print(f"Total rows: {results['total_rows']}")
        print(f"Valid rows after filtering: {results['valid_rows']}")
        print()
        
        # Column format errors
        if results['column_errors']:
            print("🔴 COLUMN FORMAT ERRORS:")
            for error in results['column_errors']:
                print(f"  - {error}")
            print()
        else:
            print("✅ Column format: OK")
            print()
        
        # Subsidiary errors
        if results['subsidiary_errors']:
            print(f"🔴 SUBSIDIARY VALIDATION ERRORS ({len(results['subsidiary_errors'])}):")
            for error in results['subsidiary_errors']:
                print(f"  - Row {error['row']}: Account '{error['account']}', "
                      f"Period '{error['period']}', Subsidiary '{error['subsidiary_value']}' (should be 'DAL')")
            print()
        else:
            print("✅ Subsidiary validation: OK")
            print()
        
        # Filtered accounts
        if results['filtered_accounts']:
            print(f"🟡 FILTERED ACCOUNTS ({len(results['filtered_accounts'])}):")
            for filtered in results['filtered_accounts']:
                print(f"  - Row {filtered['row']}: Account '{filtered['account']}', "
                      f"Period '{filtered['period']}', Reason: {filtered['reason']}")
            print()
        else:
            print("✅ No accounts filtered")
            print()
        
        # Duplicate records
        if results['duplicate_records']:
            print(f"🔴 DUPLICATE RECORDS ({len(results['duplicate_records'])}):")
            for dup in results['duplicate_records']:
                print(f"  - Subsidiary: '{dup['subsidiary']}', Account: '{dup['account']}', "
                      f"Period: '{dup['period']}' appears {dup['occurrences']} times in rows: {dup['rows']}")
            print()
        else:
            print("✅ No duplicates found")
            print()
        
        # Summary
        total_issues = len(results['column_errors']) + len(results['subsidiary_errors']) + len(results['duplicate_records'])
        if total_issues == 0:
            print("🎉 VALIDATION PASSED - No critical errors found!")
        else:
            print(f"❌ VALIDATION FAILED - {total_issues} critical issues found")
        
        print("=" * 60)

def main():
    if len(sys.argv) != 2:
        print("Usage: python excel_validator.py <excel_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    validator = ExcelValidator(file_path)
    results = validator.validate_excel()
    validator.print_report(results)

if __name__ == "__main__":
    main()