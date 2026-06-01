"""Zephyr Range Hood integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import ZephyrAuthError, ZephyrClient, ZephyrConnectionError
from .const import (
    COGNITO_APP_CLIENT_ID,
    COGNITO_APP_CLIENT_SECRET,
    COGNITO_IDENTITY_POOL_ID,
    COGNITO_USER_POOL_ID,
    CONF_COGNITO_CLIENT_ID,
    CONF_COGNITO_CLIENT_SECRET,
    CONF_COGNITO_IDENTITY_POOL_ID,
    CONF_COGNITO_USER_POOL_ID,
    CONF_GEMTEKS_BASE_URL,
    CONF_IOT_ENDPOINT,
    CONF_PASSWORD,
    CONF_SHADOW_COMMAND_SECTION,
    CONF_THING_NAME,
    CONF_USERNAME,
    GEMTEKS_BASE_URL,
    IOT_ENDPOINT,
    SHADOW_COMMAND_SECTION_REPORTED,
)
from .coordinator import ZephyrCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SWITCH,
]


@dataclass
class ZephyrData:
    """Runtime data stored on the ConfigEntry."""

    client: ZephyrClient
    coordinator: ZephyrCoordinator


# Convenience type alias used by platforms
ZephyrConfigEntry = ConfigEntry[ZephyrData]


async def async_setup_entry(hass: HomeAssistant, entry: ZephyrConfigEntry) -> bool:
    """Set up Zephyr Range Hood from a config entry.

    Bronze: test-before-setup – we verify connectivity here and raise
    ConfigEntryNotReady / ConfigEntryAuthFailed on failure.
    """
    client = ZephyrClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        iot_endpoint=entry.options.get(CONF_IOT_ENDPOINT, IOT_ENDPOINT),
        gemteks_base_url=entry.options.get(CONF_GEMTEKS_BASE_URL, GEMTEKS_BASE_URL),
        cognito_user_pool_id=entry.options.get(
            CONF_COGNITO_USER_POOL_ID, COGNITO_USER_POOL_ID
        ),
        cognito_app_client_id=entry.options.get(
            CONF_COGNITO_CLIENT_ID, COGNITO_APP_CLIENT_ID
        ),
        cognito_app_client_secret=entry.options.get(
            CONF_COGNITO_CLIENT_SECRET, COGNITO_APP_CLIENT_SECRET
        ),
        cognito_identity_pool_id=entry.options.get(
            CONF_COGNITO_IDENTITY_POOL_ID, COGNITO_IDENTITY_POOL_ID
        ),
        shadow_command_section=entry.options.get(
            CONF_SHADOW_COMMAND_SECTION, SHADOW_COMMAND_SECTION_REPORTED
        ),
    )

    try:
        await hass.async_add_executor_job(client.authenticate)
    except ZephyrAuthError as err:
        raise ConfigEntryAuthFailed(
            f"Invalid credentials for Zephyr account: {err}"
        ) from err
    except ZephyrConnectionError as err:
        raise ConfigEntryNotReady(f"Could not connect to Zephyr cloud: {err}") from err

    coordinator = ZephyrCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
        thing_name=entry.data[CONF_THING_NAME],
    )

    # Perform the first refresh; raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    # Store runtime data (Gold: runtime-data)
    entry.runtime_data = ZephyrData(client=client, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZephyrConfigEntry) -> bool:
    """Unload a config entry (Silver: config-entry-unloading)."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await hass.async_add_executor_job(entry.runtime_data.client.close)
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ZephyrConfigEntry,
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
