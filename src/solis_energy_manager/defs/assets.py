import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import dagster as dg

from solis_energy_manager.clients.pingram_client import send_email
from solis_energy_manager.clients.soliscloud_client import InverterSnapshot, get_data
from solis_energy_manager.settings import get_settings

settings = get_settings()


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


@dg.asset(
    name="validate_solis_cloud_data",
    deps=[get_solis_cloud_data],
)
def validate_solis_cloud_data(
    context: dg.AssetExecutionContext,
    get_solis_cloud_data: InverterSnapshot,
) -> None:
    """Check SolisCloud data."""

    date = datetime.now(ZoneInfo("Europe/London")).strftime("%a, %d %b %Y at %H:%M %Z")

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

            <p>
                <strong>PV Energy Generated:</strong><br>
                {get_solis_cloud_data.pv_energy_generated_today:.1f} kWh
            </p>
            <p>
                <strong>Battery charged</strong><br>
                {get_solis_cloud_data.battery_today_charge_energy:.1f} kWh
            </p>
            <p>
                <strong>Battery SOC</strong><br>
                {get_solis_cloud_data.battery_capacity_soc:.0f}%
            </p>
            <p>
                <strong>Grid exported</strong><br>
                {get_solis_cloud_data.grid_sell_today_energy:.1f} kWh
            </p>

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
