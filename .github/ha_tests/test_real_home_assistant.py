"""Exercise setup, service response and unloading in a real Home Assistant core."""

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402
from custom_components.cigarette_vending_finder.api import Machine  # noqa: E402

DOMAIN = "cigarette_vending_finder"
API = f"custom_components.{DOMAIN}.OverpassFinder.search"


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
    with patch(API, return_value=[point]):
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
        assert any(state.entity_id.startswith("geo_location.")
                   and state.attributes.get("latitude") == 50
                   for state in hass.states.async_all())
        assert await hass.config_entries.async_unload(entry.entry_id)
