# WIP: Multi-hop Recoding Latency

## Getting Started

Please be ware that some of the following commands require sudo.

1. Setup the host OS (Re-run this step after each reboot):

```bash
sudo ./setup.sh
```

2. Build `kodo-rlnc` library on the host OS (require license):

```bash
./build_kodo_rlnc.sh
```

After this step, you must find the `kodo-rlnc_install` directory under current directory.

3. Build the `kodo_rlnc_coder` Docker image:

```bash
./build_image.sh
```

4. Build executable binaries for client, server and VNFs:

```
sudo ./build_executable.py
```

After this step, you must find the `build` directory under current directory.

5. Run the multi-hop topology with all VNFs in store and forwarding mode:

```
sudo ./topology.py --vnf_mode store_forward
```
