## ADDED Requirements

### Requirement: Capture saves raw MJPEG bytes without re-encoding
When capture is triggered, the system SHALL extract the raw bytes from the cached `GstSample`'s `GstBuffer` and write them directly to a `.jpg` file. The system MUST NOT decode and re-encode the image.

#### Scenario: Captured file is byte-identical to MJPEG frame
- **WHEN** the user triggers a capture
- **THEN** the saved `.jpg` file contains the exact MJPEG bytes from the GStreamer buffer, with no re-encoding or pixel-level processing

### Requirement: Capture writes file on a worker thread
File I/O for saving captured frames SHALL happen on a background thread (via `QThreadPool`), never on the Qt main/UI thread.

#### Scenario: UI does not freeze during file save
- **WHEN** a capture is triggered and the file is being written to disk
- **THEN** the preview continues rendering and the UI remains responsive

### Requirement: Capture uses the latest cached frame
When capture is triggered, the system SHALL write the most recently cached MJPEG sample. It MUST NOT request a new frame from the pipeline on demand.

#### Scenario: Rapid captures get recent frames
- **WHEN** the user triggers two captures in quick succession
- **THEN** each capture writes whatever frame was cached at the moment the capture was triggered

### Requirement: Capture file naming includes timestamp
Each captured file SHALL be named with a timestamp to prevent overwrites and allow chronological ordering (e.g., `capture_20260327_143052_123.jpg`).

#### Scenario: Files are uniquely named
- **WHEN** multiple captures are triggered within the same second
- **THEN** each file has a unique name (using millisecond precision or a sequence counter)
