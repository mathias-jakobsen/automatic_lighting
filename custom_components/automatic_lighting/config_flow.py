#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from . import DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

ABORT_ALREADY_CONFIGURED = "already_configured"
STEP_INIT = "init"
STEP_USER = "user"


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
    def async_get_options_flow(config_entry: ConfigEntry):
        return AL_OptionsFlow(config_entry)


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_step_user(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        if user_input is not None:
            if len(self.hass.config_entries.async_entries(DOMAIN)) > 0:
                return self.async_abort(reason=ABORT_ALREADY_CONFIGURED)

            await self.async_set_unique_id(DOMAIN)
            return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(step_id=STEP_USER, data_schema=vol.Schema({}))


#-----------------------------------------------------------#
#       Options Flow
#-----------------------------------------------------------#

class AL_OptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        pass
        #self._config_entry = config_entry
        #self._data = ENTRY_BASE_SCHEMA({ **config_entry.data, **config_entry.options })

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({ vol.Required("test"): str }))