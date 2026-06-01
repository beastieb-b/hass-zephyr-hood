"""Pure-Python API client for Zephyr range hoods.

All external I/O lives here so the rest of the integration only talks to
this module, keeping Home Assistant code clean and testable.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import datetime
import json
import logging
import ssl
import threading
from typing import Any
import uuid

from awscrt import auth, io, mqtt
from awsiot import mqtt_connection_builder
import boto3
import niquests
from niquests.adapters import HTTPAdapter
from pycognito import Cognito

from .const import (
    AWS_REGION,
    COGNITO_APP_CLIENT_ID,
    COGNITO_APP_CLIENT_SECRET,
    COGNITO_IDENTITY_POOL_ID,
    COGNITO_USER_POOL_ID,
    FAN_SPEED_MAX,
    GEMTEKS_BASE_URL,
    IOT_ENDPOINT,
    LIGHT_LEVEL_MAX,
    SHADOW_COMMAND_SECTION_REPORTED,
    SHADOW_COMMAND_SECTIONS,
    STATE_FAN,
    STATE_IS_ONLINE,
    STATE_LIGHT,
    STATE_MODEL_NAME,
    STATE_POWER,
    TOPIC_GET,
    TOPIC_GET_ACCEPTED,
    TOPIC_UPDATE,
    TOPIC_UPDATE_ACCEPTED,
    TOPIC_UPDATE_REJECTED,
)

_LOGGER = logging.getLogger(__name__)


class ZephyrAuthError(Exception):
    """Raised when authentication fails."""


class ZephyrConnectionError(Exception):
    """Raised when the device cannot be reached."""


class ZephyrApiError(Exception):
    """Raised when an API call returns an unexpected error."""


class _LaxSSLAdapter(HTTPAdapter):
    """HTTPAdapter that relaxes VERIFY_X509_STRICT for the Gemteks API.

    Gemteks' TLS certificate is missing the Subject Key Identifier extension
    (RFC 5280 §4.2.1.2).  Python 3.13+ / OpenSSL 3.3+ reject these certs by
    default via VERIFY_X509_STRICT.  This adapter clears that flag while
    keeping full hostname + CA-chain verification intact.
    """

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Create pool manager with a permissive SSL context."""
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


@dataclass
class ZephyrDeviceInfo:
    """Static information about a discovered Zephyr device."""

    thing_name: str
    model_name: str
    serial_number: str
    mac_address: str


@dataclass
class ZephyrDeviceState:
    """Current runtime state of a Zephyr device."""

    power: int  # 0 = off, 1 = on
    light: int  # 0-3
    fan: int  # 0-6
    is_online: bool
    raw: dict[str, Any]

    def __post_init__(self) -> None:
        """Clamp state values to their valid device ranges."""
        self.power = max(0, min(1, self.power))
        self.light = max(0, min(LIGHT_LEVEL_MAX, self.light))
        self.fan = max(0, min(FAN_SPEED_MAX, self.fan))


