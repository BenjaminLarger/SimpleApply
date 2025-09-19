#!/usr/bin/env python3
"""
Demonstration script for the template processor module.

This script shows how to use the TemplateProcessor to generate
personalized CVs and cover letters with sample data.
"""

from src.template_processor import create_template_processor
from src.models import (
    JobOffer, MatchedSkills, SelectedProjects, UserProfile,
    PersonalInfo, Project
)


def create_sample_data():
    """Create sample data for demonstration."""

    # Sample job offer
    job_offer = JobOffer(
        job_title="Senior Python Developer",
        company_name="TechCorp Inc",
        skills_required=["Python", "Django", "PostgreSQL", "Docker", "AWS"],
        location="Remote",
        description="We are looking for a senior Python developer to join our team..."
    )

    # Sample user profile (minimal for demo)
    user_profile = UserProfile(
        personal_info=PersonalInfo(name="Benjamin Larger", email="benjaminlarger@gmail.com"),
        experiences=[],
        skills=["Python", "Django", "JavaScript", "Docker", "PostgreSQL", "React"],
        education=[],
        projects=[],
        languages=["French", "English", "Spanish"],
        achievements=["Built scalable web applications", "Led development teams", "Implemented CI/CD pipelines"],
        hobbies=["Programming", "AI Research"]
    )

    # Sample matched skills
    matched_skills = MatchedSkills(
        user_skills=["Python", "Django", "JavaScript", "Docker", "PostgreSQL", "React"],
        job_skills=["Python", "Django", "PostgreSQL", "Docker", "AWS"],
        matched_skills=["Python", "Django", "PostgreSQL", "Docker"],
        relevant_technologies=["Python", "Django", "Docker", "PostgreSQL", "JavaScript", "React"],
        relevant_achievements=[
            "Built scalable web applications with Django and PostgreSQL",
            "Implemented containerized deployments using Docker",
            "Led cross-functional development teams"
        ]
    )

    # Sample selected projects
    selected_projects = SelectedProjects(
        project1=Project(
            title="E-commerce Platform",
            description="A full-stack e-commerce platform built with Django and React, featuring user authentication, payment processing, and real-time inventory management.",
            technologies=["Python", "Django", "React", "PostgreSQL"],
            url="https://github.com/user/ecommerce",
            start_date="2023-01",
            end_date="2023-06",
            status="completed"
        ),
        project2=Project(
            title="Data Analytics Dashboard",
            description="Interactive dashboard for business analytics using Python, pandas, and visualization libraries to process large datasets and generate insights.",
            technologies=["Python", "pandas", "plotly", "Flask"],
            url="https://github.com/user/analytics",
            start_date="2023-07",
            end_date="2023-12",
            status="completed"
        ),
        selection_reasoning="Both projects demonstrate strong Python and web development skills relevant to the position."
    )

    return job_offer, user_profile, matched_skills, selected_projects


def main():
    """Demonstrate the template processor functionality."""
    print("🔧 Template Processor Demonstration")
    print("=" * 50)

    # Create sample data
    job_offer, user_profile, matched_skills, selected_projects = create_sample_data()

    # Create template processor
    processor = create_template_processor()

    try:
        # Process templates
        print("\n📄 Processing templates...")
        generated_content = processor.process_templates(
            job_offer=job_offer,
            user_profile=user_profile,
            matched_skills=matched_skills,
            selected_projects=selected_projects
        )

        print("✅ Templates processed successfully!")

        # Show some statistics
        print(f"\n📊 Generated Content Statistics:")
        print(f"   CV HTML length: {len(generated_content.cv_html):,} characters")
        print(f"   Cover Letter HTML length: {len(generated_content.cover_letter_html):,} characters")
        print(f"   Job Title: {generated_content.job_offer.job_title}")
        print(f"   Company: {generated_content.job_offer.company_name}")
        print(f"   Matched Skills: {', '.join(generated_content.matched_skills.matched_skills)}")

        # Show CV replacements sample
        print(f"\n🎯 Sample CV Replacements:")
        cv_replacements = processor.generate_cv_replacements(
            job_offer, user_profile, matched_skills, selected_projects
        )
        for key, value in list(cv_replacements.items())[:3]:  # Show first 3
            print(f"   {key}: {value}")

        # Show cover letter replacements sample
        print(f"\n📝 Sample Cover Letter Replacements:")
        cl_replacements = processor.generate_cover_letter_replacements(
            job_offer, user_profile, matched_skills, selected_projects
        )
        for key, value in list(cl_replacements.items())[:3]:  # Show first 3
            print(f"   {key}: {value}")

        print(f"\n🎉 Template processing demonstration completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during template processing: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())