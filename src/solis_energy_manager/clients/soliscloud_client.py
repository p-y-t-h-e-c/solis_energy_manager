"""Client for interacting with the SolisCloud API to retrieve inverter data.

This module implements the HMAC-based request signing scheme required by
the SolisCloud Open API and exposes a small, typed function for pulling the
battery/grid figures needed to decide whether to charge overnight from a
lower-rate grid tariff.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from solis_energy_manager.logger import get_logger
from solis_energy_manager.settings import Settings, get_settings

logger = get_logger(__name__)

_SIGN_METHOD = "POST"
_CONTENT_TYPE = "application/json"


class InverterSnapshot(BaseModel):
    """A single point-in-time reading of inverter/battery/grid state.

    Attributes:
        battery_capacity_soc: Battery state of charge, as a percentage (0-100).
        grid_sell_today_energy: Energy exported to the grid so far today, in kWh.
        battery_today_charge_energy: Energy used to charge the battery so far
            today, in kWh.
    """

    model_config = ConfigDict(frozen=True)

    battery_capacity_soc: float = Field(ge=0, le=100)
    grid_sell_today_energy: float = Field(ge=0)
    battery_today_charge_energy: float = Field(ge=0)


class SolisApiError(RuntimeError):
    """Raised when the SolisCloud API returns an error payload or an
    unexpected/malformed response body."""


def _generate_solis_api_signature(
    *,
    api_id: str,
    api_secret: str,
    body: str,
    solis_api_base: str,
    solis_api_endpoint: str,
) -> dict[str, str]:
    """Build the authentication headers required by the SolisCloud Open API.

    SolisCloud requires each request to be signed with an HMAC-SHA1
    signature over a canonical string built from the HTTP method, an MD5
    digest of the body, the content type, the request date, and the
    request path.

    Args:
        api_id: The SolisCloud API key ID (used as the Authorization key).
        api_secret: The SolisCloud API key secret, used to sign the request.
        body: The raw JSON request body, exactly as it will be sent on the wire.
        solis_api_base: The base path for the SolisCloud API (e.g. "/v1/api/").
        solis_api_endpoint: The API path being called, e.g. "inverterDetail".

    Returns:
        A dict of headers ("Content-MD5", "Content-Type", "Date",
        "Authorization") to attach to the outgoing request.
    """
    # MD5 is required here by the SolisCloud signing spec, not for security
    # purposes -- usedforsecurity=False keeps linters/bandit quiet about it.
    content_md5 = base64.b64encode(
        hashlib.md5(body.encode("utf-8"), usedforsecurity=False).digest()
    ).decode("utf-8")

    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    sign_str = (
        f"{_SIGN_METHOD}\n{content_md5}\n{_CONTENT_TYPE}\n{date}\n"
        f"{solis_api_base}{solis_api_endpoint}"
    )

    sign = base64.b64encode(
        hmac.new(
            api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    return {
        "Content-MD5": content_md5,
        "Content-Type": _CONTENT_TYPE,
        "Date": date,
        "Authorization": f"API {api_id}:{sign}",
    }


def _parse_response(output: dict[str, Any]) -> InverterSnapshot:
    """Validate and extract an ``InverterSnapshot`` from a raw API response.

    SolisCloud signals failure via the HTTP status (handled by
    ``raise_for_status`` before this is called) rather than a body-level
    flag, so this only needs to guard against a 200 response with a
    missing or malformed ``data`` payload.

    Args:
        output: The parsed JSON body returned by the SolisCloud API.

    Returns:
        The extracted InverterSnapshot.

    Raises:
        SolisApiError: If the response is missing or has malformed
            expected fields.
    """
    data = output.get("data")
    if not isinstance(data, dict):
        raise SolisApiError(f"Unexpected SolisCloud response, missing 'data': {output}")

    try:
        return InverterSnapshot(
            battery_capacity_soc=data["batteryCapacitySoc"],
            grid_sell_today_energy=data["gridSellTodayEnergy"],
            battery_today_charge_energy=data["batteryTodayChargeEnergy"],
        )
    except (KeyError, ValidationError) as exc:
        raise SolisApiError(f"Malformed SolisCloud response data: {data}") from exc


def get_data(
    settings: Settings,
    api_endpoint: str,
    api_body_content: dict[str, Any],
) -> InverterSnapshot:
    """Fetch the current battery/grid snapshot for a SolisCloud inverter.

    Retries on transport-level failures (timeouts, connection errors, HTTP
    error status codes) up to ``settings.api_call_attempts`` times, waiting
    ``settings.api_call_delay`` seconds between attempts.

    Args:
        settings: The application settings, providing SolisCloud
            credentials, API endpoints, and retry config.
        api_endpoint: The API path to call, e.g. "inverterDetail".
        api_body_content: The JSON-serialisable request payload, e.g.
            ``{"sn": "<inverter serial number>"}``.

    Returns:
        An InverterSnapshot with the battery state of charge and today's
        grid/battery energy figures.

    Raises:
        SolisApiError: If the API responds with a non-success payload, or
            the response is missing expected fields.
        requests.RequestException: If every retry attempt fails at the
            transport level (network error, timeout, or HTTP error status).
    """
    body = json.dumps(api_body_content)

    headers = _generate_solis_api_signature(
        api_id=settings.solis_key_id.get_secret_value(),
        api_secret=settings.solis_key_secret.get_secret_value(),
        body=body,
        solis_api_base=settings.solis_api_base,
        solis_api_endpoint=api_endpoint,
    )

    url = f"{settings.solis_api_url}{settings.solis_api_base}{api_endpoint}"

    logger.info("Calling SolisCloud API endpoint: %s", url)

    last_error: requests.RequestException | None = None

    for attempt in range(1, settings.api_call_attempts + 1):
        try:
            response = requests.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
            output = response.json()
            return _parse_response(output)

        except requests.RequestException as exc:
            last_error = exc
            logger.error(
                "API call failed on attempt %d/%d: %s",
                attempt,
                settings.api_call_attempts,
                exc,
            )
            if attempt < settings.api_call_attempts:
                logger.info("Retrying after %d seconds...", settings.api_call_delay)
                time.sleep(settings.api_call_delay)

    logger.error("All API call attempts failed.")
    assert last_error is not None  # loop only exits like this after an exception
    raise last_error


def _main() -> None:
    """Manual smoke-test entry point: fetch and log a live inverter snapshot."""
    settings = get_settings()

    api_body_content = {"sn": settings.solis_inverter_sn.get_secret_value()}
    api_endpoint = "inverterDetail"

    snapshot = get_data(
        settings, api_endpoint=api_endpoint, api_body_content=api_body_content
    )

    logger.info("Battery Capacity SOC: %s percent", snapshot.battery_capacity_soc)
    logger.info("Grid Sell Today Energy: %s kWh", snapshot.grid_sell_today_energy)
    logger.info(
        "Battery Today Charge Energy: %s kWh", snapshot.battery_today_charge_energy
    )


if __name__ == "__main__":
    _main()
