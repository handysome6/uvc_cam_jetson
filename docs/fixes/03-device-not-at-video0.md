# Fix: Camera not always at /dev/video0

## Error behavior

The `--device` flag defaulted to `/dev/video0`. On some Jetson boots, the UVC camera enumerated at `/dev/video1` (or `/dev/video2`), causing:

```
Cannot open device /dev/video0, exiting.
```

The user had to manually discover the correct device path via a helper script or `v4l2-ctl --list-devices` each time.

## Error deduction

Linux assigns `/dev/videoX` numbers based on probe order. Platform cameras (e.g., Tegra RTCPU virtual media devices) often claim `/dev/video0` and `/dev/media0`, pushing USB UVC cameras to higher numbers. The assignment is not stable across reboots.

Example from the Jetson:

```
NVIDIA Tegra Video Input Device (platform:tegra-camrtc-ca):
        /dev/media0

DECXIN Camera: DECXIN Camera (usb-3610000.usb-2):
        /dev/video1
        /dev/video2
        /dev/media1
```

Here `/dev/video0` does not exist at all — the first device is the platform camera at `/dev/media0`, and the USB camera starts at `/dev/video1`.

## Fix

Added UVC auto-detection in `src/camera_pipeline.py` via two new functions:

### `find_uvc_camera() -> str | None`

Scans `/sys/class/video4linux/video*` and for each entry:

1. **Resolves the sysfs symlink** — if the real path does not contain `"usb"`, the device is skipped (filters out platform/ISP cameras).
2. **Probes V4L2 capture capability** — opens the `/dev/videoX` device and calls `VIDIOC_QUERYCAP` ioctl. Only devices with `V4L2_CAP_VIDEO_CAPTURE` are returned (filters out metadata-only nodes like `/dev/video2`).

No external tools are required — uses only `os`, `glob`, `fcntl`, and `struct`.

### `_is_capture_device(dev_path: str) -> bool`

Uses the `VIDIOC_QUERYCAP` ioctl (constant `0x80685600`) to read the `v4l2_capability` struct and checks the `capabilities` field for `V4L2_CAP_VIDEO_CAPTURE` (`0x00000001`).

### Changes to `main.py`

- `--device` default changed from `"/dev/video0"` to `"auto"`
- When `"auto"`, calls `find_uvc_camera()`:
  - If found: logs `Auto-detected camera: /dev/videoX` and proceeds
  - If not found: logs an error and exits cleanly with `sys.exit(1)` before GStreamer ever tries to open the device

```
$ uv run python main.py
Auto-detected camera: /dev/video1
Config | device=/dev/video1 preview=VideoOverlay
```

Manual override is still available: `python main.py --device /dev/video3`

**Commit:** `06de1b5` — Add UVC device auto-detection and proper shutdown
