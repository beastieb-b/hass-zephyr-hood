"""Switch platform for Zephyr Range Hood integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZephyrData
from .const import STATE_POWER
from .coordinator import ZephyrCoordinator
from .entity import ZephyrEntity

PARALLEL_UPDATES = 1  # Silver: parallel-updates


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZephyrData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zephyr switch entity from a config entry."""
    data: ZephyrData = entry.runtime_data
    async_add_entities([ZephyrPowerSwitch(data.coordinator, entry.entry_id)])


class ZephyrPowerSwitch(ZephyrEntity, SwitchEntity):
    """Switch entity representing the range hood main power.

    When the hood is powered off, the fan and light are also turned off
    by the hardware.  This switch controls the hood power state (0/1).
    """

    _attr_name = "Power"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: ZephyrCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialise the power switch entity."""
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_power"

    @property
    def is_on(self) -> bool:
        """Return True if the hood is powered on."""
        if self.coordinator.data is None:
            return False
        return bool(self.coordinator.data.power)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power on the range hood."""
        await self.coordinator.async_send_command({STATE_POWER: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Power off the range hood."""
        await self.coordinator.async_send_command({STATE_POWER: 0})
