"""
project invitation automation and access management
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from .github_client import GitHubClient
from .utils import load_project_data, load_supervisor_data, extract_github_username

logger = logging.getLogger(__name__)

class InvitationManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        
    def send_bulk_student_invitations(self, project_csv_path: str) -> Dict:
        """Send invitations to all students in CSV file (students only)"""
        try:
            projects = load_project_data(project_csv_path)
            
            results = {
                'successful': [],
                'failed': [],
                'total_processed': 0,
                'summary': {}
            }
            
            logger.info(f"Starting bulk student invitation process for {len(projects)} students")
            
            for i, project in enumerate(projects, 1):
                logger.info(f"Processing student {i}/{len(projects)}: {project['Student_ID']}")
                
                # Send invitation for the main shared repository
                invitation_result = self.send_student_invitation(project)
                
                if invitation_result['status'] == 'success':
                    results['successful'].append(invitation_result)
                else:
                    results['failed'].append(invitation_result)
                
                results['total_processed'] += 1
                
                # Rate limiting - pause between requests
                if i % 10 == 0:
                    logger.info(f"Processed {i} students, pausing for rate limit...")
                    time.sleep(2)
            
            # Generate summary
            results['summary'] = {
                'success_count': len(results['successful']),
                'failure_count': len(results['failed']),
                'success_rate': (len(results['successful']) / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
            }
            
            logger.info(f"Bulk student invitation completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send bulk student invitations: {e}")
            raise
    
    def send_student_invitation(self, project_data: Dict) -> Dict:
        """Send invitation to individual student for the shared repository"""
        try:
            # Add student as collaborator with write permission to the main repository
            student_result = self._add_student_collaborator(project_data)
            
            if student_result['success']:
                status = 'success'
                message = 'Student invitation sent successfully'
            else:
                status = 'failed'
                message = f"Student invitation failed: {student_result.get('error', 'Unknown error')}"
            
            return {
                'status': status,
                'student': project_data,
                'repo_name': self.config['repository']['name'],
                'message': message,
                'invitation_details': [student_result],
                'error': student_result.get('error') if not student_result['success'] else None
            }
            
        except Exception as e:
            logger.error(f"Failed to send invitation for {project_data['Student_ID']}: {e}")
            return {
                'status': 'error',
                'student': project_data,
                'repo_name': self.config['repository']['name'],
                'error': str(e)
            }

    def _add_student_collaborator(self, project_data: Dict) -> Dict:
        """Add student as collaborator with write permission"""
        try:
            # Extract GitHub username from the GitHub_User_Name column
            github_value = project_data.get('GitHub_User_Name', '')
            
            if not github_value:
                return {
                    'type': 'student',
                    'target': project_data['Student_ID'],
                    'success': False,
                    'error': 'GitHub username not provided in CSV'
                }
            
            # Extract clean username using your function
            username = extract_github_username(github_value)
            
            if not username:
                return {
                    'type': 'student',
                    'target': project_data['Student_ID'],
                    'success': False,
                    'error': 'Invalid GitHub username format'
                }
            
            # Use the actual repository name from config
            repo_name = self.config['repository']['name']
            
            success = self.github.add_collaborator(
                org=self.org,
                repo=repo_name, 
                username=username,
                permission='push'  # Write access to repository
            )
            
            if success:
                logger.info(f"Added student {username} ({project_data['Student_ID']}) to {repo_name}")
                return {
                    'type': 'student',
                    'target': username,
                    'success': True,
                    'permission': 'push',
                    'student_id': project_data['Student_ID'],
                    'student_name': project_data.get('Student_Name', '')
                }
            else:
                return {
                    'type': 'student', 
                    'target': username,
                    'success': False,
                    'error': 'Failed to add collaborator - check if username exists and repository permissions',
                    'student_id': project_data['Student_ID']
                }
                
        except Exception as e:
            logger.error(f"Failed to add student {project_data['Student_ID']}: {e}")
            return {
                'type': 'student',
                'target': project_data['Student_ID'],
                'success': False,
                'error': str(e)
            }

    def setup_folder_protection_with_codeowners(self, project_csv_path: str) -> Dict:
        """Setup CODEOWNERS file and branch protection for folder-level control"""
        try:
            projects = load_project_data(project_csv_path)
            repo_name = self.config['repository']['name']
            
            results = {
                'codeowners_created': False,
                'branch_protection_set': False,
                'errors': [],
                'warnings': []
            }
            
            # Step 1: Create CODEOWNERS content
            codeowners_content = "# CODEOWNERS file for folder-level access control\n"
            codeowners_content += "# Each student can only modify their own folder via pull requests\n"
            codeowners_content += "# Direct pushes to main branch require code owner approval\n\n"
            
            for project in projects:
                github_value = project.get('GitHub_User_Name', '')
                username = extract_github_username(github_value) if github_value else None
                
                if username:
                    folder_path = f"projects/{project['Student_ID']}/"
                    codeowners_content += f"{folder_path}* @{username}\n"
            
            # Protect root files (only admins can modify)
            codeowners_content += f"\n# Root files - only repository admins can modify\n"
            codeowners_content += f"*.md @aaivu/admin\n"
            codeowners_content += f".github/* @aaivu/admin\n"
            codeowners_content += f"docs/* @aaivu/admin\n"
            
            # Step 2: Create/update CODEOWNERS file in repository
            try:
                success = self.github.create_or_update_file(
                    org=self.org,
                    repo=repo_name,
                    path=".github/CODEOWNERS",
                    content=codeowners_content,
                    message="Setup CODEOWNERS for student folder access control",
                    branch="main"
                )
                
                if success:
                    results['codeowners_created'] = True
                    logger.info("CODEOWNERS file created successfully")
                else:
                    results['errors'].append("Failed to create CODEOWNERS file")
                    
            except Exception as e:
                results['errors'].append(f"CODEOWNERS creation error: {str(e)}")
            
            # Step 3: Setup branch protection rules that require code owner reviews
            try:
                protection_config = {
                    "required_status_checks": {
                        "strict": False,
                        "contexts": []
                    },
                    "enforce_admins": False,
                    "required_pull_request_reviews": {
                        "required_approving_review_count": 1,
                        "dismiss_stale_reviews": False,
                        "require_code_owner_reviews": True,  # This enforces CODEOWNERS
                        "restrict_dismissal": False
                    },
                    "restrictions": None,
                    "allow_force_pushes": False,
                    "allow_deletions": False
                }
                
                success = self.github.setup_branch_protection(
                    org=self.org,
                    repo=repo_name,
                    branch="main",
                    protection_config=protection_config
                )
                
                if success:
                    results['branch_protection_set'] = True
                    logger.info("Branch protection rules configured successfully")
                else:
                    results['errors'].append("Failed to setup branch protection")
                    
            except Exception as e:
                results['errors'].append(f"Branch protection error: {str(e)}")
                results['warnings'].append("Branch protection may require admin privileges or GitHub Pro/Enterprise")
            
            # Generate summary
            if results['codeowners_created'] and results['branch_protection_set']:
                results['status'] = 'success'
                results['message'] = 'Folder-level access control configured successfully'
                results['explanation'] = 'Students must create pull requests to modify their folders'
            elif results['codeowners_created']:
                results['status'] = 'partial_success'
                results['message'] = 'CODEOWNERS created, but branch protection failed'
                results['explanation'] = 'Manual branch protection setup required'
            else:
                results['status'] = 'failed'
                results['message'] = 'Failed to setup folder-level access control'
            
            results['codeowners_content'] = codeowners_content
            results['total_students'] = len(projects)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to setup folder protection: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_student_invitation_status(self, project_csv_path: str) -> Dict:
        """Check status of sent invitations for students"""
        try:
            projects = load_project_data(project_csv_path)
            status_results = {
                'accepted': [],
                'pending': [],
                'not_invited': [],
                'invalid_username': [],
                'total_checked': 0
            }
            
            repo_name = self.config['repository']['name']
            
            for project in projects:
                github_value = project.get('GitHub_User_Name', '')
                username = extract_github_username(github_value) if github_value else None
                
                if not username:
                    status_results['invalid_username'].append({
                        'project': project,
                        'student_id': project['Student_ID'],
                        'issue': 'No valid GitHub username found'
                    })
                    status_results['total_checked'] += 1
                    continue
                
                try:
                    # Check if user exists on GitHub first
                    user_exists = self.github.check_user_exists(username)
                    if not user_exists:
                        status_results['invalid_username'].append({
                            'project': project,
                            'username': username,
                            'student_id': project['Student_ID'],
                            'issue': 'GitHub user does not exist'
                        })
                        status_results['total_checked'] += 1
                        continue
                    
                    # Check if user is collaborator on main repository
                    is_collaborator = self.github.check_collaborator(self.org, repo_name, username)
                    
                    if is_collaborator:
                        status_results['accepted'].append({
                            'project': project,
                            'username': username,
                            'student_id': project['Student_ID'],
                            'repo': repo_name,
                            'status': 'collaborator'
                        })
                    else:
                        # Check if invitation is pending
                        has_pending = self.github.check_pending_invitation(self.org, repo_name, username)
                        
                        if has_pending:
                            status_results['pending'].append({
                                'project': project,
                                'username': username,
                                'student_id': project['Student_ID'],
                                'repo': repo_name,
                                'status': 'pending_invitation'
                            })
                        else:
                            status_results['not_invited'].append({
                                'project': project,
                                'username': username,
                                'student_id': project['Student_ID'],
                                'repo': repo_name,
                                'status': 'not_invited'
                            })
                    
                except Exception as e:
                    logger.error(f"Error checking status for {username}: {e}")
                    status_results['invalid_username'].append({
                        'project': project,
                        'username': username,
                        'student_id': project['Student_ID'],
                        'issue': f'API error: {str(e)}'
                    })
                
                status_results['total_checked'] += 1
                
                # Rate limiting
                time.sleep(0.5)
            
            return status_results
            
        except Exception as e:
            logger.error(f"Failed to check invitation status: {e}")
            raise

    def retry_failed_student_invitations(self, failed_results: List[Dict]) -> Dict:
        """Retry failed student invitations"""
        retry_results = {
            'successful': [],
            'failed': [],
            'total_retried': len(failed_results)
        }
        
        logger.info(f"Retrying {len(failed_results)} failed student invitations")
        
        for result in failed_results:
            try:
                project = result.get('student', result.get('project'))
                if not project:
                    retry_results['failed'].append({
                        'error': 'No student data in failed result',
                        'original_result': result
                    })
                    continue
                
                retry_result = self.send_student_invitation(project)
                
                if retry_result['status'] == 'success':
                    retry_results['successful'].append(retry_result)
                else:
                    retry_results['failed'].append(retry_result)
                
                time.sleep(1)  # Rate limiting between retries
                
            except Exception as e:
                retry_results['failed'].append({
                    'error': str(e),
                    'original_result': result
                })
        
        return retry_results

    def validate_student_usernames(self, project_csv_path: str) -> Dict:
        """Validate all student GitHub usernames before sending invitations"""
        try:
            projects = load_project_data(project_csv_path)
            validation_results = {
                'valid_usernames': [],
                'invalid_usernames': [],
                'missing_usernames': [],
                'total_validated': 0
            }
            
            logger.info(f"Validating GitHub usernames for {len(projects)} students")
            
            for project in projects:
                github_value = project.get('GitHub_User_Name', '')
                student_id = project['Student_ID']
                
                if not github_value:
                    validation_results['missing_usernames'].append({
                        'student_id': student_id,
                        'student_name': project.get('Student_Name', ''),
                        'issue': 'No GitHub username provided'
                    })
                    validation_results['total_validated'] += 1
                    continue
                
                try:
                    username = extract_github_username(github_value)
                    
                    if not username:
                        validation_results['invalid_usernames'].append({
                            'student_id': student_id,
                            'github_value': github_value,
                            'issue': 'Could not extract valid username'
                        })
                        validation_results['total_validated'] += 1
                        continue
                    
                    # Check if GitHub user exists
                    user_exists = self.github.check_user_exists(username)
                    
                    if user_exists:
                        validation_results['valid_usernames'].append({
                            'student_id': student_id,
                            'student_name': project.get('Student_Name', ''),
                            'username': username,
                            'original_value': github_value
                        })
                    else:
                        validation_results['invalid_usernames'].append({
                            'student_id': student_id,
                            'username': username,
                            'original_value': github_value,
                            'issue': 'GitHub user does not exist'
                        })
                    
                except Exception as e:
                    validation_results['invalid_usernames'].append({
                        'student_id': student_id,
                        'github_value': github_value,
                        'issue': f'Validation error: {str(e)}'
                    })
                
                validation_results['total_validated'] += 1
                
                # Rate limiting
                time.sleep(0.3)
            
            logger.info(f"Username validation completed. Valid: {len(validation_results['valid_usernames'])}, Invalid: {len(validation_results['invalid_usernames'])}, Missing: {len(validation_results['missing_usernames'])}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate student usernames: {e}")
            raise

    def create_student_folder_codeowners(self, project_csv_path: str) -> Dict:
        """Create CODEOWNERS file for student folder protection"""
        try:
            projects = load_project_data(project_csv_path)
            
            codeowners_content = "# CODEOWNERS - Folder-level access control\n"
            codeowners_content += "# Students can only modify their own project folders\n"
            codeowners_content += "# All changes require pull request review\n\n"
            
            valid_entries = 0
            
            for project in projects:
                github_value = project.get('GitHub_User_Name', '')
                username = extract_github_username(github_value) if github_value else None
                
                if username:
                    folder_path = f"projects/{project['Student_ID']}/"
                    codeowners_content += f"# {project.get('Student_Name', '')} - {project['Student_ID']}\n"
                    codeowners_content += f"{folder_path}* @{username}\n\n"
                    valid_entries += 1
            
            # Protect root files and docs
            codeowners_content += "# Root files and documentation - admin only\n"
            codeowners_content += "*.md @aaivu/admin\n"
            codeowners_content += ".github/* @aaivu/admin\n"
            codeowners_content += "docs/* @aaivu/admin\n"
            codeowners_content += "config/* @aaivu/admin\n"
            
            return {
                'status': 'success',
                'codeowners_content': codeowners_content,
                'total_students': len(projects),
                'valid_entries': valid_entries,
                'message': 'CODEOWNERS content generated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create CODEOWNERS: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def deploy_folder_protection(self, project_csv_path: str) -> Dict:
        """Deploy complete folder protection setup"""
        try:
            results = {
                'steps_completed': [],
                'steps_failed': [],
                'overall_status': 'in_progress'
            }
            
            # Step 1: Create and deploy CODEOWNERS
            logger.info("Step 1: Creating CODEOWNERS file...")
            codeowners_result = self.create_student_folder_codeowners(project_csv_path)
            
            if codeowners_result['status'] == 'success':
                # Deploy CODEOWNERS to repository
                try:
                    success = self.github.create_or_update_file(
                        org=self.org,
                        repo=self.config['repository']['name'],
                        path=".github/CODEOWNERS",
                        content=codeowners_result['codeowners_content'],
                        message="Add CODEOWNERS for student folder access control"
                    )
                    
                    if success:
                        results['steps_completed'].append('CODEOWNERS deployed')
                        logger.info("CODEOWNERS file deployed to repository")
                    else:
                        results['steps_failed'].append('CODEOWNERS deployment failed')
                        
                except Exception as e:
                    results['steps_failed'].append(f'CODEOWNERS deployment error: {str(e)}')
            else:
                results['steps_failed'].append(f'CODEOWNERS creation failed: {codeowners_result.get("error")}')
            
            # Step 2: Setup branch protection
            logger.info("Step 2: Setting up branch protection...")
            try:
                protection_config = {
                    "required_status_checks": None,
                    "enforce_admins": False,
                    "required_pull_request_reviews": {
                        "required_approving_review_count": 1,
                        "dismiss_stale_reviews": True,
                        "require_code_owner_reviews": True,
                        "restrict_dismissal": False
                    },
                    "restrictions": None,
                    "allow_force_pushes": False,
                    "allow_deletions": False
                }
                
                success = self.github.setup_branch_protection(
                    org=self.org,
                    repo=self.config['repository']['name'],
                    branch="main",
                    protection_config=protection_config
                )
                
                if success:
                    results['steps_completed'].append('Branch protection configured')
                    logger.info("Branch protection configured successfully")
                else:
                    results['steps_failed'].append('Branch protection setup failed')
                    
            except Exception as e:
                results['steps_failed'].append(f'Branch protection error: {str(e)}')
            
            # Determine overall status
            if len(results['steps_failed']) == 0:
                results['overall_status'] = 'success'
                results['message'] = 'Folder protection deployed successfully'
            elif len(results['steps_completed']) > 0:
                results['overall_status'] = 'partial_success'
                results['message'] = 'Partial folder protection deployed'
            else:
                results['overall_status'] = 'failed'
                results['message'] = 'Folder protection deployment failed'
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to deploy folder protection: {e}")
            return {
                'overall_status': 'error',
                'error': str(e)
            }
    
    def send_repository_invitation(self, student_data: Dict) -> Dict:
        """Send invitation to student for the main repository"""
        try:
            # Add student as collaborator with write permission to main repo
            student_result = self._add_student_collaborator(student_data)
            
            if student_result['success']:
                status = 'success'
                message = 'Student invitation sent successfully'
            else:
                status = 'failed'
                message = f"Student invitation failed: {student_result.get('error', 'Unknown error')}"
            
            return {
                'status': status,
                'student': student_data,
                'repo_name': self.config['repository']['name'],
                'message': message,
                'invitation_details': [student_result],
                'error': student_result.get('error') if not student_result['success'] else None
            }
            
        except Exception as e:
            logger.error(f"Failed to send invitation for {student_data['index_number']}: {e}")
            return {
                'status': 'error',
                'student': student_data,
                'repo_name': self.config['repository']['name'],
                'error': str(e),
                'message': f"Exception occurred: {str(e)}"
            }
    

    def check_invitation_status(self, project_csv_path: str) -> Dict:
        
        """Wrapper for check_student_invitation_status"""

        return self.check_student_invitation_status(project_csv_path)

    def send_supervisors_invitations(self) -> Dict:

        """Send invitations to supervisors"""

        results = {'successful': [], 'failed': [], 'total_processed': 0}

        

        supervisors = self.config.get('supervisors', {}).get('supervisors', [])

        repo_name = self.config['repository']['name']

        

        for supervisor in supervisors:

            username = supervisor.get('github_username')

            if username:

                success = self.send_repository_invitation(

                    self.org, repo_name, username, 'admin'

                )

                

                if success:

                    results['successful'].append({'username': username, 'role': 'supervisor'})

                else:

                    results['failed'].append({'username': username, 'error': 'Failed to send invitation'})

                

                results['total_processed'] += 1

        

        return results

# 

"""
# project invitation automation and access management
# """

