"""
This file is to be executed with https://www.pyinvoke.org/ in Python 3.6+.

Contains common helpers to develop using this project.
"""
import os
import tempfile
import time
from logging import getLogger
from pathlib import Path

from invoke import exceptions, task
from invoke.util import yaml

PROJECT_ROOT = Path(__file__).parent.absolute()
SRC_PATH = PROJECT_ROOT / "odoo" / "custom" / "src"
UID_ENV = {"GID": str(os.getgid()), "UID": str(os.getuid()), "UMASK": "27"}
SERVICES_WAIT_TIME = int(os.environ.get("SERVICES_WAIT_TIME", 1))
ODOO_VERSION = float(
    yaml.safe_load((PROJECT_ROOT / "devel.yaml").read_text())["services"]["odoo"][
        "build"
    ]["args"]["ODOO_VERSION"]
)
DB_USER = yaml.safe_load((PROJECT_ROOT / "devel.yaml").read_text())["services"]["odoo"][
    "environment"
]["PGUSER"]


_logger = getLogger(__name__)


def _override_docker_env(database=False):
    extra_env = UID_ENV
    if database and isinstance(database, str):
        extra_env["PGDATABASE"] = database
    return extra_env


def _override_docker_command(service, command, file, orig_file=None):
    # Read config from main file
    if orig_file:
        with open(orig_file) as fd:
            orig_docker_config = yaml.safe_load(fd.read())
            docker_compose_file_version = orig_docker_config.get("version")
    else:
        docker_compose_file_version = "2.4"
    docker_config = {
        "version": docker_compose_file_version,
        "services": {service: {"command": command}},
    }
    docker_config_yaml = yaml.dump(docker_config)
    file.write(docker_config_yaml)
    file.flush()


def _remove_auto_reload(file, orig_file):
    with open(orig_file) as fd:
        orig_docker_config = yaml.safe_load(fd.read())
    odoo_command = orig_docker_config["services"]["odoo"]["command"]
    new_odoo_command = []
    for flag in odoo_command:
        if flag.startswith("--dev"):
            flag = flag.replace("reload,", "")
        new_odoo_command.append(flag)
    _override_docker_command("odoo", new_odoo_command, file, orig_file=orig_file)


def _get_cwd_addon(file):
    cwd = Path(file).resolve()
    manifest_file = False
    while PROJECT_ROOT < cwd:
        manifest_file = (cwd / "__manifest__.py").exists() or (
            cwd / "__openerp__.py"
        ).exists()
        if manifest_file:
            return cwd.stem
        cwd = cwd.parent
        if cwd == PROJECT_ROOT:
            return None


@task
def develop(c):
    """Set up a basic development environment."""
    # Prepare environment
    Path(PROJECT_ROOT, "odoo", "auto", "addons").mkdir(parents=True, exist_ok=True)
    with c.cd(str(PROJECT_ROOT)):
        c.run("git init")
        c.run("ln -sf devel.yaml docker-compose.yml")
        c.run("pre-commit install")


