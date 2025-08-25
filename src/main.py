"""
Main application entry point for Variance Analysis Anomaly Detection.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from .config.settings import Settings
    from .data.loader import DataLoader
    from .data.dal_loader import DALDataLoader
    from .analysis.variance_analyzer import VarianceAnalyzer
    from .analysis.correlation_engine import CorrelationEngine
    from .analysis.anomaly_detector import AnomalyDetector
    from .reports.excel_generator import ExcelGenerator
    from .utils.logging_config import setup_logging
except ImportError:
    from config.settings import Settings
    from data.loader import DataLoader
    from data.dal_loader import DALDataLoader
    from analysis.variance_analyzer import VarianceAnalyzer
    from analysis.correlation_engine import CorrelationEngine
    from analysis.anomaly_detector import AnomalyDetector
    from reports.excel_generator import ExcelGenerator
    from utils.logging_config import setup_logging


def main(input_file: Optional[str] = None, output_file: Optional[str] = None, 
         batch_directory: Optional[str] = None, batch_pattern: str = "*.xlsx",
         max_workers: int = 4, force_loader: Optional[str] = None) -> None:
    """
    Main function to run the variance analysis and anomaly detection.
    Supports both single file and batch processing modes.
    
    Args:
        input_file: Path to input Excel file (single file mode)
        output_file: Path to output Excel file (single file mode)
        batch_directory: Directory for batch processing
        batch_pattern: File pattern for batch processing (default: "*.xlsx")
        max_workers: Number of parallel workers for batch processing
        force_loader: Force specific loader type ('dal', 'standard', 'flexible')
    """
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting Variance Analysis Anomaly Detection")
        
        # Load settings
        settings = Settings()
        
        # Determine processing mode
        if batch_directory:
            # Batch processing mode
            logger.info(f"Starting batch processing mode for directory: {batch_directory}")
            _process_batch_mode(settings, batch_directory, batch_pattern, max_workers, 
                              output_file, force_loader)
        else:
            # Single file processing mode
            logger.info("Starting single file processing mode")
            _process_single_file_mode(settings, input_file, output_file, force_loader)
            
        logger.info("Processing completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        sys.exit(1)


def _process_single_file_mode(settings: Settings, input_file: Optional[str], 
                            output_file: Optional[str], force_loader: Optional[str]) -> None:
    """Process single file using improved loader factory."""
    try:
        from .data.loader_factory import LoaderFactory
    except ImportError:
        from data.loader_factory import LoaderFactory
    
    logger = logging.getLogger(__name__)
    
    # Determine file paths
    if not input_file:
        input_file = settings.default_input_file
    if not output_file:
        output_file = settings.default_output_file
    
    logger.info(f"Processing single file: {input_file}")
    
    # Load data using factory
    loader_factory = LoaderFactory(settings)
    financial_data = loader_factory.create_loader(input_file, force_loader)
    
    # Run analysis pipeline
    logger.info("Running variance analysis")
    variance_analyzer = VarianceAnalyzer(settings)
    variance_results = variance_analyzer.analyze(financial_data)
    
    logger.info("Applying correlation rules")
    correlation_engine = CorrelationEngine(settings)
    correlation_results = correlation_engine.analyze(financial_data)
    
    logger.info("Detecting anomalies")
    anomaly_detector = AnomalyDetector(settings)
    anomalies = anomaly_detector.detect(variance_results, correlation_results, financial_data)
    
    # Generate report
    logger.info(f"Generating report to {output_file}")
    excel_generator = ExcelGenerator(settings)
    excel_generator.generate_report(
        financial_data, variance_results, correlation_results, anomalies, output_file
    )
    
    logger.info(f"Single file analysis completed: {output_file}")


def _process_batch_mode(settings: Settings, batch_directory: str, batch_pattern: str,
                       max_workers: int, output_directory: Optional[str], 
                       force_loader: Optional[str]) -> None:
    """Process multiple files in batch mode."""
    try:
        from .batch.batch_processor import BatchProcessor, BatchConfig
    except ImportError:
        from batch.batch_processor import BatchProcessor, BatchConfig
    
    logger = logging.getLogger(__name__)
    
    # Setup batch configuration
    config = BatchConfig(
        input_pattern=batch_pattern,
        output_directory=output_directory,
        max_workers=max_workers,
        continue_on_error=True,
        generate_summary=True,
        force_loader_type=force_loader,
        progress_callback=_progress_callback
    )
    
    # Initialize batch processor
    batch_processor = BatchProcessor(settings)
    
    # Process directory
    logger.info(f"Starting batch processing with {max_workers} workers")
    results = batch_processor.process_directory(batch_directory, config)
    
    # Log summary
    logger.info(f"Batch processing completed:")
    logger.info(f"  Total files: {results['total_count']}")
    logger.info(f"  Successful: {results['successful_count']}")
    logger.info(f"  Failed: {results['failed_count']}")
    logger.info(f"  Success rate: {results['success_rate']:.1f}%")
    logger.info(f"  Total time: {results['total_processing_time']:.2f}s")
    
    if results.get('summary_file'):
        logger.info(f"  Summary report: {results['summary_file']}")


def _progress_callback(completed: int, total: int, current_file: str) -> None:
    """Progress callback for batch processing."""
    logger = logging.getLogger(__name__)
    percentage = (completed / total) * 100
    logger.info(f"Progress: {percentage:.1f}% ({completed}/{total}) - {current_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Variance Analysis Anomaly Detection - Single File and Batch Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file processing
  python src/main.py -i input.xlsx -o output.xlsx
  
  # Batch processing
  python src/main.py -b data/raw/ -p "*.xlsx"
  
  # Batch with custom output directory  
  python src/main.py -b data/raw/ -o data/output/
  
  # Force specific loader type
  python src/main.py -i dal_file.xlsx --loader dal
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-i", "--input", 
        help="Input Excel file path (single file mode)"
    )
    input_group.add_argument(
        "-b", "--batch",
        help="Input directory for batch processing"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output file path (single mode) or output directory (batch mode)"
    )
    
    # Batch processing options
    parser.add_argument(
        "-p", "--pattern",
        default="*.xlsx",
        help="File pattern for batch processing (default: *.xlsx)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for batch processing (default: 4)"
    )
    
    # Loader options
    parser.add_argument(
        "--loader",
        choices=['auto', 'dal', 'standard', 'flexible'],
        default='auto',
        help="Force specific loader type (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Convert loader argument
    force_loader = None if args.loader == 'auto' else args.loader
    
    # Call main with appropriate arguments
    if args.batch:
        main(
            batch_directory=args.batch,
            batch_pattern=args.pattern,
            output_file=args.output,
            max_workers=args.workers,
            force_loader=force_loader
        )
    else:
        main(
            input_file=args.input,
            output_file=args.output,
            force_loader=force_loader
        )