"""Tests for Zephyr Range Hood switch platform."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
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


async def _setup_integration(hass, mock_config_entry, mock_zephyr_client):
    """Helper to set up the integration."""
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


async def test_power_switch_on(hass, mock_config_entry, mock_zephyr_client):
    """Power switch is ON when device power == 1."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    switch_entities = hass.states.async_entity_ids(SWITCH_DOMAIN)
    assert len(switch_entities) == 1

    state = hass.states.get(switch_entities[0])
    assert state is not None
    assert state.state == STATE_ON


async def test_power_switch_off(
    hass, mock_config_entry, mock_zephyr_client, mock_device_state_off
):
    """Power switch is OFF when device power == 0."""
    mock_zephyr_client.get_device_state.return_value = mock_device_state_off

    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    switch_entities = hass.states.async_entity_ids(SWITCH_DOMAIN)
    state = hass.states.get(switch_entities[0])
    assert state.state == STATE_OFF


async def test_turn_on_sends_power_1(hass, mock_config_entry, mock_zephyr_client):
    """turn_on service sends power=1 to the device."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    switch_entities = hass.states.async_entity_ids(SWITCH_DOMAIN)

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["power"] == 1


async def test_turn_off_sends_power_0(hass, mock_config_entry, mock_zephyr_client):
    """turn_off service sends power=0 to the device."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    switch_entities = hass.states.async_entity_ids(SWITCH_DOMAIN)

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["power"] == 0
