
"""
GitHub API client with rate limiting and batch operations
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Research-Project-Manager'
        })
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now() + timedelta(hours=1)
        self.check_rate_limit()
    
    # def check_rate_limit(self):
    #     """Check current rate limit status"""
    #     try:
    #         response = self.session.get(f"{self.base_url}/rate_limit")
    #         if response.status_code == 200:
    #             data = response.json()
    #             if data and 'resources' in data and 'core' in data['resources']:
    #                 core_limit = data['resources']['core']
    #                 self.rate_limit_remaining = core_limit['remaining']
    #                 self.rate_limit_reset = datetime.fromtimestamp(core_limit['reset'])
    #                 logger.info(f"Rate limit: {self.rate_limit_remaining} requests remaining")
    #             else:
    #                 logger.warning("Rate limit response missing expected data structure")
    #         else:
    #             logger.warning(f"Rate limit check returned status {response.status_code}")
    #     except Exception as e:
    #         logger.warning(f"Could not check rate limit: {e}")
    def check_rate_limit(self):
        """Check current rate limit status"""
        try:
            response = self.session.get(f"{self.base_url}/rate_limit")
            if response.status_code == 200:
                data = response.json()
                if data and 'resources' in data and 'core' in data['resources']:
                    core_limit = data['resources']['core']
                    self.rate_limit_remaining = core_limit['remaining']
                    self.rate_limit_reset = datetime.fromtimestamp(core_limit['reset'])
                    logger.info(f"Rate limit: {self.rate_limit_remaining} requests remaining")
                else:
                    logger.warning("Rate limit response missing expected data structure")
                    # Set conservative defaults if structure is unexpected
                    self.rate_limit_remaining = 1000
            else:
                logger.warning(f"Rate limit check returned status {response.status_code}")
                # Set conservative defaults on error
                self.rate_limit_remaining = 1000
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")
            # Set conservative defaults on exception
            self.rate_limit_remaining = 1000

    def wait_for_rate_limit(self):
        """Wait if rate limit is exceeded"""
        if self.rate_limit_remaining < 100:
            wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit low, waiting {wait_time:.0f} seconds")
                time.sleep(min(wait_time, 3600))  # Max 1 hour wait
                self.check_rate_limit()
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with rate limiting"""
        self.wait_for_rate_limit()
        
        full_url = f"{self.base_url}/{url.lstrip('/')}"
        
        try:
            response = self.session.request(method, full_url, **kwargs)
            
            # Update rate limit info
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def create_repository(self, org: str, repo_name: str, description: str = "", private: bool = True) -> bool:
        """Create a repository in organization"""
        try:
            data = {
                'name': repo_name,
                'description': description,
                'private': private,
                'auto_init': True,
                'has_issues': True,
                'has_projects': True,
                'has_wiki': False
            }
            
            response = self.make_request('POST', f'/orgs/{org}/repos', json=data)
            
            if response.status_code == 201:
                logger.info(f"Created repository: {org}/{repo_name}")
                return True
            else:
                logger.error(f"Failed to create repository {repo_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating repository {repo_name}: {e}")
            return False
    
    def get_repository(self, org: str, repo: str) -> Optional[Dict]:
        """Get repository information"""
        try:
            response = self.make_request('GET', f'/repos/{org}/{repo}')
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Repository not found: {org}/{repo}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting repository {org}/{repo}: {e}")
            return None
    
    ## version 1.0
    # def create_directory(self, org: str, repo: str, path: str, message: str = None) -> bool:
    #     """Create directory by adding a .gitkeep file"""
    #     try:
    #         if not message:
    #             message = f"Create directory {path}"
            
    #         # GitHub doesn't have directories without files, so create .gitkeep
    #         gitkeep_path = f"{path}/.gitkeep" if not path.endswith('/') else f"{path}.gitkeep"
    #         content = "# This file keeps the directory in git\n"
            
    #         return self.update_repository_file(org, repo, gitkeep_path, content, message)
            
    #     except Exception as e:
    #         logger.error(f"Error creating directory {path}: {e}")
    #         return False

    ## version 1.0
    # def create_milestone(self, org: str, repo: str, title: str, description: str = "", due_date: str = None) -> Optional[int]:
    #     """Create milestone in repository"""
    #     try:
    #         data = {
    #             'title': title,
    #             'description': description,
    #             'state': 'open'
    #         }
            
    #         if due_date:
    #             # Fix: GitHub expects ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
    #             if isinstance(due_date, str) and 'T' in due_date and not due_date.endswith('Z'):
    #                 due_date = due_date + 'Z'
    #             data['due_on'] = due_date
            
    #         response = self.make_request('POST', f'/repos/{org}/{repo}/milestones', json=data)
            
    #         if response.status_code == 201:
    #             milestone_data = response.json()
    #             logger.debug(f"Created milestone: {title}")
    #             return milestone_data['number']
    #         elif response.status_code == 422:
    #             # Check if milestone already exists
    #             logger.warning(f"Milestone '{title}' validation failed, checking if it exists")
    #             milestones = self.list_milestones(org, repo)
    #             for milestone in milestones:
    #                 if milestone['title'] == title:
    #                     logger.info(f"Milestone '{title}' already exists")
    #                     return milestone['number']
    #             logger.error(f"Milestone creation failed: {response.text}")
    #             return None
    #         else:
    #             logger.error(f"Failed to create milestone: {response.status_code} - {response.text}")
    #             return None
                
    #     except Exception as e:
    #         logger.error(f"Error creating milestone: {e}")
    #         return None

    def list_milestones(self, org: str, repo: str, state: str = 'open') -> List[Dict]:
        """List milestones in repository"""
        try:
            response = self.make_request('GET', f'/repos/{org}/{repo}/milestones', params={'state': state})
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list milestones: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing milestones: {e}")
            return []

    def create_directory(self, org: str, repo: str, path: str, message: str = None) -> bool:
        """Create directory by adding a .gitkeep file"""
        try:
            if not message:
                message = f"Create directory {path}"
            
            # GitHub doesn't have directories without files, so create .gitkeep
            gitkeep_path = f"{path}/.gitkeep" if not path.endswith('/') else f"{path}.gitkeep"
            content = "# This file keeps the directory in git\n"
            
            # Fix: Pass all required parameters including sha=None
            return self.update_repository_file(org, repo, gitkeep_path, content, message, sha=None)
            
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False
            
    def create_repository_file(self, org: str, repo: str, path: str, content: str, message: str) -> bool:
        """Create or update file in repository (alias for compatibility)"""
        return self.update_repository_file(org, repo, path, content, message)

    # 3. Fix milestone creation error handling
    def create_milestone(self, org: str, repo: str, title: str, description: str = "", due_date: str = None) -> Optional[int]:
        """Create milestone in repository"""
        try:
            data = {
                'title': title,
                'description': description,
                'state': 'open'
            }
            
            if due_date:
                data['due_on'] = due_date
            
            response = self.make_request('POST', f'/repos/{org}/{repo}/milestones', json=data)
            
            if response.status_code == 201:
                milestone_data = response.json()
                logger.debug(f"Created milestone: {title}")
                return milestone_data['number']
            elif response.status_code == 422:
                # Handle validation error (milestone might already exist)
                logger.warning(f"Milestone '{title}' may already exist or validation failed: {response.text}")
                return None
            else:
                logger.error(f"Failed to create milestone: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating milestone: {e}")
            return None

    def create_repo_project(self, org: str, repo: str, name: str, description: str = "") -> Optional[int]:
        """Create repository project (different from organization project)"""
        try:
            data = {
                'name': name,
                'body': description
            }
            
            response = self.make_request('POST', f'/repos/{org}/{repo}/projects', json=data)
            
            if response.status_code == 201:
                project_data = response.json()
                logger.info(f"Created repository project: {name}")
                return project_data['id']
            else:
                logger.error(f"Failed to create repository project: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating repository project: {e}")
            return None
    
    def list_project_columns(self, project_id: int) -> List[Dict]:
        """List all columns in a project"""
        try:
            response = self.make_request('GET', f'/projects/{project_id}/columns')
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list project columns: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing project columns: {e}")
            return []
    
    def list_project_cards(self, column_id: int) -> List[Dict]:
        """List all cards in a project column"""
        try:
            cards = []
            page = 1
            
            while True:
                response = self.make_request(
                    'GET', 
                    f'/projects/columns/{column_id}/cards',
                    params={'page': page, 'per_page': 100}
                )
                
                if response.status_code != 200:
                    break
                
                page_cards = response.json()
                if not page_cards:
                    break
                
                cards.extend(page_cards)
                page += 1
            
            return cards
            
        except Exception as e:
            logger.error(f"Error listing project cards: {e}")
            return []
    
    def list_issues(self, org: str, repo: str, state: str = 'all', labels: List[str] = None, assignee: str = None) -> List[Dict]:
        """List issues with filtering options"""
        try:
            issues = []
            page = 1
            
            params = {
                'state': state,
                'page': page,
                'per_page': 100
            }
            
            if labels:
                params['labels'] = ','.join(labels)
            
            if assignee:
                params['assignee'] = assignee
            
            while True:
                response = self.make_request(
                    'GET', 
                    f'/repos/{org}/{repo}/issues',
                    params=params
                )
                
                if response.status_code != 200:
                    break
                
                page_issues = response.json()
                if not page_issues:
                    break
                
                issues.extend(page_issues)
                page += 1
                params['page'] = page
            
            return issues
            
        except Exception as e:
            logger.error(f"Error listing issues: {e}")
            return []
    
    ## version 1.0
    # def add_collaborator(self, org: str, repo: str, username: str, permission: str = 'push') -> bool:
    #     """Add collaborator to repository"""
    #     try:
    #         data = {'permission': permission}
            
    #         response = self.make_request(
    #             'PUT', 
    #             f'/repos/{org}/{repo}/collaborators/{username}',
    #             json=data
    #         )
            
    #         if response.status_code in [201, 204]:
    #             logger.debug(f"Added {username} as collaborator to {org}/{repo}")
    #             return True
    #         else:
    #             logger.error(f"Failed to add collaborator {username}: {response.status_code}")
    #             return False
                
    #     except Exception as e:
    #         logger.error(f"Error adding collaborator {username}: {e}")
    #         return False
    
    def add_collaborator(self, org: str, repo: str, username: str, permission: str = 'push') -> bool:
        """Add collaborator to repository"""
        try:
            data = {'permission': permission}
            
            response = self.make_request(
                'PUT', 
                f'/repos/{org}/{repo}/collaborators/{username}',
                json=data
            )
            
            if response.status_code in [201, 204]:
                logger.debug(f"Added {username} as collaborator to {org}/{repo}")
                return True
            elif response.status_code == 404:
                # Check if it's user not found vs repository not found
                user_check = self.make_request('GET', f'/users/{username}')
                if user_check.status_code == 404:
                    logger.error(f"User '{username}' does not exist on GitHub")
                else:
                    logger.error(f"Repository '{org}/{repo}' not found or insufficient permissions")
                return False
            else:
                logger.error(f"Failed to add collaborator {username}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding collaborator {username}: {e}")
            return False

    def create_file(self, org: str, repo: str, path: str, message: str, content: str) -> bool:
        """Create file in repository"""
        try:
            import base64
            
            data = {
                'message': message,
                'content': base64.b64encode(content.encode()).decode()
            }
            
            response = self.make_request('PUT', f'/repos/{org}/{repo}/contents/{path}', json=data)
            
            if response.status_code == 201:
                logger.debug(f"Created file {path} in {org}/{repo}")
                return True
            else:
                logger.error(f"Failed to create file: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return False

    def create_issue(self, org: str, repo: str, title: str, body: str, labels: List[str] = None) -> Optional[int]:
        """Create an issue in repository"""
        try:
            data = {
                'title': title,
                'body': body,
                'labels': labels or []
            }
            
            response = self.make_request('POST', f'/repos/{org}/{repo}/issues', json=data)
            
            if response.status_code == 201:
                issue_data = response.json()
                logger.debug(f"Created issue #{issue_data['number']}: {title}")
                return issue_data['number']
            else:
                logger.error(f"Failed to create issue: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None
    
    ## version 1.0
    # def create_milestone(self, org: str, repo: str, title: str, description: str = "", due_date: str = None) -> Optional[int]:
    #     """Create milestone in repository"""
    #     try:
    #         data = {
    #             'title': title,
    #             'description': description,
    #             'state': 'open'
    #         }
            
    #         if due_date:
    #             data['due_on'] = due_date
            
    #         response = self.make_request('POST', f'/repos/{org}/{repo}/milestones', json=data)
            
    #         if response.status_code == 201:
    #             milestone_data = response.json()
    #             logger.debug(f"Created milestone: {title}")
    #             return milestone_data['number']
    #         else:
    #             logger.error(f"Failed to create milestone: {response.status_code}")
    #             return None
                
    #     except Exception as e:
    #         logger.error(f"Error creating milestone: {e}")
    #         return None
    
    def create_project(self, org: str, name: str, description: str = "") -> Optional[int]:
        """Create organization project"""
        try:
            data = {
                'name': name,
                'body': description
            }
            
            response = self.make_request('POST', f'/orgs/{org}/projects', json=data)
            
            if response.status_code == 201:
                project_data = response.json()
                logger.info(f"Created project: {name}")
                return project_data['id']
            else:
                logger.error(f"Failed to create project: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None
    
    def create_project_column(self, project_id: int, name: str) -> Optional[int]:
        """Create column in project"""
        try:
            data = {'name': name}
            
            response = self.make_request('POST', f'/projects/{project_id}/columns', json=data)
            
            if response.status_code == 201:
                column_data = response.json()
                logger.debug(f"Created project column: {name}")
                return column_data['id']
            else:
                logger.error(f"Failed to create project column: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating project column: {e}")
            return None
    
    def create_project_card(self, column_id: int, content_id: int = None, content_type: str = 'Issue', note: str = None) -> Optional[int]:
        """Create card in project column"""
        try:
            data = {}
            
            if content_id and content_type:
                data['content_id'] = content_id
                data['content_type'] = content_type
            elif note:
                data['note'] = note
            else:
                raise ValueError("Either content_id/content_type or note must be provided")
            
            response = self.make_request('POST', f'/projects/columns/{column_id}/cards', json=data)
            
            if response.status_code == 201:
                card_data = response.json()
                logger.debug(f"Created project card")
                return card_data['id']
            else:
                logger.error(f"Failed to create project card: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating project card: {e}")
            return None
    
    def get_repository_issues(self, org: str, repo: str, state: str = 'all') -> List[Dict]:
        """Get all issues from repository"""
        try:
            issues = []
            page = 1
            
            while True:
                response = self.make_request(
                    'GET', 
                    f'/repos/{org}/{repo}/issues',
                    params={'state': state, 'page': page, 'per_page': 100}
                )
                
                if response.status_code != 200:
                    break
                
                page_issues = response.json()
                if not page_issues:
                    break
                
                issues.extend(page_issues)
                page += 1
            
            return issues
            
        except Exception as e:
            logger.error(f"Error getting repository issues: {e}")
            return []
    
    def search_user_by_email(self, email: str) -> Optional[Dict]:
        """Search for GitHub user by email"""
        try:
            response = self.make_request('GET', f'/search/users', params={'q': f'{email} in:email'})
            
            if response.status_code == 200:
                data = response.json()
                if data['total_count'] > 0:
                    return data['items'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching user by email: {e}")
            return None
    
    def invite_to_organization(self, org: str, username: str, role: str = 'member') -> bool:
        """Invite user to organization"""
        try:
            data = {'role': role}
            
            response = self.make_request(
                'PUT',
                f'/orgs/{org}/memberships/{username}',
                json=data
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"Invited {username} to organization {org}")
                return True
            else:
                logger.error(f"Failed to invite {username}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error inviting user to organization: {e}")
            return False
    
    def check_collaborator(self, org: str, repo: str, username: str) -> bool:
        """Check if user is collaborator"""
        try:
            response = self.make_request('GET', f'/repos/{org}/{repo}/collaborators/{username}')
            return response.status_code == 204
        except Exception:
            return False
    
    def check_pending_invitation(self, org: str, repo: str, username: str) -> bool:
        """Check if user has pending invitation"""
        try:
            response = self.make_request('GET', f'/repos/{org}/{repo}/invitations')
            
            if response.status_code == 200:
                invitations = response.json()
                return any(inv.get('invitee', {}).get('login') == username for inv in invitations)
            
            return False
            
        except Exception:
            return False
    
    def get_organization_repositories(self, org: str) -> List[Dict]:
        """Get all repositories in organization"""
        try:
            repos = []
            page = 1
            
            while True:
                response = self.make_request(
                    'GET',
                    f'/orgs/{org}/repos',
                    params={'page': page, 'per_page': 100, 'type': 'all'}
                )
                
                if response.status_code != 200:
                    break
                
                page_repos = response.json()
                if not page_repos:
                    break
                
                repos.extend(page_repos)
                page += 1
            
            return repos
            
        except Exception as e:
            logger.error(f"Error getting organization repositories: {e}")
            return []
    
    def update_repository_file(self, org: str, repo: str, path: str, content: str, message: str, sha: str = None) -> bool:
        """Create or update file in repository"""
        try:
            import base64
            
            data = {
                'message': message,
                'content': base64.b64encode(content.encode()).decode()
            }
            
            if sha:
                data['sha'] = sha
            
            response = self.make_request('PUT', f'/repos/{org}/{repo}/contents/{path}', json=data)
            
            if response.status_code in [200, 201]:
                logger.debug(f"Updated file {path} in {org}/{repo}")
                return True
            else:
                logger.error(f"Failed to update file: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating repository file: {e}")
            return False
    
    def get_repository_file(self, org: str, repo: str, path: str) -> Optional[Dict]:
        """Get file from repository"""
        try:
            response = self.make_request('GET', f'/repos/{org}/{repo}/contents/{path}')
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting repository file: {e}")
            return None