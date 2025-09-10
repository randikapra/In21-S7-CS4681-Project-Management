"""
Master project dashboard creation and management
"""

import logging
from typing import Dict, List, Optional
from .github_client import GitHubClient

logger = logging.getLogger(__name__)

class MasterProjectManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization'] #config['repository']['organization']
        self.master_config = config.get('master_dashboard', {}) #self.master_config = config['master_project']
        
#     def create_master_project(self) -> Dict:
#         """Create organization-level master project dashboard"""
#         try:
#             project_name = self.master_config['name']
#             project_description = f"""Master dashboard for tracking all project research projects.

# **Course:** {self.master_config.get('course_code', 'Advanced Research')}
# **Supervisor:** {self.master_config.get('supervisor', 'Research Team')}
# **Academic Year:** {self.master_config.get('academic_year', '2024')}

# This dashboard provides an overview of all project research projects, their progress, and milestones.
# """
            
#             logger.info(f"Creating master project: {project_name}")
            
#             # Create organization project
#             project = self.github.create_project(
#                 org=self.org,
#                 name=project_name,
#                 description=project_description
#             )
            
#             project_id = project['id']
            
#             # Create columns based on configuration
#             columns = self._create_project_columns(project_id)
            
#             # Store project information
#             project_info = {
#                 'id': project_id,
#                 'name': project_name,
#                 'url': project['html_url'],
#                 'columns': columns,
#                 'status': 'created'
#             }
            
#             logger.info(f"Master project created successfully: {project['html_url']}")
#             return project_info
            
