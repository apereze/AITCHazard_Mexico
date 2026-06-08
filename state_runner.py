# %%
import argparse
import os
import sys

import s3fs
import zarr
import xarray as xr
import pandas as pd
import datetime
import numpy as np
import dask
import dask.array as da
from torch import cuda

import earthkit.data as ekd
import earthkit.regrid as ekr
from anemoi.inference.runners.simple import SimpleRunner
from anemoi.inference.outputs.printer import print_state

# to open/load a dataset with anemoi.datasets
from anemoi.datasets import open_dataset

# adress for the url of the SDSC server
os.environ["ANEMOI_CONFIG_object-storage_ENDPOINT_URL"] = (
    "https://os.zhdk.cloud.switch.ch"
)

# set the number of chunks for inference
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["ANEMOI_INFERENCE_NUM_CHUNKS"] = "16"

# set dask to use threads
dask.config.set(scheduler="threads")

# %%
# %%
argparser = argparse.ArgumentParser()
argparser.add_argument(
    "--date",
    type=str,
    default="2023-10-01T00:00:00Z",
    help="Date to run the model on (UTC)",
)
argparser.add_argument(
    "--max_lead-time",
    type=int,
    default=120,
    help="Max lead time in hours",
)
argparser.add_argument(
    "--num-members",
    type=int,
    default=10,
    help="Number of ensemble members to run",
)
argparser.add_argument(
    "--save-path",
    type=str,
    default="/scratch/mgomezd1/AIFS-ens",
    help="Directory to save the output files",
)

# %% Define the units and long names for the variables
units = {
    "u": "m/s",
    "z": "m^2/s^2",
    "w": "m/s",
    "v": "m/s",
    "t": "K",
    "q": "kg/kg",
    "10u": "m/s",
    "10v": "m/s",
    "2d": "m",
    "2t": "K",
    "msl": "Pa",
    "skt": "K",
    "sp": "Pa",
    "tcw": "kg/m^2",
    "cp": "m",
    "tp": "m",
    "100u": "m/s",
    "100v": "m/s",
    "hcc": "fraction (0-1)",
    "lcc": "fraction (0-1)",
    "mcc": "fraction (0-1)",
    "ro": "m",
    "sf": "m of water equivalent",
    "ssrd": "J/m^2",
    "stl1": "K",
    "stl2": "K",
    "strd": "J/m^2",
    "swvl1": "m^3/m^3",
    "swvl2": "m^3/m^3",
    "tcc": "fraction (0-1)",
}

long_names = {
    "u": "u-component of wind",
    "z": "Geopotential height",
    "w": "w-component of wind",
    "v": "v-component of wind",
    "t": "Temperature",
    "q": "Specific humidity",
    "10u": "10 metre U wind component",
    "10v": "10 metre V wind component",
    "2d": "2 metre dewpoint temperature",
    "2t": "2 metre temperature",
    "msl": "Mean sea level pressure",
    "lsm": "Land-sea mask",
    "skt": "Skin temperature",
    "sp": "Surface pressure",
    "tcw": "Total column water vapour",
    "100u": "100 metre U wind component",
    "100v": "100 metre V wind component",
    "hcc": "High cloud cover",
    "lcc": "Low cloud cover",
    "mcc": "Medium cloud cover",
    "ro": "Runoff",
    "sf": "Snowfall",
    "ssrd": "Surface short-wave (solar) radiation downwards",
    "stl1": "Soil temperature level 1",
    "stl2": "Soil temperature level 2",
    "slor": "Slope of sub-gridscale orography",
    "sdor": "Standard deviation of sub-gridscale orography",
    "strd": "Surface long-wave (thermal) radiation downwards",
    "swvl1": "Volumetric soil water layer 1",
    "swvl2": "Volumetric soil water layer 2",
    "tcc": "Total cloud cover",
}

sel_vars = [
    "10u",
    "10v",
    "2d",
    "2t",
    "msl",
    "skt",
    "sp",
    "tcw",
    "lsm",
    "z",
    "slor",
    "sdor",
    "stl1",
    "stl2",
    "t_1000",
    "t_925",
    "t_850",
    "t_700",
    "t_600",
    "t_500",
    "t_400",
    "t_300",
    "t_250",
    "t_200",
    "t_150",
    "t_100",
    "t_50",
    "u_1000",
    "u_925",
    "u_850",
    "u_700",
    "u_600",
    "u_500",
    "u_400",
    "u_300",
    "u_250",
    "u_200",
    "u_150",
    "u_100",
    "u_50",
    "v_1000",
    "v_925",
    "v_850",
    "v_700",
    "v_600",
    "v_500",
    "v_400",
    "v_300",
    "v_250",
    "v_200",
    "v_150",
    "v_100",
    "v_50",
    "w_1000",
    "w_925",
    "w_850",
    "w_700",
    "w_600",
    "w_500",
    "w_400",
    "w_300",
    "w_250",
    "w_200",
    "w_150",
    "w_100",
    "w_50",
    "q_1000",
    "q_925",
    "q_850",
    "q_700",
    "q_600",
    "q_500",
    "q_400",
    "q_300",
    "q_250",
    "q_200",
    "q_150",
    "q_100",
    "q_50",
    "z_1000",
    "z_925",
    "z_850",
    "z_700",
    "z_600",
    "z_500",
    "z_400",
    "z_300",
    "z_250",
    "z_200",
    "z_150",
    "z_100",
    "z_50",
]

# %% Define the date and time for the run

DATE = pd.to_datetime(argparser.parse_args().date).to_pydatetime()
DATE = DATE.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc)
DATE = DATE.replace(minute=0, second=0, microsecond=0)  # Round to the nearest hour

