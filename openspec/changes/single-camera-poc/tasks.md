## 1. Project Setup

- [x] 1.1 Create `src/` directory and `src/main.py` entry point with `QApplication` bootstrap and GStreamer initialization (`Gst.init()`)
- [x] 1.2 Add platform detection utility: check GStreamer plugin registry for `nvv4l2decoder` to determine Jetson vs dev machine

## 2. CameraPipeline Core

- [x] 2.1 Implement `CameraPipeline.__init__` that accepts device path and preview mode flag, and builds the GStreamer pipeline string with tee-split (preview + capture branches)
- [x] 2.2 Implement platform-adaptive pipeline string: Jetson path (`jpegparse ! nvv4l2decoder ! nvvidconv ! nveglglessink`) vs dev path (`jpegdec ! videoconvert ! autovideosink`)
- [x] 2.3 Implement `start()` and `stop()` methods for pipeline lifecycle (PLAYING / NULL state transitions)
- [x] 2.4 Implement capture appsink `new-sample` callback that caches the latest `GstSample` in a thread-safe manner
- [x] 2.5 Implement GStreamer bus message handling (error, EOS) integrated with Qt event loop via timer-based bus poll — expose pipeline state (playing/stopped/error)

## 3. Preview Embedding

- [x] 3.1 Implement VideoOverlay path: on `sync-message` with `prepare-window-handle`, call `set_window_handle()` with the preview widget's `winId()`
- [x] 3.2 Implement appsink-to-QImage fallback path: pull decoded 720p frames from a preview appsink, convert to `QImage`/`QPixmap`, display in `QLabel`
- [x] 3.3 Handle widget resize events — call `expose()` on the VideoOverlay sink when the preview widget is resized

## 4. Frame Capture

- [x] 4.1 Implement `capture_to_file(path)`: extract raw bytes from cached `GstSample`'s `GstBuffer` via `buffer.map()`, write to `.jpg` file
- [x] 4.2 Implement `QRunnable`-based worker that performs the file write on `QThreadPool` to avoid blocking the UI thread
- [x] 4.3 Implement timestamp-based filename generation with millisecond precision (e.g., `capture_20260327_143052_123.jpg`)

## 5. Main Window GUI

- [x] 5.1 Create `MainWindow` with a preview `QWidget` (for VideoOverlay) or `QLabel` (for fallback) and a capture `QPushButton`
- [x] 5.2 Wire capture button click to `CameraPipeline.capture_to_file()` with generated filename and provide visual feedback (e.g., brief button text change)
- [x] 5.3 Start pipeline on window show, stop pipeline and release resources on window close (`closeEvent`)
- [x] 5.4 Display error message in preview area when camera is not found or pipeline fails

## 6. Integration & Verification

- [x] 6.1 End-to-end test: launch app, verify preview renders in the GUI window (VideoOverlay or fallback)
- [x] 6.2 End-to-end test: click capture, verify `.jpg` file is saved with correct raw MJPEG bytes (file size matches a 20MP JPEG, no re-encoding artifacts)
- [x] 6.3 Verify UI remains responsive during capture (preview doesn't freeze, button is clickable)
