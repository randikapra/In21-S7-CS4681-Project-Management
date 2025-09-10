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
        self.templates_dir = 'templates'
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
            
            # # Create project folders in batches
            # def create_folder(project):
            #     return self.create_student_folder(project)
            
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

    # # Version 1.0
    # def create_file_in_repo(self, path: str, content: str, message: str) -> bool:
    #     """Create file in main repository"""
    #     try:
    #         # Check if file already exists
    #         existing_file = self.github.get_repository_file(self.org, self.main_repo_name, path)
            
    #         if existing_file:
    #             # Update existing file
    #             success = self.github.update_repository_file(
    #                 org=self.org,
    #                 repo=self.main_repo_name,
    #                 path=path,
    #                 content=content,
    #                 message=f"Update {path}",
    #                 sha=existing_file['sha']
    #             )
    #         else:
    #             # Create new file
    #             success = self.github.create_file(
    #                 org=self.org,
    #                 repo=self.main_repo_name,
    #                 path=path,
    #                 message=message,
    #                 content=content
    #             )
            
    #         if success:
    #             logger.debug(f"Created/updated file: {path}")
            
    #         return success
            
    #     except Exception as e:
    #         logger.error(f"Error creating file {path}: {e}")
    #         return False
    def create_file_in_repo(self, path: str, content: str, message: str) -> bool:
        """Create file in main repository"""
        try:
            # Check if file already exists
            existing_file = self.github.get_repository_file(self.org, self.main_repo_name, path)
            
            if existing_file:
                # Update existing file
                success = self.github.update_repository_file(
                    org=self.org,
                    repo=self.main_repo_name,  # Add the missing repo parameter
                    path=path,
                    content=content,
                    message=f"Update {path}",
                    sha=existing_file['sha']
                )
            else:
                # Create new file
                success = self.github.create_file(
                    org=self.org,
                    repo=self.main_repo_name,  # Add the missing repo parameter
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
            # return self.generate_student_readme(student)
            return self.generate_project_readme(student)
        elif file_path.endswith('research_proposal.md'):
            return self.generate_proposal_template(student)
        elif file_path.endswith('literature_review.md'):
            return self.generate_literature_review_template(student)
        elif file_path.endswith('methodology.md'):
            return self.generate_methodology_template(student)
        elif file_path.endswith('requirements.txt'):
            return self.generate_requirements_template()
        elif file_path.endswith('.gitkeep'):
            return "# This file keeps the directory in git\n# You can delete this file once you add other files to this directory\n"
        elif file_path.endswith('usage_instructions.md'):
            return self.load_template('documentation/usage_instructions.md') or "# Student Usage Instructions\n\n[Instructions will be loaded from template]"
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
                ('README.md', self.generate_main_readme()),
                ('.gitignore', self.load_template('repository/.gitignore')),
                ('requirements.txt', self.load_template('repository/requirements.txt')),
                ('docs/project_overview.md', self.generate_project_overview()),
                ('docs/project_guidelines.md', self.load_template('documentation/usage_instructions.md')),
                ('docs/supervisor_guide.md', self.load_template('documentation/supervisor_guide.md')),
                ('projects/README.md', self.generate_projects_readme()),
                ('templates/project_readme_template.md', self.load_template('repository/README.md')),
                ('.github/ISSUE_TEMPLATE/progress_report.md', self.load_template('issues/progress_report.md')),
                ('.github/ISSUE_TEMPLATE/milestone_submission.md', self.generate_milestone_issue_template())
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
    
    def get_file_content(self, file_path: str, student: Dict) -> str:
        """Get appropriate content for file based on path and project data"""
        if file_path.endswith('README.md') and 'projects/' in file_path:
            return self.generate_project_readme(student)
        elif file_path.endswith('research_proposal.md'):
            return self.generate_proposal_template(student)
        elif file_path.endswith('literature_review.md'):
            return self.generate_literature_review_template(student)
        elif file_path.endswith('.gitkeep'):
            return "# This file keeps the directory in git\n# You can delete this file once you add other files to this directory\n"
        else:
            return "# Placeholder file\n"
    
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
    
    def generate_main_readme(self) -> str:
        """Generate main repository README"""
        return f"""# {self.main_repo_name}

## {self.config.get('project', {}).get('course_name', 'Advanced Machine Learning')} Research Projects

**Course Code:** {self.config.get('project', {}).get('course_code', 'CS4681')}
**Academic Year:** {self.config.get('project', {}).get('academic_year', '2024/2025')}
**Semester:** {self.config.get('project', {}).get('semester', '7')}

## Repository Structure

```
├── projects/                    # Individual project project folders
│   ├── [INDEX]-[RESEARCH-AREA]/
│   │   ├── README.md           # project project overview
│   │   ├── docs/               # Documentation and reports
│   │   ├── src/                # Source code
│   │   ├── data/               # Datasets
│   │   ├── experiments/        # Experiment results
│   │   └── reports/            # Progress reports
├── docs/                       # Course documentation
│   ├── project_overview.md     # Project overview and requirements
│   ├── project_guidelines.md   # Guidelines for projects
│   └── supervisor_guide.md     # Guide for supervisors
├── templates/                  # Templates for projects
└── README.md                   # This file
```

## projects

This repository contains research projects for {len(load_project_data(self.config.get('project_data_path', 'config/project_data.csv')) if 'project_data_path' in self.config else 'multiple')} projects working on various machine learning research topics.

## Project Timeline

| Week | Milestone | Description |
|------|-----------|-------------|
| 1-3  | Literature Review | Complete literature review and research proposal |
| 4-6  | Methodology | Develop and validate methodology |
| 7-10 | Implementation | Implement proposed solution |
| 11-13| Experimentation | Conduct experiments and analysis |
| 14-16| Documentation | Final report and presentation |

## For projects

1. Navigate to your project folder: `projects/[YOUR-INDEX]-[YOUR-RESEARCH-AREA]/`
2. Read the project guidelines in `docs/project_guidelines.md`
3. Start with your research proposal in `docs/research_proposal.md`
4. Use GitHub Issues to track your progress and communicate with supervisors
5. Regular commits are expected to show continuous progress

## For Supervisors

- Access the supervisor guide at `docs/supervisor_guide.md`
- Monitor project progress through Issues and commit history
- Use GitHub Projects to track overall progress across all projects
- Weekly check-ins are recommended through issue comments

## Support

For technical issues with this repository, create an issue with the label "support".
For academic questions, contact your assigned supervisor.

---
*This repository is managed by the Department of Computer Science & Engineering*
"""
    ## version 1.0
    # def create_or_update_file(self, file_path: str, content: str, commit_message: str) -> bool:
    #     """Create or update a file in the repository"""
    #     try:
    #         repo = self.github.get_repository(f"{self.org}/{self.main_repo_name}")
            
    #         try:
    #             # Try to get existing file
    #             existing_file = repo.get_contents(file_path)
    #             # Update existing file
    #             repo.update_file(
    #                 path=file_path,
    #                 message=commit_message,
    #                 content=content,
    #                 sha=existing_file.sha
    #             )
    #             self.logger.info(f"Updated file: {file_path}")
    #         except:
    #             # Create new file
    #             repo.create_file(
    #                 path=file_path,
    #                 message=commit_message,
    #                 content=content
    #             )
    #             self.logger.info(f"Created file: {file_path}")
            
    #         return True
            
    #     except Exception as e:
    #         self.logger.error(f"Failed to create/update file {file_path}: {e}")
    #         return False

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
            
    def generate_projects_readme(self) -> str:
        """Generate README for projects directory"""
        return """# Projects

This directory contains individual project folders for all projects enrolled in the course.

## Folder Structure

Each project has a dedicated folder named: `[INDEX_NUMBER]-[RESEARCH_AREA]`

Example: `CS19001-Natural-Language-Processing`

## Getting Started

1. Find your project folder
2. Read your individual README.md
3. Complete your research proposal
4. Start working on your literature review
5. Regular commits are expected

## Progress Tracking

- Use GitHub Issues to report weekly progress
- Tag supervisors in issues for feedback
- Follow the milestone deadlines
- Keep your documentation updated

## Need Help?

- Check the main repository docs/ folder for guidelines
- Create an issue with "support" label for technical help
- Contact your supervisor for academic guidance
"""
        
    def generate_project_readme(self, student: Dict) -> str:
        """Generate personalized README for student folder"""
        return f"""# {student['research_area']} - {student['index_number']}

## Student Information

- **Index Number:** {student['index_number']}
- **Research Area:** {student['research_area']}
- **GitHub Username:** @{student.get('github_username', 'Not provided')}
- **Email:** {student.get('email', 'Not provided')}

## Project Structure
```
{student['index_number']}-{student['research_area'].replace(' ', '-')}/
├── README.md                    # This file
├── docs/
│   ├── research_proposal.md     # Your research proposal (Required)
│   ├── literature_review.md     # Literature review and references
│   ├── methodology.md           # Detailed methodology
│   └── progress_reports/        # Weekly progress reports
├── src/                         # Your source code
├── data/                        # Datasets and data files
├── experiments/                 # Experiment scripts and configs
├── results/                     # Experimental results
└── requirements.txt             # Project dependencies
```

## Getting Started

1. **Complete Research Proposal:** Fill out `docs/research_proposal.md`
2. **Literature Review:** Document your literature review in `docs/literature_review.md`
3. **Set Up Environment:** Add your dependencies to `requirements.txt`
4. **Start Coding:** Begin implementation in the `src/` folder
5. **Track Progress:** Use GitHub Issues to report weekly progress

## Milestones

- [ ] **Week 4:** Research Proposal Submission
- [ ] **Week 5:** Literature Review Completion  
- [ ] **Week 8:** Methodology Implementation
- [ ] **Week 12:** Final Evaluation

## Progress Tracking

Create GitHub Issues with the following labels for tracking:
- `student-{student['index_number']}` (automatically added)
- `literature-review`, `implementation`, `evaluation`, etc.
- Tag supervisors (@{self.config.get('supervisors', [{}])[0].get('github_username', 'supervisor')}) for feedback

## Resources

- Check the main repository `docs/` folder for guidelines
- Use the `templates/` folder for document templates
- Refer to `docs/student_guide.md` for detailed instructions

## Academic Integrity

- All work must be original
- Properly cite all references
- Acknowledge any collaboration
- Follow university academic integrity policies

---

**Remember:** Regular commits and clear documentation are essential for project success!
"""

    def generate_methodology_template(self, student: Dict) -> str:
        """Generate methodology template"""
        return f"""# Methodology: {student['research_area']}

**Student:** {student['index_number']}
**Research Area:** {student['research_area']}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## 1. Overview

[Provide a brief overview of your methodology]

## 2. Research Design

[Describe your overall research approach]

## 3. Data Collection

### 3.1 Data Sources
[List your data sources]

### 3.2 Data Description
[Describe your datasets]

### 3.3 Data Preprocessing
[Explain preprocessing steps]

## 4. Model Architecture

[Describe your proposed model/algorithm]

## 5. Experimental Setup

### 5.1 Evaluation Metrics
[List evaluation metrics you'll use]

### 5.2 Baseline Models
[Describe baseline comparisons]

### 5.3 Hardware/Software Requirements
[List computational requirements]

## 6. Implementation Plan

| Phase | Tasks | Duration | Deliverables |
|-------|-------|----------|--------------|
| Phase 1 | Data preprocessing | 2 weeks | Clean dataset |
| Phase 2 | Model implementation | 3 weeks | Working model |
| Phase 3 | Experiments | 2 weeks | Results |
| Phase 4 | Analysis | 1 week | Final report |

## 7. Risk Analysis

[Identify potential risks and mitigation strategies]

## 8. Expected Outcomes

[Describe expected results and contributions]

---

**Note:** Update this document as your methodology evolves during implementation.
"""

    def generate_requirements_template(self) -> str:
        '''Generate requirements.txt template'''
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
    **Remember:** Regular commits and documentation are essential for project success!
    """
        
    def generate_literature_review_template(self, student: Dict) -> str:
        '''Generate literature review template for project'''
        return f"""# Literature Review: {student['research_area']}

**student:** {student['index_number']}
**Research Area:** {student['research_area']}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Abstract

[Provide a brief summary of your literature review - what areas you covered and key findings]

## 1. Introduction

[Introduce the research area and scope of your literature review]

## 2. Search Methodology

### Search Terms Used
- [List key terms and phrases used]
- [Include synonyms and variations]

### Databases Searched
- [ ] IEEE Xplore
- [ ] ACM Digital Library
- [ ] Google Scholar
- [ ] ArXiv
- [ ] Other: ___________

### Time Period
[e.g., 2018-2024, focusing on recent developments]

## 3. Key Areas of Research

### 3.1 [Topic Area 1]
[Discuss the main research directions in this area]

**Key Papers:**
- [Author, Year] - [Brief summary of contribution]
- [Author, Year] - [Brief summary of contribution]

### 3.2 [Topic Area 2]
[Continue with other relevant areas]

## 4. Research Gaps and Opportunities

[Identify gaps in current research that your project could address]

### Gap 1: [Description]
**Why it matters:** [Explanation]
**How your project addresses it:** [Your approach]

### Gap 2: [Description]
**Why it matters:** [Explanation]
**How your project addresses it:** [Your approach]

## 5. Theoretical Framework

[Describe the theoretical foundation for your research]

## 6. Methodology Insights

[What methodologies are commonly used? Which seem most promising for your work?]

## 7. Conclusion

[Summarize key findings and how they inform your research direction]

## References

[Use academic citation format - APA, IEEE, etc.]

1. [Reference 1]
2. [Reference 2]
3. [Reference 3]
...

---

**Notes:**
- Aim for 15-20 high-quality references minimum
- Focus on recent work (last 5 years) unless citing seminal papers
- Include a mix of conference papers, journal articles, and technical reports
- Keep updating this document as you discover new relevant work
"""
    
    def generate_project_overview(self) -> str:
        '''Generate project overview document'''
        return f"""# Project Overview - {self.config.get('project', {}).get('course_name', 'Advanced Machine Learning')}

## Course Information

- **Course Code:** {self.config.get('project', {}).get('course_code', 'CS4681')}
- **Course Name:** {self.config.get('project', {}).get('course_name', 'Advanced Machine Learning')}
- **Academic Year:** {self.config.get('project', {}).get('academic_year', '2024/2025')}
- **Semester:** {self.config.get('project', {}).get('semester', '7')}

## Project Objectives

The main objectives of this research project course are to:

1. **Develop Research Skills:** Learn to identify, formulate, and investigate research problems
2. **Apply Advanced Techniques:** Implement and evaluate advanced machine learning techniques
3. **Academic Writing:** Develop skills in academic writing and presentation
4. **Independent Learning:** Foster independent learning and critical thinking
5. **Professional Development:** Prepare for graduate studies or industry research roles

## Project Requirements

### 1. Research Proposal (Week 3)
- Problem identification and motivation
- Literature review summary
- Proposed methodology
- Expected outcomes and timeline
- **Weight:** 10%

### 2. Literature Review (Week 6)
- Comprehensive review of relevant literature
- Identification of research gaps
- Theoretical framework
- **Weight:** 15%

### 3. Methodology Implementation (Week 9)
- Detailed methodology description
- Implementation plan
- Initial proof-of-concept results
- **Weight:** 20%

### 4. Experimental Results (Week 12)
- Complete implementation
- Experimental setup and results
- Analysis and discussion
- **Weight:** 25%

### 5. Final Report (Week 15)
- Complete research report (8000-10000 words)
- Professional formatting and presentation
- Comprehensive evaluation and conclusions
- **Weight:** 25%

### 6. Project Presentation (Week 16)
- 15-minute presentation
- Demonstration of working system
- Q&A session
- **Weight:** 5%

## Research Areas

projects are working on diverse research topics including:
- Natural Language Processing
- Computer Vision
- Machine Learning Systems
- Deep Learning Applications
- Reinforcement Learning
- AI Ethics and Fairness
- And many others...

## Support Structure

### Supervisors
Each project is assigned supervisors who provide:
- Weekly guidance and feedback
- Technical support and direction
- Academic mentoring
- Assessment and evaluation

### Peer Collaboration
projects are encouraged to:
- Share knowledge and resources
- Collaborate on literature reviews
- Provide peer feedback
- Participate in study groups

### Resources Available
- Access to research databases and journals
- Computing resources and cloud credits
- Software licenses and development tools
- Library and research support services

## Timeline and Milestones

| Week | Milestone | Deliverable | Weight |
|------|-----------|-------------|--------|
| 1-2  | Project Setup | Repository setup, initial planning | - |
| 3    | Research Proposal | Complete proposal document | 10% |
| 4-5  | Literature Review | Ongoing research and reading | - |
| 6    | Literature Review | Comprehensive literature review | 15% |
| 7-8  | Methodology Development | Design and planning | - |
| 9    | Methodology Implementation | Working implementation | 20% |
| 10-11| Experimentation | Conducting experiments | - |
| 12   | Experimental Results | Results and analysis | 25% |
| 13-14| Report Writing | Drafting final report | - |
| 15   | Final Report | Complete research report | 25% |
| 16   | Presentation | Project presentation | 5% |

## Assessment Criteria

### Technical Excellence (40%)
- Correctness and sophistication of implementation
- Appropriate use of advanced techniques
- Quality of experimental design
- Innovation and creativity

### Research Quality (35%)
- Depth of literature review
- Clear problem formulation
- Rigorous methodology
- Valid conclusions and insights

### Communication (25%)
- Clarity of writing and presentation
- Professional formatting and organization
- Appropriate use of figures and tables
- Effective oral presentation

## Academic Integrity

All projects must:
- Submit original work only
- Properly cite all sources and references
- Acknowledge any collaboration or assistance
- Follow the university's academic integrity policy
- Use plagiarism detection tools responsibly

## Getting Help

### Technical Issues
- Create issues in the repository with "support" label
- Attend lab sessions and office hours
- Consult with technical assistants

### Academic Questions
- Schedule meetings with your assigned supervisor
- Participate in group discussions
- Utilize library research support services

### Emergency Situations
- Contact course coordinator immediately
- Use official university channels for serious issues
- Document any circumstances affecting your work

---

**Success Tips:**
- Start early and work consistently
- Regular communication with supervisors
- Keep detailed records of your progress
- Don't hesitate to ask for help when needed
- Focus on learning, not just grades
"""

    def generate_milestone_issue_template(self) -> str:
        """Generate milestone issue template"""
        return """---
name: Milestone Submission
about: Submit milestone deliverable for review
title: '[MILESTONE] [Your Index Number] - [Milestone Name]'
labels: milestone, submission
assignees: ''

---

## project Information
- **Index Number:** 
- **Research Area:** 
- **Milestone:** 
- **Due Date:** 

## Submission Details

### Deliverable Location
- [ ] Files uploaded to appropriate folder
- [ ] Documentation updated
- [ ] Code committed and pushed

### Completion Checklist
- [ ] All requirements met
- [ ] Self-review completed
- [ ] Ready for supervisor review

### Summary
[Provide a brief summary of what you've accomplished for this milestone]

### Challenges Faced
[Describe any significant challenges and how you addressed them]

### Next Steps
[Outline your plans for the next phase of work]

### Questions for Supervisors
[List any specific questions or areas where you need guidance]

## Files Changed/Added
[List the main files that were added or modified for this milestone]

---

**For Supervisors:**
Please review the submission and provide feedback. Use labels to indicate:
- `approved` - Milestone accepted
- `needs-revision` - Requires changes before acceptance
- `feedback-provided` - General feedback given
"""
    
    def load_template(self, template_path: str) -> Optional[str]:
        """Load template content from file"""
        try:
            full_path = os.path.join(self.templates_dir, template_path)
            # print(full_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Template not found: {full_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
    def generate_proposal_template(self, student: Dict) -> str:
        """Generate research proposal template"""
        return f"""# Research Proposal: {student['research_area']}

**student:** {student['index_number']}
**Research Area:** {student['research_area']}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Abstract

[Write a brief abstract of your research proposal (150-200 words)]

## 1. Introduction

[Introduce your research topic and its significance]

## 2. Problem Statement

[Clearly define the research problem you aim to solve]

## 3. Literature Review Summary

[Provide a brief summary of relevant literature and identify gaps]

## 4. Research Objectives

### Primary Objective
[Main goal of your research]

### Secondary Objectives
- [Objective 1]
- [Objective 2]
- [Objective 3]

## 5. Methodology

[Describe your proposed methodology and approach]

## 6. Expected Outcomes

[What do you expect to achieve?]

## 7. Timeline

| Week | Task |
|------|------|
| 1-2  | Literature Review |
| 3-4  | Methodology Development |
| 5-8  | Implementation |
| 9-12 | Experimentation |
| 13-15| Analysis and Writing |
| 16   | Final Submission |

## 8. Resources Required

[List required resources, datasets, tools, etc.]

## References

[Add references in academic format]

---

**Submission Instructions:**
1. Complete all sections above
2. Commit your changes to the repository
3. Create an issue with the label "milestone" and "research-proposal"
4. Tag your supervisors in the issue for review
"""
    
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
