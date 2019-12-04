## Reinforcement Learning for Routing in Software-defined networks ##
### Setup ###

```text
                s2 (3 MBits/s)
   h11    10ms/    \10ms  h41
   h12 -- s1        s3 -- h42
          14ms\    /14ms
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