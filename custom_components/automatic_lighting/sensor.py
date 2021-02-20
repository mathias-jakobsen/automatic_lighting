#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER_BASE_NAME
from .const import CONF_ATTRIBUTES, CONF_BLOCK_TIMEOUT, CONF_DURATION, CONF_GROUP, CONF_TRIGGERS, DEFAULT_BLOCK_TIMEOUT, DOMAIN, EVENT_AUTOMATIC_LIGHTING, EVENT_TYPE_RESTART, NAME, SERVICE_BLOCK, SERVICE_REGISTER, SERVICE_SCHEMA_BLOCK, SERVICE_SCHEMA_REGISTER, STATE_AMBIANCE, STATE_BLOCKED, STATE_TRIGGERED
from .utils import Timer, async_resolve_target, async_track_automations_changed, async_track_manual_control, EntityBase, EntityHelpers
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_AFTER, CONF_BEFORE, CONF_LIGHTS, CONF_NAME, CONF_TIMEOUT, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import Context, Event, HomeAssistant, ServiceCall, State
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later, async_track_state_change
from logging import Logger, getLogger
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

REFRESH_DEBOUNCE_TIME = 0.2
RESTART_DEBOUNCE_TIME = 0.2
START_DELAY = 0.5


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    supervisor = AL_Supervisor(config_entry)
    async_add_entities([supervisor], update_before_add=True)
    hass.services.async_register(DOMAIN, SERVICE_BLOCK, supervisor.async_service_block, SERVICE_SCHEMA_BLOCK)
    hass.services.async_register(DOMAIN, SERVICE_REGISTER, supervisor.async_service_register, SERVICE_SCHEMA_REGISTER)
    return True




class AL_Entity(EntityBase):
    #-----------------------------------------------------------------------------#
    #
    #       Entity Section
    #
    #-----------------------------------------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        super().__init__(getLogger(f"{LOGGER_BASE_NAME}.{config_entry.data[CONF_NAME]}"))



    #-----------------------------------------------------------------------------#
    #
    #       Logic Section
    #
    #-----------------------------------------------------------------------------#
    #       Constructor
    #--------------------------------------------#




#-----------------------------------------------------------#
#       AL_Supervisor
#-----------------------------------------------------------#

