from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from typing import Callable, Union

class Timer():
    """ A class representing a timer that will execute an action after a delay. """
    #-----------------------------------------------#
    #     Constructor                               #
    #-----------------------------------------------#

    def __init__(self, hass: HomeAssistant, delay: Union[int, None], action: Callable):
        self._action = action
        self._delay = delay
        self._hass = hass
        self._remove_listener = async_call_later(self._hass, self._delay, self._on_timer_finished)


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
        """ Cancels the timer. """
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None


    #-----------------------------------------------#
    #     Event Handlers                            #
    #-----------------------------------------------#

    def _on_timer_finished(self, _):
        """ Triggered when the timer has finished. """
        self._remove_listener = None
        self._action()