# import logging
# import time
# from typing import Dict, List, Optional, Tuple
# from .github_client import GitHubClient
# from .utils import load_project_data, load_supervisor_data, extract_github_username

# logger = logging.getLogger(__name__)

# class InvitationManager:
#     def __init__(self, config: Dict):
#         self.config = config
#         self.github = GitHubClient(config['github']['token'])
#         self.org = config['github']['organization']
        
#     def send_bulk_invitations(self, project_csv_path: str) -> Dict:
#         """Send invitations to all projects in CSV file"""
#         try:
#             projects = load_project_data(project_csv_path)
#             supervisors = load_supervisor_data(self.config)
            
#             results = {
#                 'successful': [],
#                 'failed': [],
#                 'total_processed': 0,
#                 'summary': {}
#             }
            
#             logger.info(f"Starting bulk invitation process for {len(projects)} projects")
            
#             for i, project in enumerate(projects, 1):
#                 logger.info(f"Processing project {i}/{len(projects)}: {project['index_number']}")
                
#                 # Send invitation for the main shared repository
#                 invitation_result = self.send_project_invitation(project, supervisors)
                
#                 if invitation_result['status'] == 'success':
#                     results['successful'].append(invitation_result)
#                 else:
#                     results['failed'].append(invitation_result)
                
