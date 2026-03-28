# Fix: `nveglglessink` has no `set_window_handle` attribute

## Error behavior

On Jetson Orin, the application starts and the pipeline reaches PLAYING state, but the preview window stays black. The log shows:

```
VideoOverlay: setting window handle 0x2c0000c
Traceback (most recent call last):
  File ".../camera_pipeline.py", line 410, in _on_sync_message
    message.src.set_window_handle(self._window_handle)
AttributeError: 'GstEglGlesSink' object has no attribute 'set_window_handle'
```

The pipeline continues running (decode and capture branches work), but no video is rendered to the Qt widget.

## Error deduction

The `_on_sync_message` handler called `set_window_handle()` directly on the GStreamer element object:

```python
message.src.set_window_handle(self._window_handle)
```

On some GStreamer Python bindings (e.g., `autovideosink` on desktop Linux), the element object exposes VideoOverlay methods directly as Python attributes. However, `nveglglessink` on Jetson does **not** — it implements the `GstVideoOverlay` interface at the C level, but the PyGObject introspection layer does not promote those methods onto the element instance.

The correct way to call interface methods in GStreamer's Python bindings is through the interface class itself (e.g., `GstVideo.VideoOverlay.set_window_handle(element, handle)`), which performs the proper GInterface cast internally.

A second issue compounded this: `GstVideo` was already declared with `gi.require_version('GstVideo', '1.0')` but was never actually imported from `gi.repository`, so the interface class was unavailable even if the code had tried to use it.

## Fix

### 1. Import `GstVideo` (`src/camera_pipeline.py`)

```python
# Before
from gi.repository import Gst

# After
from gi.repository import Gst, GstVideo
```

### 2. Use `GstVideo.VideoOverlay` interface (`src/camera_pipeline.py`)

```python
# Before
message.src.set_window_handle(self._window_handle)

# After
GstVideo.VideoOverlay.set_window_handle(message.src, self._window_handle)
```

This calls the C-level `gst_video_overlay_set_window_handle()` function through proper GInterface dispatch, which works on all GStreamer video sinks that implement the VideoOverlay interface — including `nveglglessink`, `autovideosink`, and `xvimagesink`.

**Commit:** *(pending)*
