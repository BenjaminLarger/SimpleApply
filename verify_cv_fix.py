#!/usr/bin/env python3
"""Verify that the CV generation now correctly fills all project placeholders."""

import yaml
import sys
from src.models import UserProfile
from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor

sample_job = """
Python Back-End Engineer

Company: PandaDoc
Location: Remote

Requirements:
- Python
- Django
- FastAPI
- Docker
- PostgreSQL
- AWS Lambda
- REST API
- Microservices
"""

def verify_cv_generation():
    """Verify CV generation with all fixes applied."""

    print("=" * 80)
    print("VERIFYING CV GENERATION FIX")
    print("=" * 80)

    # Load profile
    with open("templates/user_profile.yaml", "r") as f:
        profile_data = yaml.safe_load(f)
    user_profile = UserProfile(**profile_data)

    # Parse and process
    job_offer = parse_job_offer(sample_job)
    matched_skills = match_skills(job_offer, user_profile)
    selected_projects = select_projects(job_offer, user_profile.projects)

    # Generate CV
    template_processor = create_template_processor()
    generated_content = template_processor.process_templates(
        job_offer=job_offer,
        user_profile=user_profile,
        matched_skills=matched_skills,
        selected_projects=selected_projects
    )

    cv_html = generated_content.cv_html

    # Check for the critical issue: unfilled placeholders
    unfilled_placeholders = [
        "<!-- PROJECT 1 TITLE -->",
        "<!-- PROJECT 1 TYPE -->",
        "<!-- PROJECT 1 DESCRIPTION -->",
        "<!-- PROJECT 2 TITLE -->",
        "<!-- PROJECT 2 TYPE -->",
        "<!-- PROJECT 2 DESCRIPTION -->",
    ]

    print("\n1. CHECKING FOR UNFILLED PLACEHOLDERS:")
    print("-" * 80)

    unfilled_found = []
    for placeholder in unfilled_placeholders:
        if placeholder in cv_html:
            unfilled_found.append(placeholder)
            print(f"   ✗ UNFILLED: {placeholder}")
        else:
            print(f"   ✓ FILLED: {placeholder}")

    if unfilled_found:
        print(f"\n   FAIL: Found {len(unfilled_found)} unfilled placeholders!")
        return False

    print("\n2. VERIFYING PROJECT DATA IN CV:")
    print("-" * 80)

    # Verify the actual content is there
    checks = [
        (selected_projects.project1.title, "Project 1 title"),
        (selected_projects.project1.type, "Project 1 type"),
        (selected_projects.project1.description[:50], "Project 1 description"),
        (selected_projects.project2.title, "Project 2 title"),
        (selected_projects.project2.type, "Project 2 type"),
        (selected_projects.project2.description[:50], "Project 2 description"),
    ]

    all_good = True
    for content, label in checks:
        if content in cv_html:
            print(f"   ✓ {label}: Found in CV")
        else:
            print(f"   ✗ {label}: NOT found in CV")
            all_good = False

    if not all_good:
        return False

    print("\n3. SHOWING FREELANCE / SIDE PROJECTS SECTION:")
    print("-" * 80)

    start = cv_html.find("FREELANCE / SIDE PROJECTS")
    if start > 0:
        end = cv_html.find("PROFESSIONAL EXPERIENCE", start)
        section = cv_html[start:end]
        print(section)
    else:
        print("   ✗ FREELANCE / SIDE PROJECTS section not found!")
        return False

    print("\n" + "=" * 80)
    print("✓ VERIFICATION PASSED: CV generation is working correctly!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    try:
        success = verify_cv_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
