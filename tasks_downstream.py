"""Doodba child project tasks.

This file is to be executed with https://www.pyinvoke.org/ in Python 3.6+.

Contains common helpers to develop using this child project.
"""
import json
import os
from glob import glob, iglob
from pathlib import Path

from invoke import task
from invoke.util import yaml

PROJECT_ROOT = Path(__file__).parent.absolute()
SRC_PATH = PROJECT_ROOT / "odoo" / "custom" / "src"
UID_ENV = {"GID": str(os.getgid()), "UID": str(os.getuid()), "UMASK": "27"}
COMMON_YAML = yaml.safe_load((PROJECT_ROOT / "common.yaml").read_text())
ODOO_VERSION = float(
    COMMON_YAML["services"]["odoo"][
        "build"
    ]["args"]["ODOO_VERSION"]
)
DB_USER = COMMON_YAML["services"]["odoo"]["environment"]["PGUSER"]


@task
def write_code_workspace_file(c, cw_path=None):
    """Generate code-workspace file definition.

    Some other tasks will call this one when needed, and since you cannot specify
    the file name there, if you want a specific one, you should call this task
    before.

    Most times you just can forget about this task and let it be run automatically
    whenever needed.

    If you don't define a workspace name, this task will reuse the 1st
    `doodba.*.code-workspace` file found inside the current directory.
    If none is found, it will default to `doodba.$(basename $PWD).code-workspace`.

    If you define it manually, remember to use the same prefix and suffix if you
    want it git-ignored by default.
    Example: `--cw-path doodba.my-custom-name.code-workspace`
    """
    if not cw_path:
        try:
            cw_path = next(iglob(str(PROJECT_ROOT / "doodba.*.code-workspace")))
        except StopIteration:
            cw_path = f"doodba.{PROJECT_ROOT.name}.code-workspace"
    if not Path(cw_path).is_absolute():
        cw_path = PROJECT_ROOT / cw_path
    cw_config = {}
    try:
        with open(cw_path) as cw_fd:
            cw_config = json.load(cw_fd)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        pass  # Nevermind, we start with a new config
    cw_config["folders"] = []
    addon_repos = glob(str(SRC_PATH / "*" / ".git" / ".."))
    for subrepo in sorted(addon_repos):
        subrepo = Path(subrepo).resolve()
        cw_config["folders"].append({"path": str(subrepo.relative_to(PROJECT_ROOT))})
    # HACK https://github.com/microsoft/vscode/issues/95963 put private second to last
    private = SRC_PATH / "private"
    if private.is_dir():
        cw_config["folders"].append({"path": str(private.relative_to(PROJECT_ROOT))})
    # HACK https://github.com/microsoft/vscode/issues/37947 put top folder last
    cw_config["folders"].append({"path": "."})
    with open(cw_path, "w") as cw_fd:
        json.dump(cw_config, cw_fd, indent=2)
        cw_fd.write("\n")


@task
def develop(c):
    """Set up a basic development environment."""
    # Prepare environment
    Path(PROJECT_ROOT, "odoo", "auto", "addons").mkdir(parents=True, exist_ok=True)
    with c.cd(str(PROJECT_ROOT)):
        c.run("git init")
        c.run("ln -sf devel.yaml docker-compose.yml")
        write_code_workspace_file(c)
        c.run("pre-commit install")


@task(develop)
def git_aggregate(c):
    """Download odoo & addons git code.

    Executes git-aggregator from within the doodba container.
    """
    with c.cd(str(PROJECT_ROOT)):
        c.run(
            "docker-compose --file setup-devel.yaml run --rm odoo",
            env=UID_ENV,
        )
    write_code_workspace_file(c)
    for git_folder in iglob(str(SRC_PATH / "*" / ".git" / "..")):
        action = (
            "install"
            if Path(git_folder, ".pre-commit-config.yaml").is_file()
            else "uninstall"
        )
        with c.cd(git_folder):
            c.run(f"pre-commit {action}")


@task(develop)
def img_build(c, pull=True, no_cache=False):
    """Build docker images."""
    cmd = "docker-compose build"
    if pull:
        cmd += " --pull"
    if no_cache:
        cmd += " --no-cache"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=UID_ENV)


@task(develop)
def img_pull(c):
    """Pull docker images."""
    with c.cd(str(PROJECT_ROOT)):
        c.run("docker-compose pull")


@task(develop)
def lint(c, verbose=False):
    """Lint & format source code."""
    cmd = "pre-commit run --show-diff-on-failure --all-files --color=always"
    if verbose:
        cmd += " --verbose"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd)


@task(develop)
def start(c, detach=True, ptvsd=False):
    """Start environment."""
    cmd = "docker-compose up"
    if detach:
        cmd += " --detach"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=dict(UID_ENV, DOODBA_PTVSD_ENABLE=str(int(ptvsd))))


@task(
    develop,
    help={"purge": "Remove all related containers, networks images and volumes"},
)
def down(c, purge=False):
    """Take down and (optionally) purge environment."""
    cmd = "docker-compose down"
    if purge:
        cmd += " --remove-orphans --rmi local --volumes"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd)


