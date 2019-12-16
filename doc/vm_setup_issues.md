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
