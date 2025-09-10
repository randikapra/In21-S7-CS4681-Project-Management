import logging
from typing import Dict, List, Optional
from .github_client import GitHubClient

logger = logging.getLogger(__name__)

class StudentManager:
    def __init__(self, config: Dict):
        self.config = config
        self.github = GitHubClient(config['github']['token'])
        self.org = config['github']['organization']
        self.repo_name = config['repository']['name']
        
    def create_student_issues(self, project_data: Dict) -> Dict:
        """Create milestone tracking issues for individual student"""
        try:
            project_folder = f"projects/{project_data['index_number']}-{project_data['research_area'].replace(' ', '-')}"
            project_label = f"student-{project_data['index_number']}"
            
            # Create milestone issues
            milestones = self._get_milestone_templates(project_data, project_folder, project_label)
            
            created_issues = []
            for milestone in milestones:
                try:
                    issue_number = self.github.create_issue(
                        org=self.org,
                        repo=self.repo_name,
                        title=milestone['title'],
                        body=milestone['body'],
                        labels=milestone['labels']
                    )
                    
                    if issue_number:
                        created_issues.append({
                            'number': issue_number,
                            'title': milestone['title'],
                            'type': milestone['type']
                        })
                        logger.debug(f"Created issue: {milestone['title']}")
                        
                except Exception as e:
                    logger.warning(f"Failed to create issue {milestone['title']}: {e}")
            
            return {
                'status': 'success',
                'student': project_data,
                'issues_created': created_issues,
                'project_label': project_label
            }
            
        except Exception as e:
            logger.error(f"Failed to create issues for {project_data['index_number']}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'student': project_data
            }

    def _get_milestone_templates(self, project_data: Dict, project_folder: str, project_label: str) -> List[Dict]:
        """Get milestone issue templates"""
        return [
            {
                'title': f"📋 Research Proposal - {project_data['index_number']}",
                'type': 'research_proposal',
                'body': f"""**Student:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Research Proposal Requirements:
- [ ] Problem statement and motivation
- [ ] Preliminary literature review
- [ ] Proposed methodology outline
- [ ] Expected outcomes and timeline
- [ ] Resource requirements

**Deliverable:** `{project_folder}/docs/research_proposal.md`
**Due Date:** Week 4
**Weight:** 15%

**Submission Instructions:**
1. Complete the research proposal document
2. Commit changes to your folder
3. Comment on this issue with "Ready for Review"
4. Tag supervisors: {self._get_supervisor_tags()}
""",
                'labels': ['research-proposal', project_label, 'milestone', 'week-4']
            },
            {
                'title': f"📚 Literature Review - {project_data['index_number']}",
                'type': 'literature_review',
                'body': f"""**Student:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Literature Review Requirements:
- [ ] Comprehensive survey of relevant literature (minimum 20 papers)
- [ ] Identification of research gaps
- [ ] Theoretical framework development
- [ ] Bibliography in standard format
- [ ] Critical analysis of existing work

**Deliverable:** `{project_folder}/docs/literature_review.md`
**Due Date:** Week 5
**Weight:** 20%

**Quality Criteria:**
- Recent publications (last 5 years preferred)
- Relevant high-impact venues
- Clear categorization of related work
- Gap analysis leading to your research question
""",
                'labels': ['literature-review', project_label, 'milestone', 'week-5']
            },
            {
                'title': f"🔧 Methodology & Implementation - {project_data['index_number']}",
                'type': 'implementation',
                'body': f"""**Student:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Implementation Requirements:
- [ ] Detailed methodology documentation
- [ ] Working prototype/proof of concept
- [ ] Data preprocessing pipeline
- [ ] Baseline model implementation
- [ ] Evaluation framework setup
- [ ] Code documentation and comments

**Deliverables:** 
- `{project_folder}/docs/methodology.md`
- Working code in `{project_folder}/src/`
- `{project_folder}/requirements.txt` updated

**Due Date:** Week 8
**Weight:** 25%

**Technical Requirements:**
- Clean, well-documented code
- Reproducible experiments
- Version control best practices
- README with setup instructions
""",
                'labels': ['implementation', project_label, 'milestone', 'week-8']
            },
            {
                'title': f"📊 Final Evaluation - {project_data['index_number']}",
                'type': 'final_evaluation',
                'body': f"""**Student:** {project_data['index_number']}
**Research Area:** {project_data['research_area']}
**Folder:** `{project_folder}/`

### Final Evaluation Requirements:
- [ ] Complete experimental results
- [ ] Comprehensive analysis and discussion  
- [ ] Final research paper (8000-10000 words)
- [ ] Code repository with full documentation
- [ ] Presentation slides
- [ ] Demo/video demonstration

**Deliverables:**
- `{project_folder}/docs/final_report.md`
- Complete codebase in `{project_folder}/src/`
- Results and analysis in `{project_folder}/results/`
- Presentation materials

**Due Date:** Week 12
**Weight:** 40%

**Assessment Criteria:**
- Technical innovation and correctness
- Experimental rigor and validation
- Quality of analysis and insights
- Clear communication and presentation
- Code quality and reproducibility
""",
                'labels': ['final-evaluation', project_label, 'milestone', 'week-12']
            }
        ]

    def _get_supervisor_tags(self) -> str:
        """Get supervisor GitHub mentions"""
        supervisors_data = self.config.get('supervisors', {}).get('supervisors', [])
        supervisor_tags = []
        
        for supervisor in supervisors_data:
            username = supervisor.get('github_username')
            if username:
                supervisor_tags.append(f"@{username}")
        
        return " ".join(supervisor_tags) if supervisor_tags else "@supervisor"

    def track_project_progress(self, project_data: Dict) -> Dict:
        """Track individual student progress"""
        try:
            project_label = f"student-{project_data['index_number']}"
            
            # Get all issues for this student
            all_issues = self.github.list_issues(
                org=self.org, 
                repo=self.repo_name,
                labels=[project_label],
                state='all'
            )
            
            # Calculate progress metrics
            total_milestones = len([i for i in all_issues if 'milestone' in [l['name'] for l in i.get('labels', [])]])
            completed_milestones = len([i for i in all_issues if i['state'] == 'closed' and 'milestone' in [l['name'] for l in i.get('labels', [])]])
            
            progress_percentage = (completed_milestones / max(total_milestones, 1)) * 100
            current_phase = self._determine_current_phase(all_issues)
            
            return {
                'student_id': project_data['index_number'],
                'project_folder': f"projects/{project_data['index_number']}-{project_data['research_area'].replace(' ', '-')}",
                'total_milestones': total_milestones,
                'completed_milestones': completed_milestones,
                'progress_percentage': progress_percentage,
                'current_phase': current_phase,
                'recent_activity': self._check_recent_activity(all_issues),
                'issues_summary': self._summarize_issues(all_issues)
            }
            
        except Exception as e:
            logger.error(f"Failed to track progress for {project_data['index_number']}: {e}")
            return {
                'student_id': project_data['index_number'],
                'error': str(e)
            }