"""Reject commit identities that GitHub can attribute to the wrong account."""

from __future__ import annotations

import subprocess
import sys


ZERO_SHA = "0" * 40
GENERIC_GITHUB_EMAIL = "noreply@users.noreply.github.com"
SHARED_CONTRIBUTOR_EMAIL = "contributors@users.noreply.github.com"


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def email_from_identity(identity: str) -> str:
    opening = identity.rfind(" <")
    closing = identity.find(">", opening + 2)
    if opening == -1 or closing == -1:
        return ""
    return identity[opening + 2 : closing].strip()


def unsafe_reason(email: str) -> str | None:
    lowered = email.lower()
    if not email:
        return "the email address is missing"
    if lowered == GENERIC_GITHUB_EMAIL:
        return "the generic GitHub no-reply address belongs to another account"
    if lowered == SHARED_CONTRIBUTOR_EMAIL:
        return "the shared contributors address is not tied to the intended GitHub account"
    if "your_id+" in lowered:
        return "the email address still contains the YOUR_ID placeholder"
    return None


def reject(label: str, email: str, reason: str, commit: str | None = None) -> None:
    location = f" in commit {commit}" if commit else ""
    print(f"Blocked {label}{location}: {email or '(missing email)'}")
    print(f"Reason: {reason}.")
    print("Set user.email to the private no-reply address shown in GitHub Settings > Emails.")


def check_current_identity() -> int:
    failed = False
    for label, variable in (
        ("author identity", "GIT_AUTHOR_IDENT"),
        ("committer identity", "GIT_COMMITTER_IDENT"),
    ):
        email = email_from_identity(git("var", variable))
        reason = unsafe_reason(email)
        if reason:
            reject(label, email, reason)
            failed = True
    return 1 if failed else 0


def commits_for_push(local_sha: str, remote_sha: str, remote_name: str) -> list[str]:
    arguments = ["rev-list", local_sha]
    if remote_sha != ZERO_SHA:
        arguments.append(f"^{remote_sha}")
    else:
        arguments.extend(["--not", f"--remotes={remote_name}"])
    output = git(*arguments)
    return output.splitlines() if output else []


def check_commit(commit: str) -> bool:
    fields = git("show", "-s", "--format=%ae%n%ce", commit).splitlines()
    labels = ("author email", "committer email")
    failed = False
    for label, email in zip(labels, fields):
        reason = unsafe_reason(email.strip())
        if reason:
            reject(label, email.strip(), reason, commit)
            failed = True
    return failed


def check_push(remote_name: str) -> int:
    failed = False
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = fields
        if local_sha == ZERO_SHA:
            continue
        for commit in commits_for_push(local_sha, remote_sha, remote_name):
            failed = check_commit(commit) or failed
    return 1 if failed else 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--pre-push":
        remote_name = sys.argv[2] if len(sys.argv) >= 3 else "origin"
        return check_push(remote_name)
    return check_current_identity()


if __name__ == "__main__":
    raise SystemExit(main())
