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


| `docker system prune` | You will want to periodically run `docker system prune` to clean up any unused docker containers, images, etc. |
| `docker system prune --volumes` | As above, but clears any volumes |
| `docker image prune -a` | Clear old images not in use *right now* |
| `sudo apt-get update && sudo apt-get upgrade && sudo apt-get autoclean` | (If using VM or WSL) Update app repos and clear up old cached repo data |

### Shrinking your Development VHD (WSL Specific)

```
wsl --shutdown
diskpart
select vdisk file="{path to your vhd file}"
compact vdisk
exit
```
