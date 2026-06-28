import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streaming_server import CameraService


def test_capture_image(tmp_path):
    service = CameraService(stream_size=(320, 240), capture_size=(640, 480))
    try:
        path = service.capture_image('test-capture.jpg')
        assert os.path.exists(path)
    finally:
        service.stop_stream()
