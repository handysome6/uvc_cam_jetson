## ADDED Requirements

### Requirement: Multi-device UVC discovery
The system SHALL provide a `find_uvc_cameras()` function that returns a list of all USB UVC capture device paths, ordered by device number.

#### Scenario: Two UVC cameras connected
- **WHEN** two USB UVC cameras are connected
- **THEN** `find_uvc_cameras()` returns a list of two device paths (e.g., `["/dev/video0", "/dev/video2"]`)

#### Scenario: One UVC camera connected
- **WHEN** one USB UVC camera is connected
- **THEN** `find_uvc_cameras()` returns a list with one device path

#### Scenario: No UVC cameras connected
- **WHEN** no USB UVC cameras are connected
- **THEN** `find_uvc_cameras()` returns an empty list
