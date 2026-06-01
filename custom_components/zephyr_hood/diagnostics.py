"""Diagnostics support for Zephyr Range Hood integration.

Gold: diagnostics – provides a structured data dump useful for support.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import ZephyrData
from .const import (
    CONF_MAC_ADDRESS,
    CONF_PASSWORD,
    CONF_SERIAL_NUMBER,
    CONF_THING_NAME,
    CONF_USERNAME,
)

TO_REDACT = {
    CONF_MAC_ADDRESS,
    CONF_PASSWORD,
    CONF_SERIAL_NUMBER,
    CONF_THING_NAME,
    CONF_USERNAME,
    "AccessKeyId",
    "MAC",
    "SN",
    "SecretKey",
    "SessionToken",
    "access_key",
    "authorization",
    "id_token",
    "mac",
    "secret_key",
    "serial",
    "serialNumber",
    "session_token",
    "thingName",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[ZephyrData],
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data: ZephyrData = entry.runtime_data
    coordinator_data = data.coordinator.data

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "last_update_success": (data.coordinator.last_update_success),
            "device_state": (
                {
                    "power": coordinator_data.power,
                    "light": coordinator_data.light,
                    "fan": coordinator_data.fan,
                    "is_online": coordinator_data.is_online,
                    "raw": async_redact_data(coordinator_data.raw, TO_REDACT),
                }
                if coordinator_data
                else None
            ),
        },
    }
