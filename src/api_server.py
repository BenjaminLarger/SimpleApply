"""FastAPI server exposing user profile data for the browser extension."""

import os
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="simpleApply API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET"],
    allow_headers=["*"],
)

PROFILE_PATH = Path(__file__).parent.parent / "templates" / "user_profile.yaml"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/profile")
def get_profile():
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    personal_info = profile.get("personal_info", {})
    urls = profile.get("urls", {})

    # Map experiences from YAML format to extension ProfileData.Experience format
    experiences = []
    for exp in profile.get("experiences", []):
        # Convert start_date "2025-01-01" → "2025-01"
        start = exp.get("start_date", "")
        if start and len(start) >= 7:
            start = start[:7]  # "YYYY-MM"
        end = exp.get("end_date", "")
        if end and len(end) >= 7:
            end = end[:7]
        experiences.append({
            "company": exp.get("company", ""),
            "role": exp.get("role", ""),
            "location": exp.get("location", ""),
            "start": start,
            "end": end,
            "description": ". ".join(exp.get("achievements", [])),
            "achievements": exp.get("achievements", []),
            "technologies": exp.get("technologies", []),
        })

    # Map education from YAML format to extension ProfileData.Education format
    education = []
    for edu in profile.get("education", []):
        # Parse duration "2023 – 2026" → startYear/endYear
        duration = edu.get("duration", "")
        start_year = ""
        end_year = ""
        if duration:
            parts = duration.replace("–", "-").replace("—", "-").split("-")
            if len(parts) >= 1:
                start_year = parts[0].strip()
            if len(parts) >= 2:
                end_year = parts[1].strip()
        education.append({
            "school": edu.get("institution", ""),
            "degree": edu.get("degree", ""),
            "fieldOfStudy": "",
            "gpa": "",
            "startYear": start_year,
            "endYear": end_year,
        })

    return {
        # Personal info fields
        "name": personal_info.get("name", ""),
        "email": personal_info.get("email", ""),
        "phone": personal_info.get("phone", "") or None,
        "phoneType": personal_info.get("phoneType", "") or None,
        "address": personal_info.get("address", "") or None,
        "city": personal_info.get("city", "") or None,
        "state": personal_info.get("state", "") or None,
        "postalCode": personal_info.get("postalCode", "") or None,
        "country": personal_info.get("country", "") or None,
        # URLs
        "linkedin": urls.get("linkedin", "") or None,
        "github": urls.get("github", "") or None,
        "portfolio": urls.get("portfolio", "") or None,
        # Structured data
        "experiences": experiences,
        "education": education,
        "skills": profile.get("skills", []),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
