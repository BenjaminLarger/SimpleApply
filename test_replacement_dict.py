#!/usr/bin/env python3
"""Test what replacements are being generated."""

import yaml
from src.models import UserProfile, JobOffer
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

def main():
    print("=" * 80)
    print("TESTING REPLACEMENT DICTIONARY")
    print("=" * 80)

    # Load user profile
    with open("templates/user_profile.yaml", "r") as f:
        profile_data = yaml.safe_load(f)
    user_profile = UserProfile(**profile_data)

    # Parse job offer
    job_offer = parse_job_offer(sample_job)

    # Match skills
    matched_skills = match_skills(job_offer, user_profile)

    # Select projects
    selected_projects = select_projects(job_offer, user_profile.projects)

    # Get replacements
    template_processor = create_template_processor()
    replacements = template_processor.generate_cv_replacements(
        job_offer=job_offer,
        user_profile=user_profile,
        matched_skills=matched_skills,
        selected_projects=selected_projects
    )

    print("\nGenerated Replacements Dictionary:")
    print("=" * 80)
    for key, value in replacements.items():
        print(f"Key: {key}")
        if len(value) > 100:
            print(f"Value: {value[:100]}...")
        else:
            print(f"Value: {value}")
        print()

    # Check for required keys
    required_keys = [
        "JOB TITLE",
        "PROJECT 1 TITLE",
        "PROJECT 1 TYPE",
        "PROJECT 1 DESCRIPTION",
        "PROJECT 2 TITLE",
        "PROJECT 2 TYPE",
        "PROJECT 2 DESCRIPTION",
        "20 relevant skills/tools"
    ]

    print("\nVerifying Required Keys:")
    print("=" * 80)
    for key in required_keys:
        if key in replacements:
            print(f"✓ {key}")
        else:
            print(f"✗ MISSING: {key}")

    # Load template and check if it has the placeholders
    print("\nChecking Template for Placeholders:")
    print("=" * 80)
    template_processor = create_template_processor()
    cv_template = template_processor.load_template("cv_template.html")

    placeholders_to_check = [
        "<!-- PROJECT 1 TITLE -->",
        "<!-- PROJECT 1 TYPE -->",
        "<!-- PROJECT 1 DESCRIPTION -->",
        "<!-- PROJECT 2 TITLE -->",
        "<!-- PROJECT 2 TYPE -->",
        "<!-- PROJECT 2 DESCRIPTION -->",
    ]

    for placeholder in placeholders_to_check:
        if placeholder in cv_template:
            print(f"✓ Found in template: {placeholder}")
        else:
            print(f"✗ NOT FOUND in template: {placeholder}")

if __name__ == "__main__":
    main()
