"""
Tests for the template processor module.
"""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch

from src.template_processor import TemplateProcessor, create_template_processor
from src.models import JobOffer, MatchedSkills, SelectedProjects, UserProfile, PersonalInfo, Project


@pytest.fixture
def sample_job_offer():
    """Sample job offer for testing."""
    return JobOffer(
        job_title="Senior Python Developer",
        company_name="TechCorp Inc",
        skills_required=["Python", "Django", "PostgreSQL", "Docker"],
        location="Remote",
        description="We are looking for a senior Python developer..."
    )


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing."""
    return UserProfile(
        personal_info=PersonalInfo(name="John Doe", email="john@example.com"),
        experiences=[],
        skills=["Python", "Django", "JavaScript", "Docker"],
        education=[],
        projects=[],
        languages=["English", "Spanish"],
        achievements=["Built scalable web applications", "Led development team"],
        hobbies=["Programming", "Reading"]
    )


@pytest.fixture
def sample_matched_skills():
    """Sample matched skills for testing."""
    return MatchedSkills(
        user_skills=["Python", "Django", "JavaScript", "Docker"],
        job_skills=["Python", "Django", "PostgreSQL", "Docker"],
        matched_skills=["Python", "Django", "Docker"],
        relevant_technologies=["Python", "Django", "Docker", "PostgreSQL", "JavaScript"],
        relevant_achievements=["Built scalable web applications", "Implemented containerized deployments"]
    )


@pytest.fixture
def sample_selected_projects():
    """Sample selected projects for testing."""
    return SelectedProjects(
        project1=Project(
            title="E-commerce Platform",
            description="A full-stack e-commerce platform built with Django and React, featuring user authentication, payment processing, and real-time inventory management.",
            technologies=["Python", "Django", "React", "PostgreSQL"],
            url="https://github.com/user/ecommerce",
            start_date="2023-01",
            end_date="2023-06",
            status="completed"
        ),
        project2=Project(
            title="Data Analytics Dashboard",
            description="Interactive dashboard for business analytics using Python, pandas, and visualization libraries to process large datasets and generate insights.",
            technologies=["Python", "pandas", "plotly", "Flask"],
            url="https://github.com/user/analytics",
            start_date="2023-07",
            end_date="2023-12",
            status="completed"
        ),
        selection_reasoning="Both projects demonstrate strong Python and web development skills relevant to the position."
    )


@pytest.fixture
def template_processor():
    """Template processor instance for testing."""
    return TemplateProcessor(templates_dir=Path("test_templates"))


class TestTemplateProcessor:
    """Test cases for TemplateProcessor class."""

    def test_load_template_success(self, template_processor):
        """Test successful template loading."""
        mock_content = "<html><body>Test template</body></html>"

        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch.object(Path, "exists", return_value=True):
                result = template_processor.load_template("test.html")
                assert result == mock_content

    def test_load_template_file_not_found(self, template_processor):
        """Test template loading when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Template not found"):
                template_processor.load_template("nonexistent.html")

    def test_load_template_io_error(self, template_processor):
        """Test template loading with IO error."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(IOError, match="Failed to read template"):
                    template_processor.load_template("test.html")

    def test_replace_placeholders_html_comments(self, template_processor):
        """Test placeholder replacement for HTML comments."""
        template = "<html><!-- JOB TITLE --></html>"
        replacements = {"JOB TITLE": "Software Engineer"}

        result = template_processor.replace_placeholders(template, replacements)
        assert result == "<html>Software Engineer</html>"

    def test_replace_placeholders_direct_placeholders(self, template_processor):
        """Test placeholder replacement for direct placeholders."""
        template = "<html>{COMPANY_NAME}</html>"
        replacements = {"COMPANY_NAME": "TechCorp"}

        result = template_processor.replace_placeholders(template, replacements)
        assert result == "<html>TechCorp</html>"

    def test_replace_placeholders_case_insensitive(self, template_processor):
        """Test case insensitive placeholder replacement."""
        template = "<html><!-- job title --></html>"
        replacements = {"JOB TITLE": "Software Engineer"}

        result = template_processor.replace_placeholders(template, replacements)
        assert result == "<html>Software Engineer</html>"

    def test_generate_cv_replacements(self, template_processor, sample_job_offer,
                                   sample_user_profile, sample_matched_skills, sample_selected_projects):
        """Test CV replacements generation."""
        replacements = template_processor.generate_cv_replacements(
            sample_job_offer, sample_user_profile, sample_matched_skills, sample_selected_projects
        )

        assert replacements["JOB TITLE"] == "Senior Python Developer"
        assert replacements["TITLE OF THE SIDE PROJECT 1"] == "E-commerce Platform"
        assert replacements["TITLE OF THE SIDE PROJECT 2"] == "Data Analytics Dashboard"
        assert "Python" in replacements["20 relevant skills/tools"]

    def test_generate_cover_letter_replacements(self, template_processor, sample_job_offer,
                                              sample_user_profile, sample_matched_skills, sample_selected_projects):
        """Test cover letter replacements generation."""
        replacements = template_processor.generate_cover_letter_replacements(
            sample_job_offer, sample_user_profile, sample_matched_skills, sample_selected_projects
        )

        assert replacements["Insert Company Name"] == "TechCorp Inc"
        assert replacements["Insert Job Title"] == "Senior Python Developer"
        assert "TechCorp Inc" in replacements["Insert specific detail about the company or role that excites you"]
        assert "Python" in replacements["Insert Relevant Skills"]

    def test_truncate_description_returns_original(self, template_processor):
        """Test description truncation returns original unchanged."""
        description = "This is a test description that should be returned as-is."
        result = template_processor._truncate_description(description, 50, 150)
        assert result == description

    def test_truncate_description_long_text(self, template_processor):
        """Test description with long text returns original."""
        description = "This is a very long description that definitely exceeds the maximum character limit and needs to be truncated to fit within the specified range for the project description field."
        result = template_processor._truncate_description(description, 50, 100)
        assert result == description

    def test_truncate_description_short_text(self, template_processor):
        """Test description with short text returns original."""
        description = "Short desc"
        result = template_processor._truncate_description(description, 50, 150)
        assert result == description

    def test_process_templates_success(self, template_processor, sample_job_offer,
                                     sample_user_profile, sample_matched_skills, sample_selected_projects):
        """Test successful template processing."""
        cv_template = "<html><!-- JOB TITLE --></html>"
        cover_letter_template = "<html><!-- Insert Company Name --></html>"

        with patch.object(template_processor, "load_template") as mock_load:
            mock_load.side_effect = [cv_template, cover_letter_template]

            result = template_processor.process_templates(
                sample_job_offer, sample_user_profile, sample_matched_skills, sample_selected_projects
            )

            assert result.cv_html == "<html>Senior Python Developer</html>"
            assert result.cover_letter_html == "<html>TechCorp Inc</html>"
            assert result.job_offer == sample_job_offer
            assert result.matched_skills == sample_matched_skills
            assert result.selected_projects == sample_selected_projects

    def test_process_templates_file_error(self, template_processor, sample_job_offer,
                                        sample_user_profile, sample_matched_skills, sample_selected_projects):
        """Test template processing with file error."""
        with patch.object(template_processor, "load_template", side_effect=FileNotFoundError("Template not found")):
            with pytest.raises(IOError, match="Template processing failed"):
                template_processor.process_templates(
                    sample_job_offer, sample_user_profile, sample_matched_skills, sample_selected_projects
                )


def test_create_template_processor():
    """Test template processor factory function."""
    processor = create_template_processor("custom_templates")
    assert isinstance(processor, TemplateProcessor)
    assert processor.templates_dir == Path("custom_templates")


def test_create_template_processor_default():
    """Test template processor factory with default directory."""
    processor = create_template_processor()
    assert isinstance(processor, TemplateProcessor)
    assert processor.templates_dir == Path("templates")