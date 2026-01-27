"""
Template processor module for generating personalized CVs and cover letters.

This module handles loading HTML templates and replacing placeholder variables
with actual user data, matched skills, selected projects, and job information.
Includes multilingual support for generating documents in the language of the job offer.
"""

import re
import logging
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Optional

from .models import JobOffer, MatchedSkills, SelectedProjects, UserProfile, GeneratedContent, Project
from .translation_loader import create_translation_loader, TranslationError
from .date_translator import translate_date, translate_date_range
from .job_title_parser import extract_gender_form

# Set up logging
logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Processes HTML templates with dynamic content insertion."""

    def __init__(self, templates_dir: Path = Path("templates")):
        self.templates_dir = templates_dir
        self.cv_template_name = "cv_template.html"
        self.cover_letter_template_name = "cover_letter_template.html"
        try:
            self.translation_loader = create_translation_loader()
        except TranslationError as e:
            logger.warning(f"Failed to load translations: {e}. Falling back to English.")
            self.translation_loader = None

    def _apply_project_translations(self, selected_projects: SelectedProjects, target_language: str) -> SelectedProjects:
        """
        Apply pre-translated project titles and descriptions from translation dictionary.

        Args:
            selected_projects: Projects to translate
            target_language: Target language code (fr, es, etc.)

        Returns:
            SelectedProjects with translated titles/descriptions (if available)
        """
        if target_language == "en" or not self.translation_loader:
            return selected_projects

        try:
            # Look up translations for both projects
            p1_translation = self.translation_loader.get_project_translation(
                target_language,
                selected_projects.project1.title
            )
            p2_translation = self.translation_loader.get_project_translation(
                target_language,
                selected_projects.project2.title
            )

            # Create new projects with translated content (if available)
            p1_data = selected_projects.project1.model_dump()
            if p1_translation:
                p1_data["title"] = p1_translation.get("title", p1_data["title"])
                p1_data["description"] = p1_translation.get("description", p1_data["description"])

            p2_data = selected_projects.project2.model_dump()
            if p2_translation:
                p2_data["title"] = p2_translation.get("title", p2_data["title"])
                p2_data["description"] = p2_translation.get("description", p2_data["description"])

            translated_p1 = Project(**p1_data)
            translated_p2 = Project(**p2_data)

            return SelectedProjects(
                project1=translated_p1,
                project2=translated_p2,
                selection_reasoning=selected_projects.selection_reasoning
            )

        except TranslationError as e:
            logger.warning(f"Failed to apply project translations: {e}. Using original projects.")
            return selected_projects

    def load_template(self, template_name: str) -> str:
        """
        Load HTML template from templates directory.

        Args:
            template_name: Name of the template file to load

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
            IOError: If template cannot be read
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            raise IOError(f"Failed to read template {template_path}: {e}")

    def replace_placeholders(self, template: str, replacements: Dict[str, str]) -> str:
        """
        Replace placeholder variables in template with actual values.

        Args:
            template: HTML template content
            replacements: Dictionary mapping placeholder patterns to replacement values

        Returns:
            Template with placeholders replaced
        """
        result = template

        for placeholder, value in replacements.items():
            # Replace HTML comments (<!-- PLACEHOLDER -->)
            comment_pattern = f"<!--\\s*{re.escape(placeholder)}\\s*-->"
            result = re.sub(comment_pattern, value, result, flags=re.IGNORECASE)

            # Replace direct placeholders {PLACEHOLDER}
            direct_pattern = f"\\{{\\s*{re.escape(placeholder)}\\s*\\}}"
            result = re.sub(direct_pattern, value, result, flags=re.IGNORECASE)

            # Replace bracket placeholders [PLACEHOLDER]
            bracket_pattern = f"\\[\\s*{re.escape(placeholder)}\\s*\\]"
            result = re.sub(bracket_pattern, value, result, flags=re.IGNORECASE)

        return result

    def _translate_static_content(self, html: str, language: str, section: str) -> str:
        """
        Translate static HTML headers and labels to target language.

        Args:
            html: HTML content to translate
            language: Target language code (en, fr, es)
            section: Section type (cv or cover_letter)

        Returns:
            HTML with translated headers/labels

        Raises:
            None - Falls back to original HTML on error
        """
        if language == "en" or not self.translation_loader:
            return html

        try:
            translations = self.translation_loader.get_section_translations(language, section)

            # Create mapping of English text to translated text for string replacement
            replacements = {
                ">SUMMARY<": f">{translations.get('summary_header', 'SUMMARY')}<",
                ">EDUCATION<": f">{translations.get('education_header', 'EDUCATION')}<",
                ">FREELANCE / SIDE PROJECTS<": f">{translations.get('projects_header', 'FREELANCE / SIDE PROJECTS')}<",
                ">PROFESSIONAL EXPERIENCE<": f">{translations.get('experience_header', 'PROFESSIONAL EXPERIENCE')}<",
                ">SKILLS, LANGUAGES & HOBBIES<": f">{translations.get('skills_header', 'SKILLS, LANGUAGES & HOBBIES')}<",
                "SKILLS, LANGUAGES &amp; HOBBIES": translations.get('skills_header', 'SKILLS, LANGUAGES & HOBBIES'),
                "<u>Languages</u>": f"<u>{translations.get('languages_label', 'Languages')}</u>",
                "<u>Hobbies:</u>": f"<u>{translations.get('hobbies_label', 'Hobbies')}:</u>",
                "<u>Hobbies</u>": f"<u>{translations.get('hobbies_label', 'Hobbies')}</u>",
                "<u>Skills & Tools:</u>": f"<u>{translations.get('skills_label', 'Skills & Tools')}:</u>",
                "<u>Skills & Tools</u>": f"<u>{translations.get('skills_label', 'Skills & Tools')}</u>",
                "<u>Relevant Skills</u>": f"<u>{translations.get('relevant_skills_label', 'Relevant Skills')}</u>",
                "<u>Main classes</u>": f"<u>{translations.get('main_classes_label', 'Main classes')}</u>",
            }

            # Apply replacements
            result = html
            for english_text, translated_text in replacements.items():
                result = result.replace(english_text, translated_text)

            return result

        except TranslationError as e:
            logger.warning(f"Failed to translate static content: {e}. Using original HTML.")
            return html

    def generate_cv_replacements(
        self,
        job_offer: JobOffer,
        user_profile: UserProfile,
        matched_skills: MatchedSkills,
        selected_projects: SelectedProjects,
        translated_projects: Optional[SelectedProjects] = None
    ) -> Dict[str, str]:
        """
        Generate replacement dictionary for CV template.

        Args:
            job_offer: Parsed job offer information
            user_profile: User profile data
            matched_skills: Skills matching results
            selected_projects: Selected relevant projects
            translated_projects: Optional translated projects (for non-English languages)

        Returns:
            Dictionary of placeholder -> replacement mappings
        """
        # Format skills for display (top 20 most relevant)
        top_skills = matched_skills.relevant_technologies[:20]
        skills_text = ", ".join(top_skills)

        # SAFETY FIX: Ensure skills text is never empty to prevent blank "Compétences & Outils" section
        # This is a secondary safeguard in case relevant_technologies is unexpectedly empty
        if not skills_text or skills_text.strip() == "":
            # Fallback: Use matched skills (actual matches between job and user profile)
            # matched_skills contains 10+ confirmed matches from the AI matching process
            fallback_skills = matched_skills.matched_skills[:20] if matched_skills.matched_skills else user_profile.skills[:10]
            skills_text = ", ".join(fallback_skills)

        # Use translated projects if provided, otherwise use original
        projects_to_use = translated_projects if translated_projects else selected_projects

        # Get summary text from translations if available
        summary_text = job_offer.job_title  # Default
        if self.translation_loader:
            try:
                # Use gender-specific summary text if available
                gender = user_profile.personal_info.gender.lower()
                gender_key = f"summary_text_{gender}" if gender in ["male", "female"] else "summary_text"

                # Try gender-specific key first, fallback to generic
                try:
                    summary_text = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cv",
                        key=gender_key,
                        job_title=job_offer.job_title
                    )
                except TranslationError:
                    # Fallback to generic summary_text
                    summary_text = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cv",
                        key="summary_text",
                        job_title=job_offer.job_title
                    )
            except TranslationError as e:
                logger.debug(f"Could not load summary translation: {e}")
                summary_text = job_offer.job_title

        replacements = {
            "CV_SUMMARY": summary_text,
            "PROJECT 1 TITLE": projects_to_use.project1.title,
            "PROJECT 1 TYPE": projects_to_use.project1.type,
            "PROJECT 1 DESCRIPTION": projects_to_use.project1.description,
            "PROJECT 2 TITLE": projects_to_use.project2.title,
            "PROJECT 2 TYPE": projects_to_use.project2.type,
            "PROJECT 2 DESCRIPTION": projects_to_use.project2.description,
            "20 relevant skills/tools": skills_text,
            "SKILLS_LIST": skills_text
        }

        # Add education, hobbies, and language translations
        if self.translation_loader:
            try:
                language = job_offer.language

                # Load education translations
                education_trans = self.translation_loader.get_section_translations(language, "cv").get("education", {})
                replacements["BOOTCAMP42_DESCRIPTION"] = education_trans.get("bootcamp_description", "")
                replacements["SCHOOL42_TRAINING"] = education_trans.get("school_42_training", "")
                replacements["UNIVERSITY_DEGREE"] = education_trans.get("university_degree", "")

                # Load experience translations with gender support
                # Experience is stored at the top level, not under "cv"
                lang_translations = self.translation_loader.translations.get(language, {})
                experience_trans = lang_translations.get("experience", {})
                gender = user_profile.personal_info.gender.lower()

                # ENGIE role (gender-aware)
                engie_data = experience_trans.get("engie", {})
                if gender in ["male", "female"]:
                    engie_role = engie_data.get(f"role_{gender}", engie_data.get("role", ""))
                else:
                    engie_role = engie_data.get("role", "")
                replacements["ENGIE_ROLE"] = engie_role

                # ENGIE achievements
                engie_achievements = engie_data.get("achievements", {})
                replacements["ENGIE_ACHIEVEMENT_1"] = engie_achievements.get("collaboration", "")
                replacements["ENGIE_ACHIEVEMENT_2"] = engie_achievements.get("scraping", "")
                replacements["ENGIE_ACHIEVEMENT_3"] = engie_achievements.get("energy_solutions", "")
                replacements["ENGIE_ACHIEVEMENT_4"] = engie_achievements.get("docker", "")

                # ING role (gender-aware)
                ing_data = experience_trans.get("ing", {})
                if gender in ["male", "female"]:
                    ing_role = ing_data.get(f"role_{gender}", ing_data.get("role", ""))
                else:
                    ing_role = ing_data.get("role", "")
                replacements["ING_ROLE"] = ing_role

                # ING achievements
                ing_achievements = ing_data.get("achievements", {})
                replacements["ING_ACHIEVEMENT_1"] = ing_achievements.get("analytics", "")
                replacements["ING_ACHIEVEMENT_2"] = ing_achievements.get("vba_automation", "")

                # Load hobbies and languages
                hobbies_trans = self.translation_loader.get_section_translations(language, "cv").get("hobbies", {})
                hobbies_list = [
                    hobbies_trans.get("blockchain", "Blockchain technology"),
                    hobbies_trans.get("ai", "Artificial Intelligence"),
                    hobbies_trans.get("football", "Football"),
                    hobbies_trans.get("personal_dev", "Personal Development")
                ]
                replacements["HOBBIES_LIST"] = "; ".join(hobbies_list)

                languages_desc_trans = self.translation_loader.get_section_translations(language, "cv").get("languages_descriptions", {})
                languages_list = [
                    languages_desc_trans.get("french_native", "French (native)"),
                    languages_desc_trans.get("english_fluent", "English (fluent)"),
                    languages_desc_trans.get("spanish_fluent", "Spanish (fluent)")
                ]
                replacements["LANGUAGES_LIST"] = "; ".join(languages_list)

                # Load label translations
                cv_labels = self.translation_loader.get_section_translations(language, "cv")
                replacements["RELEVANT_SKILLS_LABEL"] = cv_labels.get("relevant_skills_label", "Relevant Skills")
                replacements["MAIN_CLASSES_LABEL"] = cv_labels.get("main_classes_label", "Main classes")
                replacements["LANGUAGES_LABEL"] = cv_labels.get("languages_label", "Languages")
                replacements["HOBBIES_LABEL"] = cv_labels.get("hobbies_label", "Hobbies")
                replacements["SKILLS_LABEL"] = cv_labels.get("skills_label", "Skills & Tools")
                replacements["AGE_PHRASE"] = cv_labels.get("age_phrase", "years old")

                # Translate dates
                replacements["BOOTCAMP42_DATE"] = translate_date("2025-05-01", language)
                replacements["SCHOOL42_DATE"] = translate_date_range("2023-01-01", "2025-12-31", language)
                replacements["UNIVERSITY_DATE"] = translate_date_range("2019-01-01", "2025-12-31", language)
                replacements["ENGIE_DATE"] = translate_date_range("2023-01-01", "2023-06-30", language)
                replacements["ING_DATE"] = translate_date_range("2023-05-01", "2023-09-30", language)

            except (TranslationError, KeyError) as e:
                logger.debug(f"Could not load some translations: {e}. Using defaults.")

        return replacements

    def _get_value_contributions_for_cover_letter(self, matched_skills: MatchedSkills) -> List[str]:
        """
        Get top 3 value contributions with fallback defaults for cover letter.

        Args:
            matched_skills: Skills matching results

        Returns:
            List of 3 value contributions (with fallbacks if needed)
        """
        top_contributions = matched_skills.key_value_contributions[:3]
        fallback_contributions = [
            "My background in software development and data science positions me to deliver innovative technical solutions that drive measurable business impact.",
            "I bring a proven track record of collaborating with cross-functional teams to implement scalable software systems and solve complex technical challenges.",
            "My experience spans full-stack development, cloud architecture, and AI integration, enabling me to contribute effectively across multiple technical domains."
        ]

        contributions = []
        for i in range(3):
            if i < len(top_contributions):
                contributions.append(top_contributions[i])
            else:
                contributions.append(fallback_contributions[i])

        return contributions

    def _generate_personalized_content(self, job_offer: JobOffer, matched_skills: MatchedSkills) -> Dict[str, str]:
        """
        Generate personalized content for cover letter.

        Args:
            job_offer: Parsed job offer information
            matched_skills: Skills matching results

        Returns:
            Dictionary with personalized content
        """
        language_defaults = {
            "en": {
                "company_excitement": f"the opportunity to work with cutting-edge technology at {job_offer.company_name}",
                "role_attraction": f"it aligns perfectly with my experience in {', '.join(matched_skills.matched_skills[:3])}",
                "specific_goal": "innovative software solutions that drive business growth",
                "relevant_skills": ", ".join(matched_skills.relevant_technologies[:5])
            },
            "fr": {
                "company_excitement": f"l'opportunité de travailler avec la technologie de pointe chez {job_offer.company_name}",
                "role_attraction": f"elle s'aligne parfaitement avec mon expérience en {', '.join(matched_skills.matched_skills[:3])}",
                "specific_goal": "des solutions logicielles innovantes qui stimulent la croissance commerciale",
                "relevant_skills": ", ".join(matched_skills.relevant_technologies[:5])
            },
            "es": {
                "company_excitement": f"la oportunidad de trabajar con tecnología de vanguardia en {job_offer.company_name}",
                "role_attraction": f"se alinea perfectamente con mi experiencia en {', '.join(matched_skills.matched_skills[:3])}",
                "specific_goal": "soluciones de software innovadoras que impulsen el crecimiento empresarial",
                "relevant_skills": ", ".join(matched_skills.relevant_technologies[:5])
            }
        }

        defaults = language_defaults.get(job_offer.language, language_defaults["en"])

        return {
            "company_excitement": defaults["company_excitement"],
            "role_attraction": defaults["role_attraction"],
            "specific_goal": defaults["specific_goal"],
            "relevant_skills": defaults["relevant_skills"]
        }

    def generate_cover_letter_replacements(
        self,
        job_offer: JobOffer,
        user_profile: UserProfile,
        matched_skills: MatchedSkills,
        selected_projects: SelectedProjects
    ) -> Dict[str, str]:
        """
        Generate replacement dictionary for cover letter template.

        Args:
            job_offer: Parsed job offer information
            user_profile: User profile data
            matched_skills: Skills matching results
            selected_projects: Selected relevant projects

        Returns:
            Dictionary of placeholder -> replacement mappings
        """
        achievements = self._get_value_contributions_for_cover_letter(matched_skills)
        personalized = self._generate_personalized_content(job_offer, matched_skills)

        replacements = {
            "Date": date.today().strftime("%d/%m/%Y"),
            "Company Name": job_offer.company_name,
            "Company Address": job_offer.location,
            "City, State ZIP": job_offer.location,
            "Job Title": job_offer.job_title,
            "Achievement 1": achievements[0],
            "Achievement 2": achievements[1],
            "Achievement 3": achievements[2],
            "specific company detail or mission": personalized["company_excitement"],
            "specific responsibility or project mentioned in job posting": personalized["specific_goal"]
        }

        # Add translated paragraphs if translation loader is available
        if self.translation_loader:
            try:
                gender = user_profile.personal_info.gender.lower()
                gender_suffix = f"_{gender}" if gender in ["male", "female"] else ""

                # Try gender-specific intro_paragraph first, fallback to generic
                try:
                    intro_para = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key=f"intro_paragraph{gender_suffix}",
                        job_title=job_offer.job_title,
                        company_name=job_offer.company_name
                    )
                except TranslationError:
                    intro_para = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key="intro_paragraph",
                        job_title=job_offer.job_title,
                        company_name=job_offer.company_name
                    )
                replacements["INTRO_PARAGRAPH"] = intro_para

                exp_para = self.translation_loader.get_translation(
                    language=job_offer.language,
                    section="cover_letter",
                    key="experience_paragraph"
                )
                replacements["EXPERIENCE_PARAGRAPH"] = exp_para

                key_areas = self.translation_loader.get_translation(
                    language=job_offer.language,
                    section="cover_letter",
                    key="key_areas_header"
                )
                replacements["KEY_AREAS_HEADER"] = key_areas

                # Try gender-specific closing_paragraph_1 first, fallback to generic
                try:
                    closing_1 = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key=f"closing_paragraph_1{gender_suffix}",
                        company_name=job_offer.company_name,
                        company_excitement=personalized["company_excitement"],
                        specific_goal=personalized["specific_goal"]
                    )
                except TranslationError:
                    closing_1 = self.translation_loader.format_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key="closing_paragraph_1",
                        company_name=job_offer.company_name,
                        company_excitement=personalized["company_excitement"],
                        specific_goal=personalized["specific_goal"]
                    )
                replacements["CLOSING_PARAGRAPH_1"] = closing_1

                closing_2 = self.translation_loader.format_translation(
                    language=job_offer.language,
                    section="cover_letter",
                    key="closing_paragraph_2",
                    company_name=job_offer.company_name
                )
                replacements["CLOSING_PARAGRAPH_2"] = closing_2

                # Try gender-specific greeting first, fallback to generic
                try:
                    greeting = self.translation_loader.get_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key=f"greeting{gender_suffix}"
                    )
                except TranslationError:
                    greeting = self.translation_loader.get_translation(
                        language=job_offer.language,
                        section="cover_letter",
                        key="greeting"
                    )
                replacements["GREETING"] = greeting

                sign_off = self.translation_loader.get_translation(
                    language=job_offer.language,
                    section="cover_letter",
                    key="sign_off"
                )
                replacements["SIGN_OFF"] = sign_off

            except TranslationError as e:
                logger.warning(f"Failed to load cover letter translations: {e}")

        return replacements

    def _truncate_description(self, description: str, min_length: int, max_length: int) -> str:
        """
        Return description as-is without truncation.

        Args:
            description: Original description text
            min_length: Minimum required length (unused)
            max_length: Maximum allowed length (unused)

        Returns:
            Original description unchanged
        """
        return description

    def process_templates(
        self,
        job_offer: JobOffer,
        user_profile: UserProfile,
        matched_skills: MatchedSkills,
        selected_projects: SelectedProjects
    ) -> GeneratedContent:
        """
        Process both CV and cover letter templates with provided data.
        Supports multilingual generation based on job offer language.

        Args:
            job_offer: Parsed job offer information
            user_profile: User profile data
            matched_skills: Skills matching results
            selected_projects: Selected relevant projects

        Returns:
            GeneratedContent with processed HTML for both documents

        Raises:
            FileNotFoundError: If template files are not found
            IOError: If templates cannot be processed
        """
        try:
            # Load templates
            cv_template = self.load_template(self.cv_template_name)
            cover_letter_template = self.load_template(self.cover_letter_template_name)

            # Apply pre-translated project descriptions if job offer is not in English
            translated_projects_obj = selected_projects
            if job_offer.language != "en":
                translated_projects_obj = self._apply_project_translations(
                    selected_projects,
                    job_offer.language
                )

            # Generate replacements
            cv_replacements = self.generate_cv_replacements(
                job_offer, user_profile, matched_skills, selected_projects,
                translated_projects=translated_projects_obj if job_offer.language != "en" else None
            )
            cover_letter_replacements = self.generate_cover_letter_replacements(
                job_offer, user_profile, matched_skills, selected_projects
            )

            # Process templates with placeholder replacement
            cv_html = self.replace_placeholders(cv_template, cv_replacements)
            cover_letter_html = self.replace_placeholders(cover_letter_template, cover_letter_replacements)

            # Translate static content headers if language is not English
            if job_offer.language != "en":
                cv_html = self._translate_static_content(cv_html, job_offer.language, "cv")
                cover_letter_html = self._translate_static_content(cover_letter_html, job_offer.language, "cover_letter")

            return GeneratedContent(
                cv_html=cv_html,
                cover_letter_html=cover_letter_html,
                job_offer=job_offer,
                matched_skills=matched_skills,
                selected_projects=selected_projects
            )

        except (FileNotFoundError, IOError) as e:
            raise IOError(f"Template processing failed: {e}")


def create_template_processor(templates_dir: str = "templates") -> TemplateProcessor:
    """
    Factory function to create a configured TemplateProcessor instance.

    Args:
        templates_dir: Path to templates directory

    Returns:
        Configured TemplateProcessor instance
    """
    return TemplateProcessor(templates_dir=Path(templates_dir))