#                 results['total_processed'] += 1
                
#                 # Rate limiting - pause between requests
#                 if i % 10 == 0:
#                     logger.info(f"Processed {i} projects, pausing for rate limit...")
#                     time.sleep(2)
            
#             # Generate summary
#             results['summary'] = {
#                 'success_count': len(results['successful']),
#                 'failure_count': len(results['failed']),
#                 'success_rate': (len(results['successful']) / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
#             }
            
#             logger.info(f"Bulk invitation completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to send bulk invitations: {e}")
#             raise
    
#     def send_project_invitation(self, project_data: Dict, supervisors: List[Dict]) -> Dict:
#         """Send invitation to individual project for the shared repository"""
#         try:
#             invitation_results = []
            
#             # Add project as collaborator with write permission to the main repository
#             project_result = self._add_project_collaborator(project_data)
#             invitation_results.append(project_result)
            
#             # Add supervisors with admin permission to the main repository (only once per supervisor)
#             # Note: In bulk operations, supervisors should be added separately to avoid duplicates
            
#             # Check overall success
#             failed_invitations = [r for r in invitation_results if not r['success']]
            
#             if not failed_invitations:
#                 status = 'success'
#                 message = 'Student invitation sent successfully'
#             else:
#                 status = 'failed'
#                 message = f'Student invitation failed: {failed_invitations[0].get("error", "Unknown error")}'
            
