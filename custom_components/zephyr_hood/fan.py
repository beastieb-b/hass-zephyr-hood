"""Fan platform for Zephyr Range Hood integration."""

from __future__ import annotations

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

_PRESET_MODES = [str(i) for i in range(FAN_SPEED_MIN, FAN_SPEED_MAX + 1)]


def _percentage_to_speed(percentage: int) -> int:
    """Map a 1-100 HA percentage to a Zephyr speed level 1-6.

    Uses rounding for a consistent round-trip with _speed_to_percentage.
    The max(FAN_SPEED_MIN, ...) clamp ensures percentages near 0 still
    produce at least speed 1 (callers guarantee percentage >= 1).
    Examples: 1%→1, 17%→1, 33%→2, 50%→3, 67%→4, 83%→5, 100%→6.
    """
    return min(
        FAN_SPEED_MAX, max(FAN_SPEED_MIN, round(percentage / 100 * FAN_SPEED_MAX))
    )


def _speed_to_percentage(level: int) -> int:
    """Map a Zephyr speed level 1-6 to a 1-100 HA percentage."""
    return round(level / FAN_SPEED_MAX * 100)


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

    Speed is controlled via preset modes 1-6 (exact Zephyr speeds) and
    via HA percentage (mapped to the nearest of the 6 discrete levels) for
    compatibility with standard HA automations and the UI speed slider.
    Level 0 = off.
    """

    _attr_name = "Fan"
    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = _PRESET_MODES
    _attr_translation_key = "fan"

    def __init__(
        self,
        coordinator: ZephyrCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialise the fan entity."""
        super().__init__(coordinator)
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
    def preset_mode(self) -> str | None:
        """Return current fan speed as a preset mode string."""
        if self.coordinator.data is None:
            return None
        level = self.coordinator.data.fan
        if level == FAN_OFF:
            return None
        return str(level)

    @property
    def percentage(self) -> int | None:
        """Return current fan speed as a 0-100 HA percentage."""
        if self.coordinator.data is None:
            return None
        level = self.coordinator.data.fan
        if level == FAN_OFF:
            return 0
        return _speed_to_percentage(level)

    @property
    def percentage_step(self) -> float:
        """Return the step size for percentage-based speed control."""
        return 100 / FAN_SPEED_MAX

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on, optionally at a given preset or percentage speed.

        percentage=0 is treated as speed 1 (minimum), not off.  Use
        async_turn_off or async_set_percentage(0) to stop the fan.
        """
        if preset_mode is not None:
            if preset_mode not in _PRESET_MODES:
                raise ValueError(f"Invalid preset mode: {preset_mode}")
            level = int(preset_mode)
        elif percentage is not None:
            level = _percentage_to_speed(max(1, percentage))
        else:
            level = FAN_SPEED_MIN
        await self.coordinator.async_send_command({STATE_FAN: level})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.coordinator.async_send_command({STATE_FAN: FAN_OFF})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the fan speed to a given preset mode."""
        await self.coordinator.async_send_command({STATE_FAN: int(preset_mode)})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed via HA percentage (0 = off, 1-100 = speed 1-6)."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self.coordinator.async_send_command(
            {STATE_FAN: _percentage_to_speed(percentage)}
        )
