## Context

This is a greenfield PySide6 + GStreamer application targeting Jetson Orin. The underlying media pipeline (v4l2src → jpegparse → nvv4l2decoder → nvvidconv → 720p sink) has already been validated via `gst-launch-1.0`. No application code exists yet. This design covers the Phase 1 single-camera PoC only; dual-camera, full GUI, and stability hardening are future phases.

## Goals / Non-Goals

**Goals:**
- Prove GStreamer pipeline can be built programmatically in Python and embedded in a PySide6 window
- Validate the tee-split architecture: one preview branch, one raw MJPEG capture branch
- Demonstrate zero-re-encoding capture (raw MJPEG bytes → .jpg file)
- Establish the `CameraPipeline` class interface that Phase 2 will reuse for dual-camera

**Non-Goals:**
- Dual-camera support (Phase 2)
- Full GUI features: status bar, FPS counter, folder picker, naming rules (Phase 3)
- Hot-plug recovery, long-run stability testing (Phase 4)
- C++ implementation (future product hardening)
- Camera parameter control (exposure, white balance, etc.)

## Decisions

### 1. Python GStreamer bindings via `gi.repository`

Use `gi.repository` (PyGObject/GObject Introspection) for GStreamer, not `gst-python`. This is the standard Jetson-supported path — the Jetson SDK ships GI bindings.

**Alternative considered:** `gst-python` — less commonly packaged on Jetson, no advantage for this use case.

### 2. Pipeline construction via `Gst.parse_launch`

Build the pipeline from a launch string rather than manual element-by-element construction. The pipeline topology is well-defined and already validated as a gst-launch command. `parse_launch` keeps the code concise and close to the tested shell pipeline.

**Alternative considered:** Manual `Gst.ElementFactory.make` + linking — more verbose, better for dynamic pipelines, unnecessary here.

### 3. Preview embedding: VideoOverlay first, appsink fallback

Primary path: use `GstVideoOverlay.set_window_handle()` to render directly into a `QWidget.winId()`. This avoids CPU-side pixel copies.

Fallback path (if VideoOverlay doesn't work with the Jetson display stack or during macOS dev): replace the preview sink with an appsink that converts decoded 720p frames to `QImage` → `QPixmap` for display in a `QLabel`.

The `CameraPipeline` class will accept a flag or factory to switch between these modes.

**Alternative considered:** Always use appsink-to-QImage — simpler but wastes CPU copying every frame at 27.5 FPS.

### 4. Capture branch: always-running leaky appsink

The capture appsink runs continuously with `drop=true max-buffers=1`. A `new-sample` signal callback caches the latest `GstSample` in a thread-safe attribute. On capture, the cached sample's buffer bytes are written to disk.

**Alternative considered:** Pull sample on-demand at capture time — risks stale or missing frames if the pipeline hasn't pushed recently.

### 5. File I/O on QThreadPool

Use `QRunnable` + `QThreadPool` for writing captured frames to disk. This keeps the UI thread responsive. The write is a simple `open(path, 'wb').write(buffer_bytes)` — no image library needed.

**Alternative considered:** Python `threading.Thread` — works fine but `QThreadPool` integrates naturally with Qt's event model and avoids thread lifecycle management.

### 6. Platform-adaptive sink selection

On Jetson: `nvv4l2decoder ! nvvidconv ! nveglglessink` (or `nv3dsink`).
On non-Jetson dev machines: `jpegdec ! videoconvert ! autovideosink` (software decode path).

Detected at startup by checking for the presence of `nvv4l2decoder` in the GStreamer plugin registry.

### 7. Module layout

```
src/
  main.py           # Entry point, QApplication setup
  camera_pipeline.py # CameraPipeline class
  main_window.py     # MainWindow with preview widget and capture button
```

Flat structure — no packages or abstractions beyond what's needed. Phase 2 will add `dual_camera_manager.py`.

## Risks / Trade-offs

- **[VideoOverlay may not work with PySide6 on Jetson's display stack]** → Mitigation: appsink-to-QImage fallback is implemented as a parallel code path and can be switched at startup.
- **[GStreamer main loop vs Qt event loop conflict]** → Mitigation: Do not run a separate `GLib.MainLoop`. Use `Gst.Bus.add_watch()` or a timer-based bus poll from the Qt event loop to handle GStreamer messages.
- **[macOS development can't test Jetson-specific plugins]** → Mitigation: Platform-adaptive sink selection allows developing and testing GUI logic on macOS with software decode, then deploying to Jetson for integration.
- **[appsink `new-sample` callback runs on GStreamer streaming thread]** → Mitigation: Only cache a reference to the `GstSample` (atomic swap); all heavy work (file I/O) happens on the Qt thread pool.
