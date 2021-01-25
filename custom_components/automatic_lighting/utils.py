#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_DOMAIN, ATTR_ENTITY_ID, ATTR_SERVICE_DATA, EVENT_CALL_SERVICE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.util import get_random_string
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Context
#-----------------------------------------------------------#

class ContextGenerator:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self):
        self._unique_id = get_random_string(6)


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def generate(self) -> Context:
        return Context(id=f"{self._unique_id}{get_random_string(30)}")

    def is_internal(self, context: Context) -> bool:
        return context.id.startswith(self._unique_id)


#-----------------------------------------------------------#
#       ManualControlTracker
#-----------------------------------------------------------#

class ManualControlTracker:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, context: ContextGenerator, entity_ids: List[str] = []):
        self._context = context
        self._entity_ids = entity_ids
        self._hass = hass
        self._listeners = []
        self._remove_listener = hass.bus.async_listen(EVENT_CALL_SERVICE, self._async_on_service_call)


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def destroy(self) -> None:
        self._listeners = []
        self._remove_listener()
        self._remove_listener = None

    def listen(self, listener: Callable[[List[str], Context], None]) -> Callable[[None], None]:
        def remove_listener():
            self._listeners.remove(listener)

        self._listeners.append(listener)
        return remove_listener


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_service_call(self, event: Event) -> None:
        domain = event.data.get(ATTR_DOMAIN, "")

        if domain != LIGHT_DOMAIN:
            return

        service_data = event.data.get(ATTR_SERVICE_DATA)
        entity_ids = [entity_id for entity_id in cv.ensure_list_csv(service_data[ATTR_ENTITY_ID]) if entity_id in self._entity_ids]

        if len(entity_ids) == 0:
            return

        if self._context.is_internal(event.context):
            return

        for listener in self._listeners:
            await listener(entity_ids, event.context)


#-----------------------------------------------------------#
#       Timer
#-----------------------------------------------------------#

class Timer():
    """ A class representing a timer that will execute an action after a delay. """
    #-----------------------------------------------#
    #     Constructor                               #
    #-----------------------------------------------#

    def __init__(self, hass: HomeAssistant, delay: Union[int, None], action: Callable, data: Dict[str, Any] = {}, start: bool = True):
        self._action = action
        self._data = data
        self._delay = delay
        self._hass = hass
        self._remove_listener = None

        if start:
            self.start()


    #-----------------------------------------------#
    #     Properties                                #
    #-----------------------------------------------#

    @property
    def is_running(self) -> bool:
        """ Gets a boolean indicating whether the timer is running. """
        return self._remove_listener is not None


    #-----------------------------------------------#
    #     Methods                                   #
    #-----------------------------------------------#

    def cancel(self) -> None:
        """ Cancels the timer, if it is currently running. """
        if not self.is_running:
            return
        self._remove_listener()
        self._remove_listener = None

    def start(self) -> None:
        """ Starts the timer, if it is not currently running. """
        if self.is_running or self._delay is None:
            return
        self._remove_listener and self._remove_listener()
        self._remove_listener = async_call_later(self._hass, self._delay, self._async_on_timer_finished)

    def restart(self) -> None:
        """ Restarts the timer. """
        self.cancel()
        self.start()


    #-----------------------------------------------#
    #     Event Handlers                            #
    #-----------------------------------------------#

    async def _async_on_timer_finished(self, _):
        """ Triggered when the timer has finished. """
        self._remove_listener = None
        await self._action()