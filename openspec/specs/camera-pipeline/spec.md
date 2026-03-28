## ADDED Requirements

### Requirement: Pipeline builds with tee-split architecture
`CameraPipeline` SHALL construct a GStreamer pipeline from `v4l2src` with MJPEG caps (5120x3840, 55/2 fps), split via `tee` into a preview branch and a capture branch.

#### Scenario: Pipeline constructed for a valid device
- **WHEN** `CameraPipeline` is instantiated with a valid device path (e.g., `/dev/video0`)
- **THEN** a GStreamer pipeline is created with `v4l2src`, `tee`, preview branch (decode + scale to 720p), and capture branch (leaky queue + appsink)

#### Scenario: Pipeline uses platform-appropriate decoder
- **WHEN** the application starts on Jetson (nvv4l2decoder available in registry)
- **THEN** the preview branch uses `jpegparse ! nvv4l2decoder mjpeg=1 ! nvvidconv`
- **WHEN** the application starts on a non-Jetson platform
- **THEN** the preview branch uses `jpegdec ! videoconvert`

### Requirement: Pipeline lifecycle management
`CameraPipeline` SHALL provide methods to start and stop the pipeline, transitioning it to PLAYING and NULL states respectively.

#### Scenario: Start pipeline
- **WHEN** `start()` is called
- **THEN** the pipeline transitions to GST_STATE_PLAYING and the preview begins rendering

#### Scenario: Stop pipeline
- **WHEN** `stop()` is called
- **THEN** the pipeline transitions to GST_STATE_NULL and all resources are released

### Requirement: Capture branch is leaky and keeps only the latest frame
The capture branch SHALL use `queue leaky=downstream max-size-buffers=1` and `appsink drop=true max-buffers=1` to ensure only the most recent MJPEG frame is available and the capture branch never blocks the main pipeline.

#### Scenario: Frames flow without backpressure
- **WHEN** the pipeline is playing and no capture is requested
- **THEN** the capture branch continuously discards old frames, keeping only the latest one, and does not cause the preview branch to stall

### Requirement: Latest MJPEG sample is always cached
`CameraPipeline` SHALL continuously cache the latest `GstSample` from the capture appsink via the `new-sample` signal. The cached sample MUST be updated in a thread-safe manner.

#### Scenario: Sample is available after pipeline starts
- **WHEN** the pipeline has been playing for at least one frame interval
- **THEN** `CameraPipeline` holds a non-null reference to the latest MJPEG sample

### Requirement: GStreamer bus errors are reported
`CameraPipeline` SHALL monitor the GStreamer bus for error and EOS messages and expose pipeline state (playing, stopped, error) to callers.

#### Scenario: Pipeline error is surfaced
- **WHEN** GStreamer posts an error message on the bus
- **THEN** `CameraPipeline` updates its state to error and makes the error message accessible
