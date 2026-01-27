"""
Translation loader module for managing multilingual content.
Loads and provides access to translation dictionaries.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class TranslationError(Exception):
    """Custom exception for translation-related errors."""
    pass


class TranslationLoader:
    """Loads and manages translation dictionaries for multiple languages."""

    def __init__(self, translations_path: Optional[Path] = None):
        """
        Initialize translation loader.

        Args:
            translations_path: Path to translations.json file.
                              If None, uses default path relative to this module.

        Raises:
            TranslationError: If translations file cannot be loaded
        """
        if translations_path is None:
            # Default path relative to src directory
            translations_path = Path(__file__).parent.parent / "translations" / "translations.json"

        self.translations_path = Path(translations_path)
        self.translations = self._load_translations()
        self.supported_languages = list(self.translations.keys())

    def _load_translations(self) -> Dict[str, Any]:
        """
        Load translations from JSON file.

        Returns:
            Dictionary containing translations

        Raises:
            TranslationError: If file cannot be read or parsed
        """
        try:
            if not self.translations_path.exists():
                raise TranslationError(f"Translations file not found: {self.translations_path}")

            with open(self.translations_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            raise TranslationError(f"Invalid JSON in translations file: {e}")
        except IOError as e:
            raise TranslationError(f"Failed to read translations file: {e}")

    def get_translation(self, language: str, section: str, key: str) -> str:
        """
        Get a single translation string.

        Args:
            language: Language code (en, fr, es)
            section: Section name (cv, cover_letter)
            key: Translation key

        Returns:
            Translated string

        Raises:
            TranslationError: If language, section, or key not found
        """
        try:
            if language not in self.translations:
                raise TranslationError(f"Language not supported: {language}. Supported: {self.supported_languages}")

            if section not in self.translations[language]:
                raise TranslationError(f"Section '{section}' not found for language '{language}'")

            if key not in self.translations[language][section]:
                raise TranslationError(f"Translation key '{key}' not found in {language}/{section}")

            return self.translations[language][section][key]

        except KeyError as e:
            raise TranslationError(f"Translation lookup failed: {e}")

    def format_translation(self, language: str, section: str, key: str, **kwargs) -> str:
        """
        Get a translation and format it with provided variables.

        Args:
            language: Language code (en, fr, es)
            section: Section name (cv, cover_letter)
            key: Translation key
            **kwargs: Variables to format into the translation string

        Returns:
            Formatted translation string

        Raises:
            TranslationError: If translation not found or formatting fails
        """
        try:
            translation = self.get_translation(language, section, key)
            return translation.format(**kwargs)
        except KeyError as e:
            raise TranslationError(f"Missing placeholder in translation: {e}")

    def get_section_translations(self, language: str, section: str) -> Dict[str, str]:
        """
        Get all translations for a specific section and language.

        Args:
            language: Language code (en, fr, es)
            section: Section name (cv, cover_letter)

        Returns:
            Dictionary of all translations in that section

        Raises:
            TranslationError: If language or section not found
        """
        try:
            if language not in self.translations:
                raise TranslationError(f"Language not supported: {language}")

            if section not in self.translations[language]:
                raise TranslationError(f"Section '{section}' not found for language '{language}'")

            return self.translations[language][section]

        except KeyError as e:
            raise TranslationError(f"Failed to get section translations: {e}")

    def get_supported_languages(self) -> list:
        """
        Get list of supported language codes.

        Returns:
            List of language codes (e.g., ['en', 'fr', 'es'])
        """
        return self.supported_languages

    def get_project_translation(self, language: str, project_title: str) -> Dict[str, str]:
        """
        Get translation for a project by English title.

        Args:
            language: Language code (en, fr, es)
            project_title: English project title

        Returns:
            Dictionary with 'title' and 'description' keys

        Raises:
            TranslationError: If project translation not found
        """
        try:
            if language not in self.translations:
                raise TranslationError(f"Language not supported: {language}")

            if 'projects' not in self.translations[language]:
                # No projects section for this language, return empty
                return None

            projects = self.translations[language]['projects']
            if project_title not in projects:
                # Project translation not found
                return None

            return projects[project_title]

        except (KeyError, TypeError) as e:
            raise TranslationError(f"Failed to get project translation: {e}")

    def validate_structure(self) -> bool:
        """
        Validate that translations have required structure.

        Returns:
            True if structure is valid

        Raises:
            TranslationError: If structure is invalid
        """
        try:
            required_sections = ['cv', 'cover_letter']
            required_cv_keys = [
                'summary_header', 'education_header', 'projects_header',
                'experience_header', 'skills_header'
            ]
            required_cl_keys = [
                'greeting', 'intro_paragraph', 'experience_paragraph',
                'key_areas_header', 'closing_paragraph_1', 'closing_paragraph_2',
                'sign_off'
            ]

            for language in self.supported_languages:
                lang_data = self.translations[language]

                # Check required sections
                for section in required_sections:
                    if section not in lang_data:
                        raise TranslationError(f"Missing section '{section}' in language '{language}'")

                # Check CV keys
                for key in required_cv_keys:
                    if key not in lang_data['cv']:
                        raise TranslationError(f"Missing CV key '{key}' in language '{language}'")

                # Check cover letter keys
                for key in required_cl_keys:
                    if key not in lang_data['cover_letter']:
                        raise TranslationError(f"Missing cover letter key '{key}' in language '{language}'")

            return True

        except (KeyError, TypeError) as e:
            raise TranslationError(f"Invalid translation structure: {e}")


def create_translation_loader(translations_path: Optional[Path] = None) -> TranslationLoader:
    """
    Factory function to create a translation loader.

    Args:
        translations_path: Optional path to translations.json file

    Returns:
        Initialized TranslationLoader instance

    Raises:
        TranslationError: If initialization fails
    """
    loader = TranslationLoader(translations_path)
    # Validate structure on creation
    loader.validate_structure()
    return loader