@task(develop)
def stop(c):
    """Stop the environment."""
    cmd = "docker-compose stop"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd)


@task(develop)
def stopstart(c, detach=True, ptvsd=False):
    """Stop the environment."""
    cmd = "docker-compose stop && docker-compose up"
    if detach:
        cmd += " --detach"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=dict(UID_ENV, DOODBA_PTVSD_ENABLE=str(int(ptvsd))))


@task(
    develop,
    help={
        "dbname": "The DB that will be DESTROYED and recreated. Default: 'devel'.",
        "modules": "Comma-separated list of modules to install. Default: 'base'.",
    },
)
def resetdb(c, modules="base", dbname="devel"):
    """Reset the specified database with the specified modules.

    Uses click-odoo-initdb behind the scenes, which has a caching system that
    makes DB resets quicker. See its docs for more info.
    """
    with c.cd(str(PROJECT_ROOT)):
        c.run("docker-compose stop odoo", pty=True)
        _run = "docker-compose run --rm -l traefik.enable=false odoo"
        c.run(
            f"{_run} click-odoo-dropdb {dbname}",
            env=UID_ENV,
            warn=True,
            pty=True,
        )
        c.run(
            f"{_run} click-odoo-initdb -n {dbname} -m {modules}",
            env=UID_ENV,
            pty=True,
        )


@task(develop)
def restart(c, quick=True):
    """Restart odoo container(s)."""
    cmd = "docker-compose restart"
    if quick:
        cmd = f"{cmd} -t0"
    cmd = f"{cmd} odoo odoo_proxy"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=UID_ENV)


@task(develop)
def logs(c, tail=10):
    """Obtain last logs of current environment."""
    cmd = "docker-compose logs -f"
    if tail:
        cmd += f" --tail {tail}"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd)


@task(develop)
def psql(c, db=None):
    """Get an interactive psql shell"""
    cmd = f"docker-compose exec db psql -U {DB_USER}"

    if db:
        cmd += f" {db}"
    else:
        cmd += " postgres"
    c.run(cmd, pty=True)


@task(develop)
def shell(c, db=None, native=True):
    """
    Get an Odoo shell. By default it will use the native odoo shell, unless
    specified, or ODOO_MAJOR <= 10.
    """
    shell_cmd = "shell"

    if not native or ODOO_VERSION <= 10.0:
        shell_cmd = "click-odoo"

    cmd = f"docker-compose run --rm odoo {shell_cmd}"
    if db:
        cmd += f" -d {db}"

    c.run(cmd, pty=True)


@task(develop)
def scaffold(c, name):
    """Create a scaffold using Odoo's built in scaffolding"""
    custom_path = PROJECT_ROOT / "odoo" / "custom"
    cmd = (
        f"docker-compose run --volume '{custom_path}:/opt/odoo/custom:rw,z'"
        f" --rm odoo odoo scaffold {name} /opt/odoo/custom/src/private"
    )
    c.run(cmd)


@task(develop)
def upgrade(c, db=None, include_core=False):
    """
    Upgrade all Odoo addons
    Ignores core addons by default.
    User --include-core to include them
    """
    cmd = "docker-compose exec odoo click-odoo-update"
    if not include_core:
        cmd += " --ignore-core-addons"
    if db:
        cmd += f" -d {db}"

    c.run(cmd, pty=True)


@task(develop)
def tests(c, db, install):
    """Run the unit tests for a module"""
    cmd = (
        f"docker-compose run"
        f" --rm odoo odoo --test-enable -d {db} -i {install}"
        f" --stop-after-init --no-http"
    )
    c.run(cmd, pty=True)


@task(develop)
def create_module_ssh_config(c, customer, target_repo):
    cmd_key = (
        f"ssh-keygen -t ed25519 -C '{customer}' -N '' -f odoo/custom/ssh/glodouk_{target_repo}_ed25519"
    )

    # Create the key
    c.run(cmd_key, pty=True)

    config_str = (
        f"\nHost glodouk_{target_repo}.github.com\n"
        f"    HostName github.com\n"
        f"    User git\n"
        f"    IdentityFile ~/.ssh/glodouk_{target_repo}_id_rsa\n"
        f"    IdentitiesOnly yes\n"
        f"    StrictHostKeyChecking no"
        )

    cmd_config = f"echo '{config_str}' >> odoo/custom/ssh/config"

    # Append Config
    c.run(cmd_config, pty=True)

    repo_str = (
        f"\n./glodouk_{target_repo}:\n"
        f"  defaults:\n"
        f"    depth: $DEPTH_DEFAULT\n"
        f"  remotes:\n"
        f"    glodo: git@glodouk_{target_repo}.github.com:GlodoUK/{target_repo}.git\n"
        f"  target: glodo $ODOO_VERSION\n"
        f"  merges:\n"
        f"    - glodo $ODOO_VERSION"
    )

    cmd_repo = f"echo '{repo_str}' >> odoo/custom/src/repos.yaml"

    c.run(cmd_repo, pty=True)

    addons_str = f"glodouk_{target_repo}: [\"*\"]"
    cmd_addons = f"echo '{addons_str}' >> odoo/custom/src/addons.yaml"
    c.run(cmd_addons, pty=True)