@task(develop)
def git_aggregate(c, local=False, pre_commit_install=True):
    """Download odoo & addons git code.

    Executes git-aggregator from within the doodba container, or locally if specified.
    """

    if local:
        if not shutil.which('gitaggregate'):
            raise FileNotFoundError(
                "Asked to gitaggregate locally, but could not find gitaggregate on"
                " path. Perhaps you need to run `pipx install gitaggregator`?"
            )

        _logger.warn("Running git-aggregate locally is currently experimental!")

        # XXX: Why run locally? So that we can start using git-autoshare!
        # 
        # If we have been asked to run gitaggregate locally, we need to massage the ssh
        # config file a bit by replacing the ~/.ssh path with the path to where it is in
        # the project, in order to maintain compatibility.
        #
        # We do this through a temporary file, which is automatically cleaned up
        # afterwards.
        #
        # If we want to remove gitaggregate from running inside the container, then we
        # can look at removing this workaround entirely. If this was the case, what do 
        # we want to do with the keys? Drop per-project keys entirely? 
        # Allow the developer to use their own keys? What about external contributors?
        with tempfile.NamedTemporaryFile(
            mode="w",
        ) as tmp_ssh_config:
            ssh_path = PROJECT_ROOT / "odoo" / "custom" / "ssh"

            with open(ssh_path / "config") as fd:
                config = fd.read().replace(
                    "IdentityFile ~/.ssh",
                    f"IdentityFile {str(ssh_path)}"
                )
                tmp_ssh_config.write(config)
                tmp_ssh_config.flush()

            extra_env = {
                # Tell git to use our custom ssh config file, which we've massaged
                "GIT_SSH_COMMAND": f"ssh -F {tmp_ssh_config.name}",
                # Some defaults that are normally provided through setup-devel.yaml,
                # which we are now by-passing
                "DEPTH_DEFAULT": os.environ.get("DEPTH_DEFAULT", "100"),
                "DEPTH_MERGE": os.environ.get("DEPTH_DEFAULT", "200"),
                "ODOO_VERSION": f"{ODOO_VERSION}",
            }

            concurrent_jobs = len(os.sched_getaffinity(0))

            with c.cd(SRC_PATH):
                c.run(
                    f"gitaggregate -e -c repos.yaml -j {concurrent_jobs}",
                    env=extra_env,
                    pty=True,
                )
    else:
        with c.cd(str(PROJECT_ROOT)):
            c.run(
                "docker compose --compatibility --file setup-devel.yaml run --rm odoo",
                env=_override_docker_env(),
                pty=True,
            )

    if pre_commit_install:
        for git_folder in SRC_PATH.glob("*/.git/.."):
            action = (
                "install"
                if (git_folder / ".pre-commit-config.yaml").is_file()
                else "uninstall"
            )
            with c.cd(str(git_folder)):
                c.run(f"pre-commit {action}")


@task(develop)
def closed_prs(c):
    with c.cd(str(PROJECT_ROOT)):
        cmd = (
            "docker compose --compatibility --file setup-devel.yaml run --rm --no-deps"
            ' --entrypoint="gitaggregate -c /opt/odoo/custom/src/repos.yaml'
            ' show-closed-prs" odoo'
        )
        c.run(cmd, env=_override_docker_env(), pty=True)


@task(develop)
def img_build(c, pull=True):
    """Build docker images."""
    cmd = "docker compose --compatibility build"
    if pull:
        cmd += " --pull"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=_override_docker_env(), pty=True)


@task(develop)
def lint(c, verbose=False):
    """Lint & format source code."""
    cmd = "pre-commit run --show-diff-on-failure --all-files --color=always"
    if verbose:
        cmd += " --verbose"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd)


@task()
def start(c, detach=True, debugpy=False):
    """Start environment."""
    cmd = "docker compose --compatibility up"
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
    ) as tmp_docker_compose_file:
        if debugpy:
            # Remove auto-reload
            cmd = (
                "docker compose --compatibility -f docker-compose.yml "
                f"-f {tmp_docker_compose_file.name} up"
            )
            _remove_auto_reload(
                tmp_docker_compose_file,
                orig_file=PROJECT_ROOT / "docker-compose.yml",
            )
        if detach:
            cmd += " --detach"
        with c.cd(str(PROJECT_ROOT)):
            result = c.run(
                cmd,
                pty=True,
                env=dict(
                    _override_docker_env(),
                    DOODBA_DEBUGPY_ENABLE=str(int(debugpy)),
                ),
            )
            if not (
                "Recreating" in result.stdout
                or "Starting" in result.stdout
                or "Creating" in result.stdout
            ):
                restart(c)
        _logger.info("Waiting for services to spin up...")
        time.sleep(SERVICES_WAIT_TIME)


