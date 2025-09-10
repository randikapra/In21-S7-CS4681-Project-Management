# ## version 1.0
# # """
# # project invitation automation and access management
# # """

# # import logging
# # import time
# # from typing import Dict, List, Optional, Tuple
# # from .github_client import GitHubClient
# # from .utils import load_project_data, load_supervisor_data

# # logger = logging.getLogger(__name__)

# # class InvitationManager:
# #     def __init__(self, config: Dict):
# #         self.config = config
# #         self.github = GitHubClient(config['github']['token'])
# #         self.org = config['github']['organization']
        
# #     def send_bulk_invitations(self, project_csv_path: str) -> Dict:
# #         """Send invitations to all projects in CSV file"""
# #         try:
# #             projects = load_project_data(project_csv_path)
# #             supervisors = load_supervisor_data(self.config)
            
# #             results = {
# #                 'successful': [],
# #                 'failed': [],
# #                 'total_processed': 0,
# #                 'summary': {}
# #             }
            
# #             logger.info(f"Starting bulk invitation process for {len(projects)} projects")
            
# #             for i, project in enumerate(projects, 1):
# #                 logger.info(f"Processing project {i}/{len(projects)}: {project['index_number']}")
                
# #                 # Generate repository name
# #                 repo_name = self._generate_repo_name(project)
                
# #                 # Send invitation for individual repository
# #                 invitation_result = self.send_project_invitation(project, repo_name, supervisors)
                
# #                 if invitation_result['status'] == 'success':
# #                     results['successful'].append(invitation_result)
# #                 else:
# #                     results['failed'].append(invitation_result)
                
# #                 results['total_processed'] += 1
                
# #                 # Rate limiting - pause between requests
# #                 if i % 10 == 0:
# #                     logger.info(f"Processed {i} projects, pausing for rate limit...")
# #                     time.sleep(2)
            
# #             # Generate summary
# #             results['summary'] = {
# #                 'success_count': len(results['successful']),
# #                 'failure_count': len(results['failed']),
# #                 'success_rate': (len(results['successful']) / results['total_processed']) * 100
# #             }
            
# #             logger.info(f"Bulk invitation completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
# #             return results
            
# #         except Exception as e:
# #             logger.error(f"Failed to send bulk invitations: {e}")
# #             raise
    
# #     def send_project_invitation(self, project_data: Dict, repo_name: str, supervisors: List[Dict]) -> Dict:
# #         """Send invitation to individual project for their repository"""
# #         try:
# #             invitation_results = []
            
# #             # Add project as collaborator with write permission
# #             project_result = self._add_project_collaborator(project_data, repo_name)
# #             invitation_results.append(project_result)
            
# #             # Add supervisors with admin permission
# #             for supervisor in supervisors:
# #                 supervisor_result = self._add_supervisor_collaborator(supervisor, repo_name)
# #                 invitation_results.append(supervisor_result)
            
# #             # Check overall success
# #             failed_invitations = [r for r in invitation_results if not r['success']]
            
# #             if not failed_invitations:
# #                 status = 'success'
# #                 message = 'All invitations sent successfully'
# #             else:
# #                 status = 'partial_success'
# #                 message = f'{len(failed_invitations)} invitations failed'
            
# #             return {
# #                 'status': status,
# #                 'project': project_data,
# #                 'repo_name': repo_name,
# #                 'message': message,
# #                 'invitation_details': invitation_results
# #             }
            
# #         except Exception as e:
# #             logger.error(f"Failed to send invitation for {project_data['index_number']}: {e}")
# #             return {
# #                 'status': 'error',
# #                 'project': project_data,
# #                 'repo_name': repo_name,
# #                 'error': str(e)
# #             }
    
# #     def _add_project_collaborator(self, project_data: Dict, repo_name: str) -> Dict:
# #         """Add project as collaborator with write permission"""
# #         try:
# #             # Try GitHub username first, fallback to email-based lookup
# #             username = project_data.get('github_username')
            
# #             if not username:
# #                 # Try to find user by email or create username suggestion
# #                 username = self._find_username_by_email(project_data.get('email', ''))
            
# #             if not username:
# #                 return {
# #                     'type': 'project',
# #                     'target': project_data['index_number'],
# #                     'success': False,
# #                     'error': 'GitHub username not found'
# #                 }
            
