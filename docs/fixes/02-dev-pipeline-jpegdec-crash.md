# Fix: Dev pipeline crashes with libjpeg decode error at 5120x3840

## Error behavior

When the app fell through to the dev-machine pipeline (due to the Jetson detection bug above), GStreamer logged:

```
GStreamer error: gst-stream-error-quark: Failed to decode JPEG image (7)
debug: ../ext/jpeg/gstjpegdec.c(1557): gst_jpeg_dec_handle_frame():
  Decode error #21: Improper call to JPEG library in state 205
```

The pipeline failed roughly 3 seconds after starting, and the preview never rendered.

## Error deduction

The dev-machine pipeline string was:

```
videotestsrc is-live=true pattern=ball !
  video/x-raw,width=5120,height=3840,framerate=55/2 !
  jpegenc ! image/jpeg !
  tee name=t
  t. ! queue ! jpegdec ! videoconvert ! videoscale ! ... ! appsink
  t. ! queue leaky=downstream ... ! appsink
```

This pipeline:

1. Generates raw video at **5120x3840 @ 27.5 fps** (~53 megapixels/second)
2. Software-encodes it to JPEG via `jpegenc`
3. Software-decodes it back via `jpegdec`

At this resolution and frame rate, libjpeg's internal state machine was overwhelmed, producing error #21 ("Improper call to JPEG library in state 205"). The 5120x3840 resolution was copied from the Jetson pipeline (which uses HW decode) but is far too heavy for a software encode/decode cycle.

## Fix

The dev pipeline exists only to exercise the GUI and pipeline logic without a real camera. There is no reason to encode/decode at the camera's native resolution.

Changed the dev-machine test source from 5120x3840 to **1280x720 @ 27 fps** (`src/camera_pipeline.py`):

```python
src = (
    "videotestsrc is-live=true pattern=ball ! "
    f"video/x-raw,width={W},height={H},framerate=27/1 ! "
    "jpegenc ! image/jpeg ! "
    "tee name=t "
)
```

Since the test source already outputs at preview resolution (1280x720), the `videoscale` element was also removed from the preview branch — it was no longer needed.

**Commit:** `6653701` — Fix Jetson detection and dev pipeline crash at 5120x3840
