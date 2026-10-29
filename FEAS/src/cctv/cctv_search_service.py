"""
CCTV Multi-Modal Temporal Search & Forensic Attribute Query Engine.
===================================================================
Enables flexible cross-attribute queries over indexed surveillance tracks and events:
1. Natural search query parser (e.g. "red car after 20:00", "person in zone A").
2. Dominant bounding-box color extraction via HSV color quantization.
3. High-throughput filtering by class, color, time interval, and event triggers.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import cv2
import numpy as np


COLOR_DEFINITIONS: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
    # HSV ranges: (H: 0-180, S: 0-255, V: 0-255)
    "red": ((0, 70, 50), (10, 255, 255)),
    "red_alt": ((170, 70, 50), (180, 255, 255)),
    "blue": ((100, 70, 50), (130, 255, 255)),
    "green": ((35, 70, 50), (85, 255, 255)),
    "yellow": ((20, 70, 70), (35, 255, 255)),
    "white": ((0, 0, 180), (180, 40, 255)),
    "black": ((0, 0, 0), (180, 255, 50)),
    "gray": ((0, 0, 51), (180, 40, 179)),
    "silver": ((0, 0, 140), (180, 35, 215))
}


def extract_dominant_color(crop_bgr: np.ndarray) -> str:
    """Extract dominant semantic color from a cropped bounding box."""
    if crop_bgr is None or crop_bgr.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    total_pixels = hsv.shape[0] * hsv.shape[1]
    if total_pixels == 0:
        return "unknown"

    color_scores: Dict[str, int] = {}
    for color_name, (lower, upper) in COLOR_DEFINITIONS.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        cnt = cv2.countNonZero(mask)
        clean_name = "red" if color_name.startswith("red") else color_name
        color_scores[clean_name] = color_scores.get(clean_name, 0) + cnt

    best_color, best_cnt = max(color_scores.items(), key=lambda item: item[1])
    if best_cnt / total_pixels > 0.15:
        return best_color
    return "unclassified"


@dataclass
class SearchQuery:
    """Structured search query parameter model."""
    raw_query: Optional[str] = None
    target_class: Optional[str] = None
    color: Optional[str] = None
    zone_name: Optional[str] = None
    min_timestamp_s: Optional[float] = None
    max_timestamp_s: Optional[float] = None
    event_type: Optional[str] = None


class CCTVSearchEngine:
    """
    In-memory and indexed search engine for forensic surveillance telemetry.
    """

    def __init__(self, tracks: Optional[List[Dict[str, Any]]] = None, events: Optional[List[Dict[str, Any]]] = None):
        self.tracks = tracks or []
        self.events = events or []

    @staticmethod
    def parse_natural_query(query_text: str) -> SearchQuery:
        """Parse natural language search string into structured search filters."""
        q = query_text.lower().strip()
        parsed = SearchQuery(raw_query=query_text)

        # Detect classes
        known_classes = ["person", "car", "motorcycle", "bicycle", "bus", "truck", "backpack", "auto", "vehicle"]
        for cls in known_classes:
            if cls in q:
                parsed.target_class = cls
                break

        # Detect colors
        known_colors = ["red", "blue", "green", "white", "black", "yellow", "silver", "gray"]
        for col in known_colors:
            if col in q:
                parsed.color = col
                break

        # Detect events
        if "loiter" in q:
            parsed.event_type = "LOITERING"
        elif "intrud" in q or "breach" in q:
            parsed.event_type = "INTRUSION"
        elif "cross" in q or "tripwire" in q:
            parsed.event_type = "TRIPWIRE_CROSSING"
        elif "abandon" in q or "unattended" in q:
            parsed.event_type = "UNATTENDED_BAGGAGE"
        elif "collision" in q or "crash" in q:
            parsed.event_type = "COLLISION"

        # Detect time constraints like 'after 20:00' or 'before 10s'
        time_match = re.search(r'after\s+(\d+(?:\.\d+)?)\s*s?', q)
        if time_match:
            parsed.min_timestamp_s = float(time_match.group(1))

        time_before = re.search(r'before\s+(\d+(?:\.\d+)?)\s*s?', q)
        if time_before:
            parsed.max_timestamp_s = float(time_before.group(1))

        return parsed

    def search_tracks(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Filter tracks by multi-modal constraints."""
        results = []
        for trk in self.tracks:
            # Class filter
            if query.target_class:
                trk_cls = trk.get("class", "").lower()
                if query.target_class == "vehicle":
                    if trk_cls not in {"car", "truck", "bus", "motorcycle", "auto"}:
                        continue
                elif query.target_class not in trk_cls:
                    continue

            # Color filter
            if query.color:
                trk_color = trk.get("dominant_color", trk.get("color", "")).lower()
                if query.color != trk_color:
                    continue

            # Time bounds
            first_s = float(str(trk.get("first_seen_timestamp", "0")).replace("s", ""))
            last_s = float(str(trk.get("last_seen_timestamp", "999999")).replace("s", ""))

            if query.min_timestamp_s is not None and last_s < query.min_timestamp_s:
                continue
            if query.max_timestamp_s is not None and first_s > query.max_timestamp_s:
                continue

            results.append(trk)
        return results

    def search_events(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """Filter events by type, target class, and time bounds."""
        results = []
        for evt in self.events:
            evt_type = evt.get("event_type", evt.get("type", "")).upper()
            if query.event_type and query.event_type not in evt_type:
                continue

            ts = float(evt.get("timestamp_seconds", evt.get("timestamp", 0.0)))
            if query.min_timestamp_s is not None and ts < query.min_timestamp_s:
                continue
            if query.max_timestamp_s is not None and ts > query.max_timestamp_s:
                continue

            results.append(evt)
        return results

