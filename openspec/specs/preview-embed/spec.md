## ADDED Requirements

### Requirement: VideoOverlay embeds preview into Qt widget
The preview sink SHALL render video directly into a PySide6 `QWidget` via the `GstVideoOverlay` interface by calling `set_window_handle()` with the widget's native window ID.

#### Scenario: Preview renders inside the GUI window
- **WHEN** the pipeline is playing and VideoOverlay is used
- **THEN** the 720p preview video appears inside the designated Qt widget, not in a separate window

#### Scenario: Widget resize is handled
- **WHEN** the user resizes the application window
- **THEN** the video display adjusts to fill the preview widget area (via `expose()` or resize event handling)

### Requirement: Fallback to appsink-to-QImage display
If VideoOverlay embedding is not available or not functional, the system SHALL fall back to pulling decoded 720p frames from an appsink and displaying them as `QPixmap` in a `QLabel`.

#### Scenario: Fallback mode renders preview
- **WHEN** VideoOverlay is not supported (e.g., macOS dev environment)
- **THEN** the preview widget displays frames pulled from appsink, converted to QImage/QPixmap

### Requirement: Preview runs at camera frame rate without UI blocking
The preview display SHALL update at the camera's frame rate (up to 27.5 FPS) without blocking the Qt event loop.

#### Scenario: UI remains responsive during preview
- **WHEN** the preview is running at full frame rate
- **THEN** the capture button and window controls remain responsive to user input
