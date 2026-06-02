"""Shared pytest fixtures for Zephyr Range Hood tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zephyr_hood.api import ZephyrDeviceInfo, ZephyrDeviceState
from custom_components.zephyr_hood.const import (
    CONF_MAC_ADDRESS,
    CONF_MODEL_NAME,
    CONF_PASSWORD,
    CONF_SERIAL_NUMBER,
    CONF_THING_NAME,
    CONF_USERNAME,
    DOMAIN,
)

MOCK_THING_NAME = "aabbccddeeff00112233445566778899aabbccdd"
MOCK_MODEL = "ZZ1234AB"
MOCK_SERIAL = "0000000ZZZ"
MOCK_MAC = "00:11:22:33:44:55"
MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "testpassword123"

MOCK_CONFIG_ENTRY_DATA = {
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_THING_NAME: MOCK_THING_NAME,
    CONF_MODEL_NAME: MOCK_MODEL,
    CONF_SERIAL_NUMBER: MOCK_SERIAL,
    CONF_MAC_ADDRESS: MOCK_MAC,
}

MOCK_DEVICE_INFO = ZephyrDeviceInfo(
    thing_name=MOCK_THING_NAME,
    model_name=MOCK_MODEL,
    serial_number=MOCK_SERIAL,
    mac_address=MOCK_MAC,
)

MOCK_DEVICE_STATE = ZephyrDeviceState(
    power=1,
    light=3,
    fan=2,
    is_online=True,
    raw={
        "power": 1,
        "light": 3,
        "fan": 2,
        "isOnline": 1,
        "modelName": MOCK_MODEL,
    },
)

MOCK_DEVICE_STATE_OFF = ZephyrDeviceState(
    power=0,
    light=0,
    fan=0,
    is_online=True,
    raw={"power": 0, "light": 0, "fan": 0, "isOnline": 1},
)


@pytest.fixture
def mock_zephyr_client() -> MagicMock:
    """Return a mocked ZephyrClient."""
    client = MagicMock()
    client.authenticate.return_value = None
    client.get_devices.return_value = [MOCK_DEVICE_INFO]
    client.get_device_state.return_value = MOCK_DEVICE_STATE
    client.publish_shadow_update.return_value = None
    return client


@pytest.fixture
def mock_config_entry(hass):
    """Return a mock ConfigEntry pre-loaded into hass."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Zephyr {MOCK_MODEL} ({MOCK_SERIAL})",
        data=MOCK_CONFIG_ENTRY_DATA,
        entry_id="test_entry_id",
        unique_id=MOCK_MAC,
    )


@pytest.fixture
def mock_device_state() -> ZephyrDeviceState:
    """Return the default mock device state (power/light/fan all on)."""
    return MOCK_DEVICE_STATE


@pytest.fixture
def mock_device_state_off() -> ZephyrDeviceState:
    """Return a mock device state with everything off."""
    return MOCK_DEVICE_STATE_OFF


@pytest.fixture
def mock_device_info() -> ZephyrDeviceInfo:
    """Return mock device discovery info."""
    return MOCK_DEVICE_INFO


@pytest.fixture
def mock_username() -> str:
    """Return the mock username."""
    return MOCK_USERNAME


@pytest.fixture
def mock_password() -> str:
    """Return the mock password."""
    return MOCK_PASSWORD
