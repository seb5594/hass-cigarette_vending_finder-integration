"""Exercise setup, service response and unloading in a real Home Assistant core."""

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError  # noqa: E402
from custom_components.cigarette_vending_finder.api import FinderError, Machine  # noqa: E402

DOMAIN = "cigarette_vending_finder"
API = f"custom_components.{DOMAIN}.OverpassFinder.search"


@pytest.fixture(autouse=True)
def _mock_http_session():
    """Keep the real-core tests offline because every Overpass lookup is mocked."""
    with patch(f"custom_components.{DOMAIN}.async_get_clientsession"):
        yield


async def test_flow_and_service(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "maximum_radius_km": 5, "map_limit": 3,
    })
    assert result["type"] == "create_entry"
    assert (await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}))["type"] == "abort"


async def test_entry_and_search_response(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"maximum_radius_km": 5, "map_limit": 3})
    entry.add_to_hass(hass)
    with patch(API, return_value=[]) as search:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        response = await hass.services.async_call(
            DOMAIN, "find_nearest", {"latitude": 50, "longitude": 8},
            blocking=True, return_response=True,
        )
        assert response["count"] == 0
        assert response["nearest"] is None
        assert response["origin"]["latitude"] == 50
        assert search.call_count == 2
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert not hass.services.has_service(DOMAIN, "find_nearest")


async def test_person_search_updates_sensor_and_map(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"maximum_radius_km": 5, "map_limit": 3})
    entry.add_to_hass(hass)
    point = Machine("node", 321, 50.0, 8.0, 0.2, "Outside station",
                    {"location": "beside exit"}, None)
    with patch(API, return_value=[point]) as search:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        hass.states.async_set("person.sebastian", "not_home", {"latitude": 50, "longitude": 8})
        response = await hass.services.async_call(
            DOMAIN, "find_nearest", {"person": "person.sebastian"},
            blocking=True, return_response=True,
        )
        await hass.async_block_till_done()
        assert response["nearest"]["details"]["location"] == "beside exit"
        sensor = hass.states.get("sensor.nearest_cigarette_vending_machine")
        assert sensor is not None and sensor.state == "0.2"
        marker, = [state for state in hass.states.async_all("geo_location")
                   if state.attributes.get("latitude") == 50]
        search.return_value = []
        await hass.services.async_call(
            DOMAIN, "find_nearest", {"latitude": 50, "longitude": 8},
            blocking=True, return_response=True,
        )
        await hass.async_block_till_done()
        assert hass.states.get(marker.entity_id) is None
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_lookup_failure_is_an_action_error(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"maximum_radius_km": 5, "map_limit": 3})
    entry.add_to_hass(hass)
    with patch(API, return_value=[]) as search:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        search.side_effect = FinderError("Overpass unavailable")
        with pytest.raises(HomeAssistantError, match="Overpass unavailable") as error:
            await hass.services.async_call(
                DOMAIN, "find_nearest", {"latitude": 50, "longitude": 8},
                blocking=True, return_response=True,
            )
        assert not isinstance(error.value, ServiceValidationError)
        with pytest.raises(ServiceValidationError, match="must be provided together"):
            await hass.services.async_call(
                DOMAIN, "find_nearest", {"latitude": 50},
                blocking=True, return_response=True,
            )
        assert await hass.config_entries.async_unload(entry.entry_id)
