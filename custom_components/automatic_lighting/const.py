#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ATTR_KELVIN, VALID_BRIGHTNESS, VALID_BRIGHTNESS_PCT
from homeassistant.const import CONF_ID, CONF_LIGHTS, CONF_TYPE
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
CONF_DURATION = "duration"
CONF_PROFILES = "profiles"
CONF_NEW_STATE = "new_state"
CONF_OLD_STATE = "old_state"

# ------ Defaults ---------------
DEFAULT_BLOCK_LIGHTS = []
DEFAULT_BLOCK_TIMEOUT = 300

# ------ Events ---------------
EVENT_AUTOMATIC_LIGHTING = "automatic_lighting_event"
EVENT_TYPE_REFRESH = "refresh"

# ------ Attributes ---------------
ATTR_BLOCKED_UNTIL = "blocked_until"

# ------ States ---------------
STATE_AMBIANCE = "ambiance"
STATE_BLOCKED = "blocked"
STATE_TRIGGERED = "triggered"


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({}, extra=True)])
}, extra=True)

SERVICE_SCHEMA_TURN_OFF = {
    vol.Required(CONF_ID): cv.string
}

SERVICE_SCHEMA_TURN_ON = {
    vol.Required(CONF_ID): cv.string,
    vol.Required(CONF_TYPE): vol.In([STATE_AMBIANCE, STATE_TRIGGERED]),
    vol.Required(CONF_LIGHTS): dict,
    vol.Optional(ATTR_BRIGHTNESS): VALID_BRIGHTNESS,
    vol.Optional(ATTR_BRIGHTNESS_PCT): VALID_BRIGHTNESS_PCT,
    vol.Optional(ATTR_KELVIN): cv.positive_int
}