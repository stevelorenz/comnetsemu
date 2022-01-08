# Known VM Setup Issues #

## On Windows

1.  Issue: Failed to run the install.sh during `vagrant up` on Windows. 'bash\r': No such file or directory or
    '\r'command not found.

    *   Potential cause:
        Some Windows editions (e.g. TUD Windows Enterprise) somehow silently modify the files in the shared
        folder which is by default enabled in Vagrantfile. The installer script is modified into Windows format which has a
        different line endings compared to Unix-like OSes like GNU/Linux.

    *   Solution:
        You can run `vagrant ssh comnetsemu` to log into the VM.
        Install the `dos2unix` tool via `sudo apt install dos2unix`
        Then reformat the installer script with `dos2unix ~/comnetsemu/util/install.sh`
        Run the installer script inside the VM via `cd ~/comnetsemu/util/install.sh && bash ./install.sh -a`

    *   Suggestion:
        If you want to keep the synced folder feature e.g. for develop in host OS and test codes inside the VM.
        It is suggested to make sure the used editor/IDE on Windows host OS save files with Unix-style format to avoid
        conflicts.
        You can also disable synced folder feature in Vagrantfile by commenting out lines starts with `comnetsemu.vm.synced_folder`.

2.  Issue: Failed to open xterms for running nodes.

    * Potential cause:
    The terminal you use does not support X11-forwarding via SSH.


    * Solution:
    [Mobaxterm](https://mobaxterm.mobatek.net/) could be used as the console to solve the problem.

3. Issue: Failed to open xterms with sudo inside the VM.

   If run `sudo xterm` inside the VM or run `xterm h1` inside the ComNetsEmu's CLI returns the following error:

   ```bash
   Warning: This program is an suid-root program or is being run by the root user.
   The full text of the error or warning message cannot be safely formatted
   in this environment. You may get a more descriptive message by running the
   program as a non-root user or by removing the suid bit on the executable.
   xterm: Xt error: Can't open display: %s
   ```

   * Potential cause: It is not allowed on most Unix/Linux systems to keep the X11-forwarding working after changing user to root inside a SSH session.  This is by
     default not allowed (e.g. It is allowed in Ubuntu 18.04 but not allowed on Ubuntu 20.04), because the X11 display connection belongs to the user you used to log with
     when connecting to your remote SSH server.  X11-forwarding mechanism does not allow anyone to use the open display.

   * Solution: You could manually retrieve X credentials in the sudo context by looking up the `xauth list` for the original username (`vagrant` for the default VM) and
     then adding them using following command (You need to do this **Everytime** for a new SSH session.):

     ```bash
     sudo xauth add $(xauth -f /home/vagrant/.Xauthority list|tail -1)
     ```

     You can also run this command using Python's `subprocess` module inside each emulation script.
