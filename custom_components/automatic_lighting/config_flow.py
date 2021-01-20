from . import DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.core import callback
from typing import Any, Dict
from voluptuous import Schema

class AL_ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    #@staticmethod
    #@callback
    #def async_get_options_flow(config_entry: ConfigEntry):
    #    return AL_OptionsFlow(config_entry)

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            if len(self.hass.config_entries.async_entries(DOMAIN)) > 0:
                return self.async_abort(reason="single_instance_allowed")

            await self.async_set_unique_id(DOMAIN)
            return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(step_id="user", data_schema=Schema({}))