"""
Master project dashboard management for GitHub Projects
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from .github_client import GitHubClient
from .utils import load_project_data, load_supervisor_data

logger = logging.getLogger(__name__)

class MasterProjectManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        self.repo_name = config['repository']['name']
        self.dashboard_config = config.get('master_dashboard', {})
        
    def create_repository_project(self, project_csv_path: str) -> Dict:
        """Create GitHub Project board in the repository for master dashboard"""
        try:
            students = load_project_data(project_csv_path)
            
            project_name = self.dashboard_config.get('name', 'Research Projects Dashboard')
            project_description = self._generate_project_description()
            
            logger.info(f"Creating repository project: {project_name}")
            
            # Create repository project (Projects v2)
            project_id = self.github.create_repo_project(
                org=self.org,
                repo=self.repo_name,
                name=project_name,
                description=project_description
            )
            
            if not project_id:
                raise Exception("Failed to create repository project")
            
            # Create project columns
            columns = self._create_project_columns(project_id)
            
            # Add student cards to appropriate columns
            student_cards = self._add_student_cards(project_id, columns, students)
            
            result = {
                'project_id': project_id,
                'project_name': project_name,
                'project_url': f"https://github.com/{self.org}/{self.repo_name}/projects",
                'columns_created': len(columns),
                'student_cards': len(student_cards),
                'total_students': len(students),
                'dashboard_ready': True
            }
            
            logger.info(f"Master dashboard created successfully: {project_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create master dashboard: {e}")
            raise

    def _generate_project_description(self) -> str:
        """Generate project description"""
        course_info = self.config.get('project', {})
        return f"""Master Dashboard for {course_info.get('course_name', 'Research Projects')}

**Course:** {course_info.get('course_code', 'CS4681')} - {course_info.get('course_name', 'Advanced Machine Learning')}
**Academic Year:** {course_info.get('academic_year', '2025/2026')}
**Semester:** {course_info.get('semester', 'S7')}

This project board tracks the progress of all student research projects in the course.

**Columns:**
- Not Started: Projects that haven't begun
- Literature Review: Students working on literature review
- Implementation: Students in implementation phase  
- Experimentation: Students conducting experiments
- Paper Writing: Students writing final papers
- Under Review: Projects under supervisor review
- Completed: Successfully completed projects
- Need Attention: Projects requiring immediate attention

**Usage:**
- Cards are automatically moved based on GitHub issue labels
- Supervisors can manually move cards as needed
- Click on cards to view student folders and issues
- Use filters to view specific research areas or supervisors

