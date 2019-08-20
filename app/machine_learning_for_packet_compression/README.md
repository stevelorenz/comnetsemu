Build O2SC docker container:

```sh
sudo docker build -t o2sc .
```

Run the O2SC decompressor:

```sh
sudo docker run -it o2sc -d -p [PORT]
```

Run the O2SC compressor:

```sh
sudo docker run -it o2sc -a [IP] -p [PORT]
```

Configure compressor intuitively:

![alt text](https://cn.ifn.et.tu-dresden.de/wp-content/uploads/2019/08/printscreen.png)