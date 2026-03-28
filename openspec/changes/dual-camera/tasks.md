## 1. Multi-device discovery

- [ ] 1.1 Add `find_uvc_cameras()` function to `camera_pipeline.py` that returns a list of all USB UVC capture device paths
- [ ] 1.2 Update `find_uvc_camera()` to delegate to `find_uvc_cameras()` (return first result or None)

## 2. DualCameraManager

- [ ] 2.1 Create `src/dual_camera_manager.py` with `DualCameraManager` class that owns two `CameraPipeline` instances (cam0, cam1)
- [ ] 2.2 Implement `start(handles)` that starts both pipelines with their respective window handles
- [ ] 2.3 Implement `stop()` that stops both pipelines and waits for resources to release
- [ ] 2.4 Implement `capture(directory)` that reads both latest frames with a shared timestamp and saves as `cam0_<ts>.jpg` / `cam1_<ts>.jpg`
- [ ] 2.5 Add per-camera error/state signals (forward from each CameraPipeline with camera index)
- [ ] 2.6 Handle single-camera mode: gracefully skip the absent pipeline slot

## 3. Dual-camera GUI

- [ ] 3.1 Refactor `MainWindow` to accept `DualCameraManager` instead of a single `CameraPipeline`
- [ ] 3.2 Create two side-by-side `_PreviewWidget` instances (horizontal layout) for cam0 and cam1
- [ ] 3.3 Update `showEvent` to pass both window handles to `DualCameraManager.start()`
- [ ] 3.4 Update capture button to call `DualCameraManager.capture()` and show status for both cameras
- [ ] 3.5 Show "Camera not connected" in the preview panel for a missing camera
- [ ] 3.6 Route per-camera errors to the corresponding preview panel

## 4. Entry point update

- [ ] 4.1 Update `main.py` to use `find_uvc_cameras()` and create `DualCameraManager` with detected devices
- [ ] 4.2 Wire `aboutToQuit` to `DualCameraManager.stop()` instead of single pipeline stop
- [ ] 4.3 Update CLI help text and window title for dual-camera mode
