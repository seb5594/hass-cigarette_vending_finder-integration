"""Display nearby vending machines as Home Assistant map entities."""

from homeassistant.components.geo_location import GeolocationEvent
# Removed template carry-over: no dispatcher is needed; the coordinator supplies updates.
# from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Add and remove transient map markers after every lookup."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = {}

    def update():
        desired = {f"{machine.osm_type}_{machine.osm_id}": machine
                   for machine in coordinator.data or []}
        for key, entity in list(entities.items()):
            if key not in desired:
                # The update listener cannot directly await removal.
                hass.async_create_task(entity.async_remove(force_remove=True))
                del entities[key]
        new = []
        for key, machine in desired.items():
            if key not in entities:
                entities[key] = MachineLocation(coordinator, entry.entry_id, key)
                new.append(entities[key])
        if new:
            async_add_entities(new)

    entry.async_on_unload(coordinator.async_add_listener(update))
    update()


class MachineLocation(CoordinatorEntity, GeolocationEvent):
    """A mapped machine, removed when it leaves the search results."""

    _attr_should_poll = False

    def __init__(self, coordinator, entry_id, key):
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def machine(self):
        """Find the current record for this marker."""
        return next((item for item in self.coordinator.data or []
                     if f"{item.osm_type}_{item.osm_id}" == self._key), None)

    @property
    def name(self):
        """Show the mapped name or a generic label."""
        return self.machine.name if self.machine else "Cigarette vending machine"

    @property
    def latitude(self):
        """Return feature latitude."""
        return self.machine.latitude if self.machine else None

    @property
    def longitude(self):
        """Return feature longitude."""
        return self.machine.longitude if self.machine else None

    @property
    def distance(self):
        """Return distance in kilometers from the latest search origin."""
        return round(self.machine.distance_km, 3) if self.machine else None

    @property
    def source(self):
        """Name the data source."""
        return DOMAIN

    @property
    def entity_picture(self):
        """Show an image only if a mapper supplied one."""
        return self.machine.image_url if self.machine else None

    @property
    def extra_state_attributes(self):
        """Expose location hints and attribution."""
        return self.machine.as_dict() if self.machine else {"attribution": ATTRIBUTION}
