"""Constants for the Zephyr Range Hood integration."""

from __future__ import annotations

DOMAIN = "zephyr_hood"

# Config entry keys (stored in ConfigEntry.data)
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_THING_NAME = "thing_name"
CONF_MODEL_NAME = "model_name"
CONF_SERIAL_NUMBER = "serial_number"
CONF_MAC_ADDRESS = "mac_address"

# Config entry options keys (overridable backend settings)
CONF_IOT_ENDPOINT = "iot_endpoint"
CONF_GEMTEKS_BASE_URL = "gemteks_base_url"
CONF_COGNITO_USER_POOL_ID = "cognito_user_pool_id"
CONF_COGNITO_CLIENT_ID = "cognito_client_id"
CONF_COGNITO_CLIENT_SECRET = "cognito_client_secret"
CONF_COGNITO_IDENTITY_POOL_ID = "cognito_identity_pool_id"
CONF_SHADOW_COMMAND_SECTION = "shadow_command_section"

# AWS / Zephyr backend (hardcoded from reverse-engineering)
AWS_REGION = "us-west-2"
COGNITO_IDENTITY_POOL_ID = "us-west-2:fb4c1b66-12c2-414b-83a1-a1902f7d98e3"
COGNITO_USER_POOL_ID = "us-west-2_McuoKpkna"
COGNITO_APP_CLIENT_ID = "5a2qiskdvvu7gre1jvbjnunu20"
COGNITO_APP_CLIENT_SECRET = "3b085l2fkgph4kt734k5e26tirb9hjasgb4rn8sjpp4mheo5kga"
IOT_ENDPOINT = "a1nqxu0hki9zw3-ats.iot.us-west-2.amazonaws.com"
GEMTEKS_BASE_URL = "https://zephyr-prod-app.gemteks.com/prod"

# MQTT shadow topics
TOPIC_UPDATE = "$aws/things/{thing}/shadow/update"
TOPIC_UPDATE_ACCEPTED = "$aws/things/{thing}/shadow/update/accepted"
TOPIC_UPDATE_REJECTED = "$aws/things/{thing}/shadow/update/rejected"

# Device state keys (as used by the MQTT shadow)
STATE_POWER = "power"
STATE_LIGHT = "light"
STATE_FAN = "fan"
STATE_IS_ONLINE = "isOnline"
STATE_MODEL_NAME = "modelName"

# Shadow command sections.  Zephyr devices have historically accepted commands
# in "reported"; "desired" is available for backends that follow the standard
# AWS IoT app/device shadow split.
SHADOW_COMMAND_SECTION_REPORTED = "reported"
SHADOW_COMMAND_SECTION_DESIRED = "desired"
SHADOW_COMMAND_SECTIONS = (
    SHADOW_COMMAND_SECTION_REPORTED,
    SHADOW_COMMAND_SECTION_DESIRED,
)

# Light levels
LIGHT_OFF = 0
LIGHT_LEVEL_MIN = 1
LIGHT_LEVEL_MAX = 3

# Fan speeds
FAN_OFF = 0
FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6

# Polling interval
SCAN_INTERVAL_SECONDS = 30

# Manufacturer
MANUFACTURER = "Zephyr"
