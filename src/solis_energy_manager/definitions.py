import dagster as dg

from solis_energy_manager.defs.assets import (
    check_solis_cloud_data,
    get_solis_cloud_data,
)
from solis_energy_manager.defs.schedules import daily_schedule

defs = dg.Definitions(
    assets=[
        get_solis_cloud_data,
        check_solis_cloud_data,
    ],
    schedules=[
        daily_schedule,
    ],
)
