# simpleApply

Automatically generate tailored CVs and cover letters for job applications using AI to match your skills with job requirements.

## Features

- Parses job offers and extracts key requirements
- Matches your skills and experience to job requirements
- Selects 2 most relevant projects from your portfolio
- Generates personalized CVs and cover letters in HTML

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