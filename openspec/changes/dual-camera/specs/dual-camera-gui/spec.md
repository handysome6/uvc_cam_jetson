## ADDED Requirements

### Requirement: Two side-by-side preview panels
`MainWindow` SHALL display two preview panels in a horizontal layout, one for each camera (cam0 on the left, cam1 on the right).

#### Scenario: Both cameras connected
- **WHEN** both cameras are detected and pipelines start
- **THEN** the window shows two live 720p previews side by side

#### Scenario: One camera missing
- **WHEN** only one camera is detected
- **THEN** the connected camera shows a live preview and the missing camera panel shows a "Camera not connected" message

### Requirement: Single capture button triggers both cameras
The `MainWindow` SHALL have one capture button that triggers `DualCameraManager.capture()`, saving frames from both cameras simultaneously.

#### Scenario: User clicks capture with both cameras running
- **WHEN** the user clicks the capture button and both cameras have cached frames
- **THEN** both frames are saved and the status message confirms both files

#### Scenario: User clicks capture with one camera running
- **WHEN** the user clicks the capture button but only one camera is running
- **THEN** the available frame is saved and the status message indicates which camera was captured

### Requirement: MainWindow uses DualCameraManager instead of CameraPipeline
`MainWindow` SHALL interact with `DualCameraManager` for all pipeline operations (start, stop, capture) rather than managing `CameraPipeline` instances directly.

#### Scenario: Window lifecycle drives manager
- **WHEN** the window is shown
- **THEN** `DualCameraManager.start()` is called with both preview widget handles
- **WHEN** the window is closed
- **THEN** `DualCameraManager.stop()` is called

### Requirement: Per-camera error feedback
If a camera pipeline fails, the corresponding preview panel SHALL display an error message while the other camera continues operating.

#### Scenario: One camera errors during operation
- **WHEN** cam1 pipeline reports an error while cam0 is running
- **THEN** the cam1 preview panel shows the error message and cam0 continues previewing normally
