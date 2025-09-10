"""
Utility functions for the GitHub project management system
"""

import json
import csv
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

# Add this function right after the existing imports at the top of utils.py

def extract_github_username(github_value: str) -> str:
    """Extract GitHub username from URL or return as-is if already a username"""
    import re
    
    if not github_value:
        return ""
    
    # Clean the input
    github_value = github_value.strip()
    
    # If it's already just a username (no URL), return it
    if not github_value.startswith(('http://', 'https://', 'github.com')):
        return github_value
    
    # Extract username from GitHub URL patterns
    patterns = [
        r'https://github\.com/([^/?#\s]+)',
        r'http://github\.com/([^/?#\s]+)',
        r'github\.com/([^/?#\s]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, github_value, re.IGNORECASE)
        if match:
            username = match.group(1).strip()
            # Remove any trailing slashes or special characters
            username = username.rstrip('/')
            return username
    
    # If no pattern matches, return the original value cleaned
    return github_value


def load_config(config_path: str = 'config/settings.json') -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Load environment variables if .env file exists
        env_path = os.path.join(os.path.dirname(config_path), '.env')
        if os.path.exists(env_path):
            config = load_env_variables(config, env_path)
        
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise

def load_env_variables(config: Dict, env_path: str) -> Dict:
    """Load environment variables from .env file"""
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Update GitHub token if provided in .env
                    if key.strip() == 'GITHUB_TOKEN':
                        config['github']['token'] = value.strip().strip('"\'')
        
        return config
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")
        return config

def assign_supervisors_to_projects(config: Dict, projects_file: str) -> Dict:
    """Assign supervisors to student projects based on research areas"""
    try:
        from scripts.utils import load_project_data
        projects = load_project_data(projects_file)
        supervisors_config = config.get('supervisors', {}).get('supervisors', [])
        
        if not supervisors_config:
            return {'error': 'No supervisors configured'}
        
        assignments = []
        
        # Simple round-robin assignment (can be enhanced with research area matching)
        for i, project in enumerate(projects):
            supervisor = supervisors_config[i % len(supervisors_config)]
            assignments.append({
                'student': project,
                'supervisor': supervisor,
                'assignment_method': 'round_robin'
            })
        
        return {
            'assignments': assignments,
            'total_assignments': len(assignments),
            'supervisors_used': len(set(a['supervisor']['github_username'] for a in assignments))
        }
        
    except Exception as e:
        return {'error': str(e)}

def validate_repository_access(config: Dict) -> Dict:
    """Validate access to the main repository"""
    try:
        repo_manager = RepositoryManager(config)
        existing_repo = repo_manager.github.get_repository(repo_manager.org, repo_manager.main_repo_name)
        
        if existing_repo:
            # Check permissions
            permissions = existing_repo.get('permissions', {})
            return {
                'exists': True,
                'can_read': permissions.get('pull', False),
                'can_write': permissions.get('push', False),
                'can_admin': permissions.get('admin', False),
                'repo_url': existing_repo.get('html_url', '')
            }
        else:
            return {
                'exists': False,
                'can_create': True  # Assume we can create if we have token
            }
            
    except Exception as e:
        return {'error': str(e), 'exists': False}

# def load_project_data(csv_path: str) -> List[Dict]:
#     """Load project data from CSV file"""
#     projects = []
    
#     try:
#         with open(csv_path, 'r', encoding='utf-8') as f:
#             reader = csv.DictReader(f)
            
#             for row in reader:
#                 # Map CSV column names to expected field names
#                 # Adjust these mappings based on your actual CSV column names
#                 project = {
#                     'index_number': row.get('project_ID', '').strip(),
#                     'name': row.get('project_Name', '').strip(), 
#                     'research_area': row.get('Research_Area', '').strip(),
#                     'email': row.get('Mail', '').strip(),
#                     'github_username': extract_github_username(row.get('GitHub_User_Name', '').strip())
#                 }
                
#                 # Validate required fields
#                 if not project['index_number'] or not project['research_area']:
#                     logger.warning(f"Skipping invalid project record: {row}")
#                     continue
                
#                 # Additional validation for GitHub username
#                 if not project['github_username']:
#                     logger.warning(f"No GitHub username for project {project['index_number']}")
#                     # You can choose to skip or continue without GitHub username
#                     # For now, we'll continue but log the warning
                
#                 # Clean research area for folder naming
#                 project['research_area_clean'] = clean_folder_name(project['research_area'])
                
#                 projects.append(project)
        
#         logger.info(f"Loaded {len(projects)} projects from {csv_path}")
#         return projects
        
#     except FileNotFoundError:
#         logger.error(f"project data file not found: {csv_path}")
#         raise
#     except Exception as e:
#         logger.error(f"Error loading project data: {e}")
#         raise

def load_project_data(csv_path: str) -> List[Dict]:
    """Load project data from CSV file"""
    projects = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Map CSV column names to expected field names
                # Based on your CSV structure: Student_Name,Student_ID,Research_Area,GitHub_User_Name,Mail
                # In the project dictionary, ensure these fields exist:
                project = {
                    'index_number': row.get('Student_ID', '').strip(),
                    'Student_ID': row.get('Student_ID', '').strip(),  # Keep original for backward compatibility
                    'student_name': row.get('Student_Name', '').strip(),
                    'Student_Name': row.get('Student_Name', '').strip(),  # Keep original
                    'research_area': row.get('Research_Area', '').strip(),
                    'email': row.get('Mail', '').strip(),
                    'github_username': extract_github_username(row.get('GitHub_User_Name', '').strip()),
                    'GitHub_User_Name': row.get('GitHub_User_Name', '').strip()  # Keep original
                }
                
                # Validate required fields
                if not project['index_number'] or not project['research_area']:
                    logger.warning(f"Skipping invalid project record: {row}")
                    continue
                
                # Additional validation for GitHub username
                if not project['github_username']:
                    logger.warning(f"No GitHub username for project {project['index_number']}")
                    # You can choose to skip or continue without GitHub username
                    # For now, we'll continue but log the warning
                
                # Clean research area for folder naming
                project['research_area_clean'] = clean_folder_name(project['research_area'])
                
                projects.append(project)
        
        logger.info(f"Loaded {len(projects)} projects from {csv_path}")
        return projects
        
    except FileNotFoundError:
        logger.error(f"Project data file not found: {csv_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading project data: {e}")
        raise

def load_supervisor_data(config: Dict) -> List[Dict]:
    """Load supervisor data from configuration"""
    try:
        supervisors = []
        
        # Load from supervisors.json if exists
        supervisors_path = 'config/supervisors.json'
        if os.path.exists(supervisors_path):
            with open(supervisors_path, 'r', encoding='utf-8') as f:
                supervisor_config = json.load(f)
                supervisors.extend(supervisor_config.get('supervisors', []))
                
                # Add module coordinator
                if 'module_coordinator' in supervisor_config:
                    coordinator = supervisor_config['module_coordinator']
                    coordinator['role'] = 'module_coordinator'
                    supervisors.append(coordinator)
        
        # Fallback to config file
        if not supervisors and 'supervisors' in config:
            supervisors = config['supervisors']
        
        return supervisors
        
    except Exception as e:
        logger.error(f"Error loading supervisor data: {e}")
        return []

def clean_folder_name(name: str) -> str:
    """Clean name for folder naming"""
    # Replace spaces and special characters with hyphens for better readability
    cleaned = name.replace(' ', '-').replace('_', '-')
    # Remove multiple hyphens
    import re
    cleaned = re.sub(r'-+', '-', cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    # Ensure it's not empty
    if not cleaned:
        cleaned = 'project'
    return cleaned.lower()

def clean_repo_name(name: str) -> str:
    """Clean name for repository naming (kept for backward compatibility)"""
    return clean_folder_name(name)

def generate_folder_name(project: Dict, config: Dict) -> str:
    """Generate folder name for project project within single repository"""
    pattern = config.get('repository', {}).get('folder_naming_pattern', '{index_number}-{research_area}')
    
    return pattern.format(
        index_number=project['index_number'],
        research_area=project['research_area_clean'],
        course_code=config.get('project', {}).get('course_code', ''),
        semester=config.get('project', {}).get('semester', '')
    )

def generate_repo_name(project: Dict, config: Dict) -> str:
    """Generate folder name (modified for Option 3 - single repo with folders)"""
    return generate_folder_name(project, config)

def create_folder_structure(base_path: str, project: Dict, config: Dict) -> Dict[str, str]:
    """Create folder structure for project project within the main repository"""
    folder_name = generate_folder_name(project, config)
    project_folder = os.path.join(base_path, folder_name)
    
    # Define standard folder structure for each project
    folders = {
        'main': project_folder,
        'docs': os.path.join(project_folder, 'docs'),
        'src': os.path.join(project_folder, 'src'),
        'data': os.path.join(project_folder, 'data'),
        'notebooks': os.path.join(project_folder, 'notebooks'),
        'results': os.path.join(project_folder, 'results'),
        'references': os.path.join(project_folder, 'references')
    }
    
    try:
        # Create directories
        for folder_type, folder_path in folders.items():
            os.makedirs(folder_path, exist_ok=True)
            logger.debug(f"Created folder: {folder_path}")
        
        # Create initial files
        create_initial_project_files(folders, project, config)
        
        logger.info(f"Created folder structure for project: {project['index_number']}")
        return folders
        
    except Exception as e:
        logger.error(f"Error creating folder structure: {e}")
        raise

def create_initial_project_files(folders: Dict[str, str], project: Dict, config: Dict):
    """Create initial files for project project"""
    try:
        # Create README.md
        readme_content = generate_project_readme(project, config)
        readme_path = os.path.join(folders['main'], 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Create .gitkeep files in empty directories
        gitkeep_folders = ['data', 'results', 'references']
        for folder_name in gitkeep_folders:
            if folder_name in folders:
                gitkeep_path = os.path.join(folders[folder_name], '.gitkeep')
                with open(gitkeep_path, 'w') as f:
                    f.write('# This file keeps the folder in git\n')
        
        # Create requirements.txt template
        requirements_path = os.path.join(folders['main'], 'requirements.txt')
        requirements_content = get_requirements_template(config)
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        
        # Create project structure guide
        structure_path = os.path.join(folders['docs'], 'project_structure.md')
        structure_content = get_project_structure_guide()
        with open(structure_path, 'w', encoding='utf-8') as f:
            f.write(structure_content)
            
    except Exception as e:
        logger.error(f"Error creating initial files: {e}")

def generate_project_readme(project: Dict, config: Dict) -> str:
    """Generate README content for project project"""
    project_name = config.get('project', {}).get('main_project_name', 'Research Project')
    
    return f"""# {project['index_number']} - {project['research_area']}

**project:** {project['index_number']}  
**Research Area:** {project['research_area']}  
**Course:** {project_name}  

## Project Structure

```
{generate_folder_name(project, config)}/
├── docs/                   # Documentation and reports
├── src/                    # Source code
├── data/                   # Dataset and data files
├── notebooks/              # Jupyter notebooks for analysis
├── results/                # Results, outputs, and figures
├── references/             # Literature and reference materials
├── README.md              # This file
└── requirements.txt       # Python dependencies
```

## Getting Started

1. Review the project requirements in `docs/`
2. Set up your development environment using `requirements.txt`
3. Document your progress using GitHub Issues
4. Keep your code organized in the `src/` folder
5. Save analysis notebooks in the `notebooks/` folder

## Milestones

- [ ] Literature Review
- [ ] Methodology Design
- [ ] Implementation
- [ ] Mid-term Evaluation
- [ ] Final Evaluation

## Contact

For questions or support, please create an issue in this repository or contact your supervisor.
"""

def get_requirements_template(config: Dict) -> str:
    """Get requirements.txt template content"""
    return """# Core scientific computing
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.5.0
seaborn>=0.11.0
scipy>=1.7.0

# Machine Learning (uncomment as needed)
# scikit-learn>=1.0.0
# tensorflow>=2.8.0
# torch>=1.11.0

# Jupyter and visualization
jupyter>=1.0.0
plotly>=5.0.0

# Data processing
# openpyxl>=3.0.0
# requests>=2.28.0

# Add your specific requirements here
"""

def get_project_structure_guide() -> str:
    """Get project structure guide content"""
    return """# Project Structure Guide

This document explains how to organize your research project files.

## Folder Descriptions

### `/docs/`
- Literature review documents
- Methodology documentation
- Progress reports
- Final thesis/report

### `/src/`
- Main source code files
- Utility functions
- Data processing scripts
- Model implementations

### `/data/`
- Raw datasets
- Processed data files
- Data description files
- **Note:** Large datasets should be stored externally (Google Drive, etc.)

### `/notebooks/`
- Exploratory data analysis notebooks
- Experimentation notebooks
- Visualization notebooks
- Prototype implementations

### `/results/`
- Generated figures and plots
- Model outputs
- Performance metrics
- Experiment results

### `/references/`
- Research papers (PDFs)
- Bibliography files
- Reference datasets
- External resources

## Best Practices

1. **Use descriptive file names** with dates or versions
2. **Document your code** with comments and docstrings
3. **Keep notebooks clean** and well-organized
4. **Regular commits** with meaningful messages
5. **Update README.md** with progress and instructions

## Naming Conventions

- Files: `snake_case.py`
- Notebooks: `01_data_exploration.ipynb`
- Documentation: `UPPERCASE.md` for important docs
"""

def save_progress_data(data: Dict, filename: str, directory: str = 'data/progress'):
    """Save progress data to JSON file"""
    try:
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.debug(f"Saved progress data to {filepath}")
        
    except Exception as e:
        logger.error(f"Error saving progress data: {e}")

def load_progress_data(filename: str, directory: str = 'data/progress') -> Dict:
    """Load progress data from JSON file"""
    try:
        filepath = os.path.join(directory, filename)
        
        if not os.path.exists(filepath):
            return {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Error loading progress data: {e}")
        return {}

def calculate_progress_percentage(issues: List[Dict], milestones: Dict) -> float:
    """Calculate overall progress percentage based on completed issues"""
    if not issues:
        return 0.0
    
    total_weight = 0
    completed_weight = 0
    
    for issue in issues:
        milestone_title = issue.get('milestone', {}).get('title', '').lower() if issue.get('milestone') else 'other'
        
        # Find milestone weight
        weight = 1  # Default weight
        for milestone_key, milestone_data in milestones.items():
            if milestone_key.lower() in milestone_title:
                weight = milestone_data.get('weight', 1)
                break
        
        total_weight += weight
        
        if issue.get('state') == 'closed':
            completed_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return (completed_weight / total_weight) * 100

def get_milestone_status(issues: List[Dict], milestone_name: str) -> str:
    """Get status of specific milestone"""
    milestone_issues = [
        issue for issue in issues 
        if issue.get('milestone', {}).get('title', '').lower().find(milestone_name.lower()) != -1
    ]
    
    if not milestone_issues:
        return 'not_started'
    
    closed_count = sum(1 for issue in milestone_issues if issue.get('state') == 'closed')
    
    if closed_count == len(milestone_issues):
        return 'completed'
    elif closed_count > 0:
        return 'in_progress'
    else:
        return 'started'

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse datetime string"""
    try:
        return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    except Exception:
        return None

def create_backup(source_file: str, backup_dir: str = 'data/backups'):
    """Create backup of a file"""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        if not os.path.exists(source_file):
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(source_file)
        backup_filename = f"{timestamp}_{filename}"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        import shutil
        shutil.copy2(source_file, backup_path)
        
        logger.debug(f"Created backup: {backup_path}")
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")

def validate_config(config: Dict) -> List[str]:
    """Validate configuration file"""
    errors = []
    
    # Check required sections
    required_sections = ['github', 'project', 'repository']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Check GitHub configuration
    if 'github' in config:
        github_config = config['github']
        if not github_config.get('token'):
            errors.append("GitHub token is required")
        if not github_config.get('organization'):
            errors.append("GitHub organization is required")
    
    # Check project configuration
    if 'project' in config:
        project_config = config['project']
        if not project_config.get('main_project_name'):
            errors.append("Main project name is required")
    
    return errors

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(f'logs/{log_file}'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

def generate_report_id() -> str:
    """Generate unique report ID"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
    return f"{timestamp}_{random_suffix}"

def export_to_csv(data: List[Dict], filename: str, directory: str = 'data/exports'):
    """Export data to CSV file"""
    try:
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        
        if not data:
            logger.warning("No data to export")
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported data to {filepath}")
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")

def batch_process(items: List, process_func, batch_size: int = 10, delay: float = 1.0):
    """Process items in batches with delay"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1}")
        
        for item in batch:
            try:
                result = process_func(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                results.append({'error': str(e), 'item': item})
        
        if i + batch_size < len(items):
            import time
            time.sleep(delay)
    
    return results

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem"""
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized

def ensure_directory_exists(path: str):
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")

def get_file_hash(filepath: str) -> str:
    """Get MD5 hash of file"""
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
    """Merge two configuration dictionaries"""
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    
    return merged

# """
# Utility functions for the GitHub project management system
# """

# import json
# import csv
# import os
# import logging
# from typing import Dict, List, Any, Optional
# from datetime import datetime, timedelta
# import hashlib

# logger = logging.getLogger(__name__)

# def load_config(config_path: str = 'config/settings.json') -> Dict:
#     """Load configuration from JSON file"""
#     try:
#         with open(config_path, 'r', encoding='utf-8') as f:
#             config = json.load(f)
        
#         # Load environment variables if .env file exists
#         env_path = os.path.join(os.path.dirname(config_path), '.env')
#         if os.path.exists(env_path):
#             config = load_env_variables(config, env_path)
        
#         return config
#     except FileNotFoundError:
#         logger.error(f"Configuration file not found: {config_path}")
#         raise
#     except json.JSONDecodeError as e:
#         logger.error(f"Invalid JSON in configuration file: {e}")
#         raise

# def load_env_variables(config: Dict, env_path: str) -> Dict:
#     """Load environment variables from .env file"""
#     try:
#         with open(env_path, 'r') as f:
#             for line in f:
#                 line = line.strip()
#                 if line and not line.startswith('#') and '=' in line:
#                     key, value = line.split('=', 1)
#                     # Update GitHub token if provided in .env
#                     if key.strip() == 'GITHUB_TOKEN':
#                         config['github']['token'] = value.strip().strip('"\'')
        
#         return config
#     except Exception as e:
#         logger.warning(f"Could not load .env file: {e}")
#         return config

# def load_project_data(csv_path: str) -> List[Dict]:
#     """Load project data from CSV file"""
#     projects = []
    
#     try:
#         with open(csv_path, 'r', encoding='utf-8') as f:
#             reader = csv.DictReader(f)
            
#             for row in reader:
#                 # Clean and validate data
#                 project = {
#                     'index_number': row.get('index_number', '').strip(),
#                     'research_area': row.get('research_area', '').strip(),
#                     'email': row.get('email', '').strip(),
#                     'github_username': row.get('github_username', '').strip() or None
#                 }
                
#                 # Validate required fields
#                 if not project['index_number'] or not project['research_area']:
#                     logger.warning(f"Skipping invalid project record: {row}")
#                     continue
                
#                 # Clean research area for repository naming
#                 project['research_area_clean'] = clean_repo_name(project['research_area'])
                
#                 projects.append(project)
        
#         logger.info(f"Loaded {len(projects)} projects from {csv_path}")
#         return projects
        
#     except FileNotFoundError:
#         logger.error(f"project data file not found: {csv_path}")
#         raise
#     except Exception as e:
#         logger.error(f"Error loading project data: {e}")
#         raise

# def load_supervisor_data(config: Dict) -> List[Dict]:
#     """Load supervisor data from configuration"""
#     try:
#         supervisors = []
        
#         # Load from supervisors.json if exists
#         supervisors_path = 'config/supervisors.json'
#         if os.path.exists(supervisors_path):
#             with open(supervisors_path, 'r', encoding='utf-8') as f:
#                 supervisor_config = json.load(f)
#                 supervisors.extend(supervisor_config.get('supervisors', []))
                
#                 # Add module coordinator
#                 if 'module_coordinator' in supervisor_config:
#                     coordinator = supervisor_config['module_coordinator']
#                     coordinator['role'] = 'module_coordinator'
#                     supervisors.append(coordinator)
        
#         # Fallback to config file
#         if not supervisors and 'supervisors' in config:
#             supervisors = config['supervisors']
        
#         return supervisors
        
#     except Exception as e:
#         logger.error(f"Error loading supervisor data: {e}")
#         return []

# def clean_repo_name(name: str) -> str:
#     """Clean name for repository naming"""
#     # Replace spaces and special characters with underscores
#     cleaned = name.replace(' ', '_').replace('-', '_')
#     # Remove multiple underscores
#     import re
#     cleaned = re.sub(r'_+', '_', cleaned)
#     # Remove leading/trailing underscores
#     cleaned = cleaned.strip('_')
#     # Ensure it's not empty
#     if not cleaned:
#         cleaned = 'project'
#     return cleaned

# def generate_repo_name(project: Dict, config: Dict) -> str:
#     """Generate repository name based on configuration pattern"""
#     pattern = config.get('repository', {}).get('naming_pattern', '{index_number}_{research_area}')
    
#     return pattern.format(
#         index_number=project['index_number'],
#         research_area=project['research_area_clean'],
#         course_code=config.get('project', {}).get('course_code', ''),
#         semester=config.get('project', {}).get('semester', '')
#     )

# def save_progress_data(data: Dict, filename: str, directory: str = 'data/progress'):
#     """Save progress data to JSON file"""
#     try:
#         os.makedirs(directory, exist_ok=True)
#         filepath = os.path.join(directory, filename)
        
#         with open(filepath, 'w', encoding='utf-8') as f:
#             json.dump(data, f, indent=2, default=str)
        
#         logger.debug(f"Saved progress data to {filepath}")
        
#     except Exception as e:
#         logger.error(f"Error saving progress data: {e}")

# def load_progress_data(filename: str, directory: str = 'data/progress') -> Dict:
#     """Load progress data from JSON file"""
#     try:
#         filepath = os.path.join(directory, filename)
        
#         if not os.path.exists(filepath):
#             return {}
        
#         with open(filepath, 'r', encoding='utf-8') as f:
#             return json.load(f)
            
#     except Exception as e:
#         logger.error(f"Error loading progress data: {e}")
#         return {}

# def calculate_progress_percentage(issues: List[Dict], milestones: Dict) -> float:
#     """Calculate overall progress percentage based on completed issues"""
#     if not issues:
#         return 0.0
    
#     total_weight = 0
#     completed_weight = 0
    
#     for issue in issues:
#         milestone_title = issue.get('milestone', {}).get('title', '').lower() if issue.get('milestone') else 'other'
        
#         # Find milestone weight
#         weight = 1  # Default weight
#         for milestone_key, milestone_data in milestones.items():
#             if milestone_key.lower() in milestone_title:
#                 weight = milestone_data.get('weight', 1)
#                 break
        
#         total_weight += weight
        
#         if issue.get('state') == 'closed':
#             completed_weight += weight
    
#     if total_weight == 0:
#         return 0.0
    
#     return (completed_weight / total_weight) * 100

# def get_milestone_status(issues: List[Dict], milestone_name: str) -> str:
#     """Get status of specific milestone"""
#     milestone_issues = [
#         issue for issue in issues 
#         if issue.get('milestone', {}).get('title', '').lower().find(milestone_name.lower()) != -1
#     ]
    
#     if not milestone_issues:
#         return 'not_started'
    
#     closed_count = sum(1 for issue in milestone_issues if issue.get('state') == 'closed')
    
#     if closed_count == len(milestone_issues):
#         return 'completed'
#     elif closed_count > 0:
#         return 'in_progress'
#     else:
#         return 'started'

# def format_datetime(dt: datetime) -> str:
#     """Format datetime for display"""
#     return dt.strftime('%Y-%m-%d %H:%M:%S')

# def parse_datetime(dt_string: str) -> Optional[datetime]:
#     """Parse datetime string"""
#     try:
#         return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
#     except Exception:
#         return None

# def create_backup(source_file: str, backup_dir: str = 'data/backups'):
#     """Create backup of a file"""
#     try:
#         os.makedirs(backup_dir, exist_ok=True)
        
#         if not os.path.exists(source_file):
#             return
        
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         filename = os.path.basename(source_file)
#         backup_filename = f"{timestamp}_{filename}"
#         backup_path = os.path.join(backup_dir, backup_filename)
        
#         import shutil
#         shutil.copy2(source_file, backup_path)
        
#         logger.debug(f"Created backup: {backup_path}")
        
#     except Exception as e:
#         logger.error(f"Error creating backup: {e}")

# def validate_config(config: Dict) -> List[str]:
#     """Validate configuration file"""
#     errors = []
    
#     # Check required sections
#     required_sections = ['github', 'project', 'repository']
#     for section in required_sections:
#         if section not in config:
#             errors.append(f"Missing required section: {section}")
    
#     # Check GitHub configuration
#     if 'github' in config:
#         github_config = config['github']
#         if not github_config.get('token'):
#             errors.append("GitHub token is required")
#         if not github_config.get('organization'):
#             errors.append("GitHub organization is required")
    
#     # Check project configuration
#     if 'project' in config:
#         project_config = config['project']
#         if not project_config.get('main_project_name'):
#             errors.append("Main project name is required")
    
#     return errors

# def setup_logging(log_level: str = 'INFO', log_file: str = None):
#     """Setup logging configuration"""
#     log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
#     # Create logs directory
#     os.makedirs('logs', exist_ok=True)
    
#     handlers = [logging.StreamHandler()]
    
#     if log_file:
#         handlers.append(logging.FileHandler(f'logs/{log_file}'))
    
#     logging.basicConfig(
#         level=getattr(logging, log_level.upper()),
#         format=log_format,
#         handlers=handlers
#     )

# def generate_report_id() -> str:
#     """Generate unique report ID"""
#     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#     random_suffix = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
#     return f"{timestamp}_{random_suffix}"

# def export_to_csv(data: List[Dict], filename: str, directory: str = 'data/exports'):
#     """Export data to CSV file"""
#     try:
#         os.makedirs(directory, exist_ok=True)
#         filepath = os.path.join(directory, filename)
        
#         if not data:
#             logger.warning("No data to export")
#             return
        
#         with open(filepath, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.DictWriter(f, fieldnames=data[0].keys())
#             writer.writeheader()
#             writer.writerows(data)
        
#         logger.info(f"Exported data to {filepath}")
        
#     except Exception as e:
#         logger.error(f"Error exporting to CSV: {e}")

# def batch_process(items: List, process_func, batch_size: int = 10, delay: float = 1.0):
#     """Process items in batches with delay"""
#     results = []
    
#     for i in range(0, len(items), batch_size):
#         batch = items[i:i + batch_size]
        
#         logger.info(f"Processing batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1}")
        
#         for item in batch:
#             try:
#                 result = process_func(item)
#                 results.append(result)
#             except Exception as e:
#                 logger.error(f"Error processing item: {e}")
#                 results.append({'error': str(e), 'item': item})
        
#         if i + batch_size < len(items):
#             time.sleep(delay)
    
#     return results

# def sanitize_filename(filename: str) -> str:
#     """Sanitize filename for filesystem"""
#     import re
#     # Remove invalid characters
#     sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
#     # Limit length
#     if len(sanitized) > 255:
#         sanitized = sanitized[:255]
#     return sanitized

# def ensure_directory_exists(path: str):
#     """Ensure directory exists, create if not"""
#     try:
#         os.makedirs(path, exist_ok=True)
#     except Exception as e:
#         logger.error(f"Error creating directory {path}: {e}")

# def get_file_hash(filepath: str) -> str:
#     """Get MD5 hash of file"""
#     try:
#         hash_md5 = hashlib.md5()
#         with open(filepath, 'rb') as f:
#             for chunk in iter(lambda: f.read(4096), b""):
#                 hash_md5.update(chunk)
#         return hash_md5.hexdigest()
#     except Exception as e:
#         logger.error(f"Error calculating file hash: {e}")
#         return ""

# def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
#     """Merge two configuration dictionaries"""
#     merged = base_config.copy()
    
#     for key, value in override_config.items():
#         if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
#             merged[key] = merge_configs(merged[key], value)
#         else:
#             merged[key] = value
    
#     return merged