#             return {
#                 'status': status,
#                 'project': project_data,
#                 'repo_name': self.config['repository']['name'],
#                 'message': message,
#                 'invitation_details': invitation_results
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to send invitation for {project_data['index_number']}: {e}")
#             return {
#                 'status': 'error',
#                 'project': project_data,
#                 'repo_name': self.config['repository']['name'],
#                 'error': str(e)
#             }

#     def _add_project_collaborator(self, project_data: Dict) -> Dict:
#         """Add project as collaborator with write permission"""
#         try:
#             # Extract GitHub username properly
#             username = project_data.get('github_username')
#             if not username:
#                 return {
#                     'type': 'project',
#                     'target': project_data['index_number'],
#                     'success': False,
#                     'error': 'GitHub username not provided'
#                 }
            
#             # Clean username if it's a URL
#             if 'github.com' in username or username.startswith('http'):
#                 username = extract_github_username(username)
            
#             if not username:
#                 return {
#                     'type': 'project',
#                     'target': project_data['index_number'],
#                     'success': False,
#                     'error': 'Invalid GitHub username format'
#                 }
            
#             # Use the actual repository name from config
#             repo_name = self.config['repository']['name']
            
#             success = self.github.add_collaborator(
#                 self.org,
#                 repo_name, 
#                 username,
#                 permission='push'  # Write access to repository
#             )
            
