#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from .const import CONF_BLOCK_DURATION, CONF_LIGHT_GROUPS, DEFAULT_BLOCK_DURATION, DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_ENTITY_ID, CONF_NAME
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

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_NAME]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=vol.Schema({ vol.Required(CONF_NAME): str }))


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
        if not CONF_LIGHT_GROUPS in self._data:
            self._data[CONF_LIGHT_GROUPS] = {}

        if user_input is not None:
            light_groups = {}

            for key in user_input[CONF_LIGHT_GROUPS]:
                if key in self._data[CONF_LIGHT_GROUPS]:
                    light_groups[key] = self._data[CONF_LIGHT_GROUPS][key]

            self._data[CONF_LIGHT_GROUPS] = light_groups

            if CONF_ENTITY_ID in user_input:
                self._data[CONF_LIGHT_GROUPS][user_input[CONF_ENTITY_ID]] = user_input[CONF_ENTITIES]

            if not user_input["new"]:
                return self.async_create_entry(title="", data=self._data)

        light_entity_ids = sorted(self.hass.states.async_entity_ids(LIGHT_DOMAIN))

        schema = vol.Schema({
            vol.Required(CONF_BLOCK_DURATION, default=self._data.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)): vol.All(int, vol.Range(min=0)),
            vol.Required(CONF_LIGHT_GROUPS, default=list(self._data.get(CONF_LIGHT_GROUPS, {}).keys())): cv.multi_select(sorted(list(self._data.get(CONF_LIGHT_GROUPS, {}).keys()))),
            vol.Optional(CONF_ENTITY_ID): vol.In(light_entity_ids),
            vol.Optional(CONF_ENTITIES, default=[]): cv.multi_select(light_entity_ids),
            vol.Required("new", default=False): bool
        })

        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)