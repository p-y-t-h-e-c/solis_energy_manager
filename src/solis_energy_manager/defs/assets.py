import dagster as dg

from solis_energy_manager.clients.pushstg_client import pushstaq_push_message
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


@dg.asset(name="check_solis_cloud_data", deps=[get_solis_cloud_data])
def check_solis_cloud_data(get_solis_cloud_data: InverterSnapshot) -> None:
    """Check SolisCloud data."""
    if get_solis_cloud_data.battery_capacity_soc > 80:
        pushstaq_push_message("Battery capacity is greater than 80%.")
    else:
        pushstaq_push_message("Battery capacity is less than or equal to 80%.")
