"""
Excel report generation with formatted output and anomaly summary.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import xlsxwriter
from datetime import datetime

from config.settings import Settings
from data.models import FinancialData
from analysis.variance_analyzer import VarianceResult
from analysis.correlation_engine import CorrelationResult
from analysis.anomaly_detector import Anomaly, AnomalySeverity
from reports.formatter import ExcelFormatter


class ExcelGenerator:
    """Excel report generator for variance analysis results."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.formatter = ExcelFormatter()
        self.logger = logging.getLogger(__name__)
    
    def generate_report(self, financial_data: FinancialData,
                       variance_results: List[VarianceResult],
                       correlation_results: List[CorrelationResult],
                       anomalies: List[Anomaly],
                       output_file: str) -> None:
        """
        Generate comprehensive Excel report.
        
        Args:
            financial_data: Original financial data
            variance_results: Variance analysis results
            correlation_results: Correlation analysis results
            anomalies: Detected anomalies
            output_file: Path to output Excel file
        """
        self.logger.info(f"Generating Excel report: {output_file}")
        
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Create workbook and worksheets
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            
            workbook = writer.book
            
            # Add formats
            self.formatter.add_formats(workbook)
            
            # Generate all sheets
            self._create_anomalies_summary_sheet(writer, anomalies)
            self._create_variance_analysis_sheet(writer, variance_results)
            self._create_correlation_violations_sheet(writer, correlation_results)
            self._create_original_data_sheets(writer, financial_data)
            self._create_dashboard_sheet(writer, variance_results, anomalies)
            
        self.logger.info(f"Excel report generated successfully: {output_file}")
    
    def _create_anomalies_summary_sheet(self, writer: pd.ExcelWriter, anomalies: List[Anomaly]) -> None:
        """Create the main Anomalies Summary sheet with enhanced formatting."""
        if not anomalies:
            self.logger.warning("No anomalies found - creating empty summary sheet")
            # Create empty sheet with headers
            empty_data = [{
                'Subsidiary': '',
                'Metric': '',
                'Period': '',
                '% Change': '',
                'Suggested Reason': ''
            }]
            df_summary = pd.DataFrame(empty_data)
        else:
            # Prepare data for anomalies summary matching the required format
            summary_data = []
            for anomaly in anomalies:
                # Extract subsidiary from account name or use account code
                subsidiary = self._extract_subsidiary(anomaly.account_name, anomaly.account_code)
                
                # Create metric description
                metric = f"{anomaly.account_name} ({anomaly.account_code})"
                
                # Format percentage change
                pct_change = f"{anomaly.variance_percent:.1f}%" if anomaly.variance_percent else "N/A"
                
                # Generate suggested reason based on anomaly type and description
                suggested_reason = self._generate_suggested_reason(anomaly)
                
                summary_data.append({
                    'Subsidiary': subsidiary,
                    'Metric': metric,
                    'Period': anomaly.period,
                    '% Change': pct_change,
                    'Suggested Reason': suggested_reason,
                    'Severity': anomaly.severity.value.upper(),
                    'Type': anomaly.type.value.replace('_', ' ').title(),
                    'Current Value': anomaly.current_value,
                    'Previous Value': anomaly.previous_value or 0,
                    'Variance Amount': anomaly.current_value - (anomaly.previous_value or 0),
                    'Category': anomaly.category.replace('_', ' ').title(),
                    'Recommended Action': anomaly.recommended_action
                })
            
            df_summary = pd.DataFrame(summary_data)
        
        # Write to Excel
        sheet_name = 'Anomalies Summary'
        df_summary.to_excel(writer, sheet_name=sheet_name, index=False, startrow=3)
        
        worksheet = writer.sheets[sheet_name]
        workbook = writer.book
        
        # Add main title
        title_format = workbook.add_format({
            'bold': True, 'font_size': 18, 'align': 'center',
            'bg_color': '#1f4e79', 'font_color': 'white'
        })
        worksheet.merge_range('A1:L1', 'VARIANCE ANALYSIS - ANOMALIES SUMMARY', title_format)
        
        # Add subtitle with key information
        subtitle_format = workbook.add_format({
            'italic': True, 'font_size': 11, 'align': 'center', 'bg_color': '#e7edf3'
        })
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        critical_count = sum(1 for a in anomalies if a.severity.value == 'critical')
        high_count = sum(1 for a in anomalies if a.severity.value == 'high')
        
        subtitle_text = f'Generated: {timestamp} | Total Anomalies: {len(anomalies)} | Critical: {critical_count} | High Priority: {high_count}'
        worksheet.merge_range('A2:L2', subtitle_text, subtitle_format)
        
        # Add instructions
        instruction_format = workbook.add_format({
            'font_size': 9, 'italic': True, 'align': 'left'
        })
        worksheet.merge_range('A3:L3', 'Instructions: Critical and High severity items require immediate attention. Review suggested reasons and take recommended actions.', instruction_format)
        
        # Apply conditional formatting
        if len(df_summary) > 0:
            self.formatter.apply_anomaly_formatting(worksheet, df_summary, start_row=4)
            
            # Add data bars for variance percentages
            if 'Variance Amount' in df_summary.columns:
                variance_col = df_summary.columns.get_loc('Variance Amount')
                self.formatter.add_data_bars(worksheet, 4, 4 + len(df_summary) - 1, variance_col)
        
        # Adjust column widths
        self.formatter.adjust_column_widths(worksheet, df_summary)
        
        # Freeze panes for better navigation
        worksheet.freeze_panes(4, 0)
        
    def _extract_subsidiary(self, account_name: str, account_code: str) -> str:
        """Extract subsidiary name from account information."""
        # Simple logic to determine subsidiary - can be enhanced based on actual data structure
        if 'subsidiary' in account_name.lower() or 'parent' in account_name.lower():
            return account_name.split(':')[0] if ':' in account_name else 'Parent Company'
        elif 'shl' in account_name.lower():
            return 'SHL Subsidiary'
        elif 'hcm' in account_name.lower():
            return 'HCM Operations'
        else:
            return 'Main Entity'
    
    def _generate_suggested_reason(self, anomaly: Anomaly) -> str:
        """Generate suggested reason based on anomaly characteristics."""
        if anomaly.type.value == 'variance':
            if 'depreciation' in anomaly.category.lower():
                return 'Asset additions, disposals, or depreciation method changes'
            elif 'revenue' in anomaly.category.lower():
                return 'Occupancy changes, lease modifications, or billing timing differences'
            elif 'cash' in anomaly.category.lower():
                return 'Operational cash flow changes or collection timing'
            elif 'borrowings' in anomaly.category.lower():
                return 'New loans, repayments, or refinancing activities'
            elif 'interest' in anomaly.category.lower():
                return 'Interest rate changes or principal balance fluctuations'
            else:
                return 'Operational changes or accounting adjustments'
        elif anomaly.type.value == 'correlation_violation':
            return f'Correlation rule violation: {anomaly.rule_violated}'
        elif anomaly.type.value == 'sign_change':
            return 'Account sign change - verify data accuracy and business events'
        elif anomaly.type.value == 'recurring_spike':
            return 'Unusual variance in normally stable account - investigate underlying causes'
        elif anomaly.type.value == 'quarterly_pattern':
            return 'Deviation from expected quarterly pattern - check billing cycles and revenue recognition'
        else:
            return 'Review business operations and accounting treatments'
    
    def _create_variance_analysis_sheet(self, writer: pd.ExcelWriter, 
                                      variance_results: List[VarianceResult]) -> None:
        """Create detailed variance analysis sheet."""
        variance_data = []
        for result in variance_results:
            variance_data.append({
                'Account Code': result.account_code,
                'Account Name': result.account_name,
                'Category': result.category,
                'Statement': result.statement_type,
                'Current Period': result.period_to,
                'Previous Period': result.period_from,
                'Current Value': result.current_value,
                'Previous Value': result.previous_value,
                'Variance Amount': result.variance_amount,
                'Variance %': result.variance_percent,
                'Significant': 'YES' if result.is_significant else 'NO'
            })
        
        df_variance = pd.DataFrame(variance_data)
        
        sheet_name = 'Variance Analysis'
        df_variance.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
        
        worksheet = writer.sheets[sheet_name]
        workbook = writer.book
        
        # Add title
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center',
            'bg_color': '#2f75b5', 'font_color': 'white'
        })
        worksheet.merge_range('A1:K1', 'DETAILED VARIANCE ANALYSIS', title_format)
        
        # Apply conditional formatting for significant variances
        if len(df_variance) > 0:
            self.formatter.apply_variance_formatting(worksheet, df_variance, start_row=2)
        
        # Adjust column widths
        self.formatter.adjust_column_widths(worksheet, df_variance)
    
    def _create_correlation_violations_sheet(self, writer: pd.ExcelWriter,
                                           correlation_results: List[CorrelationResult]) -> None:
        """Create correlation violations sheet."""
        correlation_data = []
        for result in correlation_results:
            if result.is_violation:
                correlation_data.append({
                    'Rule ID': result.rule_id,
                    'Rule Name': result.rule_name,
                    'Primary Account': result.primary_account,
                    'Correlated Account': result.correlated_account,
                    'Primary Variance %': result.primary_variance,
                    'Correlated Variance %': result.correlated_variance,
                    'Expected Relationship': result.expected_relationship.value,
                    'Violation Description': result.violation_description,
                    'Severity': result.severity.upper()
                })
        
        df_correlation = pd.DataFrame(correlation_data)
        
        sheet_name = 'Correlation Violations'
        df_correlation.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
        
        worksheet = writer.sheets[sheet_name]
        workbook = writer.book
        
        # Add title
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center',
            'bg_color': '#c55a11', 'font_color': 'white'
        })
        worksheet.merge_range('A1:I1', 'CORRELATION RULE VIOLATIONS', title_format)
        
        # Apply conditional formatting
        if len(df_correlation) > 0:
            self.formatter.apply_correlation_formatting(worksheet, df_correlation, start_row=2)
        
        # Adjust column widths
        self.formatter.adjust_column_widths(worksheet, df_correlation)
    
    def _create_original_data_sheets(self, writer: pd.ExcelWriter, financial_data: FinancialData) -> None:
        """Create sheets with original data for reference."""
        # Balance Sheet
        bs_sheet = 'Original Balance Sheet'
        financial_data.balance_sheet.to_excel(writer, sheet_name=bs_sheet, index=False)
        
        # Income Statement
        is_sheet = 'Original Income Statement'
        financial_data.income_statement.to_excel(writer, sheet_name=is_sheet, index=False)
        
        # Format headers for both sheets
        for sheet_name in [bs_sheet, is_sheet]:
            worksheet = writer.sheets[sheet_name]
            workbook = writer.book
            
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#4472c4', 'font_color': 'white',
                'align': 'center', 'valign': 'vcenter'
            })
            
            # Apply header formatting
            for col_num, column in enumerate(financial_data.balance_sheet.columns 
                                           if sheet_name == bs_sheet 
                                           else financial_data.income_statement.columns):
                worksheet.write(0, col_num, column, header_format)
    
    def _create_dashboard_sheet(self, writer: pd.ExcelWriter, 
                              variance_results: List[VarianceResult],
                              anomalies: List[Anomaly]) -> None:
        """Create a dashboard summary sheet."""
        workbook = writer.book
        worksheet = workbook.add_worksheet('Dashboard')
        
        # Title
        title_format = workbook.add_format({
            'bold': True, 'font_size': 18, 'align': 'center',
            'bg_color': '#1f4e79', 'font_color': 'white'
        })
        worksheet.merge_range('A1:F1', 'VARIANCE ANALYSIS DASHBOARD', title_format)
        
        # Summary statistics
        total_accounts = len(variance_results)
        significant_variances = sum(1 for v in variance_results if v.is_significant)
        critical_anomalies = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        high_anomalies = sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH)
        
        # Statistics table
        stats_data = [
            ['Metric', 'Value', 'Status'],
            ['Total Accounts Analyzed', total_accounts, ''],
            ['Significant Variances', significant_variances, 'WARNING' if significant_variances > total_accounts * 0.1 else 'OK'],
            ['Critical Anomalies', critical_anomalies, 'URGENT' if critical_anomalies > 0 else 'OK'],
            ['High Priority Anomalies', high_anomalies, 'REVIEW' if high_anomalies > 0 else 'OK'],
            ['Total Anomalies', len(anomalies), '']
        ]
        
        # Write statistics
        row = 3
        for row_data in stats_data:
            for col, value in enumerate(row_data):
                if row == 3:  # Header
                    format_style = workbook.add_format({'bold': True, 'bg_color': '#d9e1f2'})
                else:
                    format_style = workbook.add_format()
                worksheet.write(row, col, value, format_style)
            row += 1
        
        # Top 10 variances
        worksheet.write(row + 2, 0, 'TOP 10 VARIANCES BY PERCENTAGE', 
                       workbook.add_format({'bold': True, 'font_size': 12}))
        
        top_variances = sorted(variance_results, 
                             key=lambda x: abs(x.variance_percent), reverse=True)[:10]
        
        headers = ['Account Code', 'Account Name', 'Variance %', 'Amount']
        for col, header in enumerate(headers):
            worksheet.write(row + 3, col, header, 
                          workbook.add_format({'bold': True, 'bg_color': '#d9e1f2'}))
        
        for i, var in enumerate(top_variances):
            worksheet.write(row + 4 + i, 0, var.account_code)
            worksheet.write(row + 4 + i, 1, var.account_name)
            worksheet.write(row + 4 + i, 2, f"{var.variance_percent:.1f}%")
            worksheet.write(row + 4 + i, 3, var.variance_amount)
        
        # Adjust column widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 15)