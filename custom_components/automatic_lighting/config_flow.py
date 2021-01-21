#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import DOMAIN, LOGGER
from .const import CONF_CONFIRM, CONF_CONSTRAINTS, CONF_DELETE, CONF_PRIORITY, CONF_PROFILES, CONF_TEMPLATE
from .schemas import CONFIG_SCHEMA, ENTRY_SCHEMA, schema_builder_step_constraints_create, schema_builder_step_constraints_edit
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import callback
from homeassistant.helpers.config_validation import slugify
from homeassistant.helpers.template import is_template_string
from homeassistant.util import get_random_string
from typing import Any, Dict, Union
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Abort Reasons ---------------
ABORT_REASON_ALREADY_CONFIGURED = "already_configured"

# ------ Errors ---------------
ERROR_INVALID_TEMPLATE = "invalid_template"
ERROR_NAME_ALREADY_USED = "name_already_used"

# ------ Configuration ---------------
CONF_NEXT_ACTION = "next_action"

# ------ Actions & Steps ---------------
ACTION_CONSTRAINTS = "Constraints"
ACTION_CONSTRAINTS_CREATE = "New Constraint"
ACTION_GO_BACK = "-- Go Back --"
ACTION_GROUPS = "Groups"
ACTION_PROFILES = "Profiles"
ACTION_NAVIGATE_PROFILES = "Manage Profiles"
ACTION_SAVE = "-- Save & Exit --"

STEP_CONSTRAINTS = "constraints"
STEP_CONSTRAINTS_CREATE = "constraints_create"
STEP_CONSTRAINTS_EDIT = "constraints_edit"
STEP_GROUPS = "groups"
STEP_GROUPS_CREATE = "groups_create"
STEP_GROUPS_EDIT = "groups_edit"
STEP_INIT = "init"
STEP_PROFILES = "profiles"
STEP_PROFILES_CREATE = "profiles_create"
STEP_PROFILES_EDIT = "profiles_edit"
STEP_SAVE = "save"
STEP_USER = "user"

OPTIONS_INIT_ACTIONS = {
    ACTION_CONSTRAINTS: STEP_CONSTRAINTS,
    ACTION_GROUPS: STEP_GROUPS,
    ACTION_PROFILES: STEP_PROFILES,
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
            if len(self.hass.config_entries.async_entries(DOMAIN)) > 0:
                return self.async_abort(reason=ABORT_REASON_ALREADY_CONFIGURED)

            await self.async_set_unique_id(DOMAIN)
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
    #       Steps - Init
    #--------------------------------------------#

    async def async_step_init(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            next_action = user_input[CONF_NEXT_ACTION]
            next_step = OPTIONS_INIT_ACTIONS[next_action]

            if next_step == STEP_SAVE:
                return self.async_create_entry(title="", data=self._data)

            return await getattr(self, f"async_step_{next_step}")()

        schema = vol.Schema({ vol.Required(CONF_NEXT_ACTION, default=ACTION_SAVE): vol.In([action for action in OPTIONS_INIT_ACTIONS.keys()]) })
        return self.async_show_form(step_id=STEP_INIT, data_schema=schema)


    #--------------------------------------------#
    #       Steps - Constraints
    #--------------------------------------------#

    async def async_step_constraints(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        if user_input is not None:
            if user_input[CONF_NEXT_ACTION] == ACTION_GO_BACK:
                return await self.async_step_init()

            if user_input[CONF_NEXT_ACTION] == ACTION_CONSTRAINTS_CREATE:
                return await self.async_step_constraints_create()

            self._constraint_id = user_input[CONF_NEXT_ACTION].split("-")[0].strip()
            return await self.async_step_constraints_edit()

        constraints = [f"{key} - {constraint[CONF_NAME]}" for key, constraint in self._data[CONF_CONSTRAINTS].items()]
        schema = vol.Schema({ vol.Required(CONF_NEXT_ACTION, default=ACTION_CONSTRAINTS_CREATE): vol.In([action for action in OPTIONS_CONSTRAINTS_ACTIONS.keys()] + constraints + [ACTION_GO_BACK]) })
        return self.async_show_form(step_id=STEP_CONSTRAINTS, data_schema=schema)

    async def async_step_constraints_create(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        errors = {}

        if user_input is not None:
            if not user_input.pop(CONF_CONFIRM):
                return await self.async_step_constraints()

            if not is_template_string(user_input[CONF_TEMPLATE]):
                errors[CONF_TEMPLATE] = ERROR_INVALID_TEMPLATE

            if len(errors) == 0:
                self._data[CONF_CONSTRAINTS] = { **self._data[CONF_CONSTRAINTS], get_random_string(5): user_input }
                return await self.async_step_constraints()

        schema = schema_builder_step_constraints_create(user_input or {}, self.hass)
        return self.async_show_form(step_id=STEP_CONSTRAINTS_CREATE, data_schema=schema, errors=errors)

    async def async_step_constraints_edit(self, user_input: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        errors = {}

        if user_input is not None:
            if not user_input.pop(CONF_CONFIRM):
                return await self.async_step_constraints()

            if user_input.pop(CONF_DELETE):
                self._data[CONF_CONSTRAINTS].pop(self._constraint_id)
                return await self.async_step_constraints()

            if not is_template_string(user_input[CONF_TEMPLATE]):
                errors[CONF_TEMPLATE] = ERROR_INVALID_TEMPLATE

            if len(errors) == 0:
                self._data[CONF_CONSTRAINTS][self._constraint_id] = user_input
                return await self.async_step_constraints()

        schema = schema_builder_step_constraints_edit(user_input or self._data[CONF_CONSTRAINTS][self._constraint_id], self.hass)
        return self.async_show_form(step_id=STEP_CONSTRAINTS_EDIT, data_schema=schema, errors=errors)


    #--------------------------------------------#
    #       Helpers
    #--------------------------------------------#
