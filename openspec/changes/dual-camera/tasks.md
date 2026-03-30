## 1. Multi-device discovery

- [x] 1.1 Add `find_uvc_cameras()` function to `camera_pipeline.py` that returns a list of all USB UVC capture device paths
- [x] 1.2 Update `find_uvc_camera()` to delegate to `find_uvc_cameras()` (return first result or None)

## 2. DualCameraManager

- [x] 2.1 Create `src/dual_camera_manager.py` with `DualCameraManager` class that owns two `CameraPipeline` instances (cam0, cam1)
- [x] 2.2 Implement `start(handles)` that starts both pipelines with their respective window handles
- [x] 2.3 Implement `stop()` that stops both pipelines and waits for resources to release
- [x] 2.4 Update `capture(directory)` to use position-based naming: `A_<ts>.jpg` (left canvas) / `D_<ts>.jpg` (right canvas) based on current camera-to-canvas mapping
- [x] 2.5 Add per-camera error/state signals (forward from each CameraPipeline with camera index)
- [x] 2.6 Handle single-camera mode: gracefully skip the absent pipeline slot
- [x] 2.7 Add `swap_cameras()` method that reverses the camera-to-canvas mapping
- [x] 2.8 Add `cameras_swapped` signal to notify GUI when mapping changes
- [x] 2.9 Maintain `_camera_mapping` list to track which pipeline index maps to each canvas position

## 3. Dual-camera GUI

- [x] 3.1 Refactor `MainWindow` to accept `DualCameraManager` instead of a single `CameraPipeline`
- [x] 3.2 Update two side-by-side `_PreviewWidget` instances with position labels: "Left (A)" and "Right (D)"
- [x] 3.3 Update `showEvent` to pass both window handles to `DualCameraManager.start()`
- [x] 3.4 Update capture button to call `DualCameraManager.capture()` and show status for both cameras
- [x] 3.5 Show "Camera not connected" in the preview panel for a missing camera
- [x] 3.6 Route per-camera errors to the corresponding preview panel
- [x] 3.7 Add "Swap Cameras" button that calls `DualCameraManager.swap_cameras()`
- [x] 3.8 Handle `cameras_swapped` signal: stop pipelines, swap window handle assignments, restart pipelines

## 4. Entry point update

- [x] 4.1 Update `main.py` to use `find_uvc_cameras()` and create `DualCameraManager` with detected devices
- [x] 4.2 Wire `aboutToQuit` to `DualCameraManager.stop()` instead of single pipeline stop
- [x] 4.3 Update CLI help text and window title for dual-camera mode
