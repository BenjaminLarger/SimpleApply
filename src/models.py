"""
Pydantic data models for the AI-Powered Job Application System.
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Model for parsed job offer information."""
    job_title: str = Field(..., description="The job title/position")
    company_name: str = Field(..., description="Company name")
    skills_required: List[str] = Field(..., description="Required skills and technologies")
    location: str = Field(..., description="Job location")
    description: str = Field(..., description="Full job description text")
    language: str = Field(default="en", description="Detected language of job offer (en, fr, es)")


class PersonalInfo(BaseModel):
    """Personal information from user profile."""
    name: str
    email: str
    gender: str = Field(default="male", description="Gender for pronoun and title adaptation (male/female)")


class Experience(BaseModel):
    """Work experience entry."""
    company: str
    role: str
    start_date: str
    end_date: str
    location: str
    technologies: List[str]
    achievements: List[str]


class Education(BaseModel):
    """Education entry."""
    institution: str
    duration: str
    degree: str
    details: List[str]


class Project(BaseModel):
    """Side project or freelance project entry."""
    title: str
    description: str
    technologies: List[str]
    url: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = ""
    type: str = "Side Project"  # "Freelance" or "Side Project"


class UserProfile(BaseModel):
    """Complete user profile model matching YAML structure."""
    personal_info: PersonalInfo
    experiences: List[Experience]
    skills: List[str]
    education: List[Education]
    projects: List[Project]
    languages: List[str]
    achievements: List[str]
    hobbies: List[str]
    urls: dict = Field(default_factory=dict)


class MatchedSkills(BaseModel):
    """Skills matching results."""
    user_skills: List[str] = Field(..., description="User's available skills")
    job_skills: List[str] = Field(..., description="Job required skills")
    matched_skills: List[str] = Field(..., description="Skills that match between user and job")
    relevant_technologies: List[str] = Field(..., description="Most relevant technologies to highlight")
    key_value_contributions: List[str] = Field(..., description="3-5 dynamic paragraphs demonstrating how user adds value to the organization")


class SelectedProjects(BaseModel):
    """Selected projects for CV/cover letter."""
    project1: Project = Field(..., description="First selected project")
    project2: Project = Field(..., description="Second selected project")
    selection_reasoning: str = Field(..., description="Why these projects were selected")


class GeneratedContent(BaseModel):
    """Generated CV and cover letter content."""
    cv_html: str = Field(..., description="Generated CV HTML content")
    cover_letter_html: str = Field(..., description="Generated cover letter HTML content")
    job_offer: JobOffer = Field(..., description="Parsed job offer")
    matched_skills: MatchedSkills = Field(..., description="Skills matching results")
    selected_projects: SelectedProjects = Field(..., description="Selected projects")