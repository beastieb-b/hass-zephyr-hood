"""Base entity for Zephyr Range Hood integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAC_ADDRESS,
    CONF_MODEL_NAME,
    CONF_SERIAL_NUMBER,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import ZephyrCoordinator


class ZephyrEntity(CoordinatorEntity[ZephyrCoordinator]):
    """Base class for all Zephyr Range Hood entities.

    Inheriting from CoordinatorEntity gives us:
    - Automatic availability tracking (unavailable when coordinator fails)
    - Listener cleanup on unload
    - ``async_write_ha_state`` called on each coordinator refresh
    """

    _attr_has_entity_name = True  # Gold: has-entity-name

    def __init__(
        self,
        coordinator: ZephyrCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        entry = self.coordinator.config_entry  # type: ignore[attr-defined]
        if entry is None:
            raise RuntimeError("ZephyrEntity.device_info called before config_entry is set")
        return DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_MAC_ADDRESS])},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=entry.data.get(CONF_MODEL_NAME),
            serial_number=entry.data.get(CONF_SERIAL_NUMBER),
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator update succeeded and device is online."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.is_online
        )
