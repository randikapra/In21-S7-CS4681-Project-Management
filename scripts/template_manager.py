#!/usr/bin/env python3
"""
Template Manager for automated README and template deployment
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

from .utils import load_project_data, save_progress_data
from .repo_manager import RepositoryManager

class TemplateManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.repo_manager = RepositoryManager(config)
        self.templates_dir = Path('templates')
        
    def deploy_all_templates(self, projects_file: str) -> Dict:
        """Deploy all templates to repository and student folders"""
        results = {
            'successful': [],
            'failed': [],
            'summary': {}
        }
        
        try:
            # Deploy main repository templates
            main_result = self.deploy_main_repo_templates()
            if main_result['status'] == 'success':
                results['successful'].append(main_result)
            else:
                results['failed'].append(main_result)
            
            # Deploy student folder templates
            projects = load_project_data(projects_file)
            for project in projects:
                student_result = self.deploy_student_templates(project)
                if student_result['status'] == 'success':
                    results['successful'].append(student_result)
                else:
                    results['failed'].append(student_result)
            
            # Deploy issue templates
            issue_result = self.deploy_issue_templates()
            if issue_result['status'] == 'success':
                results['successful'].append(issue_result)
            else:
                results['failed'].append(issue_result)
            
            results['summary'] = {
                'total_processed': len(results['successful']) + len(results['failed']),
                'successful_count': len(results['successful']),
                'failed_count': len(results['failed']),
                'success_rate': len(results['successful']) / max(len(results['successful']) + len(results['failed']), 1) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Template deployment failed: {e}")
            results['failed'].append({'error': str(e), 'operation': 'deploy_all_templates'})
        
        return results
    
    def deploy_main_repo_templates(self) -> Dict:
        """Deploy templates to main repository"""
        try:
            # Deploy main README
            readme_content = self._load_template('repository/README.md')
            readme_content = self._substitute_placeholders(readme_content, {
                'REPOSITORY_NAME': self.repo_manager.main_repo_name,
                'ORGANIZATION': self.repo_manager.org,
                'COURSE_CODE': self.config.get('course', {}).get('code', 'CS4681'),
                'ACADEMIC_YEAR': self.config.get('course', {}).get('academic_year', '2024/2025')
            })
            
            # Create/update README.md
            success = self.repo_manager.create_or_update_file(
                'README.md', 
                readme_content, 
                'Deploy main repository README template'
            )
            
            if success:
                # Deploy project structure documentation
                structure_content = self._load_template('repository/project_structure.md')
                self.repo_manager.create_or_update_file(
                    'docs/project_structure.md',
                    structure_content,
                    'Add project structure documentation'
                )
                
                return {'status': 'success', 'operation': 'main_repo_templates', 'files_deployed': ['README.md', 'docs/project_structure.md']}
            else:
                return {'status': 'failed', 'operation': 'main_repo_templates', 'error': 'Failed to create README'}
                
        except Exception as e:
            return {'status': 'failed', 'operation': 'main_repo_templates', 'error': str(e)}
    
    def deploy_student_templates(self, project: Dict) -> Dict:
        """Deploy templates to individual student folders"""
        try:
            index_number = project['index_number']
            folder_path = f"projects/{index_number}"
            
            # Deploy student README
            readme_content = self._load_template('documentation/usage_instructions.md')
            readme_content = self._substitute_placeholders(readme_content, {
                'STUDENT_NAME': project.get('student_name', 'Student Name'),
                'INDEX_NUMBER': index_number,
                'RESEARCH_AREA': project.get('research_area', 'Research Area'),
                'SUPERVISOR_NAME': project.get('supervisor', 'Supervisor Name'),
                'START_DATE': datetime.now().strftime('%Y-%m-%d')
            })
            
            # Create student folder README
            success = self.repo_manager.create_or_update_file(
                f"{folder_path}/README.md",
                readme_content,
                f"Add README template for {index_number}"
            )
            
            if success:
                # Deploy other student templates
                templates_deployed = ['README.md']
                
                # Deploy methodology template
                if self.templates_dir.joinpath('documentation/methodology.md').exists():
                    methodology_content = self._load_template('documentation/methodology.md')
                    self.repo_manager.create_or_update_file(
                        f"{folder_path}/docs/methodology.md",
                        methodology_content,
                        f"Add methodology template for {index_number}"
                    )
                    templates_deployed.append('docs/methodology.md')
                
                return {
                    'status': 'success', 
                    'operation': 'student_templates',
                    'student': project,
                    'templates_deployed': templates_deployed
                }
            else:
                return {
                    'status': 'failed', 
                    'operation': 'student_templates',
                    'student': project,
                    'error': 'Failed to create student README'
                }
                
        except Exception as e:
            return {
                'status': 'failed', 
                'operation': 'student_templates',
                'student': project,
                'error': str(e)
            }
    
    def deploy_issue_templates(self) -> Dict:
        """Deploy GitHub issue templates"""
        try:
            templates_deployed = []
            
            # Deploy progress report template
            if self.templates_dir.joinpath('issues/progress_report.md').exists():
                progress_template = self._load_template('issues/progress_report.md')
                success = self.repo_manager.create_or_update_file(
                    '.github/ISSUE_TEMPLATE/progress_report.md',
                    progress_template,
                    'Add progress report issue template'
                )
                if success:
                    templates_deployed.append('progress_report.md')
            
            # Deploy other issue templates
            issue_templates = ['literature_review.md', 'methodology.md', 'mid_evaluation.md', 'final_evaluation.md']
            for template_name in issue_templates:
                template_path = self.templates_dir.joinpath(f'issues/{template_name}')
                if template_path.exists():
                    template_content = self._load_template(f'issues/{template_name}')
                    success = self.repo_manager.create_or_update_file(
                        f'.github/ISSUE_TEMPLATE/{template_name}',
                        template_content,
                        f'Add {template_name} issue template'
                    )
                    if success:
                        templates_deployed.append(template_name)
            
            return {
                'status': 'success',
                'operation': 'issue_templates',
                'templates_deployed': templates_deployed
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'operation': 'issue_templates', 
                'error': str(e)
            }
    
    def _load_template(self, template_path: str) -> str:
        """Load template file content"""
        full_path = self.templates_dir.joinpath(template_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _substitute_placeholders(self, content: str, placeholders: Dict) -> str:
        """Substitute placeholders in template content"""
        for placeholder, value in placeholders.items():
            content = content.replace(f'{{{placeholder}}}', str(value))
        return content