# #             success = self.github.add_collaborator(
# #                 self.org,
# #                 self.config['repository']['name'], 
# #                 username,
# #                 permission='push'
# #             )
            
# #             if success:
# #                 logger.info(f"Added project {username} to {repo_name}")
# #                 return {
# #                     'type': 'project',
# #                     'target': username,
# #                     'success': True,
# #                     'permission': 'push'
# #                 }
# #             else:
# #                 return {
# #                     'type': 'project', 
# #                     'target': username,
# #                     'success': False,
# #                     'error': 'Failed to add collaborator'
# #                 }
                
# #         except Exception as e:
# #             logger.error(f"Failed to add project {project_data['index_number']} to {repo_name}: {e}")
# #             return {
# #                 'type': 'project',
# #                 'target': project_data['index_number'],
# #                 'success': False,
# #                 'error': str(e)
# #             }
    
# #     def _add_supervisor_collaborator(self, supervisor_data: Dict, repo_name: str) -> Dict:
# #         """Add supervisor as collaborator with admin permission"""
# #         try:
# #             username = supervisor_data['github_username']
# #             permission = supervisor_data.get('permissions', 'admin')

# #             # Map permission levels
# #             if permission in ['owner', 'admin']:
# #                 github_permission = 'admin'
# #             elif permission in ['member', 'write']:
# #                 github_permission = 'push'
# #             else:
# #                 github_permission = 'push'

# #             success = self.github.add_collaborator(
# #                 org=self.org,
# #                 repo=self.config['repository']['name'],
# #                 username=username,
# #                 permission=github_permission
# #             )
            
# #             if success:
# #                 logger.debug(f"Added supervisor {username} to {repo_name}")
# #                 return {
# #                     'type': 'supervisor',
# #                     'target': username,
# #                     'success': True,
# #                     'permission': permission
# #                 }
# #             else:
# #                 return {
# #                     'type': 'supervisor',
# #                     'target': username,
# #                     'success': False,
# #                     'error': 'Failed to add supervisor'
# #                 }
                
# #         except Exception as e:
# #             logger.error(f"Failed to add supervisor {supervisor_data['github_username']} to {repo_name}: {e}")
# #             return {
# #                 'type': 'supervisor',
# #                 'target': supervisor_data['github_username'],
# #                 'success': False,
# #                 'error': str(e)
# #             }
    
# #     def _find_username_by_email(self, email: str) -> Optional[str]:
# #         """Try to find GitHub username by email"""
# #         if not email:
# #             return None
            
# #         try:
# #             # Search for user by email (this is limited by GitHub API)
# #             user_data = self.github.search_user_by_email(email)
# #             if user_data:
# #                 return user_data.get('login')
# #             return None
# #         except Exception as e:
# #             logger.warning(f"Could not find GitHub user for email {email}: {e}")
# #             return None
    
# #     def _generate_repo_name(self, project: Dict) -> str:
# #         """Generate repository name from project data"""
# #         index_number = project['index_number']
# #         research_area = project['research_area'].replace(' ', '_').replace('-', '_')
# #         return f"{index_number}_{research_area}"
    
# #     def retry_failed_invitations(self, failed_results: List[Dict]) -> Dict:
# #         """Retry failed invitations"""
# #         retry_results = {
# #             'successful': [],
# #             'failed': [],
# #             'total_retried': len(failed_results)
# #         }
        
# #         logger.info(f"Retrying {len(failed_results)} failed invitations")
        
# #         for result in failed_results:
# #             if result['status'] == 'error':
# #                 project = result['project']
# #                 repo_name = result['repo_name']
# #                 supervisors = load_supervisor_data(self.config)
                
# #                 retry_result = self.send_project_invitation(project, repo_name, supervisors)
                
# #                 if retry_result['status'] == 'success':
# #                     retry_results['successful'].append(retry_result)
# #                 else:
# #                     retry_results['failed'].append(retry_result)
                
# #                 time.sleep(1)  # Rate limiting
        
# #         return retry_results
    
# #     def send_organization_invitations(self, project_csv_path: str) -> Dict:
# #         """Send organization-level invitations to all projects"""
# #         try:
# #             projects = load_project_data(project_csv_path)
# #             results = {
# #                 'successful': [],
# #                 'failed': [],
# #                 'total_processed': 0
# #             }
            
