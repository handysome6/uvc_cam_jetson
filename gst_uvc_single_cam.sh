#!/usr/bin/env python3
"""Interactive single-camera launcher for Jetson UVC MJPEG preview."""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class CameraDevice:
    path: str
    label: str


@dataclass(frozen=True)
class CaptureMode:
    width: int
    height: int
    fps: Fraction

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def gst_framerate(self) -> str:
        limited = self.fps.limit_denominator(1000)
        return f"{limited.numerator}/{limited.denominator}"

    @property
    def display_fps(self) -> str:
        return f"{float(self.fps):.3f}"


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required command: {name}")


def run_checked(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            list(command),
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            sys.stderr.write(exc.stdout)
        if exc.stderr:
            sys.stderr.write(exc.stderr)
        raise SystemExit(exc.returncode or 1)

    return completed.stdout


def scan_camera_devices() -> List[CameraDevice]:
    output = run_checked(["v4l2-ctl", "--list-devices"])
    devices: List[CameraDevice] = []
    current_label = ""
    seen = set()

    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if not raw_line.startswith((" ", "\t")):
            current_label = stripped.rstrip(":")
            continue

        if re.fullmatch(r"/dev/video\d+", stripped) and stripped not in seen:
            devices.append(CameraDevice(path=stripped, label=current_label or "Unknown device"))
            seen.add(stripped)

    return devices


def select_camera_device(devices: Sequence[CameraDevice]) -> str:
    if not devices:
        fallback = Path("/dev/video0")
        if fallback.exists():
            print("No camera devices were listed by v4l2-ctl, falling back to /dev/video0.", file=sys.stderr)
            return str(fallback)
        raise SystemExit("No V4L2 camera devices found.")

    print("Available camera devices:")
    for index, device in enumerate(devices, start=1):
        print(f"  [{index}] {device.path} ({device.label})")

    if not sys.stdin.isatty():
        raise SystemExit("Interactive device selection requires a terminal. Pass a device path explicitly.")

    prompt = f"Select a device to stream [1-{len(devices)}] (default 1): "
    while True:
        selection = input(prompt).strip()
        if not selection:
            return devices[0].path
        if selection.isdigit():
            selected_index = int(selection)
            if 1 <= selected_index <= len(devices):
                return devices[selected_index - 1].path
        print(f"Invalid selection. Please enter a number between 1 and {len(devices)}.", file=sys.stderr)


def parse_fps(line: str) -> Optional[Fraction]:
    fps_match = re.search(r"\(([0-9.]+)\s+fps\)", line)
    if fps_match:
        return Fraction(fps_match.group(1))

    seconds_match = re.search(r"Interval:\s+\w+\s+([0-9.]+)s", line)
    if not seconds_match:
        return None

    seconds = Fraction(seconds_match.group(1))
    if seconds <= 0:
        return None

    return Fraction(1, 1) / seconds


def detect_best_mjpeg_mode(device: str) -> CaptureMode:
    output = run_checked(["v4l2-ctl", "-d", device, "--list-formats-ext"])
    in_mjpeg_section = False
    current_size = None
    best_mode: Optional[CaptureMode] = None

    for line in output.splitlines():
        if re.search(r"\[\d+\]:", line):
            in_mjpeg_section = "'MJPG'" in line or "'JPEG'" in line
            current_size = None
            continue

        if not in_mjpeg_section:
            continue

        discrete_match = re.search(r"Size:\s+Discrete\s+(\d+)x(\d+)", line)
        if discrete_match:
            current_size = (int(discrete_match.group(1)), int(discrete_match.group(2)))
            continue

        stepwise_match = re.search(r"Size:\s+Stepwise\s+\d+x\d+\s*-\s*(\d+)x(\d+)", line)
        if stepwise_match:
            current_size = (int(stepwise_match.group(1)), int(stepwise_match.group(2)))
            continue

        if current_size is None or "Interval:" not in line:
            continue

        fps = parse_fps(line)
        if fps is None:
            continue

        candidate = CaptureMode(width=current_size[0], height=current_size[1], fps=fps)
        if best_mode is None:
            best_mode = candidate
            continue

        if candidate.area > best_mode.area or (candidate.area == best_mode.area and candidate.fps > best_mode.fps):
            best_mode = candidate

    if best_mode is None:
        raise SystemExit(f"No MJPEG mode found for {device}")

    return best_mode


def build_gstreamer_command(device: str, mode: CaptureMode) -> List[str]:
    return [
        "gst-launch-1.0",
        "-v",
        "v4l2src",
        f"device={device}",
        "!",
        f"image/jpeg,width={mode.width},height={mode.height},framerate={mode.gst_framerate}",
        "!",
        "jpegparse",
        "!",
        "nvv4l2decoder",
        "mjpeg=1",
        "!",
        "nvvidconv",
        "!",
        "video/x-raw(memory:NVMM),width=1280,height=720,format=NV12",
        "!",
        "nveglglessink",
        "sync=false",
    ]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select a V4L2 camera, detect its best MJPEG mode, and launch a Jetson preview pipeline.",
    )
    parser.add_argument(
        "device",
        nargs="?",
        help="V4L2 device path to use directly, for example /dev/video0.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv[1:])

    require_command("python3")
    require_command("v4l2-ctl")
    require_command("gst-launch-1.0")

    if args.device:
        device = args.device
    else:
        device = select_camera_device(scan_camera_devices())

    if not Path(device).exists():
        raise SystemExit(f"V4L2 device not found: {device}")

    mode = detect_best_mjpeg_mode(device)
    command = build_gstreamer_command(device, mode)

    print(f"Using device: {device}", flush=True)
    print(
        f"Detected MJPEG mode: {mode.width}x{mode.height} @ {mode.gst_framerate} fps ({mode.display_fps} fps)",
        flush=True,
    )
    print(f"Launching: {shlex.join(command)}", flush=True)

    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except KeyboardInterrupt:
        raise SystemExit(130)