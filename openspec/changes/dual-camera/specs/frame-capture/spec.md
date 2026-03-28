## MODIFIED Requirements

### Requirement: Capture file naming includes timestamp
Each captured file SHALL be named with a camera identity prefix and a timestamp to prevent overwrites and allow chronological ordering. The format SHALL be `cam{N}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg` where `N` is the camera index (0 or 1).

#### Scenario: Files are uniquely named per camera
- **WHEN** a simultaneous capture is triggered for both cameras
- **THEN** two files are created: `cam0_<timestamp>.jpg` and `cam1_<timestamp>.jpg` with identical timestamps

#### Scenario: Multiple captures are uniquely named
- **WHEN** multiple captures are triggered within the same second
- **THEN** each pair of files has a unique timestamp (using millisecond precision)
