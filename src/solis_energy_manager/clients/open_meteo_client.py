"""Client for the Open-Meteo forecast API.

Fetches tomorrow's solar-related forecast (sunshine duration, UV index,
direct radiation) used to judge how much the panels are likely to
contribute, and therefore whether an overnight grid charge is worth it.

Requests a single explicit date via Open-Meteo's start_date/end_date
parameters rather than a day count, so the response only ever contains the
one day actually needed -- no filtering of unwanted days required downstream.

Retries are handled by urllib3's Retry/HTTPAdapter (shipped with requests,
so no extra dependency): transient failures (connection errors, 429, 5xx)
are retried with exponential backoff and Retry-After support, while
non-retryable 4xx client errors fail immediately instead of being retried
uselessly.
"""

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from solis_energy_manager.logger import get_logger
from solis_energy_manager.settings import get_settings

logger = get_logger(__name__)

_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
_REQUEST_TIMEOUT_SECONDS = 30


class DailyForecast(BaseModel):
    """Solar forecast summary for a single day.

    Attributes:
        day: The calendar date the values apply to.
        sunshine_duration_s: Forecast of sunshine for a day in seconds
        (WMO definition: direct normal irradiance above 120 W/m2).
        uv_index_max: Forecast maximum UV index for the day.
    """

    model_config = ConfigDict(frozen=True)

    day: date
    sunshine_duration_s: float = Field(ge=0)
    uv_index_max: float = Field(ge=0)

    @property
    def sunshine_hours(self) -> float:
        """Forecast hours of sunshine for the day."""
        return self.sunshine_duration_s / 3600


class HourlyForecast(BaseModel):
    """Forecast direct solar radiation and sunshine for a single hour.

    Attributes:
        time: Start of the hour, in the timezone requested from the API.
        direct_radiation_wm2: Mean direct radiation on the horizontal plane
            over the preceding hour, in W/m2.
        sunshine_duration_s: Forecast seconds of sunshine within each hour
            (WMO definition: direct normal irradiance above 120 W/m2, same
            basis as the daily total but scoped to one hour).
    """

    model_config = ConfigDict(frozen=True)

    time: datetime
    direct_radiation_wm2: float = Field(ge=0)
    sunshine_duration_s: float = Field(ge=0, le=3600)
    uv_index: float = Field(ge=0)

    @property
    def sunshine_hours(self) -> float:
        """Forecast hours of sunshine within an hour."""
        return self.sunshine_duration_s / 3600


class SolarForecast(BaseModel):
    """Solar forecast for one location.

    Attributes:
        daily: The day's summary.
        hourly: One entry per hour of the day, in chronological order.
    """

    model_config = ConfigDict(frozen=True)

    daily: DailyForecast
    hourly: list[HourlyForecast]

    def hourly_before_cutoff(self, cutoff_hour: int) -> list[HourlyForecast]:
        """Return a day's hourly readings up to (excluding) a cutoff hour.

        Args:
            cutoff_hour: The hour (0-23, local to the forecast's timezone)
                up to which the reading will be conducted; hours at or
                after this are excluded.

        Returns:
            The matching hourly readings, in chronological order.
        """
        return [reading for reading in self.hourly if reading.time.hour < cutoff_hour]

    def sunshine_hours_before_cutoff(self, cutoff_hour: int) -> float:
        """Total forecast sunshine hours for a day, up to a cutoff hour.

        The single number this exists for: "how many hours of sunshine are
        expected by, e.g. 1pm/2pm", directly comparable to the daily sunshine
        total but scoped to the window that actually reaches an east-facing
        panel.

        Args:
            cutoff_hour: The hour (0-23, local to the forecast's timezone)
                up to which the reading will be conducted; hours at or
                after this are excluded.

        Returns:
            Summed sunshine hours across the matching hourly readings.
        """
        return sum(
            reading.sunshine_hours for reading in self.hourly_before_cutoff(cutoff_hour)
        )


class OpenMeteoError(RuntimeError):
    """Raised when the Open-Meteo response is an error or is malformed."""


