# Windows using WSL (Windows Subsystem for Linux)
:warning: Ensure you using WSL2 and your instance is using WSL2. WSL1 is unusably slow for Odoo due to the file system performance. We strongly recommend only using WSL2 and a recent version of Windows 11 due to various miscellaneous improvements.

  1. Ensure WSL is installed[1]
  2. Ensure you are using WSL2 by default, by running `wsl --set-default-version 2` from either a Powershell or Windows Terminal/Command prompt.
  3. Open Powershell and run the following snippet to auto install our recommended applications. During this process you 
     ```powershell
     winget install -e --id Microsoft.VisualStudioCode
     winget install -e --id Google.Chrome
     winget install -e --id AgileBits.1Password
     winget install Canonical.Ubuntu.2204
     ```
  4. Open the Ubuntu WSL instance from the start menu. If this is the first time you have run this, it may take a few minutes to setup.
     * Inside the instance run the following snippet:
       ```bash
       curl -sfL https://raw.githubusercontent.com/GlodoUK/odoo-scaffolding/glodo/guides/provision.sh | bash -
       ```
     * During this process you will be asked for your WSL password at least once during the setup process, please ensure that you enter this
     * When prompted shutdown the wsl instance by opening a new Powershell or Command prompt and run `wsl --shutdown`
   5. Reopen Ubuntu from the start menu and you should have a fully configured Ubuntu instance ready to go.
      * You can access `~/Code` from the Ubuntu install by following the path `\\wsl$\Ubuntu\home\YOURUSERNAME\Code` in Windows. You will see this in the File Explorer as `Linux` or `Ubuntu`.
      * Ensure you clone any projects from within the WSL instance, under `~/Code`.
      * Running `code .` from within WSL should start up a VSCode instance on your desktop from that directory.
      * Follow any project specific instructions to get started.

## Tips
  * Mapping network drives to the `\\wsl$\Ubuntu\...` path sometimes fails across different Insider builds
    However mapping directly to the distro via the GUI always works; https://github.com/microsoft/WSL/issues/3854#issuecomment-465886991
  * Either cmdr, or Windows Terminal[2] is highly recommended over the default cmd/powershell terminal emulators

[1] https://docs.microsoft.com/en-us/windows/wsl/wsl2-install
[2] https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-gb&gl=gb
