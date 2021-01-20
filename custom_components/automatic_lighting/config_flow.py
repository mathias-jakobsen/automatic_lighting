#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import DOMAIN, LOGGER
from .const import CONFIG_SCHEMA, CONF_CONSTRAINTS, CONF_PRIORITY, CONF_PROFILES, ENTRY_SCHEMA
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import callback
from homeassistant.util import get_random_string
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Abort Reasons ---------------
ABORT_ALREADY_CONFIGURED = "already_configured"

# ------ Configuration ---------------
CONF_NEXT_ACTION = "next_action"

# ------ Actions & Steps ---------------
ACTION_CONSTRAINTS_CREATE = "New Constraint"
ACTION_GO_BACK = "-- Go Back --"
ACTION_NAVIGATE_CONSTRAINTS = "Manage Constraints"
ACTION_NAVIGATE_PROFILES = "Manage Profiles"
ACTION_SAVE = "-- Save & Exit --"

STEP_CONSTRAINTS = "constraints"
STEP_CONSTRAINTS_CREATE = "constraints_create"
STEP_CONSTRAINTS_EDIT = "constraints_edit"
STEP_INIT = "init"
STEP_PROFILES = "profiles"
STEP_SAVE = "save"
STEP_USER = "user"

OPTIONS_INIT_ACTIONS = {
    ACTION_NAVIGATE_CONSTRAINTS: STEP_CONSTRAINTS,
    ACTION_NAVIGATE_PROFILES: STEP_PROFILES,
    ACTION_SAVE: STEP_SAVE
}

OPTIONS_CONSTRAINTS_ACTIONS = {
    ACTION_CONSTRAINTS_CREATE: STEP_CONSTRAINTS_CREATE
}


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
            await self.async_set_unique_id(f"{DOMAIN}_{get_random_string(10)}")
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
        self._data = ENTRY_SCHEMA({ **config_entry.options })


    #--------------------------------------------#
    #       Steps
    #--------------------------------------------#

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            next_action = user_input[CONF_NEXT_ACTION]
            next_step = OPTIONS_INIT_ACTIONS[next_action]

            if next_step == STEP_SAVE:
                return self.async_create_entry(title="", data=self._data)

            return await getattr(self, f"async_step_{next_step}")()

        return await self.async_show_init_form()

    async def async_step_constraints(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            if user_input[CONF_NEXT_ACTION] == ACTION_GO_BACK:
                return await self.async_show_init_form()

            if user_input[CONF_NEXT_ACTION] == ACTION_CONSTRAINTS_CREATE:
                return self.async_show_form(step_id=STEP_CONSTRAINTS_CREATE)

            constraint_id = user_input[CONF_NEXT_ACTION].split("-")[0].strip()
            schema = vol.Schema()
            return self.async_show_form(step_id=STEP_CONSTRAINTS_EDIT, data_schema=schema)

        constraints = [f"{constraint[CONF_ID]} - {constraint[CONF_NAME]}" for constraint in self._data[CONF_CONSTRAINTS]]
        schema = vol.Schema({ vol.Required(CONF_NEXT_ACTION, default=ACTION_CONSTRAINTS_CREATE): vol.In([action for action in OPTIONS_CONSTRAINTS_ACTIONS.keys()] + constraints + [ACTION_GO_BACK]) })
        return self.async_show_form(step_id=STEP_CONSTRAINTS, data_schema=schema)


    #--------------------------------------------#
    #       Helpers
    #--------------------------------------------#

    async def async_show_init_form(self) -> Dict[str, Any]:
        schema = vol.Schema({ vol.Required(CONF_NEXT_ACTION, default=ACTION_SAVE): vol.In([action for action in OPTIONS_INIT_ACTIONS.keys()]) })
        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)