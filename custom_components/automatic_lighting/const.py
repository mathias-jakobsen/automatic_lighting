#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ATTR_KELVIN, VALID_BRIGHTNESS, VALID_BRIGHTNESS_PCT
from homeassistant.const import CONF_ENTITY_ID, CONF_LIGHTS, CONF_TYPE
from homeassistant.helpers import config_validation as cv
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Component ---------------
DOMAIN = "automatic_lighting"
PLATFORMS = ["sensor"]
UNDO_UPDATE_LISTENER = "undo_update_listener"

# ------ Configuration ---------------
CONF_BLOCK_LIGHTS = "block_lights"
CONF_BLOCK_TIMEOUT = "block_timeout"

# ------ Defaults ---------------
DEFAULT_BLOCK_LIGHTS = []
DEFAULT_BLOCK_TIMEOUT = 60

# ------ States ---------------
STATE_AMBIANCE = "ambiance"
STATE_BLOCKED = "blocked"
STATE_TRIGGERED = "triggered"

# ------ Types ---------------
TYPE_AMBIANCE = "ambiance"
TYPE_TRIGGERED = "triggered"


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

SERVICE_SCHEMA_TURN_OFF = {}

SERVICE_SCHEMA_TURN_ON = {
    vol.Required(CONF_TYPE): vol.In([TYPE_AMBIANCE, TYPE_TRIGGERED]),
    vol.Required(CONF_LIGHTS): [str],
    vol.Optional(ATTR_BRIGHTNESS): VALID_BRIGHTNESS,
    vol.Optional(ATTR_BRIGHTNESS_PCT): VALID_BRIGHTNESS_PCT,
    vol.Optional(ATTR_KELVIN): cv.positive_int
}