"""
Individual project project management for single repository with folders
"""

import logging
from typing import Dict, List, Optional
from .github_client import GitHubClient

logger = logging.getLogger(__name__)

class StudentProjectManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        self.repo_name = config['repository']['name']  # Single repo: In21-S7-CS4681-AML-Research-Projects
        
    def create_project_folder_structure(self, project_data: Dict) -> Dict:
        """Create folder structure for project in the main repository"""
        try:
            project_folder = f"projects/{project_data['index_number']}"
            
            logger.info(f"Creating folder structure for {project_data['index_number']}")
            
            # Create project folder with initial files
            files_to_create = {
                f"{project_folder}/README.md": self._generate_project_readme(project_data),
                f"{project_folder}/docs/literature_review.md": self._generate_literature_template(),
                f"{project_folder}/src/.gitkeep": "# Source code directory",
                f"{project_folder}/data/.gitkeep": "# Data directory", 
                f"{project_folder}/results/.gitkeep": "# Results directory",
                f"{project_folder}/requirements.txt": "# Add your Python dependencies here"
            }
            
            # Create files via GitHub API
            for file_path, content in files_to_create.items():
                try:
                    self.github.create_file(
                        org=self.org,
                        repo=self.repo_name,
                        path=file_path,
                        message=f"Initialize folder structure for {project_data['index_number']}",
                        content=content
                    )
                except Exception as e:
                    logger.warning(f"Could not create {file_path}: {e}")
            
            return {
                'status': 'success',
                'project_folder': project_folder,
                'project': project_data,
                'files_created': list(files_to_create.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to create folder structure for {project_data['index_number']}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'project': project_data
            }
    
    def create_project_issues(self, project_data: Dict) -> Dict:
        """Create milestone issues for individual project tracking"""
        try:
            project_folder = f"projects/{project_data['index_number']}"
            
            # Create milestone issues
            milestones = [
                {
                    'title': f"📚 Literature Review - {project_data['index_number']}",
                    'body': f"""**project:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Tasks:
- [ ] Research relevant papers in {project_data['research_area']}
- [ ] Create comprehensive literature review
- [ ] Identify research gaps
- [ ] Submit literature review document

**Deliverable:** `{project_folder}/docs/literature_review.md`
**Deadline:** Week 4""",
                    'labels': ['literature-review', f'project-{project_data["index_number"]}', 'milestone']
                },
                {
                    'title': f"🔬 Methodology & Implementation - {project_data['index_number']}",
                    'body': f"""**project:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Tasks:
- [ ] Define research methodology
- [ ] Implement baseline models
- [ ] Setup experimental framework
- [ ] Data preprocessing pipeline

**Deliverable:** Working code in `{project_folder}/src/` folder
**Deadline:** Week 8""",
                    'labels': ['implementation', f'project-{project_data["index_number"]}', 'milestone']
                },
                {
                    'title': f"📊 Mid Evaluation - {project_data['index_number']}",
                    'body': f"""**project:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Tasks:
- [ ] Submit mid-term progress report
- [ ] Present preliminary results
- [ ] Address supervisor feedback
- [ ] Update project timeline

**Deliverable:** Mid-term report + presentation in `{project_folder}/docs/`
**Deadline:** Week 10""",
                    'labels': ['mid-evaluation', f'project-{project_data["index_number"]}', 'milestone']
                },
                {
                    'title': f"📝 Final Evaluation - {project_data['index_number']}",
                    'body': f"""**project:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Tasks:
- [ ] Complete experimental evaluation
- [ ] Write research paper
- [ ] Prepare final presentation
- [ ] Submit all deliverables

**Deliverable:** Complete research paper + code in `{project_folder}/`
**Deadline:** Week 16""",
                    'labels': ['final-evaluation', f'project-{project_data["index_number"]}', 'milestone']
                }
            ]
            
            created_issues = []
            for milestone in milestones:
                try:
                    issue = self.github.create_issue(
                        org=self.org,
                        repo=self.repo_name,
                        title=milestone['title'],
                        body=milestone['body'],
                        labels=milestone['labels']
                    )
                    created_issues.append({
                        'number': issue['number'],
                        'title': issue['title'],
                        'url': issue['html_url']
                    })
                    logger.debug(f"Created issue: {milestone['title']}")
                except Exception as e:
                    logger.warning(f"Failed to create issue {milestone['title']}: {e}")
            
            return {
                'status': 'success',
                'project': project_data,
                'issues_created': created_issues
            }
            
        except Exception as e:
            logger.error(f"Failed to create issues for {project_data['index_number']}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'project': project_data
            }
    
    def update_project_progress(self, project_data: Dict) -> Dict:
        """Update project progress based on their issues"""
        try:
            # Get project-specific issues
            all_issues = self.github.list_issues(self.org, self.repo_name)
            project_label = f"project-{project_data['index_number']}"
            project_issues = [issue for issue in all_issues 
                            if any(label['name'] == project_label for label in issue.get('labels', []))]
            
            # Calculate progress metrics
            total_issues = len(project_issues)
            closed_issues = len([i for i in project_issues if i['state'] == 'closed'])
            open_issues = total_issues - closed_issues
            
            progress_percentage = (closed_issues / max(total_issues, 1)) * 100
            
            # Determine current phase
            current_phase = self._determine_current_phase(progress_percentage, project_issues)
            
            return {
                'project_id': project_data['index_number'],
                'project_folder': f"projects/{project_data['index_number']}",
                'total_issues': total_issues,
                'closed_issues': closed_issues,
                'open_issues': open_issues,
                'progress_percentage': progress_percentage,
                'current_phase': current_phase,
                'last_updated': project_issues[0]['updated_at'] if project_issues else None
            }
            
        except Exception as e:
            logger.error(f"Failed to update progress for {project_data['index_number']}: {e}")
            return {
                'project_id': project_data['index_number'],
                'error': str(e)
            }
    
    def _determine_current_phase(self, progress_percentage: float, issues: List[Dict]) -> str:
        """Determine current project phase based on progress and issues"""
        if progress_percentage == 0:
            return "Not Started"
        
        # Check for specific milestone issues
        milestone_keywords = {
            'literature': 'Literature Review',
            'implementation': 'Implementation',
            'mid': 'Mid Evaluation',
            'final': 'Final Evaluation'
        }
        
        recent_activity = issues[:3] if issues else []  # Most recent issues
        
        for issue in recent_activity:
            issue_title = issue['title'].lower()
            for keyword, phase in milestone_keywords.items():
                if keyword in issue_title:
                    return phase
        
        # Fallback to progress percentage
        if progress_percentage < 25:
            return "Literature Review"
        elif progress_percentage < 50:
            return "Implementation" 
        elif progress_percentage < 75:
            return "Mid Evaluation"
        else:
            return "Final Phase"
    
    def get_project_project_stats(self, project_data: Dict) -> Dict:
        """Get detailed statistics for project project"""
        try:
            project_label = f"project-{project_data['index_number']}"
            all_issues = self.github.list_issues(self.org, self.repo_name)
            project_issues = [issue for issue in all_issues 
                            if any(label['name'] == project_label for label in issue.get('labels', []))]
            
            # Calculate detailed metrics
            total_issues = len(project_issues)
            open_issues = [i for i in project_issues if i['state'] == 'open']
            closed_issues = [i for i in project_issues if i['state'] == 'closed']
            
            # Get milestone-specific progress
            milestone_progress = self._calculate_milestone_progress(project_issues)
            
            return {
                'project_id': project_data['index_number'],
                'project_folder': f"projects/{project_data['index_number']}",
                'total_issues': total_issues,
                'open_issues': len(open_issues),
                'closed_issues': len(closed_issues),
                'progress_percentage': (len(closed_issues) / max(total_issues, 1)) * 100,
                'milestone_progress': milestone_progress,
                'has_recent_activity': self._check_recent_activity(project_issues)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {project_data['index_number']}: {e}")
            return {'project_id': project_data['index_number'], 'error': str(e)}
    
    def _calculate_milestone_progress(self, issues: List[Dict]) -> Dict:
        """Calculate progress for each milestone"""
        milestones = {
            'Literature Review': {'total': 0, 'completed': 0},
            'Implementation': {'total': 0, 'completed': 0}, 
            'Mid Evaluation': {'total': 0, 'completed': 0},
            'Final Evaluation': {'total': 0, 'completed': 0}
        }
        
        for issue in issues:
            title = issue['title'].lower()
            labels = [label['name'].lower() for label in issue.get('labels', [])]
            
            # Categorize issues by milestone
            if 'literature' in title or 'literature-review' in labels:
                milestone = 'Literature Review'
            elif 'implementation' in title or 'methodology' in title or 'implementation' in labels:
                milestone = 'Implementation'
            elif 'mid' in title or 'mid-evaluation' in labels:
                milestone = 'Mid Evaluation'
            elif 'final' in title or 'final-evaluation' in labels:
                milestone = 'Final Evaluation'
            else:
                continue  # Skip uncategorized issues
            
            milestones[milestone]['total'] += 1
            if issue['state'] == 'closed':
                milestones[milestone]['completed'] += 1
        
        # Calculate percentages
        for milestone in milestones:
            total = milestones[milestone]['total']
            completed = milestones[milestone]['completed']
            milestones[milestone]['percentage'] = (completed / max(total, 1)) * 100
        
        return milestones
    
    def _check_recent_activity(self, issues: List[Dict]) -> bool:
        """Check if there has been recent activity (within last 7 days)"""
        import datetime
        
        if not issues:
            return False
        
        # Get most recent issue update
        latest_update = issues[0]['updated_at']
        
        # Parse date and check if within last 7 days
        try:
            from datetime import datetime, timedelta
            latest_date = datetime.strptime(latest_update, '%Y-%m-%dT%H:%M:%SZ')
            week_ago = datetime.now() - timedelta(days=7)
            return latest_date > week_ago
        except:
            return False
    
    def generate_project_report(self, project_data: Dict) -> Dict:
        """Generate comprehensive report for individual project"""
        try:
            stats = self.get_project_project_stats(project_data)
            progress = self.update_project_progress(project_data)
            
            from datetime import datetime
            return {
                'project_info': project_data,
                'folder_path': f"projects/{project_data['index_number']}",
                'repository_stats': stats,
                'progress_info': progress,
                'recommendations': self._generate_recommendations(stats, progress),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report for {project_data['index_number']}: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, stats: Dict, progress: Dict) -> List[str]:
        """Generate recommendations based on project progress"""
        recommendations = []
        
        progress_pct = progress.get('progress_percentage', 0)
        has_activity = stats.get('has_recent_activity', False)
        
        if progress_pct == 0:
            recommendations.append("⚠️ Project not started. Immediate attention required.")
        elif progress_pct < 25:
            recommendations.append("📚 Focus on completing literature review.")
        elif progress_pct < 50:
            recommendations.append("🔧 Continue with methodology and implementation.")
        elif progress_pct < 75:
            recommendations.append("📊 Prepare for mid-evaluation checkpoint.")
        else:
            recommendations.append("✅ Good progress. Focus on final deliverables.")
        
        if not has_activity:
            recommendations.append("⏰ No recent activity detected. Check-in recommended.")
        
        open_issues = stats.get('open_issues', 0)
        if open_issues > 5:
            recommendations.append(f"📋 High number of open issues ({open_issues}). Consider prioritization.")
        
        return recommendations
    
    def _generate_project_readme(self, project_data: Dict) -> str:
        """Generate README template for project folder"""
        return f"""# Research Project - {project_data['index_number']}

**project:** {project_data['index_number']}  
**Research Area:** {project_data['research_area']}  
**Email:** {project_data['email']}  
**GitHub:** @{project_data.get('github_username', 'N/A')}

## Project Structure

```
{project_data['index_number']}/
├── README.md              # This file
├── docs/                  # Documentation and reports
│   ├── literature_review.md
│   ├── methodology.md
│   ├── mid_report.md
│   └── final_paper.md
├── src/                   # Source code
├── data/                  # Datasets
├── results/               # Experimental results
└── requirements.txt       # Dependencies
```

## Milestones

- [ ] **Week 4:** Literature Review
- [ ] **Week 8:** Methodology & Implementation
- [ ] **Week 10:** Mid Evaluation
- [ ] **Week 16:** Final Evaluation

## Progress Tracking

Track your progress using GitHub Issues with label `project-{project_data['index_number']}`.

## Getting Started

1. Update this README with your specific project details
2. Complete the literature review in `docs/literature_review.md`
3. Add your code to `src/` folder
4. Update progress through GitHub Issues

---
*Generated automatically by GitHub Research Project Manager*
"""
    
    def _generate_literature_template(self) -> str:
        """Generate literature review template"""
        return """# Literature Review

## Abstract

Brief summary of your literature review findings.

## Introduction

Background and context of your research area.

## Related Work

### Category 1: [Topic Area]

- **Paper 1:** Author et al. (Year). Title. Venue. 
  - Key findings:
  - Limitations:
  
- **Paper 2:** Author et al. (Year). Title. Venue.
  - Key findings:
  - Limitations:

### Category 2: [Topic Area]

[Continue with more papers...]

## Research Gaps

Identify gaps in current research that your project will address.

## Methodology

Proposed approach based on literature analysis.

## References

[Add your references here in standard format]

---
*Update this document as you progress through your literature review*
"""