# #             logger.info(f"Sending organization invitations to {len(projects)} projects")
            
# #             for i, project in enumerate(projects, 1):
# #                 logger.info(f"Inviting project {i}/{len(projects)}: {project['index_number']}")
                
# #                 username = project.get('github_username')
# #                 if not username:
# #                     username = self._find_username_by_email(project.get('email', ''))
                
# #                 if not username:
# #                     results['failed'].append({
# #                         'project': project,
# #                         'error': 'GitHub username not found'
# #                     })
# #                     results['total_processed'] += 1
# #                     continue
                
# #                 try:
# #                     success = self.github.invite_to_organization(self.org, username, 'member')
                    
# #                     if success:
# #                         results['successful'].append({
# #                             'project': project,
# #                             'username': username,
# #                             'status': 'invited'
# #                         })
# #                     else:
# #                         results['failed'].append({
# #                             'project': project,
# #                             'username': username,
# #                             'error': 'Failed to send organization invitation'
# #                         })
                    
# #                 except Exception as e:
# #                     results['failed'].append({
# #                         'project': project,
# #                         'username': username,
# #                         'error': str(e)
# #                     })
                
# #                 results['total_processed'] += 1
                
# #                 # Rate limiting
# #                 if i % 10 == 0:
# #                     time.sleep(2)
            
# #             return results
            
# #         except Exception as e:
# #             logger.error(f"Failed to send organization invitations: {e}")
# #             raise
# #     def send_repository_invitation(self, student_data: Dict) -> Dict:
# #         """Send invitation to student for the main repository"""
# #         try:
# #             invitation_results = []
            
# #             # Add student as collaborator with write permission
# #             student_result = self._add_student_collaborator(student_data)
# #             invitation_results.append(student_result)
            
# #             # Check overall success
# #             failed_invitations = [r for r in invitation_results if not r['success']]
            
# #             if not failed_invitations:
# #                 status = 'success'
# #                 message = 'Student invitation sent successfully'
# #             else:
# #                 status = 'failed'
# #                 message = 'Student invitation failed'
            
# #             return {
# #                 'status': status,
# #                 'student': student_data,
# #                 'repo_name': self.config['repository']['name'],
# #                 'message': message,
# #                 'invitation_details': invitation_results
# #             }
            
# #         except Exception as e:
# #             logger.error(f"Failed to send invitation for {student_data['index_number']}: {e}")
# #             return {
# #                 'status': 'error',
# #                 'student': student_data,
# #                 'repo_name': self.config['repository']['name'],
# #                 'error': str(e)
# #             }

# #     def _add_student_collaborator(self, student_data: Dict) -> Dict:
# #         """Add student as collaborator with write permission"""
# #         try:
# #             username = student_data.get('github_username')
            
# #             if not username:
# #                 username = self._find_username_by_email(student_data.get('email', ''))
            
# #             if not username:
# #                 return {
# #                     'type': 'student',
# #                     'target': student_data['index_number'],
# #                     'success': False,
# #                     'error': 'GitHub username not found'
# #                 }
            
# #             success = self.github.add_collaborator(
# #                 org=self.org,
# #                 repo=self.config['repository']['name'],
# #                 username=username,
# #                 permission='push'  # Write access to their folder
# #             )
            
# #             if success:
# #                 logger.info(f"Added student {username} to repository")
# #                 return {
# #                     'type': 'student',
# #                     'target': username,
# #                     'success': True,
# #                     'permission': 'push'
# #                 }
# #             else:
# #                 return {
# #                     'type': 'student', 
# #                     'target': username,
# #                     'success': False,
# #                     'error': 'Failed to add collaborator'
# #                 }
                
# #         except Exception as e:
# #             logger.error(f"Failed to add student {student_data['index_number']}: {e}")
# #             return {
# #                 'type': 'student',
# #                 'target': student_data['index_number'],
# #                 'success': False,
# #                 'error': str(e)
# #             }

# #     def send_supervisors_invitations(self) -> Dict:
# #         """Send invitations to all supervisors"""
# #         try:
# #             supervisors_config = self.config.get('supervisors', {})
# #             supervisors_list = supervisors_config.get('supervisors', [])
            
