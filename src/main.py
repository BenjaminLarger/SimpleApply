#!/usr/bin/env python3
"""
AI-Powered Job Application System
Automatically generates tailored CVs and cover letters by analyzing job offers.
"""

import argparse
import sys
import yaml
from pathlib import Path

from .job_parser import parse_job_offer
from .skills_matcher import match_skills
from .project_selector import select_projects
from .template_processor import create_template_processor
from .models import UserProfile


def load_job_offer(job_offer_input: str) -> str:
    """
    Load job offer text from input (either direct text or file path).

    Args:
        job_offer_input: Either job offer text or path to file containing job offer

    Returns:
        Job offer text content

    Raises:
        FileNotFoundError: If file path doesn't exist
        IOError: If file cannot be read
    """
    # Check if input looks like a file path
    if len(job_offer_input) < 500 and ('\n' not in job_offer_input) and ('.' in job_offer_input):
        file_path = Path(job_offer_input)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except IOError as e:
                raise IOError(f"Failed to read job offer file {file_path}: {e}")
        else:
            # If it looks like a file path but doesn't exist, treat as text
            pass

    # Treat as direct text input
    return job_offer_input


def load_user_profile(profile_path: str) -> UserProfile:
    """
    Load user profile from YAML file.

    Args:
        profile_path: Path to user profile YAML file

    Returns:
        UserProfile instance

    Raises:
        FileNotFoundError: If profile file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValueError: If profile data is invalid
    """
    file_path = Path(profile_path)

    if not file_path.exists():
        raise FileNotFoundError(f"User profile file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            profile_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML profile file: {e}")

    try:
        return UserProfile(**profile_data)
    except Exception as e:
        raise ValueError(f"Invalid user profile data: {e}")


