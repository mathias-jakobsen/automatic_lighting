#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from voluptuous.schema_builder import Required
from . import DOMAIN
from .const import CONF_CONFIRM, CONF_CONSTRAINTS, CONF_DELETE, CONF_GROUP, CONF_PRIORITY, CONF_PROFILES, CONF_TEMPLATE, PROFILE_TYPE_ACTIVE, PROFILE_TYPE_IDLE
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import HomeAssistant
from typing import Any, Dict, Tuple
import voluptuous as vol


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=DOMAIN): str
})

ENTRY_SCHEMA = vol.Schema({
    vol.Required(CONF_CONSTRAINTS, default={}): {
        str: {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_TEMPLATE): str
        }
    },
    vol.Required(CONF_PROFILES, default={}): {
        str: {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_GROUP): str,
            vol.Required(CONF_TYPE, default=PROFILE_TYPE_ACTIVE): vol.In([PROFILE_TYPE_ACTIVE, PROFILE_TYPE_IDLE]),
            vol.Required(CONF_PRIORITY, default=0): int
        }
    }
})


#-----------------------------------------------------------#
#       Schema Builders
#-----------------------------------------------------------#

def schema_builder_step_constraints_create(data: Dict[str, Any], hass: HomeAssistant) -> Dict[str, Any]:
    return vol.Schema({
        vol.Required(CONF_NAME, default=data.get(CONF_NAME, "New Constraint")): str,
        vol.Optional(CONF_TEMPLATE, default=data.get(CONF_TEMPLATE, "{{ True }}")): str,
        vol.Required(CONF_CONFIRM, default=False): bool
    })

def schema_builder_step_constraints_edit(data: Dict[str, Any], hass: HomeAssistant) -> Dict[str, Any]:
    return vol.Schema({
        vol.Required(CONF_NAME, default=data[CONF_NAME]): str,
        vol.Optional(CONF_TEMPLATE, default=data[CONF_TEMPLATE]): str,
        vol.Required(CONF_DELETE, default=False): bool,
        vol.Required(CONF_CONFIRM, default=False): bool
    })