# #             results = {
# #                 'successful': [],
# #                 'failed': [],
# #                 'total_processed': 0
# #             }
            
# #             # Add main supervisors
# #             for supervisor in supervisors_list:
# #                 result = self._add_supervisor_collaborator(supervisor)
# #                 results['total_processed'] += 1
                
# #                 if result['success']:
# #                     results['successful'].append(result)
# #                 else:
# #                     results['failed'].append(result)
            
# #             # Add module coordinator
# #             coordinator = supervisors_config.get('module_coordinator')
# #             if coordinator:
# #                 result = self._add_supervisor_collaborator(coordinator)
# #                 results['total_processed'] += 1
                
# #                 if result['success']:
# #                     results['successful'].append(result)
# #                 else:
# #                     results['failed'].append(result)
            
# #             return results
            
# #         except Exception as e:
# #             logger.error(f"Failed to send supervisor invitations: {e}")
# #             raise

# #     def _add_supervisor_collaborator(self, supervisor_data: Dict) -> Dict:
# #         """Add supervisor as collaborator"""
# #         try:
# #             username = supervisor_data['github_username']
# #             permission = supervisor_data.get('permissions', 'admin').lower()
            
# #             # Map permission levels
# #             if permission in ['owner', 'admin']:
# #                 github_permission = 'admin'
# #             elif permission in ['member', 'write']:
# #                 github_permission = 'push'
# #             else:
# #                 github_permission = 'push'
            
# #             success = self.github.add_collaborator(
# #                 org=self.org,
# #                 repo=self.config['repository']['name'],
# #                 username=username,
# #                 permission=github_permission
# #             )
            
# #             if success:
# #                 logger.debug(f"Added supervisor {username} with {github_permission} permission")
# #                 return {
# #                     'type': 'supervisor',
# #                     'target': username,
# #                     'name': supervisor_data.get('name', username),
# #                     'success': True,
# #                     'permission': github_permission
# #                 }
# #             else:
# #                 return {
# #                     'type': 'supervisor',
# #                     'target': username,
# #                     'success': False,
# #                     'error': 'Failed to add supervisor'
# #                 }
                
# #         except Exception as e:
# #             logger.error(f"Failed to add supervisor {supervisor_data.get('github_username', 'unknown')}: {e}")
# #             return {
# #                 'type': 'supervisor',
# #                 'target': supervisor_data.get('github_username', 'unknown'),
# #                 'success': False,
# #                 'error': str(e)
# #             }    
# #     def check_invitation_status(self, project_csv_path: str) -> Dict:
# #         """Check status of sent invitations"""
# #         try:
# #             projects = load_project_data(project_csv_path)
# #             status_results = {
# #                 'accepted': [],
# #                 'pending': [],
# #                 'not_invited': [],
# #                 'total_checked': 0
# #             }
            
# #             for project in projects:
# #                 repo_name = self._generate_repo_name(project)
# #                 username = project.get('github_username')
                
# #                 if not username:
# #                     username = self._find_username_by_email(project.get('email', ''))
                
# #                 if not username:
# #                     status_results['not_invited'].append({
# #                         'project': project,
# #                         'status': 'no_username'
# #                     })
# #                     status_results['total_checked'] += 1
# #                     continue
                
# #                 try:
# #                     # Check if user is collaborator
# #                     is_collaborator = self.github.check_collaborator(self.org, repo_name, username)
                    
# #                     if is_collaborator:
# #                         status_results['accepted'].append({
# #                             'project': project,
# #                             'username': username,
# #                             'repo': repo_name,
# #                             'status': 'collaborator'
# #                         })
# #                     else:
# #                         # Check if invitation is pending
# #                         has_pending = self.github.check_pending_invitation(self.org, repo_name, username)
                        
# #                         if has_pending:
# #                             status_results['pending'].append({
# #                                 'project': project,
# #                                 'username': username,
# #                                 'repo': repo_name,
# #                                 'status': 'pending'
# #                             })
# #                         else:
# #                             status_results['not_invited'].append({
# #                                 'project': project,
# #                                 'username': username,
# #                                 'repo': repo_name,
# #                                 'status': 'not_invited'
# #                             })
                    