#             if success:
#                 logger.info(f"Added project {username} to {repo_name}")
#                 return {
#                     'type': 'project',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push',
#                     'index_number': project_data['index_number']
#                 }
#             else:
#                 return {
#                     'type': 'project', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator - check if username exists and repository permissions'
#                 }
                
#         except Exception as e:
#             logger.error(f"Failed to add project {project_data['index_number']}: {e}")
#             return {
#                 'type': 'project',
#                 'target': project_data['index_number'],
#                 'success': False,
#                 'error': str(e)
#             }
    
#     def _find_username_by_email(self, email: str) -> Optional[str]:
#         """Try to find GitHub username by email"""
#         if not email:
#             return None
            
#         try:
#             # Search for user by email (this is limited by GitHub API)
#             user_data = self.github.search_user_by_email(email)
#             if user_data:
#                 return user_data.get('login')
#             return None
#         except Exception as e:
#             logger.warning(f"Could not find GitHub user for email {email}: {e}")
#             return None
    
#     def _generate_repo_name(self, project: Dict) -> str:
#         """Generate repository name from project data"""
#         index_number = project['index_number']
#         research_area = project['research_area'].replace(' ', '_').replace('-', '_')
#         return f"{index_number}_{research_area}"
    
#     def retry_failed_invitations(self, failed_results: List[Dict]) -> Dict:
#         """Retry failed invitations"""
#         retry_results = {
#             'successful': [],
#             'failed': [],
#             'total_retried': len(failed_results)
#         }
        
