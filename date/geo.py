"""Location helpers. Stored coordinates are snapped to a ~1 km grid, and other
users only ever see a coarse distance label, never coordinates."""
import math

DISTANCE_BUCKETS_KM = (2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200)


def validate_coordinates(latitude, longitude):
    """Return (lat, lon) as floats, or raise ValueError."""
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Latitude and longitude must be numbers.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):  # NaN and inf fail this too
        raise ValueError("That location is outside the valid range.")
    return lat, lon


def snap(latitude, longitude, step=0.01):
    """Round to a ~1 km grid so an exact position is never stored."""
    return round(round(latitude / step) * step, 6), round(round(longitude / step) * step, 6)


def haversine_km(lat1, lon1, lat2, lon2):
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371 * math.asin(min(1.0, math.sqrt(a)))


def distance_label(distance_km):
    """Coarse text such as "Less than 10 km away" (None if unknown)."""
    if distance_km is None:
        return None
    for limit in DISTANCE_BUCKETS_KM:
        if distance_km < limit:
            return f"Less than {limit} km away"
    return f"More than {DISTANCE_BUCKETS_KM[-1]} km away"