class AL_Supervisor(EntityBase):
    """ The entity that acts as a supervisor for the automatic lighting system. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        super().__init__(getLogger(f"{LOGGER_BASE_NAME}.supervisor"))
        self._automations_reloading = False
        self._config = config_entry.options
        self._groups = {}
        self._name = f"{NAME} Supervisor"
        self._remove_listeners = []
        self._restart_timer = None


    #--------------------------------------------#
    #       Properties (HA)
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        return { key: group.state for [key, group] in sorted(self._groups.items(), key=lambda kv: kv[0]) }

    @property
    def name(self) -> str:
        """ Gets the name of entity. """
        return self._name

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether HomeAssistant should automatically poll the entity. """
        return True

    @property
    def state(self) -> bool:
        """ Gets the state of the entity. """
        return f"{len(self._groups)}"

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Properties (HA)
    #--------------------------------------------#

    @property
    def is_restarting(self) -> bool:
        """ Gets a boolean indicating whether the entity is restarting. """
        return self._restart_timer is not None and self._restart_timer.is_running

    @property
    def lights(self) -> List[str]:
        """ Gets the list of lights that used by groups and profiles. """
        return list(set(sum([group.lights for group in self._groups.values()], [])))


    #--------------------------------------------#
    #       Service Methods
    #--------------------------------------------#

    async def async_service_block(self, service_call: ServiceCall) -> None:
        """ Handles a service call to automatic_lighting.block. """
        group = self._groups.get(service_call.data.get(CONF_GROUP, None), None)
        timeout = service_call.data.get(CONF_TIMEOUT, None)

        if not group:
            return

        group.block(timeout)

    async def async_service_register(self, service_call: ServiceCall) -> None:
        """ Handles a service call to automatic_lighting.register. """
        if not self.is_restarting:
            return

        data = { **service_call.data }
        group_id = data.pop(CONF_GROUP)

        if not group_id in self._groups:
            self._groups[group_id] = AL_Group(self.hass, self._config, group_id, lambda: self.async_schedule_update_ha_state(True))

        await self._groups[group_id].add_profile(data)


    #--------------------------------------------#
    #       Init Methods
    #--------------------------------------------#

    def remove_listeners(self, *args: Any) -> None:
        self.logger.debug(f"Removes event listeners and cleans up timers.")

        while self._remove_listeners:
            self._remove_listeners.pop()()

        for group in self._groups:
            group.remove_listeners()

        self._restart_timer and self._restart_timer.cancel()

    def setup_listeners(self, *args: Any) -> None:
        """ Sets up event listeners. """
        self.logger.debug(f"Setting up event listeners.")
        self._remove_listeners.append(async_track_automations_changed(self.hass, self.async_on_automations_changed))
        self._remove_listeners.append(async_call_later(self.hass, START_DELAY, self.restart))


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_on_automations_changed(self, event_type: str, entity_id: str) -> None:
        """ Triggered when the automations have changed (reloaded or turned on/off). """
        self.logger.debug(f"Detected an {event_type} event.")
        self.restart()


    #--------------------------------------------#
    #       Restart Methods
    #--------------------------------------------#

    def restart(self, *args: Any) -> None:
        """ Restarts the supervisor. """
        if self.is_restarting:
            self._restart_timer.cancel()
        else:
            self.logger.debug(f"Restarting automatic lighting. Firing event {EVENT_AUTOMATIC_LIGHTING} (type: {EVENT_TYPE_RESTART}).")
            self.logger.debug(f"{len(self._groups)} groups are being removed.")
            self.logger.debug(f"{len(self.lights)} lights are being untracked.")

            for key in [key for key in self._groups]:
                self._groups[key].remove_listeners()
                del self._groups[key]

            self.fire_event(EVENT_AUTOMATIC_LIGHTING, type=EVENT_TYPE_RESTART)

        def restart():
            self.logger.debug(f"{len(self._groups)} groups have been created.")
            self.logger.debug(f"{len(self.lights)} lights are being tracked for manual control.")

            if len(self._groups) == 0:
                self.logger.debug("No groups were registered.")

            for group_id in self._groups:
                self._groups[group_id].setup_listeners()

            return self.async_schedule_update_ha_state(True)

        self._restart_timer = Timer(self.hass, RESTART_DEBOUNCE_TIME, restart)


#-----------------------------------------------------------#
#       AL_Group
#-----------------------------------------------------------#

