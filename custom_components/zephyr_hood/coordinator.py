"""DataUpdateCoordinator for Zephyr Range Hood integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZephyrApiError, ZephyrAuthError, ZephyrClient, ZephyrDeviceState
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class ZephyrCoordinator(DataUpdateCoordinator[ZephyrDeviceState]):
    """Manage fetching Zephyr device state from the cloud on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZephyrClient,
        thing_name: str,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.thing_name = thing_name

    async def _async_update_data(self) -> ZephyrDeviceState:
        """Fetch latest device state; called by the base class on each poll."""
        try:
            return await self.hass.async_add_executor_job(
                self.client.get_device_state,
                self.thing_name,
            )
        except ZephyrAuthError as err:
            # ConfigEntryAuthFailed triggers a reauthentication flow
            raise ConfigEntryAuthFailed(
                f"Authentication expired for Zephyr device {self.thing_name}: {err}"
            ) from err
        except ZephyrApiError as err:
            raise UpdateFailed(
                f"Error communicating with Zephyr API for {self.thing_name}: {err}"
            ) from err

    async def async_send_command(self, state: dict[str, Any]) -> None:
        """Send a shadow update command and trigger an immediate refresh."""
        try:
            await self.hass.async_add_executor_job(
                self.client.publish_shadow_update,
                self.thing_name,
                state,
            )
        except ZephyrAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication expired when commanding device: {err}"
            ) from err
        except Exception as err:
            _LOGGER.error(
                "Failed to send command %s to %s: %s",
                state,
                self.thing_name,
                err,
            )
            raise

        await self.async_request_refresh()
