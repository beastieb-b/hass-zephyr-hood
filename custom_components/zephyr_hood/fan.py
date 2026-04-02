"""Fan platform for Zephyr Range Hood integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZephyrData
from .const import FAN_OFF, FAN_SPEED_MAX, FAN_SPEED_MIN, STATE_FAN
from .coordinator import ZephyrCoordinator
from .entity import ZephyrEntity

PARALLEL_UPDATES = 1  # Silver: parallel-updates


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZephyrData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zephyr fan entity from a config entry."""
    data: ZephyrData = entry.runtime_data
    async_add_entities([ZephyrFan(data.coordinator, entry.entry_id)])


class ZephyrFan(ZephyrEntity, FanEntity):
    """Fan entity representing the range hood exhaust fan.

    Speed is a percentage (0-100) mapped to discrete levels 0-6.
    Level 0 = off, levels 1-6 = increasing speed.
    """

    _attr_name = "Fan"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_translation_key = "fan"

    def __init__(
        self,
        coordinator: ZephyrCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialise the fan entity."""
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_fan"

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        """Return True if the fan is running at any speed."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.fan > FAN_OFF

    @property
    def percentage(self) -> int | None:
        """Return current fan speed as a percentage."""
        if self.coordinator.data is None:
            return None
        level = self.coordinator.data.fan
        if level == FAN_OFF:
            return 0
        return round(level / FAN_SPEED_MAX * 100)

    @property
    def speed_count(self) -> int:
        """Return the number of discrete speed steps."""
        return FAN_SPEED_MAX

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on, optionally at a given speed percentage."""
        if percentage is not None and percentage > 0:
            level = max(
                FAN_SPEED_MIN,
                math.ceil(percentage / 100 * FAN_SPEED_MAX),
            )
        else:
            level = FAN_SPEED_MIN
        await self.coordinator.async_send_command({STATE_FAN: level})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.coordinator.async_send_command({STATE_FAN: FAN_OFF})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed to a given percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return
        level = max(
            FAN_SPEED_MIN,
            math.ceil(percentage / 100 * FAN_SPEED_MAX),
        )
        await self.coordinator.async_send_command({STATE_FAN: level})
