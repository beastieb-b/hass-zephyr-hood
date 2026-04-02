"""Tests for Zephyr Range Hood integration setup and teardown."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.zephyr_hood.api import ZephyrAuthError
from homeassistant.config_entries import ConfigEntryState


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this module."""
    return


async def test_setup_entry_success(
    hass, mock_config_entry, mock_zephyr_client, mock_device_state
):
    """Integration sets up successfully with valid credentials."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.coordinator.ZephyrCoordinator"
            "._async_update_data",
            return_value=mock_device_state,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_entry_auth_failure(hass, mock_config_entry):
    """Integration fails gracefully when credentials are invalid."""
    mock_config_entry.add_to_hass(hass)

    mock_bad_client = MagicMock()
    mock_bad_client.authenticate.side_effect = ZephyrAuthError("bad creds")

    with patch(
        "custom_components.zephyr_hood.ZephyrClient",
        return_value=mock_bad_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(
    hass, mock_config_entry, mock_zephyr_client, mock_device_state
):
    """Integration unloads cleanly."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.coordinator.ZephyrCoordinator"
            "._async_update_data",
            return_value=mock_device_state,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
