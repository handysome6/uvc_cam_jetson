"""
Entry point for the UVC camera preview/capture application.

Usage:
    python main.py [--device auto|/dev/videoX] [--no-overlay]

Flags:
    --device PATH      Camera device path, or 'auto' to detect (default: auto)
    --no-overlay       Force appsink-to-QImage fallback (skips VideoOverlay)
"""

import signal
import sys
import argparse

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst
from loguru import logger

from PySide6.QtWidgets import QApplication

from camera_pipeline import find_uvc_camera, is_jetson
from main_window import MainWindow


def _setup_signals(app: QApplication) -> None:
    """Route SIGINT/SIGTERM through Qt's event loop so closeEvent runs cleanly."""
    def _handler(signum, _frame):
        logger.info("Signal {} received — quitting", signal.Signals(signum).name)
        app.quit()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main():
    Gst.init(None)
    logger.info("GStreamer initialized")

    parser = argparse.ArgumentParser(description="UVC camera preview/capture")
    parser.add_argument(
        "--device",
        default="auto",
        help="Camera device path, or 'auto' to detect (default: auto)",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Force appsink-to-QImage preview instead of VideoOverlay",
    )
    args = parser.parse_args()

    # Resolve device path
    if args.device == "auto":
        device = find_uvc_camera()
        if device is None:
            logger.error(
                "No UVC camera found. Connect a camera or use --device /dev/videoX"
            )
            sys.exit(1)
        logger.info("Auto-detected camera: {}", device)
    else:
        device = args.device

    # VideoOverlay is the preferred path on Jetson; on dev machines fall back
    use_overlay = is_jetson() and not args.no_overlay
    logger.info(
        "Config | device={} preview={}",
        device,
        "VideoOverlay" if use_overlay else "appsink fallback",
    )

    app = QApplication(sys.argv)
    _setup_signals(app)

    logger.info("Launching MainWindow")
    window = MainWindow(device=device, use_overlay=use_overlay)

    # Safety net: also stop pipeline on any quit path that bypasses closeEvent
    app.aboutToQuit.connect(window._pipeline.stop)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
