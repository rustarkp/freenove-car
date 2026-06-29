import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "streaming_server.py"

spec = importlib.util.spec_from_file_location("streaming_server", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_drive_controller_maps_basic_commands():
    controller = module.DriveController(motor_factory=lambda: None)

    assert controller.apply_command("forward") is True
    assert controller.last_command == "forward"

    assert controller.apply_command("stop") is True
    assert controller.last_command == "stop"

    assert controller.apply_command("left") is True
    assert controller.last_command == "left"
