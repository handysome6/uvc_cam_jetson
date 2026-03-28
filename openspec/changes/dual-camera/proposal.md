## Why

Phase 1 validated the single-camera pipeline on Jetson: preview via VideoOverlay and raw MJPEG capture both work. The product requires two simultaneous 20MP UVC cameras for dual-view capture. Phase 2 extends the proven single-camera architecture to dual-camera parallel operation so that both cameras preview side-by-side and a single button press saves full-resolution frames from both cameras at the same moment.

## What Changes

- Add `DualCameraManager` class that owns two `CameraPipeline` instances, coordinates start/stop lifecycle, and provides a single `capture()` method that reads both latest frames with one shared timestamp
- Refactor `MainWindow` from one preview panel to two side-by-side panels, each bound to its own `CameraPipeline` via VideoOverlay
- Extend UVC auto-detection (`find_uvc_camera`) to discover multiple cameras and assign them to left/right slots
- Update capture file naming to include camera identity: `cam0_<timestamp>.jpg` / `cam1_<timestamp>.jpg`
- Update `main.py` entry point to use `DualCameraManager` instead of a single `CameraPipeline`

## Capabilities

### New Capabilities
- `dual-camera-manager`: Coordination layer that manages two CameraPipeline instances — unified lifecycle, simultaneous capture, and camera identity assignment
- `dual-camera-gui`: Extended MainWindow with two side-by-side preview panels, per-camera status indicators, and a single capture button that triggers both cameras

### Modified Capabilities
- `camera-pipeline`: Add support for camera identity/index and multi-device discovery (return list of UVC devices, not just the first)
- `frame-capture`: Capture naming scheme changes to include camera identity prefix (`cam0_`/`cam1_`)

## Impact

- **Source files**: new `src/dual_camera_manager.py`; modified `src/main_window.py`, `src/camera_pipeline.py`, `src/main.py`
- **Hardware**: requires two UVC cameras connected simultaneously (application should degrade gracefully if only one is found)
- **No new dependencies**: uses existing PySide6 + GStreamer stack
