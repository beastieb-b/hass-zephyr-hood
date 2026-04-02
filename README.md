# hass-zephyr-hood

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant custom integration for [Zephyr range hoods](https://zephyronline.com) with
"Connect" Wi-Fi functionality. Controls your hood through the same AWS IoT cloud the official
app uses, so there is no local API to set up and no reverse-proxy required. Authenticate once
with your Zephyr account and your hood appears as a proper HA device with fan, light, and
power entities.

## Features

- **Fan** — speed control (off + 6 speeds)
- **Light** — brightness control (off + 3 levels)
- **Switch** — main power
- Config flow UI — set up entirely in the HA frontend, no YAML needed
- Works alongside the official Zephyr app

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations** → three-dot menu → **Custom repositories**
2. Add this repo URL, category **Integration**
3. Search for "Zephyr" and install
4. Restart Home Assistant

### Manual

1. Copy `custom_components/zephyr_hood/` into your HA config's `custom_components/` folder
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Zephyr Range Hood**
3. Enter your Zephyr account email and password (same as the mobile app)
4. Your hood(s) will appear as devices automatically

## How It Works

The integration authenticates with AWS Cognito using your Zephyr credentials, then connects to
AWS IoT over MQTT (WebSockets) to publish and subscribe to your hood's device shadow. State
updates from the app or physical controls are reflected in HA in real time.

## Development

```bash
uv sync
uv run pytest
```

Requires Python 3.14+. Dev dependencies (Home Assistant, pytest-homeassistant-custom-component,
ruff, mypy) are declared in `pyproject.toml`.

## Disclaimer

This is an unofficial community integration, not affiliated with or endorsed by Zephyr.
