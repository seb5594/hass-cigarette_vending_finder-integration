"""Query and interpret OpenStreetMap vending-machine locations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import ATTRIBUTION, OVERPASS_URL, RADII_KM

CACHE_TTL = timedelta(hours=6)


class FinderError(Exception):
    """The map service could not provide a valid result."""


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers."""
    lat_a, lat_b = radians(lat1), radians(lat2)
    delta_lat, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 12742 * asin(min(1, sqrt(a)))


def photo_url(tags: dict) -> str | None:
    """Use a Commons image or a direct HTTPS image link, never an arbitrary file URI."""
    commons = tags.get("wikimedia_commons", "")
    if commons.startswith("File:"):
        return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(commons[5:])
    image = tags.get("image", "")
    if image.startswith("https://") and not any(c in image for c in "\n\r\t "):
        return image
    return None


@dataclass(frozen=True)
class Machine:
    """One OSM feature with optional details."""

    osm_type: str
    osm_id: int
    latitude: float
    longitude: float
    distance_km: float
    name: str
    details: dict
    image_url: str | None

    def as_dict(self) -> dict:
        """Return a service response and sensor-friendly representation."""
        lat, lon = self.latitude, self.longitude
        return {
            "id": f"{self.osm_type}/{self.osm_id}",
            "name": self.name,
            "latitude": lat,
            "longitude": lon,
            "distance_km": round(self.distance_km, 3),
            "details": self.details,
            "image_url": self.image_url,
            "osm_url": f"https://www.openstreetmap.org/{self.osm_type}/{self.osm_id}",
            "navigation_url": f"https://www.openstreetmap.org/directions?to={lat}%2C{lon}",
            "attribution": ATTRIBUTION,
        }


DETAIL_TAGS = {
    "description": "description",
    "location": "location",
    "level": "level",
    "addr:street": "street",
    "addr:housenumber": "house_number",
    "addr:city": "city",
    "operator": "operator",
    "brand": "brand",
    "access": "access",
    "indoor": "indoor",
    "opening_hours": "opening_hours",
    "payment:cash": "payment_cash",
    "payment:coins": "payment_coins",
    "payment:credit_cards": "payment_credit_cards",
    "payment:debit_cards": "payment_debit_cards",
    "payment:girocard": "payment_girocard",
    "website": "website",
    "note": "note",
    "mapillary": "mapillary",
    "check_date": "check_date",
    "survey:date": "survey_date",
}


def parse_machine(element: dict, origin: tuple[float, float]) -> Machine | None:
    """Decode a node or the center of a tagged way/relation."""
    point = element.get("center", element)
    try:
        lat, lon = float(point["lat"]), float(point["lon"])
        osm_id, osm_type = int(element["id"]), element["type"]
        if osm_type not in ("node", "way", "relation") or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    tags = element.get("tags") or {}
    if tags.get("amenity") != "vending_machine" or "cigarettes" not in (
        part.strip() for part in tags.get("vending", "").split(";")
    ):
        return None
    details = {label: tags[key] for key, label in DETAIL_TAGS.items() if tags.get(key)}
    return Machine(
        osm_type, osm_id, lat, lon, distance_km(*origin, lat, lon),
        tags.get("name") or "Cigarette vending machine", details, photo_url(tags),
    )


class OverpassFinder:
    """Search in expanding radii while respecting a shared public Overpass service."""

    def __init__(self, session: ClientSession):
        self._session = session
        self._cache: dict[tuple[float, float, int], tuple[datetime, list[dict]]] = {}
        self._lock = asyncio.Lock()

    async def _query(self, latitude: float, longitude: float, radius_km: int) -> list[dict]:
        # Cache by a ~1 km cell and include a 1 km margin to cover every point in it.
        lat_cell, lon_cell = round(latitude, 2), round(longitude, 2)
        key = (lat_cell, lon_cell, radius_km)
        async with self._lock:
            cached = self._cache.get(key)
            if cached and datetime.now(timezone.utc) - cached[0] < CACHE_TTL:
                return cached[1]
            if len(self._cache) > 150:
                self._cache = {k: v for k, v in self._cache.items()
                               if datetime.now(timezone.utc) - v[0] < CACHE_TTL}
                if len(self._cache) > 150:
                    oldest = sorted(self._cache, key=lambda item: self._cache[item][0])
                    for old_key in oldest[:len(self._cache) - 150]:
                        del self._cache[old_key]
            query = (
                "[out:json][timeout:35];"
                f'nwr["amenity"="vending_machine"]["vending"~"(^|;) *cigarettes *(;|$)"]'
                f"(around:{radius_km * 1000 + 1500},{lat_cell},{lon_cell});"
                "out center tags;"
            )
            try:
                async with self._session.post(
                    OVERPASS_URL, data={"data": query},
                    timeout=ClientTimeout(total=45),
                    headers={"User-Agent": "HomeAssistant-CigaretteVendingFinder/1.0 (github.com/seb5594/hass-cigarette_vending_finder-integration)"},
                ) as response:
                    if response.status != 200:
                        raise FinderError(f"Overpass returned HTTP {response.status}")
                    payload = await response.json(content_type=None)
            except (ClientError, asyncio.TimeoutError, ValueError) as error:
                raise FinderError("OpenStreetMap lookup failed") from error
            if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                raise FinderError("Invalid Overpass response")
            elements = payload["elements"]
            self._cache[key] = (datetime.now(timezone.utc), elements)
            return elements

    async def search(
        self, latitude: float, longitude: float, maximum_radius_km: int, limit: int
    ) -> list[Machine]:
        """Find the nearest mapped machines, expanding only as required."""
        origin = (latitude, longitude)
        results: dict[tuple[str, int], Machine] = {}
        for radius in (*[r for r in RADII_KM if r < maximum_radius_km], maximum_radius_km):
            for element in await self._query(latitude, longitude, radius):
                machine = parse_machine(element, origin)
                if machine is not None and machine.distance_km <= maximum_radius_km:
                    results[(machine.osm_type, machine.osm_id)] = machine
            nearest = sorted(results.values(), key=lambda machine: machine.distance_km)
            if len(nearest) >= limit and nearest[limit - 1].distance_km <= radius:
                break
        return sorted(results.values(), key=lambda machine: machine.distance_km)[:limit]
