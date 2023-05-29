# Linux using Docker (Native)

Any modern distro should work. Ubuntu is the only distro officially supported, however we have team members on Arch.

If you're using Ubuntu you can run our provisioning script:

```bash
curl -sfL https://raw.githubusercontent.com/GlodoUK/odoo-scaffolding/glodo/guides/provision.sh | bash -
```

For any other environments we'll assume you're capable of provisioning yourself.

- Ensure the following are installed through your distro's package manager:
  - Docker CE
  - docker-compose
  - git
  - python 3
  - pip
- Install the following
  ```bash
  python3 -m pip install --user pipx
  pipx install copier
  pipx install invoke
  pipx install pre-commit
  pipx ensurepath
  ```