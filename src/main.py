"""
Main application entry point for Variance Analysis Anomaly Detection.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import Settings
from data.loader import DataLoader
from analysis.variance_analyzer import VarianceAnalyzer
from analysis.correlation_engine import CorrelationEngine
from analysis.anomaly_detector import AnomalyDetector
from reports.excel_generator import ExcelGenerator
from utils.logging_config import setup_logging


def main(input_file: Optional[str] = None, output_file: Optional[str] = None) -> None:
    """
    Main function to run the variance analysis and anomaly detection.
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file
    """
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting Variance Analysis Anomaly Detection")
        
        # Load settings
        settings = Settings()
        
        # Determine file paths
        if not input_file:
            input_file = settings.default_input_file
        if not output_file:
            output_file = settings.default_output_file
            
        # Load and validate data
        logger.info(f"Loading data from {input_file}")
        data_loader = DataLoader(settings)
        financial_data = data_loader.load_excel_file(input_file)
        
        if not data_loader.validate_data(financial_data):
            logger.error("Data validation failed")
            sys.exit(1)
            
        # Run variance analysis
        logger.info("Running variance analysis")
        variance_analyzer = VarianceAnalyzer(settings)
        variance_results = variance_analyzer.analyze(financial_data)
        
        # Apply correlation rules
        logger.info("Applying correlation rules")
        correlation_engine = CorrelationEngine(settings)
        correlation_results = correlation_engine.analyze(financial_data)
        
        # Detect anomalies
        logger.info("Detecting anomalies")
        anomaly_detector = AnomalyDetector(settings)
        anomalies = anomaly_detector.detect(
            variance_results, 
            correlation_results, 
            financial_data
        )
        
        # Generate Excel report
        logger.info(f"Generating report to {output_file}")
        excel_generator = ExcelGenerator(settings)
        excel_generator.generate_report(
            financial_data,
            variance_results,
            correlation_results,
            anomalies,
            output_file
        )
        
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Variance Analysis Anomaly Detection"
    )
    parser.add_argument(
        "-i", "--input", 
        help="Input Excel file path"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output Excel file path"
    )
    
    args = parser.parse_args()
    main(args.input, args.output)