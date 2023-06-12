[![Copier template](https://img.shields.io/badge/template%20engine-copier-informational)](https://github.com/copier-org/copier)
[![Boost Software License 1.0](https://img.shields.io/badge/license-bsl--1.0-important)](COPYING)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

# Odoo Scaffolding & Developer Environment

This project is a combination of:
  * Documentation for how to setup your environment to run projects based on this template
  * A [Copier](https://github.com/copier-org/copier) template to standardise and maintain [Odoo](https://www.odoo.com/) projects based on [Doodba](https://github.com/Tecnativa/doodba)

This project was forked from Tecnativa/doodba-copier-template. 

As we grew our needs diverged from the original project:

  * We deploy into Kubernetes, thus a lot of the production tasks, etc. were not relevant to us
    * Deployment concerns were split into [glodouk/helm-charts](https://github.com/GlodoUK/helm-charts)
  * The project was restructured to ease the understanding between *this* project's dotfiles and the template
  * Additional bootstrapping and maintainence documentation was pulled in from an existing repository due to significant overlap

## Setting up your PC to run projects that use this template

See [Developer Environment Setup](guides/dev_setup.md).

## Creating or interact with an Odoo project using this template

See [Using copier](guides/using_copier.md).

# Credits

This project is a fork of the upstream copier-template maintained by [Tecnativa](https://www.tecnativa.com/r/H3p)

# Footnotes

<sup>1</sup> [gloduk/odoo-devenv](https://github.dev/glodouk/odoo-devenv) was retired and moved into this repository.

<sup>2</sup> Whilst the code is open source this is primarily an internal repository. As such all support outside of our customer base/internal staff is limited/at our discretion.
