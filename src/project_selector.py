"""
Project selector module using OpenAI GPT.
Intelligently selects most relevant projects for job applications.
"""

import os
import json
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from .models import JobOffer, Project, SelectedProjects
from .cost_tracker import track_openai_call

# Load environment variables
load_dotenv()


class ProjectSelectorError(Exception):
    """Custom exception for project selection errors."""
    pass


def get_openai_client() -> OpenAI:
    """Get authenticated OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ProjectSelectorError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set your OpenAI API key in the .env file."
        )
    return OpenAI(api_key=api_key)


def select_projects(job_offer: JobOffer, projects: List[Project]) -> SelectedProjects:
    """
    Select the 2 most relevant projects based on job requirements using AI intelligence.

    Args:
        job_offer: Parsed job offer information
        projects: List of user's projects

    Returns:
        SelectedProjects: Selected projects with reasoning

    Raises:
        ProjectSelectorError: If selection fails or API error occurs
    """
    try:
        if len(projects) < 2:
            raise ProjectSelectorError(f"Need at least 2 projects, but only {len(projects)} available")

        # Get OpenAI client
        client = get_openai_client()

        # Prepare projects data for analysis
        projects_data = []
        for i, project in enumerate(projects):
            project_info = {
                "index": i,
                "title": project.title,
                "description": project.description,
                "technologies": project.technologies,
                "url": project.url,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "status": project.status
            }
            projects_data.append(project_info)

        # Create comprehensive prompt
        prompt = f"""
You are an expert career counselor specializing in project selection for job applications. Analyze the job requirements and select the 2 most relevant projects that best demonstrate the candidate's suitability for this role.

JOB OFFER:
- Title: {job_offer.job_title}
- Company: {job_offer.company_name}
- Location: {job_offer.location}
- Required Skills: {job_offer.skills_required}
- Description: {job_offer.description[:500]}...

AVAILABLE PROJECTS:
{json.dumps(projects_data, indent=2)}

Please analyze and return a JSON object with the following structure:
{{
    "project1_index": <index of first selected project>,
    "project2_index": <index of second selected project>,
    "selection_reasoning": "Detailed explanation of why these two projects were selected for this specific job role"
}}

Selection Criteria:
1. **Technology Stack Alignment**: Projects using technologies mentioned in job requirements get priority
2. **Relevance to Role**: Projects that demonstrate skills directly applicable to the job responsibilities
3. **Project Complexity**: More comprehensive projects that show advanced skills
4. **Recent Activity**: More recent projects generally preferred unless older ones are significantly more relevant
5. **Demonstrable Impact**: Projects with clear outcomes, URLs, or measurable results
6. **Complementary Skills**: Select projects that together cover different aspects of the job requirements

Guidelines:
- Choose projects that best showcase the candidate's fit for this specific role
- Ensure the two selected projects complement each other (don't pick two very similar projects)
- The reasoning should be specific to this job and explain the strategic thinking behind the selection

Return only the JSON object, no additional text.
"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            max_completion_tokens=4000,
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Track API call cost
        track_openai_call(response, "project_selection")

        # Extract and parse response
        response_text = response.choices[0].message.content.strip()

        try:
            # Parse JSON response
            selection_data = json.loads(response_text)

            # Validate required fields
            required_fields = ["project1_index", "project2_index", "selection_reasoning"]
            for field in required_fields:
                if field not in selection_data:
                    raise ProjectSelectorError(f"Missing required field: {field}")

            # Validate indices
            project1_index = selection_data["project1_index"]
            project2_index = selection_data["project2_index"]

            if not (0 <= project1_index < len(projects)):
                raise ProjectSelectorError(f"Invalid project1_index: {project1_index}")

            if not (0 <= project2_index < len(projects)):
                raise ProjectSelectorError(f"Invalid project2_index: {project2_index}")

            if project1_index == project2_index:
                raise ProjectSelectorError("Cannot select the same project twice")

            # Get selected projects
            selected_project1 = projects[project1_index]
            selected_project2 = projects[project2_index]

            # Create SelectedProjects model
            selected_projects = SelectedProjects(
                project1=selected_project1,
                project2=selected_project2,
                selection_reasoning=selection_data["selection_reasoning"]
            )

            return selected_projects

        except json.JSONDecodeError as e:
            raise ProjectSelectorError(f"Failed to parse JSON response from OpenAI: {e}\nResponse Text: {response_text}")

    except Exception as e:
        if isinstance(e, ProjectSelectorError):
            raise
        raise ProjectSelectorError(f"Unexpected error during project selection: {e}")


def select_projects_safe(job_offer: JobOffer, projects: List[Project]) -> SelectedProjects | None:
    """
    Safe version of select_projects that returns None on error instead of raising.

    Args:
        job_offer: Parsed job offer information
        projects: List of user's projects

    Returns:
        SelectedProjects or None: Selected projects or None if selection failed
    """
    try:
        return select_projects(job_offer, projects)
    except ProjectSelectorError as e:
        print(f"Project selection failed: {e}")
        return None


if __name__ == "__main__":
    # Test with sample data
    from job_parser import parse_job_offer
    import yaml

    # Sample job posting
    sample_job = """
    Senior AI Engineer - LangChain/LangGraph

    Company: AI Innovations Inc.
    Location: San Francisco, CA (Hybrid)

    We are looking for a Senior AI Engineer with experience in LangChain, LangGraph, and AI agent development.

    Requirements:
    - 3+ years experience with Python
    - Strong background in AI/ML and LLM applications
    - Experience with LangChain, LangGraph frameworks
    - Knowledge of Streamlit for prototyping
    - Experience with OpenAI or Claude APIs
    - Docker and cloud deployment experience
    - Experience building AI agents and workflow automation
    """

    try:
        # Parse job offer
        job_offer = parse_job_offer(sample_job)

        # Load user profile
        with open("templates/user_profile.yaml", "r") as f:
            profile_data = yaml.safe_load(f)

        # Extract projects
        projects = [Project(**project_data) for project_data in profile_data["projects"]]

        # Select projects
        selected_projects = select_projects(job_offer, projects)

        print("Project Selection Results:")
        print(f"Selected Project 1: {selected_projects.project1.title}")
        print(f"Selected Project 2: {selected_projects.project2.title}")
        print(f"\nSelection Reasoning:")
        print(selected_projects.selection_reasoning)

    except Exception as e:
        print(f"Error: {e}")