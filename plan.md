# AI-Powered Job Application System - Implementation Plan

## System Overview
This system will automatically generate tailored CVs and cover letters by analyzing job offers and matching user skills/experience. The system leverages AI to extract job requirements and dynamically select relevant user experiences and projects.

## Architecture Design

### Core Components
1. **Job Offer Parser** - Extracts key information from job offers
2. **Skills Matcher** - Matches user skills with job requirements
3. **Project Selector** - Chooses 2 most relevant side projects
4. **Document Generator** - Fills HTML templates with personalized content

### Data Flow
```
Job Offer Input → Extract Requirements → Match Skills → Select Projects → Generate Documents
```

### Technology Stack
- **Backend**: Python 3.12 with Pydantic models
- **AI/LLM**: Claude 3 for intelligent parsing and matching
- **Document Processing**: HTML template processing
- **Data**: YAML configuration, HTML templates

## Step-by-Step Implementation Prompts

### Step 1: Project Setup
**Prompt**: "Set up the basic project structure with Python virtual environment, create main application file, and install required dependencies (pydantic, openai/anthropic, pyyaml, jinja2). Create a simple main.py entry point."

**Expected Outcome**: Basic project structure with dependencies installed

### Step 2: Data Models Creation
**Prompt**: "Create Pydantic models for:
- JobOffer (job_title, company_name, skills_required, location, description)
- UserProfile (load from templates/user_profile.yaml structure)
- MatchedSkills (user_skills, job_skills, matched_skills)
- SelectedProjects (project1, project2)
Create a models.py file with these models."

**Expected Outcome**: Typed data models matching the YAML structure

### Step 3: Job Offer Parser
**Prompt**: "Create a job_parser.py module with a function that takes a job offer text as input and uses Claude/AI to extract:
- job_title
- company_name
- skills_required (list)
- location
- key responsibilities
Return a JobOffer Pydantic model. Include proper error handling."

**Expected Outcome**: AI-powered job parsing functionality

### Step 4: Skills Matching Engine
**Prompt**: "Create a skills_matcher.py module that:
- Takes a JobOffer and UserProfile as input
- Uses AI to intelligently match user skills with job requirements
- Returns relevant skills and technologies that should be highlighted
- Includes logic to select the most relevant experience achievements
Don't hardcode skill matching - let the AI determine relevance."

**Expected Outcome**: Intelligent skills matching using AI

### Step 5: Project Selection Logic
**Prompt**: "Create a project_selector.py module that:
- Takes JobOffer and UserProfile.projects as input
- Uses AI to select the 2 most relevant side projects based on:
  - Technology stack alignment
  - Project relevance to job requirements
  - Demonstration of required skills
- Returns SelectedProjects model with project details for CV/cover letter"

**Expected Outcome**: AI-driven project selection logic

### Step 6: Template Processing Engine
**Prompt**: "Create a template_processor.py module that:
- Loads HTML templates from templates/ folder
- Replaces placeholder variables in CV template with actual user data
- Replaces placeholder variables in cover letter template
- Uses the matched skills, selected projects, and job information
- Returns processed HTML content for both documents"

**Expected Outcome**: Template processing with dynamic content insertion

### Step 7: Main Application Logic
**Prompt**: "Update main.py to:
- Accept job offer input (text or file)
- Load user profile from templates/user_profile.yaml
- Orchestrate the entire pipeline:
  1. Parse job offer
  2. Match skills
  3. Select projects
  4. Process templates
  5. Output generated CV and cover letter HTML files
- Include proper error handling and user feedback"

**Expected Outcome**: Complete working application pipeline

### Step 8: CLI Interface
**Prompt**: "Add a command-line interface to main.py that:
- Accepts job offer text as argument or from file
- Provides options for output directory
- Shows progress during processing
- Outputs success/error messages
- Saves generated files with meaningful names (CV_[company]_[job_title].html)"

**Expected Outcome**: User-friendly CLI interface

### Step 9: Testing & Validation
**Prompt**: "Create a test job offer and run the complete system end-to-end. Verify that:
- Job parsing extracts correct information
- Skills matching is relevant and accurate
- Selected projects make sense for the job
- Generated CV and cover letter contain proper information
- HTML output is valid and properly formatted
Fix any issues found during testing."

**Expected Outcome**: Tested and validated working system

### Step 10: Documentation & Examples
**Prompt**: "Create a README.md with:
- System overview and features
- Installation instructions
- Usage examples with sample commands
- Expected input/output formats
- Troubleshooting guide
Add example job offer texts for testing."

**Expected Outcome**: Complete documentation for easy usage

## Key Implementation Notes

### Template Placeholders to Fill
**CV Template**:
- `<!-- FULL_NAME -->` - From user_profile.personal_info.name
- `<!-- EMAIL -->` - From user_profile.personal_info.email
- `<!-- JOB TITLE -->` - From job offer parsing
- `<!-- TITLE OF THE SIDE PROJECT 1 -->` - From project selection
- `<!-- DESCRIPTION OF THE SIDE PROJECT 1 -->` - From project selection
- `<!-- TITLE OF THE SIDE PROJECT 2 -->` - From project selection
- `<!-- DESCRIPTION OF THE SIDE PROJECT 2 -->` - From project selection
- `<!-- 3 RELEVANT TECHNICAL SKILLS -->` - From skills matching
- `<!-- 20 relevant skills/tools -->` - From skills matching

**Cover Letter Template**:
- `<!-- Insert Date -->` - Current date
- `<!-- Insert Company Name -->` - From job parsing
- `<!-- Insert Job Title -->` - From job parsing
- `<!-- Insert Achievement 1/2/3 -->` - From skills matching
- `<!-- Insert Relevant Skills -->` - From skills matching
- Various company-specific customizations

### AI Prompting Strategy
- Use structured prompts with clear output format requirements
- Include examples in prompts for better AI understanding
- Request JSON output for easy parsing
- Include validation and error handling for AI responses

### Quality Assurance
- Validate that all placeholders are filled
- Ensure descriptions fit length requirements (100-165 chars for projects)
- Verify skill relevance and avoid generic matching
- Check that selected projects truly align with job requirements

## Expected File Structure
```
simpleApply/
├── main.py                 # Main application entry point
├── models.py              # Pydantic data models
├── job_parser.py          # Job offer parsing logic
├── skills_matcher.py      # Skills matching engine
├── project_selector.py    # Project selection logic
├── template_processor.py  # HTML template processing
├── requirements.txt       # Python dependencies
├── README.md             # Documentation
├── templates/
│   ├── user_profile.yaml
│   ├── cv_template.html
│   └── cover_letter_template.html
└── output/               # Generated documents
```

This plan provides a clear roadmap for building a robust, AI-powered job application system that intelligently matches user profiles with job requirements while maintaining simplicity and avoiding hardcoded logic.