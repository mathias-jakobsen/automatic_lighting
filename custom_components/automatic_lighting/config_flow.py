#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER
from .const import CONF_BLOCK_ATTRIBUTES, CONF_BLOCK_ENABLED, CONF_BLOCK_STATE, CONF_BLOCK_TIMEOUT, CONF_BLOCK_VARIANCE, DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ATTR_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_WHITE_VALUE,
    ATTR_XY_COLOR
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import get_random_string
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Abort Reasons ---------------
ABORT_REASON_ALREADY_CONFIGURED = "already_configured"

# ------ Block Attributes ---------------
BLOCK_ATTRIBUTES = [
    ATTR_BRIGHTNESS,
    ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ATTR_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_XY_COLOR,
    ATTR_WHITE_VALUE
]

# ------ Steps ---------------
STEP_INIT = "init"
STEP_USER = "user"

# ------ Schemas ---------------
CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=DOMAIN): str
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Required(CONF_BLOCK_ENABLED, default=False): bool,
    vol.Required(CONF_BLOCK_STATE, default=True): bool,
    vol.Required(CONF_BLOCK_ATTRIBUTES, default=[]): cv.multi_select(BLOCK_ATTRIBUTES),
    vol.Required(CONF_BLOCK_VARIANCE, default=10): vol.All(int, vol.Range(min=0)),
    vol.Required(CONF_BLOCK_TIMEOUT, default=600): vol.All(int, vol.Range(min=0))
})

# ------ Tuples ---------------
OPTIONS_VALIDATORS = [
    (CONF_BLOCK_ENABLED, False, bool),
    (CONF_BLOCK_STATE, True, bool),
    (CONF_BLOCK_ATTRIBUTES, [], cv.multi_select(BLOCK_ATTRIBUTES)),
    (CONF_BLOCK_VARIANCE, 10, vol.All(int, vol.Range(min=0))),
    (CONF_BLOCK_TIMEOUT, 600, vol.All(int, vol.Range(min=0)))
]


#-----------------------------------------------------------#
#       Functions
#-----------------------------------------------------------#

def get_options_schema(data: Dict[str, Any]) -> vol.Schema:
    validators = { vol.Optional(key, default=data.get(key, default)): validator for key, default, validator in OPTIONS_VALIDATORS }
    return vol.Schema(validators)


#-----------------------------------------------------------#
#       Config Flow
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
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id=STEP_USER, data_schema=CONFIG_SCHEMA)


#-----------------------------------------------------------#
#       Options Flow
#-----------------------------------------------------------#

class AL_OptionsFlow(OptionsFlow):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry = config_entry
        self._data = get_options_schema(config_entry.options)({ **config_entry.options })


    #--------------------------------------------#
    #       Steps - Init
    #--------------------------------------------#

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = get_options_schema(self._data)
        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)