"""
MainWindow — single-camera preview + capture UI.

Layout:
  ┌─────────────────────────────────────────────┐
  │  Preview widget (VideoOverlay or QLabel)     │
  │  1280 × 720  (expandable)                   │
  ├─────────────────────────────────────────────┤
  │  [Capture]   Status: ...                    │
  └─────────────────────────────────────────────┘

Capture files land in ~/captures/capture_YYYYMMDD_HHMMSS_mmm.jpg
"""

import os
from datetime import datetime

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
        self.setMinimumSize(1280, 720)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: black;")

    def paintEngine(self):
        # Required when WA_PaintOnScreen is set; GStreamer manages rendering
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Tell the sink to repaint to the new size (task 3.3)
        self._pipeline.expose()


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(
        self,
        device: str = "/dev/video0",
        use_overlay: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("UVC Camera — Single Camera PoC")

        self._pipeline = CameraPipeline(
            device=device,
            use_overlay=use_overlay,
            parent=self,
        )
        self._pipeline.pipeline_error.connect(self._on_pipeline_error)
        self._pipeline.pipeline_eos.connect(self._on_pipeline_eos)

        os.makedirs(CAPTURE_DIR, exist_ok=True)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction (task 5.1)
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Preview area ------------------------------------------------
        if self._pipeline.use_overlay:
            self._preview = _PreviewWidget(self._pipeline)
        else:
            # appsink fallback: decoded frames arrive as QImage via signal
            self._preview = QLabel("Waiting for camera…")
            self._preview.setAlignment(Qt.AlignCenter)
            self._preview.setMinimumSize(1280, 720)
            self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._preview.setStyleSheet("background: black; color: #888;")
            self._pipeline.preview_frame.connect(self._on_preview_frame)

        root.addWidget(self._preview, stretch=1)

        # Controls row ------------------------------------------------
        bar = QWidget()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(8)

        self._capture_btn = QPushButton("Capture")
        self._capture_btn.setMinimumHeight(36)
        self._capture_btn.setMinimumWidth(100)
        self._capture_btn.clicked.connect(self._on_capture)

        self._status = QLabel("Starting pipeline…")
        self._status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        bar_layout.addWidget(self._capture_btn)
        bar_layout.addWidget(self._status, stretch=1)
        root.addWidget(bar)

        self.resize(1310, 810)

    # ------------------------------------------------------------------
    # Window lifecycle (task 5.3)
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        # Give Qt a chance to create the native window before we hand winId
        # to GStreamer; processEvents() ensures WA_NativeWindow is realised.
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        handle = None
        if self._pipeline.use_overlay:
            handle = int(self._preview.winId())

        logger.info("Window shown — starting pipeline (overlay={})", self._pipeline.use_overlay)
        ok = self._pipeline.start(window_handle=handle)
        if ok:
            self._status.setText(f"Camera running — captures → {CAPTURE_DIR}")
            logger.success("Pipeline running | captures → {}", CAPTURE_DIR)
        else:
            msg = self._pipeline.error_message or "Unknown error"
            logger.error("Pipeline failed to start: {}", msg)
            self._show_error(msg)

    def closeEvent(self, event):
        logger.info("Window closing — stopping pipeline")
        self._pipeline.stop()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Capture button (task 5.2)
    # ------------------------------------------------------------------

    @Slot()
    def _on_capture(self):
        filename = _generate_filename()
        path = os.path.join(CAPTURE_DIR, filename)
        logger.info("Capture triggered → {}", path)
        ok = self._pipeline.capture_to_file(path)
        if ok:
            self._status.setText(f"Saved: {filename}")
            self._capture_btn.setEnabled(False)
            self._capture_btn.setText("Saved!")
            QTimer.singleShot(800, self._reset_capture_btn)
        else:
            logger.warning("Capture failed: no frame cached yet")
            self._status.setText("No frame cached yet — try again in a moment")

    @Slot()
    def _reset_capture_btn(self):
        self._capture_btn.setText("Capture")
        self._capture_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Preview frame handler — appsink fallback (task 3.2 / 5.1)
    # ------------------------------------------------------------------

    @Slot(QImage)
    def _on_preview_frame(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        self._preview.setPixmap(
            pixmap.scaled(
                self._preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------
    # Error / EOS feedback (task 5.4)
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_pipeline_error(self, msg: str):
        logger.error("Pipeline error: {}", msg)
        self._show_error(msg)

    @Slot()
    def _on_pipeline_eos(self):
        logger.warning("Pipeline EOS received")
        self._status.setText("Stream ended (EOS)")

    def _show_error(self, msg: str):
        self._status.setText(f"Error: {msg}")
        if isinstance(self._preview, QLabel):
            self._preview.setText(f"Camera error:\n{msg}")


# ---------------------------------------------------------------------------
# Filename generation (task 4.3)
# ---------------------------------------------------------------------------

def _generate_filename() -> str:
    """Return a unique timestamped filename with millisecond precision."""
    now = datetime.now()
    ms = now.microsecond // 1000
    return now.strftime("capture_%Y%m%d_%H%M%S_") + f"{ms:03d}.jpg"
