"""Config flow for Cigarette Vending Finder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers.selector import EntitySelector

from .const import CONF_LIMIT, CONF_PERSON, CONF_RADIUS, DEFAULT_LIMIT, DEFAULT_RADIUS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult


def schema(options: dict | None = None) -> vol.Schema:
    """Build configuration and options schema."""
    options = options or {}
    return vol.Schema(
        {
            vol.Optional(CONF_PERSON, description={"suggested_value": options.get(CONF_PERSON)}): EntitySelector(
                {"domain": "person"}
            ),
            vol.Optional(CONF_RADIUS, default=options.get(CONF_RADIUS, DEFAULT_RADIUS)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=100)
            ),
            vol.Optional(CONF_LIMIT, default=options.get(CONF_LIMIT, DEFAULT_LIMIT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=30)
            ),
        }
    )


class CigaretteVendingFinderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one OSM finder instance."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Create the instance."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Cigarette Vending Finder", data=user_input)
        return self.async_show_form(step_id="user", data_schema=schema())

    @staticmethod
    def async_get_options_flow(config_entry):
        """Expose options without duplicating an integration instance."""
        return FinderOptionsFlow(config_entry)


class FinderOptionsFlow(OptionsFlow):
    """Change radius, person, and map result count."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Store updated options."""
        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_PERSON: "", **user_input})
        return self.async_show_form(
            step_id="init", data_schema=schema({**self._entry.data, **self._entry.options})
        )
