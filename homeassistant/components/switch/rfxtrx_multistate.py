"""
homeassistant.components.switch.rfxtrx_multistate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for RFXtrx switches with multiple states
   - e.g. LightwaveRF Mood Switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rfxtrx_multistate/
"""
import logging
import homeassistant.components.rfxtrx as rfxtrx

from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.components.rfxtrx import ATTR_STATE, ATTR_FIREEVENT, ATTR_PACKETID, \
    ATTR_NAME, EVENT_BUTTON_PRESSED


DEPENDENCIES = ['rfxtrx']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Setup the RFXtrx platform. """
    import RFXtrx as rfxtrxmod

    # Add switch from config file
    switches = []
    devices = config.get('devices')
    if devices:
        for entity_id, entity_info in devices.items():
            if entity_id not in rfxtrx.RFX_DEVICES:
                _LOGGER.info("Add %s rfxtrx_multistate.switch",
                             entity_info[ATTR_NAME])

                # Check if i must fire event
                fire_event = entity_info.get(ATTR_FIREEVENT, False)
                datas = {ATTR_STATE: STATE_UNKNOWN, ATTR_FIREEVENT: fire_event}

                rfxobject = rfxtrx.get_rfx_object(entity_info[ATTR_PACKETID])
                newswitch = RfxtrxMultiStateSwitch(
                    entity_info[ATTR_NAME], rfxobject, datas)
                rfxtrx.RFX_DEVICES[entity_id] = newswitch
                switches.append(newswitch)

    add_devices_callback(switches)

    def multistate_switch_update(event):
        """ Callback for multistate switch updates from the RFXtrx gateway. """
        if not isinstance(event.device, rfxtrxmod.LightingDevice):
            return

        entity_id = slugify(event.device.id_string.lower())

        # Check if entity exists or previously added automatically
        if entity_id in rfxtrx.RFX_DEVICES \
                and isinstance(rfxtrx.RFX_DEVICES[entity_id],
                               RfxtrxMultiStateSwitch):
            _LOGGER.info(
                "EntityID: %s switch_update. Command: %s",
                entity_id,
                event.values['Command']
            )

            # Update the rfxtrx device state
            # pylint: disable=protected-access
            rfxtrx.RFX_DEVICES[entity_id]._state = \
                event.values['Command'].lower()
            rfxtrx.RFX_DEVICES[entity_id].update_ha_state()

            # Fire event
            if rfxtrx.RFX_DEVICES[entity_id].should_fire_event:
                rfxtrx.RFX_DEVICES[entity_id].hass.bus.fire(
                    EVENT_BUTTON_PRESSED, {
                        ATTR_ENTITY_ID:
                            rfxtrx.RFX_DEVICES[entity_id].entity_id,
                        ATTR_STATE: event.values['Command'].lower()
                    }
                )

    # Subscribe to main rfxtrx events
    if multistate_switch_update not in rfxtrx.RECEIVED_EVT_SUBSCRIBERS:
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS.append(multistate_switch_update)


class RfxtrxMultiStateSwitch(Entity):
    """ Provides a RFXtrx multistate switch. """
    def __init__(self, name, event, datas):
        self._name = name
        self._event = event
        self._state = datas[ATTR_STATE]
        self._should_fire_event = datas[ATTR_FIREEVENT]

    @property
    def should_poll(self):
        """ No polling needed for a RFXtrx switch. """
        return False

    @property
    def state(self):
        """ Returns the state of the device if any. """
        return self._state

    @property
    def name(self):
        """ Returns the name of the device if any. """
        return self._name

    @property
    def should_fire_event(self):
        """ Returns is the device must fire event"""
        return self._should_fire_event