#         except Exception as e:
#             logger.error(f"Failed to create master project: {e}")
#             raise
    # In your master_project.py, replace the create_master_project method with this:

    def create_master_project(self) -> Dict:
        """Create repository-level master project dashboard"""
        try:
            project_name = self.master_config['name']
            project_description = f"""Master dashboard for tracking all project research projects.

    **Course:** {self.master_config.get('course_code', 'Advanced Research')}
    **Supervisor:** {self.master_config.get('supervisor', 'Research Team')}
    **Academic Year:** {self.master_config.get('academic_year', '2024')}

    This dashboard provides an overview of all project research projects, their progress, and milestones.
    """
            
            logger.info(f"Creating master project: {project_name}")
            
            # Create a dedicated repository for the master project dashboard
            master_repo_name = f"{project_name.replace(' ', '-').lower()}-repo"
            
            # Create repository first
            repo_created = self.github.create_repository(
                org=self.org,
                repo_name=master_repo_name,
                description=f"Repository for {project_name}",
                private=True
            )
            
            if not repo_created:
                raise Exception("Failed to create master repository")
            
            # Create repository project (this still works)
            project_id = self.github.create_repo_project(
                org=self.org,
                repo=master_repo_name,
                name=project_name,
                description=project_description
            )
            
            if not project_id:
                raise Exception("Failed to create repository project")
            
            # Create columns based on configuration
            columns = self._create_project_columns(project_id)
            
            # Store project information
            project_info = {
                'id': project_id,
                'name': project_name,
                'repository': master_repo_name,
                'url': f"https://github.com/{self.org}/{master_repo_name}/projects",
                'columns': columns,
                'status': 'created'
            }
            
            logger.info(f"Master project created successfully in repository: {master_repo_name}")
            return project_info
            
        except Exception as e:
            logger.error(f"Failed to create master project: {e}")
            raise
    
    def _create_project_columns(self, project_id: int) -> Dict:
        """Create columns for the master project"""
        columns = {}
        column_names = self.master_config['columns']
        
        for column_name in column_names:
            try:
                column = self.github.create_project_column(project_id, column_name)
                columns[column_name] = {
                    'id': column['id'],
                    'name': column_name,
                    'url': column['url']
                }
                logger.debug(f"Created column: {column_name}")
            except Exception as e:
                logger.error(f"Failed to create column {column_name}: {e}")
        
        return columns
    
    def add_project_card(self, project_id: int, project_data: Dict, column_name: str = None) -> Dict:
        """Add project card to master project"""
        if not column_name:
            column_name = self.master_config['columns'][0]  # Default to first column
        
        try:
            # Get column ID
            columns = self.github.list_project_columns(project_id)
            target_column = None
            for column in columns:
                if column['name'] == column_name:
                    target_column = column
                    break
            
            if not target_column:
                raise ValueError(f"Column '{column_name}' not found")
            
            # Create card content
            card_content = self._generate_project_card_content(project_data)
            
            # Create card
            card = self.github.create_project_card(
                column_id=target_column['id'],
                note=card_content
            )
            
            logger.info(f"Added project card: {project_data['index_number']}")
            return card
            
        except Exception as e:
            logger.error(f"Failed to add project card: {e}")
            raise
    
    def _generate_project_card_content(self, project_data: Dict) -> str:
        """Generate content for project project card"""
        repo_name = self._generate_repo_name(project_data)
        repo_url = f"https://github.com/{self.org}/{repo_name}"
        
        content = f"""**{project_data['index_number']}**
📚 **Research Area:** {project_data['research_area']}
🔗 **Repository:** [{repo_name}]({repo_url})
📧 **Email:** {project_data.get('email', 'N/A')}
📅 **Started:** {project_data.get('start_date', 'TBD')}

**Progress:** 0% (Not Started)
**Last Update:** {project_data.get('last_update', 'Never')}
**Status:** Not Started
"""
        return content
    
    def _generate_repo_name(self, project_data: Dict) -> str:
        """Generate repository name for project"""
        pattern = self.config['repository']['naming_pattern']
        return pattern.format(
            project_id=project_data['index_number'],
            research_area=project_data['research_area'].replace(' ', '-').replace('_', '-')
        )
    
    def update_project_card(self, project_id: int, project_data: Dict, progress_data: Dict) -> bool:
        """Update project card with progress information"""
        try:
            # Find project card
            columns = self.github.list_project_columns(project_id)
            project_card = None
            current_column = None
            
            for column in columns:
                cards = self.github.list_project_cards(column['id'])
                for card in cards:
                    if card.get('note') and project_data['index_number'] in card['note']:
                        project_card = card
                        current_column = column
                        break
                if project_card:
                    break
            
            if not project_card:
                logger.warning(f"project card not found: {project_data['index_number']}")
                return False
            
            # Update card content
            updated_content = self._generate_updated_card_content(project_data, progress_data)
            
            # Move card to appropriate column based on progress
            target_column = self._determine_target_column(progress_data)
            
            # Note: GitHub API doesn't provide direct card update
            # This would require additional implementation for card movement and content update
            
            logger.info(f"Updated project card: {project_data['index_number']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update project card: {e}")
            return False
    
    def _generate_updated_card_content(self, project_data: Dict, progress_data: Dict) -> str:
        """Generate updated content for project card"""
        repo_name = self._generate_repo_name(project_data)
        repo_url = f"https://github.com/{self.org}/{repo_name}"
        
        # Determine status based on progress
        progress_percent = progress_data.get('progress_percentage', 0)
        if progress_percent == 0:
            status = "Not Started"
        elif progress_percent < 25:
            status = "Literature Review"
        elif progress_percent < 50:
            status = "Implementation"
        elif progress_percent < 75:
            status = "Experimentation"
        elif progress_percent < 100:
            status = "Paper Writing"
        else:
            status = "Completed"
        
        content = f"""**{project_data['index_number']}**
📚 **Research Area:** {project_data['research_area']}
🔗 **Repository:** [{repo_name}]({repo_url})
📧 **Email:** {project_data.get('email', 'N/A')}
📅 **Started:** {progress_data.get('created_at', 'TBD')}

**Progress:** {progress_percent:.1f}% ({status})
**Last Update:** {progress_data.get('updated_at', 'Never')}
**Open Issues:** {progress_data.get('open_issues', 0)}
**Closed Issues:** {progress_data.get('closed_issues', 0)}
**Commits:** {progress_data.get('commits_count', 0)}
"""
        return content
    
    def _determine_target_column(self, progress_data: Dict) -> str:
        """Determine target column based on progress data"""
        progress_percent = progress_data.get('progress_percentage', 0)
        
        if progress_percent == 0:
            return "Not Started"
        elif progress_percent < 25:
            return "Literature Review"
        elif progress_percent < 50:
            return "Implementation"
        elif progress_percent < 75:
            return "Experimentation"
        elif progress_percent < 100:
            return "Paper Writing"
        else:
            return "Completed"
    
    def get_master_project_info(self) -> Dict:
        """Get master project information"""
        try:
            # This would need to be stored/retrieved from config or database
            # For now, return basic info
            return {
                'name': self.master_config['name'],
                'organization': self.org,
                'columns': self.master_config['columns']
            }
        except Exception as e:
            logger.error(f"Failed to get master project info: {e}")
            return {}
    
    def generate_master_dashboard_summary(self, project_id: int) -> Dict:
        """Generate summary statistics for master dashboard"""
        try:
            columns = self.github.list_project_columns(project_id)
            summary = {
                'total_projects': 0,
                'by_status': {},
                'completion_rate': 0
            }
            
            for column in columns:
                cards = self.github.list_project_cards(column['id'])
                card_count = len(cards)
                summary['by_status'][column['name']] = card_count
                summary['total_projects'] += card_count
            
            # Calculate completion rate
            completed = summary['by_status'].get('Completed', 0)
            if summary['total_projects'] > 0:
                summary['completion_rate'] = (completed / summary['total_projects']) * 100
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard summary: {e}")
            return {}