# #                 except Exception as e:
# #                     logger.error(f"Error checking status for {username}: {e}")
# #                     status_results['not_invited'].append({
# #                         'project': project,
# #                         'username': username,
# #                         'status': 'error',
# #                         'error': str(e)
# #                     })
                
# #                 status_results['total_checked'] += 1
            
# #             return status_results
            
# #         except Exception as e:
# #             logger.error(f"Failed to check invitation status: {e}")
# #             raise

# ## version 2.0 

# """
# project invitation automation and access management
# """

# import logging
# import time
# from typing import Dict, List, Optional, Tuple
# from .github_client import GitHubClient
# from .utils import load_project_data, load_supervisor_data

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
                
#                 # Generate repository name
#                 repo_name = self._generate_repo_name(project)
                
#                 # Send invitation for individual repository
#                 invitation_result = self.send_project_invitation(project, repo_name, supervisors)
                
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
#                 'success_rate': (len(results['successful']) / results['total_processed']) * 100
#             }
            
#             logger.info(f"Bulk invitation completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to send bulk invitations: {e}")
#             raise
    
#     def send_project_invitation(self, project_data: Dict, repo_name: str, supervisors: List[Dict]) -> Dict:
#         """Send invitation to individual project for their repository"""
#         try:
#             invitation_results = []
            
#             # Add project as collaborator with write permission
#             project_result = self._add_project_collaborator(project_data, repo_name)
#             invitation_results.append(project_result)
            
#             # Add supervisors with admin permission
#             for supervisor in supervisors:
#                 supervisor_result = self._add_supervisor_collaborator(supervisor, repo_name)
#                 invitation_results.append(supervisor_result)
            
#             # Check overall success
#             failed_invitations = [r for r in invitation_results if not r['success']]
            
#             if not failed_invitations:
#                 status = 'success'
#                 message = 'All invitations sent successfully'
#             else:
#                 status = 'partial_success'
#                 message = f'{len(failed_invitations)} invitations failed'
            
#             return {
#                 'status': status,
#                 'project': project_data,
#                 'repo_name': repo_name,
#                 'message': message,
#                 'invitation_details': invitation_results
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to send invitation for {project_data['index_number']}: {e}")
#             return {
#                 'status': 'error',
#                 'project': project_data,
#                 'repo_name': repo_name,
#                 'error': str(e)
#             }
    
#     def _add_project_collaborator(self, project_data: Dict, repo_name: str) -> Dict:
#         """Add project as collaborator with write permission"""
#         try:
#             # Try GitHub username first, fallback to email-based lookup
#             username = project_data.get('github_username')
            
#             if not username:
#                 # Try to find user by email or create username suggestion
#                 username = self._find_username_by_email(project_data.get('email', ''))
            
#             if not username:
#                 return {
#                     'type': 'project',
#                     'target': project_data['index_number'],
#                     'success': False,
#                     'error': 'GitHub username not found'
#                 }
            
#             success = self.github.add_collaborator(
#                 self.org,
#                 self.config['repository']['name'], 
#                 username,
#                 permission='push'
#             )
            
#             if success:
#                 logger.info(f"Added project {username} to {repo_name}")
#                 return {
#                     'type': 'project',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push'
#                 }
#             else:
#                 return {
#                     'type': 'project', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator'
#                 }
                
#         except Exception as e:
#             logger.error(f"Failed to add project {project_data['index_number']} to {repo_name}: {e}")
#             return {
#                 'type': 'project',
#                 'target': project_data['index_number'],
#                 'success': False,
#                 'error': str(e)
#             }
    
#     # def _add_supervisor_collaborator(self, supervisor_data: Dict, repo_name: str) -> Dict:
#     #     """Add supervisor as collaborator with admin permission"""
#     #     try:
#     #         username = supervisor_data['github_username']
#     #         permission = supervisor_data.get('permissions', 'admin')
            
#     #         success = self.github.add_collaborator(
#     #             self.org,
#     #             self.config['repository']['name'],
#     #             username,
#     #             :permission=permission
#     #         )
            
#     #         if success:
#     #             logger.debug(f"Added supervisor {username} to {repo_name}")
#     #             return {
#     #                 'type': 'supervisor',
#     #                 'target': username,
#     #                 'success': True,
#     #                 'permission': permission
#     #             }
#     #         else:
#     #             return {
#     #                 'type': 'supervisor',
#     #                 'target': username,
#     #                 'success': False,
#     #                 'error': 'Failed to add supervisor'
#     #             }
                
