# AI-Powered Job Application System

An intelligent system that automatically generates tailored CVs and cover letters by analyzing job offers and matching your skills and experience using AI.

## 🚀 Features

- **Smart Job Analysis**: Extracts key requirements from job offers using Claude AI
- **Intelligent Skills Matching**: Matches your skills with job requirements
- **Project Selection**: Automatically selects your 2 most relevant side projects
- **Dynamic Document Generation**: Creates personalized CVs and cover letters
- **HTML Template System**: Uses customizable HTML templates for professional output
- **YAML Configuration**: Easy-to-maintain user profile configuration

## 📋 System Overview

The system follows a clean pipeline architecture:

```
Job Offer Input → Extract Requirements → Match Skills → Select Projects → Generate Documents
```

### Core Components

1. **Job Offer Parser** (`src/job_parser.py`) - Extracts key information from job offers
2. **Skills Matcher** (`src/skills_matcher.py`) - Matches user skills with job requirements
3. **Project Selector** (`src/project_selector.py`) - Chooses most relevant side projects
4. **Document Generator** (`src/document_generator.py`) - Fills HTML templates with personalized content

## 🛠️ Installation

### Prerequisites

- Python 3.12+
- OpenAI API key (for Claude AI integration)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd simpleApply
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Configure your profile**
   ```bash
   # Edit config/user_profile.yaml with your information
   ```

## 🎯 Usage

### Basic Usage

```bash
# Generate CV and cover letter for a job
python src/main.py --job-file examples/job_offers/software_engineer.txt

# Generate only CV
python src/main.py --job-file examples/job_offers/data_scientist.txt --cv-only

# Generate only cover letter
python src/main.py --job-file examples/job_offers/frontend_dev.txt --cover-letter-only

# Specify custom output directory
python src/main.py --job-file job_offer.txt --output-dir ./applications/company_name
```

### Advanced Usage

```bash
# Use custom user profile
python src/main.py --job-file job_offer.txt --profile config/custom_profile.yaml

# Generate with specific project count
python src/main.py --job-file job_offer.txt --max-projects 3

# Verbose output for debugging
python src/main.py --job-file job_offer.txt --verbose
```

## 📁 Input/Output Formats

### Input Formats

#### Job Offer File (.txt)
Plain text file containing the job description:

```
Software Engineer - Full Stack
Company: TechCorp Inc.

We are looking for a skilled Full Stack Developer with experience in:
- Python and Django/Flask
- React and TypeScript
- PostgreSQL and Redis
- AWS cloud services
- RESTful API development

Requirements:
- 3+ years of experience
- Strong problem-solving skills
- Experience with agile methodologies
```

#### User Profile (YAML)
```yaml
personal_info:
  name: "John Doe"
  email: "john.doe@email.com"
  phone: "+1-555-0123"

skills:
  programming_languages:
    - name: "Python"
      years_experience: 5
      proficiency: "Expert"
    - name: "JavaScript"
      years_experience: 4
      proficiency: "Advanced"

side_projects:
  - name: "E-commerce Platform"
    description: "Full-stack web application built with Django and React"
    technologies: ["Python", "Django", "React", "PostgreSQL"]
    impact: "Improved user engagement by 40%"
```

### Output Formats

The system generates:

1. **CV** (`cv.html`) - Tailored resume highlighting relevant skills and projects
2. **Cover Letter** (`cover_letter.html`) - Personalized cover letter addressing job requirements
3. **Analysis Report** (`analysis.json`) - Detailed matching analysis and reasoning

### Expected Output Structure

```
output/
├── cv.html
├── cover_letter.html
└── analysis.json
```

## 🧪 Testing

### Run All Tests
```bash
uv run pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Test with Example Data
```bash
# Test with provided examples
python src/main.py --job-file examples/job_offers/software_engineer.txt
python src/main.py --job-file examples/job_offers/data_scientist.txt
python src/main.py --job-file examples/job_offers/frontend_dev.txt
```

## 📚 Examples

### Example 1: Software Engineer Position

**Input**: `examples/job_offers/software_engineer.txt`
```
Senior Software Engineer - Backend
Location: Remote

We're seeking a talented Senior Software Engineer to join our backend team.

Key Requirements:
- 5+ years Python development experience
- Experience with Django/Flask frameworks
- Knowledge of PostgreSQL and Redis
- AWS cloud services experience
- RESTful API design and development
- Strong problem-solving skills

Nice to have:
- Docker and Kubernetes experience
- CI/CD pipeline experience
- Microservices architecture knowledge
```

**Command**:
```bash
python src/main.py --job-file examples/job_offers/software_engineer.txt
```

**Expected Output**:
- CV highlighting Python, Django, PostgreSQL experience
- Selected projects demonstrating backend development skills
- Cover letter addressing specific requirements

### Example 2: Data Scientist Role

**Input**: `examples/job_offers/data_scientist.txt`
```
Data Scientist - Machine Learning
Company: DataTech Solutions

Join our ML team to build predictive models and data pipelines.

Requirements:
- PhD/Masters in Data Science, Statistics, or related field
- 3+ years experience with Python (pandas, scikit-learn, TensorFlow)
- Experience with SQL and data warehousing
- Statistical analysis and hypothesis testing
- Machine learning model deployment experience

Preferred:
- Cloud platforms (AWS, GCP, Azure)
- Big data tools (Spark, Hadoop)
- Visualization tools (Tableau, PowerBI)
```

**Expected Output**:
- CV emphasizing ML projects and statistical analysis
- Projects showcasing data science and ML implementations
- Cover letter demonstrating analytical thinking

## 🔧 Troubleshooting

### Common Issues

#### 1. OpenAI API Key Issues
**Problem**: `OpenAI API key not found` or `Authentication failed`

**Solution**:
- Verify `.env` file exists and contains `OPENAI_API_KEY=your_key_here`
- Check API key is valid and has sufficient credits
- Ensure no extra spaces or quotes around the key

#### 2. Template Not Found Errors
**Problem**: `Template file not found: templates/cv_template.html`

**Solution**:
- Verify template files exist in `templates/` directory
- Check file permissions (should be readable)
- Ensure working directory is project root

#### 3. YAML Configuration Errors
**Problem**: `yaml.scanner.ScannerError` or `KeyError` in user profile

**Solution**:
- Validate YAML syntax using online YAML validator
- Check required fields are present (see `config/user_profile.yaml` example)
- Ensure proper indentation (use spaces, not tabs)

#### 4. Virtual Environment Issues
**Problem**: `ModuleNotFoundError` for installed packages

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv pip install -r requirements.txt

# Verify installation
uv pip list
```

#### 5. Permission Errors
**Problem**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Check file permissions
ls -la templates/ config/ output/

# Fix permissions if needed
chmod 644 templates/*.html config/*.yaml
chmod 755 src/ tests/
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Enable debug output
python src/main.py --job-file job_offer.txt --verbose

# Check log files
tail -f logs/application.log
```

### Performance Issues

If processing is slow:

1. **Check API rate limits**: OpenAI has rate limiting
2. **Reduce project count**: Use `--max-projects 1` for faster processing
3. **Simplify job offers**: Remove excessive detail from job descriptions
4. **Check internet connection**: AI API calls require stable internet

### Getting Help

1. **Check logs**: Look in `logs/` directory for detailed error messages
2. **Validate configuration**: Use `python src/validate_config.py` to check setup
3. **Test components**: Run individual tests to isolate issues
4. **Create minimal example**: Test with simple job offer and basic profile

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`uv run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for Claude AI integration
- Pydantic for robust data validation
- The open-source community for excellent Python tools