#         logger.info(f"Retrying {len(failed_results)} failed invitations")
        
#         for result in failed_results:
#             if result['status'] == 'error':
#                 project = result['project']
#                 supervisors = load_supervisor_data(self.config)
                
#                 retry_result = self.send_project_invitation(project, supervisors)
                
#                 if retry_result['status'] == 'success':
#                     retry_results['successful'].append(retry_result)
#                 else:
#                     retry_results['failed'].append(retry_result)
                
#                 time.sleep(1)  # Rate limiting
        
#         return retry_results
    
#     def send_organization_invitations(self, project_csv_path: str) -> Dict:
#         """Send organization-level invitations to all projects"""
#         try:
#             projects = load_project_data(project_csv_path)
#             results = {
#                 'successful': [],
#                 'failed': [],
#                 'total_processed': 0
#             }
            
#             logger.info(f"Sending organization invitations to {len(projects)} projects")
            
#             for i, project in enumerate(projects, 1):
#                 logger.info(f"Inviting project {i}/{len(projects)}: {project['index_number']}")
                
#                 username = project.get('github_username')
#                 if 'github.com' in username or username.startswith('http'):
#                     username = extract_github_username(username)
                
#                 if not username:
#                     username = self._find_username_by_email(project.get('email', ''))
                
#                 if not username:
#                     results['failed'].append({
#                         'project': project,
#                         'error': 'GitHub username not found'
#                     })
#                     results['total_processed'] += 1
#                     continue
                
#                 try:
#                     success = self.github.invite_to_organization(self.org, username, 'member')
                    
#                     if success:
#                         results['successful'].append({
#                             'project': project,
#                             'username': username,
#                             'status': 'invited'
#                         })
#                     else:
#                         results['failed'].append({
#                             'project': project,
#                             'username': username,
#                             'error': 'Failed to send organization invitation'
#                         })
                    
#                 except Exception as e:
#                     results['failed'].append({
#                         'project': project,
#                         'username': username,
#                         'error': str(e)
#                     })
                
#                 results['total_processed'] += 1
                
#                 # Rate limiting
#                 if i % 10 == 0:
#                     time.sleep(2)
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to send organization invitations: {e}")
#             raise

#     def send_repository_invitation(self, student_data: Dict) -> Dict:
#         """Send invitation to student for the main repository"""
#         try:
#             # Add student as collaborator with write permission to main repo
#             student_result = self._add_student_collaborator(student_data)
            
#             if student_result['success']:
#                 status = 'success'
#                 message = 'Student invitation sent successfully'
#             else:
#                 status = 'failed'
#                 message = f"Student invitation failed: {student_result.get('error', 'Unknown error')}"
            
#             return {
#                 'status': status,
#                 'student': student_data,
#                 'repo_name': self.config['repository']['name'],
#                 'message': message,
#                 'invitation_details': [student_result],
#                 'error': student_result.get('error') if not student_result['success'] else None
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to send invitation for {student_data['index_number']}: {e}")
#             return {
#                 'status': 'error',
#                 'student': student_data,
#                 'repo_name': self.config['repository']['name'],
#                 'error': str(e),
#                 'message': f"Exception occurred: {str(e)}"
#             }
    
#     def _add_student_collaborator(self, student_data: Dict) -> Dict:
#         """Add student as collaborator with write permission"""
#         try:
#             username = student_data.get('github_username')
            
#             # Clean username if it's a URL
#             if username and ('github.com' in username or username.startswith('http')):
#                 username = extract_github_username(username)
            
#             if not username:
#                 username = self._find_username_by_email(student_data.get('email', ''))
            
#             if not username:
#                 return {
#                     'type': 'student',
#                     'target': student_data['index_number'],
#                     'success': False,
#                     'error': 'GitHub username not found'
#                 }
            
#             success = self.github.add_collaborator(
#                 org=self.org,
#                 repo=self.config['repository']['name'],
#                 username=username,
#                 permission='push'  # Write access to repository
#             )
            
#             if success:
#                 logger.info(f"Added student {username} to repository")
#                 return {
#                     'type': 'student',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push',
#                     'index_number': student_data['index_number']
#                 }
#             else:
#                 return {
#                     'type': 'student', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator - check username and repository permissions'
#                 }
                
#         except Exception as e:
#             logger.error(f"Failed to add student {student_data['index_number']}: {e}")
#             return {
#                 'type': 'student',
#                 'target': student_data['index_number'],
#                 'success': False,
#                 'error': str(e)
#             }

