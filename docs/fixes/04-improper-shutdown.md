# Fix: GStreamer pipeline and threads not cleaned up on exit/kill

## Error behavior

When the application was closed (window X button) or killed (Ctrl+C, `kill`), the GStreamer pipeline was not fully shut down:

- **`set_state(NULL)` was fire-and-forget** — the call returned immediately, but GStreamer's internal streaming threads could still be running when the process exited. This could leave the UVC device locked (subsequent launches fail with "device busy").
- **Pending file writes could be interrupted** — if the user clicked Capture and immediately closed the window, the `QThreadPool` worker writing the `.jpg` file might be killed mid-write, producing a corrupt file.
- **Ctrl+C / SIGTERM did nothing** — there was no signal handler, so these signals killed the process without running any cleanup. The GStreamer pipeline was never set to NULL.
- **No safety net beyond `closeEvent`** — if the application exited through any path other than clicking the window X button (e.g., `sys.exit()` from another part of the code), the pipeline was never stopped.

## Error deduction

Three gaps in the shutdown path:

1. `CameraPipeline.stop()` called `self._pipeline.set_state(Gst.State.NULL)` but did not wait for the state change to complete. GStreamer state transitions are asynchronous — the pipeline's streaming threads continue running until the transition actually reaches NULL.

2. No `signal.signal(SIGINT, ...)` or `signal.signal(SIGTERM, ...)` handlers were installed. Python's default behavior for SIGINT is to raise `KeyboardInterrupt`, which does not trigger Qt's `closeEvent`. SIGTERM simply terminates the process.

3. `QApplication.aboutToQuit` was not connected to any cleanup logic, so exit paths that bypass the window's `closeEvent` skipped pipeline shutdown entirely.

## Fix

### `stop()` blocks until resources are released (`src/camera_pipeline.py`)

After `set_state(NULL)`, the method now calls `get_state(3 * Gst.SECOND)` which blocks until GStreamer actually reaches NULL state (up to a 3-second safety timeout):

```python
self._pipeline.set_state(Gst.State.NULL)
self._pipeline.get_state(3 * Gst.SECOND)   # block until streaming threads drain
```

After the pipeline is torn down, it waits for any in-flight file-write tasks:

```python
QThreadPool.globalInstance().waitForDone(2000)  # up to 2 s
```

The method is also now **idempotent** — calling `stop()` twice (e.g., from both `closeEvent` and `aboutToQuit`) is safe:

```python
if self._state == "stopped" and self._pipeline is None:
    return
```

### Signal handlers installed (`src/main.py`)

SIGINT and SIGTERM now route through Qt's event loop:

```python
def _setup_signals(app: QApplication):
    def _handler(signum, _frame):
        app.quit()
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)
```

`app.quit()` posts a quit event to the Qt event loop, which triggers the normal shutdown sequence: `closeEvent` → `pipeline.stop()`.

### `aboutToQuit` safety net (`src/main.py`)

```python
app.aboutToQuit.connect(window._pipeline.stop)
```

This ensures `pipeline.stop()` runs on every exit path — not just window close.

### Shutdown flow after fix

```
SIGINT/SIGTERM/window close
  → app.quit()
  → closeEvent() calls pipeline.stop()
  → aboutToQuit also calls pipeline.stop() (idempotent, no-op if already stopped)
  → stop():
      1. bus_timer.stop()
      2. pipeline.set_state(NULL)
      3. pipeline.get_state(3s)    ← blocks until GStreamer threads drain
      4. QThreadPool.waitForDone(2s) ← blocks until file writes finish
      5. state = "stopped"
```

**Commit:** `06de1b5` — Add UVC device auto-detection and proper shutdown
