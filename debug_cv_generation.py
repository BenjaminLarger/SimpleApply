#!/usr/bin/env python3
"""Debug script to reproduce CV generation failure."""

import yaml
from src.models import UserProfile, JobOffer
from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor

# Sample job posting for testing
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
    print("DEBUG: CV GENERATION FAILURE INVESTIGATION")
    print("=" * 80)

    try:
        # 1. Load user profile
        print("\n1. Loading user profile...")
        with open("templates/user_profile.yaml", "r") as f:
            profile_data = yaml.safe_load(f)
        user_profile = UserProfile(**profile_data)
        print(f"✓ Loaded profile for {user_profile.personal_info.name}")
        print(f"  - Projects: {len(user_profile.projects)}")
        for i, proj in enumerate(user_profile.projects):
            print(f"    [{i}] {proj.title} (type: {proj.type})")

        # 2. Parse job offer
        print("\n2. Parsing job offer...")
        job_offer = parse_job_offer(sample_job)
        print(f"✓ Parsed job offer: {job_offer.job_title} at {job_offer.company_name}")

        # 3. Match skills
        print("\n3. Matching skills...")
        matched_skills = match_skills(job_offer, user_profile)
        print(f"✓ Matched {len(matched_skills.matched_skills)} skills")
        print(f"  Matched: {matched_skills.matched_skills}")
        print(f"  Relevant techs: {matched_skills.relevant_technologies}")

        # 4. Select projects
        print("\n4. Selecting projects...")
        selected_projects = select_projects(job_offer, user_profile.projects)
        print(f"✓ Selected projects:")
        print(f"  Project 1: {selected_projects.project1.title}")
        print(f"    - Type: {selected_projects.project1.type}")
        print(f"    - Description length: {len(selected_projects.project1.description)}")
        print(f"  Project 2: {selected_projects.project2.title}")
        print(f"    - Type: {selected_projects.project2.type}")
        print(f"    - Description length: {len(selected_projects.project2.description)}")
        print(f"  Reasoning: {selected_projects.selection_reasoning[:100]}...")

        # 5. Process templates
        print("\n5. Processing templates...")
        template_processor = create_template_processor()
        generated_content = template_processor.process_templates(
            job_offer=job_offer,
            user_profile=user_profile,
            matched_skills=matched_skills,
            selected_projects=selected_projects
        )
        print(f"✓ Templates processed successfully")

        # 6. Check CV content
        print("\n6. Checking CV content...")
        cv_html = generated_content.cv_html

        # Check for unfilled placeholders
        placeholders = [
            "<!-- PROJECT 1 TITLE -->",
            "<!-- PROJECT 1 TYPE -->",
            "<!-- PROJECT 1 DESCRIPTION -->",
            "<!-- PROJECT 2 TITLE -->",
            "<!-- PROJECT 2 TYPE -->",
            "<!-- PROJECT 2 DESCRIPTION -->",
        ]

        unfilled = []
        for placeholder in placeholders:
            if placeholder in cv_html:
                unfilled.append(placeholder)

        if unfilled:
            print(f"✗ FOUND {len(unfilled)} UNFILLED PLACEHOLDERS:")
            for p in unfilled:
                print(f"  - {p}")
        else:
            print(f"✓ All placeholders filled successfully")

            # Show what was filled
            print(f"\n  Project 1 Title filled: {selected_projects.project1.title in cv_html}")
            print(f"  Project 1 Type filled: {selected_projects.project1.type in cv_html}")
            print(f"  Project 2 Title filled: {selected_projects.project2.title in cv_html}")
            print(f"  Project 2 Type filled: {selected_projects.project2.type in cv_html}")

        # 7. Save output for inspection
        print("\n7. Saving debug output...")
        with open("/tmp/debug_cv.html", "w") as f:
            f.write(cv_html)
        print(f"✓ Saved to /tmp/debug_cv.html")

        # Extract and show the projects section
        print("\n8. FREELANCE / SIDE PROJECTS Section:")
        start = cv_html.find("FREELANCE / SIDE PROJECTS")
        if start > 0:
            section = cv_html[start:start+1500]
            print(section)

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
