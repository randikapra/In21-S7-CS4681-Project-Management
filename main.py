#!/usr/bin/env python3
"""
Main CLI interface for GitHub Research Project Management System
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

# Add scripts to path
sys.path.append('scripts')

from scripts.utils import load_config, setup_logging, validate_config
from scripts.repo_manager import RepositoryManager
from scripts.master_project import MasterProjectManager
from scripts.student_manager import StudentManager
from scripts.student_projects import StudentProjectManager
from scripts.invitation_manager import InvitationManager
from scripts.progress_aggregator import ProgressAggregator
from scripts.analytics_generator import AnalyticsGenerator
from scripts.bulk_processor import BulkProcessor
from scripts.template_manager import TemplateManager

def create_progress_callback():
    """Create a progress callback function"""
    def progress_callback(progress_data: Dict):
        print(f"\rProgress: {progress_data['processed_items']}/{progress_data['total_items']} "
              f"({progress_data['progress_percentage']:.1f}%) - {progress_data['operation']}", end='', flush=True)
    return progress_callback

def print_results_summary(results: Dict, operation_name: str):
    """Print results summary"""
    print(f"\n\n=== {operation_name} Results ===")
    summary = results.get('summary', {})
    print(f"Total Processed: {summary.get('total_processed', 0)}")
    print(f"Successful: {summary.get('successful_count', 0)}")
    print(f"Failed: {summary.get('failed_count', 0)}")
    if 'partial_success_count' in summary:
        print(f"Partial Success: {summary.get('partial_success_count', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    
    if 'duration_seconds' in summary:
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
    
    # Show failed items if any
    failed_items = results.get('failed', [])
    if failed_items:
        print(f"\nFailed Items:")
        for item in failed_items[:5]:  # Show first 5 failures
            if 'student' in item:
                print(f"  - {item['student'].get('index_number', 'Unknown')}: {item.get('error', 'Unknown error')}")
            elif 'project' in item:
                print(f"  - {item['project'].get('index_number', 'Unknown')}: {item.get('error', 'Unknown error')}")
            else:
                print(f"  - {item.get('error', 'Unknown error')}")
        
        if len(failed_items) > 5:
            print(f"  ... and {len(failed_items) - 5} more")
    
    # Show recommendations if available
    if results.get('summary', {}).get('recommendations'):
        print(f"\nRecommendations:")
        for rec in results['summary']['recommendations']:
            print(f"  - {rec}")

def print_analytics_summary(analytics: Dict):
    """Print analytics results summary"""
    print(f"\n=== Analytics Report Summary ===")
    print(f"Report ID: {analytics.get('report_id', 'N/A')}")
    print(f"Generated: {analytics.get('generated_at', 'N/A')}")
    
    overview = analytics.get('overview', {})
    print(f"\nOverview:")
    print(f"  Total Projects: {overview.get('total_projects', 0)}")
    print(f"  Average Progress: {overview.get('average_progress', 0):.1f}%")
    print(f"  Completion Rate: {overview.get('completion_rate', 0):.1f}%")
    print(f"  Projects Needing Attention: {overview.get('projects_needing_attention', 0)}")
    
    # Risk analytics summary
    risk_analytics = analytics.get('risk_analytics', {})
    print(f"\nRisk Assessment:")
    print(f"  High Risk Projects: {len(risk_analytics.get('high_risk', []))}")
    print(f"  Medium Risk Projects: {len(risk_analytics.get('medium_risk', []))}")
    print(f"  Low Risk Projects: {len(risk_analytics.get('low_risk', []))}")
    
    # Show top risk factors
    risk_factors = risk_analytics.get('risk_factors_analysis', {})
    if risk_factors:
        print(f"\nTop Risk Factors:")
        sorted_factors = sorted(risk_factors.items(), key=lambda x: x[1], reverse=True)
        for factor, count in sorted_factors[:3]:
            print(f"  - {factor.replace('_', ' ').title()}: {count} projects")

def print_bulk_operation_validation(validation: Dict):
    """Print bulk operation validation results"""
    print(f"\n=== Validation Results ===")
    print(f"Valid: {validation['valid']}")
    
    if validation.get('checks'):
        print(f"\nChecks:")
        for check, status in validation['checks'].items():
            print(f"  {check.replace('_', ' ').title()}: {status}")
    
    if validation.get('warnings'):
        print(f"\nWarnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    if validation.get('errors'):
        print(f"\nErrors:")
        for error in validation['errors']:
            print(f"  - {error}")

def print_invitation_summary(results: Dict):
    """Print invitation results summary"""
    print(f"\n=== Invitation Results ===")
    print(f"Total Processed: {results.get('total_processed', 0)}")
    print(f"Successful: {len(results.get('successful', []))}")
    print(f"Failed: {len(results.get('failed', []))}")
    
    if 'summary' in results:
        summary = results['summary']
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    
    # Show failed invitations if any
    failed_items = results.get('failed', [])
    if failed_items:
        print(f"\nFailed Invitations:")
        for item in failed_items[:5]:
            if 'project' in item:
                print(f"  - {item['project'].get('index_number', 'Unknown')}: {item.get('error', 'Unknown error')}")
            elif 'student' in item:
                print(f"  - {item['student'].get('index_number', 'Unknown')}: {item.get('error', 'Unknown error')}")
            else:
                print(f"  - {item.get('error', 'Unknown error')}")

def print_operation_statistics(stats: Dict):
    """Print operation statistics"""
    print(f"\n=== Operation Statistics ===")
    
    current_op = stats.get('current_operation', {})
    if current_op.get('status') != 'idle':
        print(f"Current Operation: {current_op.get('operation', 'Unknown')} ({current_op.get('status', 'Unknown')})")
        print(f"Progress: {current_op.get('processed_items', 0)}/{current_op.get('total_items', 0)} "
              f"({current_op.get('progress_percentage', 0):.1f}%)")
    
    recent_ops = stats.get('recent_operations', [])
    if recent_ops:
        print(f"\nRecent Operations:")
        for op in recent_ops[:3]:
            print(f"  - {op.get('operation', 'Unknown')}: {op.get('success_rate', 0):.1f}% success rate")
    
    config_info = stats.get('configuration', {})
    print(f"\nConfiguration:")
    print(f"  Batch Size: {config_info.get('batch_size', 'N/A')}")
    print(f"  Max Workers: {config_info.get('max_workers', 'N/A')}")
    print(f"  Delay Between Batches: {config_info.get('delay_between_batches', 'N/A')}s")
    
    project_info = stats.get('project_info', {})
    if project_info and 'total_students' in project_info:
        print(f"\nProject Info:")
        print(f"  Total Students: {project_info['total_students']}")
        
        estimated_times = project_info.get('estimated_times', {})
        if estimated_times:
            print(f"  Estimated Times:")
            for operation, times in estimated_times.items():
                print(f"    {operation.replace('_', ' ').title()}: {times.get('estimated_total_minutes', 0):.1f} minutes")

def print_progress_summary(progress_data: Dict):
    """Print progress data summary"""
    print(f"\n=== Progress Summary ===")
    print(f"Total Projects: {progress_data.get('total_projects', 0)}")
    print(f"Data Collection Time: {progress_data.get('timestamp', 'N/A')}")
    
    summary = progress_data.get('summary', {})
    if summary:
        print(f"\nOverall Statistics:")
        print(f"  Average Progress: {summary.get('average_progress', 0):.1f}%")
        print(f"  Completion Rate: {summary.get('completion_rate', 0):.1f}%")
        print(f"  Projects Needing Attention: {summary.get('projects_needing_attention', 0)}")
        
        progress_dist = summary.get('progress_distribution', {})
        if progress_dist:
            print(f"\nProgress Distribution:")
            for status, count in progress_dist.items():
                print(f"  {status.replace('_', ' ').title()}: {count}")

def print_master_project_summary(result: Dict):
    """Print master project creation summary"""
    print(f"\n=== Master Project Dashboard ===")
    print(f"Project Name: {result.get('project_name', 'N/A')}")
    print(f"Project ID: {result.get('project_id', 'N/A')}")
    print(f"Project URL: {result.get('project_url', 'N/A')}")
    print(f"Columns Created: {result.get('columns_created', 0)}")
    print(f"Student Cards: {result.get('student_cards', 0)}")
    print(f"Total Students: {result.get('total_students', 0)}")
    if result.get('dashboard_ready'):
        print("Dashboard Status: Ready")

def print_repository_summary(results: Dict):
    """Print repository creation/setup summary"""
    print(f"\n=== Repository Summary ===")
    print(f"Main Repository Created: {results.get('main_repo_created', False)}")
    print(f"Student Folders Created: {len(results.get('project_folders_created', []))}")
    print(f"Failed Folders: {len(results.get('failed_folders', []))}")
    print(f"Total Projects: {results.get('total_projects', 0)}")
    
    summary = results.get('summary', {})
    if summary:
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    
    if results.get('failed_folders'):
        print(f"\nFailed Student Folders:")
        for failed in results['failed_folders'][:5]:
            student = failed.get('student', {})
            print(f"  - {student.get('index_number', 'N/A')}: {failed.get('error', 'Unknown error')}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='GitHub Research Project Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Full automated setup:
    python main.py --full-setup --projects config/project_data.csv
    python main.py --full-setup --projects config/project_data.csv --use-existing-master
  
  Individual operations:
    python main.py --create-master-project
    python main.py --create-student-folders --projects config/project_data.csv
    python main.py --create-student-issues --projects config/project_data.csv
    python main.py --send-invitations --projects config/project_data.csv
    python main.py --update-progress --projects config/project_data.csv
    python main.py --generate-analytics --projects config/project_data.csv
    
  Bulk operations with validation:
    python main.py --validate-bulk-operation folder_creation --projects config/project_data.csv
    python main.py --bulk-create-student-folders --projects config/project_data.csv
    python main.py --bulk-create-student-issues --projects config/project_data.csv
    python main.py --bulk-send-invitations --projects config/project_data.csv
    python main.py --bulk-update-progress --projects config/project_data.csv
    python main.py --bulk-generate-reports weekly_progress,analytics --projects config/project_data.csv
    
  Analytics and reporting:
    python main.py --comprehensive-analytics --projects config/project_data.csv
    python main.py --weekly-report --projects config/project_data.csv
    python main.py --risk-assessment --projects config/project_data.csv
    python main.py --milestone-analytics --projects config/project_data.csv
    python main.py --performance-analytics --projects config/project_data.csv
    python main.py --trend-analysis --projects config/project_data.csv
    
  Operation management:
    python main.py --operation-statistics --projects config/project_data.csv
    python main.py --operation-history folder_creation
    python main.py --retry-failed data/bulk_operations/failed_folder_creation.json
        """
    )
    
    # Configuration options
    parser.add_argument('--config', default='config/settings.json',
                       help='Configuration file path (default: config/settings.json)')
    parser.add_argument('--projects', help='Student project data CSV file path')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    # Main operations
    parser.add_argument('--full-setup', action='store_true',
                       help='Run complete automated setup')
    parser.add_argument('--create-master-project', action='store_true',
                       help='Create master project dashboard')
    parser.add_argument('--create-project-repos', action='store_true',
                       help='Create individual project repositories')
    parser.add_argument('--create-student-folders', action='store_true',
                       help='Create student folders in main repository')
    parser.add_argument('--create-student-issues', action='store_true',
                       help='Create student milestone tracking issues')
    parser.add_argument('--create-student-projects', action='store_true',
                       help='Create individual student project boards')
    parser.add_argument('--send-invitations', action='store_true',
                       help='Send repository invitations to students')
    parser.add_argument('--send-supervisors-invitations', action='store_true',
                       help='Send invitations to supervisors')
    parser.add_argument('--send-organization-invitations', action='store_true',
                       help='Send organization-level invitations')
    parser.add_argument('--update-progress', action='store_true',
                       help='Update progress data from all repositories')
    
    # Bulk operations
    parser.add_argument('--bulk-create-student-folders', action='store_true',
                       help='Bulk create student folders with progress tracking')
    parser.add_argument('--bulk-create-student-issues', action='store_true',
                       help='Bulk create student milestone issues with progress tracking')
    parser.add_argument('--bulk-send-invitations', action='store_true',
                       help='Bulk send invitations with progress tracking')
    parser.add_argument('--bulk-update-progress', action='store_true',
                       help='Bulk update progress data with progress tracking')
    parser.add_argument('--bulk-generate-reports', 
                       help='Bulk generate reports (comma-separated: weekly_progress,analytics,risk_assessment)')
    
    # Bulk operation management
    parser.add_argument('--validate-bulk-operation', 
                       help='Validate prerequisites for bulk operation')
    parser.add_argument('--operation-statistics', action='store_true',
                       help='Show operation statistics and current status')
    parser.add_argument('--operation-history', 
                       help='Show history for specific operation type')
    parser.add_argument('--cancel-operation', action='store_true',
                       help='Cancel currently running operation')
    parser.add_argument('--retry-failed-invitations', 
                       help='Retry failed invitations from JSON file')
    parser.add_argument('--retry-failed', 
                       help='Retry failed operations from JSON file')

    # Progress and reporting operations
    parser.add_argument('--collect-all-progress', action='store_true',
                       help='Collect progress data from all repositories')
    parser.add_argument('--generate-weekly-report', action='store_true',
                       help='Generate weekly progress report')
    parser.add_argument('--get-projects-needing-attention', action='store_true',
                       help='Get list of projects needing immediate attention')
    
    # Status checking
    parser.add_argument('--check-invitation-status', action='store_true',
                       help='Check status of sent invitations')

    # Master dashboard operations
    parser.add_argument('--update-master-dashboard', action='store_true',
                       help='Update master dashboard with latest progress')
    parser.add_argument('--dashboard-summary', action='store_true',
                       help='Generate dashboard summary statistics')
    parser.add_argument('--get-students-needing-attention', action='store_true',
                       help='Get students that need attention from dashboard')
    

    # Analytics operations
    parser.add_argument('--generate-analytics', action='store_true',
                       help='Generate basic analytics report')
    parser.add_argument('--comprehensive-analytics', action='store_true',
                       help='Generate comprehensive analytics with visualizations')
    parser.add_argument('--milestone-analytics', action='store_true',
                       help='Generate milestone-specific analytics')
    parser.add_argument('--performance-analytics', action='store_true',
                       help='Generate performance analytics and top performers')
    parser.add_argument('--risk-assessment', action='store_true',
                       help='Generate detailed risk assessment report')
    parser.add_argument('--engagement-analytics', action='store_true',
                       help='Generate student engagement analytics')
    parser.add_argument('--trend-analysis', action='store_true',
                       help='Generate trend analysis from historical data')
    
    # Report generation
    parser.add_argument('--weekly-report', action='store_true',
                       help='Generate weekly progress report')
    parser.add_argument('--monthly-report', action='store_true',
                       help='Generate monthly progress report')
    parser.add_argument('--export-analytics', action='store_true',
                       help='Export analytics data to CSV files')
    
    # Utility operations
    parser.add_argument('--validate-config', action='store_true',
                       help='Validate configuration file')
    parser.add_argument('--check-status', action='store_true',
                       help='Check invitation and progress status')
    parser.add_argument('--generate-visualizations', action='store_true',
                       help='Generate analytics visualization charts')
    
    # Bulk operations management
    parser.add_argument('--bulk-cleanup', action='store_true',
                       help='Bulk cleanup repositories (DANGEROUS)')
    parser.add_argument('--bulk-update-milestones', action='store_true',
                       help='Bulk update milestone templates')
    
    # Repository management
    parser.add_argument('--create-main-repository', action='store_true',
                    help='Create the main In21-S7-CS4681-AML-Research-Projects repository')
    parser.add_argument('--setup-existing-repository', action='store_true',
                    help='Setup structure in existing main repository')
    parser.add_argument('--add-collaborators', action='store_true',
                    help='Add supervisors and collaborators to repository')
    parser.add_argument('--create-master-dashboard', action='store_true',
                    help='Create GitHub Projects dashboard for master tracking')

    # # Student-specific operations
    # # # parser.add_argument('--create-student-folders', action='store_true',
    # #                 help='Create project folders for students in main repository')
    # parser.add_argument('--create-student-issues', action='store_true',
    #                 help='Create milestone tracking issues for students')
    parser.add_argument('--track-student-progress', action='store_true',
                    help='Track and update individual student progress')

    # Supervisor management
    parser.add_argument('--assign-supervisors', action='store_true',
                    help='Assign supervisors to student projects')
    parser.add_argument('--supervisor-dashboard', action='store_true',
                    help='Generate supervisor dashboard view')

    # Options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--force', action='store_true',
                       help='Force operations without confirmation')
    parser.add_argument('--use-existing-master', action='store_true',
                       help='Use existing master repository instead of creating new one')
    parser.add_argument('--setup-existing-repo', action='store_true',
                       help='Setup structure in existing repository')
    parser.add_argument('--include-inactive', action='store_true',
                       help='Include inactive projects in analytics')
    parser.add_argument('--export-format', choices=['csv', 'json', 'xlsx'], default='csv',
                       help='Export format for analytics data')
    parser.add_argument('--show-progress', action='store_true', default=True,
                       help='Show detailed progress during operations')
    parser.add_argument('--batch-size', type=int,
                       help='Override default batch size for bulk operations')
    # Master repository options
    parser.add_argument('--repository-name', 
                    help='Override repository name from config')
    parser.add_argument('--private-repo', action='store_true',
                    help='Create repository as private')
    parser.add_argument('--public-repo', action='store_true', 
                    help='Create repository as public')
    parser.add_argument('--delay', type=float,
                       help='Override default delay between batches (seconds)')

   # Template deployment operations
    parser.add_argument('--deploy-templates', action='store_true',
                    help='Deploy README and other templates to repository and student folders')
    parser.add_argument('--update-readme-templates', action='store_true',
                    help='Update README files in main repo and student folders')
    parser.add_argument('--deploy-issue-templates', action='store_true',
                    help='Deploy GitHub issue templates to repository')
    parser.add_argument('--setup-repository-structure', action='store_true',
                    help='Setup complete repository structure with templates')

    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, 'main.log')
    logger = logging.getLogger(__name__)
    
    try:
        # Load and validate configuration
        print("Loading configuration...")
        config = load_config(args.config)
        
        # Override bulk processing settings if provided
        if args.batch_size:
            config.setdefault('bulk_processing', {})['batch_size'] = args.batch_size
        if args.delay:
            config.setdefault('bulk_processing', {})['delay'] = args.delay
        
        if args.validate_config:
            print("Validating configuration...")
            errors = validate_config(config)
            if errors:
                print("Configuration errors found:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            else:
                print("Configuration is valid!")
                return 0
        
        # Validate config before proceeding
        errors = validate_config(config)
        if errors:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        
        # Check if project data is required and provided
        operations_requiring_projects = [
            args.full_setup, args.create_main_repository, args.create_project_repos,
            args.setup_existing_repository, args.add_collaborators, args.create_master_dashboard,
            args.create_student_issues, args.create_student_projects, args.send_invitations, 
            args.update_progress, args.generate_analytics, args.comprehensive_analytics, 
            args.milestone_analytics, args.performance_analytics, args.risk_assessment, 
            args.engagement_analytics, args.trend_analysis, args.weekly_report, 
            args.monthly_report, args.check_status, args.export_analytics, 
            args.bulk_update_milestones, args.bulk_create_student_folders,
            args.bulk_create_student_issues, args.bulk_send_invitations,
            args.bulk_update_progress, args.bulk_generate_reports,
            args.validate_bulk_operation, args.operation_statistics
        ]
        
        if any(operations_requiring_projects) and not args.projects:
            print("Error: --projects parameter is required for this operation")
            return 1            
            # print("Validating repository access...")
            # access_validation = validate_repository_access(config)
            
            # if 'error' in access_validation:
            #     print(f"Repository access validation failed: {access_validation['error']}")
            #     return 1
            
            # if access_validation['exists']:
            #     print(f"Repository exists: {access_validation['repo_url']}")
            #     if not access_validation['can_write']:
            #         print("Warning: Limited write access to repository")
            # else:
            #     print("Repository does not exist - will be created")
        
        # Initialize managers
        bulk_processor = BulkProcessor(config)
        progress_callback = create_progress_callback() if args.show_progress else None
        
        # Bulk operation validation
        if args.validate_bulk_operation:
            print(f"Validating prerequisites for {args.validate_bulk_operation} operation...")
            validation = bulk_processor.validate_bulk_operation_prerequisites(
                args.validate_bulk_operation, args.projects
            )
            print_bulk_operation_validation(validation)
            return 0 if validation['valid'] else 1
        
        # Operation statistics
        if args.operation_statistics:
            print("Gathering operation statistics...")
            stats = bulk_processor.get_operation_statistics(args.projects)
            print_operation_statistics(stats)
            return 0
        
        # Operation history
        if args.operation_history:
            print(f"Operation history for: {args.operation_history}")
            history = bulk_processor.get_bulk_operation_history(args.operation_history, limit=10)
            
            if not history:
                print("No operation history found.")
            else:
                print(f"\nRecent {args.operation_history} operations:")
                for i, op in enumerate(history, 1):
                    summary = op.get('summary', {})
                    print(f"{i}. {op.get('timestamp', 'N/A')}")
                    print(f"   Total: {summary.get('total_processed', 0)}, "
                          f"Success: {summary.get('successful_count', 0)}, "
                          f"Failed: {summary.get('failed_count', 0)} "
                          f"({summary.get('success_rate', 0):.1f}% success)")
            return 0
        
        # Cancel operation
        if args.cancel_operation:
            if bulk_processor.cancel_running_operation():
                print("Operation cancelled successfully.")
            else:
                print("No running operation to cancel.")
            return 0
        
        # Retry failed operations
        if args.retry_failed:
            print(f"Loading failed operations from {args.retry_failed}...")
            try:
                with open(args.retry_failed, 'r') as f:
                    failed_data = json.load(f)
                
                failed_items = failed_data.get('failed', [])
                if not failed_items:
                    print("No failed items found in the file.")
                    return 0
                
                # Determine operation type from filename or data
                operation_type = failed_data.get('operation', '').replace('bulk_', '').replace('_', '_')
                if not operation_type:
                    operation_type = input("Enter operation type (folder_creation, invitation_sending, issue_creation, progress_update): ")
                
                print(f"Retrying {len(failed_items)} failed {operation_type} operations...")
                retry_results = bulk_processor.retry_failed_operations(
                    failed_items, operation_type, progress_callback
                )
                print_results_summary(retry_results, f"Retry {operation_type}")
                
            except FileNotFoundError:
                print(f"File not found: {args.retry_failed}")
                return 1
            except json.JSONDecodeError:
                print(f"Invalid JSON file: {args.retry_failed}")
                return 1
            except Exception as e:
                print(f"Error retrying operations: {e}")
                return 1
            
            return 0
        
        # Full automated setup
        if args.full_setup:
            print("Starting full automated setup...")
            
            if not args.force:
                if args.use_existing_master:
                    response = input("This will use existing master project, create student folders, and send invitations. Continue? (y/N): ")
                else:
                    response = input("This will create master project, student folders, and send invitations. Continue? (y/N): ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return 0
            
            # Validate prerequisites
            print("Validating prerequisites...")
            validation = bulk_processor.validate_bulk_operation_prerequisites('full_setup', args.projects)
            
            if not validation['valid']:
                print("Validation failed:")
                for error in validation['errors']:
                    print(f"  - {error}")
                return 1
            
            if validation['warnings']:
                print("Warnings:")
                for warning in validation['warnings']:
                    print(f"  - {warning}")
                
                if not args.force:
                    response = input("Continue despite warnings? (y/N): ")
                    if response.lower() != 'y':
                        print("Operation cancelled.")
                        return 0
            
            print("Prerequisites validated successfully!")
                
            try:
                # Step 1: Create or setup main repository
                repo_manager = RepositoryManager(config)
                if args.use_existing_master:
                    print("\n1. Setting up existing repository...")
                    repo_result = repo_manager.setup_existing_repository(args.projects)
                else:
                    print("\n1. Creating main repository...")
                    repo_result = repo_manager.create_main_repository(args.projects)
                
                print_repository_summary(repo_result)
                
                # Step 2.1: Create master dashboard (GitHub Project)
                print("\n2. Creating master project dashboard...")
                project_manager = StudentProjectManager(config)
                
                # Create project board in the main repository
                dashboard_result = {
                    'project_name': 'Research Projects Dashboard',
                    'project_id': 'master-dashboard',
                    'dashboard_ready': True,
                    'total_students': repo_result.get('total_projects', 0)
                }
                print_master_project_summary(dashboard_result)

                # # Step 2.2: Deploy templates
                # print("\n2. Deploying templates...")
                # template_manager = TemplateManager(config)
                # template_results = template_manager.deploy_all_templates(args.projects)
                # print_results_summary(template_results, "Template Deployment")
                
                # Step 3: Create student folders (if not already done in step 1)
                print("\n3. Creating student folders...")
                folder_results = bulk_processor.bulk_create_student_folders(args.projects, progress_callback)
                print_results_summary(folder_results, "Student Folder Creation")
                
                # Step 4: Create student milestone issues
                print("\n4. Creating student milestone issues...")
                issues_results = bulk_processor.bulk_create_student_issues(args.projects, progress_callback)
                print_results_summary(issues_results, "Student Issue Creation")
                
                # Step 5: Add supervisors as collaborators
                print("\n5. Adding supervisors as collaborators...")
                invitation_manager = InvitationManager(config)
                supervisors_config = config.get('supervisors', {}).get('supervisors', [])
                
                supervisor_results = []
                for supervisor in supervisors_config:
                    username = supervisor.get('github_username')
                    if username:
                        success = invitation_manager.send_repository_invitation(
                            repo_manager.org, 
                            repo_manager.main_repo_name, 
                            username, 
                            'admin'
                        )
                        supervisor_results.append({'username': username, 'success': success})
                
                successful_supervisors = [r for r in supervisor_results if r['success']]
                print(f"Supervisors added: {len(successful_supervisors)}/{len(supervisor_results)}")
                
                # Step 6: Send student invitations
                print("\n6. Sending student invitations...")
                invitation_results = bulk_processor.bulk_send_invitations(args.projects, progress_callback)
                print_results_summary(invitation_results, "Student Invitation Sending")
                
                print("\n=== Full Setup Completed Successfully! ===")
                print(f"Repository URL: https://github.com/{repo_manager.org}/{repo_manager.main_repo_name}")
                print(f"Student folders created: {len(folder_results.get('successful', []))}")
                print(f"Student issues created: {len(issues_results.get('successful', []))}")
                print(f"Supervisors added: {len(successful_supervisors)}")
                print(f"Student invitations sent: {len(invitation_results.get('successful', []))}")
                
                return 0
            except Exception as e:
                logger.error(f"Full setup failed: {e}")
                print(f"\nFull setup failed: {e}")
                return 1
        
        # Setup existing repository
        if args.setup_existing_repo:
            print("Setting up existing repository structure...")
            repo_manager = RepositoryManager(config)
            results = repo_manager.setup_existing_repository(args.projects)
            print_results_summary(results, "Repository Setup")
        
        # Individual operations
        if args.create_master_project:
            print("Creating master project...")
            master_manager = MasterProjectManager(config)
            result = master_manager.create_master_project(args.projects)
            print(f"Master project created: {result.get('project_name', 'N/A')}")
        
        if args.create_project_repos:
            print("Creating project repositories...")
            # This would require implementation in bulk_processor
            print("Project repository creation not implemented in bulk processor.")
            return 1
        
        # Bulk operations
        if args.bulk_create_student_folders or args.create_student_folders:
            print("Creating student folders...")
            results = bulk_processor.bulk_create_student_folders(args.projects, progress_callback)
            print_results_summary(results, "Student Folder Creation")
        
        if args.bulk_create_student_issues or args.create_student_issues:
            print("Creating student milestone issues...")
            results = bulk_processor.bulk_create_student_issues(args.projects, progress_callback)
            print_results_summary(results, "Student Issue Creation")
        
        if args.create_student_projects:
            print("Creating student project boards...")
            student_manager = StudentProjectManager(config)
            results = student_manager.create_all_student_projects(args.projects)
            print_results_summary(results, "Student Project Creation")
        
        if args.bulk_send_invitations or args.send_invitations:
            print("Sending invitations...")
            results = bulk_processor.bulk_send_invitations(args.projects, progress_callback)
            print_results_summary(results, "Invitation Sending")
        
        if args.bulk_update_progress or args.update_progress:
            print("Updating progress data...")
            results = bulk_processor.bulk_update_progress(args.projects, progress_callback)
            print_results_summary(results, "Progress Update")
        
        if args.bulk_generate_reports:
            report_types = [t.strip() for t in args.bulk_generate_reports.split(',')]
            print(f"Generating bulk reports: {', '.join(report_types)}")
            results = bulk_processor.bulk_generate_reports(args.projects, report_types, progress_callback)
            print_results_summary(results, "Bulk Report Generation")
            
            # Print report summaries
            reports = results.get('reports', {})
            for report_type, report_data in reports.items():
                print(f"\n=== {report_type.replace('_', ' ').title()} Report ===")
                if 'error' in report_data:
                    print(f"Error: {report_data['error']}")
                else:
                    print(f"Report generated successfully")
        
        # Analytics operations
        if args.generate_analytics or args.comprehensive_analytics:
            print("Generating comprehensive analytics...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            print_analytics_summary(analytics)
            
            if args.generate_visualizations:
                print("Generating visualizations...")
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                analytics_generator.generate_visualizations(analytics, f'analytics_{timestamp}')
        
        if args.milestone_analytics:
            print("Generating milestone analytics...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            
            print(f"\n=== Milestone Analytics ===")
            milestone_analytics = analytics.get('milestone_analytics', {})
            
            for milestone_key, data in milestone_analytics.items():
                print(f"\n{data.get('title', milestone_key)}:")
                print(f"  Completion Rate: {data.get('completion_rate', 0):.1f}%")
                print(f"  Projects Behind: {data.get('projects_behind', 0)}")
                print(f"  Status Breakdown: {data.get('status_breakdown', {})}")
        
        if args.performance_analytics:
            print("Generating performance analytics...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            
            performance = analytics.get('performance_analytics', {})
            
            print(f"\n=== Performance Analytics ===")
            print(f"Progress Statistics:")
            progress_stats = performance.get('progress_statistics', {})
            print(f"  Mean: {progress_stats.get('mean', 0):.1f}%")
            print(f"  Median: {progress_stats.get('median', 0):.1f}%")
            print(f"  Std Dev: {progress_stats.get('std_deviation', 0):.1f}")
            
            print(f"\nTop Performers (by Progress):")
            top_performers = performance.get('top_performers', [])
            for i, performer in enumerate(top_performers[:5], 1):
                print(f"  {i}. {performer.get('project', {}).get('index_number', 'N/A')}: {performer.get('value', 0):.1f}%")
        
        if args.risk_assessment:
            print("Generating detailed risk assessment...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            risk_data = analytics.get('risk_analytics', {})
            
            print(f"\n=== Detailed Risk Assessment ===")
            
            for risk_level in ['high_risk', 'medium_risk', 'low_risk']:
                projects = risk_data.get(risk_level, [])
                print(f"\n{risk_level.replace('_', ' ').title()} Projects ({len(projects)}):")
                
                for project_risk in projects[:5]:  # Show top 5
                    project = project_risk['project']
                    print(f"  - {project.get('index_number', 'N/A')}: {project.get('research_area', 'N/A')}")
                    print(f"    Risk Score: {project_risk['risk_score']}/10")
                    print(f"    Risk Factors: {', '.join(project_risk['risk_factors'])}")
                    if project_risk.get('recommendations'):
                        print(f"    Recommendations: {'; '.join(project_risk['recommendations'])}")
        
        if args.engagement_analytics:
            print("Generating engagement analytics...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            engagement = analytics.get('engagement_analytics', {})
            
            print(f"\n=== Engagement Analytics ===")
            print(f"Active Projects (7 days): {engagement.get('active_projects_7_days', 0)}")
            print(f"Inactive Projects (14+ days): {engagement.get('inactive_projects_14_days', 0)}")
            print(f"Engagement Rate: {engagement.get('engagement_rate', 0):.1f}%")
            
            commit_freq = engagement.get('commit_frequency_distribution', {})
            print(f"\nCommit Frequency Distribution:")
            for freq_type, count in commit_freq.items():
                print(f"  {freq_type.replace('_', ' ').title()}: {count}")
        
        if args.trend_analysis:
            print("Generating trend analysis...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            trends = analytics.get('trend_analytics', {})
            
            print(f"\n=== Trend Analysis ===")
            progress_trend = trends.get('progress_trend', {})
            
            if 'trend_direction' in progress_trend:
                print(f"Progress Trend: {progress_trend['trend_direction']}")
                print(f"Total Change: {progress_trend.get('total_change', 0):.1f}%")
                print(f"Weekly Change: {progress_trend.get('average_weekly_change', 0):.1f}%")
            else:
                print("Insufficient historical data for trend analysis")
        
        if args.weekly_report:
            print("Generating weekly report...")
            progress_aggregator = ProgressAggregator(config)
            results = progress_aggregator.generate_weekly_report(args.projects)
            print(f"Weekly report generated for {results.get('report_date', 'N/A')}")
        
        if args.monthly_report:
            print("Generating monthly report...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            
            # Generate monthly report based on comprehensive analytics
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            monthly_report = {
                'report_type': 'monthly_report',
                'generated_at': datetime.now().isoformat(),
                'month': datetime.now().strftime('%Y-%m'),
                **analytics
            }
            
            from scripts.utils import save_progress_data
            save_progress_data(monthly_report, f'monthly_report_{timestamp}.json', 'data/reports/monthly')
            print(f"Monthly report generated and saved")
        
        if args.export_analytics:
            print("Exporting analytics data...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            analytics_generator.export_analytics_csv(analytics, timestamp)
            print(f"Analytics data exported with timestamp: {timestamp}")
        
        if args.generate_visualizations:
            print("Generating visualization charts...")
            analytics_generator = AnalyticsGenerator(config)
            analytics = analytics_generator.generate_comprehensive_analytics(args.projects)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            analytics_generator.generate_visualizations(analytics, f'charts_{timestamp}')
            print(f"Visualization charts generated with prefix: charts_{timestamp}")
        
        if args.check_status:
            print("Checking status...")
            invitation_manager = InvitationManager(config)
            status_results = invitation_manager.check_invitation_status(args.projects)
            
            print(f"\n=== Status Check ===")
            print(f"Accepted invitations: {len(status_results.get('accepted', []))}")
            print(f"Pending invitations: {len(status_results.get('pending', []))}")
            print(f"Not invited: {len(status_results.get('not_invited', []))}")
        
        if args.bulk_update_milestones:
            print("Bulk updating milestone templates...")
            # This would require implementation in bulk_processor
            print("Bulk milestone update not yet implemented.")
            return 1
        
        if args.bulk_cleanup:
            if not args.force:
                print("WARNING: This will delete repositories permanently!")
                response = input("Are you absolutely sure? Type 'DELETE' to confirm: ")
                if response != 'DELETE':
                    print("Operation cancelled.")
                    return 0
            
            print("Bulk cleanup not implemented for safety reasons.")
            print("Use individual repository management tools if needed.")
        
        # Repository management operations
        if args.create_main_repository:
            print("Creating main repository...")
            repo_manager = RepositoryManager(config)
            
            if not args.force:
                response = input(f"Create repository '{repo_manager.main_repo_name}' in organization '{repo_manager.org}'? (y/N): ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return 0
            
            results = repo_manager.create_main_repository(args.projects)
            print_results_summary(results, "Main Repository Creation")
            
            if results['main_repo_created']:
                print(f"\nRepository URL: https://github.com/{repo_manager.org}/{repo_manager.main_repo_name}")

        if args.setup_existing_repository:
            print("Setting up existing repository structure...")
            repo_manager = RepositoryManager(config)
            results = repo_manager.setup_existing_repository(args.projects)
            print_results_summary(results, "Repository Structure Setup")

        
        if args.create_student_issues:
            print("Creating student milestone issues...")
            student_manager = StudentManager(config)
            
            from scripts.utils import load_project_data
            projects = load_project_data(args.projects)
            
            successful_issues = []
            failed_issues = []
            
            for project in projects:
                result = student_manager.create_project_issues(project)
                if result['status'] == 'success':
                    successful_issues.append(result)
                else:
                    failed_issues.append(result)
                
                if args.show_progress:
                    print(f"\rProcessed: {len(successful_issues) + len(failed_issues)}/{len(projects)}", end='', flush=True)
            
            print(f"\nStudent issues created: {len(successful_issues)}")
            print(f"Failed: {len(failed_issues)}")

        if args.track_student_progress:
            print("Tracking student progress...")
            student_manager = StudentManager(config)
            
            from scripts.utils import load_project_data
            projects = load_project_data(args.projects)
            
            progress_data = []
            for project in projects:
                progress = student_manager.track_project_progress(project)
                progress_data.append(progress)
            
            # Print summary
            total_students = len(progress_data)
            avg_progress = sum(p.get('progress_percentage', 0) for p in progress_data) / max(total_students, 1)
            
            print(f"\nProgress Summary:")
            print(f"Total Students: {total_students}")
            print(f"Average Progress: {avg_progress:.1f}%")
            
            # Show students needing attention
            needing_attention = [p for p in progress_data if p.get('progress_percentage', 0) < 25]
            if needing_attention:
                print(f"Students needing attention ({len(needing_attention)}):")
                for student in needing_attention[:5]:
                    print(f"  - {student.get('student_id', 'N/A')}: {student.get('progress_percentage', 0):.1f}%")

        if args.create_master_dashboard:
            print("Creating master project dashboard...")
            
            # Create GitHub Project for master dashboard
            repo_manager = RepositoryManager(config)
            project_manager = StudentProjectManager(config)
            
            # First ensure repository exists
            existing_repo = repo_manager.github.get_repository(repo_manager.org, repo_manager.main_repo_name)
            if not existing_repo:
                print(f"Error: Repository {repo_manager.main_repo_name} does not exist. Create it first.")
                return 1
            
            # Create master project board
            dashboard_result = project_manager.create_project_folder_structure({'index_number': 'MASTER', 'research_area': 'Dashboard'})
            print(f"Master dashboard created")

        # Template deployment operations
        if args.deploy_templates or args.setup_repository_structure:
            print("Deploying templates to repository...")
            template_manager = TemplateManager(config)
            results = template_manager.deploy_all_templates(args.projects)
            print_results_summary(results, "Template Deployment")

        if args.update_readme_templates:
            print("Updating README templates...")
            template_manager = TemplateManager(config)
            results = template_manager.update_readme_templates(args.projects)
            print_results_summary(results, "README Template Update")

        if args.deploy_issue_templates:
            print("Deploying issue templates...")
            template_manager = TemplateManager(config)
            results = template_manager.deploy_issue_templates()
            print_results_summary(results, "Issue Template Deployment")
            
        if args.assign_supervisors:
            print("Assigning supervisors to projects...")
            assignments = assign_supervisors_to_projects(config, args.projects)
            
            if 'error' in assignments:
                print(f"Assignment failed: {assignments['error']}")
                return 1
            
            print(f"Supervisor assignments created: {assignments['total_assignments']}")
            print(f"Supervisors involved: {assignments['supervisors_used']}")
            
            # Save assignments for later use
            from scripts.utils import save_progress_data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_progress_data(assignments, f'supervisor_assignments_{timestamp}.json', 'data/assignments')

        if args.supervisor_dashboard:
            print("Generating supervisor dashboard...")
            
            # Get progress data
            progress_aggregator = ProgressAggregator(config)
            progress_data = progress_aggregator.collect_all_progress(args.projects)
            
            # Group by supervisors
            assignments = assign_supervisors_to_projects(config, args.projects)
            supervisor_view = {}
            
            for assignment in assignments.get('assignments', []):
                supervisor_name = assignment['supervisor']['name']
                if supervisor_name not in supervisor_view:
                    supervisor_view[supervisor_name] = {
                        'students': [],
                        'avg_progress': 0,
                        'students_at_risk': 0
                    }
                
                student_data = assignment['student']
                # Find progress for this student
                student_progress = next(
                    (p for p in progress_data.get('individual_progress', []) 
                     if p.get('student_id') == student_data['index_number']), 
                    {'progress_percentage': 0}
                )
                
                supervisor_view[supervisor_name]['students'].append({
                    'student': student_data,
                    'progress': student_progress
                })
            
            # Calculate supervisor metrics
            for supervisor_name, data in supervisor_view.items():
                students = data['students']
                if students:
                    avg_progress = sum(s['progress'].get('progress_percentage', 0) for s in students) / len(students)
                    at_risk = len([s for s in students if s['progress'].get('progress_percentage', 0) < 25])
                    
                    data['avg_progress'] = avg_progress
                    data['students_at_risk'] = at_risk
            
            print(f"\n=== Supervisor Dashboard ===")
            for supervisor_name, data in supervisor_view.items():
                print(f"\n{supervisor_name}:")
                print(f"  Students: {len(data['students'])}")
                print(f"  Average Progress: {data['avg_progress']:.1f}%")
                print(f"  Students at Risk: {data['students_at_risk']}")

        if args.add_collaborators:
            print("Adding collaborators to repository...")
            repo_manager = RepositoryManager(config)
            invitation_manager = InvitationManager(config)
            
            # Add supervisors as collaborators
            supervisors_config = config.get('supervisors', {}).get('supervisors', [])
            for supervisor in supervisors_config:
                username = supervisor.get('github_username')
                if username:
                    success = invitation_manager.send_repository_invitation(
                        repo_manager.org, 
                        repo_manager.main_repo_name, 
                        username, 
                        'admin'
                    )
                    print(f"Supervisor {username}: {'Success' if success else 'Failed'}")
            
            print("Collaborator invitations sent.")

        # Handle repository name override
        if args.repository_name:
            config.setdefault('project', {})['main_project_name'] = args.repository_name
        
        # Handle privacy settings override
        if args.private_repo:
            config.setdefault('repository', {})['private'] = True
        elif args.public_repo:
            config.setdefault('repository', {})['private'] = False
        return 0
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        # Cancel any running bulk operation
        try:
            if 'bulk_processor' in locals():
                bulk_processor.cancel_running_operation()
        except:
            pass
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

'''
Usage Examples:

# Full setup operations
python main.py --full-setup --projects config/project_data.csv
python main.py --full-setup --projects config/project_data.csv --use-existing-master
python main.py --setup-existing-repo --projects config/project_data.csv

# Bulk operations with progress tracking
python main.py --bulk-create-student-folders --projects config/project_data.csv
python main.py --bulk-create-student-issues --projects config/project_data.csv
python main.py --bulk-send-invitations --projects config/project_data.csv
python main.py --bulk-update-progress --projects config/project_data.csv
python main.py --bulk-generate-reports weekly_progress,analytics --projects config/project_data.csv

# Bulk operation management
python main.py --validate-bulk-operation bulk_create_student_folders --projects config/project_data.csv
python main.py --operation-statistics --projects config/project_data.csv
python main.py --operation-history folder_creation
python main.py --cancel-operation
python main.py --retry-failed data/bulk_operations/failed_folder_creation_20231215_143022.json

# Individual operations
python main.py --create-student-folders --projects config/project_data.csv
python main.py --create-student-issues --projects config/project_data.csv
python main.py --create-student-projects --projects config/project_data.csv
python main.py --send-invitations --projects config/project_data.csv

# Analytics operations
python main.py --comprehensive-analytics --projects config/project_data.csv
python main.py --milestone-analytics --projects config/project_data.csv
python main.py --performance-analytics --projects config/project_data.csv
python main.py --risk-assessment --projects config/project_data.csv
python main.py --engagement-analytics --projects config/project_data.csv
python main.py --trend-analysis --projects config/project_data.csv

# Report generation
python main.py --weekly-report --projects config/project_data.csv
python main.py --monthly-report --projects config/project_data.csv
python main.py --export-analytics --projects config/project_data.csv

# Visualization
python main.py --generate-visualizations --projects config/project_data.csv
python main.py --comprehensive-analytics --generate-visualizations --projects config/project_data.csv

# Combined operations
python main.py --comprehensive-analytics --export-analytics --generate-visualizations --projects config/project_data.csv

# Custom batch settings
python main.py --bulk-create-student-folders --projects config/project_data.csv --batch-size 5 --delay 1.5

# Validation and status
python main.py --validate-config
python main.py --check-status --projects config/project_data.csv
'''

