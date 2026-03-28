## ADDED Requirements

### Requirement: Main window displays a single preview panel
The `MainWindow` SHALL contain a widget area that displays the live camera preview from the `CameraPipeline`.

#### Scenario: Preview is visible on launch
- **WHEN** the application starts and the camera is connected
- **THEN** the main window shows a live 720p preview of the camera feed

### Requirement: Capture button triggers frame save
The `MainWindow` SHALL have a capture button that, when clicked, calls `CameraPipeline.capture_to_file()` to save the latest MJPEG frame.

#### Scenario: User clicks capture
- **WHEN** the user clicks the capture button
- **THEN** the latest cached MJPEG frame is saved to disk as a `.jpg` file and the user receives visual feedback (e.g., button text change or status message)

### Requirement: Application starts and stops pipeline with window lifecycle
The pipeline SHALL start when the window is shown and stop when the window is closed.

#### Scenario: Pipeline stops on window close
- **WHEN** the user closes the application window
- **THEN** the GStreamer pipeline is stopped and all resources are released cleanly

### Requirement: Basic error feedback
If the camera is not connected or the pipeline fails, the `MainWindow` SHALL display an error message in the preview area or via a dialog.

#### Scenario: No camera connected
- **WHEN** the application starts and no camera is found at the configured device path
- **THEN** the preview area shows an error message (e.g., "Camera not found") instead of a blank widget
