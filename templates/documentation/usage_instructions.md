# Student Usage Instructions

## Getting Started with Your Project

### 1. Initial Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/{ORGANIZATION}/{MAIN_REPO_NAME}.git
   cd {MAIN_REPO_NAME}
   ```

2. **Navigate to Your Project Folder**
   ```bash
   cd projects/{STUDENT_INDEX}-{RESEARCH_AREA}
   ```

3. **Set Up Your Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### 2. Project Workflow

#### Week 1-3: Research Phase
1. Complete your research proposal in `docs/research_proposal.md`
2. Begin literature review in `docs/literature_review.md`
3. Create your first progress report issue

#### Week 4-6: Planning Phase
1. Finalize your methodology in `docs/methodology.md`
2. Set up your development environment
3. Create initial code structure in `src/`

#### Week 7-12: Implementation Phase
1. Implement your solution in `src/`
2. Document experiments in `experiments/`
3. Store results in `results/`
4. Create weekly progress issues

#### Week 13-16: Finalization Phase
1. Complete final report
2. Prepare presentation materials
3. Clean up code and documentation

### 3. GitHub Workflow

#### Creating Progress Reports
1. Go to the main repository Issues tab
2. Click "New Issue"
3. Select "Progress Report" template
4. Fill in your progress details
5. Tag your supervisors (@{SUPERVISOR_USERNAME})

#### Submitting Milestones
1. Complete your milestone deliverable
2. Commit and push your changes
3. Create a new issue using "Milestone Submission" template
4. Include links to relevant files and commits

#### Daily Development Workflow
```bash
# Start your work session
git pull origin main
git checkout -b feature/your-feature-name

# Make your changes
# ... edit files ...

# Commit your changes
git add .
git commit -m "Descriptive commit message"
git push origin feature/your-feature-name

# Create pull request for major changes (optional but recommended)
```

### 4. File Organization Best Practices

#### Source Code (`src/`)
- Keep your main implementation files here
- Use clear, descriptive filenames
- Include docstrings and comments
- Follow Python PEP 8 style guide

#### Data (`data/`)
- Store your datasets here
- Include data description files
- Use version control for small datasets only
- Document data sources and preprocessing steps

#### Experiments (`experiments/`)
- Store experiment scripts and configurations
- Use descriptive names like `experiment_01_baseline.py`
- Include results and logs
- Document experiment parameters

#### Documentation (`docs/`)
- Keep all written reports here
- Use consistent formatting
- Regular updates are expected
- Include figures and tables in subdirectories

### 5. Communication Guidelines

#### With Supervisors
- Create issues for questions and progress updates
- Tag supervisors using @username
- Be specific about what help you need
- Include relevant code/files in your questions

#### Weekly Progress Reports
- Submit every Friday by 5 PM
- Include what you accomplished
- Mention any blockers or challenges
- Outline next week's plans

#### Milestone Submissions
- Submit on time according to course schedule
- Include all required deliverables
- Provide clear documentation
- Be prepared to discuss your work

### 6. Common Issues and Solutions

#### "I can't find my project folder"
- Check that you're in the right repository
- Your folder is named `{STUDENT_INDEX}-[research-area-with-dashes]`
- Contact support if still having issues

#### "Git is confusing"
- Use GitHub Desktop for a visual interface
- Ask for help in office hours
- Check the Git documentation in the main docs folder

#### "My code isn't working"
- Check your requirements.txt
- Ensure you're in the right virtual environment
- Create an issue with the "support" label

#### "I don't understand the assignment"
- Review the project guidelines in docs/
- Attend office hours
- Ask specific questions in issues

### 7. Academic Integrity Reminders

- All code must be your own work
- Cite any external libraries or code snippets
- Acknowledge help from classmates or online resources
- Use proper academic citation format
- When in doubt, ask your supervisor

### 8. Tips for Success

- **Start Early:** Don't wait until deadlines approach
- **Commit Often:** Small, frequent commits are better than large ones
- **Document Everything:** Future you will thank present you
- **Ask Questions:** Supervisors are here to help
- **Stay Organized:** Use the provided folder structure
- **Backup Your Work:** Git is your backup system

---

**Need Help?** Create an issue with the "support" label or contact your supervisor directly.