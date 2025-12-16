import logging

import pandas as pd
import requests
import xarray as xr
from hwt import init_times
from metpy.constants import g

gefs_members = ["gec00"] + [f"gep{i:02d}" for i in range(1, 31)]
era5_varid = {"z": 129, "t": 130}
mpas_rename = {"height_500hPa": "z", "temperature_850hPa": "t"}


def download_file(url, local_file_path):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(local_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded: {local_file_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error during download: {e}")
        print(f"Could not download {url}")


def select_variables(ds, shortName, isobaricInhPa):
    # Get the name of the variable we are looking for
    vars_to_keep = f"{shortName}{isobaricInhPa}"

    # Get the source filename from the dataset's encoding information
    source_file = ds.encoding.get("source", "Unknown file")

    # Try to select the variable, but catch the error if it fails
    try:
        return ds[[vars_to_keep]]
    except KeyError:
        print(f"---" * 20)
        print(f"❌ KEY ERROR: The variable '{vars_to_keep}' was not found.")
        print(f"   Problem file: {source_file}")
        print(f"---" * 20)
        # Re-raise the error to stop the program as before,
        # but now with our helpful message printed above.
        raise


def get_graphcast_output(shortName, isobaricInhPa):
    ifiles = []
    for init_time in init_times:
        idir = f"/glade/derecho/scratch/ahijevyc/ai-models/output/graphcast/{init_time:%Y%m%d%H}"
        ifiles.append([f"{idir}/{p}.nc" for p in gefs_members])
    logging.warning(f"Opening {len(ifiles)} files")
    ds_graphcast = (
        xr.open_mfdataset(
            ifiles,
            combine="nested",
            concat_dim=["time", "number"],
            preprocess=lambda x: select_variables(x, shortName, isobaricInhPa),
        )
        .rename(
            time="initialization_time",
            lat="latitude",
            lon="longitude",
        )
        .rename({f"{shortName}{isobaricInhPa}": shortName})
    )

    # Assign the coordinates to the dataset
    lead_time_as_hours = ds_graphcast["lead_time"] / \
        pd.to_timedelta(1, unit="h")
    ds_graphcast = ds_graphcast.assign_coords(
        forecast_hour=("lead_time", lead_time_as_hours.data))
    ds_graphcast = ds_graphcast.swap_dims(lead_time="forecast_hour")
    ds_graphcast = ds_graphcast.assign_coords(
        valid_time=ds_graphcast.initialization_time + ds_graphcast.lead_time
    )
    # just return 0z please (use where instead of sel for non-indexed coord, valid_time)
    ds_graphcast = ds_graphcast.where(
        ds_graphcast.valid_time.dt.hour == 0, drop=True)
    ds_graphcast = ds_graphcast.reindex(latitude=ds_graphcast.latitude[::-1])

    if shortName == "z":
        ds_graphcast = ds_graphcast / g.m
    return ds_graphcast