#     #     except Exception as e:
#     #         logger.error(f"Failed to add supervisor {supervisor_data['github_username']} to {repo_name}: {e}")
#     #         return {
#     #             'type': 'supervisor',
#     #             'target': supervisor_data['github_username'],
#     #             'success': False,
#     #             'error': str(e)
#     #         }
    
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
#                 repo_name = result['repo_name']
#                 supervisors = load_supervisor_data(self.config)
                
#                 retry_result = self.send_project_invitation(project, repo_name, supervisors)
                
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
#             invitation_results = []
            
#             # Add student as collaborator with write permission
#             student_result = self._add_student_collaborator(student_data)
#             invitation_results.append(student_result)
            
#             # Check overall success
#             failed_invitations = [r for r in invitation_results if not r['success']]
            
#             if not failed_invitations:
#                 status = 'success'
#                 message = 'Student invitation sent successfully'
#             else:
#                 status = 'failed'
#                 message = 'Student invitation failed'
            
#             return {
#                 'status': status,
#                 'student': student_data,
#                 'repo_name': self.config['repository']['name'],
#                 'message': message,
#                 'invitation_details': invitation_results
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to send invitation for {student_data['index_number']}: {e}")
#             return {
#                 'status': 'error',
#                 'student': student_data,
#                 'repo_name': self.config['repository']['name'],
#                 'error': str(e)
#             }

#     def _add_student_collaborator(self, student_data: Dict) -> Dict:
#         """Add student as collaborator with write permission"""
#         try:
#             username = student_data.get('github_username')
            
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
#                 permission='push'  # Write access to their folder
#             )
            
#             if success:
#                 logger.info(f"Added student {username} to repository")
#                 return {
#                     'type': 'student',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push'
#                 }
#             else:
#                 return {
#                     'type': 'student', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator'
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
            
#             # Map permission levels
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
#                 # :permission=permission
#                 permission=permission
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
#                     'error': 'Failed to add supervisor'
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
            
#             for project in projects:
#                 repo_name = self._generate_repo_name(project)
#                 username = project.get('github_username')
                
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
#                     # Check if user is collaborator
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


# ## Version 2.0 

# """
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
                
#                 # Generate repository name
#                 repo_name = self._generate_repo_name(project)
                
#                 # Send invitation for individual repository
#                 invitation_result = self.send_project_invitation(project, repo_name, supervisors)
                
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
#                 'success_rate': (len(results['successful']) / results['total_processed']) * 100
#             }
            
#             logger.info(f"Bulk invitation completed. Success: {results['summary']['success_count']}, Failed: {results['summary']['failure_count']}")
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to send bulk invitations: {e}")
#             raise
    
#     def send_project_invitation(self, project_data: Dict, repo_name: str, supervisors: List[Dict]) -> Dict:
#         """Send invitation to individual project for the shared repository"""
#         try:
#             invitation_results = []
            
#             # Add project as collaborator with write permission to the main repository
#             project_result = self._add_project_collaborator(project_data, self.config['repository']['name'])
#             invitation_results.append(project_result)
            
#             # Add supervisors with admin permission to the main repository
#             for supervisor in supervisors:
#                 supervisor_result = self._add_supervisor_collaborator(supervisor, self.config['repository']['name'])
#                 invitation_results.append(supervisor_result)
            
#             # Check overall success
#             failed_invitations = [r for r in invitation_results if not r['success']]
            
#             if not failed_invitations:
#                 status = 'success'
#                 message = 'All invitations sent successfully'
#             else:
#                 status = 'partial_success'
#                 message = f'{len(failed_invitations)} invitations failed'
            
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

#     def _add_project_collaborator(self, project_data: Dict, repo_name: str) -> Dict:
#         """Add project as collaborator with write permission"""
#         try:
#             # Try GitHub username first, fallback to email-based lookup
#             username = project_data.get('github_username')
#             if username and ('github.com' in username or username.startswith('http')):
#                 username = extract_github_username(username)
#             if not username:
#                 # Try to find user by email or create username suggestion
#                 username = self._find_username_by_email(project_data.get('email', ''))
            
