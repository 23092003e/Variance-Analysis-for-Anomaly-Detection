"""
Excel formatting utilities for conditional formatting and styling.
"""

import xlsxwriter
import pandas as pd
from typing import Dict, Any


class ExcelFormatter:
    """Excel formatting utilities for variance analysis reports."""
    
    def __init__(self):
        self.formats = {}
    
    def add_formats(self, workbook: xlsxwriter.Workbook) -> None:
        """Add standard formats to workbook."""
        self.formats = {
            'header': workbook.add_format({
                'bold': True,
                'bg_color': '#4472c4',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            }),
            'critical': workbook.add_format({
                'bg_color': '#ff4d4d',
                'font_color': 'white',
                'bold': True,
                'border': 1
            }),
            'high': workbook.add_format({
                'bg_color': '#ff9999',
                'border': 1
            }),
            'medium': workbook.add_format({
                'bg_color': '#ffff99',
                'border': 1
            }),
            'low': workbook.add_format({
                'bg_color': '#ccffcc',
                'border': 1
            }),
            'normal': workbook.add_format({
                'border': 1
            }),
            'percentage': workbook.add_format({
                'num_format': '0.0%',
                'border': 1
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0',
                'border': 1
            }),
            'positive_variance': workbook.add_format({
                'bg_color': '#e6ffe6',
                'num_format': '0.0%',
                'border': 1
            }),
            'negative_variance': workbook.add_format({
                'bg_color': '#ffe6e6',
                'num_format': '0.0%',
                'border': 1
            })
        }
    
    def apply_anomaly_formatting(self, worksheet: xlsxwriter.worksheet.Worksheet,
                                df: pd.DataFrame, start_row: int = 1) -> None:
        """Apply conditional formatting to anomalies summary sheet."""
        if len(df) == 0:
            return
        
        # Define the range for data (excluding headers)
        last_row = start_row + len(df)
        last_col = len(df.columns) - 1
        
        # Severity-based row formatting
        for i, (_, row) in enumerate(df.iterrows()):
            row_num = start_row + i
            severity = row['Severity'].lower()
            
            if severity == 'critical':
                format_style = self.formats['critical']
            elif severity == 'high':
                format_style = self.formats['high']
            elif severity == 'medium':
                format_style = self.formats['medium']
            else:
                format_style = self.formats['low']
            
            # Apply format to entire row
            for col in range(len(df.columns)):
                cell_value = row.iloc[col]
                if col in [6, 7]:  # Current/Previous Value columns
                    worksheet.write(row_num, col, cell_value, self.formats['currency'])
                elif col == 8:  # Variance % column
                    if pd.notna(cell_value):
                        worksheet.write(row_num, col, cell_value / 100, self.formats['percentage'])
                    else:
                        worksheet.write(row_num, col, '', format_style)
                else:
                    worksheet.write(row_num, col, cell_value, format_style)
    
    def apply_variance_formatting(self, worksheet: xlsxwriter.worksheet.Worksheet,
                                df: pd.DataFrame, start_row: int = 1) -> None:
        """Apply conditional formatting to variance analysis sheet."""
        if len(df) == 0:
            return
        
        # Format current and previous value columns as currency
        for i, (_, row) in enumerate(df.iterrows()):
            row_num = start_row + i
            
            # Current Value (column 6)
            worksheet.write(row_num, 6, row['Current Value'], self.formats['currency'])
            
            # Previous Value (column 7)
            worksheet.write(row_num, 7, row['Previous Value'], self.formats['currency'])
            
            # Variance Amount (column 8)
            worksheet.write(row_num, 8, row['Variance Amount'], self.formats['currency'])
            
            # Variance % (column 9) - conditional formatting based on value
            variance_pct = row['Variance %']
            if pd.notna(variance_pct):
                if abs(variance_pct) >= 10:
                    format_style = self.formats['critical']
                elif abs(variance_pct) >= 5:
                    format_style = self.formats['high']
                elif variance_pct > 0:
                    format_style = self.formats['positive_variance']
                else:
                    format_style = self.formats['negative_variance']
                
                worksheet.write(row_num, 9, variance_pct / 100, format_style)
            
            # Significant column (column 10)
            is_significant = row['Significant']
            if is_significant == 'YES':
                worksheet.write(row_num, 10, is_significant, self.formats['high'])
            else:
                worksheet.write(row_num, 10, is_significant, self.formats['normal'])
    
    def apply_correlation_formatting(self, worksheet: xlsxwriter.worksheet.Worksheet,
                                   df: pd.DataFrame, start_row: int = 1) -> None:
        """Apply conditional formatting to correlation violations sheet."""
        if len(df) == 0:
            return
        
        for i, (_, row) in enumerate(df.iterrows()):
            row_num = start_row + i
            severity = row['Severity'].lower()
            
            # Apply severity-based formatting to severity column
            if severity == 'high':
                format_style = self.formats['critical']
            elif severity == 'medium':
                format_style = self.formats['high']
            else:
                format_style = self.formats['medium']
            
            # Apply formatting to the entire row
            for col in range(len(df.columns)):
                cell_value = row.iloc[col]
                if col in [4, 5]:  # Variance percentage columns
                    if pd.notna(cell_value):
                        worksheet.write(row_num, col, cell_value / 100, self.formats['percentage'])
                    else:
                        worksheet.write(row_num, col, '', format_style)
                elif col == 8:  # Severity column
                    worksheet.write(row_num, col, cell_value, format_style)
                else:
                    worksheet.write(row_num, col, cell_value, self.formats['normal'])
    
    def adjust_column_widths(self, worksheet: xlsxwriter.worksheet.Worksheet,
                           df: pd.DataFrame) -> None:
        """Adjust column widths based on content."""
        for i, column in enumerate(df.columns):
            # Calculate the maximum width needed for this column
            max_length = len(str(column))  # Header length
            
            # Check data lengths
            for value in df.iloc[:, i]:
                if pd.notna(value):
                    max_length = max(max_length, len(str(value)))
            
            # Set a reasonable width (with some padding)
            width = min(max_length + 2, 50)  # Max width of 50
            worksheet.set_column(i, i, width)
    
    def add_data_bars(self, worksheet: xlsxwriter.worksheet.Worksheet,
                     start_row: int, end_row: int, col: int) -> None:
        """Add data bars to a range of cells."""
        worksheet.conditional_format(
            start_row, col, end_row, col,
            {
                'type': 'data_bar',
                'bar_color': '#4472c4',
                'bar_solid': True
            }
        )
    
    def add_color_scale(self, worksheet: xlsxwriter.worksheet.Worksheet,
                       start_row: int, end_row: int, col: int) -> None:
        """Add color scale formatting to a range."""
        worksheet.conditional_format(
            start_row, col, end_row, col,
            {
                'type': '3_color_scale',
                'min_color': '#63be7b',
                'mid_color': '#ffeb84',
                'max_color': '#f87c7c'
            }
        )
    
    def add_icon_set(self, worksheet: xlsxwriter.worksheet.Worksheet,
                    start_row: int, end_row: int, col: int) -> None:
        """Add icon set to indicate status."""
        worksheet.conditional_format(
            start_row, col, end_row, col,
            {
                'type': 'icon_set',
                'icon_style': '3_traffic_lights'
            }
        )