@task(
    develop,
    help={
        "modules": "Comma-separated list of modules to install.",
        "core": "Install all core addons. Default: False",
        "extra": "Install all extra addons. Default: False",
        "private": "Install all private addons. Default: False",
        "enterprise": "Install all enterprise addons. Default: False",
        "cur-file": "Path to the current file."
        " Addon name will be obtained from there to install.",
    },
)
def install(
    c,
    modules=None,
    cur_file=None,
    core=False,
    extra=False,
    private=False,
    enterprise=False,
    database=False,
):
    """Install Odoo addons

    By default, installs addon from directory being worked on,
    unless other options are specified.
    """
    if not (modules or core or extra or private or enterprise):
        cur_module = _get_cwd_addon(cur_file or Path.cwd())
        if not cur_module:
            raise exceptions.ParseError(
                msg="Odoo addon to install not found. "
                "You must provide at least one option for modules"
                " or be in a subdirectory of one."
                " See --help for details."
            )
        modules = cur_module
    cmd = "docker compose --compatibility run --rm odoo addons init"
    if core:
        cmd += " --core"
    if extra:
        cmd += " --extra"
    if private:
        cmd += " --private"
    if enterprise:
        cmd += " --enterprise"
    if modules:
        cmd += f" -w {modules}"
    with c.cd(str(PROJECT_ROOT)):
        c.run(
            cmd,
            env=_override_docker_env(database),
            pty=True,
        )


def _test_in_debug_mode(c, odoo_command, database):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml"
    ) as tmp_docker_compose_file:
        cmd = (
            "docker compose --compatibility -f docker-compose.yml "
            f"-f {tmp_docker_compose_file.name} up -d"
        )
        _override_docker_command(
            "odoo",
            odoo_command,
            file=tmp_docker_compose_file,
            orig_file=Path(str(PROJECT_ROOT), "docker-compose.yml"),
        )
        with c.cd(str(PROJECT_ROOT)):
            c.run(
                cmd,
                env=dict(
                    _override_docker_env(database),
                    DOODBA_DEBUGPY_ENABLE="1",
                ),
                pty=True,
            )
        _logger.info("Waiting for services to spin up...")
        time.sleep(SERVICES_WAIT_TIME)


def _get_module_list(
    c,
    modules=None,
    core=False,
    extra=False,
    private=False,
    enterprise=False,
    only_installable=True,
):
    """Returns a list of addons according to the passed parameters.

    By default, refers to the addon from directory being worked on,
    unless other options are specified.
    """
    # Get list of dependencies for addon
    cmd = "docker compose --compatibility run --rm odoo addons list"
    if core:
        cmd += " --core"
    if extra:
        cmd += " --extra"
    if private:
        cmd += " --private"
    if enterprise:
        cmd += " --enterprise"
    if modules:
        cmd += f" -w {modules}"
    if only_installable:
        cmd += " --installable"
    with c.cd(str(PROJECT_ROOT)):
        module_list = c.run(
            cmd,
            env=UID_ENV,
            pty=True,
            hide="stdout",
        ).stdout.splitlines()[-1]
    return module_list


def _test_inject_coverage(odoo_command, modules_list):
    # Inject coverage into the command
    coverage_paths = ",".join(
        map(lambda m: "/opt/odoo/custom/src/private/{}".format(m), modules_list)
    )
    if coverage_paths:
        odoo_command[0] = "/usr/local/bin/odoo"
        odoo_command = [
            "coverage",
            "run",
            "--data-file=/opt/odoo/auto/.coverage",
            "--source={}".format(coverage_paths),
        ] + odoo_command

    return odoo_command


