"""Local IMAP Sandbox Driver"""

import os
import argparse
import subprocess
from pathlib import Path

import colorama


def colored(string: str, color: str) -> str:
    colors = {
        "green": colorama.Fore.GREEN,
        "red": colorama.Fore.RED,
    }
    return f"{colors[color.lower()]}{string}{colorama.Fore.RESET}"


MARKS = {
    "ok": colored("✓", "green"),
    "fail": colored("✗", "red"),
}
IMAP_BASE_DIR = Path(os.environ.get("IMAP_BASE_DIR", "~/imap")).expanduser()


def git(*args: str, cwd: str | Path, capture: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
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


def sync_repo(repo_dir: Path, force: bool = False) -> bool:
    if not force:
        if not git("status", "--porcelain", cwd=repo_dir):
            return False

    if not git("fetch", "--all", cwd=repo_dir):
        return False

    main_branch = get_main_branch(repo_dir)
    if main_branch is None:
        return False

    if not git("switch", main_branch, cwd=repo_dir):
        return False

    if not git("merge", "--ff-only", f"upstream/{main_branch}", cwd=repo_dir):
        return False

    return True


def sync_all(force: bool = False):
    imap_repos = [
        IMAP_BASE_DIR / "imap_processing",
        IMAP_BASE_DIR / "imap_L3_processing",
        IMAP_BASE_DIR / "imap-data-access",
        IMAP_BASE_DIR / "sds-data-manager",
    ]
    print("Syncing all IMAP repos...")

    for repo in imap_repos:
        if sync_repo(repo, force=force):
            print(f"  {MARKS['ok']} {repo.name}")
        else:
            print(f"  {MARKS['fail']} {repo.name}")


def status(args):
    print("status")


def main():
    parser = argparse.ArgumentParser(prog="imap")
    subparsers = parser.add_subparsers(required=True)

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--force", action="store_true")
    sync_parser.set_defaults(func=sync_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
