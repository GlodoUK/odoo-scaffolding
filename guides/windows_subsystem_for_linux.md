# Windows using WSL (Windows Subsystem for Linux)
:warning: Ensure you using WSL2 and your instance is using WSL2. WSL1 is unusably slow for Odoo due to the file system performance.

  1. Ensure WSL is installed - https://docs.microsoft.com/en-us/windows/wsl/wsl2-install
  2. Ensure you are using WSL2 by default `wsl --set-default-version 2`
  2. If not already installed, install Ubuntu from the Windows App Store.
     * If Ubuntu was already installed, convert it to WSL2
  2. Open the Ubuntu WSL instance from the start menu, and inside the instance;
     * Run `mkdir -p ~/Code && cd ~/Code`
     * Clone this repository and run `sudo ./guides/provision.sh $USER`
  3. Shutdown and restart the WSL instance. Although you can workaround the core need for this, I've found failure to do so results in other oddities.
     * Run `wsl --shutdown Ubuntu` from Windows (not within the Ubuntu WSL instance)
     * Restart the WSL instance
  4. You may need to run `sudo service docker start` at start up. If you are running recent version of WSL and Windows, you can bypass this by adding the following to `/etc/wsl.conf` using your preferred editor.
     ```
     [boot]
     systemd=true
     ```
  6. You can access `~/Code` from the host by following the path `\\wsl$\Ubuntu\home\YOURUSERNAME\Code`
     * Ensure you clone any projects from within the WSL instance, under `~/Code`
  8. Running `code .` from within WSL should start up a VSCode instance on your desktop
  7. Follow any project specific instructions

## Tips
  * Mapping network drives to the `\\wsl$\Ubuntu\...` path sometimes fails across different Insider builds
    However mapping directly to the distro via the GUI always works; https://github.com/microsoft/WSL/issues/3854#issuecomment-465886991
  * Either cmdr, or Windows Terminal[1] is highly recommended over the default cmd/powershell terminal emulators

[1] https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-gb&gl=gb
