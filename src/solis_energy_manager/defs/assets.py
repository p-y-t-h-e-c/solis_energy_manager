import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import dagster as dg

from solis_energy_manager.clients.open_meteo_client import (
    SolarForecast,
    get_solar_forecast,
)
from solis_energy_manager.clients.pingram_client import send_email
from solis_energy_manager.clients.soliscloud_client import InverterSnapshot, get_data
from solis_energy_manager.settings import get_settings

settings = get_settings()
_TIME_ZONE = "Europe/London"


@dg.asset(
    retry_policy=dg.RetryPolicy(
        max_retries=settings.fallback_max_retry, delay=settings.fallback_retry_delay
    )
)
def get_solis_cloud_data() -> InverterSnapshot:
    """Current battery SOC and grid/battery energy figures."""

    return get_data(
        settings,
        api_body_content={"sn": settings.solis_inverter_sn.get_secret_value()},
        api_endpoint="inverterDetail",
    )


@dg.asset
def get_open_meteo_data() -> SolarForecast:
    """Fetch tomorrow's solar forecast."""

    tomorrow = datetime.now(ZoneInfo(_TIME_ZONE)).date() + timedelta(days=1)

    return get_solar_forecast(
        url=settings.open_meteo_api_url,
        latitude=float(settings.home_latitude.get_secret_value()),
        longitude=float(settings.home_longitude.get_secret_value()),
        target_day=tomorrow,
        timezone=_TIME_ZONE,
    )


@dg.asset(
    name="validate_solis_cloud_data",
    deps=[get_solis_cloud_data, get_open_meteo_data],
)
def validate_solis_cloud_data(
    context: dg.AssetExecutionContext,
    get_solis_cloud_data: InverterSnapshot,
    get_open_meteo_data: SolarForecast,
) -> None:
    """Check SolisCloud data."""

    date = datetime.now(ZoneInfo(_TIME_ZONE)).strftime("%a, %d %b %Y at %H:%M %Z")

    if get_solis_cloud_data.battery_capacity_soc > 80:
        decision_content = """
            <p>
                <span style="color: green;">
                    ✅ <strong>No overnight grid charging should be required.</strong>
                </span>
            </p>

            <p style="color: #666;">
                However, check tomorrow's weather forecast before making the final decision.
            </p>
        """
    else:
        decision_content = """
            <p>
                <span style="color: #d97706;">
                    ⚠️ <strong>Overnight grid charging is recommended.</strong>
                </span>
            </p>

            <p style="color: #666;">
                Please enable overnight grid charging on the inverter. <br>
                Also check tomorrow's weather forecast before making the final decision.
            </p>
        """

    html_content = f"""
        <div style="font-family: Arial, Helvetica, sans-serif; max-width: 600px;">

            <h2 style="margin-bottom: 5px;">
                ☀️ Solis Energy Manager
            </h2>

            <p style="margin-top: 0; color: #666;">
                <strong>Today's SolisCloud data</strong><br>
                {date}
            </p>

            <hr>

            <table style="border-collapse: collapse; font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #222;">
                <tr>
                    <td colspan="2" style="padding: 0 0 8px 0; font-size: 14px; font-weight: bold;">
                        Energy Summary
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; border-bottom: 1px solid #e0e0e0; color: #555;">
                        PV Energy Generated
                    </td>
                    <td style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {get_solis_cloud_data.pv_energy_generated_today:.1f} kWh
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; border-bottom: 1px solid #e0e0e0; color: #555;">
                        Battery Charged
                    </td>
                    <td style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {get_solis_cloud_data.battery_today_charge_energy:.1f} kWh
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; border-bottom: 1px solid #e0e0e0; color: #555;">
                        Grid Exported
                    </td>
                    <td style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {get_solis_cloud_data.grid_sell_today_energy:.1f} kWh
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0;  font-weight: bold;">
                        Battery SOC
                    </td>
                    <td style="padding: 5px 0; text-align: right; font-weight: bold;">
                        {get_solis_cloud_data.battery_capacity_soc:.0f}%
                    </td>
                </tr>
            </table>

            <table style="border-collapse: collapse; font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #222; margin-top: 20px;">
                <tr>
                    <td colspan="2" style="padding: 0 0 8px 0; font-size: 14px; font-weight: bold;">
                        Tomorrow's Weather Forecast
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; border-bottom: 1px solid #e0e0e0; color: #555;">
                        Total Sunshine Hours
                    </td>
                    <td style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {get_open_meteo_data.daily.sunshine_hours:.1f} h
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; border-bottom: 1px solid #e0e0e0; color: #555;">
                        Max UV Index
                    </td>
                    <td style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {get_open_meteo_data.daily.uv_index_max:.1f}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 5px 24px 5px 0; font-weight: bold;">
                        Sunshine Before {settings.cutoff_hour}:00
                    </td>
                    <td style="padding: 5px 0; text-align: right; font-weight: bold;">
                        {get_open_meteo_data.sunshine_hours_before_cutoff(settings.cutoff_hour):.1f} h
                    </td>
                </tr>
            </table>

            <hr>

            <h3>🌙 Tonight</h3>

            {decision_content}

            <hr>

            <p>
                Kind regards,<br>
                <strong>p_y_t_h_e_c</strong>
            </p>
        </div>
        """

    context.log.info("Sending Solis energy notification email")

    asyncio.run(
        send_email(
            settings,
            "Battery Capacity Info",
            html_content,
        )
    )
