## Reinforcement Learning for Routing in Software-defined networks ##
### Setup ###

```text
             s2 (3 MBits/s)
   h1  10ms/    \10ms  h4
   h2 -- s1      s3 -- h5
   h3  14ms\    /14ms  h6
             s4 (4 MBits/s)
```

### How to run ###

Terminal 1:
```bash
sudo python ./example.py
``` 

Terminal 2:
```bash
ryu-manager ./controller/remote_controller.py
``` 

### ###
