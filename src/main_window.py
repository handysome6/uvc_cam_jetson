"""
MainWindow — dual-camera preview + capture UI.

Layout:
  ┌──────────────────┬──────────────────┐
  │   Camera 0       │   Camera 1       │
  │   (720p preview) │   (720p preview) │
  ├──────────────────┴──────────────────┤
  │  [Capture]   Status: ...            │
  └─────────────────────────────────────┘

Capture files land in ~/captures/cam{N}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg
"""

import os

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from camera_pipeline import CameraPipeline
from dual_camera_manager import DualCameraManager

CAPTURE_DIR = os.path.expanduser("~/captures")


# ---------------------------------------------------------------------------
# PreviewWidget — native container for VideoOverlay rendering
# ---------------------------------------------------------------------------

class _PreviewWidget(QWidget):
    """
    Opaque native widget into which nveglglessink renders via VideoOverlay.

    WA_NativeWindow  — ensures the widget has its own OS window handle (winId)
    WA_PaintOnScreen — tells Qt not to manage painting (GStreamer owns the surface)
    paintEngine()    — returning None is required when WA_PaintOnScreen is set
    """

    def __init__(self, pipeline: CameraPipeline, parent=None):
        super().__init__(parent)
        self._pipeline = pipeline
        self.setAttribute(Qt.WA_NativeWindow)
        self.setAttribute(Qt.WA_PaintOnScreen)
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: black;")

    def paintEngine(self):
        # Required when WA_PaintOnScreen is set; GStreamer manages rendering
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._pipeline.expose()


# ---------------------------------------------------------------------------
# Placeholder for missing camera
# ---------------------------------------------------------------------------

def _make_placeholder(text: str = "Camera not connected") -> QLabel:
    label = QLabel(text)
    label.setAlignment(Qt.AlignCenter)
    label.setMinimumSize(640, 360)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    label.setStyleSheet("background: black; color: #888; font-size: 16px;")
    return label


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(
        self,
        manager: DualCameraManager,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("UVC Camera — Dual Camera")
        self._manager = manager
        self._manager.camera_error.connect(self._on_camera_error)
        self._manager.camera_eos.connect(self._on_camera_eos)

        os.makedirs(CAPTURE_DIR, exist_ok=True)

        # Preview widgets: one per camera slot (may be _PreviewWidget or QLabel)
        self._previews: list[QWidget] = [None, None]
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Preview area — two panels side by side
        preview_row = QWidget()
        preview_layout = QHBoxLayout(preview_row)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(6)

        for i in range(2):
            pipe = self._manager.pipeline(i)
            if pipe is not None:
                if self._manager.use_overlay:
                    widget = _PreviewWidget(pipe)
                else:
                    widget = QLabel(f"Cam {i}: waiting…")
                    widget.setAlignment(Qt.AlignCenter)
                    widget.setMinimumSize(640, 360)
                    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    widget.setStyleSheet("background: black; color: #888;")
                    pipe.preview_frame.connect(
                        lambda img, lbl=widget: self._on_preview_frame(lbl, img)
                    )
            else:
                widget = _make_placeholder()
            self._previews[i] = widget
            preview_layout.addWidget(widget, stretch=1)

        root.addWidget(preview_row, stretch=1)

        # Controls row
        bar = QWidget()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(8)

        self._capture_btn = QPushButton("Capture")
        self._capture_btn.setMinimumHeight(36)
        self._capture_btn.setMinimumWidth(100)
        self._capture_btn.clicked.connect(self._on_capture)

        self._status = QLabel("Starting pipelines…")
        self._status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        bar_layout.addWidget(self._capture_btn)
        bar_layout.addWidget(self._status, stretch=1)
        root.addWidget(bar)

        self.resize(1310, 810)

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        handles: list[int | None] = [None, None]
        for i in range(2):
            pipe = self._manager.pipeline(i)
            if pipe is not None and self._manager.use_overlay:
                handles[i] = int(self._previews[i].winId())

        logger.info("Window shown — starting pipelines (overlay={})", self._manager.use_overlay)
        results = self._manager.start(handles)

        started = sum(1 for r in results if r)
        if started > 0:
            self._status.setText(
                f"{started} camera(s) running — captures → {CAPTURE_DIR}"
            )
            logger.success("{} pipeline(s) running | captures → {}", started, CAPTURE_DIR)
        else:
            logger.error("No pipelines started")
            self._status.setText("Error: no cameras started")

    def closeEvent(self, event):
        logger.info("Window closing — stopping pipelines")
        self._manager.stop()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Capture button
    # ------------------------------------------------------------------

    @Slot()
    def _on_capture(self):
        logger.info("Capture triggered")
        paths = self._manager.capture(CAPTURE_DIR)

        saved = [p for p in paths if p is not None]
        if saved:
            names = [os.path.basename(p) for p in saved]
            self._status.setText(f"Saved: {', '.join(names)}")
            self._capture_btn.setEnabled(False)
            self._capture_btn.setText("Saved!")
            QTimer.singleShot(800, self._reset_capture_btn)
        else:
            logger.warning("Capture failed: no frames cached yet")
            self._status.setText("No frames cached yet — try again in a moment")

    @Slot()
    def _reset_capture_btn(self):
        self._capture_btn.setText("Capture")
        self._capture_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Preview frame handler — appsink fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _on_preview_frame(label: QLabel, image: QImage):
        pixmap = QPixmap.fromImage(image)
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------
    # Error / EOS feedback
    # ------------------------------------------------------------------

    @Slot(int, str)
    def _on_camera_error(self, cam_idx: int, msg: str):
        logger.error("Camera {} error: {}", cam_idx, msg)
        self._status.setText(f"Cam {cam_idx} error: {msg}")
        widget = self._previews[cam_idx]
        if isinstance(widget, QLabel):
            widget.setText(f"Camera {cam_idx} error:\n{msg}")

    @Slot(int)
    def _on_camera_eos(self, cam_idx: int):
        logger.warning("Camera {} EOS", cam_idx)
        self._status.setText(f"Cam {cam_idx}: stream ended (EOS)")