# get the date as a string YYYY-MM-DDTHH:MM:SS
DATE_str = DATE.strftime("%Y-%m-%dT%H:%M:%S")

# Get the strings for 6 hours before DATE
DATE_prev_str = (DATE - datetime.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")

# %% Get the number of ensemble members
num_members = argparser.parse_args().num_members

# %% Access the data on the s3 bucket and open the larger set as main_ds

# Define the 2 subfolders in the s3 bucket
s3_path1 = "s3://nwf4ch-data/aifs-od-an-oper-0001-mars-n320-2016-2023-6h-v1-land.zarr"
s3_path2 = "s3://nwf4ch-data/aifs-od-an-oper-0001-mars-n320-2019-2023-6h-v6.zarr"

print("Accessing the data on the S3 bucket...", flush=True)
# access both datasets for the overlapped dates
ds1 = open_dataset(s3_path1, start="2019-01-01", end="2023-12-31", frequency="6h")
ds2 = open_dataset(s3_path2, start="2019-01-01", end="2023-12-31", frequency="6h")

print("Putting the data together...", flush=True)
# load the two datasets together, selecting the variables
# needed for AIFS-ens
main_ds = open_dataset(
    ds1, ds2, select=sel_vars, start=DATE_prev_str, end=DATE_str, frequency="6h"
)

print("Preparing the input fields...", flush=True)
input_fields = dict(
    zip(
        main_ds.variables,
        # main ds has shape (timesteps, fields, surface/levels, points)
        # we want to reshape it to (fields, timesteps, points)
        # note that each field has only one level (pressure levels are stored
        # with the field name, e.g. t_1000)
        main_ds[:].squeeze().transpose(1, 0, 2),
    )
)

# We create an input state dictionary for running AIFS-ens with anemoi
input_state = {
    "date": DATE,
    "fields": input_fields,
}

# %%
# if cuda.is_available():
#     calc_device = "cuda"
# else:
#     calc_device = "cpu"

# %% Load the checkpoint and create the runner`
checkpoint = {"huggingface": "ecmwf/aifs-ens-1.0"}
runner = SimpleRunner(checkpoint, device="cuda")

# %%
for n in range(num_members):
    save_name = f"AIFS-ens-{DATE_str}-{n+1:02d}_maxlead-{argparser.parse_args().max_lead_time}h.nc"
    save_path = os.path.join(argparser.parse_args().save_path, save_name)
    if os.path.exists(save_path):
        print(f"File {save_path} already exists. Skipping member {n+1}.")
        continue
    print(f"Running member {n+1}/{num_members}...", flush=True)
    i = 0
    latitudes = np.arange(-90, 90 + 0.25, 0.25)
    longitudes = np.arange(0, 360, 0.25)
    out_ds = None
    for state in runner.run(input_state=input_state, lead_time=120):
        if i == 0:
            # Read in the keys from the state
            mlevel_keys = [member for member in state["fields"].keys() if "_" in member]
            mlevel_vars = {key.split("_")[0] for key in mlevel_keys}
            slevel_keys = [
                member for member in state["fields"].keys() if "_" not in member
            ]
            levels = sorted(list({int(key.split("_")[1]) for key in mlevel_keys}))

        temp_ds = xr.Dataset(
            coords={
                "valid_time": pd.to_datetime(state["date"]).tz_localize(None),
                "lat": latitudes,
                "lon": longitudes,
                "level": levels,
            }
        )

        for var in mlevel_vars:
            var_field = da.full(
                (180 * 4 + 1, 360 * 4, len(levels)),
                np.nan,
                chunks=(180 * 4 + 1, 360 * 4, len(levels)),
            )
            for i, level in enumerate(levels):
                if f"{var}_{level}" in state["fields"]:
                    temp_field = ekr.interpolate(
                        state["fields"][f"{var}_{level}"],
                        {"grid": "N320"},
                        {"grid": (0.25, 0.25)},
                    )
                    var_field[:, :, i] = da.from_array(
                        temp_field, chunks=(180 * 4 + 1, 360 * 4)
                    )
            # var_field = var_field[, ...]
            temp_ds[var] = (("lat", "lon", "level"), var_field)
            temp_ds[var].attrs["units"] = units.get(var, "unknown")
            temp_ds[var].attrs["long_name"] = long_names.get(var, "unknown")

        for var in slevel_keys:
            var_field = da.full(
                (180 * 4 + 1, 360 * 4), np.nan, chunks=(180 * 4 + 1, 360 * 4)
            )
            if var in state["fields"]:
                temp_field = ekr.interpolate(
                    state["fields"][var],
                    {"grid": "N320"},
                    {"grid": (0.25, 0.25)},
                )
                var_field[:, :] = da.from_array(
                    temp_field, chunks=(180 * 4 + 1, 360 * 4)
                )
            # var_field = var_field[None, ...]
            temp_ds[var] = (("lat", "lon"), var_field)
            temp_ds[var].attrs["units"] = units.get(var, "unknown")
            temp_ds[var].attrs["long_name"] = long_names.get(var, "unknown")

        if out_ds is None:
            out_ds = temp_ds
        else:
            out_ds = xr.concat([out_ds, temp_ds], dim="valid_time")
        i += 1
    # out_ds = out_ds.assign_coords(valid_time=out_ds.valid_time.dt.tz_localize(None))
    out_ds.to_netcdf(
        save_path,
        mode="w",
        unlimited_dims="valid_time",
        compute=True,
    )
    print(f"Saved member {n+1} to {save_path}", flush=True)
