# MacOS, Windows or Linux using Virtual Machines

:warning: This is not currently used by any team members and highly unrecommended.

  * This will pre-configure a VM for you, with the necessary development environment pre-reqs for most Odoo related projects
    * The instructions will have you checkout all code inside the VM. This is to speed up disk access, and enable hot code reloading reliably across all OS'. If you attempt to do the reverse you'll have serious development slow downs.
  * If you are on Linux, it is *highly* recommended to use Docker natively, rather than VMs
  * It is *not* recommended to use a VM per-project, at this time, but reuse it for multiple projects.
  * If you are migrating from a previous version of our dev environment that uses Unison for file syncing between host and guest VM, ensure you have pushed any work to the origin repository, delete the existing VM and cloned repo(s) and start over with these instructions.

  1. Ensure you have [git](https://git-scm.com/) (or any other git client installed), plus one of the following virtualisation environments are installed [1] [2];
     * [VirtualBox](https://www.virtualbox.org/)
     * libvirt [3]
  2. Ensure [vagrant](https://www.vagrantup.com/) is installed
  3. Clone this repository, `cd guide/vagrant` and then run `vagrant up`
  4. Your development environment is now setup
     * Run `vagrant ssh` to enter the VM
       * Run `git config --global user.email "youremail"`
       * Run `git config --global user.name "your name"`
       * Ensure you clone any projects from within the VM, into `~/Code`
       * You can access `~/Code` from the host by following the network sharing
         instructions from the `vagrant up` command.
     * From the host, in a terminal window open to the cloned directory:
       * To shutdown the VM you can issue `vagrant halt` at anytime
       * To boot up the VM you can issue `vagrant up` at anytime
       * To destroy the VM you can issue `vagrant destroy` at anytime
  5. Follow any project specific instructions

[1] We have not tested Parallels or VMWare. You are welcome to provide feedback/test.

[2] Hyper-V is not recommended, but will work. Due to how Hyper-V works you will see issues with port forwarding, etc. not working as expected. 
    You will need to access the VM via the IP address assigned, rather than localhost.

[3] Requires third party [libvirt provider](https://github.com/vagrant-libvirt/vagrant-libvirt) to be installed.
