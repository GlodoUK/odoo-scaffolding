# Windows using WSL (Windows Subsystem for Linux)
:warning: Ensure you using WSL2 and your instance is using WSL2. WSL1 is unusably slow for Odoo due to the file system performance.

  1. Ensure WSL is installed: https://docs.microsoft.com/en-us/windows/wsl/wsl2-install
  2. Ensure you are using WSL2 by default, by running `wsl --set-default-version 2` from either a Powershell or Windows Terminal/Command prompt.
  2. If not already installed, install Ubuntu from the Windows App Store.
  3. Open the Ubuntu WSL instance from the start menu, and inside the instance;
     * Run `curl -sfL https://raw.githubusercontent.com/GlodoUK/odoo-scaffolding/glodo/guides/provision.sh | bash -`
     * You will be asked for your WSL password at least once during the setup process, please ensure that you enter this
     * After restarting WSL you may need to run `sudo systemctl enable docker && sudo systemctl start docker` at first startup up if any docker commands fail.

From this point
  * You can access `~/Code` from the host by following the path `\\wsl$\Ubuntu\home\YOURUSERNAME\Code`
  * Ensure you clone any projects from within the WSL instance, under `~/Code`
  * Running `code .` from within WSL should start up a VSCode instance on your desktop
  * Follow any project specific instructions

## Tips
  * Mapping network drives to the `\\wsl$\Ubuntu\...` path sometimes fails across different Insider builds
    However mapping directly to the distro via the GUI always works; https://github.com/microsoft/WSL/issues/3854#issuecomment-465886991
  * Either cmdr, or Windows Terminal[1] is highly recommended over the default cmd/powershell terminal emulators

[1] https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-gb&gl=gb
