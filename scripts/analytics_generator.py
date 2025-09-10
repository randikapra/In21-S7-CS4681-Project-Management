"""
Analytics and reporting generation
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from .progress_aggregator import ProgressAggregator
from .utils import load_project_data

logger = logging.getLogger(__name__)

class AnalyticsGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.progress_aggregator = ProgressAggregator(config)
        
    def generate_comprehensive_analytics(self, project_csv_path: str) -> Dict:
        """Generate comprehensive analytics report"""
        try:
            progress_data = self.progress_aggregator.collect_all_progress(project_csv_path)
            
            analytics = {
                'report_id': f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'overview': self._generate_overview_stats(progress_data),
                'risk_analytics': self._analyze_risk_factors(progress_data),
                'milestone_analytics': self._analyze_milestone_progress(progress_data),
                'recommendations': self._generate_recommendations(progress_data)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate analytics: {e}")
            return {'error': str(e)}
    
    def _generate_overview_stats(self, progress_data: Dict) -> Dict:
        """Generate overview statistics"""
        total_students = len(progress_data)
        if total_students == 0:
            return {'total_students': 0}
        
        progress_values = [data.get('progress_percentage', 0) for data in progress_data.values()]
        average_progress = sum(progress_values) / len(progress_values)
        
        return {
            'total_students': total_students,
            'average_progress': round(average_progress, 2),
            'students_completed': len([p for p in progress_values if p >= 100]),
            'students_at_risk': len([p for p in progress_values if p < 25])
        }
    
    def _analyze_risk_factors(self, progress_data: Dict) -> Dict:
        """Analyze risk factors for students"""
        high_risk = []
        medium_risk = []
        low_risk = []
        
        for student_id, data in progress_data.items():
            progress = data.get('progress_percentage', 0)
            recent_activity = data.get('recent_activity', False)
            
            if progress < 25 and not recent_activity:
                high_risk.append(student_id)
            elif progress < 50 or not recent_activity:
                medium_risk.append(student_id)
            else:
                low_risk.append(student_id)
        
        return {
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'low_risk': low_risk
        }
    
    def _analyze_milestone_progress(self, progress_data: Dict) -> Dict:
        """Analyze milestone completion across students"""
        return {
            'research_proposal': self._count_milestone_completion(progress_data, 'research_proposal'),
            'literature_review': self._count_milestone_completion(progress_data, 'literature_review'),
            'implementation': self._count_milestone_completion(progress_data, 'implementation'),
            'final_evaluation': self._count_milestone_completion(progress_data, 'final_evaluation')
        }
    
    def _count_milestone_completion(self, progress_data: Dict, milestone: str) -> Dict:
        """Count completion for specific milestone"""
        # This would need to check specific milestone completion in the actual implementation
        return {'completed': 0, 'in_progress': 0, 'not_started': 0}
    
    def _generate_recommendations(self, progress_data: Dict) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []
        
        overview = self._generate_overview_stats(progress_data)
        risk_analysis = self._analyze_risk_factors(progress_data)
        
        if len(risk_analysis['high_risk']) > 0:
            recommendations.append(f"Immediate attention needed for {len(risk_analysis['high_risk'])} high-risk students")
        
        if overview['average_progress'] < 50:
            recommendations.append("Overall progress is below 50% - consider additional support measures")
        
        return recommendations