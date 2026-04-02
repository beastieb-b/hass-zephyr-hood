"""Tests for Zephyr Range Hood config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.zephyr_hood.api import ZephyrAuthError
from custom_components.zephyr_hood.const import DOMAIN
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this module."""
    return


async def test_user_step_single_device(
    hass, mock_zephyr_client, mock_username, mock_password, mock_device_info
):
    """Config flow succeeds and creates an entry for a single device."""
    with (
        patch(
            "custom_components.zephyr_hood.config_flow.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": mock_username,
                "password": mock_password,
            },
        )
        await hass.async_block_till_done()
    expected_title = (
        f"Zephyr {mock_device_info.model_name} ({mock_device_info.serial_number})"
    )
    assert result["title"] == expected_title
    assert result["data"]["username"] == mock_username
    assert result["data"]["thing_name"] == mock_device_info.thing_name


async def test_user_step_invalid_auth(hass, mock_username):
    """Config flow shows error on bad credentials."""
    mock_client = MagicMock()
    mock_client.authenticate.side_effect = ZephyrAuthError("bad creds")

    with patch(
        "custom_components.zephyr_hood.config_flow.ZephyrClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": mock_username, "password": "wrong"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_step_no_devices(hass, mock_username, mock_password):
    """Config flow shows error when account has no devices."""
    mock_client = MagicMock()
    mock_client.authenticate.return_value = None
    mock_client.get_devices.return_value = []

    with patch(
        "custom_components.zephyr_hood.config_flow.ZephyrClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": mock_username, "password": mock_password},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "no_devices"


async def test_unique_config_entry_aborts_duplicate(
    hass, mock_zephyr_client, mock_username, mock_password
):
    """Attempting to add the same device twice aborts the flow."""
    with (
        patch(
            "custom_components.zephyr_hood.config_flow.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
    ):
        # First setup
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": mock_username, "password": mock_password},
        )

        # Second attempt with same device
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"username": mock_username, "password": mock_password},
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_reauth_flow_success(hass, mock_config_entry, mock_zephyr_client):
    """Reauthentication flow succeeds with new password."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.zephyr_hood.config_flow.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
    ):
        result = await mock_config_entry.start_reauth_flow(hass)
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"password": "new_password"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reconfigure_flow_success(
    hass, mock_config_entry, mock_zephyr_client, mock_username
):
    """Reconfigure flow succeeds and updates entry."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.zephyr_hood.config_flow.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
        patch(
            "custom_components.zephyr_hood.ZephyrClient",
            return_value=mock_zephyr_client,
        ),
    ):
        result = await mock_config_entry.start_reconfigure_flow(hass)
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": mock_username, "password": "updated_pass"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