class ZephyrClient:
    """Unified API client – handles auth, device discovery and control."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        iot_endpoint: str = IOT_ENDPOINT,
        gemteks_base_url: str = GEMTEKS_BASE_URL,
        cognito_user_pool_id: str = COGNITO_USER_POOL_ID,
        cognito_app_client_id: str = COGNITO_APP_CLIENT_ID,
        cognito_app_client_secret: str = COGNITO_APP_CLIENT_SECRET,
        cognito_identity_pool_id: str = COGNITO_IDENTITY_POOL_ID,
        shadow_command_section: str = SHADOW_COMMAND_SECTION_REPORTED,
    ) -> None:
        """Initialize the client with Cognito user credentials."""
        if shadow_command_section not in SHADOW_COMMAND_SECTIONS:
            raise ValueError(
                f"Unsupported shadow command section: {shadow_command_section}"
            )
        self._username = username
        self._password = password
        self._iot_endpoint = iot_endpoint
        self._gemteks_base_url = gemteks_base_url
        self._cognito_user_pool_id = cognito_user_pool_id
        self._cognito_app_client_id = cognito_app_client_id
        self._cognito_app_client_secret = cognito_app_client_secret
        self._cognito_identity_pool_id = cognito_identity_pool_id
        self._shadow_command_section = shadow_command_section
        # Derived from pool ID – must stay in sync with the user pool region
        self._cognito_logins_key = (
            f"cognito-idp.{AWS_REGION}.amazonaws.com/{cognito_user_pool_id}"
        )
        self._id_token: str | None = None
        self._aws_creds: dict[str, str] | None = None
        self._token_expiry: datetime.datetime | None = None
        self._session_cache: niquests.Session | None = None
        self._auth_lock = threading.Lock()
        self._session_lock = threading.Lock()
        # CRT resources created once per client and reused across MQTT calls
        self._mqtt_evg = io.EventLoopGroup(1)
        self._mqtt_resolver = io.DefaultHostResolver(self._mqtt_evg)
        self._mqtt_bootstrap = io.ClientBootstrap(self._mqtt_evg, self._mqtt_resolver)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_session(self) -> niquests.Session:
        """Return (and lazily create) the shared niquests session.

        Deferred to first use so ``ssl.create_default_context()`` is never
        called on the event loop thread – it only runs inside
        ``async_add_executor_job``.

        Returns:
            Shared session mounted with the lax-SSL adapter.
        """
        with self._session_lock:
            if self._session_cache is None:
                session = niquests.Session()
                session.mount("https://", _LaxSSLAdapter())
                self._session_cache = session
            return self._session_cache

    def close(self) -> None:
        """Close the cached HTTP session, if one has been created."""
        if self._session_cache is not None:
            self._session_cache.close()
            self._session_cache = None

    def authenticate(self) -> None:
        """Authenticate with Cognito SRP and obtain temporary AWS credentials.

        Performs a two-phase exchange: first trades ``username``/``password``
        for a Cognito ID token, then trades that token for short-lived AWS STS
        credentials used to sign IoT/MQTT requests.  The credential expiry
        timestamp is stored for proactive renewal by ``_ensure_authenticated``.

        Raises:
            ZephyrAuthError: If the Cognito or STS exchange fails for any
                reason.
        """
        try:
            cognito = Cognito(
                user_pool_id=self._cognito_user_pool_id,
                client_id=self._cognito_app_client_id,
                client_secret=self._cognito_app_client_secret,
                user_pool_region=AWS_REGION,
                username=self._username,
            )
            cognito.authenticate(password=self._password)
            self._id_token = cognito.id_token
        except Exception as err:
            raise ZephyrAuthError(
                f"Authentication failed for {self._username}: {err}"
            ) from err

        try:
            ident = boto3.client("cognito-identity", region_name=AWS_REGION)
            identity_id = ident.get_id(
                IdentityPoolId=self._cognito_identity_pool_id,
                Logins={self._cognito_logins_key: self._id_token},
            )["IdentityId"]
            creds = ident.get_credentials_for_identity(
                IdentityId=identity_id,
                Logins={self._cognito_logins_key: self._id_token},
            )["Credentials"]
            self._aws_creds = {
                "access_key": creds["AccessKeyId"],
                "secret_key": creds["SecretKey"],
                "session_token": creds["SessionToken"],
            }
            # boto3 returns a timezone-aware datetime; store it so we can
            # proactively refresh before it expires.
            self._token_expiry = creds.get("Expiration")
        except Exception as err:
            raise ZephyrAuthError(f"Failed to obtain AWS credentials: {err}") from err

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def get_devices(self) -> list[ZephyrDeviceInfo]:
        """Return all devices registered to this account.

        Returns:
            List of device info objects for every hood on the account.

        Raises:
            ZephyrAuthError: If credentials are absent or cannot be refreshed.
            ZephyrApiError: If the ``/getowndevices`` API call fails.
        """
        self._ensure_authenticated()
        try:
            resp = self._get_session().post(
                f"{self._gemteks_base_url}/getowndevices",
                headers=self._api_headers(),
                json={},
                timeout=10,
            )
            resp.raise_for_status()
        except niquests.RequestException as err:
            raise ZephyrApiError(f"Failed to list devices: {err}") from err

        devices = []
        for dev in resp.json().get("devices", []):
            thing_name = dev.get("thingName")
            if not thing_name:
                _LOGGER.warning(
                    "Skipping device with missing thingName: %s", list(dev.keys())
                )
                continue
            devices.append(
                ZephyrDeviceInfo(
                    thing_name=thing_name,
                    model_name=dev.get(STATE_MODEL_NAME, ""),
                    serial_number=dev.get("SN", ""),
                    mac_address=dev.get("MAC", ""),
                )
            )
        return devices

    def get_device_state(self, thing_name: str) -> ZephyrDeviceState:
        """Fetch current device state via the Gemteks REST API.

        This is the method called by the coordinator on every poll cycle.

        Args:
            thing_name: AWS IoT thing name that identifies the device.

        Returns:
            Current power, fan, and light state of the device.

        Raises:
            ZephyrAuthError: If credentials are absent or cannot be refreshed.
            ZephyrApiError: If the ``/discoverdevice`` API call fails.
        """
        self._ensure_authenticated()
        try:
            resp = self._get_session().post(
                f"{self._gemteks_base_url}/discoverdevice",
                headers=self._api_headers(),
                json={"thingName": thing_name},
                timeout=10,
            )
            resp.raise_for_status()
        except niquests.RequestException as err:
            raise ZephyrApiError(
                f"Failed to get device state for {thing_name}: {err}"
            ) from err

        data = resp.json()
        try:
            return ZephyrDeviceState(
                power=int(data.get(STATE_POWER, 0)),
                light=int(data.get(STATE_LIGHT, 0)),
                fan=int(data.get(STATE_FAN, 0)),
                is_online=self._parse_bool(data.get(STATE_IS_ONLINE, False)),
                raw=data,
            )
        except (ValueError, TypeError) as err:
            raise ZephyrApiError(
                f"Unexpected device state format from {thing_name}: {err}"
            ) from err

    # ------------------------------------------------------------------
    # Device control (MQTT)
    # ------------------------------------------------------------------

    def publish_shadow_update(
        self,
        thing_name: str,
        state: dict[str, Any],
        timeout_s: int = 10,
    ) -> None:
        """Publish an AWS IoT Device Shadow update to control the device.

        Writes ``state`` into the configured shadow command section via MQTT
        and waits for AWS IoT to accept or reject the update.  A fresh
        MQTT-over-WebSocket connection is opened, used, and torn down for each
        call.

        Args:
            thing_name: AWS IoT thing name that identifies the device.
            state: Key/value pairs to write into the configured shadow command
                section (e.g. ``{"fan": 3, "light": 1}``).
            timeout_s: Seconds to wait for the shadow update acknowledgement.

        Raises:
            ZephyrAuthError: If credentials are absent or cannot be refreshed.
            ZephyrConnectionError: If the MQTT connection, publish, or shadow
                acknowledgement fails.
        """
        self._ensure_authenticated()

        conn = self._build_mqtt_connection()
        ack_event = threading.Event()
        ack: dict[str, Any] = {}

        def _on_ack(topic: str, payload: bytes, **_kwargs: Any) -> None:
            try:
                data = json.loads(payload.decode("utf-8"))
            except Exception:  # noqa: BLE001
                data = {"raw": payload.decode("utf-8", errors="replace")}
            ack["topic"] = topic
            ack["payload"] = data
            ack_event.set()

        try:
            conn.connect().result(timeout=15)
            topic_accepted = TOPIC_UPDATE_ACCEPTED.format(thing=thing_name)
            topic_rejected = TOPIC_UPDATE_REJECTED.format(thing=thing_name)
            conn.subscribe(
                topic=topic_accepted,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=_on_ack,
            )[0].result(timeout=10)
            conn.subscribe(
                topic=topic_rejected,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=_on_ack,
            )[0].result(timeout=10)

            payload = json.dumps(
                {"state": {self._shadow_command_section: state}},
                separators=(",", ":"),
            ).encode("utf-8")
            topic = TOPIC_UPDATE.format(thing=thing_name)
            fut, _ = conn.publish(
                topic=topic, payload=payload, qos=mqtt.QoS.AT_LEAST_ONCE
            )
            fut.result(timeout=10)

            self._raise_for_shadow_update_ack(
                ack_event,
                ack,
                topic_rejected,
                thing_name,
                timeout_s,
            )

            _LOGGER.debug(
                "Shadow %s-state update accepted for %s: %s",
                self._shadow_command_section,
                thing_name,
                sorted(state),
            )
        except Exception as err:
            if isinstance(err, ZephyrConnectionError):
                raise
            raise ZephyrConnectionError(
                f"MQTT publish failed for {thing_name}: {err}"
            ) from err
        finally:
            with contextlib.suppress(Exception):
                conn.disconnect().result(timeout=10)

    def get_shadow_state(self, thing_name: str, timeout_s: int = 5) -> dict[str, Any]:
        """Get current device shadow state via MQTT.

        More real-time than the REST poll: subscribes to the
        ``shadow/get/accepted`` topic, publishes an empty message to
        ``shadow/get`` to trigger AWS to respond, then waits for the reply.

        Args:
            thing_name: AWS IoT thing name that identifies the device.
            timeout_s: Seconds to wait for the shadow response before raising
                a ``ZephyrConnectionError``.

        Returns:
            Parsed shadow document returned by AWS IoT.

        Raises:
            ZephyrAuthError: If credentials are absent or cannot be refreshed.
            ZephyrConnectionError: If the MQTT subscribe/get fails or the
                response does not arrive within ``timeout_s`` seconds.
        """
        self._ensure_authenticated()

        conn = self._build_mqtt_connection()
        got: dict[str, Any] = {}
        done = threading.Event()

        def _on_msg(_topic: str, payload: bytes, **_kwargs: Any) -> None:
            nonlocal got
            try:
                got = json.loads(payload.decode("utf-8"))
            except Exception:  # noqa: BLE001
                got = {"raw": payload.decode("utf-8", errors="replace")}
            done.set()

        try:
            conn.connect().result(timeout=15)
            topic_accepted = TOPIC_GET_ACCEPTED.format(thing=thing_name)
            topic_get = TOPIC_GET.format(thing=thing_name)
            conn.subscribe(
                topic=topic_accepted,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=_on_msg,
            )[0].result(timeout=10)
            fut, _ = conn.publish(
                topic=topic_get, payload=b"{}", qos=mqtt.QoS.AT_LEAST_ONCE
            )
            fut.result(timeout=10)

            done.wait(timeout_s)
        except Exception as err:
            raise ZephyrConnectionError(
                f"MQTT get failed for {thing_name}: {err}"
            ) from err
        finally:
            with contextlib.suppress(Exception):
                conn.disconnect().result(timeout=10)

        if not done.is_set():
            raise ZephyrConnectionError(
                f"Timed out waiting for shadow state from {thing_name}"
            )
        return got

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_authenticated(self) -> None:
        """Re-authenticate if tokens are absent or within 5 minutes of expiry."""
        # Fast path: skip lock acquisition when credentials are valid
        now = datetime.datetime.now(tz=datetime.UTC)
        if self._id_token and self._aws_creds:
            expiring_soon = (
                self._token_expiry is not None
                and now >= self._token_expiry - datetime.timedelta(minutes=5)
            )
            if not expiring_soon:
                return

        # Slow path: acquire lock and recheck before making network calls so
        # concurrent callers don't each trigger a full re-auth round-trip
        with self._auth_lock:
            now = datetime.datetime.now(tz=datetime.UTC)
            expiring_soon = (
                self._token_expiry is not None
                and now >= self._token_expiry - datetime.timedelta(minutes=5)
            )
            if self._id_token and self._aws_creds and not expiring_soon:
                return
            _LOGGER.debug(
                "Cognito credentials %s; re-authenticating",
                "expiring soon" if expiring_soon else "not present",
            )
            self.authenticate()

    def _api_headers(self) -> dict[str, str]:
        """Build HTTP headers required by the Gemteks REST API.

        Returns:
            Headers dict containing JSON content-type and the Cognito ID token
            as the ``Authorization`` value.
        """
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": self._id_token or "",
        }

    @staticmethod
    def _raise_for_shadow_update_ack(
        ack_event: threading.Event,
        ack: dict[str, Any],
        topic_rejected: str,
        thing_name: str,
        timeout_s: int,
    ) -> None:
        """Raise when AWS IoT does not accept a shadow update."""
        if not ack_event.wait(timeout_s):
            raise ZephyrConnectionError(
                f"Timed out waiting for shadow update acknowledgement from {thing_name}"
            )
        if ack.get("topic") == topic_rejected:
            err_payload = ack.get("payload", {})
            raise ZephyrConnectionError(
                f"Shadow update rejected for {thing_name}: {err_payload}"
            )

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse boolean-ish values returned by the Gemteks API."""
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _require_aws_credentials(self) -> dict[str, str]:
        """Return current AWS credentials or raise a real runtime error."""
        if self._aws_creds is None:
            raise ZephyrAuthError("Missing AWS credentials; authentication is required")
        return self._aws_creds

    def _build_mqtt_connection(self) -> mqtt.Connection:
        """Build a signed MQTT-over-WebSocket connection using current STS credentials.

        A new connection object is constructed on every call; the caller is
        responsible for ``connect()``, using, and ``disconnect()``-ing it.

        Returns:
            Configured but not yet connected MQTT connection.
        """
        aws_creds = self._require_aws_credentials()
        provider = auth.AwsCredentialsProvider.new_static(
            access_key_id=aws_creds["access_key"],
            secret_access_key=aws_creds["secret_key"],
            session_token=aws_creds["session_token"],
        )
        return mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=self._iot_endpoint,
            region=AWS_REGION,
            credentials_provider=provider,
            client_bootstrap=self._mqtt_bootstrap,
            client_id=f"hass-zephyr-{uuid.uuid4().hex}",
            clean_session=True,
            keep_alive_secs=30,
        )