def _build_session(retries: int, backoff_factor: float) -> requests.Session:
    """Create a ``requests`` session that retries transient failures.

    Retries connection errors and the status codes in ``_RETRY_STATUS_CODES``
    with exponential backoff, honouring any ``Retry-After`` header. Other
    4xx responses (e.g. a malformed request) are not retried, since they
    will fail identically on every attempt.

    Args:
        retries: Maximum number of retries per request.
        backoff_factor: Base for exponential backoff between retries, in seconds.

    Returns:
        A configured ``requests.Session``.
    """
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=_RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _parse_response(output: dict[str, Any]) -> SolarForecast:
    """Validate and convert a raw Open-Meteo JSON body into a ``SolarForecast``.

    Args:
        output: The parsed JSON body returned by the API.

    Returns:
        The validated forecast, covering the single requested day.

    Raises:
        OpenMeteoError: If the body is an API error, is missing or has
            mismatched ``daily``/``hourly`` arrays, or the ``daily`` arrays
            don't contain exactly one day.
    """
    if output.get("error"):
        raise OpenMeteoError(f"Open-Meteo returned an error: {output.get('reason')}")

    try:
        daily = output["daily"]
        hourly = output["hourly"]

        if not (
            len(daily["time"])
            == len(daily["sunshine_duration"])
            == len(daily["uv_index_max"])
            == 1
        ):
            raise OpenMeteoError(
                f"Expected exactly one daily entry, got: {daily['time']}"
            )
        if not (
            len(hourly["time"])
            == len(hourly["direct_radiation"])
            == len(hourly["sunshine_duration"])
            == len(hourly["uv_index"])
        ):
            raise OpenMeteoError("Mismatched hourly array lengths in response")

        return SolarForecast(
            daily=DailyForecast(
                day=daily["time"][0],
                sunshine_duration_s=daily["sunshine_duration"][0],
                uv_index_max=daily["uv_index_max"][0],
            ),
            hourly=[
                HourlyForecast(
                    time=time,
                    direct_radiation_wm2=direct_radiation_wm2,
                    sunshine_duration_s=sunshine_duration_s,
                    uv_index=uv_index,
                )
                for time, direct_radiation_wm2, sunshine_duration_s, uv_index in zip(
                    hourly["time"],
                    hourly["direct_radiation"],
                    hourly["sunshine_duration"],
                    hourly["uv_index"],
                    strict=True,
                )
            ],
        )
    except (KeyError, TypeError, ValidationError) as exc:
        raise OpenMeteoError(f"Malformed Open-Meteo response: {output}") from exc


def get_solar_forecast(
    url: str,
    latitude: float,
    longitude: float,
    target_day: date,
    timezone: str = "Europe/London",
    retries: int = 5,
    backoff_factor: float = 0.5,
) -> SolarForecast:
    """Fetch the solar forecast for a location on a single day.

    Args:
        url: The Open-Meteo forecast endpoint to call.
        latitude: Latitude in WGS84 decimal degrees.
        longitude: Longitude in WGS84 decimal degrees (negative for west).
        target_day: The single calendar day to fetch (e.g. tomorrow).
        timezone: IANA timezone name used to align the day and hourly
            timestamps.
        retries: Maximum retries on transient failures (network errors, 429
            and 5xx responses). Non-retryable 4xx errors fail immediately.
        backoff_factor: Base for exponential backoff between retries, in seconds.

    Returns:
        A SolarForecast for ``target_day``, with a daily sunshine/UV summary
        and hourly direct radiation, sunshine and UV.

    Raises:
        OpenMeteoError: If the API reports an error or the response is
            malformed.
        requests.RequestException: If the request fails after all retries,
            or immediately on a non-retryable client error.
    """
    params: dict[str, str | float] = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "uv_index_max,sunshine_duration",
        "hourly": "direct_radiation,sunshine_duration,uv_index",
        "timezone": timezone,
        "start_date": target_day.isoformat(),
        "end_date": target_day.isoformat(),
    }

    logger.info("Calling Open-Meteo forecast API for %s", target_day)

    with _build_session(retries, backoff_factor) as session:
        try:
            response = session.get(url, params=params, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Open-Meteo request failed after retries: %s", exc)
            raise

    return _parse_response(response.json())


def _main() -> None:
    """Manual smoke-test entry point: fetch and log tomorrow's forecast."""
    settings = get_settings()
    forecast_timezone = "Europe/London"
    tomorrow = datetime.now(ZoneInfo(forecast_timezone)).date() + timedelta(days=1)

    forecast = get_solar_forecast(
        url=settings.open_meteo_api_url,
        latitude=float(settings.home_latitude.get_secret_value()),
        longitude=float(settings.home_longitude.get_secret_value()),
        target_day=tomorrow,
        timezone=forecast_timezone,
    )

    logger.info(
        "%s: %.1f h sunshine, max UV %.1f",
        forecast.daily.day,
        forecast.daily.sunshine_hours,
        forecast.daily.uv_index_max,
    )

    # East-facing panels: only morning-to-early-afternoon sun is useful for
    # charging in autumn/winter/spring. Adjust cutoff_hour seasonally
    # (e.g. 13 in Dec/Jan, 14 in Sep/Mar) once this feeds the actual charge
    # decision.
    cutoff_hour = 13
    morning_sunshine_hours = forecast.sunshine_hours_before_cutoff(cutoff_hour)
    logger.info(
        "%s: %.1f h sunshine expected before %02d:00",
        forecast.daily.day,
        morning_sunshine_hours,
        cutoff_hour,
    )


if __name__ == "__main__":
    _main()
