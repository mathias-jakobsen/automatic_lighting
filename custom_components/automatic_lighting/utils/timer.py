#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from typing import Any, Callable, Union


#-----------------------------------------------------------#
#       Timer
#-----------------------------------------------------------#

class Timer():
    """ A class representing a timer that will execute an action after a delay. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, delay: Union[int, None], action: Callable, start: bool = True):
        self._action = action
        self._delay = delay
        self._hass = hass
        self._remove_listener = None

        if start:
            self.start()


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_running(self) -> bool:
        """ Gets a boolean indicating whether the timer is running. """
        return self._remove_listener is not None


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

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


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _on_timer_finished(self, *args: Any) -> None:
        """ Triggered when the timer has finished. """
        self._remove_listener = None
        await self._action()