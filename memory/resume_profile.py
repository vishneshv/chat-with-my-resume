"""Build and load structured resume profile JSON from data/*.txt|md."""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "resume_profile.json"


def _parse_resume_txt(text: str) -> dict:
    name = "Vishnesh Vojjala"
    m = re.search(r"^Name:\s*(.+)$", text, re.M)
    if m:
        name = m.group(1).strip()

    role = ""
    m = re.search(r"^Role:\s*(.+)$", text, re.M)
    if m:
        role = m.group(1).strip()

    company = ""
    m = re.search(r"^Company:\s*(.+)$", text, re.M)
    if m:
        company = m.group(1).strip()

    skills_block = ""
    m = re.search(r"Core Skills:\s*\n(.*?)(?=\n[A-Z][a-z]+ \w+:|$)", text, re.S)
    if m:
        skills_block = m.group(1).strip()

    skills: list[str] = []
    for line in skills_block.splitlines():
        line = line.strip()
        if ":" in line:
            _, rest = line.split(":", 1)
            for part in re.split(r"[,;]", rest):
                p = part.strip()
                if p:
                    skills.append(p)

    achievements: list[str] = []
    in_ach = False
    for line in text.splitlines():
        if line.strip().startswith("Key Achievements:"):
            in_ach = True
            continue
        if in_ach:
            if line.strip().startswith("Certifications:") or line.strip().startswith("Education:"):
                break
            if line.strip().startswith("-"):
                achievements.append(line.strip().lstrip("- ").strip())

    education = ""
    m = re.search(r"Education:\s*\n(.*?)(?=\nCore Skills:|\nKey Achievements:|\Z)", text, re.S)
    if m:
        education = " ".join(m.group(1).split())

    experience = f"{role} at {company}" if role and company else role or company

    return {
        "name": name,
        "role": role,
        "company": company,
        "experience": experience,
        "education": education,
        "skills": skills[:40],
        "achievements": achievements[:20],
    }


def build_resume_profile_file() -> dict:
    """Parse data/resume.txt and write data/resume_profile.json."""
    resume_path = DATA_DIR / "resume.txt"
    if not resume_path.exists():
        profile = {
            "name": "Vishnesh Vojjala",
            "skills": [],
            "projects": [],
            "experience": "",
            "achievements": [],
            "education": "",
            "raw_note": "resume.txt not found",
        }
    else:
        text = resume_path.read_text(encoding="utf-8")
        profile = _parse_resume_txt(text)
        projects_md = DATA_DIR / "projects.md"
        projects: list[str] = []
        if projects_md.exists():
            content = projects_md.read_text(encoding="utf-8")
            for block in content.split("## ")[1:]:
                first_line = block.split("\n", 1)[0].strip()
                if first_line:
                    projects.append(first_line)
        profile["projects"] = projects[:30]

    if not profile.get("skills"):
        # Fallback: pull comma-separated tokens from Core Skills region
        if "Core Skills:" in text:
            block = text.split("Core Skills:", 1)[1]
            block = block.split("Key Achievements:", 1)[0]
            for line in block.splitlines():
                if ":" in line:
                    _, rest = line.split(":", 1)
                    for part in re.split(r"[,;]", rest):
                        p = part.strip()
                        if len(p) > 1:
                            profile.setdefault("skills", []).append(p)

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def load_resume_profile() -> dict:
    """Load cached profile; build file if missing."""
    if not PROFILE_PATH.exists():
        return build_resume_profile_file()
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return build_resume_profile_file()
