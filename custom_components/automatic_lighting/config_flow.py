#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from .const import CONF_BLOCK_LIGHTS, CONF_BLOCK_TIMEOUT, DEFAULT_BLOCK_LIGHTS, DEFAULT_BLOCK_TIMEOUT, DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Abort Reasons ---------------
ABORT_REASON_ALREADY_CONFIGURED = "already_configured"

# ------ Steps ---------------
STEP_INIT = "init"
STEP_USER = "user"


#-----------------------------------------------------------#
#       Config Flowx
#-----------------------------------------------------------#

class AL_ConfigFlow(ConfigFlow, domain=DOMAIN):
    #--------------------------------------------#
    #       Static Properties
    #--------------------------------------------#

    VERSION = 1


    #--------------------------------------------#
    #       Static Methods
    #--------------------------------------------#

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AL_OptionsFlow:
        return AL_OptionsFlow(config_entry)


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_step_import(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        await self.async_set_unique_id(user_input[CONF_NAME])

        for config_entry in self._async_current_entries():
            if config_entry.unique_id != self.unique_id:
                continue

            self.hass.config_entries.async_update_entry(config_entry, data=user_input)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema({ vol.Required(CONF_NAME, default=DOMAIN): str })
        return self.async_show_form(step_id=STEP_USER, data_schema=schema)


#-----------------------------------------------------------#
#       Options Flow
#-----------------------------------------------------------#

class AL_OptionsFlow(OptionsFlow):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry = config_entry
        self._data = { **config_entry.options }


    #--------------------------------------------#
    #       Steps - Init
    #--------------------------------------------#

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        light_entity_ids = self.hass.states.async_entity_ids(domain_filter=LIGHT_DOMAIN)
        schema = vol.Schema({
            vol.Required(CONF_BLOCK_LIGHTS, default=self._data.get(CONF_BLOCK_LIGHTS, DEFAULT_BLOCK_LIGHTS)): cv.multi_select(light_entity_ids),
            vol.Required(CONF_BLOCK_TIMEOUT, default=self._data.get(CONF_BLOCK_TIMEOUT, DEFAULT_BLOCK_TIMEOUT)): vol.All(int, vol.Range(min=0))
        })

        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)