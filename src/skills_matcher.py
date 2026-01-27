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

    NOTE: This function requests exactly 20 relevant technologies from OpenAI.
    However, OpenAI may return fewer items or empty lists. The parse_skills_response()
    function includes fallback logic to handle these edge cases.

    See: https://github.com/BenjaminLarger/simpleApply/issues (Compétences & Outils not filling)

    Args:
        job_offer: Parsed job offer information
        user_profile: User's complete profile
        user_technologies: Technologies from user's experience
        user_achievements: All user achievements

    Returns:
        Formatted prompt string
    """
    language_map = {
        "en": "English",
        "fr": "French",
        "es": "Spanish"
    }
    target_language = language_map.get(job_offer.language, "English")

    return f"""
You are an expert career counselor and skills matcher. Analyze the job requirements against the user's profile and intelligently match skills, technologies, and achievements.

**IMPORTANT**: The job offer is in {target_language}. You MUST:
1. Return all matched_skills and relevant_technologies in {target_language}
2. Translate all user profile content from English to {target_language}
3. **PRESERVE TECHNICAL TERMS IN ENGLISH**: Python, JavaScript, Docker, React, Django, AWS, SQL, etc. should remain in English
4. Translate soft skills and descriptions naturally

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
    "user_skills": ["List of all user's skills and technologies - in {target_language} with technical terms in English"],
    "job_skills": ["List of all job required skills - in {target_language} with technical terms in English"],
    "matched_skills": ["Skills that match - in {target_language} with technical terms in English"],
    "relevant_technologies": ["20 most relevant technologies - in {target_language} with technical terms in English"],
    "key_value_contributions": [
        "First dynamic paragraph explaining project experience relevant to this job",
        "Second paragraph highlighting professional achievements that align with requirements",
        "Third paragraph showcasing technical expertise and value to organization",
        "Optional fourth paragraph if particularly strong match exists",
        "Optional fifth paragraph for exceptional cases"
    ]
}}

Guidelines for matching:
1. MATCHED SKILLS: Include exact matches and close semantic matches (e.g., "Python" matches "Python development", "REST API" matches "RESTful APIs")
2. RELEVANT TECHNOLOGIES: Return exactly 20 relevant technologies. Prioritize technologies mentioned in job requirements, but also include related ones from user's experience
3. KEY VALUE CONTRIBUTIONS: Generate 3-5 CONCISE STATEMENTS demonstrating how user adds value to this specific organization:
   - Each statement: MAXIMUM 350 CHARACTERS
   - Focus on VALUE TO THE ORGANIZATION (not just listing skills)
   - Mention SPECIFIC PROJECTS from user profile that demonstrate relevant experience
   - Highlight PROFESSIONAL ACHIEVEMENTS from experiences that align with job requirements
   - Use HIGH VARIABILITY - each statement should be unique and contextual to this specific job
   - Write in {target_language} (preserve technical terms in English)
   - Use first-person narrative ("I have experience...", "My work on...")
   - Demonstrate FIT FOR THE POSITION through concrete examples
4. Consider transferable skills and related technologies (e.g., if job requires React and user has JavaScript experience)
5. Prioritize recent and significant experiences over older ones
6. Include both technical and soft skills where relevant
7. Keep all technical terms and programming languages in English

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

        required_fields = ["user_skills", "job_skills", "matched_skills", "relevant_technologies", "key_value_contributions"]
        for field in required_fields:
            if field not in skills_data:
                raise SkillsMatcherError(f"Missing required field: {field}")

        for field in required_fields:
            if not isinstance(skills_data[field], list):
                skills_data[field] = []

        # CRITICAL FIX: Ensure relevant_technologies is never empty (prevents blank "Compétences & Outils" section)
        # This is the most critical field for CV generation - if empty, the skills section appears blank
        if not skills_data.get("relevant_technologies") or len(skills_data["relevant_technologies"]) == 0:
            # Fallback: Use matched_skills as base for technologies
            fallback_technologies = skills_data.get("matched_skills", [])
            if fallback_technologies:
                # Extend to at least 10 items if possible by combining with job skills
                if len(fallback_technologies) < 10:
                    fallback_technologies = fallback_technologies + skills_data.get("job_skills", [])
                skills_data["relevant_technologies"] = fallback_technologies[:20]  # Limit to 20
            else:
                # Last resort: Use job skills if no matches found
                skills_data["relevant_technologies"] = skills_data.get("job_skills", ["Technology"])[:20]

        # CRITICAL FIX: Ensure key_value_contributions is never empty (prevents blank professional value section)
        # Each contribution should be a complete paragraph demonstrating value to the organization
        if not skills_data.get("key_value_contributions") or len(skills_data["key_value_contributions"]) == 0:
            skills_data["key_value_contributions"] = [
                "My software development and data science expertise enables me to deliver innovative technical solutions that drive measurable business impact.",
                "I bring a proven track record of collaborating with cross-functional teams to implement scalable systems and solve complex technical challenges.",
                "My experience spans full-stack development, cloud architecture, and AI integration, enabling me to contribute effectively across multiple technical domains."
            ]

        # Enforce 350 character limit per contribution (safety measure)
        # Truncate at word boundary to avoid cutting off mid-word
        contributions = skills_data.get("key_value_contributions", [])
        truncated_contributions = []
        for contrib in contributions:
            if len(contrib) > 350:
                # Truncate at 350 chars and find last space to avoid breaking words
                truncated = contrib[:350]
                last_space = truncated.rfind(" ")
                if last_space > 0:
                    truncated = truncated[:last_space]
                truncated_contributions.append(truncated.rstrip() + ".")
            else:
                truncated_contributions.append(contrib)
        skills_data["key_value_contributions"] = truncated_contributions

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
        print(f"Key Value Contributions: {len(matched_skills.key_value_contributions)} paragraphs generated")

    except Exception as e:
        print(f"Error: {e}")