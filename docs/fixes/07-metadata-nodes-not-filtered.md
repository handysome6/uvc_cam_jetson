# Fix: Metadata-only /dev/video nodes not filtered from device selector

## Error behavior

With two USB UVC cameras connected, the single-camera script (`scirpts/gst_uvc_single_cam.py`) listed 4 devices instead of 2:

```
Available camera devices:
  [1] /dev/video0 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2))
  [2] /dev/video1 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2))
  [3] /dev/video2 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2.3))
  [4] /dev/video3 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2.3))
```

Each physical camera exposes two `/dev/video*` nodes — one for video capture, one for metadata only. Selecting a metadata node (video1 or video3) would fail to stream.

## Error deduction

The `scan_camera_devices()` function parsed `v4l2-ctl --list-devices` output and included every `/dev/video*` path without checking whether the node supports actual video capture.

The dual-camera GUI (`src/camera_pipeline.py`) already had a `_is_capture_device()` ioctl check, but it was reading the wrong struct offset. The `v4l2_capability` struct layout:

```c
struct v4l2_capability {
    __u8   driver[16];       // offset  0
    __u8   card[32];         // offset 16
    __u8   bus_info[32];     // offset 48
    __u32  version;          // offset 80
    __u32  capabilities;     // offset 84  (overall device caps)
    __u32  device_caps;      // offset 88  (this node's caps)
    __u32  reserved[3];      // offset 92
};
```

The code was reading at offset 20 — inside the `card` name string, not a capabilities field at all. The bytes at that offset happened to have the `V4L2_CAP_VIDEO_CAPTURE` bit set by coincidence (card name `"DECXIN Camera..."` has `0x49` = `'I'` at that position, which has bit 0 set).

## Investigation

Added debug logging to `_is_capture_device()` to print the raw capability value for each device:

```
DEBUG: /dev/video0 caps=0x43204e49 has_capture=True
DEBUG: /dev/video1 caps=0x43204e49 has_capture=True
DEBUG: /dev/video2 caps=0x43204e49 has_capture=True
DEBUG: /dev/video3 caps=0x43204e49 has_capture=True
```

All 4 devices reported the same value (`0x43204e49`), which is clearly not a valid capabilities bitmask — it decodes to ASCII `"C NI"`, part of the card name. This confirmed the wrong struct offset.

Cross-referencing with `v4l2-ctl -d /dev/videoX --all` output showed the correct per-node capabilities:

| Device | `device_caps` (offset 88) | Flags |
|--------|--------------------------|-------|
| /dev/video0 | `0x04200001` | Video Capture, Streaming, Extended Pix Format |
| /dev/video1 | `0x04a00000` | Metadata Capture, Streaming, Extended Pix Format |
| /dev/video2 | `0x04200001` | Video Capture, Streaming, Extended Pix Format |
| /dev/video3 | `0x04a00000` | Metadata Capture, Streaming, Extended Pix Format |

The `device_caps` field at offset 88 correctly distinguishes capture nodes (bit 0 set) from metadata-only nodes (bit 0 clear).

## Fix

### 1. Fix struct offset in both files

Changed `struct.unpack_from("I", info, 20)` to `struct.unpack_from("I", info, 88)` to read the `device_caps` field instead of bytes inside the card name.

**`src/camera_pipeline.py`:**
```python
device_caps = struct.unpack_from("I", info, 88)[0]  # .device_caps field
return bool(device_caps & _V4L2_CAP_VIDEO_CAPTURE)
```

**`scirpts/gst_uvc_single_cam.py`:**
Same fix applied to the duplicated `_is_capture_device()` function.

### 2. Add ioctl filtering to single-camera script

Added `_is_capture_device()` (duplicated from `src/camera_pipeline.py`) to `scirpts/gst_uvc_single_cam.py` and added it as a filter condition in `scan_camera_devices()`:

```python
if re.fullmatch(r"/dev/video\d+", stripped) and stripped not in seen and _is_capture_device(stripped):
```

This preserves the human-readable labels from `v4l2-ctl --list-devices` while filtering out metadata-only nodes.

### Result

```
Available camera devices:
  [1] /dev/video0 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2))
  [2] /dev/video2 (DECXIN Camera: DECXIN Camera (usb-3610000.usb-2.3))
```

**Commits:** `28bbc0b`, `18b2b9f`, `460a26f`
