# Phase 1 streaming prototype

## Goal
Provide a simple local-first camera workflow that supports:
- on-demand high-resolution image capture saved locally on the Pi
- a browser-accessible low-latency live stream for phone viewing

## Runtime
Run the prototype with:

```bash
. .venv/bin/activate
python streaming_server.py
```

Then open:
- http://<pi-ip>:8000/ for the simple browser page
- http://<pi-ip>:8000/stream.mjpg for the MJPEG stream

## Storage
- still images: private_data/images/
- future videos: private_data/videos/

## Notes
- The live stream is optimized for responsiveness rather than maximum quality.
- Still capture uses the highest available local resolution and writes to disk first.
