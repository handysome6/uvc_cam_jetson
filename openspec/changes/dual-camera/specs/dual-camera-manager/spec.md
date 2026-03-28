## ADDED Requirements

### Requirement: DualCameraManager owns two CameraPipeline instances
`DualCameraManager` SHALL create and manage two `CameraPipeline` instances, one per camera device, identified as cam0 and cam1.

#### Scenario: Manager initialized with two devices
- **WHEN** `DualCameraManager` is constructed with two device paths
- **THEN** it creates two `CameraPipeline` instances, one for each device

#### Scenario: Manager initialized with one device
- **WHEN** `DualCameraManager` is constructed with only one device path
- **THEN** it creates one `CameraPipeline` instance for the available device and marks the other slot as absent

### Requirement: Unified start and stop lifecycle
`DualCameraManager` SHALL provide `start()` and `stop()` methods that manage both pipelines together.

#### Scenario: Start with two cameras
- **WHEN** `start()` is called with window handles for both cameras
- **THEN** both pipelines transition to PLAYING state and both previews begin rendering

#### Scenario: Start with one camera
- **WHEN** `start()` is called but only one camera is available
- **THEN** the available pipeline starts and the missing camera slot reports its absence without error

#### Scenario: Stop releases both pipelines
- **WHEN** `stop()` is called
- **THEN** both pipelines transition to NULL state and all resources are released

### Requirement: Simultaneous capture with shared timestamp
`DualCameraManager` SHALL provide a `capture(directory)` method that reads the latest cached frame from both pipelines at the same moment and saves them with a shared timestamp.

#### Scenario: Both cameras capture simultaneously
- **WHEN** `capture()` is called and both cameras have cached frames
- **THEN** two files are saved: `cam0_<timestamp>.jpg` and `cam1_<timestamp>.jpg` where `<timestamp>` is identical for both files

#### Scenario: Only one camera has a cached frame
- **WHEN** `capture()` is called but only one camera has a cached frame
- **THEN** the available frame is saved and the missing frame is reported (not an error that blocks the successful save)

### Requirement: Per-camera error and state signals
`DualCameraManager` SHALL expose per-camera state (playing, stopped, error) and forward error signals from each `CameraPipeline` with camera identity.

#### Scenario: Error on one camera
- **WHEN** one camera pipeline reports an error
- **THEN** `DualCameraManager` emits an error signal that includes the camera index (0 or 1) and the error message, and the other camera continues running
