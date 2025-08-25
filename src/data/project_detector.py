"""
Project type detection and classification system.
Automatically identifies project types based on file content, structure, and naming patterns.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Supported project types for financial analysis."""
    DAL = "DAL"
    STANDARD = "STANDARD"
    VIETNAM_CHART = "VIETNAM_CHART"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


class ProjectDetector:
    """Detects and classifies project types from Excel files."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # DAL project indicators
        self.dal_indicators = {
            'filename_patterns': [
                r'dal_.*\.xlsx?$',
                r'.*_dal_.*\.xlsx?$',
                r'dal.*may.*\.xlsx?$',
                r'dal.*example.*\.xlsx?$'
            ],
            'sheet_names': [
                'dal balance sheet',
                'dal income statement', 
                'dal bs',
                'dal is'
            ],
            'account_patterns': [
                r'^[12345]\d{8}$',  # 9-digit codes starting with 1-5
                r'^2170000\d{2}$',  # Investment properties pattern
                r'^3411600\d{2}$'   # Borrowings pattern
            ],
            'content_keywords': [
                'land use rights',
                'investment properties',
                'borrowings: subsidiaries/parents'
            ]
        }
        
        # Vietnam Chart of Accounts indicators
        self.vietnam_chart_indicators = {
            'account_patterns': [
                r'^[1-9]\d{8}$',    # 9-digit Vietnamese account codes
                r'^11\d{7}$',       # Assets (11x)
                r'^21\d{7}$',       # Fixed assets (21x)
                r'^33\d{7}$',       # Payables (33x)
                r'^51\d{7}$',       # Revenue (51x)
                r'^62\d{7}$'        # Expenses (62x)
            ],
            'sheet_names': [
                'bảng cân đối',
                'báng cân đối kế toán',
                'kết quả kinh doanh',
                'balance sheet',
                'income statement'
            ]
        }
        
        # Standard format indicators
        self.standard_indicators = {
            'account_patterns': [
                r'^\d{4,6}$',       # 4-6 digit account codes
                r'^[A-Z]{2,4}\d+$'  # Letter prefixes with numbers
            ],
            'sheet_names': [
                'balance sheet',
                'income statement',
                'bs',
                'is',
                'p&l',
                'profit and loss'
            ]
        }

    def detect_project_type(self, file_path: str) -> Tuple[ProjectType, Dict[str, Any]]:
        """
        Detect project type from Excel file.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Tuple of (ProjectType, detection_details)
        """
        try:
            file_path = Path(file_path)
            
            # Initialize detection details
            details = {
                'filename': file_path.name,
                'detected_features': [],
                'confidence_score': 0.0,
                'sheet_info': {},
                'account_patterns': [],
                'recommended_loader': 'standard'
            }
            
            # Step 1: Check filename patterns
            filename_type, filename_confidence = self._check_filename_patterns(file_path.name)
            details['filename_confidence'] = filename_confidence
            
            # Step 2: Analyze Excel file content
            try:
                # Get basic file info without loading all data
                xl_info = self._get_excel_info(file_path)
                details['sheet_info'] = xl_info
                
                # Step 3: Analyze sheet content for patterns
                content_type, content_confidence, content_details = self._analyze_sheet_content(file_path, xl_info)
                details.update(content_details)
                details['content_confidence'] = content_confidence
                
                # Step 4: Combine results and determine final type
                final_type, final_confidence = self._combine_detection_results(
                    filename_type, filename_confidence,
                    content_type, content_confidence
                )
                
                details['confidence_score'] = final_confidence
                details['recommended_loader'] = self._get_recommended_loader(final_type)
                
                self.logger.info(f"Detected {final_type.value} project type for {file_path.name} "
                               f"(confidence: {final_confidence:.2f})")
                
                return final_type, details
                
            except Exception as e:
                self.logger.warning(f"Error analyzing file content for {file_path.name}: {e}")
                # Fallback to filename-based detection
                if filename_confidence > 0.5:
                    return filename_type, details
                else:
                    return ProjectType.UNKNOWN, details
                    
        except Exception as e:
            self.logger.error(f"Error detecting project type for {file_path}: {e}")
            return ProjectType.UNKNOWN, {'error': str(e)}

    def _check_filename_patterns(self, filename: str) -> Tuple[ProjectType, float]:
        """Check filename against known patterns."""
        filename_lower = filename.lower()
        
        # Check DAL patterns
        for pattern in self.dal_indicators['filename_patterns']:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return ProjectType.DAL, 0.8
        
        # Check for Vietnam-specific naming
        vietnam_keywords = ['vn', 'vietnam', 'vietnamese', 'viet']
        if any(keyword in filename_lower for keyword in vietnam_keywords):
            return ProjectType.VIETNAM_CHART, 0.6
            
        # Default to standard
        return ProjectType.STANDARD, 0.3

    def _get_excel_info(self, file_path: Path) -> Dict[str, Any]:
        """Get basic information about Excel file structure."""
        try:
            xl_file = pd.ExcelFile(file_path)
            return {
                'sheet_names': xl_file.sheet_names,
                'sheet_count': len(xl_file.sheet_names)
            }
        except Exception as e:
            self.logger.warning(f"Error reading Excel file info: {e}")
            return {'sheet_names': [], 'sheet_count': 0}

    def _analyze_sheet_content(self, file_path: Path, xl_info: Dict[str, Any]) -> Tuple[ProjectType, float, Dict[str, Any]]:
        """Analyze sheet content to determine project type."""
        details = {
            'detected_features': [],
            'account_patterns': [],
            'sheet_analysis': {}
        }
        
        try:
            # Analyze sheet names
            sheet_type_scores = {
                ProjectType.DAL: 0.0,
                ProjectType.VIETNAM_CHART: 0.0,
                ProjectType.STANDARD: 0.0
            }
            
            for sheet_name in xl_info.get('sheet_names', []):
                sheet_name_lower = sheet_name.lower()
                
                # Check DAL sheet patterns
                if any(indicator in sheet_name_lower for indicator in self.dal_indicators['sheet_names']):
                    sheet_type_scores[ProjectType.DAL] += 0.3
                    details['detected_features'].append(f'DAL sheet name: {sheet_name}')
                
                # Check Vietnam chart patterns
                if any(indicator in sheet_name_lower for indicator in self.vietnam_chart_indicators['sheet_names']):
                    sheet_type_scores[ProjectType.VIETNAM_CHART] += 0.2
                    details['detected_features'].append(f'Vietnam chart sheet name: {sheet_name}')
                
                # Check standard patterns
                if any(indicator in sheet_name_lower for indicator in self.standard_indicators['sheet_names']):
                    sheet_type_scores[ProjectType.STANDARD] += 0.2
                    details['detected_features'].append(f'Standard sheet name: {sheet_name}')

            # Analyze account code patterns by sampling data
            account_patterns = self._sample_account_patterns(file_path, xl_info['sheet_names'][:2])
            details['account_patterns'] = account_patterns
            
            # Score account patterns
            for pattern_info in account_patterns:
                pattern = pattern_info['pattern']
                count = pattern_info['count']
                
                # Weight by frequency
                weight = min(count / 10, 1.0)
                
                # Check against DAL patterns
                if any(re.match(dal_pattern, pattern) for dal_pattern in self.dal_indicators['account_patterns']):
                    sheet_type_scores[ProjectType.DAL] += 0.4 * weight
                    details['detected_features'].append(f'DAL account pattern: {pattern} ({count} instances)')
                
                # Check against Vietnam chart patterns
                elif any(re.match(vn_pattern, pattern) for vn_pattern in self.vietnam_chart_indicators['account_patterns']):
                    sheet_type_scores[ProjectType.VIETNAM_CHART] += 0.3 * weight
                    details['detected_features'].append(f'Vietnam chart pattern: {pattern} ({count} instances)')
                
                # Check against standard patterns
                elif any(re.match(std_pattern, pattern) for std_pattern in self.standard_indicators['account_patterns']):
                    sheet_type_scores[ProjectType.STANDARD] += 0.2 * weight
                    details['detected_features'].append(f'Standard pattern: {pattern} ({count} instances)')

            # Determine best match
            best_type = max(sheet_type_scores.keys(), key=lambda k: sheet_type_scores[k])
            best_score = sheet_type_scores[best_type]
            
            # Minimum confidence threshold
            if best_score < 0.1:
                return ProjectType.UNKNOWN, 0.0, details
                
            return best_type, best_score, details
            
        except Exception as e:
            self.logger.warning(f"Error analyzing sheet content: {e}")
            return ProjectType.UNKNOWN, 0.0, details

    def _sample_account_patterns(self, file_path: Path, sheet_names: List[str]) -> List[Dict[str, Any]]:
        """Sample account code patterns from sheets."""
        patterns = {}
        
        try:
            for sheet_name in sheet_names:
                try:
                    # Read only first 20 rows to sample patterns
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=20)
                    
                    # Look for account code-like columns
                    account_columns = []
                    for col in df.columns:
                        col_str = str(col).lower()
                        if any(keyword in col_str for keyword in ['account', 'code', 'mã', 'tài khoản']):
                            account_columns.append(col)
                    
                    # Sample patterns from account columns
                    for col in account_columns:
                        values = df[col].dropna().astype(str)
                        for value in values:
                            # Clean and standardize
                            clean_value = re.sub(r'[^\d]', '', value)
                            if len(clean_value) >= 4:  # Minimum account code length
                                if clean_value not in patterns:
                                    patterns[clean_value] = 0
                                patterns[clean_value] += 1
                                
                except Exception as e:
                    self.logger.debug(f"Error sampling from sheet {sheet_name}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error sampling account patterns: {e}")
        
        # Convert to list format and sort by frequency
        pattern_list = [{'pattern': pattern, 'count': count} 
                       for pattern, count in patterns.items()]
        pattern_list.sort(key=lambda x: x['count'], reverse=True)
        
        return pattern_list[:10]  # Return top 10 patterns

    def _combine_detection_results(self, filename_type: ProjectType, filename_conf: float,
                                 content_type: ProjectType, content_conf: float) -> Tuple[ProjectType, float]:
        """Combine filename and content analysis results."""
        
        # If both agree, high confidence
        if filename_type == content_type:
            combined_confidence = min(filename_conf + content_conf * 0.7, 1.0)
            return filename_type, combined_confidence
        
        # Content analysis has higher weight if confident
        if content_conf > 0.6:
            return content_type, content_conf
        
        # Filename analysis as fallback
        if filename_conf > 0.5:
            return filename_type, filename_conf * 0.8
        
        # Default to higher confidence option
        if content_conf > filename_conf:
            return content_type, content_conf
        else:
            return filename_type, filename_conf

    def _get_recommended_loader(self, project_type: ProjectType) -> str:
        """Get recommended loader based on project type."""
        loader_mapping = {
            ProjectType.DAL: 'dal',
            ProjectType.VIETNAM_CHART: 'standard',
            ProjectType.STANDARD: 'standard',
            ProjectType.CUSTOM: 'standard',
            ProjectType.UNKNOWN: 'standard'
        }
        return loader_mapping.get(project_type, 'standard')

    def get_project_profile(self, project_type: ProjectType, details: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommended project configuration profile."""
        
        base_profile = {
            'project_type': project_type.value,
            'confidence_score': details.get('confidence_score', 0.0),
            'recommended_loader': details.get('recommended_loader', 'standard'),
            'features': details.get('detected_features', [])
        }
        
        if project_type == ProjectType.DAL:
            base_profile.update({
                'account_mapping_template': 'dal_template',
                'variance_thresholds': {
                    'default': 5.0,
                    'recurring_accounts': 3.0,
                    'investment_properties': 2.0
                },
                'special_handling': ['investment_properties', 'borrowings', 'depreciation']
            })
        
        elif project_type == ProjectType.VIETNAM_CHART:
            base_profile.update({
                'account_mapping_template': 'vietnam_chart_template',
                'variance_thresholds': {
                    'default': 7.0,
                    'assets': 5.0,
                    'revenue': 4.0
                }
            })
        
        else:  # STANDARD, CUSTOM, UNKNOWN
            base_profile.update({
                'account_mapping_template': 'standard_template',
                'variance_thresholds': {
                    'default': 5.0
                }
            })
        
        return base_profile