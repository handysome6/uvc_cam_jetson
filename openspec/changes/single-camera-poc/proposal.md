## Why

This is a greenfield project — no application code exists yet. Before building the full dual-camera GUI, we need to validate the critical path: can a PySide6 app embed a live GStreamer preview of a 20MP UVC MJPEG stream and simultaneously save raw full-resolution frames on demand? This PoC de-risks the entire project by proving the GStreamer-to-Qt integration and the zero-re-encoding capture strategy on a single camera first.

## What Changes

- Introduce the foundational `CameraPipeline` class that builds and manages a GStreamer pipeline with preview and capture branches
- Implement GStreamer VideoOverlay embedding into a PySide6 `QWidget` for live 720p preview (with appsink-to-QImage fallback path)
- Implement raw MJPEG frame capture: continuously cache the latest sample from appsink and write raw bytes to `.jpg` on button press
- Create a minimal `MainWindow` with a single preview panel and a capture button
- File writes happen on a worker thread to avoid blocking the UI

## Capabilities

### New Capabilities
- `camera-pipeline`: GStreamer pipeline lifecycle (build, start, stop) with tee-split into preview and capture branches, latest-frame caching, and `capture_to_file(path)` interface
- `preview-embed`: Embedding GStreamer video sink into a PySide6 widget via VideoOverlay (primary) or appsink-to-QImage (fallback)
- `frame-capture`: Single-click raw MJPEG frame save to disk on a worker thread without re-encoding
- `single-camera-gui`: Minimal PySide6 window with one preview panel, capture button, and basic status feedback

### Modified Capabilities

(none — greenfield project)

## Impact

- **New files**: application entry point, `CameraPipeline` module, `MainWindow` module
- **Dependencies**: PySide6, GStreamer Python bindings (`gi.repository: Gst, GstVideo`)
- **Platform**: runs on Jetson Orin with `nvv4l2decoder`/`nvvidconv`; preview sink may differ on dev machines (e.g., `autovideosink` on macOS)
- **Devices**: requires at least one UVC camera at `/dev/video0`