#     def send_supervisors_invitations(self) -> Dict:
#         """Send invitations to all supervisors"""
#         try:
#             supervisors_config = self.config.get('supervisors', {})
#             supervisors_list = supervisors_config.get('supervisors', [])
            
#             results = {
#                 'successful': [],
#                 'failed': [],
#                 'total_processed': 0
#             }
            
#             # Add main supervisors
#             for supervisor in supervisors_list:
#                 result = self._add_supervisor_collaborator(supervisor)
#                 results['total_processed'] += 1
                
#                 if result['success']:
#                     results['successful'].append(result)
#                 else:
#                     results['failed'].append(result)
            
#             # Add module coordinator
#             coordinator = supervisors_config.get('module_coordinator')
#             if coordinator:
#                 result = self._add_supervisor_collaborator(coordinator)
#                 results['total_processed'] += 1
                
#                 if result['success']:
#                     results['successful'].append(result)
#                 else:
#                     results['failed'].append(result)
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to send supervisor invitations: {e}")
#             raise

#     def _add_supervisor_collaborator(self, supervisor_data: Dict) -> Dict:
#         """Add supervisor as collaborator"""
#         try:
#             username = supervisor_data['github_username']
#             permission = supervisor_data.get('permissions', 'admin').lower()
            
#             # Map permission levels correctly
#             if permission in ['owner', 'admin']:
#                 github_permission = 'admin'
#             elif permission in ['member', 'write']:
#                 github_permission = 'push'
#             else:
#                 github_permission = 'push'
            
#             success = self.github.add_collaborator(
#                 org=self.org,
#                 repo=self.config['repository']['name'],
#                 username=username,
#                 permission=github_permission  # Use the mapped permission
#             )
            
#             if success:
#                 logger.debug(f"Added supervisor {username} with {github_permission} permission")
#                 return {
#                     'type': 'supervisor',
#                     'target': username,
#                     'name': supervisor_data.get('name', username),
#                     'success': True,
#                     'permission': github_permission
#                 }
#             else:
#                 return {
#                     'type': 'supervisor',
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add supervisor - check username and repository permissions'
#                 }
                
#         except Exception as e:
#             logger.error(f"Failed to add supervisor {supervisor_data.get('github_username', 'unknown')}: {e}")
#             return {
#                 'type': 'supervisor',
#                 'target': supervisor_data.get('github_username', 'unknown'),
#                 'success': False,
#                 'error': str(e)
#             }    
    
#     def check_invitation_status(self, project_csv_path: str) -> Dict:
#         """Check status of sent invitations"""
#         try:
#             projects = load_project_data(project_csv_path)
#             status_results = {
#                 'accepted': [],
#                 'pending': [],
#                 'not_invited': [],
#                 'total_checked': 0
#             }
            
#             repo_name = self.config['repository']['name']  # Use main repository name
            
#             for project in projects:
#                 username = project.get('github_username')
                
#                 # Clean username if it's a URL
#                 if username and ('github.com' in username or username.startswith('http')):
#                     username = extract_github_username(username)
                
#                 if not username:
#                     username = self._find_username_by_email(project.get('email', ''))
                
#                 if not username:
#                     status_results['not_invited'].append({
#                         'project': project,
#                         'status': 'no_username'
#                     })
#                     status_results['total_checked'] += 1
#                     continue
                
#                 try:
#                     # Check if user is collaborator on main repository
#                     is_collaborator = self.github.check_collaborator(self.org, repo_name, username)
                    
#                     if is_collaborator:
#                         status_results['accepted'].append({
#                             'project': project,
#                             'username': username,
#                             'repo': repo_name,
#                             'status': 'collaborator'
#                         })
#                     else:
#                         # Check if invitation is pending
#                         has_pending = self.github.check_pending_invitation(self.org, repo_name, username)
                        
#                         if has_pending:
#                             status_results['pending'].append({
#                                 'project': project,
#                                 'username': username,
#                                 'repo': repo_name,
#                                 'status': 'pending'
#                             })
#                         else:
#                             status_results['not_invited'].append({
#                                 'project': project,
#                                 'username': username,
#                                 'repo': repo_name,
#                                 'status': 'not_invited'
#                             })
                    
#                 except Exception as e:
#                     logger.error(f"Error checking status for {username}: {e}")
#                     status_results['not_invited'].append({
#                         'project': project,
#                         'username': username,
#                         'status': 'error',
#                         'error': str(e)
#                     })
                
#                 status_results['total_checked'] += 1
            
#             return status_results
            
#         except Exception as e:
#             logger.error(f"Failed to check invitation status: {e}")
#             raise

#     def setup_branch_protection_for_folders(self, project_csv_path: str) -> Dict:
#         """Setup branch protection rules to manage folder access (GitHub Enterprise feature)"""
#         try:
#             projects = load_project_data(project_csv_path)
#             results = {
#                 'successful': [],
#                 'failed': [],
#                 'total_processed': 0
#             }
            
