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
from logging import getLogger

logger = getLogger(__name__)

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
        self._remove_listener = None


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def listen(self, listener: Callable[[List[str], Context], None]) -> Callable[[None], None]:
        def remove_listener():
            self._listeners.remove(listener)

        self._listeners.append(listener)
        return remove_listener

    def start(self) -> None:
        if self._remove_listener:
            return

        self._remove_listener = self._hass.bus.async_listen(EVENT_CALL_SERVICE, self._on_service_call)

    def stop(self, clear_listeners: bool = False) -> None:
        self._listeners = []

        if not self._remove_listener:
            return

        self._remove_listener()
        self._remove_listener = None


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    def _on_service_call(self, event: Event) -> None:
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
            listener(entity_ids, event.context)


#-----------------------------------------------------------#
#       Profile
#-----------------------------------------------------------#

class Profile:
    #-----------------------------------------------#
    #     Constructor                               #
    #-----------------------------------------------#

    def __init__(self, id: str, type: str, entity_ids: List[str], attributes: Dict[str, Any]):
        self._id = id
        self._type = type
        self._entity_ids = entity_ids
        self._attributes = attributes


    #-----------------------------------------------#
    #     Properties                                #
    #-----------------------------------------------#

    @property
    def attributes(self) -> Dict[str, Any]:
        """ Returns the attributes. """
        return self._attributes

    @property
    def entity_ids(self) -> List[str]:
        """ Returns the entity ids. """
        return self._entity_ids

    @property
    def id(self) -> str:
        """ Returns the id. """
        return self._id

    @property
    def type(self) -> str:
        """ Returns the id. """
        return self._type


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
        self._remove_listener = async_call_later(self._hass, self._delay, self._on_timer_finished)

    def restart(self) -> None:
        """ Restarts the timer. """
        self.cancel()
        self.start()


    #-----------------------------------------------#
    #     Event Handlers                            #
    #-----------------------------------------------#

    def _on_timer_finished(self, _):
        """ Triggered when the timer has finished. """
        self._remove_listener = None
        self._action()