# Fix: Jetson platform detection returns False on actual Jetson

## Error behavior

On Jetson Orin (`jetson@ubuntu`), the application logs:

```
Platform: Dev machine (SW path)
```

This causes the app to use `videotestsrc` (dev fallback) instead of `v4l2src` with Jetson HW-accelerated decode, even though all NVIDIA GStreamer plugins are installed on the host.

## Error deduction

`is_jetson()` checked for a GStreamer **plugin** named `"nvv4l2"`:

```python
Gst.Registry.get().find_plugin("nvv4l2") is not None
```

GStreamer plugin names vary across JetPack SDK versions. The plugin package may register under a different name (e.g., `nvvideo4l2`) depending on the installed JetPack. This is a fragile check — the plugin name is an internal registry detail, not a stable API.

## Fix

Replaced the plugin-name lookup with two more reliable checks (`src/camera_pipeline.py`):

1. **Element factory check** — query for the specific GStreamer element we actually use:
   ```python
   Gst.ElementFactory.find("nvv4l2decoder") is not None
   ```
   This works regardless of the plugin's internal registry name.

2. **Filesystem fallback** — check for `/etc/nv_tegra_release`, a marker file present on every Jetson platform across all JetPack versions:
   ```python
   os.path.exists("/etc/nv_tegra_release")
   ```

Final implementation:

```python
def is_jetson() -> bool:
    if Gst.ElementFactory.find("nvv4l2decoder") is not None:
        result = True
    else:
        result = os.path.exists("/etc/nv_tegra_release")
    return result
```

**Commit:** `6653701` — Fix Jetson detection and dev pipeline crash at 5120x3840
