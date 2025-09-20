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
from .cost_tracker import track_openai_call

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


def extract_user_data(user_profile: UserProfile) -> tuple[List[str], List[str]]:
    """
    Extract technologies and achievements from user profile.

    Args:
        user_profile: User's complete profile

    Returns:
        Tuple of (user_technologies, user_achievements)
    """
    user_technologies = []
    for experience in user_profile.experiences:
        user_technologies.extend(experience.technologies)

    user_achievements = []
    for experience in user_profile.experiences:
        user_achievements.extend(experience.achievements)
    user_achievements.extend(user_profile.achievements)

    return user_technologies, user_achievements


def create_skills_matching_prompt(job_offer: JobOffer, user_profile: UserProfile, user_technologies: List[str], user_achievements: List[str]) -> str:
    """
    Create comprehensive prompt for skills matching.

    Args:
        job_offer: Parsed job offer information
        user_profile: User's complete profile
        user_technologies: Technologies from user's experience
        user_achievements: All user achievements

    Returns:
        Formatted prompt string
    """
    return f"""
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
2. RELEVANT TECHNOLOGIES: Return exactly 20 relevant technologies. Prioritize technologies mentioned in job requirements, but also include related ones from user's experience
3. RELEVANT ACHIEVEMENTS: Select achievements that demonstrate skills needed for this role, even if not exact keyword matches
4. Consider transferable skills and related technologies (e.g., if job requires React and user has JavaScript experience)
5. Prioritize recent and significant experiences over older ones
6. Include both technical and soft skills where relevant

Return only the JSON object, no additional text.
"""


def call_openai_for_skills_matching(prompt: str):
    """
    Call OpenAI API for skills matching.

    Args:
        prompt: Formatted prompt for skills matching

    Returns:
        OpenAI API response

    Raises:
        SkillsMatcherError: If API call fails
    """
    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.1,
        max_completion_tokens=4000,
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    track_openai_call(response, "skills_matching")
    return response


def parse_skills_response(response_text: str) -> MatchedSkills:
    """
    Parse OpenAI response and create MatchedSkills model.

    Args:
        response_text: JSON response from OpenAI

    Returns:
        MatchedSkills model instance

    Raises:
        SkillsMatcherError: If parsing or validation fails
    """
    try:
        skills_data = json.loads(response_text)

        required_fields = ["user_skills", "job_skills", "matched_skills", "relevant_technologies", "relevant_achievements"]
        for field in required_fields:
            if field not in skills_data:
                raise SkillsMatcherError(f"Missing required field: {field}")

        for field in required_fields:
            if not isinstance(skills_data[field], list):
                skills_data[field] = []

        return MatchedSkills(**skills_data)

    except json.JSONDecodeError as e:
        raise SkillsMatcherError(f"Failed to parse JSON response from OpenAI: {e}\nResponse Text: {response_text}")


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
        user_technologies, user_achievements = extract_user_data(user_profile)
        prompt = create_skills_matching_prompt(job_offer, user_profile, user_technologies, user_achievements)
        response = call_openai_for_skills_matching(prompt)
        response_text = response.choices[0].message.content.strip()
        return parse_skills_response(response_text)

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