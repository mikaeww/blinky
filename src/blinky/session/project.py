"""Name the project a session works in, from its git repository or folder.

Reads `.git/config` directly instead of running git: hooks fire on every tool call and
must stay fast. No network: the GitHub name comes from the `origin` URL.
"""

import configparser
import re
from pathlib import Path

# The last path segment of a remote URL, without ".git": git@github.com:me/rewa.git -> rewa
REMOTE_NAME = re.compile(r"[/:]([^/:]+?)(?:\.git)?/?$")
MAX_UP = 32


def _git_dir(root: Path) -> Path | None:
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        # Worktrees and submodules: ".git" is a file pointing at the real directory.
        target = dot_git.read_text().partition("gitdir:")[2].strip()
        git_dir = (root / target).resolve()
        common = git_dir / "commondir"
        return (git_dir / common.read_text().strip()).resolve() if common.is_file() else git_dir
    return None


def _origin_name(git_dir: Path) -> str | None:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read(git_dir / "config")
        url = parser.get('remote "origin"', "url", fallback="")
    except (configparser.Error, OSError):
        return None
    match = REMOTE_NAME.search(url.strip())
    return match.group(1) if match else None


def name_for(cwd: str) -> str:
    """Repo name from origin, else the repository folder, else the folder itself."""
    start = Path(cwd)
    candidate = start
    for _ in range(MAX_UP):
        try:
            git_dir = _git_dir(candidate)
        except OSError:
            git_dir = None
        if git_dir is not None:
            return _origin_name(git_dir) or candidate.name or str(candidate)
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return start.name or str(start)
