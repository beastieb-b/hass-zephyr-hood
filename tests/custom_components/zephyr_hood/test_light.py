"""Tests for Zephyr Range Hood light platform."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
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


async def test_light_state_on(hass, mock_config_entry, mock_zephyr_client):
    """Light entity is on when light level > 0."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    light_entities = hass.states.async_entity_ids(LIGHT_DOMAIN)
    assert len(light_entities) == 1

    state = hass.states.get(light_entities[0])
    assert state is not None
    assert state.state == STATE_ON
    # MOCK_DEVICE_STATE has light=3 (max), should map to 255
    assert state.attributes["brightness"] == 255


async def test_light_state_off(
    hass, mock_config_entry, mock_zephyr_client, mock_device_state_off
):
    """Light entity is off when light level == 0."""
    mock_zephyr_client.get_device_state.return_value = mock_device_state_off

    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)

    light_entities = hass.states.async_entity_ids(LIGHT_DOMAIN)
    state = hass.states.get(light_entities[0])
    assert state.state == STATE_OFF


async def test_light_turn_on_full_brightness(
    hass, mock_config_entry, mock_zephyr_client
):
    """turn_on with no kwargs defaults to max brightness (level 3)."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    light_entities = hass.states.async_entity_ids(LIGHT_DOMAIN)

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: light_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["light"] == 3


async def test_light_turn_on_with_brightness(
    hass, mock_config_entry, mock_zephyr_client
):
    """turn_on with brightness maps to correct level."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    light_entities = hass.states.async_entity_ids(LIGHT_DOMAIN)

    # Brightness ~128 (50%) should map to level 2
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: light_entities[0], ATTR_BRIGHTNESS: 128},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["light"] in (1, 2)


async def test_light_turn_off(hass, mock_config_entry, mock_zephyr_client):
    """turn_off sends light=0."""
    await _setup_integration(hass, mock_config_entry, mock_zephyr_client)
    light_entities = hass.states.async_entity_ids(LIGHT_DOMAIN)

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: light_entities[0]},
        blocking=True,
    )

    mock_zephyr_client.publish_shadow_update.assert_called_once()
    call_args = mock_zephyr_client.publish_shadow_update.call_args
    assert call_args[0][1]["light"] == 0
