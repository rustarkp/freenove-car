# Gamepad control

## Mapping
- **Left stick**: 2D drive — up/down = forward/backward, left/right = strafe.
- **Right stick X** (left/right): rotate the car body (yaw).
- **Right stick Y** (up/down): tilt the camera servo.
- **LB / RB (shoulder bumpers)** and **D-pad left/right**: pan the camera servo
  (either input works; both map to the same pan direction).

Drive input goes through the same `DriveController.apply_vector(x, y, rotation)`
used by the web UI's touch joystick (`streaming_server.py`), so gamepad and
touch control share one code path. Pan/tilt go through the new
`CameraController`, which integrates a `-1..1` rate per axis over time rather
than mapping stick position directly to angle — release the stick/button and
the camera holds its last position instead of snapping back to center.

## Setup
The gamepad must be paired/plugged into the **Raspberry Pi itself** (USB or
Bluetooth), not the phone/browser viewing the stream. `streaming_server.py`
polls it on a background thread via `pygame` (already in `requirements.txt`).
If no gamepad is connected, the rest of the server (streaming, touch joystick,
buttons) works exactly as before — the gamepad thread just no-ops.

## Calibrating axis/button indices
`Code/Server/gamepad_controller.py` hardcodes axis/button indices for a
common Xbox-style SDL mapping:
```
LEFT_X_AXIS = 0    LEFT_Y_AXIS = 1
RIGHT_X_AXIS = 2   RIGHT_Y_AXIS = 3
BUTTON_LB = 4      BUTTON_RB = 5
```
Controllers vary. If movement/camera control doesn't match the mapping above,
run the file directly to see live axis/button/hat values and adjust the
constants:
```bash
.venv/bin/python Code/Server/gamepad_controller.py
```

## Known unknowns — verify by testing
Pan/tilt direction (which way is "increasing angle") depends on how the servo
horns are physically mounted, which can't be determined from code alone. If
pushing the right stick up tilts the camera down, or a bumper pans the wrong
way, flip the sign in `GamepadController.poll_once` (`-right_y` /
`pan_rate` terms in `gamepad_controller.py`) or in `CameraController`'s
`PAN_SPEED_DEG_S` / `TILT_SPEED_DEG_S` constants in `streaming_server.py`.

## Tuning
- `DEADZONE` (`gamepad_controller.py`): minimum stick deflection before it
  counts as input. Raise this if a stick drifts at rest.
- `PAN_SPEED_DEG_S` / `TILT_SPEED_DEG_S` (`CameraController` in
  `streaming_server.py`): degrees/second at full deflection.
- `PAN_MIN/MAX` (0-180) and `TILT_MIN/MAX` (80-180): clamp ranges, matching
  the original Freenove client's slider limits for the same servo channels.

## Status endpoint
`/status` now also reports `gamepad_connected`, `pan_angle`, `tilt_angle`, and
`camera_hardware_ready`, alongside the existing drive fields.
