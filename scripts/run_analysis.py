#!/usr/bin/env python3
"""
Batch processing script for variance analysis anomaly detection.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main as run_analysis
from config.settings import Settings
from utils.logging_config import setup_logging


def process_single_file(input_file: str, output_file: Optional[str] = None) -> bool:
    """
    Process a single Excel file for variance analysis.
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate output filename if not provided
        if not output_file:
            input_path = Path(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(input_path.parent / f"variance_analysis_{input_path.stem}_{timestamp}.xlsx")
        
        logging.info(f"Processing: {input_file} -> {output_file}")
        
        # Run the main analysis
        run_analysis(input_file, output_file)
        
        logging.info(f"Successfully processed: {input_file}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to process {input_file}: {str(e)}")
        return False


def process_directory(input_dir: str, output_dir: Optional[str] = None, 
                     pattern: str = "*.xlsx") -> List[str]:
    """
    Process all Excel files in a directory.
    
    Args:
        input_dir: Directory containing input Excel files
        output_dir: Directory for output files (optional)
        pattern: File pattern to match (default: *.xlsx)
        
    Returns:
        List of successfully processed files
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        logging.error(f"Input directory does not exist: {input_dir}")
        return []
    
    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path / "analysis_results"
        output_path.mkdir(exist_ok=True)
    
    # Find Excel files
    excel_files = list(input_path.glob(pattern))
    
    if not excel_files:
        logging.warning(f"No Excel files found in {input_dir} matching pattern {pattern}")
        return []
    
    logging.info(f"Found {len(excel_files)} files to process")
    
    successful_files = []
    failed_files = []
    
    for excel_file in excel_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"variance_analysis_{excel_file.stem}_{timestamp}.xlsx"
        
        success = process_single_file(str(excel_file), str(output_file))
        
        if success:
            successful_files.append(str(excel_file))
        else:
            failed_files.append(str(excel_file))
    
    # Summary
    logging.info(f"Processing complete: {len(successful_files)} successful, {len(failed_files)} failed")
    
    if failed_files:
        logging.error(f"Failed files: {failed_files}")
    
    return successful_files


def generate_summary_report(processed_files: List[str], output_dir: str) -> None:
    """
    Generate a summary report of processed files.
    
    Args:
        processed_files: List of successfully processed file paths
        output_dir: Output directory for summary report
    """
    if not processed_files:
        logging.info("No files processed - skipping summary report")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = Path(output_dir) / f"processing_summary_{timestamp}.txt"
    
    with open(summary_file, 'w') as f:
        f.write(f"Variance Analysis Processing Summary\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"="*50 + "\n\n")
        
        f.write(f"Total files processed: {len(processed_files)}\n\n")
        
        f.write("Processed files:\n")
        for i, file_path in enumerate(processed_files, 1):
            f.write(f"{i:3d}. {file_path}\n")
        
        f.write("\n" + "="*50 + "\n")
        f.write("Note: Individual analysis reports generated for each file.\n")
        f.write("Check the output directory for detailed Excel reports.\n")
    
    logging.info(f"Summary report generated: {summary_file}")


def main():
    """Main function for batch processing script."""
    parser = argparse.ArgumentParser(
        description="Batch processing for Variance Analysis Anomaly Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single file
  python run_analysis.py -f input.xlsx
  
  # Process single file with custom output
  python run_analysis.py -f input.xlsx -o output.xlsx
  
  # Process all Excel files in directory
  python run_analysis.py -d /path/to/excel/files
  
  # Process directory with custom output location
  python run_analysis.py -d /path/to/input -o /path/to/output
  
  # Process with custom file pattern
  python run_analysis.py -d /path/to/input --pattern "DAL_*.xlsx"
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-f", "--file",
        help="Process single Excel file"
    )
    input_group.add_argument(
        "-d", "--directory",
        help="Process all Excel files in directory"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output file (for single file) or output directory (for directory processing)"
    )
    
    # Directory processing options
    parser.add_argument(
        "--pattern",
        default="*.xlsx",
        help="File pattern for directory processing (default: *.xlsx)"
    )
    
    # Processing options
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (default: logs to console only)"
    )
    
    parser.add_argument(
        "--summary",
        action='store_true',
        help="Generate processing summary report"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting batch variance analysis processing")
    
    successful_files = []
    
    try:
        if args.file:
            # Process single file
            success = process_single_file(args.file, args.output)
            if success:
                successful_files = [args.file]
            
        elif args.directory:
            # Process directory
            successful_files = process_directory(
                args.directory,
                args.output,
                args.pattern
            )
        
        # Generate summary report if requested
        if args.summary and successful_files:
            output_dir = args.output if args.output else "."
            generate_summary_report(successful_files, output_dir)
        
        # Exit code based on results
        if successful_files:
            logger.info("Batch processing completed successfully")
            return 0
        else:
            logger.error("Batch processing failed - no files processed successfully")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error during batch processing: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())