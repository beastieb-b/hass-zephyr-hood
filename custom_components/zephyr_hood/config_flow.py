"""Config flow for Zephyr Range Hood integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .api import ZephyrApiError, ZephyrAuthError, ZephyrClient, ZephyrConnectionError
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
    CONF_MAC_ADDRESS,
    CONF_MODEL_NAME,
    CONF_PASSWORD,
    CONF_SERIAL_NUMBER,
    CONF_SHADOW_COMMAND_SECTION,
    CONF_THING_NAME,
    CONF_USERNAME,
    DOMAIN,
    GEMTEKS_BASE_URL,
    IOT_ENDPOINT,
    SHADOW_COMMAND_SECTION_REPORTED,
    SHADOW_COMMAND_SECTIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ZephyrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zephyr Range Hood."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise config flow."""
        self._username: str = ""
        self._password: str = ""
        self._devices: list[Any] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step – collect credentials.

        Bronze: config-flow, test-before-configure.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            try:
                client = ZephyrClient(
                    username=self._username,
                    password=self._password,
                )
                await self.hass.async_add_executor_job(client.authenticate)
                self._devices = await self.hass.async_add_executor_job(
                    client.get_devices
                )
            except ZephyrAuthError:
                errors["base"] = "invalid_auth"
            except (ZephyrConnectionError, ZephyrApiError):
                _LOGGER.exception("Unexpected error during Zephyr setup")
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    # Only one device – skip device selection step
                    return await self._create_entry(self._devices[0])
                else:
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose which device to add when multiple are found."""
        device_map = {dev.thing_name: dev.model_name for dev in self._devices}

        if user_input is not None:
            chosen = next(
                dev
                for dev in self._devices
                if dev.thing_name == user_input[CONF_THING_NAME]
            )
            return await self._create_entry(chosen)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_THING_NAME): vol.In(device_map),
                }
            ),
        )

    async def _create_entry(self, device: Any) -> ConfigFlowResult:
        """Finalise the config entry for the chosen device.

        Bronze: unique-config-entry – abort if the device is already set up.
        """
        await self.async_set_unique_id(device.mac_address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Zephyr {device.model_name} ({device.serial_number})",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_THING_NAME: device.thing_name,
                CONF_MODEL_NAME: device.model_name,
                CONF_SERIAL_NUMBER: device.serial_number,
                CONF_MAC_ADDRESS: device.mac_address,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication (Silver: reauthentication-flow)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                client = ZephyrClient(
                    username=reauth_entry.data[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
                await self.hass.async_add_executor_job(client.authenticate)
            except ZephyrAuthError:
                errors["base"] = "invalid_auth"
            except (ZephyrConnectionError, ZephyrApiError):
                _LOGGER.exception("Unexpected error during Zephyr reauth")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration (Gold: reconfiguration-flow)."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                client = ZephyrClient(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
                await self.hass.async_add_executor_job(client.authenticate)
            except ZephyrAuthError:
                errors["base"] = "invalid_auth"
            except (ZephyrConnectionError, ZephyrApiError):
                _LOGGER.exception("Unexpected error during Zephyr reconfiguration")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reconfigure_entry.data[CONF_USERNAME],
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ZephyrOptionsFlow:
        """Return the options flow handler."""
        return ZephyrOptionsFlow()


class ZephyrOptionsFlow(OptionsFlow):
    """Handle options for Zephyr Range Hood."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage backend override options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IOT_ENDPOINT,
                        default=opts.get(CONF_IOT_ENDPOINT, IOT_ENDPOINT),
                    ): str,
                    vol.Required(
                        CONF_GEMTEKS_BASE_URL,
                        default=opts.get(CONF_GEMTEKS_BASE_URL, GEMTEKS_BASE_URL),
                    ): str,
                    vol.Required(
                        CONF_COGNITO_USER_POOL_ID,
                        default=opts.get(
                            CONF_COGNITO_USER_POOL_ID, COGNITO_USER_POOL_ID
                        ),
                    ): str,
                    vol.Required(
                        CONF_COGNITO_CLIENT_ID,
                        default=opts.get(CONF_COGNITO_CLIENT_ID, COGNITO_APP_CLIENT_ID),
                    ): str,
                    vol.Required(
                        CONF_COGNITO_CLIENT_SECRET,
                        default=opts.get(
                            CONF_COGNITO_CLIENT_SECRET, COGNITO_APP_CLIENT_SECRET
                        ),
                    ): str,
                    vol.Required(
                        CONF_COGNITO_IDENTITY_POOL_ID,
                        default=opts.get(
                            CONF_COGNITO_IDENTITY_POOL_ID, COGNITO_IDENTITY_POOL_ID
                        ),
                    ): str,
                    vol.Required(
                        CONF_SHADOW_COMMAND_SECTION,
                        default=opts.get(
                            CONF_SHADOW_COMMAND_SECTION,
                            SHADOW_COMMAND_SECTION_REPORTED,
                        ),
                    ): vol.In(SHADOW_COMMAND_SECTIONS),
                }
            ),
        )
