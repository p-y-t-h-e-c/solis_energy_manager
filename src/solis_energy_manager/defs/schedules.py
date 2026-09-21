import dagster as dg

from solis_energy_manager.settings import get_settings

from .jobs import all_asset_job

daily_schedule = dg.ScheduleDefinition(
    name=get_settings().schedule_name,
    cron_schedule=get_settings().cron_schedule,
    target=all_asset_job,
    execution_timezone="Europe/London",
    default_status=dg.DefaultScheduleStatus.RUNNING,
)
