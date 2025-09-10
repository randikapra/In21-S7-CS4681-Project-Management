"""
Bulk processing for 100+ operations with progress tracking
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .github_client import GitHubClient
from .utils import load_project_data, save_progress_data, batch_process

logger = logging.getLogger(__name__)

class BulkProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        self.max_workers = config.get('bulk_processing', {}).get('max_workers', 5)
        self.batch_size = config.get('bulk_processing', {}).get('batch_size', 10)
        self.delay_between_batches = config.get('bulk_processing', {}).get('delay', 2.0)
        
        # Progress tracking
        self.progress_data = {
            'total_items': 0,
            'processed_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'start_time': None,
            'end_time': None,
            'status': 'idle'
        }
        
        # Thread-safe progress tracking
        self.progress_lock = threading.Lock()
    
    def bulk_create_repositories(self, project_csv_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Bulk create repositories with progress tracking"""
        try:
            projects = load_project_data(project_csv_path)
            self._initialize_progress(len(projects), 'Creating repositories')
            
            logger.info(f"Starting bulk repository creation for {len(projects)} projects")
            
            results = {
                'successful': [],
                'failed': [],
                'summary': {},
                'operation': 'bulk_create_repositories',
                'timestamp': datetime.now().isoformat()
            }
            
            # Process in batches with threading
            def create_repo_batch(batch_projects):
                batch_results = []
                for project in batch_projects:
                    try:
                        from .repo_manager import RepositoryManager
                        repo_manager = RepositoryManager(self.config)
                        result = repo_manager.create_project_folder(project)
                        batch_results.append(result)
                        
                        self._update_progress(1, progress_callback)
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'project': project,
                            'error': str(e)
                        }
                        batch_results.append(error_result)
                        self._update_progress(1, progress_callback)
                
                return batch_results
            
            # Process batches
            all_results = []
            for i in range(0, len(projects), self.batch_size):
                batch = projects[i:i + self.batch_size]
                batch_results = create_repo_batch(batch)
                all_results.extend(batch_results)
                
                # Rate limiting between batches
                if i + self.batch_size < len(projects):
                    logger.info(f"Completed batch {i//self.batch_size + 1}, waiting {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
            
            # Process results
            for result in all_results:
                if result.get('status') == 'success':
                    results['successful'].append(result)
                else:
                    results['failed'].append(result)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_create_repositories')
            
            logger.info(f"Bulk repository creation completed. Success: {len(results['successful'])}, Failed: {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Bulk repository creation failed: {e}")
            raise
    
    def bulk_send_invitations(self, project_csv_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Bulk send invitations with progress tracking"""
        try:
            from .invitation_manager import InvitationManager
            invitation_manager = InvitationManager(self.config)
            
            projects = load_project_data(project_csv_path)
            self._initialize_progress(len(projects), 'Sending invitations')
            
            logger.info(f"Starting bulk invitation sending for {len(projects)} projects")
            
            results = {
                'successful': [],
                'failed': [],
                'partial_success': [],
                'summary': {},
                'operation': 'bulk_send_invitations',
                'timestamp': datetime.now().isoformat()
            }
            
            # Process invitations in batches
            for i in range(0, len(projects), self.batch_size):
                batch = projects[i:i + self.batch_size]
                
                logger.info(f"Processing invitation batch {i//self.batch_size + 1}/{(len(projects)-1)//self.batch_size + 1}")
                
                for project in batch:
                    try:
                        from .utils import generate_repo_name, load_supervisor_data
                        repo_name = generate_repo_name(project, self.config)
                        supervisors = load_supervisor_data(self.config)
                        
                        result = invitation_manager.send_project_invitation(project, repo_name, supervisors)
                        
                        if result['status'] == 'success':
                            results['successful'].append(result)
                        elif result['status'] == 'partial_success':
                            results['partial_success'].append(result)
                        else:
                            results['failed'].append(result)
                        
                        self._update_progress(1, progress_callback)
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'project': project,
                            'error': str(e)
                        }
                        results['failed'].append(error_result)
                        self._update_progress(1, progress_callback)
                
                # Rate limiting between batches
                if i + self.batch_size < len(projects):
                    time.sleep(self.delay_between_batches)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_send_invitations')
            
            logger.info(f"Bulk invitation sending completed. Success: {len(results['successful'])}, Failed: {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Bulk invitation sending failed: {e}")
            raise
    
    def bulk_update_progress(self, project_csv_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Bulk update progress data for all projects"""
        try:
            from .progress_aggregator import ProgressAggregator
            progress_aggregator = ProgressAggregator(self.config)
            
            projects = load_project_data(project_csv_path)
            self._initialize_progress(len(projects), 'Updating progress data')
            
            logger.info(f"Starting bulk progress update for {len(projects)} projects")
            
            results = {
                'successful': [],
                'failed': [],
                'summary': {},
                'operation': 'bulk_update_progress',
                'timestamp': datetime.now().isoformat(),
                'progress_data': {}
            }
            
            # Collect progress data
            try:
                progress_data = progress_aggregator.collect_all_progress(project_csv_path)
                results['progress_data'] = progress_data
                
                # Update progress for each project processed
                for project_progress in progress_data.get('projects', []):
                    self._update_progress(1, progress_callback)
                    results['successful'].append({
                        'project': project_progress.get('project'),
                        'progress': project_progress.get('overall_progress', 0)
                    })
                
            except Exception as e:
                results['failed'].append({
                    'error': f"Failed to collect progress data: {str(e)}"
                })
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_update_progress')
            
            logger.info(f"Bulk progress update completed. Processed: {len(results['successful'])} projects")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Bulk progress update failed: {e}")
            raise
    
    def bulk_generate_reports(self, project_csv_path: str, report_types: List[str], progress_callback: Optional[Callable] = None) -> Dict:
        """Bulk generate various types of reports"""
        try:
            self._initialize_progress(len(report_types), 'Generating reports')
            
            logger.info(f"Starting bulk report generation for {len(report_types)} report types")
            
            results = {
                'successful': [],
                'failed': [],
                'summary': {},
                'operation': 'bulk_generate_reports',
                'timestamp': datetime.now().isoformat(),
                'reports': {}
            }
            
            for report_type in report_types:
                try:
                    logger.info(f"Generating {report_type} report...")
                    
                    if report_type == 'weekly_progress':
                        from .progress_aggregator import ProgressAggregator
                        aggregator = ProgressAggregator(self.config)
                        report = aggregator.generate_weekly_report(project_csv_path)
                        results['reports']['weekly_progress'] = report
                        
                    elif report_type == 'analytics':
                        from .analytics_generator import AnalyticsGenerator
                        analytics = AnalyticsGenerator(self.config)
                        report = analytics.generate_comprehensive_analytics(project_csv_path)
                        results['reports']['analytics'] = report
                        
                    elif report_type == 'risk_assessment':
                        from .analytics_generator import AnalyticsGenerator
                        analytics = AnalyticsGenerator(self.config)
                        full_analytics = analytics.generate_comprehensive_analytics(project_csv_path)
                        report = full_analytics.get('risk_analytics', {})
                        results['reports']['risk_assessment'] = report
                    
                    results['successful'].append({
                        'report_type': report_type,
                        'status': 'generated'
                    })
                    
                    self._update_progress(1, progress_callback)
                    
                except Exception as e:
                    results['failed'].append({
                        'report_type': report_type,
                        'error': str(e)
                    })
                    self._update_progress(1, progress_callback)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_generate_reports')
            
            logger.info(f"Bulk report generation completed. Success: {len(results['successful'])}, Failed: {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Bulk report generation failed: {e}")
            raise
    
    def bulk_cleanup_repositories(self, repo_names: List[str], progress_callback: Optional[Callable] = None) -> Dict:
        """Bulk cleanup/delete repositories (use with extreme caution)"""
        try:
            self._initialize_progress(len(repo_names), 'Cleaning up repositories')
            
            logger.warning(f"Starting bulk repository cleanup for {len(repo_names)} repositories")
            
            results = {
                'successful': [],
                'failed': [],
                'summary': {},
                'operation': 'bulk_cleanup_repositories',
                'timestamp': datetime.now().isoformat()
            }
            
            # Confirm cleanup operation
            logger.warning("Repository cleanup is destructive and cannot be undone!")
            
            for repo_name in repo_names:
                try:
                    # Add safety check - only delete if repo name matches expected pattern
                    if not self._is_safe_to_delete(repo_name):
                        results['failed'].append({
                            'repo_name': repo_name,
                            'error': 'Repository name does not match expected pattern - safety check failed'
                        })
                        self._update_progress(1, progress_callback)
                        continue
                    
                    # Delete repository
                    from .repo_manager import RepositoryManager
                    repo_manager = RepositoryManager(self.config)
                    success = repo_manager.delete_repository(repo_name)
                    
                    if success:
                        results['successful'].append({
                            'repo_name': repo_name,
                            'status': 'deleted'
                        })
                    else:
                        results['failed'].append({
                            'repo_name': repo_name,
                            'error': 'Failed to delete repository'
                        })
                    
                    self._update_progress(1, progress_callback)
                    
                    # Rate limiting for delete operations
                    time.sleep(1)
                    
                except Exception as e:
                    results['failed'].append({
                        'repo_name': repo_name,
                        'error': str(e)
                    })
                    self._update_progress(1, progress_callback)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_cleanup_repositories')
            
            logger.info(f"Bulk repository cleanup completed. Deleted: {len(results['successful'])}, Failed: {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Bulk repository cleanup failed: {e}")
            raise
    
    def _initialize_progress(self, total_items: int, operation: str):
        """Initialize progress tracking"""
        with self.progress_lock:
            self.progress_data = {
                'total_items': total_items,
                'processed_items': 0,
                'successful_items': 0,
                'failed_items': 0,
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'status': 'running',
                'operation': operation,
                'progress_percentage': 0.0
            }
    
    def _update_progress(self, increment: int = 1, callback: Optional[Callable] = None):
        """Update progress tracking"""
        with self.progress_lock:
            self.progress_data['processed_items'] += increment
            
            if self.progress_data['total_items'] > 0:
                self.progress_data['progress_percentage'] = (
                    self.progress_data['processed_items'] / self.progress_data['total_items']
                ) * 100
            
            # Call progress callback if provided
            if callback:
                try:
                    callback(self.progress_data.copy())
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def _finalize_progress(self, status: str):
        """Finalize progress tracking"""
        with self.progress_lock:
            self.progress_data['status'] = status
            self.progress_data['end_time'] = datetime.now().isoformat()
            
            if self.progress_data['start_time']:
                start_time = datetime.fromisoformat(self.progress_data['start_time'])
                end_time = datetime.fromisoformat(self.progress_data['end_time'])
                duration = (end_time - start_time).total_seconds()
                self.progress_data['duration_seconds'] = duration
    
    def _generate_summary(self, results: Dict) -> Dict:
        """Generate operation summary"""
        total_processed = len(results.get('successful', [])) + len(results.get('failed', [])) + len(results.get('partial_success', []))
        
        summary = {
            'total_processed': total_processed,
            'successful_count': len(results.get('successful', [])),
            'failed_count': len(results.get('failed', [])),
            'partial_success_count': len(results.get('partial_success', [])),
            'success_rate': 0.0,
            'operation': results.get('operation', 'unknown'),
            'timestamp': results.get('timestamp')
        }
        
        if total_processed > 0:
            summary['success_rate'] = (summary['successful_count'] / total_processed) * 100
        
        return summary
    
    def _save_bulk_results(self, results: Dict, operation_name: str):
        """Save bulk operation results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{operation_name}_{timestamp}.json'
            
            save_progress_data(results, filename, 'data/bulk_operations')
            
            # Also save as latest for the operation type
            save_progress_data(results, f'latest_{operation_name}.json', 'data/bulk_operations')
            
        except Exception as e:
            logger.error(f"Error saving bulk results: {e}")
    
    def _is_safe_to_delete(self, repo_name: str) -> bool:
        """Safety check for repository deletion"""
        # Only allow deletion of repos that match expected project repo pattern
        # This is a safety measure to prevent accidental deletion of important repos
        
        # Check if repo name contains index number pattern (IN21-XXX)
        import re
        index_pattern = r'IN\d{2}-\d{3}'
        
        if not re.search(index_pattern, repo_name):
            return False
        
        # Check if repo name doesn't contain sensitive keywords
        sensitive_keywords = ['master', 'main', 'admin', 'config', 'system']
        repo_name_lower = repo_name.lower()
        
        for keyword in sensitive_keywords:
            if keyword in repo_name_lower:
                return False
        
        return True
    
    def get_progress_status(self) -> Dict:
        """Get current progress status"""
        with self.progress_lock:
            return self.progress_data.copy()
    
    def create_progress_display(self, show_details: bool = True) -> str:
        """Create progress display string"""
        with self.progress_lock:
            progress = self.progress_data.copy()
        
        if progress['status'] == 'idle':
            return "No operation in progress"
        
        display = f"""
Operation: {progress.get('operation', 'Unknown')}
Status: {progress['status']}
Progress: {progress['processed_items']}/{progress['total_items']} ({progress['progress_percentage']:.1f}%)
"""
        
        if show_details:
            display += f"""Successful: {progress['successful_items']}
Failed: {progress['failed_items']}
"""
        
        if progress['start_time']:
            display += f"Started: {progress['start_time']}\n"
        
        if progress['end_time']:
            display += f"Completed: {progress['end_time']}\n"
            if 'duration_seconds' in progress:
                display += f"Duration: {progress['duration_seconds']:.1f} seconds\n"
        
        return display.strip()
    
    def retry_failed_operations(self, failed_results: List[Dict], operation_type: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Retry failed operations"""
        try:
            self._initialize_progress(len(failed_results), f'Retrying {operation_type}')
            
            logger.info(f"Retrying {len(failed_results)} failed {operation_type} operations")
            
            results = {
                'successful': [],
                'failed': [],
                'summary': {},
                'operation': f'retry_{operation_type}',
                'timestamp': datetime.now().isoformat()
            }
            
            for failed_item in failed_results:
                try:
                    # Retry based on operation type
                    if operation_type == 'repository_creation':
                        from .repo_manager import RepositoryManager
                        repo_manager = RepositoryManager(self.config)
                        result = repo_manager.create_project_folder(failed_item.get('project'))
                        
                    elif operation_type == 'invitation_sending':
                        from .invitation_manager import InvitationManager
                        from .utils import generate_repo_name, load_supervisor_data
                        
                        invitation_manager = InvitationManager(self.config)
                        project = failed_item.get('project')
                        repo_name = generate_repo_name(project, self.config)
                        supervisors = load_supervisor_data(self.config)
                        result = invitation_manager.send_project_invitation(project, repo_name, supervisors)
                    
                    else:
                        result = {'status': 'error', 'error': 'Unknown operation type'}
                    
                    if result.get('status') == 'success':
                        results['successful'].append(result)
                    else:
                        results['failed'].append(result)
                    
                    self._update_progress(1, progress_callback)
                    
                    # Rate limiting for retries
                    time.sleep(0.5)
                    
                except Exception as e:
                    error_result = {
                        'status': 'error',
                        'original_item': failed_item,
                        'error': str(e)
                    }
                    results['failed'].append(error_result)
                    self._update_progress(1, progress_callback)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, f'retry_{operation_type}')
            
            logger.info(f"Retry operation completed. Success: {len(results['successful'])}, Still Failed: {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Retry operation failed: {e}")
            raise
    
    def validate_bulk_operation_prerequisites(self, operation_type: str, project_csv_path: str = None) -> Dict:
        """Validate prerequisites for bulk operations"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        try:
            # Check GitHub API connectivity
            try:
                self.github.check_rate_limit()
                validation_results['checks']['github_api'] = 'OK'
            except Exception as e:
                validation_results['valid'] = False
                validation_results['errors'].append(f"GitHub API connectivity failed: {e}")
                validation_results['checks']['github_api'] = 'FAILED'
            
            # Check rate limits
            if self.github.rate_limit_remaining < 100:
                validation_results['warnings'].append(f"Low rate limit: {self.github.rate_limit_remaining} requests remaining")
                validation_results['checks']['rate_limit'] = 'WARNING'
            else:
                validation_results['checks']['rate_limit'] = 'OK'
            
            # Check organization access
            try:
                repos = self.github.get_organization_repositories(self.org)
                validation_results['checks']['organization_access'] = 'OK'
            except Exception as e:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Organization access failed: {e}")
                validation_results['checks']['organization_access'] = 'FAILED'
            
            # Check project data if provided
            if project_csv_path:
                try:
                    projects = load_project_data(project_csv_path)
                    validation_results['checks']['project_data'] = f'OK ({len(projects)} projects)'
                    
                    if len(projects) > 200:
                        validation_results['warnings'].append(f"Large number of projects ({len(projects)}) - operation may take significant time")
                    
                except Exception as e:
                    validation_results['valid'] = False
                    validation_results['errors'].append(f"project data validation failed: {e}")
                    validation_results['checks']['project_data'] = 'FAILED'
            
            # Operation-specific checks
            if operation_type == 'repository_creation':
                # Check if templates exist
                import os
                if not os.path.exists('templates'):
                    validation_results['warnings'].append("Templates directory not found - will use default templates")
                    validation_results['checks']['templates'] = 'WARNING'
                else:
                    validation_results['checks']['templates'] = 'OK'
            
            elif operation_type == 'invitation_sending':
                # Check supervisor configuration
                try:
                    from .utils import load_supervisor_data
                    supervisors = load_supervisor_data(self.config)
                    if not supervisors:
                        validation_results['valid'] = False
                        validation_results['errors'].append("No supervisors configured")
                        validation_results['checks']['supervisors'] = 'FAILED'
                    else:
                        validation_results['checks']['supervisors'] = f'OK ({len(supervisors)} supervisors)'
                except Exception as e:
                    validation_results['valid'] = False
                    validation_results['errors'].append(f"Supervisor configuration error: {e}")
                    validation_results['checks']['supervisors'] = 'FAILED'
            
            # Check disk space for large operations
            import shutil
            free_space_gb = shutil.disk_usage('.').free / (1024**3)
            if free_space_gb < 1:
                validation_results['warnings'].append(f"Low disk space: {free_space_gb:.1f}GB available")
                validation_results['checks']['disk_space'] = 'WARNING'
            else:
                validation_results['checks']['disk_space'] = 'OK'
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
        
        return validation_results
    
    def estimate_operation_time(self, operation_type: str, item_count: int) -> Dict:
        """Estimate time required for bulk operation"""
        # Base time estimates per item (in seconds)
        time_estimates = {
            'repository_creation': 3.0,  # Repository creation + setup
            'invitation_sending': 1.0,   # Send invitations
            'progress_update': 0.5,      # Update progress data
            'report_generation': 10.0,   # Generate reports
            'repository_cleanup': 2.0    # Delete repositories
        }
        
        base_time_per_item = time_estimates.get(operation_type, 2.0)
        
        # Calculate total time including batch delays
        batches = (item_count + self.batch_size - 1) // self.batch_size
        batch_delay_time = (batches - 1) * self.delay_between_batches
        
        processing_time = item_count * base_time_per_item
        total_time = processing_time + batch_delay_time
        
        return {
            'estimated_total_seconds': total_time,
            'estimated_total_minutes': total_time / 60,
            'estimated_processing_time': processing_time,
            'estimated_delay_time': batch_delay_time,
            'batches_required': batches,
            'items_per_batch': self.batch_size,
            'base_time_per_item': base_time_per_item
        }
    
    def get_bulk_operation_history(self, operation_type: str = None, limit: int = 10) -> List[Dict]:
        """Get history of bulk operations"""
        try:
            import os
            import glob
            
            history = []
            
            # Look for bulk operation files
            pattern = 'data/bulk_operations/*.json'
            if operation_type:
                pattern = f'data/bulk_operations/*{operation_type}*.json'
            
            files = glob.glob(pattern)
            files.sort(key=os.path.getmtime, reverse=True)  # Most recent first
            
            for file_path in files[:limit]:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        history.append({
                            'file_path': file_path,
                            'operation': data.get('operation', 'unknown'),
                            'timestamp': data.get('timestamp'),
                            'summary': data.get('summary', {}),
                            'total_processed': data.get('summary', {}).get('total_processed', 0),
                            'success_rate': data.get('summary', {}).get('success_rate', 0)
                        })
                except Exception as e:
                    logger.error(f"Error reading operation history file {file_path}: {e}")
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting bulk operation history: {e}")
            return []