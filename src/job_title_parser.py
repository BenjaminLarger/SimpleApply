"""
Job title gender-aware parsing utility.

Handles extraction of gender-specific job titles from inclusive gender forms
like "Développeur(se)", "Développeur/euse", or "Développeur·euse".

Supports three formats:
1. Parenthetical: "Développeur(se)" → base form: "Développeur", feminine form: "Développeuse"
2. Slash: "Développeur/euse" → base form: "Développeur", feminine form: "Développeuse"
3. Middle dot: "Développeur·euse" → base form: "Développeur", feminine form: "Développeuse"
"""

import re


def extract_gender_form(job_title: str, gender: str = "male") -> str:
    """
    Extract gender-specific form from an inclusive job title.

    Args:
        job_title: Job title that may contain gender markers
                   Examples: "Développeur(se)", "Développeur/euse", "Développeur·euse"
        gender: User's gender ('male' or 'female'). Defaults to 'male'.

    Returns:
        Cleaned job title in the appropriate gender form.
        - If gender='male': returns base form without gender markers
        - If gender='female': returns feminine form if detectable, otherwise base form

    Examples:
        >>> extract_gender_form("Développeur(se)", "male")
        'Développeur'
        >>> extract_gender_form("Développeur(se)", "female")
        'Développeuse'
        >>> extract_gender_form("Développeur/euse", "male")
        'Développeur'
        >>> extract_gender_form("Développeur/euse", "female")
        'Développeuse'
        >>> extract_gender_form("Software Engineer", "male")
        'Software Engineer'
    """
    gender = gender.lower()

    # If male, just extract base form and return
    if gender == "male":
        return _extract_base_form(job_title)

    # If female, try to extract feminine form
    if gender == "female":
        return _extract_feminine_form(job_title)

    # Default: return original if gender not recognized
    return job_title


def _extract_base_form(job_title: str) -> str:
    """
    Extract the base (typically masculine) form from a gendered job title.

    Examples:
        >>> _extract_base_form("Développeur(se)")
        'Développeur'
        >>> _extract_base_form("Développeur/euse")
        'Développeur'
        >>> _extract_base_form("Développeur·euse")
        'Développeur'
    """
    # Pattern 1: Remove parenthetical content and strip whitespace
    # "Développeur(se)" → "Développeur"
    result = re.sub(r'\([^)]*\)', '', job_title).strip()

    # Pattern 2: Take only the part before slash
    # "Développeur/euse" → "Développeur"
    result = result.split('/')[0].strip()

    # Pattern 3: Take only the part before middle dot
    # "Développeur·euse" → "Développeur"
    result = result.split('·')[0].strip()

    return result


def _extract_feminine_form(job_title: str) -> str:
    """
    Extract the feminine form from a gendered job title.

    Attempts to identify and return the feminine variant.
    Falls back to base form if feminine form cannot be determined.

    Examples:
        >>> _extract_feminine_form("Développeur(se)")
        'Développeuse'
        >>> _extract_feminine_form("Développeur/euse")
        'Développeuse'
        >>> _extract_feminine_form("Développeur·euse")
        'Développeuse'
    """
    # Pattern 1: Parenthetical form "Word(suffix)" or "Word(full_form)"
    # Extract what's in parentheses and combine with base
    paren_match = re.search(r'^([^()]+)\(([^)]+)\)(.*)$', job_title)
    if paren_match:
        base = paren_match.group(1).strip()
        paren_content = paren_match.group(2).strip()
        suffix = paren_match.group(3).strip()

        # If parenthetical content is just a suffix (single letter or short ending),
        # combine with base: "Développeur(se)" → base="Développeur", paren="se" → "Développeuse"
        if len(paren_content) <= 3 and paren_content.lower() in ['se', 'e', 'a', 'euse', 'eure']:
            # Simple suffix case - assume pattern is: "DeveloperX(suffix)" → "DeveloperSuffix"
            # For "Développeur(se)", we want "Développeuse"
            # Common pattern: remove last letter of base and add suffix
            if paren_content.lower() in ['se', 'euse']:
                # "Développeur" + "se" → "Développeuse" (remove -r, add -se)
                if base.endswith('r') and paren_content.lower() == 'se':
                    return base[:-1] + paren_content
                elif base.endswith('r') and paren_content.lower() == 'euse':
                    return base[:-1] + paren_content
            # Fallback: just add suffix to base
            return base + paren_content + suffix
        else:
            # Full word in parentheses: "Something(Somethinge)" → use the parenthetical form
            return paren_content + suffix

    # Pattern 2: Slash form "male/female" or "male/female_suffix"
    slash_match = re.search(r'^([^/]+)/(.+)$', job_title)
    if slash_match:
        base = slash_match.group(1).strip()
        feminine = slash_match.group(2).strip()
        # "Développeur/euse" → "Développeuse"
        if feminine.lower() in ['euse', 'se', 'e', 'a']:
            # Suffix only - combine with base
            if base.endswith('r') and feminine.lower() == 'euse':
                return base[:-1] + feminine
            elif base.endswith('r') and feminine.lower() == 'se':
                return base[:-1] + feminine
            else:
                return base + feminine
        else:
            # Full feminine word provided
            return feminine

    # Pattern 3: Middle dot form "male·female"
    dot_match = re.search(r'^([^·]+)·(.+)$', job_title)
    if dot_match:
        feminine = dot_match.group(2).strip()
        return feminine

    # No gender marker found - return original
    return job_title


def is_gendered_title(job_title: str) -> bool:
    """
    Check if a job title contains gender markers.

    Args:
        job_title: Job title to check

    Returns:
        True if the title contains parenthetical, slash, or dot gender markers.

    Examples:
        >>> is_gendered_title("Développeur(se)")
        True
        >>> is_gendered_title("Software Engineer")
        False
    """
    return bool(re.search(r'[\(/]|\·', job_title))
