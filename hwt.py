import cartopy
import pandas as pd
import xarray


class Model:
    """model has a name and number of members
    It starts with no variables, v, to analyze, 
    but when group attribute is assigned, the 
    v attribute is also assigned. """

    def __init__(self, name, nmem, lead_time_days):
        self.name = name
        self.nmem = nmem
        self.lead_time_days = lead_time_days
        self.v = None

    """ return the string self.name when Model is printed """

    def __repr__(self):
        return self.name

    """ set the v property when the group property is set """
    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, value:str):
        possible_groups = ["wind", "uh"]
        assert value in possible_groups, f"unexpected group {value}. Expected one of {possible_groups}"
        if self.name == "fv3":
            if value == "uh": 
                v = ["MXUPHL0_1km_max", "MXUPHL0_3km_max", "MXUPHL2_5km_max"]
            else:
                v = ["MAXUVV_max", "MAXWIND10m"]
        elif self.name == "mpas":
            if value == "uh":
                v = ["updraft_helicity_max01", "updraft_helicity_max03", "updraft_helicity_max"]
            else:
                v = ["w_velocity_max", "wind_speed_10m_max"]
        self.v = v
        self._group = value


def firstRun(year=2024):
    if year == 2023:
        return pd.to_datetime("20230424")
    if year == 2024:
        return pd.to_datetime("20240420")


# for interp output
projection =  cartopy.crs.LambertConformal(
    central_longitude=262.5 - 360,
    standard_parallels=(38.5,38.5),
)
extent = (-123.0, -72.1, 21.6, 50.4)



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

fv3 = Model(
    "fv3",
    nmem=10,
    lead_time_days=8,
)

mpas = Model(
    "mpas",
    nmem=5,
    lead_time_days=5,
)
