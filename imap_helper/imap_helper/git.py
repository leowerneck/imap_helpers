import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FetchUpdate:
    """A ref update reported by ``git fetch --porcelain``."""

    flag: str
    remote: str | None
    branch: str
    ref: str

    @property
    def added(self) -> bool:
        return self.flag == "*"

    @property
    def pruned(self) -> bool:
        return self.flag == "-"


@dataclass(frozen=True)
class SyncResult:
    """Structured result of synchronizing one repository."""

    ok: bool
    main_branch: str | None = None
    starting_branch: str | None = None
    fetch_updates: list[FetchUpdate] = field(default_factory=list)
    main_updated: bool = False
    push_requested: bool = False
    pushed: bool = False
    error: str | None = None


def git(
    *args: str, cwd: str | Path, verbose: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run ``git <args>`` in ``cwd`` and retain its output."""
    if verbose:
        print(f"Running: {' '.join(['git', *args])!r}")
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def parse_fetch_output(output: str) -> list[FetchUpdate]:
    """Parse the output from ``git fetch --porcelain``."""
    updates: list[FetchUpdate] = []

    for line in output.splitlines():
        # The flag may itself be a space, so it cannot be parsed with split().
        if len(line) < 3 or line[1] != " ":
            continue

        flag = line[0]
        fields = line[2:].split(maxsplit=2)
        if len(fields) != 3:
            continue
        _old_oid, _new_oid, ref = fields

        remote = None
        branch = ref
        remote_prefix = "refs/remotes/"
        if ref.startswith(remote_prefix):
            remote_and_branch = ref.removeprefix(remote_prefix)
            if "/" in remote_and_branch:
                remote, branch = remote_and_branch.split("/", maxsplit=1)

        updates.append(FetchUpdate(flag, remote, branch, ref))

    return updates


def parse_push_changed(output: str) -> bool:
    """Return whether porcelain push output contains a changed remote ref."""
    for line in output.splitlines():
        fields = line.split("\t", maxsplit=2)
        if len(fields) == 3 and fields[0] in {" ", "*", "+", "-"}:
            return True
    return False


def get_main_branch(repo_dir: str | Path, verbose: bool = False) -> str | None:
    """Get the name of a repo's main branch."""
    for name in ["main", "dev"]:
        result = git(
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/remotes/upstream/{name}",
            cwd=repo_dir,
            verbose=verbose,
        )
        if result.returncode == 0:
            return name

    return None


def get_repo_name(repo_dir: str | Path) -> str | None:
    """Get the preferred remote repository name for `repo_dir`."""
    for remote in ("upstream", "origin"):
        result = git("remote", "get-url", remote, cwd=repo_dir)
        if result.returncode == 0:
            repo_url = result.stdout.strip().removesuffix(".git")
            return repo_url.rsplit("/", maxsplit=1)[-1]

    return None


def _failure(
    message: str,
    *,
    main_branch: str | None = None,
    starting_branch: str | None = None,
    fetch_updates: list[FetchUpdate] | None = None,
    main_updated: bool = False,
    push_requested: bool = False,
    pushed: bool = False,
) -> SyncResult:
    return SyncResult(
        ok=False,
        main_branch=main_branch,
        starting_branch=starting_branch,
        fetch_updates=fetch_updates or [],
        main_updated=main_updated,
        push_requested=push_requested,
        pushed=pushed,
        error=message,
    )


def _restore_checkout(
    repo_dir: Path,
    *,
    starting_branch: str | None,
    starting_commit: str,
    main_branch: str,
    verbose: bool,
) -> str | None:
    """Restore the branch (or detached commit) checked out before syncing."""
    if starting_branch == main_branch:
        return None

    if starting_branch:
        result = git("switch", starting_branch, cwd=repo_dir, verbose=verbose)
        target = starting_branch
    else:
        result = git(
            "switch", "--detach", starting_commit, cwd=repo_dir, verbose=verbose
        )
        target = starting_commit

    if result.returncode != 0:
        return result.stderr.strip() or f"could not restore checkout {target}"
    return None


def sync_repo(
    repo_dir: Path,
    *,
    force: bool = False,
    push: bool = False,
    verbose: bool = False,
) -> SyncResult:
    """Fetch, fast-forward the main branch, and optionally push it."""
    status = git("status", "--porcelain", cwd=repo_dir, verbose=verbose)
    if status.returncode != 0:
        return _failure(status.stderr.strip() or "could not read repository status")
    if status.stdout and not force:
        return _failure("working tree has uncommitted changes")

    branch_result = git("branch", "--show-current", cwd=repo_dir, verbose=verbose)
    if branch_result.returncode != 0:
        return _failure(
            branch_result.stderr.strip() or "could not determine current branch"
        )
    starting_branch = branch_result.stdout.strip() or None

    commit_result = git("rev-parse", "HEAD", cwd=repo_dir, verbose=verbose)
    if commit_result.returncode != 0:
        return _failure(
            commit_result.stderr.strip() or "could not resolve starting HEAD",
            starting_branch=starting_branch,
        )
    starting_commit = commit_result.stdout.strip()

    fetch = git(
        "fetch", "--porcelain", "--all", "--prune", cwd=repo_dir, verbose=verbose
    )
    fetch_updates = parse_fetch_output(fetch.stdout)
    if fetch.returncode != 0:
        return _failure(
            fetch.stderr.strip() or "fetch failed",
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )

    main_branch = get_main_branch(repo_dir, verbose=verbose)
    if main_branch is None:
        return _failure(
            "neither upstream/main nor upstream/dev exists",
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )

    switched = git("switch", main_branch, cwd=repo_dir, verbose=verbose)
    if switched.returncode != 0:
        return _failure(
            switched.stderr.strip() or f"could not switch to {main_branch}",
            main_branch=main_branch,
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )

    before = git("rev-parse", "HEAD", cwd=repo_dir, verbose=verbose)
    if before.returncode != 0:
        restore_error = _restore_checkout(
            repo_dir,
            starting_branch=starting_branch,
            starting_commit=starting_commit,
            main_branch=main_branch,
            verbose=verbose,
        )
        error = before.stderr.strip() or "could not resolve HEAD"
        if restore_error:
            error = f"{error}; {restore_error}"
        return _failure(
            error,
            main_branch=main_branch,
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )

    merged = git(
        "merge",
        "--ff-only",
        f"upstream/{main_branch}",
        cwd=repo_dir,
        verbose=verbose,
    )
    if merged.returncode != 0:
        restore_error = _restore_checkout(
            repo_dir,
            starting_branch=starting_branch,
            starting_commit=starting_commit,
            main_branch=main_branch,
            verbose=verbose,
        )
        error = merged.stderr.strip() or "fast-forward merge failed"
        if restore_error:
            error = f"{error}; {restore_error}"
        return _failure(
            error,
            main_branch=main_branch,
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )

    after = git("rev-parse", "HEAD", cwd=repo_dir, verbose=verbose)
    if after.returncode != 0:
        restore_error = _restore_checkout(
            repo_dir,
            starting_branch=starting_branch,
            starting_commit=starting_commit,
            main_branch=main_branch,
            verbose=verbose,
        )
        error = after.stderr.strip() or "could not resolve HEAD after merge"
        if restore_error:
            error = f"{error}; {restore_error}"
        return _failure(
            error,
            main_branch=main_branch,
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
        )
    main_updated = before.stdout.strip() != after.stdout.strip()

    pushed = False
    if push:
        push_result = git(
            "push",
            "--porcelain",
            "origin",
            main_branch,
            cwd=repo_dir,
            verbose=verbose,
        )
        if push_result.returncode != 0:
            restore_error = _restore_checkout(
                repo_dir,
                starting_branch=starting_branch,
                starting_commit=starting_commit,
                main_branch=main_branch,
                verbose=verbose,
            )
            error = push_result.stderr.strip() or "push failed"
            if restore_error:
                error = f"{error}; {restore_error}"
            return SyncResult(
                ok=False,
                main_branch=main_branch,
                starting_branch=starting_branch,
                fetch_updates=fetch_updates,
                main_updated=main_updated,
                push_requested=True,
                error=error,
            )
        pushed = parse_push_changed(push_result.stdout)

    restore_error = _restore_checkout(
        repo_dir,
        starting_branch=starting_branch,
        starting_commit=starting_commit,
        main_branch=main_branch,
        verbose=verbose,
    )
    if restore_error:
        return _failure(
            restore_error,
            main_branch=main_branch,
            starting_branch=starting_branch,
            fetch_updates=fetch_updates,
            main_updated=main_updated,
            push_requested=push,
            pushed=pushed,
        )

    return SyncResult(
        ok=True,
        main_branch=main_branch,
        starting_branch=starting_branch,
        fetch_updates=fetch_updates,
        main_updated=main_updated,
        push_requested=push,
        pushed=pushed,
    )
