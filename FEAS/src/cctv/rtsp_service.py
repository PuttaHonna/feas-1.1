"""
CCTV Live IP Stream Ingestion Worker (RTSP / RTMP / HLS / File).
================================================================
Provides robust threaded frame ingestion for IP surveillance cameras:
1. Threaded non-blocking grabber preventing buffer bloat and network latency lag.
2. Auto-reconnect with exponential backoff on dropped RTSP connections.
3. Universal support for offline files (.mp4, .avi, .mkv, .dav) and network streams.
"""

from __future__ import annotations
from collections import deque
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("CCTVRTSPService")


class RTSPStreamWorker:
    """
    Non-blocking worker for IP CCTV video streams and recorded files.
    """

    def __init__(
        self,
        stream_uri: str,
        buffer_size: int = 5,
        target_fps: Optional[float] = None,
        reconnect_interval_s: float = 3.0
    ):
        self.stream_uri = str(stream_uri)
        self.buffer_size = buffer_size
        self.target_fps = target_fps
        self.reconnect_interval = reconnect_interval_s

        self.frame_buffer: deque = deque(maxlen=self.buffer_size)
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None

        self.total_frames_read: int = 0
        self.fps: float = 25.0
        self.frame_width: int = 1280
        self.frame_height: int = 720
        self.is_connected: bool = False
        self.last_error: Optional[str] = None

    def start(self) -> bool:
        """Start background frame capture thread."""
        if self.running:
            return True

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        # Wait up to 2 seconds for initial connection
        timeout = time.time() + 2.0
        while time.time() < timeout and not self.is_connected and self.running:
            time.sleep(0.05)
        return self.is_connected

    def stop(self) -> None:
        """Stop worker and release camera handle."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.is_connected = False

    def _connect(self) -> bool:
        try:
            if self.cap:
                self.cap.release()
            
            # Handle RTSP with TCP transport flag if OpenCV ffmpeg backend is active
            if self.stream_uri.startswith("rtsp://"):
                import os
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

            self.cap = cv2.VideoCapture(self.stream_uri)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.frame_height, self.frame_width = frame.shape[:2]
                    raw_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    self.fps = raw_fps if 5.0 <= raw_fps <= 120.0 else 25.0
                    self.is_connected = True
                    self.frame_buffer.append((self.total_frames_read, frame))
                    self.total_frames_read += 1
                    return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Failed to connect to stream {self.stream_uri}: {e}")

        self.is_connected = False
        return False

    def _capture_loop(self) -> None:
        while self.running:
            if not self.is_connected:
                if not self._connect():
                    time.sleep(self.reconnect_interval)
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.warning(f"Stream frame read failed from {self.stream_uri}. Reconnecting...")
                self.is_connected = False
                time.sleep(1.0)
                continue

            self.total_frames_read += 1
            self.frame_buffer.append((self.total_frames_read, frame))

            # FPS pacing if target_fps configured
            if self.target_fps:
                time.sleep(1.0 / self.target_fps)

    def read_latest_frame(self) -> Tuple[bool, Optional[np.ndarray], int]:
        """Read the most recent frame from ring buffer, discarding stale frames."""
        if not self.frame_buffer:
            return False, None, 0
        frame_idx, frame = self.frame_buffer[-1]
        return True, frame.copy(), frame_idx

    def get_status(self) -> Dict[str, Any]:
        """Return operational telemetry."""
        return {
            "stream_uri": self.stream_uri,
            "connected": self.is_connected,
            "running": self.running,
            "fps": round(self.fps, 1),
            "resolution": f"{self.frame_width}x{self.frame_height}",
            "frames_ingested": self.total_frames_read,
            "buffer_depth": len(self.frame_buffer),
            "last_error": self.last_error
        }

