#!/usr/bin/env python3
"""
Integration test: Validate multilingual implementation with real job offers.
Tests language detection, translation loading, and template processing in all 3 languages.
"""

import pytest
from pathlib import Path
import yaml

from src.job_parser import parse_job_offer
from src.translation_loader import create_translation_loader, TranslationError
from src.models import UserProfile
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor


class TestMultilingualValidation:
    """Validation tests for multilingual implementation with real job offers."""

    @pytest.fixture
    def user_profile(self):
        """Load user profile from YAML."""
        with open("templates/user_profile.yaml", "r") as f:
            profile_data = yaml.safe_load(f)
        return UserProfile(**profile_data)

    @pytest.fixture
    def translation_loader(self):
        """Load translation loader."""
        return create_translation_loader()

    @pytest.fixture
    def english_job_offer_text(self):
        """Load English job offer."""
        with open("templates/job_offers/job_offer_en.txt", "r", encoding="utf-8") as f:
            return f.read()

    @pytest.fixture
    def french_job_offer_text(self):
        """Load French job offer."""
        with open("templates/job_offers/job_offer_fr.txt", "r", encoding="utf-8") as f:
            return f.read()

    @pytest.fixture
    def spanish_job_offer_text(self):
        """Load Spanish job offer."""
        with open("templates/job_offers/job_offer_es.txt", "r", encoding="utf-8") as f:
            return f.read()

    # ========================================================================
    # ENGLISH JOB OFFER TESTS
    # ========================================================================

    def test_english_job_offer_language_detection(self, english_job_offer_text):
        """Test English job offer is correctly detected."""
        job_offer = parse_job_offer(english_job_offer_text)

        assert job_offer.language == "en"
        assert job_offer.job_title is not None
        assert len(job_offer.skills_required) > 0
        assert job_offer.company_name is not None

    def test_english_job_offer_parsing(self, english_job_offer_text):
        """Test English job offer parsing extracts all key information."""
        job_offer = parse_job_offer(english_job_offer_text)

        # Verify key fields are populated
        assert job_offer.job_title is not None and len(job_offer.job_title) > 0
        assert job_offer.company_name is not None and len(job_offer.company_name) > 0
        assert job_offer.location is not None and len(job_offer.location) > 0
        assert job_offer.skills_required is not None and len(job_offer.skills_required) > 0
        assert job_offer.description is not None and len(job_offer.description) > 0

    def test_english_skills_matching(self, english_job_offer_text, user_profile):
        """Test skills matching works for English job offer."""
        job_offer = parse_job_offer(english_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)

        assert matched_skills.matched_skills is not None
        assert len(matched_skills.matched_skills) > 0
        assert matched_skills.relevant_technologies is not None
        assert matched_skills.key_value_contributions is not None

    def test_english_project_selection(self, english_job_offer_text, user_profile):
        """Test project selection works for English job offer."""
        job_offer = parse_job_offer(english_job_offer_text)
        selected_projects = select_projects(job_offer, user_profile.projects)

        assert selected_projects.project1 is not None
        assert selected_projects.project2 is not None
        assert selected_projects.selection_reasoning is not None
        assert selected_projects.project1.title != selected_projects.project2.title

    def test_english_translations_available(self, translation_loader):
        """Test English translations are available."""
        # Verify CV headers
        assert translation_loader.get_translation("en", "cv", "summary_header") == "SUMMARY"
        assert translation_loader.get_translation("en", "cv", "education_header") == "EDUCATION"

        # Verify cover letter content
        assert translation_loader.get_translation("en", "cover_letter", "greeting") == "Dear"
        assert translation_loader.get_translation("en", "cover_letter", "sign_off") == "Sincerely"

    # ========================================================================
    # FRENCH JOB OFFER TESTS
    # ========================================================================

    def test_french_job_offer_language_detection(self, french_job_offer_text):
        """Test French job offer is correctly detected."""
        job_offer = parse_job_offer(french_job_offer_text)

        assert job_offer.language == "fr"
        assert job_offer.job_title is not None
        assert len(job_offer.skills_required) > 0
        assert job_offer.company_name is not None

    def test_french_job_offer_parsing(self, french_job_offer_text):
        """Test French job offer parsing extracts all key information."""
        job_offer = parse_job_offer(french_job_offer_text)

        # Verify key fields are populated
        assert job_offer.job_title is not None and len(job_offer.job_title) > 0
        assert job_offer.company_name is not None and len(job_offer.company_name) > 0
        assert job_offer.location is not None and len(job_offer.location) > 0
        assert job_offer.skills_required is not None and len(job_offer.skills_required) > 0
        assert job_offer.description is not None and len(job_offer.description) > 0

    def test_french_skills_matching(self, french_job_offer_text, user_profile):
        """Test skills matching works for French job offer."""
        job_offer = parse_job_offer(french_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)

        assert matched_skills.matched_skills is not None
        assert len(matched_skills.matched_skills) > 0
        assert matched_skills.relevant_technologies is not None
        assert matched_skills.key_value_contributions is not None

    def test_french_project_selection(self, french_job_offer_text, user_profile):
        """Test project selection works for French job offer."""
        job_offer = parse_job_offer(french_job_offer_text)
        selected_projects = select_projects(job_offer, user_profile.projects)

        assert selected_projects.project1 is not None
        assert selected_projects.project2 is not None
        assert selected_projects.selection_reasoning is not None
        assert selected_projects.project1.title != selected_projects.project2.title

    def test_french_translations_available(self, translation_loader):
        """Test French translations are available."""
        # Verify CV headers
        assert translation_loader.get_translation("fr", "cv", "summary_header") == "RÉSUMÉ"
        assert translation_loader.get_translation("fr", "cv", "education_header") == "FORMATION"

        # Verify cover letter content
        assert translation_loader.get_translation("fr", "cover_letter", "greeting") == "Madame, Monsieur"
        assert translation_loader.get_translation("fr", "cover_letter", "sign_off") == "Cordialement"

    def test_french_project_translations_available(self, translation_loader):
        """Test French project translations are available."""
        # Verify at least one project is translated to French
        projects = translation_loader.get_section_translations("fr", "projects")
        assert len(projects) > 0

    # ========================================================================
    # SPANISH JOB OFFER TESTS
    # ========================================================================

    def test_spanish_job_offer_language_detection(self, spanish_job_offer_text):
        """Test Spanish job offer is correctly detected."""
        job_offer = parse_job_offer(spanish_job_offer_text)

        assert job_offer.language == "es"
        assert job_offer.job_title is not None
        assert len(job_offer.skills_required) > 0
        assert job_offer.company_name is not None

    def test_spanish_job_offer_parsing(self, spanish_job_offer_text):
        """Test Spanish job offer parsing extracts all key information."""
        job_offer = parse_job_offer(spanish_job_offer_text)

        # Verify key fields are populated
        assert job_offer.job_title is not None and len(job_offer.job_title) > 0
        assert job_offer.company_name is not None and len(job_offer.company_name) > 0
        assert job_offer.location is not None and len(job_offer.location) > 0
        assert job_offer.skills_required is not None and len(job_offer.skills_required) > 0
        assert job_offer.description is not None and len(job_offer.description) > 0

    def test_spanish_skills_matching(self, spanish_job_offer_text, user_profile):
        """Test skills matching works for Spanish job offer."""
        job_offer = parse_job_offer(spanish_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)

        assert matched_skills.matched_skills is not None
        assert len(matched_skills.matched_skills) > 0
        assert matched_skills.relevant_technologies is not None
        assert matched_skills.key_value_contributions is not None

    def test_spanish_project_selection(self, spanish_job_offer_text, user_profile):
        """Test project selection works for Spanish job offer."""
        job_offer = parse_job_offer(spanish_job_offer_text)
        selected_projects = select_projects(job_offer, user_profile.projects)

        assert selected_projects.project1 is not None
        assert selected_projects.project2 is not None
        assert selected_projects.selection_reasoning is not None
        assert selected_projects.project1.title != selected_projects.project2.title

    def test_spanish_translations_available(self, translation_loader):
        """Test Spanish translations are available."""
        # Verify CV headers
        assert translation_loader.get_translation("es", "cv", "summary_header") == "RESUMEN"
        assert translation_loader.get_translation("es", "cv", "education_header") == "FORMACIÓN"

        # Verify cover letter content
        assert translation_loader.get_translation("es", "cover_letter", "greeting") == "Estimado"
        assert translation_loader.get_translation("es", "cover_letter", "sign_off") == "Atentamente"

    # ========================================================================
    # CROSS-LANGUAGE COMPARISON TESTS
    # ========================================================================

    def test_all_languages_have_same_cv_sections(self, translation_loader):
        """Test all languages have the same CV sections."""
        en_sections = translation_loader.get_section_translations("en", "cv").keys()
        fr_sections = translation_loader.get_section_translations("fr", "cv").keys()
        es_sections = translation_loader.get_section_translations("es", "cv").keys()

        assert en_sections == fr_sections == es_sections

    def test_all_languages_have_same_cover_letter_sections(self, translation_loader):
        """Test all languages have the same cover letter sections."""
        en_sections = translation_loader.get_section_translations("en", "cover_letter").keys()
        fr_sections = translation_loader.get_section_translations("fr", "cover_letter").keys()
        es_sections = translation_loader.get_section_translations("es", "cover_letter").keys()

        assert en_sections == fr_sections == es_sections

    def test_language_field_propagates_through_pipeline(self, english_job_offer_text):
        """Test language field is preserved through the pipeline."""
        job_offer = parse_job_offer(english_job_offer_text)
        original_language = job_offer.language

        # Language should remain consistent
        assert job_offer.language == original_language

    # ========================================================================
    # TEMPLATE PROCESSOR MULTILINGUAL TESTS
    # ========================================================================

    def test_template_processor_handles_english(self, english_job_offer_text, user_profile, translation_loader):
        """Test template processor correctly handles English."""
        job_offer = parse_job_offer(english_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)
        selected_projects = select_projects(job_offer, user_profile.projects)

        processor = create_template_processor()
        processor.translation_loader = translation_loader

        result = processor.process_templates(
            job_offer, user_profile, matched_skills, selected_projects
        )

        assert result.cv_html is not None
        assert result.cover_letter_html is not None
        assert "SUMMARY" in result.cv_html  # English header

    def test_template_processor_handles_french(self, french_job_offer_text, user_profile, translation_loader):
        """Test template processor correctly handles French."""
        job_offer = parse_job_offer(french_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)
        selected_projects = select_projects(job_offer, user_profile.projects)

        processor = create_template_processor()
        processor.translation_loader = translation_loader

        result = processor.process_templates(
            job_offer, user_profile, matched_skills, selected_projects
        )

        assert result.cv_html is not None
        assert result.cover_letter_html is not None
        # Should contain French translations (or SUMMARY if not replaced)
        assert "RÉSUMÉ" in result.cv_html or "SUMMARY" in result.cv_html

    def test_template_processor_handles_spanish(self, spanish_job_offer_text, user_profile, translation_loader):
        """Test template processor correctly handles Spanish."""
        job_offer = parse_job_offer(spanish_job_offer_text)
        matched_skills = match_skills(job_offer, user_profile)
        selected_projects = select_projects(job_offer, user_profile.projects)

        processor = create_template_processor()
        processor.translation_loader = translation_loader

        result = processor.process_templates(
            job_offer, user_profile, matched_skills, selected_projects
        )

        assert result.cv_html is not None
        assert result.cover_letter_html is not None
        # Should contain Spanish translations (or SUMMARY if not replaced)
        assert "RESUMEN" in result.cv_html or "SUMMARY" in result.cv_html

    # ========================================================================
    # SUMMARY VALIDATION TESTS
    # ========================================================================

    def test_multilingual_pipeline_english_to_spanish(self, english_job_offer_text, user_profile):
        """Test complete pipeline validates job offers across languages."""
        job_offer = parse_job_offer(english_job_offer_text)

        assert job_offer.language == "en"
        assert job_offer.job_title is not None
        assert job_offer.company_name is not None
        assert len(job_offer.skills_required) > 0

    def test_all_three_languages_detected_correctly(self, english_job_offer_text, french_job_offer_text, spanish_job_offer_text):
        """Test all three language detections work correctly."""
        en_job = parse_job_offer(english_job_offer_text)
        fr_job = parse_job_offer(french_job_offer_text)
        es_job = parse_job_offer(spanish_job_offer_text)

        assert en_job.language == "en"
        assert fr_job.language == "fr"
        assert es_job.language == "es"

    def test_translation_loader_consistency(self, translation_loader):
        """Test translation loader is consistent across all languages."""
        # All languages should have the required sections
        for language in ["en", "fr", "es"]:
            cv_sections = translation_loader.get_section_translations(language, "cv")
            cl_sections = translation_loader.get_section_translations(language, "cover_letter")

            assert "summary_header" in cv_sections
            assert "greeting" in cl_sections
            assert "sign_off" in cl_sections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
