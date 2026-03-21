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
    # Flatten personal_info keys to top level for easy access by extension
    personal_info = profile.get("personal_info", {})
    return {
        "name": personal_info.get("name"),
        "email": personal_info.get("email"),
        "gender": personal_info.get("gender"),
        **{k: v for k, v in profile.items() if k != "personal_info"},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
