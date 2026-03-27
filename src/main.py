"""
Entry point for the UVC camera preview/capture application.

Usage:
    python main.py [--device /dev/video0] [--no-overlay]

Flags:
    --device PATH      Camera device path (default: /dev/video0)
    --no-overlay       Force appsink-to-QImage fallback (skips VideoOverlay)
"""

import sys
import argparse

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst
from loguru import logger

from PySide6.QtWidgets import QApplication

from camera_pipeline import is_jetson
from main_window import MainWindow


def main():
    Gst.init(None)
    logger.info("GStreamer initialized")

    parser = argparse.ArgumentParser(description="UVC dual-camera preview/capture")
    parser.add_argument("--device", default="/dev/video0", help="Camera device path")
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Force appsink-to-QImage preview instead of VideoOverlay",
    )
    args = parser.parse_args()

    # VideoOverlay is the preferred path on Jetson; on dev machines fall back
    use_overlay = is_jetson() and not args.no_overlay
    logger.info(
        "Config | device={} preview={}",
        args.device,
        "VideoOverlay" if use_overlay else "appsink fallback",
    )

    app = QApplication(sys.argv)
    logger.info("Launching MainWindow")
    window = MainWindow(device=args.device, use_overlay=use_overlay)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
