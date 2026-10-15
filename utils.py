import os
import re

def parse_time_str(s):
    s = s.strip()
    if ":" not in s and s.isdigit():
        if len(s) == 6:
            s = f"{s[:2]}:{s[2:4]}:{s[4:]}"
        elif len(s) == 4:
            s = f"00:{s[:2]}:{s[2:]}"
        elif len(s) == 5:
            s = f"0{s[0]}:{s[1:3]}:{s[3:]}"
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            h, m, sec = 0, int(parts[0]), int(parts[1])
        else:
            return None, None
    except ValueError:
        return None, None
    if h < 0 or not (0 <= m < 60) or not (0 <= sec < 60):
        return None, None
    total = h * 3600 + m * 60 + sec
    h_out, rem = divmod(total, 3600)
    m_out, s_out = divmod(rem, 60)
    hms = (
        f"{h_out:02d}:{m_out:02d}:{s_out:02d}"
        if h_out
        else f"{m_out:02d}:{s_out:02d}"
    )
    return total, hms


def calc_pace(course_name, sec, distance_km=None):
    km = parse_km(course_name, distance_km)
    if km > 0:
        p = sec / km
        return f"{int(p // 60)}'{int(p % 60):02d}\"/km"
    return "-"


def parse_km(course_name, distance_km=None):
    if distance_km is not None and distance_km > 0:
        return float(distance_km)
    m = re.search(r"(\d+(?:\.\d+)?)\s*km", course_name, re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def get_mime(filename):
    ext = os.path.splitext(filename)[1].lower().strip(".")
    if ext in ["jpg", "jpeg"]:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "jxl":
        return "image/jxl"
    if ext in ["mp4", "mov"]:
        return "video/mp4"
    if ext == "avi":
        return "video/x-msvideo"
    if ext == "mkv":
        return "video/x-matroska"
    if ext in ["cr2", "nef", "arw", "dng", "raw"]:
        return "image/x-adobe-dng"
    return "application/octet-stream"