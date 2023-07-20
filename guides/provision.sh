#!/bin/bash

set -e

# Usage:
#   curl -sfL https://raw.githubusercontent.com/GlodoUK/odoo-scaffolding/glodo/guides/provision.sh | bash -
#
# This script is intended to be as minimally destructive as possible to any existing Ubuntu installation

# --- helper functions for logs
info() {
    echo '[INFO] ' "$@"
}

warn() {
    echo '[WARN] ' "$@" >&2
}

fatal() {
    echo '[ERROR] ' "$@" >&2
    exit 1
}

verify_system() {
  if [ `lsb_release -si` != "Ubuntu" ]; then 
    fatal 'Expected Ubuntu'
  fi

  if [ -x /bin/systemctl ] || type systemctl > /dev/null 2>&1; then
    return
  fi
  fatal 'Can not find systemd'
}

install_prerequisites() {
  info "Installing prerequisites"

  sudo add-apt-repository -y ppa:git-core/ppa
  sudo apt-get -yq update
  sudo apt-get install -y \
      apt-transport-https \
      ca-certificates \
      curl \
      wget \
      gnupg-agent \
      software-properties-common \
      build-essential \
      samba \
      acl \
      inotify-tools \
      git \
      python3-pip \
      python3-venv \
      gnupg
}

install_docker() {
  info "Installing Docker"

  # cleanup any incompatible stuff
  for pkg in docker.io docker-doc docker-compose podman-docker containerd runc
  do 
    if dpkg --get-selections | grep -q "^$pkg[[:space:]]*install$" >/dev/null; then 
      sudo apt-get remove -y $pkg
    fi
  done

  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  sudo usermod -a -G docker $USER
}

install_docker_compose() {
    info "Installing docker-compose"
    sudo curl -L https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
    sudo chmod a+x /usr/local/bin/docker-compose
}

install_kubectl() {
  if [ -x "$(command -v kubectl)" ]; then
    warn "Skipping installation of kubectl as found on path"
  else
    info "Installing kubectl"
    sudo curl -fsSLo /etc/apt/keyrings/kubernetes.gpg https://dl.k8s.io/apt/doc/apt-key.gpg
    echo "deb [signed-by=/etc/apt/keyrings/kubernetes.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
    sudo apt-get update
    sudo apt-get install -y kubectl
  fi
}

install_flux() {
  if [ -x "$(command -v flux)" ]; then
    warn "Skipping installation of FluxCD as flux found on path"
  else
    info "Installing FluxCD"
    curl -s https://fluxcd.io/install.sh | sudo bash
  fi
}

install_starship() {
  info "Installing Starship.rs"

  curl -sS https://starship.rs/install.sh | sh

  grep -qxF 'starship' ~/.bashrc || echo '
if [ -x "$(command -v starship)" ]; then
  unset PROMPT_COMMAND
  eval "$(starship init bash)"
fi' >> ~/.bashrc

  grep -qxF 'bash_completion' ~/.bashrc || echo '
if [ -f /etc/bash_completion ] && ! shopt -oq posix; then
  . /etc/bash_completion
fi

if [ -f /usr/share/bash-completion/bash_completion ] && ! shopt -oq posix; then
  . /usr/share/bash-completion/bash_completion
fi'

  source ~/.bashrc
}

install_teleport() {
  if [ -x "$(command -v tsh)" ]; then
    warn "Skipping installation of teleport as tsh already found on path"
  else
    info "Installing Teleport"
    sudo curl "https://apt.releases.teleport.dev/gpg" -o /usr/share/keyrings/teleport-archive-keyring.asc
    source /etc/os-release
    echo "deb [signed-by=/usr/share/keyrings/teleport-archive-keyring.asc] \
    https://apt.releases.teleport.dev/${ID?} ${VERSION_CODENAME?} stable/v13" \
    | sudo tee /etc/apt/sources.list.d/teleport.list > /dev/null

    sudo apt-get update
    sudo apt-get install -yq teleport
  fi
}

install_sops() {
  if [ -x "$(command -v tsh)" ]; then
    warn "Skipping installation of SOPS as already installed"
  else
    info "Installing Mozilla SOPS"
    curl -L "https://github.com/mozilla/sops/releases/download/v3.7.3/sops_3.7.3_amd64.deb" -o sops.deb
    dpkg -i sops.deb
    rm sops.deb
  fi
}

install_code_dir() {
  info "Creating ~/Code"
  mkdir -p ~/Code
}

install_pipx() {
  info "Installing pipx, copier, invoke, pre-commit"
  python3 -m pip install --user pipx
  ~/.local/bin/pipx install copier
  ~/.local/bin/pipx install invoke
  ~/.local/bin/pipx install pre-commit
  
  grep -qxF 'export PATH=$PATH:~/.local/bin/' ~/.bashrc || echo 'export PATH=$PATH:~/.local/bin/' >> ~/.bashrc

  grep -qxF 'invoke --print-completion-script=bash' ~/.bashrc || echo '
if [ -x "$(command -v invoke)" ]; then
  eval "$(invoke --print-completion-script=bash)"
fi ' >> ~/.bashrc
}

update_sysctl() {
  if [[ $(sudo dmidecode -s system-product-name) == "Virtual Machine" && $(sudo dmidecode -s system-manufacturer == "Microsoft Corporation") ]]
  then
    info "Hyper-V detected, applying net.ipv6.config.all.forwarding=1 to avoid docker-compose issues"
    # fixes issue specific to Hyper-V and docker-compose forwarding
    sudo sysctl -w net.ipv6.conf.all.forwarding=1
  fi

  info "Raising fs.inotify.max_user_watches"
  sudo sysctl -w fs.inotify.max_user_watches=524288
}

use_wsl_systemd_boot() {
  if grep -qi microsoft /proc/version; then
    sudo python3 <<EOF
import os
import configparser

c = configparser.ConfigParser()
if os.path.isfile('/etc/wsl.conf'):
  c.read('/etc/wsl.conf')

if not c.has_section('boot'):
  c.add_section('boot')

if not c.has_option('boot', 'systemd') or c.get('boot', 'systemd') != 'true':
  c.set('boot', 'systemd', 'true')

  with open('/etc/wsl.conf', 'w') as f:
    c.write(f)
EOF
  else
    warn "Native Linux detected, skipping /etc/wsl.conf modifications"
  fi
}

ensure_not_root() {
  if [ "$EUID" -eq 0 ]; then 
    fatal "Please do not run this as root!"
  fi
}

WORKING_DIR=$(mktemp -d)

info "Created temp directory $WORKING_DIR"

# Exit if the temp directory wasn't created successfully.
if [ ! -e "$WORKING_DIR" ]; then
    >&2 echo "Failed to create temp directory"
    exit 1
fi

pushd "$WORKING_DIR"

trap '{ popd; rm -rf -- "$WORKING_DIR"; }' EXIT

export DEBIAN_FRONTEND=noninteractive

info "You may be asked to enter your sudo password during the course of this script."

verify_system
ensure_not_root
install_prerequisites
install_docker
install_docker_compose
install_kubectl
install_teleport
install_starship
install_code_dir
install_pipx
update_sysctl
use_wsl_systemd_boot

source ~/.bashrc

if grep -qi microsoft /proc/version; then
  info "Run wsl --shutdown and then reopen Ubuntu"
fi
