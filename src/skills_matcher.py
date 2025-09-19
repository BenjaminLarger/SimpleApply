"""
Skills matcher module using OpenAI GPT.
Intelligently matches user skills with job requirements.
"""

import os
import json
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from .models import JobOffer, UserProfile, MatchedSkills

# Load environment variables
load_dotenv()


class SkillsMatcherError(Exception):
    """Custom exception for skills matching errors."""
    pass


def get_openai_client() -> OpenAI:
    """Get authenticated OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SkillsMatcherError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set your OpenAI API key in the .env file."
        )
    return OpenAI(api_key=api_key)


def match_skills(job_offer: JobOffer, user_profile: UserProfile) -> MatchedSkills:
    """
    Match user skills with job requirements using AI intelligence.

    Args:
        job_offer: Parsed job offer information
        user_profile: User's complete profile

    Returns:
        MatchedSkills: Matched skills analysis

    Raises:
        SkillsMatcherError: If matching fails or API error occurs
    """
    try:
        # Get OpenAI client
        client = get_openai_client()

        # Prepare user technologies from experiences
        user_technologies = []
        for experience in user_profile.experiences:
            user_technologies.extend(experience.technologies)

        # Prepare user achievements from experiences
        user_achievements = []
        for experience in user_profile.experiences:
            user_achievements.extend(experience.achievements)

        # Add profile-level achievements
        user_achievements.extend(user_profile.achievements)

        # Create comprehensive prompt
        prompt = f"""
You are an expert career counselor and skills matcher. Analyze the job requirements against the user's profile and intelligently match skills, technologies, and achievements.

JOB OFFER:
- Title: {job_offer.job_title}
- Company: {job_offer.company_name}
- Location: {job_offer.location}
- Required Skills: {job_offer.skills_required}

USER PROFILE:
- Skills: {user_profile.skills}
- Technologies from Experience: {user_technologies}
- Achievements: {user_achievements}

Please analyze and return a JSON object with the following structure:
{{
    "user_skills": ["List of all user's skills and technologies"],
    "job_skills": ["List of all job required skills"],
    "matched_skills": ["Skills that directly or closely match between user and job"],
    "relevant_technologies": ["Most relevant technologies to highlight for this role"],
    "relevant_achievements": ["Most relevant achievements that align with job requirements"]
}}

Guidelines for matching:
1. MATCHED SKILLS: Include exact matches and close semantic matches (e.g., "Python" matches "Python development", "REST API" matches "RESTful APIs")
2. RELEVANT TECHNOLOGIES: Prioritize technologies mentioned in job requirements, but also include related ones from user's experience
3. RELEVANT ACHIEVEMENTS: Select achievements that demonstrate skills needed for this role, even if not exact keyword matches
4. Consider transferable skills and related technologies (e.g., if job requires React and user has JavaScript experience)
5. Prioritize recent and significant experiences over older ones
6. Include both technical and soft skills where relevant

Return only the JSON object, no additional text.
"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            max_tokens=3000,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract and parse response
        response_text = response.choices[0].message.content.strip()

        try:
            # Parse JSON response
            skills_data = json.loads(response_text)

            # Validate required fields
            required_fields = ["user_skills", "job_skills", "matched_skills", "relevant_technologies", "relevant_achievements"]
            for field in required_fields:
                if field not in skills_data:
                    raise SkillsMatcherError(f"Missing required field: {field}")

            # Ensure all fields are lists
            for field in required_fields:
                if not isinstance(skills_data[field], list):
                    skills_data[field] = []

            # Create and validate MatchedSkills model
            matched_skills = MatchedSkills(**skills_data)
            return matched_skills

        except json.JSONDecodeError as e:
            raise SkillsMatcherError(f"Failed to parse JSON response from OpenAI: {e}")

    except Exception as e:
        if isinstance(e, SkillsMatcherError):
            raise
        raise SkillsMatcherError(f"Unexpected error during skills matching: {e}")


def match_skills_safe(job_offer: JobOffer, user_profile: UserProfile) -> MatchedSkills | None:
    """
    Safe version of match_skills that returns None on error instead of raising.

    Args:
        job_offer: Parsed job offer information
        user_profile: User's complete profile

    Returns:
        MatchedSkills or None: Matched skills or None if matching failed
    """
    try:
        return match_skills(job_offer, user_profile)
    except SkillsMatcherError as e:
        print(f"Skills matching failed: {e}")
        return None


if __name__ == "__main__":
    # Test with sample data
    from job_parser import parse_job_offer
    import yaml

    # Sample job posting
    sample_job = """
    Senior Python Developer - AI/ML Focus

    Company: DataTech Solutions
    Location: Remote (US timezone)

    We are seeking a Senior Python Developer with expertise in AI/ML to join our growing team.

    Requirements:
    - 5+ years experience with Python
    - Strong background in machine learning and AI frameworks
    - Experience with FastAPI, Django, or Flask
    - Knowledge of Docker and AWS
    - Proficiency in SQL and PostgreSQL
    - Experience with REST APIs
    - LangChain, LangGraph experience preferred
    - Strong problem-solving skills
    """

    try:
        # Parse job offer
        job_offer = parse_job_offer(sample_job)

        # Load user profile
        with open("templates/user_profile.yaml", "r") as f:
            profile_data = yaml.safe_load(f)

        user_profile = UserProfile(**profile_data)

        # Match skills
        matched_skills = match_skills(job_offer, user_profile)

        print("Skills Matching Results:")
        print(f"Matched Skills: {matched_skills.matched_skills}")
        print(f"Relevant Technologies: {matched_skills.relevant_technologies}")
        print(f"Relevant Achievements: {len(matched_skills.relevant_achievements)} achievements selected")

    except Exception as e:
        print(f"Error: {e}")