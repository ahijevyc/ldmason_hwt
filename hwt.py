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
    [10, 20, 30, 40, 50, 75, 100, 125, 150, 200, 250, 300],
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


def xtime(ds: xarray.Dataset):
    """convert xtime variable to datetime and assign to coordinate"""

    # remove one-element-long Time dimension
    ds = ds.squeeze(dim="Time", drop=True)

    logging.info("decode initialization time variable")
    initial_time = pd.to_datetime(
        ds["initial_time"].load().item().decode("utf-8").strip(),
        format="%Y-%m-%d_%H:%M:%S",
    )

    # assign initialization time variable to its own coordinate
    ds = ds.assign_coords(
        initial_time=(
            ["initial_time"],
            [initial_time],
        ),
    )

    # extract member number from part of file path
    # assign to its own coordinate
    filename = Path(ds.encoding["source"])
    mem = [p for p in filename.parts if p.startswith("mem")]
    if mem:
        mem = mem[0].lstrip("mem_")
        mem = int(mem)
        ds = ds.assign_coords(mem=(["mem"], [mem]))

    logging.info("decode valid time and assign to variable")
    valid_time = pd.to_datetime(
        ds["xtime"].load().item().decode("utf-8").strip(),
        format="%Y-%m-%d_%H:%M:%S",
    )
    ds = ds.assign(valid_time=[valid_time])

    # calculate forecast hour and assign to variable
    forecastHour = (valid_time - initial_time) / pd.to_timedelta(1, unit="hour")
    ds = ds.assign(forecastHour=float(forecastHour))

    return ds
