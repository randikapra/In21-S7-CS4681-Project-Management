"""
Single repository creation and management with project folders
"""

import logging
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .github_client import GitHubClient
from .utils import load_project_data, generate_repo_name, batch_process

logger = logging.getLogger(__name__)

class RepositoryManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        self.templates_dir = '/home/oshadi/research_workspace/In21-S7-CS4681-Project-Management/templates'
        self.main_repo_name = config.get('project', {}).get('main_project_name', 'In21-S7-CS4681-AML-Research-Projects')
        self.logger = logging.getLogger(__name__)
    
    def create_main_repository(self, project_csv_path: str) -> Dict:
        """Create single main repository with project folders"""
        try:
            projects = load_project_data(project_csv_path)
            
            results = {
                'main_repo_created': False,
                'project_folders_created': [],
                'failed_folders': [],
                'total_projects': len(projects),
                'summary': {}
            }
            
            logger.info(f"Creating main repository '{self.main_repo_name}' for {len(projects)} projects")
            
            # Create main repository
            main_repo_success = self.create_single_repository()
            if not main_repo_success:
                raise Exception("Failed to create main repository")
            
            results['main_repo_created'] = True
            
            # Create project folders in batches
            def create_folder(project):
                return self.create_student_folder(project)
            
            batch_results = batch_process(projects, create_folder, batch_size=10, delay=2.0)
            
            # Process results
            for result in batch_results:
                if result.get('status') == 'success':
                    results['project_folders_created'].append(result)
                else:
                    results['failed_folders'].append(result)
            
            # Generate summary
            results['summary'] = {
                'success_count': len(results['project_folders_created']),
                'failure_count': len(results['failed_folders']),
                'success_rate': (len(results['project_folders_created']) / results['total_projects']) * 100 if results['total_projects'] > 0 else 0
            }
            
            logger.info(f"Repository setup completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to create main repository: {e}")
            raise
    
    def create_single_repository(self, project_count: int = 0) -> bool:
        """Create the main repository or use existing one"""
        try:
            description = f"Research Projects Repository - {self.config.get('project', {}).get('course_name', 'Advanced Machine Learning')}"
            
            # Check if repository already exists
            existing_repo = self.github.get_repository(self.org, self.main_repo_name)
            
            if existing_repo:
                logger.info(f"Repository '{self.main_repo_name}' already exists, using existing repository")
                # Setup structure in existing repository
                self.setup_main_repository_structure(project_count)
                return True
            else:
                # Create new repository
                success = self.github.create_repository(
                    org=self.org,
                    repo_name=self.main_repo_name,
                    description=description,
                    private=self.config.get('repository', {}).get('private', True)
                )
                
                if success:
                    # Setup main repository structure
                    self.setup_main_repository_structure(project_count)
                    logger.info(f"Main repository '{self.main_repo_name}' created successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating main repository: {e}")
            return False

    def create_file_in_repo(self, path: str, content: str, message: str) -> bool:
        """Create file in main repository"""
        try:
            # Check if file already exists
            existing_file = self.github.get_repository_file(self.org, self.main_repo_name, path)
            
            if existing_file:
                # Update existing file
                success = self.github.update_repository_file(
                    org=self.org,
                    repo=self.main_repo_name,
                    path=path,
                    content=content,
                    message=f"Update {path}",
                    sha=existing_file['sha']
                )
            else:
                # Create new file
                success = self.github.create_file(
                    org=self.org,
                    repo=self.main_repo_name,
                    path=path,
                    message=message,
                    content=content
                )
            
            if success:
                logger.debug(f"Created/updated file: {path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create/update file {path}: {e}")
            return False

    def setup_existing_repository(self, project_csv_path: str) -> Dict:
        """Setup structure in existing repository"""
        try:
            projects = load_project_data(project_csv_path)
            
            results = {
                'structure_created': False,
                'student_folders_created': [],
                'failed_folders': [],
                'total_students': len(projects),
                'summary': {}
            }
            
            logger.info(f"Setting up existing repository '{self.main_repo_name}' for {len(projects)} students")
            
            # Check if repository exists
            existing_repo = self.github.get_repository(self.org, self.main_repo_name)
            if not existing_repo:
                raise Exception(f"Repository '{self.main_repo_name}' does not exist")
            
            # Setup main repository structure
            structure_result = self.setup_main_repository_structure()
            results['structure_created'] = len(structure_result.get('errors', [])) == 0
            
            # Create student folders
            for student in projects:
                folder_result = self.create_student_folder(student)
                if folder_result.get('status') == 'success':
                    results['student_folders_created'].append(folder_result)
                else:
                    results['failed_folders'].append(folder_result)
            
            # Generate summary
            results['summary'] = {
                'success_count': len(results['student_folders_created']),
                'failure_count': len(results['failed_folders']),
                'success_rate': (len(results['student_folders_created']) / results['total_students']) * 100 if results['total_students'] > 0 else 0
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to setup existing repository: {e}")
            raise

    def create_student_folder(self, student: Dict) -> Dict:
        """Create folder structure for individual student"""
        try:
            folder_name = f"{student['index_number']}-{student['research_area'].replace(' ', '-').replace('/', '-')}"
            
            # Create student folder structure
            folder_structure = [
                f"projects/{folder_name}/README.md",
                f"projects/{folder_name}/docs/research_proposal.md",
                f"projects/{folder_name}/docs/literature_review.md",
                f"projects/{folder_name}/docs/methodology.md",
                f"projects/{folder_name}/docs/usage_instructions.md",
                f"projects/{folder_name}/docs/progress_reports/.gitkeep",
                f"projects/{folder_name}/src/.gitkeep",
                f"projects/{folder_name}/data/.gitkeep",
                f"projects/{folder_name}/experiments/.gitkeep",
                f"projects/{folder_name}/results/.gitkeep",
                f"projects/{folder_name}/requirements.txt"
            ]
            
            created_files = []
            errors = []
            
            for file_path in folder_structure:
                content = self.get_student_file_content(file_path, student)
                success = self.create_file_in_repo(file_path, content, f"Initialize {file_path} for {student['index_number']}")
                
                if success:
                    created_files.append(file_path)
                else:
                    errors.append(file_path)
            
            return {
                'status': 'success' if len(errors) == 0 else 'partial',
                'student': student,
                'folder_name': folder_name,
                'created_files': created_files,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error creating folder for {student['index_number']}: {e}")
            return {
                'status': 'error',
                'student': student,
                'error': str(e)
            }

    def get_student_file_content(self, file_path: str, student: Dict) -> str:
        """Get appropriate content for student files"""
        if file_path.endswith('README.md') and 'projects/' in file_path:
            return self.generate_project_readme(student)
        elif file_path.endswith('research_proposal.md'):
            return self.generate_proposal_template(student)
        elif file_path.endswith('literature_review.md'):
            return self.generate_literature_review_template(student)
        elif file_path.endswith('methodology.md'):
            return self.generate_methodology_template(student)
        elif file_path.endswith('requirements.txt'):
            return self.load_template('project/requirements.txt') or self.generate_requirements_template()
        elif file_path.endswith('.gitkeep'):
            return "# This file keeps the directory in git\n# You can delete this file once you add other files to this directory\n"
        elif file_path.endswith('usage_instructions.md'):
            return self.load_template('project/usage_instructions.md') or "# Student Usage Instructions\n\n[Instructions will be loaded from template]"
        else:
            return "# Placeholder file\n"

    def setup_main_repository_structure(self) -> Dict:
        """Setup main repository structure and files"""
        setup_results = {
            'files_created': [],
            'milestones_created': [],
            'errors': []
        }
        
        try:
            # Create main repository files
            main_files = [
                ('README.md', self.load_template_with_substitution('repository/main_readme.md')),
                ('.gitignore', self.load_template('repository/.gitignore')),
                ('requirements.txt', self.load_template('repository/requirements.txt')),
                ('docs/project_overview.md', self.load_template_with_substitution('documentation/project_overview.md')),
                ('docs/project_guidelines.md', self.load_template('documentation/project_guidelines.md')),
                ('docs/supervisor_guide.md', self.load_template('documentation/supervisor_guide.md')),
                ('projects/README.md', self.load_template('repository/projects_readme.md')),
                ('templates/project_readme_template.md', self.load_template('project/project_readme_template.md')),
                ('.github/ISSUE_TEMPLATE/progress_report.md', self.load_template('issues/progress_report.md')),
                ('.github/ISSUE_TEMPLATE/milestone_submission.md', self.load_template('issues/milestone_submission.md'))
            ]
            
            for file_path, content in main_files:
                if content:
                    success = self.create_file_in_repo(file_path, content, f"Initialize {file_path}")
                    if success:
                        setup_results['files_created'].append(file_path)
                    else:
                        setup_results['errors'].append(f"Failed to create {file_path}")
            
            # Create project milestones
            milestones_result = self.create_project_milestones()
            setup_results['milestones_created'] = milestones_result
            
        except Exception as e:
            logger.error(f"Error setting up main repository structure: {e}")
            setup_results['errors'].append(str(e))
        
        return setup_results
    
    def create_project_milestones(self) -> List[Dict]:
        """Create project milestones for the main repository"""
        created_milestones = []
        
        try:
            milestones_config = self.config.get('milestones', {})
            
            for milestone_key, milestone_data in milestones_config.items():
                title = milestone_data.get('title', milestone_key.replace('_', ' ').title())
                description = milestone_data.get('description', f'{title} milestone for all projects')
                
                # Calculate due date based on week
                if 'week' in milestone_data:
                    due_date = (datetime.now() + timedelta(weeks=milestone_data['week'])).isoformat()
                else:
                    due_date = None
                
                milestone_id = self.github.create_milestone(
                    org=self.org,
                    repo=self.main_repo_name,
                    title=title,
                    description=description,
                    due_date=due_date
                )
                
                if milestone_id:
                    created_milestones.append({
                        'id': milestone_id,
                        'key': milestone_key,
                        'title': title,
                        'weight': milestone_data.get('weight', 1)
                    })
                    logger.debug(f"Created milestone: {title}")
            
        except Exception as e:
            logger.error(f"Error creating milestones: {e}")
        
        return created_milestones
    
    def load_template(self, template_path: str) -> Optional[str]:
        """Load template content from file"""
        try:
            full_path = os.path.join(self.templates_dir, template_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Template not found: {full_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
    def load_template_with_substitution(self, template_path: str, substitutions: Dict = None) -> Optional[str]:
        """Load template and perform variable substitutions"""
        try:
            template_content = self.load_template(template_path)
            if not template_content:
                return None
            
            # Default substitutions from config
            default_substitutions = {
                'MAIN_REPO_NAME': self.main_repo_name,
                'COURSE_NAME': self.config.get('project', {}).get('course_name', 'Advanced Machine Learning'),
                'COURSE_CODE': self.config.get('project', {}).get('course_code', 'CS4681'),
                'ACADEMIC_YEAR': self.config.get('project', {}).get('academic_year', '2024/2025'),
                'SEMESTER': self.config.get('project', {}).get('semester', '7'),
                'ORGANIZATION': self.org,
                'CURRENT_DATE': datetime.now().strftime('%Y-%m-%d'),
                'SUPERVISOR_USERNAME': self.config.get('supervisors', [{}])[0].get('github_username', 'supervisor')
            }
            
            # Merge with provided substitutions
            if substitutions:
                default_substitutions.update(substitutions)
            
            # Perform substitutions
            for key, value in default_substitutions.items():
                template_content = template_content.replace(f'{{{key}}}', str(value))
            
            return template_content
            
        except Exception as e:
            logger.error(f"Error loading template with substitution {template_path}: {e}")
            return None
    
    def generate_project_readme(self, student: Dict) -> str:
        """Generate personalized README for student folder"""
        substitutions = {
            'STUDENT_INDEX': student['index_number'],
            'RESEARCH_AREA': student['research_area'],
            'GITHUB_USERNAME': student.get('github_username', 'Not provided'),
            'STUDENT_EMAIL': student.get('email', 'Not provided'),
            'FOLDER_NAME': student['research_area'].replace(' ', '-')
        }
        
        return self.load_template_with_substitution('project/project_readme.md', substitutions)
    
    def generate_proposal_template(self, student: Dict) -> str:
        """Generate research proposal template"""
        substitutions = {
            'STUDENT_INDEX': student['index_number'],
            'RESEARCH_AREA': student['research_area']
        }
        
        return self.load_template_with_substitution('project/research_proposal.md', substitutions)
    
    def generate_literature_review_template(self, student: Dict) -> str:
        """Generate literature review template for project"""
        substitutions = {
            'STUDENT_INDEX': student['index_number'],
            'RESEARCH_AREA': student['research_area']
        }
        
        return self.load_template_with_substitution('project/literature_review.md', substitutions)
    
    def generate_methodology_template(self, student: Dict) -> str:
        """Generate methodology template"""
        substitutions = {
            'STUDENT_INDEX': student['index_number'],
            'RESEARCH_AREA': student['research_area']
        }
        
        return self.load_template_with_substitution('project/methodology.md', substitutions)
    
    def generate_requirements_template(self) -> str:
        """Fallback requirements template if file not found"""
        return """# Core ML Libraries
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=1.0.0
matplotlib>=3.5.0
seaborn>=0.11.0

# Deep Learning (uncomment as needed)
# torch>=1.10.0
# torchvision>=0.11.0
# tensorflow>=2.8.0
# keras>=2.8.0

# NLP Libraries (uncomment as needed)
# nltk>=3.7.0
# spacy>=3.4.0
# transformers>=4.15.0

# Computer Vision (uncomment as needed)
# opencv-python>=4.5.0
# pillow>=8.3.0

# Utilities
jupyter>=1.0.0
tqdm>=4.62.0
python-dotenv>=0.19.0

# Add your specific requirements below
"""
        
    def create_or_update_file(self, file_path: str, content: str, commit_message: str) -> bool:
        """Create or update a file in the repository"""
        try:
            # Check if file already exists
            existing_file = self.github.get_repository_file(self.org, self.main_repo_name, file_path)
            
            if existing_file:
                # Update existing file
                success = self.github.update_repository_file(
                    org=self.org,
                    repo=self.main_repo_name,
                    path=file_path,
                    content=content,
                    message=commit_message,
                    sha=existing_file['sha']
                )
            else:
                # Create new file
                success = self.github.create_file(
                    org=self.org,
                    repo=self.main_repo_name,
                    path=file_path,
                    message=commit_message,
                    content=content
                )
            
            if success:
                self.logger.info(f"Created/updated file: {file_path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to create/update file {file_path}: {e}")
            return False
            
    def update_repository_settings(self) -> bool:
        """Update main repository settings"""
        try:
            # Enable issues and projects
            settings = {
                'has_issues': True,
                'has_projects': True,
                'has_wiki': False,
                'allow_merge_commit': True,
                'allow_squash_merge': True,
                'allow_rebase_merge': False
            }
            
            logger.debug(f"Repository settings configured for {self.main_repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating repository settings: {e}")
            return False
    
    def delete_repository(self) -> bool:
        """Delete main repository (use with caution)"""
        try:
            response = self.github.make_request('DELETE', f'/repos/{self.org}/{self.main_repo_name}')
            
            if response.status_code == 204:
                logger.warning(f"Deleted repository: {self.main_repo_name}")
                return True
            else:
                logger.error(f"Failed to delete repository: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting repository {self.main_repo_name}: {e}")
            return False