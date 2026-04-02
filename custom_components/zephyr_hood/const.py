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
TOPIC_GET = "$aws/things/{thing}/shadow/get"
TOPIC_GET_ACCEPTED = "$aws/things/{thing}/shadow/get/accepted"
TOPIC_UPDATE_DOCS = "$aws/things/{thing}/shadow/update/documents"

# Device state keys (as used by the MQTT shadow)
STATE_POWER = "power"
STATE_LIGHT = "light"
STATE_FAN = "fan"
STATE_DELAY_TIMER = "setdelaytimer"
STATE_IS_ONLINE = "isOnline"
STATE_MODEL_NAME = "modelName"

# Light levels
LIGHT_OFF = 0
LIGHT_LEVEL_MIN = 1
LIGHT_LEVEL_MAX = 3

# Fan speeds
FAN_OFF = 0
FAN_SPEED_MIN = 1
FAN_SPEED_MAX = 6

# Delay timer choices (seconds) — reserved for future delay-off feature
DELAY_TIMER_OFF = 0
DELAY_TIMER_5_MIN = 300
DELAY_TIMER_10_MIN = 600

# Polling interval
SCAN_INTERVAL_SECONDS = 30

# Manufacturer
MANUFACTURER = "Zephyr"
