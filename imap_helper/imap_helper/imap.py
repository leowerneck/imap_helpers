"""IMAP Helper Functions"""

import argparse
import subprocess
from pathlib import Path

from imap_helper.constants import IMAP_BASE_DIR, IMAP_REPOS, PROGRESS_SYMBOLS


def git(*args: str, cwd: str | Path, capture: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )


def get_main_branch(repo_dir: str | Path) -> str | None:
    for name in ["main", "dev"]:
        if git(
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/remotes/upstream/{name}",
            cwd=repo_dir,
        ):
            return name

    return None


def get_repo_name(repo_dir: str | Path) -> str | None:
    repo_url = subprocess.check_output(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_dir,
        text=True,
    ).strip()
    if repo_url.endswith(".git"):
        return repo_url.split("/")[-1][:-4]

    return repo_url.split("/")[-1]


def sync_repo(repo_dir: Path, force: bool = False) -> bool:
    if not force and not git("status", "--porcelain", cwd=repo_dir):
        return False

    if not git("fetch", "--all", cwd=repo_dir):
        return False

    main_branch = get_main_branch(repo_dir)
    if main_branch is None:
        return False

    if not git("switch", main_branch, cwd=repo_dir):
        return False

    return not git("merge", "--ff-only", f"upstream/{main_branch}", cwd=repo_dir)


def sync(args: argparse.Namespace) -> None:
    if args.all:
        imap_repos = [IMAP_BASE_DIR / repo for repo in IMAP_REPOS]
        print("Syncing all of IMAP repos...")
    else:
        cwd = Path.cwd()
        repo_name = get_repo_name(cwd)
        if repo_name not in IMAP_REPOS:
            raise ValueError(f"Current repository ({repo_name!r}) is not an IMAP repo")

        imap_repos = [cwd]
        print(f"Syncing IMAP repository {repo_name!r}...")

    for repo in imap_repos:
        if sync_repo(repo, force=args.force):
            print(f"  {PROGRESS_SYMBOLS['ok']} {repo.name}")
        else:
            print(f"  {PROGRESS_SYMBOLS['fail']} {repo.name}")


def main():
    parser = argparse.ArgumentParser(prog="imap")
    subparsers = parser.add_subparsers(required=True)

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument(
        "-a", "--all", action="store_true", help="Sync all IMAP repositories"
    )
    sync_parser.add_argument(
        "-f", "--force", action="store_true", help="Attempt sync even if repo not clean"
    )
    sync_parser.set_defaults(func=sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
