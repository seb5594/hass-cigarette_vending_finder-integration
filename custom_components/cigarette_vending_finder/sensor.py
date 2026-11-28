"""Distance and location of the nearest cigarette vending machine."""

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the nearest-machine sensor."""
    async_add_entities([NearestMachine(hass.data[DOMAIN][entry.entry_id], entry.entry_id)])


class NearestMachine(CoordinatorEntity, SensorEntity):
    """Represent the nearest machine from the latest search."""

    entity_description = SensorEntityDescription(
        key="nearest", name="Nearest cigarette vending machine",
        native_unit_of_measurement="km",
        icon="mdi:map-marker-radius",
    )
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_nearest"
        self._attr_name = "Nearest cigarette vending machine"

    @property
    def native_value(self):
        """Return the air distance in km."""
        return round(self.coordinator.data[0].distance_km, 2) if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        """Expose identification and access details without hiding missing data."""
        nearest = self.coordinator.data[0].as_dict() if self.coordinator.data else None
        return {
            "machine": nearest,
            "matches": len(self.coordinator.data or []),
            "person": self.coordinator.person,
            "origin": self.coordinator.origin,
            "attribution": ATTRIBUTION,
        }
