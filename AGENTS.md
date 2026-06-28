# Project agent instructions

## Purpose
This repository contains the Freenove 4WD Raspberry Pi car software, plus custom work for a mecanum-wheel robot, remote video streaming, gamepad control, and future AI features.

## Working conventions
- Keep the original Freenove structure intact where possible.
- Prefer small, focused changes over large rewrites.
- Work in feature branches and keep commits descriptive.
- Use the local virtual environment in .venv.
- Update documentation when behavior changes.

## Environment
- Python 3.10+ is expected.
- Activate the environment with: `. .venv/bin/activate`
- Install dependencies with: `pip install -r requirements.txt`

## Project layout
- Code/Server: Raspberry Pi server-side control, motors, camera, sensors, and networking.
- Code/Client: client-side UI and video display logic.
- docs/: project-specific design notes and roadmap.

## Priorities for this fork
1. Preserve the existing Freenove functionality.
2. Add a reliable remote video stream for a phone-based controller.
3. Add configurable gamepad mappings for movement and camera pan/tilt.
4. Explore face recognition and following as a later milestone.
5. Keep future AI and hardware expansions modular.

## Guidance for changes
- Do not break existing command protocols without updating both server and client code.
- Prefer clear names and comments for new modules.
- If a change touches hardware control, keep the logic isolated and easy to test.
- When adding AI features, start with a simple detection pipeline and make the fallback path explicit.
