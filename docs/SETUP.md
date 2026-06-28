# Development environment setup

## Python environment

From the repository root:

```bash
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install ./Code/Libs/rpi-ws281x-python/library
```

## System packages on Raspberry Pi OS

The following packages are also recommended for the full Freenove stack:

```bash
sudo apt-get update
sudo apt-get install -y \
  python3-dev python3-pyqt5 python3-opencv python3-numpy \
  python3-pil python3-gpiozero python3-requests python3-flask \
  python3-socketio python3-pygame python3-picamera2
```

## Run the original server UI

```bash
cd Code/Server
python main.py
```

## Run the original client UI

```bash
cd Code/Client
python Main.py
```

## Notes

- The repository uses the local .venv environment for Python packages.
- The system packages are used for hardware and GUI support on Raspberry Pi OS.
- Future remote-control work should be implemented as separate modules rather than by patching the original UI directly.
