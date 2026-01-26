"""Geocoding utilities for converting location strings to coordinates."""

import re
from typing import Optional
from models import GeoLocation

# US State coordinates (approximate centers) for fallback
US_STATE_COORDS = {
    "alabama": (32.806671, -86.791130), "al": (32.806671, -86.791130),
    "alaska": (61.370716, -152.404419), "ak": (61.370716, -152.404419),
    "arizona": (33.729759, -111.431221), "az": (33.729759, -111.431221),
    "arkansas": (34.969704, -92.373123), "ar": (34.969704, -92.373123),
    "california": (36.116203, -119.681564), "ca": (36.116203, -119.681564),
    "colorado": (39.059811, -105.311104), "co": (39.059811, -105.311104),
    "connecticut": (41.597782, -72.755371), "ct": (41.597782, -72.755371),
    "delaware": (39.318523, -75.507141), "de": (39.318523, -75.507141),
    "florida": (27.766279, -81.686783), "fl": (27.766279, -81.686783),
    "georgia": (33.040619, -83.643074), "ga": (33.040619, -83.643074),
    "hawaii": (21.094318, -157.498337), "hi": (21.094318, -157.498337),
    "idaho": (44.240459, -114.478828), "id": (44.240459, -114.478828),
    "illinois": (40.349457, -88.986137), "il": (40.349457, -88.986137),
    "indiana": (39.849426, -86.258278), "in": (39.849426, -86.258278),
    "iowa": (42.011539, -93.210526), "ia": (42.011539, -93.210526),
    "kansas": (38.526600, -96.726486), "ks": (38.526600, -96.726486),
    "kentucky": (37.668140, -84.670067), "ky": (37.668140, -84.670067),
    "louisiana": (31.169546, -91.867805), "la": (31.169546, -91.867805),
    "maine": (44.693947, -69.381927), "me": (44.693947, -69.381927),
    "maryland": (39.063946, -76.802101), "md": (39.063946, -76.802101),
    "massachusetts": (42.230171, -71.530106), "ma": (42.230171, -71.530106),
    "michigan": (43.326618, -84.536095), "mi": (43.326618, -84.536095),
    "minnesota": (45.694454, -93.900192), "mn": (45.694454, -93.900192),
    "mississippi": (32.741646, -89.678696), "ms": (32.741646, -89.678696),
    "missouri": (38.456085, -92.288368), "mo": (38.456085, -92.288368),
    "montana": (46.921925, -110.454353), "mt": (46.921925, -110.454353),
    "nebraska": (41.125370, -98.268082), "ne": (41.125370, -98.268082),
    "nevada": (38.313515, -117.055374), "nv": (38.313515, -117.055374),
    "new hampshire": (43.452492, -71.563896), "nh": (43.452492, -71.563896),
    "new jersey": (40.298904, -74.521011), "nj": (40.298904, -74.521011),
    "new mexico": (34.840515, -106.248482), "nm": (34.840515, -106.248482),
    "new york": (42.165726, -74.948051), "ny": (42.165726, -74.948051),
    "north carolina": (35.630066, -79.806419), "nc": (35.630066, -79.806419),
    "north dakota": (47.528912, -99.784012), "nd": (47.528912, -99.784012),
    "ohio": (40.388783, -82.764915), "oh": (40.388783, -82.764915),
    "oklahoma": (35.565342, -96.928917), "ok": (35.565342, -96.928917),
    "oregon": (44.572021, -122.070938), "or": (44.572021, -122.070938),
    "pennsylvania": (40.590752, -77.209755), "pa": (40.590752, -77.209755),
    "rhode island": (41.680893, -71.511780), "ri": (41.680893, -71.511780),
    "south carolina": (33.856892, -80.945007), "sc": (33.856892, -80.945007),
    "south dakota": (44.299782, -99.438828), "sd": (44.299782, -99.438828),
    "tennessee": (35.747845, -86.692345), "tn": (35.747845, -86.692345),
    "texas": (31.054487, -97.563461), "tx": (31.054487, -97.563461),
    "utah": (40.150032, -111.862434), "ut": (40.150032, -111.862434),
    "vermont": (44.045876, -72.710686), "vt": (44.045876, -72.710686),
    "virginia": (37.769337, -78.169968), "va": (37.769337, -78.169968),
    "washington": (47.400902, -121.490494), "wa": (47.400902, -121.490494),
    "west virginia": (38.491226, -80.954453), "wv": (38.491226, -80.954453),
    "wisconsin": (44.268543, -89.616508), "wi": (44.268543, -89.616508),
    "wyoming": (42.755966, -107.302490), "wy": (42.755966, -107.302490),
    # DC
    "washington dc": (38.907192, -77.036873), "dc": (38.907192, -77.036873),
    "district of columbia": (38.907192, -77.036873),
    # Canada provinces (some stories mention)
    "canada": (56.130366, -106.346771),
    "ontario": (51.253775, -85.323214),
    "quebec": (52.939916, -73.549136),
    "british columbia": (53.726669, -127.647621), "bc": (53.726669, -127.647621),
    "alberta": (53.933271, -116.576503), "ab": (53.933271, -116.576503),
}

