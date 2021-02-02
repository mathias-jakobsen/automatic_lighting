#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ATTR_HS_COLOR, ATTR_KELVIN, ATTR_RGB_COLOR, VALID_BRIGHTNESS, VALID_BRIGHTNESS_PCT
from homeassistant.const import CONF_ID, CONF_LIGHTS, CONF_TYPE
from homeassistant.helpers import config_validation as cv
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Component ---------------
DOMAIN = "automatic_lighting"
PLATFORMS = ["sensor"]
NAME = "Automatic Lighting"
UNDO_UPDATE_LISTENER = "undo_update_listener"

# ------ Configuration ---------------
CONF_BLOCK_LIGHTS = "block_lights"
CONF_BLOCK_TIMEOUT = "block_timeout"
CONF_DURATION = "duration"
CONF_GROUP = "group"
CONF_PROFILES = "profiles"
CONF_NEW_STATE = "new_state"
CONF_OLD_STATE = "old_state"
CONF_SUPERVISOR = "supervisor"

# ------ Defaults ---------------
DEFAULT_BLOCK_LIGHTS = []
DEFAULT_BLOCK_TIMEOUT = 300

# ------ Events ---------------
EVENT_AUTOMATIC_LIGHTING = "automatic_lighting_event"
EVENT_TYPE_REFRESH = "refresh"
EVENT_TYPE_RESTART = "restart"

# ------ Attributes ---------------
ATTR_BLOCKED_UNTIL = "blocked_until"

# ------ Services ---------------
SERVICE_REGISTER = "register"

# ------ States ---------------
STATE_AMBIANCE = "ambiance"
STATE_BLOCKED = "blocked"
STATE_TRIGGERED = "triggered"

# ------ Validators ---------------
VALID_COLOR_NAME = cv.string
VALID_COLOR_TEMP = vol.All(vol.Coerce(int), vol.Range(min=1))
VALID_HS_COLOR = vol.All(vol.ExactSequence((vol.All(vol.Coerce(float), vol.Range(min=0, max=360)), vol.All(vol.Coerce(float), vol.Range(min=0, max=100)))),vol.Coerce(tuple))
VALID_KELVIN = cv.positive_int
VALID_RGB_COLOR = vol.All(vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple))
VALID_XY_COLOR = vol.All(vol.ExactSequence((cv.small_float, cv.small_float)), vol.Coerce(tuple))
VALID_WHITE_VALUE = vol.All(vol.Coerce(int), vol.Range(min=0, max=255))


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({}, extra=True)])
}, extra=True)

SERVICE_SCHEMA_REGISTER = {
    vol.Required(CONF_GROUP): str,
    vol.Required(CONF_LIGHTS): vol.Any(str, [str], dict)
}

SERVICE_SCHEMA_TURN_OFF = {
    vol.Required(CONF_ID): cv.string
}

SERVICE_SCHEMA_TURN_ON = {
    vol.Required(CONF_ID): cv.string,
    vol.Required(CONF_TYPE): vol.In([STATE_AMBIANCE, STATE_TRIGGERED]),
    vol.Required(CONF_LIGHTS): dict,
    vol.Optional(ATTR_BRIGHTNESS): VALID_BRIGHTNESS,
    vol.Optional(ATTR_BRIGHTNESS_PCT): VALID_BRIGHTNESS_PCT,
    vol.Optional(ATTR_KELVIN): VALID_KELVIN,
    vol.Optional(ATTR_HS_COLOR): VALID_HS_COLOR,
    vol.Optional(ATTR_RGB_COLOR): VALID_RGB_COLOR
}