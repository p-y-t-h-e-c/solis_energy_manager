import dagster as dg

from solis_energy_manager.defs.assets import (
    get_open_meteo_data,
    get_solis_cloud_data,
    validate_solis_cloud_data,
)
from solis_energy_manager.defs.jobs import all_asset_job
from solis_energy_manager.defs.schedules import daily_schedule

defs = dg.Definitions(
    assets=[
        get_solis_cloud_data,
        get_open_meteo_data,
        validate_solis_cloud_data,
    ],
    jobs=[all_asset_job],
    schedules=[
        daily_schedule,
    ],
)