@task(
    help={
        "modules": "Comma-separated list of modules to test.",
        "core": "Test all core addons. Default: False",
        "extra": "Test all extra addons. Default: False",
        "private": "Test all private addons. Default: False",
        "enterprise": "Test all enterprise addons. Default: False",
        "skip": "List of addons to skip. Default: []",
        "debugpy": "Whether or not to run tests in a VSCode debugging session. "
        "Default: False",
        "cur-file": "Path to the current file."
        " Addon name will be obtained from there to run tests",
        "mode": "Mode in which tests run. Options: ['init'(default), 'update']",
        "database": "Database to run against. Defaults to $PGDATABASE",
        "coverage": "Generate a coverage.py output",
    },
)
def test(
    c,
    modules=None,
    core=False,
    extra=False,
    private=False,
    enterprise=False,
    skip="",
    debugpy=False,
    cur_file=None,
    mode="init",
    database=False,
    coverage=False,
):
    """Run Odoo tests

    By default, tests addon from directory being worked on,
    unless other options are specified.

    NOTE: Odoo must be restarted manually after this to go back to normal mode
    """
    if not (modules or core or extra or private or enterprise):
        cur_module = _get_cwd_addon(cur_file or Path.cwd())
        if not cur_module:
            raise exceptions.ParseError(
                msg="Odoo addon to install not found. "
                "You must provide at least one option for modules"
                " or be in a subdirectory of one."
                " See --help for details."
            )
        modules = cur_module
    else:
        modules = _get_module_list(c, modules, core, extra, private, enterprise)
    odoo_command = ["odoo", "--test-enable", "--stop-after-init", "--workers=0"]
    if mode == "init":
        odoo_command.append("-i")
    elif mode == "update":
        odoo_command.append("-u")
    else:
        raise exceptions.ParseError(
            msg="Available modes are 'init' or 'update'. See --help for details."
        )
    # Skip test in some modules
    modules_list = modules.split(",")
    for m_to_skip in skip.split(","):
        if not m_to_skip:
            continue
        if m_to_skip not in modules_list:
            _logger.warning(
                "%s not found in the list of addons to test: %s", m_to_skip, modules
            )
        modules_list.remove(m_to_skip)
    modules = ",".join(modules_list)
    odoo_command.append(modules)

    if coverage and modules_list:
        if debugpy:
            raise exceptions.ParseError(
                msg="Coverage cannot run at the same time as debugpy"
            )
        odoo_command = _test_inject_coverage(odoo_command, modules_list)

    if ODOO_VERSION >= 12:
        # Limit tests to explicit list
        # Filter spec format (comma-separated)
        # [-][tag][/module][:class][.method]
        odoo_command.extend(["--test-tags", "/" + ",/".join(modules_list)])
    if debugpy:
        _test_in_debug_mode(c, odoo_command, database)
    else:
        cmd = ["docker compose", "--compatibility", "run", "--rm"]
        cmd.append("odoo")
        cmd.extend(odoo_command)
        with c.cd(str(PROJECT_ROOT)):
            c.run(
                " ".join(cmd),
                env=_override_docker_env(database),
                pty=True,
            )


@task(
    help={
        "format": "Format to generate a coverage report in",
    }
)
def test_coverage_report(c, format=None):
    if format is None:
        format = "html"

    if not (PROJECT_ROOT / "odoo" / "auto" / ".coverage").exists():
        _logger.warning("Coverage input file does not exist, skipping")
        return

    FORMAT_TO_COMMAND = {
        "html": "html -d /opt/odoo/auto/coverage",
        "xml": "xml -o /opt/odoo/auto/coverage.xml",
        "report": "report",
    }

    cmd = [
        "docker compose run --rm odoo coverage",
        FORMAT_TO_COMMAND.get(format, "report"),
        "--data-file=/opt/odoo/auto/.coverage",
        "--omit=*/__init__.py,*/__manifest__.py,*/tests/*.py",
    ]

    with c.cd(str(PROJECT_ROOT)):
        c.run(
            " ".join(cmd),
            env=UID_ENV,
            pty=True,
        )


@task()
def stop(c):
    """Stop environment."""
    cmd = "docker compose --compatibility stop"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, pty=True)


@task()
def restart(c, quick=True):
    """Restart odoo container(s)."""
    cmd = "docker compose --compatibility restart"
    if quick:
        cmd = f"{cmd} -t0"
    cmd = f"{cmd} odoo odoo_proxy"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, env=_override_docker_env(), pty=True)


@task(
    help={
        "container": "Names of the containers from which logs will be obtained."
        " You can specify a single one, or several comma-separated names."
        " Default: None (show logs for all containers)"
    },
)
def logs(c, tail=10, follow=True, container=None):
    """Obtain last logs of current environment."""
    cmd = "docker compose --compatibility logs"
    if follow:
        cmd += " -f"
    if tail:
        cmd += f" --tail {tail}"
    if container:
        cmd += f" {container.replace(',', ' ')}"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, pty=True)