class AL_Group(EntityHelpers):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any], id: str, async_update_func: Callable[[bool], None]):
        super().__init__(getLogger(f"{LOGGER_BASE_NAME}.group.{id}"))
        self._async_update_func = async_update_func
        self._block_config_timeout = config.get(CONF_BLOCK_TIMEOUT, DEFAULT_BLOCK_TIMEOUT)
        self._block_timeout = self._block_config_timeout
        self._block_timer = None
        self._hass = hass
        self._id = id
        self._current_ambiance_profile = None
        self._current_triggered_profile = None
        self._current_triggered_profile_timer = None
        self._profiles_ambience = []
        self._profiles_triggered = []
        self._remove_listeners = []
        self._state = STATE_AMBIANCE


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def id(self) -> str:
        """ Gets the id of the group. """
        return self._id

    @property
    def is_blocked(self) -> bool:
        """ Gets a boolean indicating whether the group is blocked. """
        return self._block_timer is not None

    @property
    def lights(self) -> List[str]:
        """ Gets the list of lights associated with the group. """
        return list(set(sum([profile[CONF_LIGHTS] for profile in self._profiles_ambience + self._profiles_triggered], [])))

    @property
    def state(self) -> str:
        """ Gets the state of the group. """
        return self._state

    @property
    def triggers(self) -> List[str]:
        return list(set(sum([profile[CONF_TRIGGERS] for profile in self._profiles_triggered], [])))


    #--------------------------------------------#
    #       Listener Methods
    #--------------------------------------------#

    def remove_listeners(self) -> None:
        """ Removes all event & state listeners. """
        while self._remove_listeners:
            self._remove_listeners.pop()()

        self._block_timer and self._reset_block_timer()
        self._current_triggered_profile and self._reset_current_triggered_profile()

    def setup_listeners(self) -> None:
        self._remove_listeners.append(async_track_state_change(self._hass, self.triggers, self.async_on_trigger_state_change))


    #--------------------------------------------#
    #       Profile Methods
    #--------------------------------------------#

    async def add_profile(self, data: Dict[str, Any]) -> None:
        triggers = await async_resolve_target(self._hass, data.pop(CONF_TRIGGERS))
        lights = await async_resolve_target(self._hass, data.pop(CONF_LIGHTS))

        if CONF_TRIGGERS in data:
            self._profiles_triggered.append({ **data, CONF_TRIGGERS: triggers, CONF_LIGHTS: lights })
        else:
            self._profiles_ambience.append({ **data, CONF_LIGHTS: lights })


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_on_trigger_state_change(self, entity_id: str, old_state: State, new_state: State) -> None:
        if old_state is None or old_state.state == new_state.state:
            return

        if new_state.state == STATE_OFF:
            if self._current_triggered_profile and not self._current_triggered_profile.is_triggered and not self._current_triggered_profile.is_running:
                self._current_triggered_profile.start()
                pass

            return self.update()

        if self.is_blocked:
            return self.block()

        self.update()


    def update(self) -> None:
        if self.is_active and self.is_blocked:
            self._reset_current_triggered_profile()

        if self.is_blocked:
            self._state = STATE_BLOCKED
            return self._async_update_func()

        if self.is_active:
            self._current_triggered_profile.is_running and self._current_triggered_profile.restart()
            return self._async_update_func()

        if self.is_triggered:
            self._set_triggered_profile()
            if self.is_active:
                self._state = STATE_TRIGGERED
                return self._async_update_func()

        self._state = STATE_AMBIANCE
        self._set_ambience_profile()
        return self._async_update_func()


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    # --- Profile ----------
    # ---------------------------------------------

    async def _set_triggered_profile(self) -> None:
        """ Activates a profile. """
        if (profile := self._get_profile(self._active_profiles)) is None:
            if not self.is_active:
                return
            profile = self._current_active_profile.data
            self._reset_current_active_profile()

        self._current_active_profile = Timer(self._hass, profile[CONF_DURATION], self._on_active_profile_finished, data=profile, start=False)
        self.call_service(self._hass, LIGHT_DOMAIN, SERVICE_TURN_ON, **profile[CONF_ATTRIBUTES])

    async def _set_ambiance_profile(self) -> None:
        if (profile := self._get_profile(self._idle_profiles)) is None:
            self._current_idle_profile = None
            return await self._call_service(SERVICE_TURN_OFF, entity_id=self._light_entities)

        #if profile == self._current_idle_profile:
        #    return

        self._current_idle_profile = profile

    def _get_profile(self, profiles: List[Dict[str, Any]]) -> Union[Dict[str, Any], None]:
        """ Attempts to match and return a profile. """
        for profile in profiles:
            if not now_is_between(profile[CONF_AFTER], profile[CONF_BEFORE]):
                continue

            if self._current_illuminance is not None and self._current_illuminance > profile[CONF_ILLUMINANCE]:
                continue

            return profile
        return None

    def _reset_block_timer(self):
        """ Resets the block timer. """
        if self._block_timer:
            self._block_timer.cancel()
            self._block_timer = None

    def _reset_current_triggered_profile(self):
        """ Resets the profile timer. """
        if self._current_triggered_profile:
            self._current_triggered_profile.cancel()
            self._current_triggered_profile = None

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        unused_entities = [entity_id for entity_id in old_entity_ids if entity_id not in new_entity_ids]
        self.call_service(self._hass, LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)




#-----------------------------------------------------------#
#       AL_Profile
#-----------------------------------------------------------#

class AL_Ambiance_Profile(Timer):

    def __init__(self, hass: HomeAssistant, lights: List[str], data: Dict[str, Any], on_profile_finished: Callable[[], None]):
        self._duration = data.pop(CONF_DURATION)
        self._lights = lights
        self._on_pro
        self._time_after = data.pop(CONF_AFTER)
        self._time_before = data.pop(CONF_BEFORE)
        self._triggers = data.pop(CONF_TRIGGERS)
        self._attributes = data

        super().__init__(hass, self._duration, )



class AL_Triggered_Profile(Timer):

    def __init__(self, hass: HomeAssistant, lights: List[str], data: Dict[str, Any], on_profile_finished: Callable[[], None]):
        self._duration = data.pop(CONF_DURATION)
        self._lights = lights
        self._on_pro
        self._time_after = data.pop(CONF_AFTER)
        self._time_before = data.pop(CONF_BEFORE)
        self._triggers = data.pop(CONF_TRIGGERS)
        self._attributes = data

        super().__init__(hass, self._duration, )

