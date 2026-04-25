import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "vishneshv")

def get_github_client():
    return Github(GITHUB_TOKEN)

def github_get_repos() -> dict:
    try:
        g = get_github_client()
        user = g.get_user(GITHUB_USERNAME)
        repos = user.get_repos(sort="updated", direction="desc")

        repo_list = []
        for repo in repos:
            if not repo.fork:
                repo_list.append({
                    "name": repo.name,
                    "description": repo.description or "",
                    "language": repo.language or "Unknown",
                    "stars": repo.stargazers_count,
                    "url": repo.html_url,
                    "updated": str(repo.updated_at.date()),
                    "topics": repo.get_topics()
                })

        return {
            "success": True,
            "username": GITHUB_USERNAME,
            "total_repos": len(repo_list),
            "repos": repo_list[:10]  # top 10 most recently updated
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def github_get_repo_details(repo_name: str) -> dict:
    try:
        g = get_github_client()
        repo = g.get_repo(f"{GITHUB_USERNAME}/{repo_name}")

        # Get README
        try:
            readme = repo.get_readme()
            import base64
            readme_content = base64.b64decode(readme.content).decode("utf-8")[:1000]
        except Exception:
            readme_content = "No README available"

        # Get languages
        languages = repo.get_languages()

        return {
            "success": True,
            "name": repo.name,
            "description": repo.description or "",
            "languages": dict(languages),
            "stars": repo.stargazers_count,
            "url": repo.html_url,
            "readme_preview": readme_content,
            "updated": str(repo.updated_at.date()),
            "topics": repo.get_topics()
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def github_get_language_summary() -> dict:
    try:
        g = get_github_client()
        user = g.get_user(GITHUB_USERNAME)
        repos = user.get_repos()

        language_bytes = {}
        for repo in repos:
            if not repo.fork:
                langs = repo.get_languages()
                for lang, bytes_count in langs.items():
                    language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count

        # Sort by usage
        sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)

        return {
            "success": True,
            "languages": [{"language": l, "bytes": b} for l, b in sorted_langs[:8]]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