@task()
def stopstart(c, quick=False, detach=True, debugpy=False):
    """Stop the environment, then start it again"""
    result = c.run("docker compose ps --format=json", hide=True)
    if result.stdout != "[]" and quick:
        c.run("docker compose --compatibility stop -t0 odoo", pty=True)
        start(c, detach, debugpy)
    else:
        c.run("docker compose --compatibility stop", pty=True)
        start(c, detach, debugpy)


@task()
def psql(c, db=None):
    """Get an interactive psql shell"""
    cmd = f"docker compose exec db psql -U {DB_USER}"

    if db:
        cmd += f" {db}"
    else:
        cmd += " postgres"
    c.run(cmd, pty=True)


@task()
def shell(c, db=None, native=True):
    """
    Get an Odoo shell. By default it will use the native odoo shell, unless
    specified, or ODOO_MAJOR <= 10.
    """
    shell_cmd = "shell"

    if not native or ODOO_VERSION <= 10.0:
        shell_cmd = "click-odoo"

    cmd = f"docker compose run --rm odoo {shell_cmd}"
    if db:
        cmd += f" -d {db}"

    c.run(cmd, env=_override_docker_env(), pty=True)


@task()
def bash(c):
    """Get a bash shell in the Odoo container"""
    cmd = "docker compose exec odoo bash"
    c.run(cmd, pty=True)


@task()
def scaffold(c, name):
    """Create a scaffold using Odoo's built in scaffolding"""
    cmd = (
        f"docker compose run --rm odoo odoo scaffold {name}"
        f" /opt/odoo/custom/src/private"
    )
    c.run(cmd)


@task()
def upgrade(c, db=None, include_core=False):
    """
    Upgrade all Odoo addons
    Ignores core addons by default.
    User --include-core to include them
    """
    cmd = "docker compose exec odoo click-odoo-update"
    if not include_core:
        cmd += " --ignore-core-addons"
    if db:
        cmd += f" -d {db}"
    c.run(cmd, pty=True)


@task(develop)
def add_github_enterprise_repository(c, ssh_key_type=None):
    """
    Helper tool to add GlodoUK enterprise repo mirror.
    """
    return add_github_repository(
        c,
        organisation="glodouk",
        repository="enterprise",
        yaml_alias="enterprise",
        private=True,
        no_raise_exception=True,
        ssh_key_type=ssh_key_type,
    )


@task(
    develop,
    help={
        "organisation": "The github organisation or username i.e. glodouk, or oca",
        "repository": "The repository name i.e. edi, or enterprise",
        "yaml_alias": "The alias to use in the yaml file. Optional.",
        "private": "Is this a private repo?",
    },
)
def add_github_repository(
    c,
    organisation,
    repository,
    yaml_alias=None,
    private=False,
    no_raise_exception=False,
    ssh_key_type=None,
):
    target_repo = f"{organisation}_{repository}".lower()
    ssh_key = None
    if not ssh_key_type:
        ssh_key_type = "ed25519"
    git_remote = f"https://github.com/{organisation}/{repository}.git"

    if private:
        repo_domain = f"{target_repo}.github.com"
        git_remote = f"git@{repo_domain}:{organisation}/{repository}.git"
        ssh_key = f"odoo/custom/ssh/{target_repo}_{ssh_key_type}"

        if os.path.exists(ssh_key):
            error = f"{ssh_key} already exists"
            if no_raise_exception:
                _logger.warning(error)
            else:
                raise FileExistsError(error)

        cmd_key = (
            f"ssh-keygen -t {ssh_key_type} -N '' -f"
            f" odoo/custom/ssh/{target_repo}_{ssh_key_type}"
        )

        # Create the key
        c.run(cmd_key, pty=True)

        with open(PROJECT_ROOT / "odoo" / "custom" / "ssh" / "config", "a+") as f:
            f.seek(0)

            if f"Host {repo_domain}" not in f.read():
                ssh_config = (
                    f"\nHost {repo_domain}\n"
                    f"    HostName github.com\n"
                    f"    User git\n"
                    f"    IdentityFile ~/.ssh/{target_repo}_{ssh_key_type}\n"
                    f"    IdentitiesOnly yes\n"
                    f"    StrictHostKeyChecking no"
                )

                f.write(ssh_config)
            else:
                error = f"{repo_domain} already appears in ssh/config?"
                if no_raise_exception:
                    _logger.warning(error)
                else:
                    raise FileExistsError(error)

    if not yaml_alias:
        yaml_alias = target_repo

    with open(SRC_PATH / "repos.yaml", "r+") as f:
        repos = yaml.safe_load(f.read())
        if f"./{yaml_alias}" not in repos:
            repos.update(
                {
                    f"./{yaml_alias}": {
                        "default": {"depth": "$DEPTH_DEFAULT"},
                        "remotes": {
                            f"{organisation.lower()}": git_remote,
                        },
                        "target": f"{organisation.lower()} $ODOO_VERSION",
                        "merges": [f"{organisation.lower()} $ODOO_VERSION"],
                    }
                }
            )

            f.seek(0)
            f.write(yaml.dump(repos))
            f.truncate()
        else:
            error = f"{yaml_alias} already in repos.yaml"
            if no_raise_exception:
                _logger.warning(error)
            else:
                raise FileExistsError(error)

    with open(SRC_PATH / "addons.yaml", "r+") as f:
        addons = yaml.safe_load(f.read())
        if not addons or f"{yaml_alias}" not in addons:
            addons = addons or {}
            addons.update({f"{yaml_alias}": ["*"]})

            f.seek(0)
            f.write(yaml.dump(addons))
            f.truncate()
        else:
            error = f"{yaml_alias} already in repos.yaml"
            if no_raise_exception:
                _logger.warning(error)
            else:
                raise FileExistsError(error)

    msg = []

    if private and ssh_key:
        msg = [
            f"Ensure that you add the new SSH key {ssh_key} to"
            " {organisation}/{repository}.",
            "Run img-build for the new SSH config to be picked up.",
        ]

    msg.append("Run git-aggregate.")
    _logger.info("\n".join(msg))