#             if not username:
#                 return {
#                     'type': 'project',
#                     'target': project_data['index_number'],
#                     'success': False,
#                     'error': 'GitHub username not found'
#                 }
            
#             success = self.github.add_collaborator(
#                 self.org,
#                 self.config['repository']['name'], 
#                 username,
#                 permission='push'
#             )
            
#             if success:
#                 logger.info(f"Added project {username} to {repo_name}")
#                 return {
#                     'type': 'project',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push'
#                 }
#             else:
#                 return {
#                     'type': 'project', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator'
#                 }
                
#         except Exception as e:
#             logger.error(f"Failed to add project {project_data['index_number']} to {repo_name}: {e}")
#             return {
#                 'type': 'project',
#                 'target': project_data['index_number'],
#                 'success': False,
#                 'error': str(e)
#             }
    
#     # def _add_supervisor_collaborator(self, supervisor_data: Dict, repo_name: str) -> Dict:
#     #     """Add supervisor as collaborator with admin permission"""
#     #     try:
#     #         username = supervisor_data['github_username']
#     #         permission = supervisor_data.get('permissions', 'admin')
            
#     #         success = self.github.add_collaborator(
#     #             self.org,
#     #             self.config['repository']['name'],
#     #             username,
#     #             :permission=permission
#     #         )
            
#     #         if success:
#     #             logger.debug(f"Added supervisor {username} to {repo_name}")
#     #             return {
#     #                 'type': 'supervisor',
#     #                 'target': username,
#     #                 'success': True,
#     #                 'permission': permission
#     #             }
#     #         else:
#     #             return {
#     #                 'type': 'supervisor',
#     #                 'target': username,
#     #                 'success': False,
#     #                 'error': 'Failed to add supervisor'
#     #             }
                
#     #     except Exception as e:
#     #         logger.error(f"Failed to add supervisor {supervisor_data['github_username']} to {repo_name}: {e}")
#     #         return {
#     #             'type': 'supervisor',
#     #             'target': supervisor_data['github_username'],
#     #             'success': False,
#     #             'error': str(e)
#     #         }
    
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
#                 repo_name = result['repo_name']
#                 supervisors = load_supervisor_data(self.config)
                
#                 retry_result = self.send_project_invitation(project, repo_name, supervisors)
                
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
#     ## version 1.0
#     # def send_repository_invitation(self, student_data: Dict) -> Dict:
#     #     """Send invitation to student for the main repository"""
#     #     try:
#     #         invitation_results = []
            
#     #         # Add student as collaborator with write permission
#     #         student_result = self._add_student_collaborator(student_data)
#     #         invitation_results.append(student_result)
            
#     #         # Check overall success
#     #         failed_invitations = [r for r in invitation_results if not r['success']]
            
#     #         if not failed_invitations:
#     #             status = 'success'
#     #             message = 'Student invitation sent successfully'
#     #         else:
#     #             status = 'failed'
#     #             message = 'Student invitation failed'
            
#     #         return {
#     #             'status': status,
#     #             'student': student_data,
#     #             'repo_name': self.config['repository']['name'],
#     #             'message': message,
#     #             'invitation_details': invitation_results
#     #         }
            
#     #     except Exception as e:
#     #         logger.error(f"Failed to send invitation for {student_data['index_number']}: {e}")
#     #         return {
#     #             'status': 'error',
#     #             'student': student_data,
#     #             'repo_name': self.config['repository']['name'],
#     #             'error': str(e)
#     #         }

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
#                 permission='push'  # Write access to their folder
#             )
            
#             if success:
#                 logger.info(f"Added student {username} to repository")
#                 return {
#                     'type': 'student',
#                     'target': username,
#                     'success': True,
#                     'permission': 'push'
#                 }
#             else:
#                 return {
#                     'type': 'student', 
#                     'target': username,
#                     'success': False,
#                     'error': 'Failed to add collaborator'
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
            
#             # Map permission levels
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
#                 # :permission=permission
#                 permission=permission
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
#                     'error': 'Failed to add supervisor'
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
            
#             for project in projects:
#                 repo_name = self._generate_repo_name(project)
#                 username = project.get('github_username')
                
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
#                     # Check if user is collaborator
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