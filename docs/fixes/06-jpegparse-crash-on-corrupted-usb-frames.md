# Fix: `jpegparse` crashes pipeline on corrupted MJPEG frames from USB

## Error behavior

During live preview with 20MP UVC cameras (5120x3840 MJPEG @ 27.5 fps), the pipeline crashes after 9 seconds to 9 minutes with:

```
ERROR: from element /GstPipeline:pipeline0/GstJpegParse:jpegparse0: Failed to parse stream
Additional debug info:
../libs/gst/base/gstbaseparse.c(3012): gst_base_parse_check_sync (): /GstPipeline:pipeline0/GstJpegParse:jpegparse0
```

Before the crash, the preview shows visual artifacts: flickering horizontal lines and black/white rectangular blocks. The crash timing is random and varies across runs. The issue is reproducible with a specific USB-A-to-C cable but not with other cables.

## Error deduction

The pipeline was:

```
v4l2src ! image/jpeg,5120x3840 ! jpegparse ! nvv4l2decoder ! nvvidconv ! nveglglessink
```

At 5120x3840 @ 27.5 fps, each MJPEG frame is ~1-5 MB, requiring ~55-140 MB/s sustained USB bandwidth. A marginal USB cable introduces intermittent bit-level corruption in the transfer.

`jpegparse` calls `gst_base_parse_check_sync()` which verifies JPEG marker structure. When a corrupted frame arrives with invalid markers (missing SOI, broken segment headers, etc.), `jpegparse` cannot resync and posts a fatal `GST_FLOW_ERROR`, killing the entire pipeline. There is no built-in error tolerance — a single badly-corrupted frame is fatal.

**Removing `jpegparse`** was tested first but made things worse: `nvv4l2decoder` without `jpegparse` loses frame alignment, producing severe tearing on most frames. `jpegparse` is necessary because it produces `parsed=true` caps that the decoder requires for proper framing.

## Investigation

The `gst-launch-1.0` pipeline was converted to a programmatic Python GStreamer pipeline (`gst_uvc_single_cam.py`) to enable pad probes. A JPEG validation pad probe was added before `jpegparse` to drop corrupted frames before they reach the parser.

Three independently toggleable checks were implemented:
- **SOI**: verify `0xFFD8` at frame start
- **EOI**: verify `0xFFD9` at frame end
- **Walk**: walk all JPEG marker segments, verifying types and lengths

An automated test harness (`test_validation_flags.sh`) ran all 8 flag combinations for 5 minutes each:

```
FLAGS                                          RESULT  DURATION
all checks ON                                  PASS    300s
--no-check-soi                                 PASS    301s
--no-check-eoi                                 FAIL    35s
--no-check-walk                                PASS    301s
--no-check-soi --no-check-eoi                  FAIL    30s
--no-check-soi --no-check-walk                 FAIL    5s
--no-check-eoi --no-check-walk                 FAIL    81s
all checks OFF                                 FAIL    34s
```

**Findings:**
- **EOI is the critical check** — every PASS case has EOI enabled, every case without it crashes
- **EOI alone is not sufficient** — needs at least SOI or walk as a second layer
- **SOI + EOI (no walk) is sufficient** — survived 5 minutes with the fewest unnecessary drops
- **The marker walk is not needed** to prevent crashes; it only adds ~250 extra drops per 5 minutes that `jpegparse` would have handled fine

The root cause is USB transfer errors corrupting or truncating the tail end of large MJPEG frames, destroying the EOI marker (`0xFFD9`).

## Fix

### 1. Convert to programmatic GStreamer pipeline (`gst_uvc_single_cam.py`)

Replaced `gst-launch-1.0` invocation with Python GStreamer bindings (`gi.repository.Gst`) to enable pad probes.

### 2. Add JPEG validation pad probe

A buffer pad probe on `jpegparse`'s sink pad validates each frame before `jpegparse` sees it. Default checks (SOI + EOI):

```python
def validate_jpeg(data, check_soi=True, check_eoi=True, check_walk=False):
    size = len(data)
    if size < 4:
        return False
    if check_soi:
        if data[0] != 0xFF or data[1] != 0xD8:
            return False
    if check_eoi:
        if data[size - 2] != 0xFF or data[size - 1] != 0xD9:
            return False
    # ... optional marker walk ...
    return True
```

Invalid frames are dropped with `Gst.PadProbeReturn.DROP` — `jpegparse` never sees them and never loses sync.

### 3. Force `v4l2src io-mode=mmap`

Explicitly set `io-mode=mmap` to avoid auto-mode surprises in the kernel buffer pool.

### 4. Default to SOI + EOI only

The marker walk (`--check-walk`) is disabled by default. SOI + EOI provides crash prevention with minimal false-positive frame drops.

**Commits:** `5f5eda6`, `5fdac40`