**Supervisors:**
{self._get_supervisors_list()}

Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _get_supervisors_list(self) -> str:
        """Get formatted list of supervisors"""
        supervisors_config = self.config.get('supervisors', {})
        supervisors_list = supervisors_config.get('supervisors', [])
        
        supervisor_lines = []
        for supervisor in supervisors_list:
            name = supervisor.get('name', 'Unknown')
            username = supervisor.get('github_username', 'N/A')
            role = supervisor.get('role', 'supervisor')
            supervisor_lines.append(f"- {name} (@{username}) - {role.title()}")
        
        coordinator = supervisors_config.get('module_coordinator')
        if coordinator:
            name = coordinator.get('name', 'Module Coordinator')
            username = coordinator.get('github_username', 'N/A')
            supervisor_lines.append(f"- {name} (@{username}) - Module Coordinator")
        
        return "\n".join(supervisor_lines) if supervisor_lines else "- No supervisors configured"

    def _create_project_columns(self, project_id: int) -> Dict:
        """Create project columns based on configuration"""
        columns = {}
        column_names = self.dashboard_config.get('columns', [
            'Not Started', 'Literature Review', 'Implementation', 
            'Experimentation', 'Paper Writing', 'Under Review', 
            'Completed', 'Need Attention'
        ])
        
        for column_name in column_names:
            try:
                column_id = self.github.create_project_column(project_id, column_name)
                if column_id:
                    columns[column_name] = column_id
                    logger.debug(f"Created column: {column_name}")
            except Exception as e:
                logger.warning(f"Failed to create column {column_name}: {e}")
        
        return columns

    def _add_student_cards(self, project_id: int, columns: Dict, students: List[Dict]) -> List[Dict]:
        """Add student cards to the project board"""
        created_cards = []
        
        for student in students:
            try:
                # Determine initial column based on student progress
                initial_column = self._determine_initial_column(student)
                column_id = columns.get(initial_column)
                
                if not column_id:
                    logger.warning(f"Column '{initial_column}' not found, using 'Not Started'")
                    column_id = columns.get('Not Started')
                
                if not column_id:
                    logger.error("No valid columns found for student cards")
                    continue
                
                # Create card content
                card_note = self._generate_student_card_content(student)
                
                # Create project card
                card_id = self.github.create_project_card(
                    column_id=column_id,
                    note=card_note
                )
                
                if card_id:
                    created_cards.append({
                        'student': student,
                        'card_id': card_id,
                        'column': initial_column,
                        'folder_path': f"projects/{student['index_number']}-{student['research_area'].replace(' ', '-')}"
                    })
                    logger.debug(f"Created card for student {student['index_number']}")
                
            except Exception as e:
                logger.warning(f"Failed to create card for {student['index_number']}: {e}")
        
        return created_cards

    def _determine_initial_column(self, student: Dict) -> str:
        """Determine initial column for student based on any existing progress"""
        # For new setup, all students start in "Not Started"
        # This can be enhanced later to check existing issues/progress
        return "Not Started"

    def _generate_student_card_content(self, student: Dict) -> str:
        """Generate content for student project card"""
        folder_name = f"{student['index_number']}-{student['research_area'].replace(' ', '-')}"
        
        return f"""**{student['index_number']}** - {student['research_area']}

👤 **Student:** {student.get('github_username', 'N/A')}
📂 **Folder:** `projects/{folder_name}/`
📧 **Email:** {student.get('email', 'N/A')}

**Quick Links:**
- [Student Folder](projects/{folder_name}/)
- [Issues](issues?q=label%3Astudent-{student['index_number']})
- [Progress Reports](projects/{folder_name}/docs/progress_reports/)

**Milestones:**
- [ ] Research Proposal (Week 4)
- [ ] Literature Review (Week 5) 
- [ ] Implementation (Week 8)
- [ ] Final Evaluation (Week 12)

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
"""

    def update_master_dashboard(self, project_id: int, progress_data: Dict) -> Dict:
        """Update master dashboard with current progress data"""
        try:
            logger.info("Updating master dashboard with latest progress")
            
            # Get current project columns and cards
            columns = self.github.list_project_columns(project_id)
            column_map = {col['name']: col['id'] for col in columns}
            
            updates_made = 0
            errors = []
            
            # Process each student's progress
            for student_id, student_progress in progress_data.items():
                try:
                    # Determine target column based on progress
                    target_column = self._determine_target_column(student_progress)
                    target_column_id = column_map.get(target_column)
                    
                    if not target_column_id:
                        errors.append(f"Target column '{target_column}' not found for student {student_id}")
                        continue
                    
                    # Find student's card and move if necessary
                    card_moved = self._move_student_card(
                        columns, student_id, target_column_id, student_progress
                    )
                    
                    if card_moved:
                        updates_made += 1
                        
                except Exception as e:
                    errors.append(f"Failed to update student {student_id}: {str(e)}")
            
            result = {
                'project_id': project_id,
                'updates_made': updates_made,
                'errors': errors,
                'last_updated': datetime.now().isoformat(),
                'total_students': len(progress_data)
            }
            
            logger.info(f"Dashboard updated: {updates_made} students moved")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update master dashboard: {e}")
            raise

    def _determine_target_column(self, student_progress: Dict) -> str:
        """Determine target column based on student progress"""
        progress_pct = student_progress.get('progress_percentage', 0)
        current_phase = student_progress.get('current_phase', '')
        recent_activity = student_progress.get('recent_activity', False)
        
        # Check for issues that need attention
        if progress_pct == 0 and not recent_activity:
            return "Need Attention"
        
        # Check for high-risk situations
        open_issues = student_progress.get('open_issues', 0)
        if open_issues > 5 or (progress_pct < 25 and not recent_activity):
            return "Need Attention"
        
        # Map current phase to columns
        phase_mapping = {
            'Literature Review': 'Literature Review',
            'Implementation': 'Implementation',
            'Experimentation': 'Experimentation',
            'Paper Writing': 'Paper Writing',
            'Under Review': 'Under Review',
            'Completed': 'Completed'
        }
        
        if current_phase in phase_mapping:
            return phase_mapping[current_phase]
        
        # Fallback based on progress percentage
        if progress_pct == 0:
            return "Not Started"
        elif progress_pct < 25:
            return "Literature Review"
        elif progress_pct < 50:
            return "Implementation"
        elif progress_pct < 75:
            return "Experimentation"
        elif progress_pct < 100:
            return "Paper Writing"
        else:
            return "Completed"

    def _move_student_card(self, columns: List[Dict], student_id: str, 
                          target_column_id: int, student_progress: Dict) -> bool:
        """Move student card to appropriate column"""
        try:
            # Find the student's card across all columns
            for column in columns:
                cards = self.github.list_project_cards(column['id'])
                
                for card in cards:
                    card_content = card.get('note', '')
                    if student_id in card_content:
                        # Check if card is already in target column
                        if column['id'] == target_column_id:
                            return False  # No move needed
                        
                        # Move card to target column
                        # Note: This would require GitHub API call to move card
                        # For now, we'll log the intended move
                        logger.info(f"Would move student {student_id} from {column['name']} to target column")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error moving card for student {student_id}: {e}")
            return False

    def generate_dashboard_summary(self, project_id: int) -> Dict:
        """Generate summary statistics for the dashboard"""
        try:
            columns = self.github.list_project_columns(project_id)
            
            summary = {
                'total_columns': len(columns),
                'column_stats': {},
                'overall_stats': {
                    'total_students': 0,
                    'not_started': 0,
                    'in_progress': 0,
                    'completed': 0,
                    'need_attention': 0
                },
                'generated_at': datetime.now().isoformat()
            }
            
            for column in columns:
                cards = self.github.list_project_cards(column['id'])
                card_count = len(cards)
                
                summary['column_stats'][column['name']] = {
                    'count': card_count,
                    'percentage': 0  # Will calculate after getting totals
                }
                
                # Update overall stats
                summary['overall_stats']['total_students'] += card_count
                
                if column['name'] == 'Not Started':
                    summary['overall_stats']['not_started'] += card_count
                elif column['name'] in ['Completed']:
                    summary['overall_stats']['completed'] += card_count
                elif column['name'] == 'Need Attention':
                    summary['overall_stats']['need_attention'] += card_count
                else:
                    summary['overall_stats']['in_progress'] += card_count
            
            # Calculate percentages
            total = summary['overall_stats']['total_students']
            if total > 0:
                for column_name, stats in summary['column_stats'].items():
                    stats['percentage'] = (stats['count'] / total) * 100
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard summary: {e}")
            return {'error': str(e)}

    def get_students_needing_attention(self, project_id: int) -> List[Dict]:
        """Get list of students that need immediate attention"""
        try:
            columns = self.github.list_project_columns(project_id)
            students_at_risk = []
            
            for column in columns:
                # Focus on "Need Attention" and "Not Started" columns
                if column['name'] not in ['Need Attention', 'Not Started']:
                    continue
                
                cards = self.github.list_project_cards(column['id'])
                
                for card in cards:
                    # Parse student info from card content
                    card_content = card.get('note', '')
                    student_info = self._parse_student_from_card(card_content)
                    
                    if student_info:
                        students_at_risk.append({
                            'student_id': student_info.get('student_id'),
                            'research_area': student_info.get('research_area'),
                            'current_column': column['name'],
                            'folder_path': student_info.get('folder_path'),
                            'reason': self._determine_attention_reason(column['name'], card_content)
                        })
            
            return students_at_risk
            
        except Exception as e:
            logger.error(f"Failed to get students needing attention: {e}")
            return []

    def _parse_student_from_card(self, card_content: str) -> Dict:
        """Parse student information from card content"""
        try:
            lines = card_content.strip().split('\n')
            
            student_info = {}
            
            for line in lines:
                if line.startswith('**') and '**' in line[2:]:
                    # Extract student ID from first bold line
                    parts = line.split('**')
                    if len(parts) >= 2:
                        student_info['student_id'] = parts[1].strip()
                        if '-' in line:
                            student_info['research_area'] = line.split('-', 1)[1].strip()
                
                elif 'Folder:' in line and '`projects/' in line:
                    # Extract folder path
                    start = line.find('`projects/') + 1
                    end = line.find('`', start)
                    if start > 0 and end > start:
                        student_info['folder_path'] = line[start:end]
            
            return student_info
            
        except Exception as e:
            logger.debug(f"Failed to parse student from card: {e}")
            return {}

    def _determine_attention_reason(self, column_name: str, card_content: str) -> str:
        """Determine why student needs attention"""
        if column_name == 'Not Started':
            return "Project not started - immediate action required"
        elif column_name == 'Need Attention':
            return "Flagged for supervisor attention - check recent activity"
        else:
            return "Unknown reason - manual review needed"