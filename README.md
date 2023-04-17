# lan-to-can-bridge

```bash
# install these for the bridge
pip install python-can msgpack uptime

# these for packing
pip install pyinstaller
```

```bash
# build the exe-file
pyinstaller main.spec

# run it 
dist/bridgeapp
```