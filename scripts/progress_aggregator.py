"""
Progress tracking and aggregation across all repositories
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .github_client import GitHubClient
from .utils import (
    load_project_data, generate_repo_name, save_progress_data, 
    load_progress_data, calculate_progress_percentage, get_milestone_status
)

logger = logging.getLogger(__name__)

class ProgressAggregator:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
    
    def collect_all_progress(self, project_csv_path: str) -> Dict:
        """Collect progress data from all project repositories"""
        try:
            projects = load_project_data(project_csv_path)
            
            progress_data = {
                'timestamp': datetime.now().isoformat(),
                'total_projects': len(projects),
                'projects': [],
                'summary': {},
                'milestones_overview': {}
            }
            
            logger.info(f"Collecting progress from {len(projects)} repositories")
            
            milestone_stats = {}
            
            for i, project in enumerate(projects, 1):
                logger.info(f"Processing {i}/{len(projects)}: {project['index_number']}")
                
                repo_name = generate_repo_name(project, self.config)
                project_progress = self.get_project_progress(project, repo_name)
                
                progress_data['projects'].append(project_progress)
                
                # Aggregate milestone statistics
                for milestone_key, status in project_progress.get('milestones', {}).items():
                    if milestone_key not in milestone_stats:
                        milestone_stats[milestone_key] = {
                            'not_started': 0,
                            'started': 0,
                            'in_progress': 0,
                            'completed': 0
                        }
                    milestone_stats[milestone_key][status] += 1
            
            # Calculate summary statistics
            progress_data['summary'] = self.calculate_summary_stats(progress_data['projects'])
            progress_data['milestones_overview'] = milestone_stats
            
            # Save progress data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_progress_data(progress_data, f'progress_snapshot_{timestamp}.json')
            save_progress_data(progress_data, 'latest_progress.json')
            
            logger.info("Progress collection completed")
            return progress_data
            
        except Exception as e:
            logger.error(f"Error collecting progress data: {e}")
            raise
    
    def get_project_progress(self, project: Dict, repo_name: str) -> Dict:
        """Get progress data for individual project"""
        try:
            progress = {
                'project': project,
                'repo_name': repo_name,
                'timestamp': datetime.now().isoformat(),
                'overall_progress': 0.0,
                'milestones': {},
                'issues': {
                    'total': 0,
                    'open': 0,
                    'closed': 0
                },
                'commits': {
                    'total': 0,
                    'last_commit': None
                },
                'status': 'unknown',
                'needs_attention': False,
                'last_activity': None
            }
            
            # Get repository issues
            issues = self.github.get_repository_issues(self.org, repo_name)
            progress['issues']['total'] = len(issues)
            progress['issues']['open'] = len([i for i in issues if i.get('state') == 'open'])
            progress['issues']['closed'] = len([i for i in issues if i.get('state') == 'closed'])
            
            # Calculate milestone progress
            milestones_config = self.config.get('milestones', {})
            for milestone_key in milestones_config.keys():
                status = get_milestone_status(issues, milestone_key)
                progress['milestones'][milestone_key] = status
            
            # Calculate overall progress percentage
            progress['overall_progress'] = calculate_progress_percentage(issues, milestones_config)
            
            # Get commit information
            try:
                commits = self.get_repository_commits(repo_name)
                progress['commits']['total'] = len(commits)
                if commits:
                    progress['commits']['last_commit'] = commits[0].get('commit', {}).get('committer', {}).get('date')
                    progress['last_activity'] = commits[0].get('commit', {}).get('committer', {}).get('date')
            except Exception as e:
                logger.warning(f"Could not get commits for {repo_name}: {e}")
            
            # Determine status
            progress['status'] = self.determine_project_status(progress)
            
            # Check if needs attention
            progress['needs_attention'] = self.check_needs_attention(progress)
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting progress for {project['index_number']}: {e}")
            return {
                'project': project,
                'repo_name': repo_name,
                'error': str(e),
                'status': 'error',
                'needs_attention': True
            }
    
    def get_repository_commits(self, repo_name: str) -> List[Dict]:
        """Get recent commits from repository"""
        try:
            response = self.github.make_request('GET', f'/repos/{self.org}/{repo_name}/commits')
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []
    
    def determine_project_status(self, progress: Dict) -> str:
        """Determine overall status of project progress"""
        overall_progress = progress.get('overall_progress', 0)
        
        if overall_progress == 0:
            return 'not_started'
        elif overall_progress < 25:
            return 'just_started'
        elif overall_progress < 50:
            return 'in_progress'
        elif overall_progress < 75:
            return 'good_progress'
        elif overall_progress < 100:
            return 'near_completion'
        else:
            return 'completed'
    
    def check_needs_attention(self, progress: Dict) -> bool:
        """Check if project needs attention"""
        # No recent activity
        last_activity = progress.get('last_activity')
        if last_activity:
            try:
                last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                if (datetime.now() - last_date.replace(tzinfo=None)).days > 7:
                    return True
            except Exception:
                pass
        
        # Very low progress
        if progress.get('overall_progress', 0) < 10:
            return True
        
        # No commits
        if progress.get('commits', {}).get('total', 0) == 0:
            return True
        
        # All issues still open
        issues = progress.get('issues', {})
        if issues.get('total', 0) > 0 and issues.get('closed', 0) == 0:
            return True
        
        return False
    
    def calculate_summary_stats(self, projects_data: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        total_projects = len(projects_data)
        
        if total_projects == 0:
            return {}
        
        # Progress distribution
        progress_ranges = {
            'not_started': 0,
            'low_progress': 0,
            'medium_progress': 0,
            'high_progress': 0,
            'completed': 0
        }
        
        # Status distribution
        status_counts = {}
        
        # projects needing attention
        needs_attention_count = 0
        
        total_progress = 0
        
        for project_data in projects_data:
            progress = project_data.get('overall_progress', 0)
            total_progress += progress
            
            # Progress ranges
            if progress == 0:
                progress_ranges['not_started'] += 1
            elif progress < 25:
                progress_ranges['low_progress'] += 1
            elif progress < 75:
                progress_ranges['medium_progress'] += 1
            elif progress < 100:
                progress_ranges['high_progress'] += 1
            else:
                progress_ranges['completed'] += 1
            
            # Status counts
            status = project_data.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Needs attention
            if project_data.get('needs_attention', False):
                needs_attention_count += 1
        
        return {
            'total_projects': total_projects,
            'average_progress': total_progress / total_projects,
            'progress_distribution': progress_ranges,
            'status_distribution': status_counts,
            'projects_needing_attention': needs_attention_count,
            'completion_rate': (progress_ranges['completed'] / total_projects) * 100
        }
    
    def generate_weekly_report(self, project_csv_path: str) -> Dict:
        """Generate weekly progress report"""
        try:
            current_progress = self.collect_all_progress(project_csv_path)
            
            # Load previous week's data for comparison
            previous_data = load_progress_data('weekly_report_previous.json')
            
            report = {
                'report_date': datetime.now().isoformat(),
                'report_type': 'weekly',
                'current_data': current_progress,
                'changes': {},
                'highlights': [],
                'concerns': [],
                'recommendations': []
            }
            
            if previous_data:
                report['changes'] = self.calculate_changes(previous_data, current_progress)
            
            # Generate highlights and concerns
            report['highlights'] = self.generate_highlights(current_progress)
            report['concerns'] = self.generate_concerns(current_progress)
            report['recommendations'] = self.generate_recommendations(current_progress)
            
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d')
            save_progress_data(report, f'weekly_report_{timestamp}.json', 'data/reports/weekly_reports')
            
            # Save current data as previous for next week
            save_progress_data(current_progress, 'weekly_report_previous.json')
            
            logger.info("Weekly report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise
    
    def calculate_changes(self, previous: Dict, current: Dict) -> Dict:
        """Calculate changes between two progress snapshots"""
        changes = {
            'progress_change': 0,
            'new_completions': 0,
            'projects_improved': 0,
            'projects_declined': 0,
            'milestone_changes': {}
        }
        
        try:
            prev_summary = previous.get('summary', {})
            curr_summary = current.get('summary', {})
            
            # Overall progress change
            prev_avg = prev_summary.get('average_progress', 0)
            curr_avg = curr_summary.get('average_progress', 0)
            changes['progress_change'] = curr_avg - prev_avg
            
            # New completions
            prev_completed = prev_summary.get('progress_distribution', {}).get('completed', 0)
            curr_completed = curr_summary.get('progress_distribution', {}).get('completed', 0)
            changes['new_completions'] = curr_completed - prev_completed
            
            # Individual project changes
            prev_projects = {s['project']['index_number']: s for s in previous.get('projects', [])}
            
            for project_data in current.get('projects', []):
                index_num = project_data['project']['index_number']
                curr_progress = project_data.get('overall_progress', 0)
                
                if index_num in prev_projects:
                    prev_progress = prev_projects[index_num].get('overall_progress', 0)
                    diff = curr_progress - prev_progress
                    
                    if diff > 5:  # Improved by more than 5%
                        changes['projects_improved'] += 1
                    elif diff < -5:  # Declined by more than 5%
                        changes['projects_declined'] += 1
            
        except Exception as e:
            logger.error(f"Error calculating changes: {e}")
        
        return changes
    
    def generate_highlights(self, progress_data: Dict) -> List[str]:
        """Generate report highlights"""
        highlights = []
        summary = progress_data.get('summary', {})
        
        # Completion rate
        completion_rate = summary.get('completion_rate', 0)
        if completion_rate > 0:
            highlights.append(f"{completion_rate:.1f}% of projects have completed their projects")
        
        # High performers
        high_progress_count = summary.get('progress_distribution', {}).get('high_progress', 0)
        if high_progress_count > 0:
            highlights.append(f"{high_progress_count} projects are making excellent progress (75%+ completion)")
        
        # Active participation
        total_commits = sum(s.get('commits', {}).get('total', 0) for s in progress_data.get('projects', []))
        if total_commits > 0:
            highlights.append(f"Total of {total_commits} commits across all repositories")
        
        return highlights
    
    def generate_concerns(self, progress_data: Dict) -> List[str]:
        """Generate report concerns"""
        concerns = []
        summary = progress_data.get('summary', {})
        
        # projects needing attention
        attention_count = summary.get('projects_needing_attention', 0)
        if attention_count > 0:
            concerns.append(f"{attention_count} projects need immediate attention")
        
        # Not started
        not_started = summary.get('progress_distribution', {}).get('not_started', 0)
        if not_started > 0:
            concerns.append(f"{not_started} projects have not started their projects")
        
        # Low progress
        low_progress = summary.get('progress_distribution', {}).get('low_progress', 0)
        if low_progress > 0:
            concerns.append(f"{low_progress} projects have very low progress (< 25%)")
        
        return concerns
    
    def generate_recommendations(self, progress_data: Dict) -> List[str]:
        """Generate recommendations based on progress data"""
        recommendations = []
        summary = progress_data.get('summary', {})
        
        # For projects needing attention
        if summary.get('projects_needing_attention', 0) > 0:
            recommendations.append("Schedule individual meetings with projects needing attention")
        
        # For low progress projects
        if summary.get('progress_distribution', {}).get('low_progress', 0) > 5:
            recommendations.append("Consider additional support sessions for struggling projects")
        
        # For inactive projects
        inactive_projects = [
            s for s in progress_data.get('projects', []) 
            if s.get('commits', {}).get('total', 0) == 0
        ]
        if len(inactive_projects) > 3:
            recommendations.append("Send reminders about regular commits and progress updates")
        
        return recommendations
    
    def get_projects_needing_attention(self, project_csv_path: str) -> List[Dict]:
        """Get list of projects who need immediate attention"""
        try:
            progress_data = self.collect_all_progress(project_csv_path)
            
            projects_needing_attention = [
                project_data for project_data in progress_data.get('projects', [])
                if project_data.get('needs_attention', False)
            ]
            
            # Sort by severity (lowest progress first)
            projects_needing_attention.sort(key=lambda x: x.get('overall_progress', 0))
            
            return projects_needing_attention
            
        except Exception as e:
            logger.error(f"Error getting projects needing attention: {e}")
            return []
    
    def update_master_dashboard_progress(self, master_project_id: int, progress_data: Dict) -> bool:
        """Update master dashboard with progress data"""
        try:
            # This would integrate with master_project.py
            # For now, save progress data that can be used by master dashboard
            save_progress_data(progress_data, 'master_dashboard_data.json')
            
            logger.info("Progress data saved for master dashboard update")
            return True
            
        except Exception as e:
            logger.error(f"Error updating master dashboard: {e}")
            return False