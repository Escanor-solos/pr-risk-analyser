import os


def get_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")
    from github import Github

    return Github(token)


def fetch_diff(repo_fullname: str, pr_number: int) -> str:
    return _diff_via_api(repo_fullname, pr_number)


def _diff_via_api(repo_fullname: str, pr_number: int) -> str:
    import httpx

    token = os.environ["GITHUB_TOKEN"]
    resp = httpx.get(
        f"https://api.github.com/repos/{repo_fullname}/pulls/{pr_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def post_comment(repo_fullname: str, pr_number: int, body: str, dry_run: bool = True) -> bool:
    if dry_run:
        print(f"[dry-run] would post comment on {repo_fullname}#{pr_number}:\n{body}")
        return False
    client = get_client()
    repo = client.get_repo(repo_fullname)
    issue = repo.get_issue(pr_number)
    existing = [c for c in issue.get_comments() if c.user.login == "github-actions[bot]" or "Risk analysis" in c.body]
    marker = "<!-- pr-risk-analyzer -->"
    body = f"{marker}\n{body}"
    if existing:
        existing[-1].edit(body)
    else:
        issue.create_comment(body)
    return True
