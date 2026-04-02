"""Tests for Zephyr Range Hood fan platform."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this module."""
    return


FAN_ENTITY_ID = "fan.zephyr_zz1234ab_0000000zzz_fan"


async def _setup_integration(hass, mock_config_entry, mock_zephyr_client):
    """Helper to set up the integration and return the entry."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.coordinator.ZephyrCoordinator"
            "._async_update_data",
            return_value=mock_zephyr_client.get_device_state.return_value,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


async def test_fan_state_on(hass, mock_config_entry, mock_zephyr_client):
    """Fan entity reflects on state when fan speed > 0."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    # MOCK_DEVICE_STATE has fan=2
    fan_entities = hass.states.async_entity_ids(FAN_DOMAIN)
    assert len(fan_entities) == 1

    state = hass.states.get(fan_entities[0])
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["percentage"] == round(2 / 6 * 100)


async def test_fan_state_off(
    hass, mock_config_entry, mock_zephyr_client, mock_device_state_off
):
    """Fan entity reflects off state when fan speed == 0."""
    mock_zephyr_client.get_device_state.return_value = mock_device_state_off

    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    fan_entities = hass.states.async_entity_ids(FAN_DOMAIN)
    state = hass.states.get(fan_entities[0])
    assert state.state == STATE_OFF


async def test_fan_turn_on_calls_api(hass, mock_config_entry, mock_zephyr_client):
    """Calling turn_on publishes the correct shadow update."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    fan_entities = hass.states.async_entity_ids(FAN_DOMAIN)

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["fan"] >= 1


async def test_fan_turn_off_calls_api(hass, mock_config_entry, mock_zephyr_client):
    """Calling turn_off sends fan=0 to the API."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    fan_entities = hass.states.async_entity_ids(FAN_DOMAIN)

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: fan_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["fan"] == 0


async def test_fan_set_percentage(hass, mock_config_entry, mock_zephyr_client):
    """Setting percentage maps to the correct speed level."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    fan_entities = hass.states.async_entity_ids(FAN_DOMAIN)

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: fan_entities[0], ATTR_PERCENTAGE: 50},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    # 50% of 6 = 3
    assert call_args[0][1]["fan"] == 3
