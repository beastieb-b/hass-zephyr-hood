"""Light platform for Zephyr Range Hood integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from . import ZephyrData
from .const import LIGHT_LEVEL_MAX, LIGHT_LEVEL_MIN, LIGHT_OFF, STATE_LIGHT
from .coordinator import ZephyrCoordinator
from .entity import ZephyrEntity

PARALLEL_UPDATES = 1  # Silver: parallel-updates

# Map HA brightness 0-255 to Zephyr levels 1-3
_BRIGHTNESS_SCALE = (LIGHT_LEVEL_MIN, LIGHT_LEVEL_MAX)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZephyrData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zephyr light entity from a config entry."""
    data: ZephyrData = entry.runtime_data
    async_add_entities([ZephyrLight(data.coordinator, entry.entry_id)])


class ZephyrLight(ZephyrEntity, LightEntity):
    """Light entity representing the range hood under-cabinet lights.

    Brightness maps HA 0-255 to Zephyr light levels 1-3.
    Level 0 means off; levels 1-3 are brightness steps.
    """

    _attr_name = "Light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_translation_key = "light"

    def __init__(
        self,
        coordinator: ZephyrCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialise the light entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry_id}_light"

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        """Return True if the light is on at any level."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.light > LIGHT_OFF

    @property
    def brightness(self) -> int | None:
        """Return current brightness scaled to HA 0-255 range."""
        if self.coordinator.data is None:
            return None
        level = self.coordinator.data.light
        if level == LIGHT_OFF:
            return None
        return value_to_brightness(_BRIGHTNESS_SCALE, level)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on, optionally at a given brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            raw = brightness_to_value(_BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])
            level = min(LIGHT_LEVEL_MAX, max(LIGHT_LEVEL_MIN, round(raw)))
        else:
            # Default to full brightness when no level specified
            level = LIGHT_LEVEL_MAX
        await self.coordinator.async_send_command({STATE_LIGHT: level})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.coordinator.async_send_command({STATE_LIGHT: LIGHT_OFF})
