# simpleApply

Automatically generate tailored CVs and cover letters for job applications using AI to match your skills with job requirements.

## Features

- **AI-Powered Job Analysis** - Parses job postings and extracts key requirements using OpenAI GPT
- **Skill Matching** - Intelligently matches your skills and experience to job requirements
- **Project Selection** - Automatically selects the 2 most relevant projects from your portfolio
- **Document Generation** - Creates personalized CVs and cover letters in HTML and PDF formats
- **PDF Conversion** - Generates downloadable PDF versions with professional A4 formatting
- **Multilingual Support** - Auto-detects job posting language and generates documents in English, French, or Spanish
- **Application Tracking** - Maintains persistent history of all applications with matching rates and metrics
- **Cost Analytics** - Tracks OpenAI API usage and costs per application session
- **Interactive Web UI** - Streamlit-based dashboard for real-time preview and application management

## Installation

### Prerequisites

- Python 3.12+
- OpenAI API key

### Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Edit your profile
vim templates/user_profile.yaml
```

## Technology Stack

### Core
- **Python 3.12+** - Primary language with type hints
- **OpenAI API** - GPT models for intelligent job analysis and content generation
- **Pydantic v2** - Data validation and type safety across the pipeline

### Frontend & UI
- **Streamlit** - Interactive web application dashboard
- **Jinja2** - HTML template rendering engine
- **Plotly** - Cost analytics visualization

### Data & Processing
- **SQLite** - Application history and cost tracking database
- **Playwright** - Headless browser automation for HTML-to-PDF conversion
- **PyYAML** - User profile configuration parsing

### Development
- **pytest** - Unit and integration testing
- **python-dotenv** - Environment variable management

## Architecture

The application processes job applications through a sequential AI pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                             │
│        Job Posting + User Profile (YAML)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Job Parsing (OpenAI GPT)       │
        │  • Extract requirements         │
        │  • Detect language              │
        │  • Parse job titles             │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Skills Matching (OpenAI GPT)   │
        │  • Match user skills to job     │
        │  • Generate value contributions │
        │  • Calculate relevance score    │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Project Selection (OpenAI GPT) │
        │  • Rank portfolio projects      │
        │  • Select 2 most relevant       │
        │  • Generate reasoning           │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────────────┐
        │  Document Generation                   │
        │  • Render HTML templates (Jinja2)     │
        │  • Localize dates & language           │
        │  • Convert to PDF (Playwright)         │
        └────────────────┬───────────────────────┘
                         │
        ┌────────────────▼────────────────────────┐
        │  Output & Persistence                  │
        │  • Save HTML files                     │
        │  • Generate downloadable PDFs          │
        │  • Store in SQLite database            │
        │  • Track costs and metrics             │
        └────────────────────────────────────────┘
```

### Core Modules

| Module | Responsibility |
|--------|-----------------|
| `job_parser.py` | Extracts job requirements and language detection |
| `skills_matcher.py` | Matches user skills to job requirements with AI-generated value contributions |
| `project_selector.py` | Ranks and selects 2 most relevant portfolio projects |
| `template_processor.py` | Renders HTML documents with Jinja2 templates and localization |
| `database.py` | SQLite persistence for application history and metrics |
| `cost_tracker.py` | Monitors and calculates OpenAI API costs per operation |
| `translation_loader.py` | Manages multilingual translation dictionaries |

## Usage

```bash
# Generate CV and cover letter
python src/main.py job_offer.txt

# CLI mode
streamlit run streamlit_app.py

# See all options
python src/main.py --help
```

## Input/Output

**Input**: Job offer text file and YAML user profile
**Output**: CV and cover letter in HTML format saved to `output/`

## Testing

```bash
uv run pytest
```

## Troubleshooting

**OpenAI API key error**: Check `.env` has valid `OPENAI_API_KEY`

**YAML errors**: Validate YAML syntax and ensure proper indentation (spaces only)

**ModuleNotFoundError**: Activate virtual environment and run `uv pip install -r requirements.txt`

## License

MIT