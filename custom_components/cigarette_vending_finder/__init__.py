"""Find mapped cigarette vending machines near a home or person."""

from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FinderError, OverpassFinder
from .const import CONF_LIMIT, CONF_PERSON, CONF_RADIUS, DEFAULT_LIMIT, DEFAULT_RADIUS, DOMAIN

PLATFORMS = ("sensor", "geo_location")
_LOGGER = logging.getLogger(__name__)


def coordinates(hass: HomeAssistant, person: str | None = None) -> tuple[float, float]:
    """Use a tracked person's location or the Home Assistant home coordinates."""
    if not person:
        return hass.config.latitude, hass.config.longitude
    state = hass.states.get(person)
    if state is None or not person.startswith("person."):
        raise ServiceValidationError(f"Person entity is unavailable: {person}")
    try:
        latitude = float(state.attributes["latitude"])
        longitude = float(state.attributes["longitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise ServiceValidationError(f"Person has no coordinates: {person}") from error
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ServiceValidationError(f"Person has invalid coordinates: {person}")
    return latitude, longitude


class FinderCoordinator(DataUpdateCoordinator):
    """Keep a modest map view and the most recent search in sync."""

    def __init__(self, hass, entry, finder):
        super().__init__(hass, logger=_LOGGER,
                         name=DOMAIN, update_interval=timedelta(hours=6))
        self.entry = entry
        self.finder = finder
        self.origin: tuple[float, float] | None = None
        self.person: str | None = None

    @property
    def settings(self):
        """Use the latest options with the initial entry values as fallback."""
        return {**self.entry.data, **self.entry.options}

    async def _async_update_data(self):
        settings = self.settings
        person = settings.get(CONF_PERSON) or None
        try:
            origin = coordinates(self.hass, person)
            machines = await self.finder.search(
                *origin, settings.get(CONF_RADIUS, DEFAULT_RADIUS),
                settings.get(CONF_LIMIT, DEFAULT_LIMIT),
            )
        except (FinderError, ServiceValidationError) as error:
            raise UpdateFailed(str(error)) from error
        self.origin, self.person = origin, person
        return machines

    async def async_find(self, origin, person, radius, limit):
        """Search on demand and publish the resulting map view."""
        machines = await self.finder.search(*origin, radius, limit)
        self.origin, self.person = origin, person
        self.async_set_updated_data(machines)
        return machines


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    finder = OverpassFinder(async_get_clientsession(hass))
    coordinator = FinderCoordinator(hass, entry, finder)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    # An unavailable API or person must not prevent configuration or service registration.
    await coordinator.async_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    async def find_nearest(call: ServiceCall) -> dict:
        """Return the nearest machines relative to a person or explicit coordinates."""
        settings = coordinator.settings
        if ("latitude" in call.data) != ("longitude" in call.data):
            raise ServiceValidationError("Latitude and longitude must be provided together")
        person = call.data.get(CONF_PERSON) or settings.get(CONF_PERSON) or None
        if "latitude" in call.data:
            person = None
            origin = (call.data["latitude"], call.data["longitude"])
        else:
            origin = coordinates(hass, person)
        try:
            machines = await coordinator.async_find(
                origin, person,
                call.data.get(CONF_RADIUS, settings.get(CONF_RADIUS, DEFAULT_RADIUS)),
                call.data.get("limit", settings.get(CONF_LIMIT, DEFAULT_LIMIT)),
            )
        except FinderError as error:
            raise HomeAssistantError(str(error)) from error
        return {
            "origin": {"latitude": origin[0], "longitude": origin[1], "person": person},
            "count": len(machines),
            "nearest": machines[0].as_dict() if machines else None,
            "machines": [machine.as_dict() for machine in machines],
        }

    hass.services.async_register(
        DOMAIN, "find_nearest", find_nearest,
        schema=vol.Schema({
            vol.Optional(CONF_PERSON): str,
            vol.Optional("latitude"): vol.All(vol.Coerce(float), vol.Range(min=-90, max=90)),
            vol.Optional("longitude"): vol.All(vol.Coerce(float), vol.Range(min=-180, max=180)),
            vol.Optional(CONF_RADIUS): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
            vol.Optional("limit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        }),
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply new options and refresh the result view."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and its action."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.services.async_remove(DOMAIN, "find_nearest")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
