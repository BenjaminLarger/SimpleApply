"""
Job offer parser module using OpenAI GPT.
Extracts structured job information from job posting text.
"""

import os
import json
from typing import Union
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from .models import JobOffer
from .cost_tracker import track_openai_call


# Load environment variables
load_dotenv()


class JobParserError(Exception):
    """Custom exception for job parsing errors."""
    pass


def get_openai_client() -> OpenAI:
    """Get authenticated OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise JobParserError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set your OpenAI API key in the .env file."
        )
    return OpenAI(api_key=api_key)


def load_job_content(job_text: Union[str, Path]) -> str:
    """
    Load job content from various input types.

    Args:
        job_text: Either raw job posting text or path to file containing job text

    Returns:
        Job content as string

    Raises:
        JobParserError: If content cannot be loaded or is empty
    """
    if isinstance(job_text, Path):
        with open(job_text, 'r', encoding='utf-8') as f:
            job_content = f.read()
    elif isinstance(job_text, str) and len(job_text) < 1000 and '\n' not in job_text and Path(job_text).exists():
        with open(job_text, 'r', encoding='utf-8') as f:
            job_content = f.read()
    else:
        job_content = str(job_text)

    if not job_content.strip():
        raise JobParserError("Job offer text is empty")

    return job_content


def create_job_parsing_prompt(job_content: str) -> str:
    """
    Create structured prompt for job parsing.

    Args:
        job_content: Raw job posting text

    Returns:
        Formatted prompt string
    """
    return f"""
You are an expert job posting analyzer. Extract structured information from the following job posting text and return it as valid JSON format.

Job Posting Text:
{job_content}

Please analyze the text and extract the following information in JSON format:
{{
    "job_title": "The specific job title/position",
    "company_name": "The company name",
    "skills_required": ["Array of required skills, technologies, programming languages, frameworks, etc."],
    "location": "Job location (city, state/country, or 'Remote')",
    "description": "The full original job posting text"
}}

Guidelines:
- Extract all technical skills, programming languages, frameworks, tools, and methodologies mentioned
- Include both hard and soft skills if clearly stated as requirements
- For location, include the most specific information available (city, state, country, or Remote/Hybrid)
- If information is not clearly stated, make reasonable inferences but avoid hallucinating details
- Ensure the JSON is valid and properly formatted
- Include the complete original job posting text in the description field

Return only the JSON object, no additional text or explanation.
"""


def call_openai_for_parsing(prompt: str):
    """
    Call OpenAI API for job parsing.

    Args:
        prompt: Formatted prompt for job parsing

    Returns:
        OpenAI API response

    Raises:
        JobParserError: If API call fails
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

    track_openai_call(response, "job_parsing")
    return response


def parse_job_response(response_text: str, job_content: str) -> JobOffer:
    """
    Parse OpenAI response and create JobOffer model.

    Args:
        response_text: JSON response from OpenAI
        job_content: Original job content for fallback description

    Returns:
        JobOffer model instance

    Raises:
        JobParserError: If parsing or validation fails
    """
    try:
        job_data = json.loads(response_text)

        required_fields = ["job_title", "company_name", "skills_required", "location"]
        for field in required_fields:
            if field not in job_data:
                raise JobParserError(f"Missing required field: {field}")

        if "description" not in job_data:
            job_data["description"] = job_content

        return JobOffer(**job_data)

    except json.JSONDecodeError as e:
        raise JobParserError(f"Failed to parse JSON response from OpenAI: {e}\nResponse Text: {response_text}")


def parse_job_offer(job_text: Union[str, Path]) -> JobOffer:
    """
    Parse job offer text using OpenAI to extract structured information.

    Args:
        job_text: Either raw job posting text or path to file containing job text

    Returns:
        JobOffer: Parsed job information as Pydantic model

    Raises:
        JobParserError: If parsing fails or API error occurs
    """
    try:
        job_content = load_job_content(job_text)
        prompt = create_job_parsing_prompt(job_content)
        response = call_openai_for_parsing(prompt)
        response_text = response.choices[0].message.content.strip()
        return parse_job_response(response_text, job_content)

    except Exception as e:
        if isinstance(e, JobParserError):
            raise
        raise JobParserError(f"Unexpected error during job parsing: {e}")


def parse_job_offer_safe(job_text: Union[str, Path]) -> Union[JobOffer, None]:
    """
    Safe version of parse_job_offer that returns None on error instead of raising.

    Args:
        job_text: Either raw job posting text or path to file containing job text

    Returns:
        JobOffer or None: Parsed job information or None if parsing failed
    """
    try:
        return parse_job_offer(job_text)
    except JobParserError as e:
        print(f"Job parsing failed: {e}")
        return None


if __name__ == "__main__":
    # Test with sample job posting
    sample_job = """
    Senior Software Engineer - Python & AI

    Company: TechCorp Inc.
    Location: San Francisco, CA (Hybrid)

    We are looking for an experienced Senior Software Engineer to join our AI team.

    Requirements:
    - 5+ years experience with Python
    - Strong background in machine learning and AI
    - Experience with FastAPI, Django, or Flask
    - Knowledge of Docker and AWS
    - Proficiency in SQL and PostgreSQL
    - Experience with REST APIs
    - Strong problem-solving skills

    Nice to have:
    - Experience with LangChain, LangGraph
    - Knowledge of Streamlit
    - Experience with Claude AI or OpenAI APIs
    """

    try:
        job_offer = parse_job_offer(sample_job)
        print("Parsed Job Offer:")
        print(f"Title: {job_offer.job_title}")
        print(f"Company: {job_offer.company_name}")
        print(f"Location: {job_offer.location}")
        print(f"Skills: {job_offer.skills_required}")
    except JobParserError as e:
        print(f"Error: {e}")