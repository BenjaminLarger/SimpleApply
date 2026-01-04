"""
Template processor module for generating personalized CVs and cover letters.

This module handles loading HTML templates and replacing placeholder variables
with actual user data, matched skills, selected projects, and job information.
"""

import re
from pathlib import Path
from datetime import date
from typing import Dict, Any, List


from .models import JobOffer, MatchedSkills, SelectedProjects, UserProfile, GeneratedContent


class TemplateProcessor:
    """Processes HTML templates with dynamic content insertion."""

    def __init__(self, templates_dir: Path = Path("templates")):
        self.templates_dir = templates_dir
        self.cv_template_name = "cv_template.html"
        self.cover_letter_template_name = "cover_letter_template.html"

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

    def generate_cv_replacements(
        self,
        job_offer: JobOffer,
        user_profile: UserProfile,
        matched_skills: MatchedSkills,
        selected_projects: SelectedProjects
    ) -> Dict[str, str]:
        """
        Generate replacement dictionary for CV template.

        Args:
            job_offer: Parsed job offer information
            user_profile: User profile data
            matched_skills: Skills matching results
            selected_projects: Selected relevant projects

        Returns:
            Dictionary of placeholder -> replacement mappings
        """
        # Format skills for display (top 20 most relevant)
        top_skills = matched_skills.relevant_technologies[:20]
        skills_text = ", ".join(top_skills)

        return {
            "JOB TITLE": job_offer.job_title,
            "PROJECT 1 TITLE": selected_projects.project1.title,
            "PROJECT 1 TYPE": selected_projects.project1.type,
            "PROJECT 1 DESCRIPTION": selected_projects.project1.description,
            "PROJECT 2 TITLE": selected_projects.project2.title,
            "PROJECT 2 TYPE": selected_projects.project2.type,
            "PROJECT 2 DESCRIPTION": selected_projects.project2.description,
            "20 relevant skills/tools": skills_text
        }

    def _get_achievements_with_fallbacks(self, matched_skills: MatchedSkills) -> List[str]:
        """
        Get top 3 achievements with fallback defaults.

        Args:
            matched_skills: Skills matching results

        Returns:
            List of 3 achievements (with fallbacks if needed)
        """
        top_achievements = matched_skills.relevant_achievements[:3]
        fallback_achievements = [
            "Developed scalable software solutions",
            "Collaborated effectively in cross-functional teams",
            "Implemented data-driven decision making processes"
        ]

        achievements = []
        for i in range(3):
            if i < len(top_achievements):
                achievements.append(top_achievements[i])
            else:
                achievements.append(fallback_achievements[i])

        return achievements

    def _generate_personalized_content(self, job_offer: JobOffer, matched_skills: MatchedSkills) -> Dict[str, str]:
        """
        Generate personalized content for cover letter.

        Args:
            job_offer: Parsed job offer information
            matched_skills: Skills matching results

        Returns:
            Dictionary with personalized content
        """
        company_excitement = f"the opportunity to work with cutting-edge technology at {job_offer.company_name}"
        role_attraction = f"it aligns perfectly with my experience in {', '.join(matched_skills.matched_skills[:3])}"
        specific_goal = "innovative software solutions that drive business growth"
        relevant_skills = ", ".join(matched_skills.relevant_technologies[:5])

        return {
            "company_excitement": company_excitement,
            "role_attraction": role_attraction,
            "specific_goal": specific_goal,
            "relevant_skills": relevant_skills
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
        achievements = self._get_achievements_with_fallbacks(matched_skills)
        personalized = self._generate_personalized_content(job_offer, matched_skills)

        return {
            "Date": date.today().strftime("%B %d, %Y"),
            "Hiring Manager Name / Hiring Team": "Hiring Team",
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

            # Generate replacements
            cv_replacements = self.generate_cv_replacements(
                job_offer, user_profile, matched_skills, selected_projects
            )
            cover_letter_replacements = self.generate_cover_letter_replacements(
                job_offer, user_profile, matched_skills, selected_projects
            )

            # Process templates
            cv_html = self.replace_placeholders(cv_template, cv_replacements)
            cover_letter_html = self.replace_placeholders(cover_letter_template, cover_letter_replacements)

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