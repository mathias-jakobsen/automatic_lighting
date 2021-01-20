#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from .const import CONF_CONSTRAINTS, CONF_PRIORITY, CONF_PROFILES, CONF_SHARE, CONF_TEMPLATE, PROFILE_TYPE_ACTIVE, PROFILE_TYPE_IDLE
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import HomeAssistant
from typing import Any, Dict
import voluptuous as vol


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): str
})

ENTRY_SCHEMA = vol.Schema({
    vol.Required(CONF_CONSTRAINTS, default=[]): [{
        vol.Required(CONF_ID): str,
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_TEMPLATE): str
    }],
    vol.Required(CONF_PROFILES, default=[]): [{
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_TYPE, default=PROFILE_TYPE_ACTIVE): vol.In([PROFILE_TYPE_ACTIVE, PROFILE_TYPE_IDLE]),
        vol.Required(CONF_PRIORITY, default=0): int
    }]
})


#-----------------------------------------------------------#
#       Schema Builders
#-----------------------------------------------------------#

def schema_builder_step_constraints_edit(data: Dict[str, Any], hass: HomeAssistant) -> Dict[str, Any]:
    return {
        vol.Required(CONF_NAME, default=data[CONF_NAME]): str,
        vol.Required(CONF_TEMPLATE, default=data[CONF_TEMPLATE]): str,
        vol.Required(CONF_SHARE, default=False): bool
    }
    #return {

    #    vol.Required(CONF_ENABLED, default=data[CONF_ENABLED]): bool,
    #    vol.Optional(CONF_STATE, default=data[CONF_STATE]): bool,
    #    vol.Optional(CONF_ATTRIBUTES, default=data[CONF_ATTRIBUTES]): cv.multi_select(BLOCK_ATTRIBUTES),
    #    vol.Optional(CONF_DURATION, default=data[CONF_DURATION]): cv.positive_int
    #}