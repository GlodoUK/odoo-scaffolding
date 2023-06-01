<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
<summary>Table of contents</summary>

- [Install the dependencies](#install-the-dependencies)
- [Use the template to generate your subproject](#use-the-template-to-generate-your-subproject)
- [Getting updates for your subproject](#getting-updates-for-your-subproject)
- [Interacting with a project based on this template](#interacting-with-a-project-based-on-this-template)
  - [Development/Start up](#developmentstart-up)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Install the dependencies

This project itself is just the template, but you need to install these tools to use it:

- Linux<sup>1</sup>
- [copier](https://github.com/copier-org/copier)
- [Docker](https://docs.docker.com/) and [Compose V2 plugin](https://docs.docker.com/compose/)
- [git](https://git-scm.com/) 2.24 or newer
- [invoke](https://www.pyinvoke.org/) installed in Python 3.6+ (and the binary must be
  called `invoke` — beware if your distro installs it as `invoke3` or similar).
- [pre-commit](https://pre-commit.com/)
- [python](https://www.python.org/) 3.6+
- [venv](https://docs.python.org/3/library/venv.html)

Install non-python apps with your distro's recommended package manager.

The recommended way to install Python CLI apps is [pipx](https://pipxproject.github.io/pipx/):

```bash
python3 -m pip install --user pipx
pipx install copier
pipx install invoke
pipx install pre-commit
pipx ensurepath --force
```

# Use the template to generate your subproject

Once you installed everything, you can now use Copier to copy this template:

```bash
copier copy https://github.com/GlodoUK/odoo-scaffolding.git ~/path/to/your/subproject
```

Copier will ask you a lot of questions. Answer them to properly generate the template.

# Getting updates for your subproject

```bash
cd ~/path/to/your/downstream/scaffolding
SKIP=flake8 copier update -D
```

# Interacting with a project based on this template

## Development/Start up

Set up a valid VSCode development environment with:

```sh
invoke develop
```

Get Odoo and addons code with:

```bash
invoke img-build --pull
invoke git-aggregate
```

Start Odoo with:

```bash
invoke start
```

All of the above in one shot:

```bash
invoke develop img-build git-aggregate start
```

See the other tasks:

```bash
invoke --list
```

To browse Odoo go to `http://localhost:${ODOO_MAJOR}069` (i.e. for Odoo 11.0 this would
be `http://localhost:11069`).

[MailPit](https://github.com/axllent/mailpit) is bundled to provide a fake SMTP server that
intercepts all mail sent by Odoo and displays a simple interface that lets you see and
debug all that mail comfortably, including headers sent, attachments, etc.
You will find this on `http://localhost:${ODOO_MAJOR}025`.

The Docker network is in `--internal` mode, which means that it has no access to the
Internet. This feature protects you in cases where a production database is restored
and Odoo tries to connect to SMTP/IMAP/POP3 servers to send or receive emails. Also when
you are using [connectors](https://github.com/OCA/connector),
[mail trackers](https://www.odoo.com/apps/modules/browse?search=mail_tracking) or any
API sync/calls.

If you still need to have public access, set `internal: false` in the environment file,
detach all containers from that network, remove the network, reatach all containers to
it, and possibly restart them. You can also just do:

```bash
invoke down
invoke start
```

Alternatively you may add a whitelist service in the same manner as `cdnjs.cloudflare.com`, for example. Explore `devel.yaml`.

There are several options for debugging: wdb and debugpy.

wdb can be used by placing the following anywhere and then browsing to `http://localhost:${ODOO_MAJOR}984`

```python
import wdb
wdb.set_trace()
```

Debugpy is enabled by calling `invoke start --debugpy`, or by using F5 in VSCode.

Running tests `invoke test`
