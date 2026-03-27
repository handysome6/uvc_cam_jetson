# Single-Camera PoC — Integration Testing Checklist

Run these on Jetson Orin with `/dev/video0` connected.

## 6.1 Preview renders in the GUI window

```bash
cd src
python main.py --device /dev/video0
```

Expected:
- Window opens showing a live 720p preview rendered inside the Qt widget (VideoOverlay mode).
- Preview is not in a separate floating window.
- Window title: "UVC Camera — Single Camera PoC"

Fallback (no overlay):
```bash
python main.py --device /dev/video0 --no-overlay
```
- Preview renders in the QLabel via appsink-to-QImage at ~27 FPS.

## 6.2 Capture saves raw MJPEG bytes

1. With the preview running, click **Capture**.
2. Check `~/captures/` for a file named `capture_YYYYMMDD_HHMMSS_mmm.jpg`.
3. Verify it is a valid JPEG (open in an image viewer — expect a full-resolution 20MP image).
4. Verify it is NOT re-encoded: file size should be consistent with a high-quality MJPEG frame
   (typically several MB for 5120×3840).

```bash
# Quick sanity check — file size and JPEG magic bytes:
ls -lh ~/captures/
file ~/captures/capture_*.jpg     # should say "JPEG image data"
```

## 6.3 UI stays responsive during capture

1. Hold the **Capture** button down rapidly (multi-click).
2. Observe: preview keeps running without freezing.
3. Observe: button text flips to "Saved!" and back within ~800 ms per click.
4. Observe: multiple `.jpg` files are created (unique timestamps).

## Dev machine (macOS) smoke test

```bash
python main.py --no-overlay   # uses videotestsrc (no camera needed)
```

Expected:
- Animated test pattern renders in preview QLabel.
- Clicking Capture saves a small JPEG of the test frame to ~/captures/.
