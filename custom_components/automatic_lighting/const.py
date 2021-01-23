#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.const import CONF_ENTITY_ID, CONF_LIGHTS
from typing import List
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Component ---------------
DOMAIN = "automatic_lighting"
PLATFORMS = ["sensor"]
UNDO_UPDATE_LISTENER = "undo_update_listener"

# ------ Configuration ---------------
CONF_BLOCK_ENABLED = "block_enabled"
CONF_BLOCK_TIMEOUT = "block_timeout"

# ------ Services ---------------
SERVICE_REGISTER_LIGHTS = "register_lights"
SERVICE_SET_AMBIANCE_LIGHTING = "set_ambiance_lighting"
SERVICE_SET_TRIGGERED_LIGHTING = "set_triggered_lighting"

# ------ States ---------------
STATE_AMBIANCE = "ambiance"
STATE_BLOCKED = "blocked"
STATE_TRIGGERED = "triggered"


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

SERVICE_SCHEMA_REGISTER_LIGHTS = {
    vol.Required(CONF_LIGHTS): dict
}

SERVICE_SCHEMA_SET_AMBIANCE_LIGHTING = {
    vol.Required(CONF_LIGHTS): vol.Schema({
        vol.Required(CONF_ENTITY_ID): [str]
    }, extra=True)
}