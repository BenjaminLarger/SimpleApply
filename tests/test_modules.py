#!/usr/bin/env python3
"""
Test script to validate all three modules work together.
"""

import yaml
from src.models import UserProfile
from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects


def test_complete_pipeline():
    """Test the complete pipeline with sample data."""
    print("🧪 Testing AI Job Application System Pipeline")
    print("=" * 50)

    # Sample job posting
    sample_job = """
    AI/ML Engineer - LangChain & Python

    Company: InnovateAI Corp
    Location: Remote (Global)

    We're seeking an experienced AI/ML Engineer to build cutting-edge AI applications.

    Requirements:
    - 3+ years of Python development experience
    - Experience with LangChain, LangGraph frameworks
    - Knowledge of AI/ML concepts and LLM integration
    - FastAPI or Django web framework experience
    - Docker containerization skills
    - Experience with cloud platforms (AWS, Google Cloud)
    - REST API development experience
    - Streamlit for rapid prototyping
    - Git/GitHub for version control

    Preferred:
    - Experience with OpenAI or Claude APIs
    - Background in AI agent development
    - Experience with PostgreSQL or similar databases
    - Knowledge of CI/CD practices
    """

    try:
        # Step 1: Parse job offer
        print("🔍 Step 1: Parsing job offer...")
        job_offer = parse_job_offer(sample_job)
        print(f"✅ Parsed job: {job_offer.job_title} at {job_offer.company_name}")
        print(f"   📍 Location: {job_offer.location}")
        print(f"   🛠️  Skills required: {len(job_offer.skills_required)} skills identified")

        # Step 2: Load user profile
        print("\n👤 Step 2: Loading user profile...")
        with open("templates/user_profile.yaml", "r") as f:
            profile_data = yaml.safe_load(f)

        user_profile = UserProfile(**profile_data)
        print(f"✅ Loaded profile for: {user_profile.personal_info.name}")
        print(f"   💼 Experience: {len(user_profile.experiences)} positions")
        print(f"   🎯 Skills: {len(user_profile.skills)} skills")
        print(f"   📂 Projects: {len(user_profile.projects)} projects")

        # Step 3: Match skills
        print("\n🎯 Step 3: Matching skills...")
        matched_skills = match_skills(job_offer, user_profile)
        print(f"✅ Skills analysis complete:")
        print(f"   🔄 Matched skills: {len(matched_skills.matched_skills)} found")
        print(f"   🛠️  Relevant technologies: {len(matched_skills.relevant_technologies)} highlighted")
        print(f"   🏆 Key value contributions: {len(matched_skills.key_value_contributions)} paragraphs generated")

        print(f"\n   Top matched skills: {matched_skills.matched_skills[:5]}")

        # Step 4: Select project
        print("\n📂 Step 4: Selecting relevant project...")
        selected_projects = select_projects(job_offer, user_profile.projects)
        print(f"✅ Project selection complete:")
        print(f"   📌 Project: {selected_projects.project.title}")

        print(f"\n   Selection reasoning: {selected_projects.selection_reasoning[:150]}...")

        # Summary
        print("\n🎉 Pipeline Test Results:")
        print("=" * 50)
        print(f"✅ Job Parser: Successfully parsed {job_offer.company_name} position")
        print(f"✅ Skills Matcher: Found {len(matched_skills.matched_skills)} skill matches")
        print(f"✅ Project Selector: Selected most relevant project")
        print(f"\n💡 The system is ready to generate tailored applications!")

        return True

    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)