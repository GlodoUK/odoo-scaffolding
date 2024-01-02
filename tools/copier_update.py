#!/usr/bin/env python3

import datetime
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
from jinja2 import Template


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


def _extract_repository_refs(ctx, param, value):
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


def _render_template(template_path: str, **kwargs) -> str:
    with open(template_path, "r", encoding="utf8") as tf:
        template = Template(tf.read())
        return template.render(**kwargs)


def _create_or_update_github_pr(
    token: str,
    head: str,
    current_repo: RepositoryRef,
    title: str,
    body: str,
) -> str | None:
    # Create the pull request
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "title": title,
        "body": body,
        "head": f"{current_repo.org}:{head}",
        "base": current_repo.branch,
    }

    existing_response = requests.get(
        f"https://api.github.com/repos/{current_repo.org}/{current_repo.repo}/pulls?state=open&head={current_repo.org}:{head}&base={current_repo.branch}",
        headers=headers,
    )

    if existing_response.ok:
        existing = next(iter(existing_response.json()), {})
        if existing.get("number"):
            number = existing.get("number")
            requests.patch(
                f"https://api.github.com/repos/{current_repo.org}/{current_repo.repo}/pulls/{number}",
                headers=headers,
                json=payload,
            )
            return existing.get("html_url")

    response = requests.post(
        f"https://api.github.com/repos/{current_repo.org}/{current_repo.repo}/pulls",
        headers=headers,
        json=payload,
    )

    if response.ok:
        return response.json().get("html_url")

    _logger.warning(
        f"Failed to create PR for {current_repo}: %s %s",
        response.status_code,
        response.text,
    )

    return None


@click.command()
@click.option(
    "--repo",
    required=True,
    multiple=True,
    callback=_extract_repository_refs,
    help='Should match the format "org/repo#branch. Repeat for each repo',
)
@click.option("--github-auth-token", required=True, help="GitHub Token to create PRs")
@click.option(
    "--pull-request-body-template",
    default=os.path.join(
        os.path.dirname(__file__),
        "copier_update-body.md.jinja",
    ),
    help="Template file to use for pull request template",
)
def main(
    repo: typing.List[RepositoryRef],
    github_auth_token: str,
    pull_request_body_template: str,
):
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
                answers = yaml.safe_load(answers.read())
                copier_version_before = answers.get("_commit", "unknown")
                copier_template_url = answers.get("_src_path", "unknown")

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

            # Make sure we've definitely got everything
            if not is_clean:
                subprocess.check_call(["git", "add", "."])

            # Are there any differences?
            r = subprocess.call(["git", "diff", "--cached", "--quiet", "--exit-code"])
            if r == 0:
                # No, continue
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

            # Create pull request
            pull_url = _create_or_update_github_pr(
                github_auth_token,
                copier_branch,
                current_repo,
                title=f"ci: copier template update {copier_version_before} to {copier_version_after}",
                body=_render_template(
                    pull_request_body_template,
                    copier_template_url=copier_template_url,
                    copier_version_before=copier_version_before,
                    copier_version_after=copier_version_after,
                    is_clean=is_clean,
                    now=datetime.datetime.now(),
                    current_repo=current_repo,
                ),
            )

            if pull_url:
                completion_msg = f"Created/Updated PR for {current_repo} - {pull_url}"
                _logger.info(completion_msg)
                results.append(completion_msg)

        for i in results:
            _logger.info(i)


if __name__ == "__main__":
    main()