@task(
    help={"purge": "Remove all related containers, networks images and volumes"},
)
def down(c, purge=False):
    """Take down and (optionally) purge environment."""
    cmd = "docker compose down"
    if purge:
        cmd += " --remove-orphans --rmi all --volumes"
    with c.cd(str(PROJECT_ROOT)):
        c.run(cmd, pty=True)


@task()
def preparedb(c, database=False):
    """
    Run the `preparedb` script inside the container which will set the following
    system parameters:
      - report url
      - database expiration
    """
    if ODOO_VERSION < 11:
        raise exceptions.PlatformError(
            "The preparedb script is not available for Doodba environments bellow v11."
        )
    with c.cd(str(PROJECT_ROOT)):
        c.run(
            "docker compose run --rm odoo preparedb",
            env=_override_docker_env(database),
            pty=True,
        )


@task(
    help={
        "base": "Any valid tree-ish to compare against",
        "coverage": "Generate a coverage.py output",
    }
)
def test_changed(c, base=None, coverage=False):
    """
    Automatically run unit tests for changed modules.
    """
    private_path = SRC_PATH / "private"
    import subprocess

    if not base:
        base = "origin/HEAD"

    git_output = (
        subprocess.check_output(
            [
                "git",
                "diff-index",
                "--name-only",
                base,
                "--",
                private_path,
            ]
        )
        .decode("utf-8")
        .split("\n")
    )

    todo = set(
        map(
            # Extract just the directory name from our against_path
            # These should just be Odoo modules by default
            lambda p: Path(p).parts[4:5][0],
            filter(
                # Remove False-y values and only directories within our against
                # path
                lambda p: p and os.path.isdir(os.path.join(*Path(p).parts[0:5])),
                git_output,
            ),
        )
    )

    if not todo:
        _logger.info("No changed modules found")
        return

    _logger.info("Running tests for modules: %s", todo)
    return test(c, modules=",".join(todo), coverage=coverage)


@task
def after_copier_update(c):
    """Execute some actions after a copier update or init"""

    # Ensure coverage is present in the pip.txt file
    pip = Path(PROJECT_ROOT, "odoo", "custom", "dependencies", "pip.txt")
    with open(pip, "a+") as f:
        if not any("coverage" == x.rstrip() for x in f):
            f.write("coverage" + "\n")
