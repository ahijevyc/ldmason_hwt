import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import cartopy
import pandas as pd
import xarray as xr


class Model:
    """model has a name and number of members
    It starts with no variables, v, to analyze,
    but when group attribute is assigned, the
    v attribute is also assigned."""

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
    def group(self, value: str):
        possible_groups = ["wind", "uh"]
        assert (
            value in possible_groups
        ), f"unexpected group {value}. Expected one of {possible_groups}"
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
projection = cartopy.crs.LambertConformal(
    central_longitude=262.5 - 360,
    standard_parallels=(38.5, 38.5),
)
extent = (-123.0, -72.1, 21.6, 50.4)


# Multiple thresholds for updraft helicity
helicityThresholds = xr.DataArray(
    [10, 20, 30, 40, 50, 75, 100, 125, 150, 200, 250, 300],
    dims="thresh",
    attrs={"units": "$m^2/s^2$", "short_name": "uh"},
)

windThresholds = xr.DataArray(
    [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    dims="thresh",
    attrs={"units": "$m/s$", "short_name": "wind"},
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

# created with derecho/scratch/ahijevyc/ldmason_hwt/make_latlon_mask_hwt.ipynb
# hwt_mask is a LambertConf grid within geographic_sel. Trim others to mpas hwt interp domain
mask0p25 = xr.open_dataarray("hwt_0.25deg_mask.nc")
mask0p5 = xr.open_dataarray("hwt_0.5deg_mask.nc")


def xtime(ds: xr.Dataset):
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


def get_dynamics_model(
    model: str,
    forecast_hours: Iterable[int],
    ens_size: int,
    vars_dict: Dict[str, str],
    init_times: Sequence[pd.Timestamp],
    output_grid: xr.Dataset,
    CACHEDIR: Path,
) -> xr.Dataset:
    """
    Retrieves and processes a dynamics model dataset.

    Checks for a cached version of the data, otherwise loads it from NetCDF files,
    processes it, regrids it to a target grid, and saves it to a Zarr store.
    """
    # Tried native mesh but no 850t or 500z.
    ofile: Path = CACHEDIR / f"{model}.zarr"
    print(f"creating {ofile}")
    # Create list of input files
    # This is a nested list comprehension, looping through
    # init_times
    #   forecast_hours
    #       members (1 through ens_size)
    # Create a triply-nested list of input files:
    # Level 1: Initialization Times
    # Level 2: Forecast Hours
    # Level 3: Ensemble Members
    ifiles: List[List[List[Path]]] = [
        [
            [
                Path(f"/glade/campaign/mmm/parc/schwartz/HWT{init_time:%Y}/{model}")
                / init_time.strftime("%Y%m%d%H")
                / "post"
                / f"mem_{mem}"
                / f"interp_{model}_3km_{init_time:%Y%m%d%H}_mem{mem}_f{fhr:03d}.nc"
                for mem in range(1, ens_size + 1)
            ]
            for fhr in forecast_hours
        ]
        for init_time in init_times
    ]

    ds = xr.open_mfdataset(
        ifiles,
        combine="nested",
        concat_dim=["initialization_time", "forecast_hour", "number"],
        preprocess=lambda ds: ds.assign_coords(forecast_hour=int(ds.attrs["forecastHour"])),
        drop_variables=["total_precip_hrly"],
        coords="minimal",
        compat="override",
        combine_attrs="drop",
        chunks={},
    ).squeeze(dim="time")
    ds = ds.assign_coords(number=range(1, ens_size + 1), initialization_time=init_times)
    ds = ds.assign_coords(
        valid_time=ds["initialization_time"] + ds["forecast_hour"] * pd.Timedelta("1h")
    )
    ds = ds.rename(lat="y", lon="x")
    # Define new output grid
    output_grid = xr.Dataset(
        coords={
            "latitude": output_grid.coords["latitude"],
            "longitude": output_grid.coords["longitude"],
        }
    )

    # Select the first index along the dimensions you want to remove
    # The `drop=True` argument removes the dimension and coordinate from the variable
    for var_name in ["latitude", "longitude"]:
        ds[var_name] = ds[var_name].isel(
            initialization_time=0, forecast_hour=0, number=0, drop=True
        )
    ds["longitude"] = ds["longitude"] + 360  # MPAS/FV3 -180,180
    ds = ds.rename(vars_dict)

    # Create the regridding tool
    regridder: xe.Regridder = xe.Regridder(ds, output_grid, method="bilinear")

    # Apply the regridding to your dataset
    ds = regridder(ds)

    ds[list(vars_dict.values())].to_zarr(ofile)
    return ds


