"""
Core batch processing engine for handling multiple financial files.
Supports parallel processing, error isolation, and progress tracking.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import glob

try:
    from ..config.settings import Settings
    from ..data.loader_factory import LoaderFactory
    from ..data.models import FinancialData
    from ..analysis.variance_analyzer import VarianceAnalyzer
    from ..analysis.correlation_engine import CorrelationEngine
    from ..analysis.anomaly_detector import AnomalyDetector
    from ..reports.excel_generator import ExcelGenerator
except ImportError:
    import sys
    from pathlib import Path
    # Add src directory to path for standalone execution
    src_path = Path(__file__).parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from config.settings import Settings
    from data.loader_factory import LoaderFactory
    from data.models import FinancialData
    from analysis.variance_analyzer import VarianceAnalyzer
    from analysis.correlation_engine import CorrelationEngine
    from analysis.anomaly_detector import AnomalyDetector
    from reports.excel_generator import ExcelGenerator

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    file_path: str
    success: bool
    processing_time: float
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    project_type: Optional[str] = None
    anomaly_count: Optional[int] = None
    variance_count: Optional[int] = None
    correlation_violations: Optional[int] = None
    file_size_mb: Optional[float] = None


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    input_pattern: str = "*.xlsx"
    output_directory: Optional[str] = None
    max_workers: int = 4
    continue_on_error: bool = True
    generate_summary: bool = True
    file_size_limit_mb: Optional[float] = None
    timeout_minutes: Optional[int] = 30
    force_loader_type: Optional[str] = None
    progress_callback: Optional[Callable[[int, int, str], None]] = None


class BatchProcessor:
    """
    Processes multiple financial analysis files in parallel.
    Provides error isolation, progress tracking, and comprehensive reporting.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.loader_factory = LoaderFactory(settings)
        
        # Initialize analysis components
        self.variance_analyzer = VarianceAnalyzer(settings)
        self.correlation_engine = CorrelationEngine(settings)
        self.anomaly_detector = AnomalyDetector(settings)
        self.excel_generator = ExcelGenerator(settings)
        
    def process_directory(self, input_directory: str, config: BatchConfig) -> Dict[str, Any]:
        """
        Process all matching files in a directory.
        
        Args:
            input_directory: Directory containing Excel files
            config: Batch processing configuration
            
        Returns:
            Dictionary containing processing results and summary
        """
        start_time = time.time()
        input_path = Path(input_directory)
        
        self.logger.info(f"Starting batch processing in {input_directory}")
        self.logger.info(f"Pattern: {config.input_pattern}, Max workers: {config.max_workers}")
        
        if not input_path.exists():
            raise ValueError(f"Input directory does not exist: {input_directory}")
        
        # Find matching files
        files_to_process = self._find_files_to_process(input_path, config)
        
        if not files_to_process:
            self.logger.warning(f"No files found matching pattern '{config.input_pattern}' in {input_directory}")
            return self._create_empty_result()
        
        self.logger.info(f"Found {len(files_to_process)} files to process")
        
        # Setup output directory
        output_dir = self._setup_output_directory(input_directory, config.output_directory)
        
        # Process files
        results = self._process_files_parallel(files_to_process, output_dir, config)
        
        # Generate summary
        processing_time = time.time() - start_time
        summary = self._generate_processing_summary(results, processing_time, input_directory, output_dir)
        
        if config.generate_summary:
            summary_file = self._save_batch_summary(summary, output_dir)
            summary['summary_file'] = summary_file
        
        self.logger.info(f"Batch processing completed in {processing_time:.2f}s")
        self.logger.info(f"Success rate: {summary['success_rate']:.1f}% ({summary['successful_count']}/{summary['total_count']})")
        
        return summary

    def process_files(self, file_paths: List[str], config: BatchConfig) -> Dict[str, Any]:
        """
        Process specific list of files.
        
        Args:
            file_paths: List of file paths to process
            config: Batch processing configuration
            
        Returns:
            Dictionary containing processing results and summary
        """
        start_time = time.time()
        
        self.logger.info(f"Processing {len(file_paths)} specified files")
        
        # Validate files exist
        valid_files = []
        for file_path in file_paths:
            if Path(file_path).exists():
                valid_files.append(file_path)
            else:
                self.logger.warning(f"File not found: {file_path}")
        
        if not valid_files:
            self.logger.error("No valid files to process")
            return self._create_empty_result()
        
        # Setup output directory
        output_dir = self._setup_output_directory(Path(valid_files[0]).parent, config.output_directory)
        
        # Process files
        results = self._process_files_parallel(valid_files, output_dir, config)
        
        # Generate summary
        processing_time = time.time() - start_time
        summary = self._generate_processing_summary(results, processing_time, "specified_files", output_dir)
        
        if config.generate_summary:
            summary_file = self._save_batch_summary(summary, output_dir)
            summary['summary_file'] = summary_file
        
        return summary

    def _find_files_to_process(self, input_path: Path, config: BatchConfig) -> List[str]:
        """Find files matching the specified pattern."""
        pattern = str(input_path / config.input_pattern)
        files = glob.glob(pattern)
        
        # Filter by file size if limit specified
        if config.file_size_limit_mb:
            filtered_files = []
            for file_path in files:
                try:
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb <= config.file_size_limit_mb:
                        filtered_files.append(file_path)
                    else:
                        self.logger.info(f"Skipping {file_path} (size: {file_size_mb:.1f}MB exceeds limit)")
                except OSError:
                    self.logger.warning(f"Could not determine size of {file_path}")
            files = filtered_files
        
        return sorted(files)

    def _setup_output_directory(self, base_path: Path, output_directory: Optional[str]) -> Path:
        """Setup output directory for results."""
        if output_directory:
            output_dir = Path(output_directory)
        else:
            output_dir = base_path / "batch_output" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory: {output_dir}")
        return output_dir

    def _process_files_parallel(self, files: List[str], output_dir: Path, config: BatchConfig) -> List[ProcessingResult]:
        """Process files in parallel using ThreadPoolExecutor."""
        results = []
        completed_count = 0
        total_count = len(files)
        
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # Submit all jobs
            future_to_file = {}
            for file_path in files:
                output_file = self._generate_output_filename(file_path, output_dir)
                future = executor.submit(self._process_single_file, file_path, output_file, config)
                future_to_file[future] = file_path
            
            # Process completed jobs
            for future in as_completed(future_to_file, timeout=config.timeout_minutes * 60 if config.timeout_minutes else None):
                file_path = future_to_file[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.success:
                        self.logger.info(f"[{completed_count}/{total_count}] Successfully processed {Path(file_path).name}")
                    else:
                        self.logger.error(f"[{completed_count}/{total_count}] Failed to process {Path(file_path).name}: {result.error_message}")
                        
                        # Stop processing if configured to do so
                        if not config.continue_on_error:
                            self.logger.error("Stopping batch processing due to error")
                            # Cancel remaining tasks
                            for remaining_future in future_to_file:
                                remaining_future.cancel()
                            break
                    
                    # Progress callback
                    if config.progress_callback:
                        config.progress_callback(completed_count, total_count, Path(file_path).name)
                        
                except Exception as e:
                    error_result = ProcessingResult(
                        file_path=file_path,
                        success=False,
                        processing_time=0.0,
                        error_message=f"Unexpected error: {str(e)}"
                    )
                    results.append(error_result)
                    self.logger.error(f"[{completed_count}/{total_count}] Unexpected error processing {Path(file_path).name}: {e}")
        
        return results

    def _process_single_file(self, file_path: str, output_file: str, config: BatchConfig) -> ProcessingResult:
        """Process a single file and return result."""
        start_time = time.time()
        file_path_obj = Path(file_path)
        
        try:
            self.logger.debug(f"Processing {file_path_obj.name}")
            
            # Get file size
            file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
            
            # Load data using factory
            financial_data = self.loader_factory.create_loader(file_path, config.force_loader_type)
            
            # Run variance analysis
            variance_results = self.variance_analyzer.analyze(financial_data)
            
            # Apply correlation rules
            correlation_results = self.correlation_engine.analyze(financial_data)
            
            # Detect anomalies
            anomalies = self.anomaly_detector.detect(
                variance_results, 
                correlation_results, 
                financial_data
            )
            
            # Generate report
            self.excel_generator.generate_report(
                financial_data,
                variance_results,
                correlation_results,
                anomalies,
                output_file
            )
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                success=True,
                processing_time=processing_time,
                output_file=output_file,
                project_type=getattr(financial_data, 'project_type', 'Unknown'),
                anomaly_count=len(anomalies) if anomalies else 0,
                variance_count=len(variance_results) if variance_results else 0,
                correlation_violations=len([r for r in correlation_results if not r.get('compliant', True)]) if correlation_results else 0,
                file_size_mb=file_size_mb
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                file_path=file_path,
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                file_size_mb=file_size_mb if 'file_size_mb' in locals() else None
            )

    def _generate_output_filename(self, input_file: str, output_dir: Path) -> str:
        """Generate output filename based on input file."""
        input_path = Path(input_file)
        base_name = input_path.stem
        output_filename = f"{base_name}_analysis_report.xlsx"
        return str(output_dir / output_filename)

    def _generate_processing_summary(self, results: List[ProcessingResult], 
                                   processing_time: float, input_source: str, output_dir: Path) -> Dict[str, Any]:
        """Generate comprehensive processing summary."""
        total_count = len(results)
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'input_source': input_source,
            'output_directory': str(output_dir),
            'total_count': total_count,
            'successful_count': len(successful_results),
            'failed_count': len(failed_results),
            'success_rate': (len(successful_results) / total_count * 100) if total_count > 0 else 0,
            'total_processing_time': processing_time,
            'average_processing_time': sum(r.processing_time for r in results) / total_count if total_count > 0 else 0,
            'results': results,
            'statistics': self._calculate_statistics(results),
            'errors': self._summarize_errors(failed_results)
        }
        
        return summary

    def _calculate_statistics(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """Calculate processing statistics."""
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return {'message': 'No successful processing results'}
        
        # File size statistics
        file_sizes = [r.file_size_mb for r in successful_results if r.file_size_mb]
        
        # Anomaly statistics
        anomaly_counts = [r.anomaly_count for r in successful_results if r.anomaly_count is not None]
        
        # Processing time statistics
        processing_times = [r.processing_time for r in successful_results]
        
        stats = {
            'file_sizes': {
                'min': min(file_sizes) if file_sizes else 0,
                'max': max(file_sizes) if file_sizes else 0,
                'average': sum(file_sizes) / len(file_sizes) if file_sizes else 0
            },
            'anomaly_counts': {
                'min': min(anomaly_counts) if anomaly_counts else 0,
                'max': max(anomaly_counts) if anomaly_counts else 0,
                'average': sum(anomaly_counts) / len(anomaly_counts) if anomaly_counts else 0,
                'total': sum(anomaly_counts) if anomaly_counts else 0
            },
            'processing_times': {
                'min': min(processing_times) if processing_times else 0,
                'max': max(processing_times) if processing_times else 0,
                'average': sum(processing_times) / len(processing_times) if processing_times else 0
            }
        }
        
        return stats

    def _summarize_errors(self, failed_results: List[ProcessingResult]) -> Dict[str, Any]:
        """Summarize error patterns from failed results."""
        if not failed_results:
            return {'message': 'No errors occurred'}
        
        error_patterns = {}
        for result in failed_results:
            error_msg = result.error_message or 'Unknown error'
            # Categorize errors
            if 'account code column' in error_msg.lower():
                category = 'Missing Account Code Column'
            elif 'balance sheet' in error_msg.lower():
                category = 'Balance Sheet Issues'
            elif 'income statement' in error_msg.lower():
                category = 'Income Statement Issues'
            elif 'validation' in error_msg.lower():
                category = 'Data Validation Errors'
            elif 'loader' in error_msg.lower():
                category = 'Data Loading Errors'
            else:
                category = 'Other Errors'
            
            if category not in error_patterns:
                error_patterns[category] = []
            error_patterns[category].append({
                'file': Path(result.file_path).name,
                'error': error_msg
            })
        
        return error_patterns

    def _save_batch_summary(self, summary: Dict[str, Any], output_dir: Path) -> str:
        """Save batch processing summary to file."""
        import json
        
        summary_file = output_dir / "batch_processing_summary.json"
        
        # Create serializable version
        serializable_summary = {
            'timestamp': summary['timestamp'],
            'input_source': summary['input_source'],
            'output_directory': summary['output_directory'],
            'total_count': summary['total_count'],
            'successful_count': summary['successful_count'],
            'failed_count': summary['failed_count'],
            'success_rate': summary['success_rate'],
            'total_processing_time': summary['total_processing_time'],
            'average_processing_time': summary['average_processing_time'],
            'statistics': summary['statistics'],
            'errors': summary['errors'],
            'successful_files': [
                {
                    'file': Path(r.file_path).name,
                    'output': Path(r.output_file).name if r.output_file else None,
                    'processing_time': r.processing_time,
                    'anomaly_count': r.anomaly_count,
                    'file_size_mb': r.file_size_mb
                }
                for r in summary['results'] if r.success
            ],
            'failed_files': [
                {
                    'file': Path(r.file_path).name,
                    'error': r.error_message
                }
                for r in summary['results'] if not r.success
            ]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Batch summary saved to {summary_file}")
        return str(summary_file)

    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result structure."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_count': 0,
            'successful_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
            'total_processing_time': 0.0,
            'results': [],
            'message': 'No files processed'
        }