
"""
Bulk processing for 100+ operations with progress tracking
Enhanced version focusing on folder creation and student management
"""

import logging
import time
import threading
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import load_project_data, save_progress_data, batch_process
from .repo_manager import RepositoryManager
from .invitation_manager import InvitationManager
from .student_manager import StudentManager
from .progress_aggregator import ProgressAggregator

logger = logging.getLogger(__name__)

class BulkProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.repo_manager = RepositoryManager(config)
        self.invitation_manager = InvitationManager(config)
        self.student_manager = StudentManager(config)
        self.progress_aggregator = ProgressAggregator(config)
        
        # Bulk processing configuration
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
        
    def bulk_create_student_folders(self, project_csv_path: str, 
                                   progress_callback: Optional[Callable] = None) -> Dict:
        """Create folders for all students in the main repository with enhanced progress tracking"""
        try:
            students = load_project_data(project_csv_path)
            self._initialize_progress(len(students), 'Creating student folders')
            
            logger.info(f"Starting bulk folder creation for {len(students)} students")
            
            results = {
                'successful': [],
                'failed': [],
                'total_processed': 0,
                'summary': {},
                'operation': 'bulk_create_student_folders',
                'timestamp': datetime.now().isoformat()
            }
            
            # Process in batches
            def create_folder_batch(batch_students):
                batch_results = []
                for student in batch_students:
                    try:
                        logger.info(f"Creating folder for {student['index_number']}")
                        
                        # Create student folder
                        folder_result = self.repo_manager.create_student_folder(student)
                        batch_results.append(folder_result)
                        
                        self._update_progress(1, progress_callback, folder_result.get('status') == 'success')
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'student': student,
                            'error': str(e)
                        }
                        batch_results.append(error_result)
                        self._update_progress(1, progress_callback, False)
                
                return batch_results
            
            # Process batches
            all_results = []
            for i in range(0, len(students), self.batch_size):
                batch = students[i:i + self.batch_size]
                batch_number = i // self.batch_size + 1
                total_batches = (len(students) - 1) // self.batch_size + 1
                
                logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} students)")
                
                batch_results = create_folder_batch(batch)
                all_results.extend(batch_results)
                
                # Rate limiting between batches
                if i + self.batch_size < len(students):
                    logger.info(f"Completed batch {batch_number}, waiting {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
            
            # Process results
            for result in all_results:
                if result.get('status') == 'success':
                    results['successful'].append(result)
                else:
                    results['failed'].append(result)
                results['total_processed'] += 1
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_create_student_folders')
            
            logger.info(f"Bulk folder creation completed. Success: {results['summary']['successful_count']}, Failed: {results['summary']['failed_count']}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Failed to create student folders: {e}")
            raise

    def bulk_create_student_issues(self, project_csv_path: str, 
                                  progress_callback: Optional[Callable] = None) -> Dict:
        """Create milestone tracking issues for all students with enhanced progress tracking"""
        try:
            students = load_project_data(project_csv_path)
            self._initialize_progress(len(students), 'Creating student issues')
            
            logger.info(f"Starting bulk issue creation for {len(students)} students")
            
            results = {
                'successful': [],
                'failed': [],
                'total_processed': 0,
                'summary': {},
                'operation': 'bulk_create_student_issues',
                'timestamp': datetime.now().isoformat()
            }
            
            # Process in batches
            for i in range(0, len(students), self.batch_size):
                batch = students[i:i + self.batch_size]
                batch_number = i // self.batch_size + 1
                total_batches = (len(students) - 1) // self.batch_size + 1
                
                logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} students)")
                
                for student in batch:
                    try:
                        logger.info(f"Creating issues for {student['index_number']}")
                        
                        # Create student milestone issues
                        issues_result = self.student_manager.create_student_issues(student)
                        
                        if issues_result.get('status') == 'success':
                            results['successful'].append(issues_result)
                        else:
                            results['failed'].append(issues_result)
                        
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, issues_result.get('status') == 'success')
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'student': student,
                            'error': str(e)
                        }
                        results['failed'].append(error_result)
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, False)
                
                # Rate limiting between batches
                if i + self.batch_size < len(students):
                    time.sleep(self.delay_between_batches)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_create_student_issues')
            
            logger.info(f"Issue creation completed. Success: {results['summary']['successful_count']}, Failed: {results['summary']['failed_count']}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Failed to create student issues: {e}")
            raise

    def bulk_send_invitations(self, project_csv_path: str, 
                             progress_callback: Optional[Callable] = None) -> Dict:
        """Send repository invitations to all students and supervisors with enhanced progress tracking"""
        try:
            students = load_project_data(project_csv_path)
            # +1 for supervisors batch
            self._initialize_progress(len(students) + 1, 'Sending invitations')
            
            logger.info(f"Starting bulk invitation sending for {len(students)} students plus supervisors")
            
            results = {
                'successful': [],
                'failed': [],
                'partial_success': [],
                'total_processed': 0,
                'summary': {},
                'operation': 'bulk_send_invitations',
                'timestamp': datetime.now().isoformat()
            }
            
            # Send student invitations in batches
            for i in range(0, len(students), self.batch_size):
                batch = students[i:i + self.batch_size]
                batch_number = i // self.batch_size + 1
                total_batches = (len(students) - 1) // self.batch_size + 1
                
                logger.info(f"Processing invitation batch {batch_number}/{total_batches} ({len(batch)} students)")
                
                for student in batch:
                    try:
                        logger.info(f"Inviting student {student['index_number']}")
                        
                        # Send repository invitation
                        # invitation_result = self.invitation_manager.send_repository_invitation(student)
                        # send projects invitations
                        invitation_result = self.invitation_manager.send_student_invitation(student)
                        
                        if invitation_result.get('status') == 'success':
                            results['successful'].append(invitation_result)
                        elif invitation_result.get('status') == 'partial_success':
                            results['partial_success'].append(invitation_result)
                        else:
                            results['failed'].append(invitation_result)
                        
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, invitation_result.get('status') == 'success')
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'student': student,
                            'error': str(e)
                        }
                        results['failed'].append(error_result)
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, False)
                
                # Rate limiting between batches
                if i + self.batch_size < len(students):
                    time.sleep(self.delay_between_batches)
            
            # Send supervisor invitations
            logger.info("Sending supervisor invitations...")
            try:
                supervisor_results = self.invitation_manager.send_supervisors_invitations()
                
                # Add supervisor results to totals
                results['successful'].extend(supervisor_results.get('successful', []))
                results['failed'].extend(supervisor_results.get('failed', []))
                results['total_processed'] += supervisor_results.get('total_processed', 0)
                
                self._update_progress(1, progress_callback, len(supervisor_results.get('successful', [])) > 0)
                
            except Exception as e:
                logger.error(f"Failed to send supervisor invitations: {e}")
                results['failed'].append({
                    'status': 'error',
                    'type': 'supervisor_invitations',
                    'error': str(e)
                })
                self._update_progress(1, progress_callback, False)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_send_invitations')
            
            logger.info(f"Invitation sending completed. Success: {results['summary']['successful_count']}, Failed: {results['summary']['failed_count']}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Failed to send bulk invitations: {e}")
            raise

    def bulk_update_progress(self, project_csv_path: str, 
                            progress_callback: Optional[Callable] = None) -> Dict:
        """Update progress tracking for all students with enhanced tracking"""
        try:
            students = load_project_data(project_csv_path)
            self._initialize_progress(len(students), 'Updating progress data')
            
            logger.info(f"Starting bulk progress update for {len(students)} students")
            
            results = {
                'successful': [],
                'failed': [],
                'total_processed': 0,
                'summary': {},
                'operation': 'bulk_update_progress',
                'timestamp': datetime.now().isoformat(),
                'progress_data': {}
            }
            
            # Collect overall progress data first
            try:
                progress_data = self.progress_aggregator.collect_all_progress(project_csv_path)
                results['progress_data'] = progress_data
            except Exception as e:
                logger.error(f"Failed to collect overall progress data: {e}")
            
            # Update individual student progress in batches
            for i in range(0, len(students), self.batch_size):
                batch = students[i:i + self.batch_size]
                batch_number = i // self.batch_size + 1
                total_batches = (len(students) - 1) // self.batch_size + 1
                
                logger.info(f"Processing progress batch {batch_number}/{total_batches} ({len(batch)} students)")
                
                for student in batch:
                    try:
                        logger.info(f"Updating progress for {student['index_number']}")
                        
                        # Update student progress
                        progress_result = self.student_manager.track_student_progress(student)
                        
                        if 'error' not in progress_result:
                            results['successful'].append(progress_result)
                        else:
                            results['failed'].append(progress_result)
                        
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, 'error' not in progress_result)
                        
                    except Exception as e:
                        error_result = {
                            'status': 'error',
                            'student': student,
                            'error': str(e)
                        }
                        results['failed'].append(error_result)
                        results['total_processed'] += 1
                        self._update_progress(1, progress_callback, False)
                
                # Rate limiting between batches
                if i + self.batch_size < len(students):
                    time.sleep(self.delay_between_batches)
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(results, 'bulk_update_progress')
            
            logger.info(f"Progress update completed. Success: {results['summary']['successful_count']}, Failed: {results['summary']['failed_count']}")
            
            return results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Failed to update student progress: {e}")
            raise

    def bulk_generate_reports(self, project_csv_path: str, report_types: List[str], 
                             progress_callback: Optional[Callable] = None) -> Dict:
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
                        report = self.progress_aggregator.generate_weekly_report(project_csv_path)
                        results['reports']['weekly_progress'] = report
                        
                    elif report_type == 'analytics':
                        try:
                            from .analytics_generator import AnalyticsGenerator
                            analytics = AnalyticsGenerator(self.config)
                            report = analytics.generate_comprehensive_analytics(project_csv_path)
                            results['reports']['analytics'] = report
                        except ImportError:
                            logger.warning("Analytics generator not available")
                            report = {'error': 'Analytics generator module not available'}
                            results['reports']['analytics'] = report
                            
                    elif report_type == 'risk_assessment':
                        try:
                            from .analytics_generator import AnalyticsGenerator
                            analytics = AnalyticsGenerator(self.config)
                            full_analytics = analytics.generate_comprehensive_analytics(project_csv_path)
                            report = full_analytics.get('risk_analytics', {})
                            results['reports']['risk_assessment'] = report
                        except ImportError:
                            logger.warning("Analytics generator not available for risk assessment")
                            report = {'error': 'Analytics generator module not available'}
                            results['reports']['risk_assessment'] = report
                    
                    else:
                        raise ValueError(f"Unknown report type: {report_type}")
                    
                    results['successful'].append({
                        'report_type': report_type,
                        'status': 'generated'
                    })
                    
                    self._update_progress(1, progress_callback, True)
                    
                except Exception as e:
                    results['failed'].append({
                        'report_type': report_type,
                        'error': str(e)
                    })
                    self._update_progress(1, progress_callback, False)
            
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

    def validate_bulk_operation_prerequisites(self, operation_type: str, 
                                           project_csv_path: str) -> Dict:
        """Enhanced validation of prerequisites for bulk operations"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        try:
            # Check if CSV file exists and is readable
            try:
                students = load_project_data(project_csv_path)
                if not students:
                    validation_result['errors'].append("No students found in CSV file")
                    validation_result['valid'] = False
                else:
                    validation_result['checks']['project_data'] = f'OK ({len(students)} students)'
                    
                    if len(students) > 200:
                        validation_result['warnings'].append(f"Large number of students ({len(students)}) - operation may take significant time")
                    
            except Exception as e:
                validation_result['errors'].append(f"Cannot read project CSV: {e}")
                validation_result['valid'] = False
                validation_result['checks']['project_data'] = 'FAILED'
                return validation_result
            
            # Validate GitHub access
            try:
                org = self.config['github']['organization']
                repo_name = self.config['repository']['name']
                
                # Check repository existence for relevant operations
                if operation_type in ['bulk_create_student_folders', 'bulk_create_student_issues', 'bulk_send_invitations']:
                    # For student folder operations, we need the main repository to exist
                    repo_info = self.repo_manager.github.get_repository(org, repo_name)
                    if not repo_info and operation_type != 'bulk_create_repositories':
                        validation_result['errors'].append(f"Repository {org}/{repo_name} does not exist")
                        validation_result['valid'] = False
                        validation_result['checks']['repository_access'] = 'FAILED'
                    else:
                        validation_result['checks']['repository_access'] = 'OK'
                        
            except Exception as e:
                validation_result['errors'].append(f"GitHub API access error: {e}")
                validation_result['valid'] = False
                validation_result['checks']['github_api'] = 'FAILED'
            
            # # Check GitHub rate limits
            # try:
            #     rate_limit_info = self.repo_manager.github.check_rate_limit()
            #     # remaining = rate_limit_info.get('remaining', 0)
            #     remaining = rate_limit_info.get('remaining', 0) if rate_limit_info else 0
                
            #     if remaining < 100:
            #         validation_result['warnings'].append(f"Low GitHub rate limit: {remaining} requests remaining")
            #         validation_result['checks']['rate_limit'] = 'WARNING'
            #     else:
            #         validation_result['checks']['rate_limit'] = 'OK'
                    
            # except Exception as e:
            #     validation_result['warnings'].append(f"Could not check rate limit: {e}")
            #     validation_result['checks']['rate_limit'] = 'WARNING'
            
            # Check GitHub rate limits
            try:
                rate_limit_info = self.repo_manager.github.check_rate_limit()
                remaining = rate_limit_info.get('remaining', 0) if rate_limit_info else 0
                
                if remaining < 100:
                    validation_result['warnings'].append(f"Low GitHub rate limit: {remaining} requests remaining")
                    validation_result['checks']['rate_limit'] = 'WARNING'
                else:
                    validation_result['checks']['rate_limit'] = f'OK ({remaining} requests remaining)'
                    
            except Exception as e:
                validation_result['warnings'].append(f"Could not check rate limit: {e}")
                validation_result['checks']['rate_limit'] = 'WARNING'

            # Validate student data
            required_fields = ['index_number', 'research_area', 'email']
            for i, student in enumerate(students):
                for field in required_fields:
                    if field not in student or not student[field]:
                        validation_result['warnings'].append(
                            f"Student {i+1}: Missing or empty field '{field}'"
                        )
                
                # Check GitHub username for invitation operations
                if operation_type == 'bulk_send_invitations' and not student.get('github_username'):
                    validation_result['warnings'].append(
                        f"Student {student.get('index_number', i+1)}: No GitHub username provided"
                    )
            
            # Validate configuration
            required_config = ['github.token', 'github.organization', 'repository.name']
            for config_path in required_config:
                keys = config_path.split('.')
                current = self.config
                try:
                    for key in keys:
                        current = current[key]
                    if not current:
                        validation_result['errors'].append(f"Configuration missing: {config_path}")
                        validation_result['valid'] = False
                except KeyError:
                    validation_result['errors'].append(f"Configuration missing: {config_path}")
                    validation_result['valid'] = False
            
            # Operation-specific validation
            if operation_type == 'bulk_send_invitations':
                # Check supervisor configuration
                try:
                    supervisors = self.config.get('supervisors', [])
                    if not supervisors:
                        validation_result['warnings'].append("No supervisors configured")
                        validation_result['checks']['supervisors'] = 'WARNING'
                    else:
                        validation_result['checks']['supervisors'] = f'OK ({len(supervisors)} supervisors)'
                except Exception as e:
                    validation_result['warnings'].append(f"Supervisor configuration error: {e}")
                    validation_result['checks']['supervisors'] = 'WARNING'
            
            # Check disk space
            import shutil
            try:
                free_space_gb = shutil.disk_usage('.').free / (1024**3)
                if free_space_gb < 1:
                    validation_result['warnings'].append(f"Low disk space: {free_space_gb:.1f}GB available")
                    validation_result['checks']['disk_space'] = 'WARNING'
                else:
                    validation_result['checks']['disk_space'] = 'OK'
            except Exception:
                validation_result['checks']['disk_space'] = 'UNKNOWN'
            
            return validation_result
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
            validation_result['valid'] = False
            validation_result['checks']['validation'] = 'FAILED'
            return validation_result

    def retry_failed_operations(self, failed_results: List[Dict], 
                               operation_type: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Retry failed operations with enhanced tracking"""
        try:
            self._initialize_progress(len(failed_results), f'Retrying {operation_type}')
            
            logger.info(f"Retrying {len(failed_results)} failed {operation_type} operations")
            
            retry_results = {
                'successful': [],
                'failed': [],
                'total_retried': len(failed_results),
                'operation': f'retry_{operation_type}',
                'timestamp': datetime.now().isoformat()
            }
            
            for failed_item in failed_results:
                try:
                    student = failed_item.get('student')
                    if not student:
                        retry_results['failed'].append({
                            'error': 'No student data in failed item',
                            'original_item': failed_item
                        })
                        self._update_progress(1, progress_callback, False)
                        continue
                    
                    result = None
                    
                    if operation_type == 'folder_creation':
                        result = self.repo_manager.create_student_folder(student)
                        
                    elif operation_type == 'invitation_sending':
                        result = self.invitation_manager.send_repository_invitation(student)
                        
                    elif operation_type == 'issue_creation':
                        result = self.student_manager.create_student_issues(student)
                        
                    elif operation_type == 'progress_update':
                        result = self.student_manager.track_student_progress(student)
                    
                    else:
                        result = {'status': 'error', 'error': f'Unknown operation type: {operation_type}'}
                    
                    if result and result.get('status') == 'success':
                        retry_results['successful'].append(result)
                        self._update_progress(1, progress_callback, True)
                    else:
                        retry_results['failed'].append(result or {
                            'status': 'error',
                            'error': 'No result returned',
                            'original_item': failed_item
                        })
                        self._update_progress(1, progress_callback, False)
                    
                    # Rate limiting between retries
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error during retry: {e}")
                    retry_results['failed'].append({
                        'error': str(e),
                        'original_item': failed_item
                    })
                    self._update_progress(1, progress_callback, False)
            
            # Generate summary
            retry_results['summary'] = self._generate_summary(retry_results)
            
            self._finalize_progress('completed')
            
            # Save results
            self._save_bulk_results(retry_results, f'retry_{operation_type}')
            
            logger.info(f"Retry completed. Success: {len(retry_results['successful'])}, Failed: {len(retry_results['failed'])}")
            
            return retry_results
            
        except Exception as e:
            self._finalize_progress('error')
            logger.error(f"Retry operation failed: {e}")
            raise

    def generate_bulk_operation_report(self, operation_results: Dict, 
                                     operation_name: str) -> Dict:
        """Generate comprehensive report for bulk operation"""
        report = {
            'operation_name': operation_name,
            'timestamp': datetime.now().isoformat(),
            'summary': operation_results.get('summary', {}),
            'successful_items': len(operation_results.get('successful', [])),
            'failed_items': len(operation_results.get('failed', [])),
            'partial_success_items': len(operation_results.get('partial_success', [])),
            'total_processed': operation_results.get('total_processed', 0),
            'detailed_results': {
                'successful': operation_results.get('successful', []),
                'failed': operation_results.get('failed', []),
                'partial_success': operation_results.get('partial_success', [])
            },
            'recommendations': self._generate_operation_recommendations(operation_results),
            'performance_metrics': self._calculate_performance_metrics(operation_results)
        }
        
        return report

    def _generate_operation_recommendations(self, operation_results: Dict) -> List[str]:
        """Generate recommendations based on operation results"""
        recommendations = []
        
        failed_count = len(operation_results.get('failed', []))
        success_rate = operation_results.get('summary', {}).get('success_rate', 0)
        partial_count = len(operation_results.get('partial_success', []))
        
        if success_rate == 100 and failed_count == 0:
            recommendations.append("✅ All operations completed successfully!")
        elif success_rate >= 90:
            recommendations.append("✅ High success rate achieved")
            if failed_count > 0:
                recommendations.append(f"📋 Review {failed_count} failed operations for patterns")
        elif success_rate >= 70:
            recommendations.append("⚠️ Moderate success rate - investigate common failure causes")
            recommendations.append(f"🔄 Consider retrying {failed_count} failed operations")
        else:
            recommendations.append("❌ Low success rate - review configuration and prerequisites")
            recommendations.append("🔍 Check GitHub API limits and network connectivity")
        
        if partial_count > 0:
            recommendations.append(f"📊 Review {partial_count} partially successful operations")
        
        # Time-based recommendations
        duration = operation_results.get('summary', {}).get('duration_seconds', 0)
        total_items = operation_results.get('total_processed', 0)
        if duration > 0 and total_items > 0:
            avg_time_per_item = duration / total_items
            if avg_time_per_item > 5:
                recommendations.append("⚡ Consider increasing batch size or reducing delays for better performance")
        
        return recommendations

    def _calculate_performance_metrics(self, operation_results: Dict) -> Dict:
        """Calculate performance metrics for the operation"""
        metrics = {
            'duration_seconds': 0,
            'items_per_second': 0,
            'average_time_per_item': 0,
            'total_items': 0
        }
        
        # Get duration from progress data if available
        if hasattr(self, 'progress_data') and 'duration_seconds' in self.progress_data:
            metrics['duration_seconds'] = self.progress_data['duration_seconds']
        
        total_items = operation_results.get('total_processed', 0)
        metrics['total_items'] = total_items
        
        if metrics['duration_seconds'] > 0 and total_items > 0:
            metrics['items_per_second'] = total_items / metrics['duration_seconds']
            metrics['average_time_per_item'] = metrics['duration_seconds'] / total_items
        
        return metrics

    # Enhanced progress tracking methods
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
    
    def _update_progress(self, increment: int = 1, callback: Optional[Callable] = None, success: bool = True):
        """Update progress tracking"""
        with self.progress_lock:
            self.progress_data['processed_items'] += increment
            
            if success:
                self.progress_data['successful_items'] += increment
            else:
                self.progress_data['failed_items'] += increment
            
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
        
        # Add duration if available
        if hasattr(self, 'progress_data') and 'duration_seconds' in self.progress_data:
            summary['duration_seconds'] = self.progress_data['duration_seconds']
        
        return summary
    
    def _save_bulk_results(self, results: Dict, operation_name: str):
        """Save bulk operation results"""
        try:
            import os
            
            # Ensure directory exists
            os.makedirs('data/bulk_operations', exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{operation_name}_{timestamp}.json'
            
            save_progress_data(results, filename, 'data/bulk_operations')
            
            # Also save as latest for the operation type
            save_progress_data(results, f'latest_{operation_name}.json', 'data/bulk_operations')
            
        except Exception as e:
            logger.error(f"Error saving bulk results: {e}")
    
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
        
        display = f"""Operation: {progress.get('operation', 'Unknown')}
Status: {progress['status']}
Progress: {progress['processed_items']}/{progress['total_items']} ({progress['progress_percentage']:.1f}%)"""
        
        if show_details:
            display += f"""
Successful: {progress['successful_items']}
Failed: {progress['failed_items']}"""
        
        if progress['start_time']:
            display += f"\nStarted: {progress['start_time']}"
        
        if progress['end_time']:
            display += f"\nCompleted: {progress['end_time']}"
            if 'duration_seconds' in progress:
                display += f"\nDuration: {progress['duration_seconds']:.1f} seconds"
        elif progress['status'] == 'running':
            # Calculate elapsed time for running operations
            try:
                start_time = datetime.fromisoformat(progress['start_time'])
                elapsed = (datetime.now() - start_time).total_seconds()
                display += f"\nElapsed: {elapsed:.1f} seconds"
                
                # Estimate remaining time
                if progress['processed_items'] > 0:
                    avg_time_per_item = elapsed / progress['processed_items']
                    remaining_items = progress['total_items'] - progress['processed_items']
                    estimated_remaining = avg_time_per_item * remaining_items
                    display += f"\nETA: {estimated_remaining:.1f} seconds"
            except Exception:
                pass
        
        return display.strip()
    
    def estimate_operation_time(self, operation_type: str, item_count: int) -> Dict:
        """Estimate time required for bulk operation"""
        # Base time estimates per item (in seconds)
        time_estimates = {
            'bulk_create_student_folders': 3.0,  # Folder creation + setup
            'bulk_create_student_issues': 2.0,   # Issue creation
            'bulk_send_invitations': 1.0,        # Send invitations
            'bulk_update_progress': 0.5,         # Update progress data
            'bulk_generate_reports': 10.0,       # Generate reports
        }
        
        base_time_per_item = time_estimates.get(operation_type, 2.0)
        
        # Calculate total time including batch delays
        batches = (item_count + self.batch_size - 1) // self.batch_size
        batch_delay_time = max(0, (batches - 1) * self.delay_between_batches)
        
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
    
    def cancel_running_operation(self):
        """Cancel the currently running operation"""
        with self.progress_lock:
            if self.progress_data['status'] == 'running':
                self.progress_data['status'] = 'cancelled'
                self.progress_data['end_time'] = datetime.now().isoformat()
                logger.info("Operation cancelled by user request")
                return True
            return False
    
    def get_operation_statistics(self, project_csv_path: str = None) -> Dict:
        """Get statistics about bulk operations and current state"""
        stats = {
            'current_operation': self.get_progress_status(),
            'recent_operations': self.get_bulk_operation_history(limit=5),
            'configuration': {
                'batch_size': self.batch_size,
                'max_workers': self.max_workers,
                'delay_between_batches': self.delay_between_batches
            }
        }
        
        if project_csv_path:
            try:
                students = load_project_data(project_csv_path)
                stats['project_info'] = {
                    'total_students': len(students),
                    'estimated_times': {
                        'folder_creation': self.estimate_operation_time('bulk_create_student_folders', len(students)),
                        'issue_creation': self.estimate_operation_time('bulk_create_student_issues', len(students)),
                        'invitation_sending': self.estimate_operation_time('bulk_send_invitations', len(students) + 1),
                        'progress_update': self.estimate_operation_time('bulk_update_progress', len(students))
                    }
                }
            except Exception as e:
                stats['project_info'] = {'error': str(e)}
        
        return stats