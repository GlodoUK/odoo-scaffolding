# Install the dependencies

This project itself is just the template, but you need to install these tools to use it:

- Linux<sup>1</sup>
- [copier](https://github.com/copier-org/copier)
- [docker-compose](https://docs.docker.com/compose/install/)
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
copier copy git@github.com:GlodoUK/odoo-scaffolding.git ~/path/to/your/subproject
```

Copier will ask you a lot of questions. Answer them to properly generate the template.

# Getting updates for your subproject

```bash
cd ~/path/to/your/downstream/scaffolding
SKIP=flake8 copier update -D
```