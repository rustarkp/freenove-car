# Freenove Car Fork Vision

This fork is being shaped around a custom Raspberry Pi robot platform that keeps the original Freenove hardware and software base, while extending it with modern remote-control and AI capabilities.

## Goals
- Stream live video from the car to an Android phone.
- Control the car with a gamepad connected either directly to the Pi or to the phone.
- Support custom gamepad mapping for movement and camera control.
- Explore face recognition and person-following behavior.
- Keep the architecture modular so future work can include speech, a turret, and ML-based aiming.

## Proposed architecture
- Raspberry Pi server handles motor control, camera capture, and command handling.
- A lightweight web or socket-based stream serves frames to a phone-friendly client.
- A gamepad layer maps input events to drive commands and camera movement.
- AI modules can run as optional services that observe the camera stream.

## Milestones
1. Baseline: preserve and document the original Freenove behavior.
2. Remote control: add video streaming and a phone-friendly control UI.
3. Gamepad control: support mapping and tuning for movement and camera pan/tilt.
4. AI follow: implement face detection and person following.
5. Future expansions: speech, turret control, and ML training loops.
