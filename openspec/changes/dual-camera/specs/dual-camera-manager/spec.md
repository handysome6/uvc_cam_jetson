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

### Requirement: Simultaneous capture with shared timestamp and position-based naming
`DualCameraManager` SHALL provide a `capture(directory)` method that reads the latest cached frame from both pipelines at the same moment and saves them with a shared timestamp. Files are named based on canvas position: `A_{timestamp}.jpg` for left canvas, `D_{timestamp}.jpg` for right canvas.

#### Scenario: Both cameras capture simultaneously
- **WHEN** `capture()` is called and both cameras have cached frames
- **THEN** two files are saved: `A_<timestamp>.jpg` and `D_<timestamp>.jpg` where `<timestamp>` is identical for both files, and the prefixes correspond to the current left/right canvas positions

#### Scenario: Only one camera has a cached frame
- **WHEN** `capture()` is called but only one camera has a cached frame
- **THEN** the available frame is saved with the appropriate prefix (A or D based on its canvas position) and the missing frame is reported (not an error that blocks the successful save)

### Requirement: Per-camera error and state signals
`DualCameraManager` SHALL expose per-camera state (playing, stopped, error) and forward error signals from each `CameraPipeline` with camera identity.

#### Scenario: Error on one camera
- **WHEN** one camera pipeline reports an error
- **THEN** `DualCameraManager` emits an error signal that includes the camera index (0 or 1) and the error message, and the other camera continues running

### Requirement: Camera swap functionality
`DualCameraManager` SHALL provide a `swap_cameras()` method that swaps the left/right canvas positions. The left canvas (position 0) always corresponds to the "A" camera and the right canvas (position 1) always corresponds to the "D" camera.

#### Scenario: User swaps camera positions
- **WHEN** `swap_cameras()` is called while both cameras are running
- **THEN** the camera-to-canvas mapping is reversed, and a `cameras_swapped` signal is emitted to notify the GUI to rebind window handles

#### Scenario: Capture after swap
- **WHEN** cameras are swapped and then `capture()` is called
- **THEN** the camera currently on the left canvas is saved as `A_<timestamp>.jpg` and the camera on the right canvas is saved as `D_<timestamp>.jpg`

#### Scenario: Swap with one camera
- **WHEN** `swap_cameras()` is called but only one camera is connected
- **THEN** the mapping is updated and the single camera moves to the opposite canvas position
