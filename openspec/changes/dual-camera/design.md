## Context

Phase 1 established a working single-camera pipeline (`CameraPipeline`) with VideoOverlay preview and raw MJPEG capture on Jetson. The codebase currently has three source files: `camera_pipeline.py` (pipeline + auto-detect + capture), `main_window.py` (single-preview GUI), and `main.py` (entry point). The product requires dual 20MP UVC cameras streaming simultaneously.

Two independent UVC cameras have no hardware sync — "simultaneous" capture means reading both latest cached frames at the same software moment.

## Goals / Non-Goals

**Goals:**
- Two cameras previewing side-by-side in a single window, each via its own VideoOverlay sink
- Single capture button saves both latest frames with a shared timestamp
- Graceful degradation: if only one camera is detected, run in single-camera mode
- `DualCameraManager` as the coordination layer so `MainWindow` doesn't manage pipelines directly

**Non-Goals:**
- Hardware-synchronized exposure across cameras
- Hot-plug recovery (Phase 4)
- Status bar with FPS / connection indicators (Phase 3)
- Folder picker or naming rule configuration (Phase 3)

## Decisions

### 1. New `DualCameraManager` class in `src/dual_camera_manager.py`

**Choice:** Separate module rather than expanding `CameraPipeline` or `MainWindow`.

**Rationale:** `CameraPipeline` is intentionally per-camera and should stay that way. `MainWindow` should not own pipeline coordination logic. A dedicated manager keeps responsibilities clean and makes the Phase 3 GUI additions straightforward.

**Responsibilities:**
- Own two `CameraPipeline` instances (cam0, cam1)
- `start(handles)` / `stop()` lifecycle for both
- `capture()` reads both latest samples with one shared timestamp, writes `cam0_<ts>.jpg` + `cam1_<ts>.jpg`
- Expose per-camera state and error signals

### 2. Extend `find_uvc_camera()` → `find_uvc_cameras()`

**Choice:** Add a new `find_uvc_cameras() -> list[str]` function that returns all UVC capture devices, keep `find_uvc_camera()` as a convenience wrapper.

**Rationale:** Minimal change to existing code. The new function scans all `/dev/videoX` devices (same sysfs + ioctl logic) and returns the full list. `main.py` uses the list to assign cam0/cam1.

**Alternative considered:** Passing device paths manually via CLI. Rejected because auto-detection is already proven and manual paths are error-prone with USB enumeration order.

### 3. Two `_PreviewWidget` instances in `MainWindow`

**Choice:** Horizontal `QHBoxLayout` with two `_PreviewWidget` containers, each bound to its own `CameraPipeline` via separate VideoOverlay handles.

**Rationale:** Each `nveglglessink` instance needs its own native window handle. Two `_PreviewWidget` instances (each with `WA_NativeWindow`) provide two distinct X11 windows for GStreamer to render into. This is the same pattern as Phase 1, just duplicated.

**Layout:**
```
┌──────────────────┬──────────────────┐
│   Camera 0       │   Camera 1       │
│   (720p preview) │   (720p preview) │
├──────────────────┴──────────────────┤
│  [Capture]   Status: ...            │
└─────────────────────────────────────┘
```

### 4. Capture naming: `cam{N}_{timestamp}.jpg`

**Choice:** Prefix with camera index, shared timestamp across both cameras in a single capture action.

**Rationale:** Makes it trivial to pair left/right images by timestamp. The `DualCameraManager.capture()` method generates the timestamp once and passes it to both `CameraPipeline.capture_to_file()` calls.

### 5. Single-camera fallback

**Choice:** If only one UVC device is detected, `DualCameraManager` runs with one pipeline. The second preview panel shows "Camera not connected". No error, no crash.

**Rationale:** During development or if a cable is loose, the app should still be usable with one camera.

## Risks / Trade-offs

- **Two `nveglglessink` instances on one GPU** → Jetson Orin has sufficient GPU/display resources for two 720p overlay sinks. Validated assumption based on Orin specs; needs testing.
  Mitigation: If GPU resources are insufficient, fall back to appsink-to-QImage for one or both previews.

- **USB bandwidth for two 20MP MJPEG streams** → Two cameras at 5120x3840 @ 27.5 FPS MJPEG require significant USB bandwidth.
  Mitigation: Cameras should be on separate USB buses (USB2 + USB3 or two USB3 ports). This is a hardware setup concern, not a software issue.

- **Capture timing skew** → Reading two `_latest_sample` values is not atomic across both pipelines. Skew could be up to one frame interval (~36 ms).
  Mitigation: Acceptable for the use case (no hardware sync). Document the limitation.
