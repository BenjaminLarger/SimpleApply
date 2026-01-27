"""
Date translation utility for multilingual CV and cover letter generation.

Handles conversion of ISO date format (YYYY-MM-DD) to localized date strings
with translated month names for EN, FR, and ES languages.
"""

from datetime import datetime


# Month translations for each language
MONTH_TRANSLATIONS = {
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ],
    "fr": [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ],
    "es": [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
}


def translate_date(iso_date: str, language: str = "en", include_day: bool = False) -> str:
    """
    Convert ISO date format to localized date string with translated month name.

    Args:
        iso_date: Date string in ISO format (YYYY-MM-DD), e.g., "2023-01-15"
        language: Language code ('en', 'fr', 'es'). Defaults to 'en'.
        include_day: If True, include day in output (e.g., "January 15, 2023").
                    If False, only include month and year (e.g., "January 2023").

    Returns:
        Formatted date string with translated month name.
        Falls back to English if language not supported.

    Examples:
        >>> translate_date("2023-01-15", "fr", include_day=False)
        'Janvier 2023'
        >>> translate_date("2023-05-30", "es", include_day=True)
        'Mayo 30, 2023'
        >>> translate_date("2025-12-01", "en")
        'December 2025'
    """
    try:
        # Parse ISO date format
        date_obj = datetime.strptime(iso_date, "%Y-%m-%d")

        # Get language-specific month names (fallback to English)
        if language not in MONTH_TRANSLATIONS:
            language = "en"

        months = MONTH_TRANSLATIONS[language]
        month_name = months[date_obj.month - 1]
        year = date_obj.year

        if include_day:
            day = date_obj.day
            if language == "en":
                return f"{month_name} {day}, {year}"
            elif language == "fr":
                return f"{day} {month_name} {year}"
            elif language == "es":
                return f"{day} de {month_name} de {year}"
        else:
            return f"{month_name} {year}"

    except (ValueError, IndexError):
        # If date parsing fails, return original input
        return iso_date


def translate_date_range(start_date: str, end_date: str, language: str = "en") -> str:
    """
    Convert a date range from ISO format to localized format.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        language: Language code ('en', 'fr', 'es'). Defaults to 'en'.

    Returns:
        Formatted date range string.

    Examples:
        >>> translate_date_range("2023-01-01", "2023-06-30", "en")
        'January 2023 – June 2023'
        >>> translate_date_range("2023-01-01", "2023-06-30", "fr")
        'Janvier 2023 – Juin 2023'
        >>> translate_date_range("2023-01-01", "2023-06-30", "es")
        'Enero 2023 – Junio 2023'
    """
    start_formatted = translate_date(start_date, language, include_day=False)
    end_formatted = translate_date(end_date, language, include_day=False)

    return f"{start_formatted} – {end_formatted}"
