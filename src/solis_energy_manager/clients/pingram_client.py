from pingram import Pingram
from pingram.models.send_email_request import SendEmailRequest

from solis_energy_manager.settings import Settings


async def send_email(settings: Settings, subject: str, html_content: str) -> None:
    async with Pingram(
        api_key=settings.pingram_api_key.get_secret_value(),
        base_url=settings.pingram_api_url,
    ) as client:
        await client.email.email_send(
            SendEmailRequest(
                type="email_compose_preview",
                to=settings.destination_email.get_secret_value(),
                subject=subject,
                html=html_content,
                fromName=settings.from_name,
                fromAddress="noreply@pingram.io",
            )
        )


if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from solis_energy_manager.clients.soliscloud_client import (
        get_data,
    )
    from solis_energy_manager.settings import get_settings

    settings = get_settings()

    api_body_content = {"sn": settings.solis_inverter_sn.get_secret_value()}
    api_endpoint = "inverterDetail"

    get_solis_cloud_data = get_data(
        settings, api_endpoint=api_endpoint, api_body_content=api_body_content
    )

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

    asyncio.run(send_email(settings, "Battery Capacity Info", html_content))
