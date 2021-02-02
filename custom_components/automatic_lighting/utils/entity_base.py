#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from .entity_helpers import EntityHelpers
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.template import is_template_string, Template
from homeassistant.util import get_random_string
from logging import Logger
from typing import Any, Dict


#-----------------------------------------------------------#
#       Class - EntityBase
#-----------------------------------------------------------#

class EntityBase(Entity, EntityHelpers):
    """ Provides a set of base functions for an entity. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, logger: Logger):
        EntityHelpers.__init__(self, logger)


    #--------------------------------------------#
    #       HA Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        if self.hass.is_running:
            self.setup_listeners()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self.setup_listeners)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        self.remove_listeners()


    #--------------------------------------------#
    #       Init Methods
    #--------------------------------------------#

    def remove_listeners(self, *args: Any) -> None:
        pass

    def setup_listeners(self, *args: Any) -> None:
        pass


    #--------------------------------------------#
    #       Action Methods
    #--------------------------------------------#

    def call_service(self, domain: str, service: str, **service_data: Any):
        """ Calls a service. """
        context = self.create_context()
        self.async_set_context(context)
        super().call_service(self.hass, domain, service, context, **service_data)

    def fire_event(self, event_type: str, **event_data: Any):
        """ Fires an event using the Home Assistant bus. """
        context = self.create_context()
        self.async_set_context(context)
        super().fire_event(self.hass, event_type, context, **event_data)