def save_html_file(content: str, output_path: Path, description: str) -> None:
    """
    Save HTML content to file.

    Args:
        content: HTML content to save
        output_path: Path where to save the file
        description: Description for user feedback

    Raises:
        IOError: If file cannot be written
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {description} saved to: {output_path}")
    except IOError as e:
        raise IOError(f"Failed to save {description.lower()}: {e}")


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup and configure command line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Job Application System - Generate tailored CV and cover letter from job offer",
        epilog="Examples:\n"
               "  %(prog)s 'Software Engineer at Google'\n"
               "  %(prog)s job_offer.txt\n"
               "  %(prog)s job_offer.txt --output-dir custom_output\n"
               "  %(prog)s job_offer.txt --profile my_profile.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "job_offer",
        help="Job offer text or path to file containing job offer"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save generated documents (default: output)"
    )
    parser.add_argument(
        "--profile",
        default="templates/user_profile.yaml",
        help="Path to user profile YAML file (default: templates/user_profile.yaml)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed progress information"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="AI-Powered Job Application System v1.0.0"
    )
    return parser


def print_configuration(args, verbose: bool) -> None:
    """Print system configuration and input parameters."""
    print("🚀 AI-Powered Job Application System")
    print("=" * 40)

    if verbose:
        print(f"🔧 Configuration:")
        print(f"   Job Offer Input: {args.job_offer}")
        print(f"   User Profile: {args.profile}")
        print(f"   Output Directory: {args.output_dir}")
        print(f"   Verbose Mode: Enabled")

    print(f"📄 Processing job offer: {args.job_offer}")
    print(f"👤 Using profile: {args.profile}")
    print(f"📁 Output directory: {args.output_dir}")


def load_and_display_job_offer(job_offer_input: str, verbose: bool) -> str:
    """Load job offer and display loading information."""
    print("\n🔍 Step 1: Loading job offer...")
    job_offer_text = load_job_offer(job_offer_input)
    print(f"   Job offer loaded ({len(job_offer_text)} characters)")

    if verbose:
        input_type = "file" if Path(job_offer_input).exists() else "direct text"
        print(f"   Input type: {input_type}")
        if len(job_offer_text) > 200:
            print(f"   Preview: {job_offer_text[:200]}...")

    return job_offer_text


def load_and_display_user_profile(profile_path: str, verbose: bool) -> UserProfile:
    """Load user profile and display profile information."""
    print("\n👤 Step 2: Loading user profile...")
    user_profile = load_user_profile(profile_path)
    print(f"   Profile loaded for {user_profile.personal_info.name}")
    print(f"   Skills: {len(user_profile.skills)}")
    print(f"   Projects: {len(user_profile.projects)}")
    print(f"   Experiences: {len(user_profile.experiences)}")

    if verbose:
        print(f"   Email: {user_profile.personal_info.email}")
        print(f"   Languages: {', '.join(user_profile.languages)}")
        if user_profile.projects:
            print(f"   Available projects: {', '.join([p.title for p in user_profile.projects])}")

    return user_profile


def parse_and_display_job_offer(job_offer_text: str, verbose: bool):
    """Parse job offer and display parsing results."""
    print("\n🔧 Step 3: Parsing job offer...")
    job_offer = parse_job_offer(job_offer_text)
    print(f"   Job Title: {job_offer.job_title}")
    print(f"   Company: {job_offer.company_name}")
    print(f"   Required Skills: {len(job_offer.skills_required)}")

    if verbose:
        print(f"   Location: {job_offer.location}")
        print(f"   Skills required: {', '.join(job_offer.skills_required[:5])}{'...' if len(job_offer.skills_required) > 5 else ''}")

    return job_offer


def match_and_display_skills(job_offer, user_profile, verbose: bool):
    """Match skills and display matching results."""
    print("\n🎯 Step 4: Matching skills...")
    matched_skills = match_skills(job_offer, user_profile)
    print(f"   Matched Skills: {len(matched_skills.matched_skills)}")
    print(f"   Relevant Technologies: {len(matched_skills.relevant_technologies)}")
    print(f"   Relevant Achievements: {len(matched_skills.relevant_achievements)}")

    if verbose:
        print(f"   Top matched skills: {', '.join(matched_skills.matched_skills[:3])}{'...' if len(matched_skills.matched_skills) > 3 else ''}")
        total_required = len(job_offer.skills_required)
        matched_count = len(matched_skills.matched_skills)
        match_percentage = (matched_count / total_required * 100) if total_required > 0 else 0.0
        print(f"   Skills match rate: {matched_count}/{total_required} ({match_percentage:.1f}%)")

    return matched_skills


def select_and_display_projects(job_offer, projects):
    """Select projects and display selection results."""
    print("\n📋 Step 5: Selecting relevant projects...")
    selected_projects = select_projects(job_offer, projects)
    print(f"   Selected Project 1: {selected_projects.project1.title}")
    print(f"   Selected Project 2: {selected_projects.project2.title}")
    return selected_projects


def generate_and_display_documents(job_offer, user_profile, matched_skills, selected_projects, verbose: bool):
    """Generate documents and display generation progress."""
    print("\n📝 Step 6: Generating documents...")
    template_processor = create_template_processor()
    generated_content = template_processor.process_templates(
        job_offer=job_offer,
        user_profile=user_profile,
        matched_skills=matched_skills,
        selected_projects=selected_projects
    )
    print(f"   CV HTML length: {len(generated_content.cv_html):,} characters")
    print(f"   Cover Letter HTML length: {len(generated_content.cover_letter_html):,} characters")

    if verbose:
        print(f"   Templates processed successfully")
        print(f"   Using template directory: templates/")

    return generated_content


def generate_safe_filenames(job_offer):
    """Generate safe filenames from job offer information."""
    job_title_safe = "".join(c for c in job_offer.job_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    job_title_safe = job_title_safe.replace(' ', '_')
    company_safe = "".join(c for c in job_offer.company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    company_safe = company_safe.replace(' ', '_')

    cv_filename = f"CV_{job_title_safe}_{company_safe}.html"
    cover_letter_filename = f"CoverLetter_{job_title_safe}_{company_safe}.html"

    return cv_filename, cover_letter_filename


def save_and_display_files(generated_content, job_offer, matched_skills, selected_projects, output_dir, verbose: bool):
    """Save output files and display completion status."""
    print("\n💾 Step 7: Saving output files...")

    cv_filename, cover_letter_filename = generate_safe_filenames(job_offer)
    cv_path = output_dir / cv_filename
    cover_letter_path = output_dir / cover_letter_filename

    save_html_file(generated_content.cv_html, cv_path, "CV")
    save_html_file(generated_content.cover_letter_html, cover_letter_path, "Cover Letter")

    print("\n🎉 Success! Documents generated successfully!")
    print(f"📋 Generated for: {job_offer.job_title} at {job_offer.company_name}")
    print(f"🎯 Matched {len(matched_skills.matched_skills)} skills")
    print(f"📁 Files saved in: {output_dir}")

    if verbose:
        print(f"\n📊 Generation Summary:")
        print(f"   CV file: {cv_filename} ({len(generated_content.cv_html):,} chars)")
        print(f"   Cover Letter file: {cover_letter_filename} ({len(generated_content.cover_letter_html):,} chars)")
        print(f"   Total processing time: Complete")
        print(f"   Selected projects: {selected_projects.project1.title}, {selected_projects.project2.title}")
        print(f"   Match quality: {len(matched_skills.matched_skills)}/{len(job_offer.skills_required)} skills matched")


def main():
    """Main entry point for the job application system."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    verbose = args.verbose
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print_configuration(args, verbose)

    try:
        job_offer_text = load_and_display_job_offer(args.job_offer, verbose)
        user_profile = load_and_display_user_profile(args.profile, verbose)
        job_offer = parse_and_display_job_offer(job_offer_text, verbose)
        matched_skills = match_and_display_skills(job_offer, user_profile, verbose)
        selected_projects = select_and_display_projects(job_offer, user_profile.projects)
        generated_content = generate_and_display_documents(job_offer, user_profile, matched_skills, selected_projects, verbose)
        save_and_display_files(generated_content, job_offer, matched_skills, selected_projects, output_dir, verbose)

    except FileNotFoundError as e:
        print(f"❌ File Error: {e}")
        sys.exit(1)
    except (yaml.YAMLError, ValueError) as e:
        print(f"❌ Data Error: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"❌ IO Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()