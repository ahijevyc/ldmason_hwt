import pandas as pd
import xarray
class Model:
    """model has a name and number of members
    and variable(s), v, to analyze."""

    def __init__(self, name, nmem, v, lead_time_days):
        self.name = name
        self.nmem = nmem
        self.v = v
        self.lead_time_days = lead_time_days

    """ return the string self.name when Model is printed """

    def __repr__(self):
        return self.name

def firstRun(year=2024):
    if year == 2023:
        return pd.to_datetime("20230424")
    if year == 2024:
        return pd.to_datetime("20240420")

# Multiple thresholds for updraft helicity
helicityThresholds = xarray.DataArray(
    [10, 20, 30, 40, 50, 75, 100, 125, 150, 175, 200, 250],
    dims="thresh",
    attrs={"units": "$m^2/s^2$", "short_name":"uh"},
)

windThresholds = xarray.DataArray(
    [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    dims="thresh",
    attrs={"units": "$m/s$", "short_name":"wind"},
)

