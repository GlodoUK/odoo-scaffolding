# Developer Environment setup and pre-reqs

You will need access to Docker and have the ability to run Linux based Docker containers for a supported development environment.

* [Windows using WSL (Windows Subsystem for Linux)](windows_subsystem_for_linux.md)
* [Linux using Docker (Native)](linux_native.md)

### Editor/IDE Setup & Code Conventions

Use any editor you like, as long as it has support for [editorconfig](https://editorconfig.org/) and is enabled/installed.

The majority of the team use VSCode.

### Git Client Setup

Ensure your git email and name are correctly configured, where ever you use it. If you are calling git from within WSL/VMs then please ensure it is configured within there as well.

 * Run `git config --global user.email "youremail"`
 * Run `git config --global user.name "your name"`

 ## Environment Maintenance
  
  * You will want to periodically run `docker system prune` to clean up any unused docker containers, images, etc.
  * You may also want to periodically run `docker system prune --volumes`, this will also clean up volumes as well as containers, images, etc.
  * If you are using a VM, or WSL, you should also periodically run `sudo apt-get update && sudo apt-get upgrade`
