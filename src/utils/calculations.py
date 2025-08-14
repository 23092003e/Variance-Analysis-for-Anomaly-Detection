"""
Mathematical and statistical calculation utilities.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Union
from scipy import stats
import warnings
from typing import Dict


def has_sign_change(current: float, previous: float) -> bool:
    """
    Check if there's a sign change between periods.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        True if there's a sign change
    """
    if previous == 0 and current != 0:
        return True
    if previous != 0 and current == 0:
        return True
    if previous > 0 and current < 0:
        return True
    if previous < 0 and current > 0:
        return True
    return False


def calculate_variance_percentage(current: float, previous: float) -> float:
    """
    Calculate variance percentage between two values.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Variance percentage
    """
    if previous == 0:
        return 100.0 if current != 0 else 0.0
    return ((current - previous) / abs(previous)) * 100


def calculate_variance_amount(current: float, previous: float) -> float:
    """
    Calculate absolute variance amount between two values.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Variance amount
    """
    return current - previous


class VarianceCalculator:
    """Utility class for variance calculations."""
    
    @staticmethod
    def calculate_percentage_change(current: float, previous: float) -> float:
        """
        Calculate percentage change between two values.
        
        Args:
            current: Current period value
            previous: Previous period value
            
        Returns:
            Percentage change
        """
        if previous == 0:
            return 100.0 if current != 0 else 0.0
        
        return ((current - previous) / abs(previous)) * 100
    
    @staticmethod
    def calculate_absolute_change(current: float, previous: float) -> float:
        """Calculate absolute change between two values."""
        return current - previous
    
    @staticmethod
    def is_significant_change(current: float, previous: float, threshold: float = 5.0) -> bool:
        """
        Determine if change between values is significant.
        
        Args:
            current: Current value
            previous: Previous value
            threshold: Percentage threshold for significance
            
        Returns:
            True if change is significant
        """
        percentage_change = VarianceCalculator.calculate_percentage_change(current, previous)
        return abs(percentage_change) >= threshold
    
    @staticmethod
    def detect_outliers(values: List[float], method: str = 'iqr') -> List[bool]:
        """
        Detect outliers in a list of values.
        
        Args:
            values: List of numerical values
            method: Method to use ('iqr', 'zscore', 'modified_zscore')
            
        Returns:
            List of boolean values indicating outliers
        """
        values_array = np.array(values)
        
        if method == 'iqr':
            return VarianceCalculator._detect_outliers_iqr(values_array)
        elif method == 'zscore':
            return VarianceCalculator._detect_outliers_zscore(values_array)
        elif method == 'modified_zscore':
            return VarianceCalculator._detect_outliers_modified_zscore(values_array)
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
    
    @staticmethod
    def _detect_outliers_iqr(values: np.ndarray) -> List[bool]:
        """Detect outliers using Interquartile Range method."""
        Q1 = np.percentile(values, 25)
        Q3 = np.percentile(values, 75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        return [(v < lower_bound or v > upper_bound) for v in values]
    
    @staticmethod
    def _detect_outliers_zscore(values: np.ndarray, threshold: float = 3.0) -> List[bool]:
        """Detect outliers using Z-score method."""
        z_scores = np.abs(stats.zscore(values))
        return [z > threshold for z in z_scores]
    
    @staticmethod
    def _detect_outliers_modified_zscore(values: np.ndarray, threshold: float = 3.5) -> List[bool]:
        """Detect outliers using Modified Z-score method."""
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        
        if mad == 0:
            return [False] * len(values)
        
        modified_z_scores = 0.6745 * (values - median) / mad
        return [abs(z) > threshold for z in modified_z_scores]


class CorrelationCalculator:
    """Utility class for correlation calculations."""
    
    @staticmethod
    def calculate_pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
        """
        Calculate Pearson correlation coefficient and p-value.
        
        Args:
            x: First dataset
            y: Second dataset
            
        Returns:
            Tuple of (correlation coefficient, p-value)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0, 1.0
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            correlation, p_value = stats.pearsonr(x, y)
            
        return correlation if not np.isnan(correlation) else 0.0, p_value if not np.isnan(p_value) else 1.0
    
    @staticmethod
    def calculate_spearman_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
        """
        Calculate Spearman rank correlation coefficient and p-value.
        
        Args:
            x: First dataset
            y: Second dataset
            
        Returns:
            Tuple of (correlation coefficient, p-value)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0, 1.0
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            correlation, p_value = stats.spearmanr(x, y)
            
        return correlation if not np.isnan(correlation) else 0.0, p_value if not np.isnan(p_value) else 1.0
    
    @staticmethod
    def is_correlation_significant(correlation: float, p_value: float, 
                                 alpha: float = 0.05, min_correlation: float = 0.3) -> bool:
        """
        Determine if correlation is statistically significant.
        
        Args:
            correlation: Correlation coefficient
            p_value: Statistical p-value
            alpha: Significance level
            min_correlation: Minimum correlation threshold
            
        Returns:
            True if correlation is significant
        """
        return p_value < alpha and abs(correlation) >= min_correlation


class TrendAnalyzer:
    """Utility class for trend analysis."""
    
    @staticmethod
    def calculate_trend(values: List[float]) -> Dict[str, float]:
        """
        Calculate trend statistics for a series of values.
        
        Args:
            values: Time series values
            
        Returns:
            Dictionary with trend statistics
        """
        if len(values) < 2:
            return {'slope': 0.0, 'r_squared': 0.0, 'trend': 'insufficient_data'}
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Remove NaN values
        mask = ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return {'slope': 0.0, 'r_squared': 0.0, 'trend': 'insufficient_data'}
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
        
        # Determine trend direction
        if abs(slope) < 0.01:  # Very small slope
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'std_error': std_err,
            'trend': trend_direction
        }
    
    @staticmethod
    def detect_seasonality(values: List[float], period: int = 4) -> Dict[str, Union[bool, float]]:
        """
        Detect seasonal patterns in data.
        
        Args:
            values: Time series values
            period: Expected seasonal period (e.g., 4 for quarterly)
            
        Returns:
            Dictionary with seasonality detection results
        """
        if len(values) < period * 2:
            return {'has_seasonality': False, 'strength': 0.0}
        
        values_array = np.array(values)
        
        # Calculate seasonal indices
        seasonal_means = []
        for i in range(period):
            season_values = values_array[i::period]
            seasonal_means.append(np.nanmean(season_values))
        
        # Calculate seasonality strength
        overall_mean = np.nanmean(values_array)
        seasonal_variance = np.var(seasonal_means)
        total_variance = np.nanvar(values_array)
        
        if total_variance == 0:
            seasonality_strength = 0.0
        else:
            seasonality_strength = seasonal_variance / total_variance
        
        return {
            'has_seasonality': seasonality_strength > 0.1,
            'strength': seasonality_strength,
            'seasonal_indices': seasonal_means
        }


class StatisticalSummary:
    """Utility class for statistical summaries."""
    
    @staticmethod
    def describe_series(values: List[float]) -> Dict[str, float]:
        """
        Generate comprehensive statistical summary.
        
        Args:
            values: List of numerical values
            
        Returns:
            Dictionary with statistical measures
        """
        values_array = np.array(values)
        values_clean = values_array[~np.isnan(values_array)]
        
        if len(values_clean) == 0:
            return {}
        
        return {
            'count': len(values_clean),
            'mean': np.mean(values_clean),
            'median': np.median(values_clean),
            'std': np.std(values_clean),
            'min': np.min(values_clean),
            'max': np.max(values_clean),
            'q25': np.percentile(values_clean, 25),
            'q75': np.percentile(values_clean, 75),
            'skewness': stats.skew(values_clean),
            'kurtosis': stats.kurtosis(values_clean)
        }
    
    @staticmethod
    def calculate_confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for the mean.
        
        Args:
            values: List of numerical values
            confidence: Confidence level (0.0 to 1.0)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        values_clean = [v for v in values if not np.isnan(v)]
        
        if len(values_clean) < 2:
            return (0.0, 0.0)
        
        mean = np.mean(values_clean)
        std_err = stats.sem(values_clean)
        
        # Calculate t-critical value
        alpha = 1 - confidence
        df = len(values_clean) - 1
        t_critical = stats.t.ppf(1 - alpha/2, df)
        
        margin_of_error = t_critical * std_err
        
        return (mean - margin_of_error, mean + margin_of_error)