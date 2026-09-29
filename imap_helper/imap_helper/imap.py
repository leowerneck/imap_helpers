"""IMAP Helper Functions"""

import argparse
from collections import defaultdict
from pathlib import Path

from .constants import IMAP_BASE_DIR, IMAP_REPOS, SYMBOLS
from .git import FetchUpdate, SyncResult, get_repo_name, sync_repo


def _format_sync_result(repo_name: str, result: SyncResult) -> list[str]:
    """Format one repository's synchronization result for the terminal."""
    symbol = SYMBOLS["ok" if result.ok else "fail"]
    if not result.ok:
        detail = f" ({result.error})" if result.error else ""
        return [f"  {symbol} {repo_name}{detail}"]

    added = [update for update in result.fetch_updates if update.added]
    pruned = [update for update in result.fetch_updates if update.pruned]
    lines = [f"  {symbol} {repo_name}"]
    by_remote: dict[str, list[FetchUpdate]] = defaultdict(list)
    for update in [*added, *pruned]:
        by_remote[update.remote or "other refs"].append(update)

    for remote, updates in by_remote.items():
        lines.append(f"      {remote}:")
        for update in updates:
            marker = SYMBOLS["add"] if update.added else SYMBOLS["prune"]
            lines.append(f"        {marker} {update.branch}")

    if result.main_updated and result.main_branch:
        lines.append(f"      {SYMBOLS['sync']} {result.main_branch}")
    if result.pushed and result.main_branch:
        lines.append(f"      {SYMBOLS['push']} {result.main_branch}")

    return lines


def sync(args: argparse.Namespace) -> None:
    if args.all:
        imap_repos = [IMAP_BASE_DIR / repo for repo in IMAP_REPOS]
        if args.verbose:
            print("Syncing all of IMAP repos...")
    else:
        cwd = Path.cwd()
        repo_name = get_repo_name(cwd)
        if repo_name not in IMAP_REPOS:
            raise ValueError(f"Current repository ({repo_name!r}) is not an IMAP repo")

        imap_repos = [cwd]
        if args.verbose:
            print(f"Syncing IMAP repository {repo_name!r}...")

    for repo in imap_repos:
        if args.verbose:
            print(f"Attempting to sync repo '{repo.name}' ({repo})")
        result = sync_repo(repo, force=args.force, push=args.push, verbose=args.verbose)
        print("\n".join(_format_sync_result(repo.name, result)))


def _add_bool_arg(p: argparse.ArgumentParser, n: str, h: str):
    p.add_argument(f"-{n[0]}", f"--{n}", action="store_true", help=h)


def main():
    parser = argparse.ArgumentParser(prog="imap")
    subparsers = parser.add_subparsers(required=True)

    sync_parser = subparsers.add_parser("sync")
    _add_bool_arg(sync_parser, "all", "Sync all IMAP repositories")
    _add_bool_arg(sync_parser, "force", "Attempt sync even if repo not clean")
    _add_bool_arg(sync_parser, "push", "Push changes to origin after syncing")
    _add_bool_arg(sync_parser, "verbose", "Verbose output")
    sync_parser.set_defaults(func=sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