#             logger.info("Setting up branch protection for student folders...")
#             logger.warning("Note: Advanced branch protection features require GitHub Enterprise")
            
#             for project in projects:
#                 try:
#                     # This is a conceptual implementation - actual folder restrictions
#                     # require GitHub Enterprise and specific CODEOWNERS setup
#                     folder_path = f"projects/{project['index_number']}/"
                    
#                     # Create CODEOWNERS entry (this is the closest GitHub gets to folder permissions)
#                     codeowners_entry = f"{folder_path}* @{project.get('github_username', '')}"
                    
#                     results['successful'].append({
#                         'project': project,
#                         'folder_path': folder_path,
#                         'codeowners_entry': codeowners_entry,
#                         'status': 'configured'
#                     })
                    
#                 except Exception as e:
#                     results['failed'].append({
#                         'project': project,
#                         'error': str(e)
#                     })
                
#                 results['total_processed'] += 1
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to setup branch protection: {e}")
#             raise

#     def create_codeowners_file(self, project_csv_path: str) -> Dict:
#         """Create CODEOWNERS file to manage folder permissions"""
#         try:
#             projects = load_project_data(project_csv_path)
            
#             codeowners_content = "# CODEOWNERS file for folder-level access control\n"
#             codeowners_content += "# Each student can only modify their own folder\n\n"
            
#             for project in projects:
#                 username = project.get('github_username')
#                 if username and ('github.com' in username or username.startswith('http')):
#                     username = extract_github_username(username)
                
#                 if username:
#                     folder_path = f"projects/{project['index_number']}/"
#                     codeowners_content += f"{folder_path}* @{username}\n"
            
#             # Add supervisors as owners of all folders
#             supervisors = load_supervisor_data(self.config)
#             if supervisors:
#                 supervisor_handles = []
#                 for supervisor in supervisors:
#                     supervisor_handles.append(f"@{supervisor['github_username']}")
                
#                 codeowners_content += f"\n# Supervisors have access to all folders\n"
#                 codeowners_content += f"projects/* {' '.join(supervisor_handles)}\n"
            
#             return {
#                 'status': 'success',
#                 'codeowners_content': codeowners_content,
#                 'total_students': len(projects),
#                 'message': 'CODEOWNERS file generated - upload this to .github/CODEOWNERS in your repository'
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to create CODEOWNERS file: {e}")
#             return {
#                 'status': 'error',
#                 'error': str(e)
#             }

#     def validate_student_access(self, project_csv_path: str) -> Dict:
#         """Validate that all students have proper access to the repository"""
#         try:
#             projects = load_project_data(project_csv_path)
#             validation_results = {
#                 'valid_access': [],
#                 'invalid_access': [],
#                 'missing_username': [],
#                 'total_validated': 0
#             }
            
#             repo_name = self.config['repository']['name']
            
#             for project in projects:
#                 username = project.get('github_username')
#                 if username and ('github.com' in username or username.startswith('http')):
#                     username = extract_github_username(username)
                
#                 if not username:
#                     validation_results['missing_username'].append({
#                         'project': project,
#                         'issue': 'No GitHub username provided'
#                     })
#                     validation_results['total_validated'] += 1
#                     continue
                
#                 try:
#                     # Check if user exists on GitHub
#                     user_exists = self.github.check_user_exists(username)
#                     if not user_exists:
#                         validation_results['invalid_access'].append({
#                             'project': project,
#                             'username': username,
#                             'issue': 'GitHub user does not exist'
#                         })
#                         validation_results['total_validated'] += 1
#                         continue
                    
#                     # Check if user is collaborator
#                     is_collaborator = self.github.check_collaborator(self.org, repo_name, username)
                    
#                     if is_collaborator:
#                         validation_results['valid_access'].append({
#                             'project': project,
#                             'username': username,
#                             'status': 'collaborator'
#                         })
#                     else:
#                         # Check if invitation is pending
#                         has_pending = self.github.check_pending_invitation(self.org, repo_name, username)
                        
#                         if has_pending:
#                             validation_results['valid_access'].append({
#                                 'project': project,
#                                 'username': username,
#                                 'status': 'pending_invitation'
#                             })
#                         else:
#                             validation_results['invalid_access'].append({
#                                 'project': project,
#                                 'username': username,
#                                 'issue': 'Not invited and not a collaborator'
#                             })
                    
#                 except Exception as e:
#                     validation_results['invalid_access'].append({
#                         'project': project,
#                         'username': username,
#                         'issue': f'Validation error: {str(e)}'
#                     })
                
#                 validation_results['total_validated'] += 1
                
#                 # Rate limiting
#                 time.sleep(0.5)
            
#             return validation_results
            
#         except Exception as e:
#             logger.error(f"Failed to validate student access: {e}")
#             raise