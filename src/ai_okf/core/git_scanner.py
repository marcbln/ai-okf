from pathlib import Path

from git import GitCommandError, Repo


def get_git_summary(path: Path) -> str:
    try:
        repo = Repo(path)
        if repo.bare or not repo.head.is_valid():
            return ""
        commits = list(repo.iter_commits(max_count=30))
        if not commits:
            return ""
        lines = [f"Branch: {repo.active_branch.name}"]
        lines.append(f"Total commits: {sum(1 for _ in repo.iter_commits())}")
        lines.append("Recent activity (last 10 commits):")
        for c in commits[:10]:
            date = c.committed_datetime.strftime("%Y-%m-%d")
            raw = c.message
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            msg = raw.split("\n")[0][:80]
            lines.append(f"  [{date}] {c.hexsha[:8]} {msg}")
        return "\n".join(lines)
    except (GitCommandError, Exception):
        return ""


def get_changes_since(path: Path, since_ref: str = "HEAD") -> str:
    try:
        repo = Repo(path)
        if repo.bare or not repo.head.is_valid():
            return ""
        diff = repo.git.diff(since_ref, "--stat")
        log = repo.git.log(since_ref, "--oneline", "--max-count=20")
        return f"Changes since {since_ref}:\n{diff}\n\nRecent commits:\n{log}"
    except (GitCommandError, Exception):
        return ""
