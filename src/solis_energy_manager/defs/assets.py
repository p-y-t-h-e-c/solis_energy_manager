import dagster as dg


@dg.asset
def get_battery_soc_data(context: dg.AssetExecutionContext) -> dg.MaterializeResult: ...
