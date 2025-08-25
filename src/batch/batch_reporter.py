"""
Batch reporting system for generating comprehensive summaries of multi-file processing.
Creates Excel-based dashboard reports for batch analysis results.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import json

logger = logging.getLogger(__name__)


class BatchReporter:
    """
    Generates comprehensive batch processing reports.
    Creates Excel dashboards, summary statistics, and error analysis reports.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_batch_excel_report(self, batch_results: Dict[str, Any], 
                                  output_file: Optional[str] = None) -> str:
        """
        Generate comprehensive Excel report for batch processing results.
        
        Args:
            batch_results: Results from BatchProcessor
            output_file: Optional custom output file path
            
        Returns:
            Path to generated Excel report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"batch_analysis_dashboard_{timestamp}.xlsx"
        
        output_path = Path(output_file)
        self.logger.info(f"Generating batch Excel report: {output_path}")
        
        try:
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                # Create summary dashboard
                self._create_summary_dashboard(writer, workbook, batch_results)
                
                # Create detailed results sheet
                self._create_detailed_results(writer, workbook, batch_results)
                
                # Create error analysis sheet
                self._create_error_analysis(writer, workbook, batch_results)
                
                # Create statistics sheet
                self._create_statistics_sheet(writer, workbook, batch_results)
                
                # Create file size analysis
                self._create_file_analysis(writer, workbook, batch_results)
                
                # Create processing performance sheet
                self._create_performance_analysis(writer, workbook, batch_results)
                
            self.logger.info(f"Batch Excel report generated successfully: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error generating batch Excel report: {e}")
            raise
    
    def _create_summary_dashboard(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create main summary dashboard sheet."""
        worksheet = workbook.add_worksheet('Dashboard')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center'
        })
        
        metric_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center'
        })
        
        value_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'num_format': '0'
        })
        
        percentage_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'num_format': '0.0%'
        })
        
        # Title
        worksheet.merge_range('A1:H1', 'Batch Processing Dashboard', header_format)
        worksheet.write('A2', f"Generated: {batch_results.get('timestamp', 'Unknown')}")
        worksheet.write('A3', f"Input Source: {batch_results.get('input_source', 'Unknown')}")
        
        # Key Metrics
        row = 5
        worksheet.write(row, 0, 'Key Metrics', metric_format)
        
        metrics = [
            ('Total Files Processed', batch_results.get('total_count', 0)),
            ('Successfully Processed', batch_results.get('successful_count', 0)),
            ('Failed Processing', batch_results.get('failed_count', 0)),
            ('Success Rate', batch_results.get('success_rate', 0) / 100),
            ('Total Processing Time (sec)', batch_results.get('total_processing_time', 0)),
            ('Average Time per File (sec)', batch_results.get('average_processing_time', 0))
        ]
        
        for i, (metric, value) in enumerate(metrics):
            worksheet.write(row + 1 + i, 0, metric)
            if 'Rate' in metric:
                worksheet.write(row + 1 + i, 1, value, percentage_format)
            else:
                worksheet.write(row + 1 + i, 1, value, value_format)
        
        # Statistics Summary
        stats = batch_results.get('statistics', {})
        if stats and 'message' not in stats:
            row += 10
            worksheet.write(row, 0, 'File Statistics', metric_format)
            
            # File sizes
            file_stats = stats.get('file_sizes', {})
            if file_stats:
                worksheet.write(row + 1, 0, 'Average File Size (MB)')
                worksheet.write(row + 1, 1, file_stats.get('average', 0), value_format)
                worksheet.write(row + 2, 0, 'Largest File (MB)')
                worksheet.write(row + 2, 1, file_stats.get('max', 0), value_format)
            
            # Anomaly statistics
            anomaly_stats = stats.get('anomaly_counts', {})
            if anomaly_stats:
                worksheet.write(row + 4, 0, 'Total Anomalies Found')
                worksheet.write(row + 4, 1, anomaly_stats.get('total', 0), value_format)
                worksheet.write(row + 5, 0, 'Average per File')
                worksheet.write(row + 5, 1, anomaly_stats.get('average', 0), value_format)
        
        # Auto-adjust column widths
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
    
    def _create_detailed_results(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create detailed results sheet."""
        results = batch_results.get('results', [])
        
        if not results:
            return
        
        # Convert results to DataFrame
        data = []
        for result in results:
            data.append({
                'File Name': Path(result.file_path).name,
                'Success': 'Yes' if result.success else 'No',
                'Processing Time (sec)': result.processing_time,
                'File Size (MB)': result.file_size_mb or 0,
                'Project Type': result.project_type or 'Unknown',
                'Anomalies Found': result.anomaly_count or 0,
                'Variance Count': result.variance_count or 0,
                'Correlation Violations': result.correlation_violations or 0,
                'Output File': Path(result.output_file).name if result.output_file else 'N/A',
                'Error Message': result.error_message or 'None'
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Detailed Results', index=False)
        
        # Format the sheet
        worksheet = writer.sheets['Detailed Results']
        workbook = writer.book
        
        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAD3',
            'border': 1
        })
        
        # Success format
        success_format = workbook.add_format({
            'bg_color': '#D4EDDA',
            'border': 1
        })
        
        # Error format
        error_format = workbook.add_format({
            'bg_color': '#F8D7DA',
            'border': 1
        })
        
        # Apply formats
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Conditional formatting for success/failure
        for row_num in range(1, len(df) + 1):
            success = df.iloc[row_num - 1]['Success']
            format_to_use = success_format if success == 'Yes' else error_format
            
            for col_num in range(len(df.columns)):
                worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], format_to_use)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, min(max_length + 2, 50))
    
    def _create_error_analysis(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create error analysis sheet."""
        errors = batch_results.get('errors', {})
        
        if not errors or 'message' in errors:
            # Create empty sheet with message
            worksheet = workbook.add_worksheet('Error Analysis')
            worksheet.write(0, 0, errors.get('message', 'No errors to analyze'))
            return
        
        # Create error summary data
        error_data = []
        for category, error_list in errors.items():
            for error_info in error_list:
                error_data.append({
                    'Category': category,
                    'File': error_info['file'],
                    'Error Message': error_info['error']
                })
        
        df = pd.DataFrame(error_data)
        df.to_excel(writer, sheet_name='Error Analysis', index=False)
        
        # Create error category summary
        category_summary = df['Category'].value_counts().reset_index()
        category_summary.columns = ['Error Category', 'Count']
        
        # Add to the same sheet, starting from a different position
        start_row = len(df) + 5
        category_summary.to_excel(writer, sheet_name='Error Analysis', 
                                 startrow=start_row, index=False)
        
        # Format the sheet
        worksheet = writer.sheets['Error Analysis']
        worksheet.write(start_row - 2, 0, 'Error Category Summary:', 
                       workbook.add_format({'bold': True, 'font_size': 14}))
    
    def _create_statistics_sheet(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create detailed statistics sheet."""
        stats = batch_results.get('statistics', {})
        
        worksheet = workbook.add_worksheet('Statistics')
        
        if 'message' in stats:
            worksheet.write(0, 0, stats['message'])
            return
        
        row = 0
        
        # File Size Statistics
        file_stats = stats.get('file_sizes', {})
        if file_stats:
            worksheet.write(row, 0, 'File Size Statistics (MB)', 
                           workbook.add_format({'bold': True, 'font_size': 14}))
            row += 1
            
            for key, value in file_stats.items():
                worksheet.write(row, 0, key.title())
                worksheet.write(row, 1, value)
                row += 1
            row += 2
        
        # Anomaly Statistics
        anomaly_stats = stats.get('anomaly_counts', {})
        if anomaly_stats:
            worksheet.write(row, 0, 'Anomaly Statistics', 
                           workbook.add_format({'bold': True, 'font_size': 14}))
            row += 1
            
            for key, value in anomaly_stats.items():
                worksheet.write(row, 0, key.title())
                worksheet.write(row, 1, value)
                row += 1
            row += 2
        
        # Processing Time Statistics
        time_stats = stats.get('processing_times', {})
        if time_stats:
            worksheet.write(row, 0, 'Processing Time Statistics (seconds)', 
                           workbook.add_format({'bold': True, 'font_size': 14}))
            row += 1
            
            for key, value in time_stats.items():
                worksheet.write(row, 0, key.title())
                worksheet.write(row, 1, value)
                row += 1
    
    def _create_file_analysis(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create file-specific analysis sheet."""
        results = batch_results.get('results', [])
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return
        
        # Create file performance data
        file_data = []
        for result in successful_results:
            file_data.append({
                'File Name': Path(result.file_path).name,
                'File Size (MB)': result.file_size_mb or 0,
                'Processing Time (sec)': result.processing_time,
                'Processing Rate (MB/sec)': (result.file_size_mb or 0) / result.processing_time if result.processing_time > 0 else 0,
                'Anomalies Found': result.anomaly_count or 0,
                'Anomaly Density': (result.anomaly_count or 0) / (result.file_size_mb or 1),
                'Project Type': result.project_type or 'Unknown'
            })
        
        df = pd.DataFrame(file_data)
        df.to_excel(writer, sheet_name='File Analysis', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['File Analysis']
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, min(max_length + 2, 30))
    
    def _create_performance_analysis(self, writer: pd.ExcelWriter, workbook, batch_results: Dict[str, Any]):
        """Create processing performance analysis sheet."""
        results = batch_results.get('results', [])
        
        if not results:
            return
        
        # Performance summary
        total_time = batch_results.get('total_processing_time', 0)
        successful_count = batch_results.get('successful_count', 0)
        failed_count = batch_results.get('failed_count', 0)
        
        worksheet = workbook.add_worksheet('Performance Analysis')
        
        # Summary metrics
        row = 0
        worksheet.write(row, 0, 'Performance Summary', 
                       workbook.add_format({'bold': True, 'font_size': 16}))
        row += 2
        
        perf_metrics = [
            ('Total Processing Time', f"{total_time:.2f} seconds"),
            ('Average Time per File', f"{total_time / len(results):.2f} seconds" if results else "N/A"),
            ('Files per Minute', f"{len(results) / (total_time / 60):.1f}" if total_time > 0 else "N/A"),
            ('Success Rate', f"{successful_count / len(results) * 100:.1f}%" if results else "N/A"),
            ('Failure Rate', f"{failed_count / len(results) * 100:.1f}%" if results else "N/A")
        ]
        
        for metric, value in perf_metrics:
            worksheet.write(row, 0, metric)
            worksheet.write(row, 1, value)
            row += 1
        
        # Processing time distribution
        row += 3
        worksheet.write(row, 0, 'Processing Time Distribution', 
                       workbook.add_format({'bold': True, 'font_size': 14}))
        row += 1
        
        # Create buckets for processing times
        times = [r.processing_time for r in results if r.processing_time]
        if times:
            import numpy as np
            
            buckets = [
                ('< 5 seconds', sum(1 for t in times if t < 5)),
                ('5-15 seconds', sum(1 for t in times if 5 <= t < 15)),
                ('15-30 seconds', sum(1 for t in times if 15 <= t < 30)),
                ('30-60 seconds', sum(1 for t in times if 30 <= t < 60)),
                ('> 60 seconds', sum(1 for t in times if t >= 60))
            ]
            
            for bucket_name, count in buckets:
                worksheet.write(row, 0, bucket_name)
                worksheet.write(row, 1, count)
                worksheet.write(row, 2, f"{count / len(times) * 100:.1f}%")
                row += 1
    
    def create_text_summary(self, batch_results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """
        Create a simple text summary of batch processing results.
        
        Args:
            batch_results: Results from BatchProcessor
            output_file: Optional custom output file path
            
        Returns:
            Path to generated text summary
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"batch_summary_{timestamp}.txt"
        
        output_path = Path(output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("BATCH PROCESSING SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Timestamp: {batch_results.get('timestamp', 'Unknown')}\n")
                f.write(f"Input Source: {batch_results.get('input_source', 'Unknown')}\n")
                f.write(f"Output Directory: {batch_results.get('output_directory', 'Unknown')}\n\n")
                
                # Overall statistics
                f.write("OVERALL STATISTICS\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total Files: {batch_results.get('total_count', 0)}\n")
                f.write(f"Successful: {batch_results.get('successful_count', 0)}\n")
                f.write(f"Failed: {batch_results.get('failed_count', 0)}\n")
                f.write(f"Success Rate: {batch_results.get('success_rate', 0):.1f}%\n")
                f.write(f"Total Processing Time: {batch_results.get('total_processing_time', 0):.2f} seconds\n")
                f.write(f"Average Time per File: {batch_results.get('average_processing_time', 0):.2f} seconds\n\n")
                
                # Error summary
                errors = batch_results.get('errors', {})
                if errors and 'message' not in errors:
                    f.write("ERROR SUMMARY\n")
                    f.write("-" * 30 + "\n")
                    
                    for category, error_list in errors.items():
                        f.write(f"{category}: {len(error_list)} files\n")
                        for error_info in error_list[:3]:  # Show first 3 examples
                            f.write(f"  - {error_info['file']}: {error_info['error'][:100]}...\n")
                        if len(error_list) > 3:
                            f.write(f"  ... and {len(error_list) - 3} more\n")
                    f.write("\n")
                
                # Statistics
                stats = batch_results.get('statistics', {})
                if stats and 'message' not in stats:
                    f.write("DETAILED STATISTICS\n")
                    f.write("-" * 30 + "\n")
                    
                    for section, data in stats.items():
                        f.write(f"{section.replace('_', ' ').title()}:\n")
                        for key, value in data.items():
                            f.write(f"  {key.title()}: {value:.2f}\n")
                        f.write("\n")
            
            self.logger.info(f"Text summary generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error generating text summary: {e}")
            raise