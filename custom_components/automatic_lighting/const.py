#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ATTR_HS_COLOR, ATTR_KELVIN, ATTR_RGB_COLOR, VALID_BRIGHTNESS, VALID_BRIGHTNESS_PCT
from homeassistant.const import CONF_ID, CONF_LIGHTS
from homeassistant.helpers import config_validation as cv
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Component ---------------
DOMAIN = "automatic_lighting"
PLATFORMS = ["switch"]
NAME = "Automatic Lighting"
UNDO_UPDATE_LISTENER = "undo_update_listener"

# ------ Configuration ---------------
CONF_ATTRIBUTES = "attributes"
CONF_BLOCK_DURATION = "block_timeout"
CONF_CONSTRAIN = "constrain"
CONF_DURATION = "duration"
CONF_GROUP = "group"
CONF_ILLUMINANCE_ENTITY = "illuminance_entity"
CONF_ILLUMINANCE_THRESHOLD = "illuminance_threshold"
CONF_PROFILES = "profiles"
CONF_NEW_STATE = "new_state"
CONF_OLD_STATE = "old_state"
CONF_SUPERVISOR = "supervisor"
CONF_TRIGGERS = "triggers"

# ------ Defaults ---------------
DEFAULT_BLOCK_DURATION = 300

# ------ Events ---------------
EVENT_AUTOMATIC_LIGHTING = "automatic_lighting_event"
EVENT_TYPE_REFRESH = "refresh"
EVENT_TYPE_RESTART = "restart"

# --- Attributes ----------
ATTR_ACTIVE_UNTIL = "active_until"
ATTR_BLOCKED_UNTIL = "blocked_until"
ATTR_LAST_TRIGGERED_AT = "last_triggered_at"
ATTR_LAST_TRIGGERED_BY = "last_triggered_by"
ATTR_STATUS = "status"

# ------ Services ---------------
SERVICE_BLOCK = "block"
SERVICE_CONSTRAIN = "constrain"
SERVICE_REGISTER = "register"

# ------ Status ---------------
STATUS_ACTIVE = "active"
STATUS_BLOCKED = "blocked"
STATUS_IDLE = "idle"

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

SERVICE_SCHEMA_BLOCK = {
    vol.Optional(CONF_BLOCK_DURATION): cv.positive_int
}

SERVICE_SCHEMA_CONSTRAIN = {
    vol.Required(CONF_CONSTRAIN): bool,
    vol.Optional(CONF_ID): str
}

SERVICE_SCHEMA_REGISTER = {
    vol.Inclusive(CONF_TRIGGERS, "triggered"): vol.Any(str, [str], dict),
    vol.Inclusive(CONF_DURATION, "triggered"): cv.positive_int,
    vol.Required(CONF_LIGHTS): vol.Any(str, [str], dict),
    vol.Optional(CONF_ID): str,
    vol.Optional(ATTR_BRIGHTNESS): VALID_BRIGHTNESS,
    vol.Optional(ATTR_BRIGHTNESS_PCT): VALID_BRIGHTNESS_PCT,
    vol.Optional(ATTR_KELVIN): VALID_KELVIN,
    vol.Optional(ATTR_HS_COLOR): VALID_HS_COLOR,
    vol.Optional(ATTR_RGB_COLOR): VALID_RGB_COLOR
}