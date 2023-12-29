#!/usr/bin/env python3

import yaml
import logging
import os
import subprocess
import tempfile
from contextlib import contextmanager
import click
import typing
import re
from typing import NamedTuple
import requests

logging.basicConfig()
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
RepositoryRef = NamedTuple("Repo", [("org", str), ("repo", str), ("branch", str)])


@contextmanager
def with_temporary_clone(repo: RepositoryRef):
    """
    context manager that clones a git branch and cd to it
    """
    repo_url = f"git@github.com:{repo.org}/{repo.repo}.git"

    with tempfile.TemporaryDirectory() as temp_dir:
        clone_cmd = [
            "git",
            "clone",
            "--branch",
            repo.branch,
            "--",
            repo_url,
            temp_dir,
        ]
        subprocess.check_call(clone_cmd)
        cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            yield
        finally:
            os.chdir(cwd)


def _extract_repository_refs(_ctx, _param, value) -> typing.List[RepositoryRef]:
    res = []
    for i in value:
        matches = re.match(
            r"([a-z0-9_\-\.]+)\/([a-z0-9_\-\.]+)#([a-z0-9_\-\.\/]+)", i, re.IGNORECASE
        )
        if not matches:
            raise click.BadParameter(
                f'Should match the format "org/repo#branch", found {i}'
            )
        res.append(
            RepositoryRef(
                org=matches.group(1), repo=matches.group(2), branch=matches.group(3)
            )
        )
    return res


def _create_github_pull(
    token,
    copier_branch,
    current_repo,
    copier_version_before,
    copier_version_after,
    is_clean,
) -> str | None:
    # Create the pull request
    # FIXME: Handle if the PR already exists, and then update it
    body = [
        f"Copier update from {copier_version_before} to {copier_version_after}"
        "\nPlease ensure that you check this PR carefully before merging."
    ]
    if not is_clean:
        body.append(
            ":warning: Manual intervention is required. The commit was not clean."
        )

    body.append(
        "This PR was raised using glodouk/odoo-scaffolding/tools/copier_update.py"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {
        "title": f"ci: copier template update {copier_version_before} to {copier_version_after}",
        "body": "\n\n".join(body),
        "head": f"{current_repo.org}:{copier_branch}",
        "base": current_repo.branch,
    }

    response = requests.post(
        f"https://api.github.com/repos/{current_repo.org}/{current_repo.repo}/pulls",
        headers=headers,
        json=payload,
    )

    if not response.ok:
        _logger.error(
            f"Failed to create PR for {current_repo}",
            response.status_code,
            response.text,
        )
        return None

    return response.json().get("html_url")


@click.command()
@click.option(
    "--repo",
    required=True,
    multiple=True,
    callback=_extract_repository_refs,
    help='Should match the format "org/repo#branch. Repeat for each repo',
)
@click.option("--token", required=True, help="GitHub Token to create PRs")
def main(repo: typing.List[RepositoryRef], token: str):
    results = []

    for current_repo in repo:
        _logger.info("Working on %s", current_repo)

        copier_branch = f"{current_repo.branch}-copier"

        with with_temporary_clone(current_repo):
            if not os.path.exists(".copier-answers.yml"):
                _logger.warning(
                    f" - skipping {current_repo} because it has no .copier-answers.yml"
                )
                continue

            with open(".copier-answers.yml", "r") as answers:
                copier_version_before = yaml.safe_load(answers.read()).get(
                    "_commit", "unknown"
                )

            subprocess.check_call(["git", "checkout", "-B", copier_branch])

            r = subprocess.call(["copier", "update", "--defaults", "--trust"])
            if r != 0:
                _logger.error(f" - copier update failed on {current_repo}")
                continue

            is_clean = False

            # 3 attempts for a clean run is ideal
            for _ in range(3):
                # make sure we've added any files which may have been modified
                subprocess.check_call(["git", "add", "."])
                r = subprocess.call(["pre-commit", "run", "-a"])
                if r == 0:
                    is_clean = True
                    break

            # make sure we've definitely got everything
            if not is_clean:
                subprocess.check_call(["git", "add", "."])

            # are there any differences?
            r = subprocess.call(["git", "diff", "--cached", "--quiet", "--exit-code"])
            if r == 0:
                # no, continue
                _logger.warn(f" - skipping {current_repo}, no changes pending")
                continue

            commit_cmd = [
                "git",
                "commit",
                "-m",
                "ci: copier update",
            ]
            if not is_clean:
                commit_cmd.append("--no-verify")

            with open(".copier-answers.yml", "r") as answers:
                copier_version_after = yaml.safe_load(answers.read()).get(
                    "_commit", "unknown"
                )

            # Push to GitHub
            subprocess.check_call(commit_cmd)
            subprocess.check_call(["git", "push", "-f", "-u", "origin", copier_branch])

            pull_url = _create_github_pull(
                token,
                copier_branch,
                current_repo,
                copier_version_before,
                copier_version_after,
                is_clean,
            )

            if pull_url:
                completion_msg = f"Created PR for {current_repo} - {pull_url}"
                _logger.info(completion_msg)
                results.append(completion_msg)

        for i in results:
            _logger.info(i)


if __name__ == "__main__":
    main()
