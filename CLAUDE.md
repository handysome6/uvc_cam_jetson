# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PySide6 GUI application for dual 20MP UVC camera preview and capture on NVIDIA Jetson Orin. Two USB UVC cameras stream MJPEG at 5120x3840 @ 27.5 FPS. The GUI shows dual 720p live previews and supports single-click full-resolution capture (saving raw MJPEG frames as .jpg without re-encoding).

## Target Platform

- NVIDIA Jetson Orin (aarch64, Linux)
- GStreamer with Jetson hardware-accelerated plugins (`nvv4l2decoder`, `nvvidconv`, `nveglglessink`)
- Development may happen on macOS but the app runs on Jetson

## Architecture

Each camera runs an independent GStreamer pipeline with a `tee` splitting into two branches:

```
v4l2src (MJPEG 5120x3840)
  -> tee
     ├─ Preview branch: jpegparse -> nvv4l2decoder -> nvvidconv -> 720p sink (GUI)
     └─ Capture branch: queue(leaky) -> appsink (latest MJPEG frame only)
```

**Key classes to implement:**
- `CameraPipeline` — one per camera; builds/starts/stops the GStreamer pipeline, maintains the latest MJPEG sample, provides `capture_to_file(path)`
- `DualCameraManager` — manages two `CameraPipeline` instances, coordinates simultaneous capture, handles naming/timestamps
- `MainWindow` — two preview panels, capture button, connection status, save path config

## Critical Design Constraints

- **No re-encoding on capture**: save raw MJPEG buffer bytes directly as .jpg — never use `cv::imwrite()` or similar
- **Capture branch must be leaky**: `queue leaky=downstream max-size-buffers=1` + `appsink drop=true max-buffers=1` — only keep the latest frame, never queue history
- **Always-cached latest frame**: don't pull a frame on-demand at capture time; continuously cache the latest sample and write it on button press
- **File writes on worker thread**: never block the UI thread for disk I/O
- **No hardware sync between cameras**: two independent UVC cameras have no synchronized exposure; "simultaneous" capture means reading both latest frames at the same moment in software

## GUI Embedding Strategy

Preferred approach (try first): **VideoOverlay** — bind GStreamer video sink to a Qt widget window handle via `GstVideoOverlay` interface. Fallback: **appsink to QImage** — pull decoded 720p frames from appsink and display via `QPixmap` in Qt (more CPU overhead).

## Tech Stack

- **Python 3** with **PySide6** (Qt 6)
- **GStreamer** (via `gi.repository: Gst, GstVideo`) for pipeline management
- GStreamer source: `v4l2src` (not `nvv4l2camerasrc`)
- Camera devices: `/dev/video0`, `/dev/video1` (or as detected)

## Development Phases

1. Single-camera preview + appsink capture PoC
2. Dual-camera parallel preview + simultaneous capture
3. Full GUI with status bar (FPS, connection state, last capture), folder picker, naming rules
4. Stability: 30min+ continuous run, capture stress test, hot-plug recovery
