import dagster as dg

from solis_energy_manager.defs.assets import (
    check_solis_cloud_data,
    get_solis_cloud_data,
)

all_asset_job = dg.define_asset_job(
    name="solis_energy_manager_job",
    selection=dg.AssetSelection.assets(get_solis_cloud_data, check_solis_cloud_data),
)
