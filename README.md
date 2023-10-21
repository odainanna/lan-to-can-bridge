# lan-to-can-bridge

```bash
# install these for the bridge
pip install python-can>=4.2.1 msgpack uptime

# these for packing
pip install pyinstaller
```

```bash
# build the exe-file
Pyinstaller bridgeapp.py --noconsole --onefile

# run it 
dist/bridgeapp
```

## Config for PCAN viewer

![pcan_viewer_ucan8_dio_config.png](pcan_viewer_ucan8_dio_config.png)

## Run

### fd

python --dbitrate 2000000 --bitrate 250000

### non-fd

python --bitrate 125000

### single cna

python --bitrate 125000 --single 1 