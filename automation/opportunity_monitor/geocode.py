"""Geography hard filter: is a posting's location within Evan's real
commute radius, or remote/hybrid?"""

from geopy.distance import geodesic
from geopy.geocoders import Nominatim

from automation.opportunity_monitor import config

_geolocator = Nominatim(user_agent="job-hunt-automation-efparnell")


def _geocode(location_text: str) -> tuple[float, float] | None:
    """Look up a free-text location string. Returns None if it can't
    be geocoded (e.g. vague text like 'United States; remote')."""
    result = _geolocator.geocode(location_text, timeout=10)
    if result is None:
        return None
    return (result.latitude, result.longitude)


def within_commute_radius(location_text: str, remote_ok: bool) -> bool:
    """True if remote/hybrid, or if the geocoded location falls inside
    MAX_COMMUTE_RADIUS_MILES of Evan's Edgewater, MD origin. Fails
    closed (returns False) if the location can't be geocoded, since an
    unrecognized location shouldn't silently pass the filter."""
    if remote_ok:
        return True
    coords = _geocode(location_text)
    if coords is None:
        return False
    distance = geodesic(config.EDGEWATER_ORIGIN, coords).miles
    return distance <= config.MAX_COMMUTE_RADIUS_MILES
