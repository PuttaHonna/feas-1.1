"""
Forensic Evidence Analysis System (FEAS) - Metadata & EXIF Extraction Pipeline
Extracts EXIF metadata and GPS coordinates using PIL and piexif with safe fallbacks.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from PIL import Image, ExifTags
import piexif


def _convert_to_degrees(value: Any) -> float:
    """Helper to convert GPS rational coordinates to decimal degrees."""
    try:
        if isinstance(value, (list, tuple)) and len(value) == 3:
            # Each item might be a tuple/ratio (numerator, denominator) or float
            d = value[0][0] / value[0][1] if isinstance(value[0], (list, tuple)) else float(value[0])
            m = value[1][0] / value[1][1] if isinstance(value[1], (list, tuple)) else float(value[1])
            s = value[2][0] / value[2][1] if isinstance(value[2], (list, tuple)) else float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        return float(value)
    except Exception:
        return 0.0


def extract_gps_coordinates(exif_dict: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Extract latitude and longitude in decimal degrees from EXIF GPS data."""
    try:
        gps_info = exif_dict.get("GPS", {})
        if not gps_info:
            return None
        
        # piexif GPS tags: 1 = LatRef, 2 = Latitude, 3 = LongRef, 4 = Longitude
        lat_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef, b"N")
        if isinstance(lat_ref, bytes):
            lat_ref = lat_ref.decode("latin1", errors="ignore")
        
        lat_val = gps_info.get(piexif.GPSIFD.GPSLatitude)
        
        long_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef, b"E")
        if isinstance(long_ref, bytes):
            long_ref = long_ref.decode("latin1", errors="ignore")
            
        long_val = gps_info.get(piexif.GPSIFD.GPSLongitude)
        
        if lat_val and long_val:
            lat = _convert_to_degrees(lat_val)
            if lat_ref.upper() == "S":
                lat = -lat
            
            lon = _convert_to_degrees(long_val)
            if long_ref.upper() == "W":
                lon = -lon
                
            return {"latitude": round(lat, 6), "longitude": round(lon, 6)}
    except Exception:
        pass
    return None


def extract_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract full EXIF metadata, camera specifications, and GPS information.
    Returns a standardized dictionary with clean fallback if metadata is missing.
    """
    path = Path(file_path)
    fallback: Dict[str, Any] = {
        "has_exif": False,
        "device_make": "Unknown",
        "device_model": "Unknown",
        "software": "Unknown",
        "datetime_original": None,
        "gps": None,
        "image_width": None,
        "image_height": None,
        "color_space": "Unknown",
        "raw_tags": {}
    }

    if not path.exists():
        return fallback

    # Handle images
    if path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".tiff"]:
        try:
            with Image.open(path) as img:
                fallback["image_width"] = img.width
                fallback["image_height"] = img.height
                fallback["color_space"] = img.mode

                # Try loading piexif
                raw_exif = img.info.get("exif")
                if raw_exif:
                    exif_dict = piexif.load(raw_exif)
                    fallback["has_exif"] = True
                    
                    # 0th IFD
                    zeroth = exif_dict.get("0th", {})
                    if piexif.ImageIFD.Make in zeroth:
                        val = zeroth[piexif.ImageIFD.Make]
                        fallback["device_make"] = val.decode("latin1", errors="ignore").strip("\x00") if isinstance(val, bytes) else str(val)
                    if piexif.ImageIFD.Model in zeroth:
                        val = zeroth[piexif.ImageIFD.Model]
                        fallback["device_model"] = val.decode("latin1", errors="ignore").strip("\x00") if isinstance(val, bytes) else str(val)
                    if piexif.ImageIFD.Software in zeroth:
                        val = zeroth[piexif.ImageIFD.Software]
                        fallback["software"] = val.decode("latin1", errors="ignore").strip("\x00") if isinstance(val, bytes) else str(val)

                    # Exif IFD
                    exif_sub = exif_dict.get("Exif", {})
                    if piexif.ExifIFD.DateTimeOriginal in exif_sub:
                        val = exif_sub[piexif.ExifIFD.DateTimeOriginal]
                        fallback["datetime_original"] = val.decode("latin1", errors="ignore").strip("\x00") if isinstance(val, bytes) else str(val)

                    # GPS IFD
                    gps_coords = extract_gps_coordinates(exif_dict)
                    if gps_coords:
                        fallback["gps"] = gps_coords

                    # Extract printable raw tags summary
                    printable_tags = {}
                    for ifd_name, ifd in exif_dict.items():
                        if isinstance(ifd, dict):
                            for tag, val in ifd.items():
                                if isinstance(val, bytes):
                                    printable_tags[f"{ifd_name}:{tag}"] = val.decode("latin1", errors="ignore")[:50]
                                elif isinstance(val, (int, float, str)):
                                    printable_tags[f"{ifd_name}:{tag}"] = val
                    fallback["raw_tags"] = printable_tags

        except Exception as e:
            fallback["error"] = str(e)

    return fallback
