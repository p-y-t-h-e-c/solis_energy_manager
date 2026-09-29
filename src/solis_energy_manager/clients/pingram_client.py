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
                ccAddresses=[settings.cc_email.get_secret_value()],
                subject=subject,
                html=html_content,
                fromName=settings.from_name,
                fromAddress="noreply@pingram.io",
            )
        )