# Major US cities with coordinates
US_CITY_COORDS = {
    "new york city": (40.712776, -74.005974),
    "los angeles": (34.052234, -118.243685),
    "chicago": (41.878113, -87.629799),
    "houston": (29.760427, -95.369804),
    "phoenix": (33.448377, -112.074037),
    "philadelphia": (39.952583, -75.165222),
    "san antonio": (29.424122, -98.493628),
    "san diego": (32.715738, -117.161084),
    "dallas": (32.776664, -96.796988),
    "san jose": (37.338208, -121.886329),
    "austin": (30.267153, -97.743061),
    "jacksonville": (30.332184, -81.655651),
    "fort worth": (32.755488, -97.330766),
    "columbus": (39.961176, -82.998794),
    "charlotte": (35.227087, -80.843127),
    "san francisco": (37.774929, -122.419416),
    "indianapolis": (39.768403, -86.158068),
    "seattle": (47.606209, -122.332071),
    "denver": (39.739236, -104.990251),
    "boston": (42.360082, -71.058880),
    "nashville": (36.162664, -86.781602),
    "detroit": (42.331427, -83.045754),
    "portland": (45.505106, -122.675026),
    "las vegas": (36.169941, -115.139830),
    "memphis": (35.149534, -90.048980),
    "atlanta": (33.748995, -84.387982),
    "miami": (25.761680, -80.191790),
    "pittsburgh": (40.440625, -79.995886),
    "cleveland": (41.499320, -81.694361),
    "new orleans": (29.951066, -90.071532),
    "tampa": (27.950575, -82.457178),
    "minneapolis": (44.977753, -93.265011),
    "st louis": (38.627003, -90.199404),
    "salt lake city": (40.760779, -111.891047),
}


def extract_state_from_location(location: str) -> Optional[str]:
    """Extract state name/abbreviation from location string."""
    loc_lower = location.lower().strip()

    # Check for state abbreviation at end (e.g., "Dallas, TX")
    match = re.search(r',\s*([a-z]{2})$', loc_lower)
    if match:
        abbrev = match.group(1)
        if abbrev in US_STATE_COORDS:
            return abbrev

    # Check for full state name
    for state in US_STATE_COORDS:
        if state in loc_lower and len(state) > 2:
            return state

    return None


def geocode_location(location: str) -> Optional[GeoLocation]:
    """
    Convert a location string to coordinates.
    Uses a simple rule-based approach with fallback to state centers.
    """
    if not location or location.lower() in ("unknown", "n/a", ""):
        return None

    loc_lower = location.lower().strip()

    # Try to match city first
    for city, coords in US_CITY_COORDS.items():
        if city in loc_lower:
            state = extract_state_from_location(location)
            return GeoLocation(
                location=location,
                lat=coords[0],
                lng=coords[1],
                state=state,
                country="USA"
            )

    # Try to match state
    state = extract_state_from_location(location)
    if state and state in US_STATE_COORDS:
        coords = US_STATE_COORDS[state]
        return GeoLocation(
            location=location,
            lat=coords[0],
            lng=coords[1],
            state=state,
            country="USA"
        )

    # Check for full state name anywhere in string
    for state_name, coords in US_STATE_COORDS.items():
        if len(state_name) > 2 and state_name in loc_lower:
            return GeoLocation(
                location=location,
                lat=coords[0],
                lng=coords[1],
                state=state_name,
                country="USA"
            )

    # Check for "area" patterns (e.g., "Houston area", "Dallas area")
    area_match = re.search(r'(\w+)\s+area', loc_lower)
    if area_match:
        area_city = area_match.group(1)
        for city, coords in US_CITY_COORDS.items():
            if area_city in city:
                return GeoLocation(
                    location=location,
                    lat=coords[0],
                    lng=coords[1],
                    state=extract_state_from_location(location),
                    country="USA"
                )

    return None


def batch_geocode(locations: list[str]) -> dict[str, Optional[GeoLocation]]:
    """Geocode multiple locations."""
    return {loc: geocode_location(loc) for loc in locations}
