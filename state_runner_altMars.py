# %%
import argparse
import os
import sys

from collections import defaultdict
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
os.environ["ANEMOI_INFERENCE_NUM_CHUNKS"] = "4"

# set dask to use threads
dask.config.set(scheduler="threads")

from netCDF4 import Dataset

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
    default="/home/mgomez/work2/AIFS-out",
    help="Directory to save the output files",
)
#%%
PARAM_SFC = [
    "165",  # "10u",
    "166",  # "10v",
    "168",  # "2d",
    "167",  # "2t",
    "151",  # "msl",
    "235",  # "skt",
    "134",  # "sp",
    "136",  # "tcw",
    "172",  # "lsm",
    "129",  # "z",
    "163.128",  # "slor",
    "160.128",  # "sdor",

]
PARAM_SOIL = [
    # "39.128", #Soil water layer 1
    # "40.128", #Soil water layer 2
    # "41.128",
    # "42.128",
    "139.128",
    "170.128",
    # "183.128",
    # "236.128",
]
# ["vsw", "sot"]
PARAM_PL = ["129.128", "130.128", "131", "132", "133.128", "135.128"]



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
    "z_500": "m^2/s^2",
    "z_300": "m^2/s^2",
    "t_100": "K",
    "t_200": "K",
    "t_300": "K",
    "t_500": "K",
    "q_500": "kg/kg",
    "t_1000": "K",
    "q_1000": "kg/kg",
    "t_850": "K",
    "u_200": "m/s",
    "v_200": "m/s",
    "u_850": "m/s",
    "v_850": "m/s",
    "u_1000": "m/s",
    "v_1000": "m/s",
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
    "z_500": "Geopotential height at 500 hPa",
    "z_300": "Geopotential height at 300 hPa",
    "t_100": "Temperature at 100 hPa",
    "t_200": "Temperature at 200 hPa",
    "t_300": "Temperature at 300 hPa",
    "t_500": "Temperature at 500 hPa",
    "q_500": "Specific humidity at 500 hPa",
    "t_1000": "Temperature at 1000 hPa",
    "q_1000": "Specific humidity at 1000 hPa",
    "t_850": "Temperature at 850 hPa",
    "u_200": "u-component of wind at 200 hPa",
    "v_200": "v-component of wind at 200 hPa",
    "u_850": "u-component of wind at 850 hPa",
    "v_850": "v-component of wind at 850 hPa",
    "u_1000": "u-component of wind at 1000 hPa",
    "v_1000": "v-component of wind at 1000 hPa",
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

save_vars = [
    "skt",  # skin temperature, proxy for sst
    "10u",  # 10m u wind
    "10v",  # 10m v wind
    "msl",  # mean sea level pressure
    # --------- For geopotential thickness -----------
    "z_500",  # geopotential height at 500 hPa
    "z_300",  # geopotential height at 300 hPa
    # --------- Outflow Temperatures -----------
    "t_100",  # temperature at 100 hPa
    "t_200",  # temperature at 200 hPa
    "t_300",  # temperature at 300 hPa
    # --------- Moisture Variables -----------
    # Used to calculate RH at different levels
    "t_500",  # temperature at 500 hPa
    "q_500",  # specific humidity at 500 hPa
    "t_1000",  # temperature at 1000 hPa
    "q_1000",  # specific humidity at 1000 hPa
    # --------- Low level temperature -----------
    "t_850",
    # --------- Wind Shear -----------
    "u_200",  # u wind at 200 hPa
    "v_200",  # v wind at 200 hPa
    "u_850",  # u wind at 850 hPa
    "v_850",  # v wind at 850 hPa
    "u_1000",  # u wind at 1000 hPa
    "v_1000",  # v wind at 1000 hPa
]

# %%
args = argparser.parse_args()

# %% Define the date and time for the run

DATE = pd.to_datetime(args.date).to_pydatetime()
DATE = DATE.replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc)
DATE = DATE.replace(minute=0, second=0, microsecond=0)  # Round to the nearest hour

# get the date as a string YYYY-MM-DDTHH:MM:SS
DATE_str = DATE.strftime("%Y-%m-%dT%H:%M:%S")

# Get the strings for 6 hours before DATE
DATE_prev_str = (DATE - datetime.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")


# %% Get the number of ensemble members
num_members = args.num_members

#%%
debug = True
if not debug:
    # Print out the arguments
    print("Arguments:")
    for arg in sys.argv:
        print(f"  {arg}", flush=True)

    LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]
    SOIL_LEVELS = [1, 2]

    def get_data(param, levelist=[], date=None, levtype=None):
        fields = defaultdict(list)
        # Get the data for the current date and the previous date
        for date in [DATE - datetime.timedelta(hours=6), DATE]:

            data = ekd.from_source(
                "mars",  # Meteorological Archival and Retrieval System instead of "ecmwf-open-data"
                date=date,
                param=param,
                levelist=levelist,
                levtype=levtype,
                grid="N320",  # N320 is the native grid for the model
            )
            for f in data:

                # # Add the values to the list
                values = f.to_numpy()
                name = (
                    f"{f.metadata('param')}_{f.metadata('levelist')}"
                    if levelist
                    else f.metadata("param")
                )
                fields[name].append(values)

        # Create a single matrix for each parameter
        for param, values in fields.items():
            fields[param] = np.stack(values)

        return fields


    fields = {}

    surface = get_data(param=PARAM_SFC, date=DATE, levtype="sfc")
    fields.update(surface)
    soil = get_data(param=PARAM_SOIL, date=DATE, levtype="sfc")
    fields.update(soil)
    pressure = get_data(param=PARAM_PL, levelist=LEVELS, date=DATE, levtype="pl")
    fields.update(pressure)

    # mapping = {"sot_1": "stl1", "sot_2": "stl2", "vsw_1": "swvl1", "vsw_2": "swvl2"}
    # for k, v in soil.items():
    #     try:
    #         fields[mapping[k]] = v
    #     except KeyError:
    #         print(f"KeyError: {k} not in mapping", flush=True)

    # fields.update(get_data(param=PARAM_PL, levelist=LEVELS, date=DATE, levtype="pl"))

    input_state = dict(date=DATE, fields=fields)
else:
    import pickle
    with open(os.path.join(args.save_path, "debug_input_state_mars.pkl"), "rb") as f:
        input_state = pickle.load(f)


# %%
# if cuda.is_available():
#     calc_device = "cuda"
# else:
#     calc_device = "cpu"

# %% Load the checkpoint and create the runner`
checkpoint = {"huggingface": "ecmwf/aifs-ens-1.0"}
runner = SimpleRunner(checkpoint, device="cuda")

# %% Create the output netCDF file
save_name = f"AIFS-ens-{DATE_str}-ens_{num_members}-maxlead_{args.max_lead_time}h.nc"
save_path = os.path.join(args.save_path, save_name)
# %%
if os.path.exists(save_path):
    print(f"File {save_path} already exists. Skipping.")
    sys.exit(0)

print(f"Running all members and saving to {save_path}...", flush=True)
ncfile = Dataset(save_path, "w", format="NETCDF4")


n_horizons = args.max_lead_time // 6

# create dimensions
ncfile.createDimension("initial_time", None)
ncfile.createDimension("member", num_members)
ncfile.createDimension("valid_time", n_horizons)
ncfile.createDimension("latitude", 180 * 4 + 1)
ncfile.createDimension("longitude", 360 * 4)

# initialize initial_time variable
initial_time_var = ncfile.createVariable("initial_time", "f8", ("initial_time",))
initial_time_var.units = "hours since 1970-01-01 00:00:00"
initial_time_var.calendar = "standard"
initial_time_var[:] = (
    np.datetime64(DATE.replace(tzinfo=None)).astype("datetime64[ns]").astype("f8")
    / 1e9
    / 3600
)

# initialize valid_time variable
valid_time_var = ncfile.createVariable("valid_time", "f8", ("valid_time",))
valid_time_var.units = "hours since 1970-01-01 00:00:00"
valid_time_var.calendar = "standard"

# initialize spatial coordinates
lat_var = ncfile.createVariable("latitude", "f4", ("latitude",))
lon_var = ncfile.createVariable("longitude", "f4", ("longitude",))
lat_var.units = "degrees_north"
lon_var.units = "degrees_east"
lat_var[:] = np.arange(-90, 90.25, 0.25).astype("f4") * -1  # Flipped to correct
lon_var[:] = np.arange(0, 360, 0.25).astype("f4")

# initialize ensemble member dimension
member_var = ncfile.createVariable("member", "i4", ("member",))
member_var.units = "none"
member_var.long_name = "Ensemble member index"
member_var[:] = np.arange(1, num_members + 1)

# data variables (stored under LONG names; dict keyed by raw)
data_vars = {}
for key in save_vars:
    longname = long_names[key]
    data_vars[key] = ncfile.createVariable(
        key,
        "f4",
        ("initial_time", "member", "valid_time", "latitude", "longitude"),
        zlib=False,
        # complevel=6,
        chunksizes=(1, num_members, n_horizons, 180 * 4 + 1, 360 * 4),
        fill_value=np.float32(np.nan),
    )
    data_vars[key].units = units.get(key, "unknown")
    data_vars[key].long_name = longname

# %%
for n in range(num_members):
    for state in runner.run(input_state=input_state, lead_time=120):
        for key in save_vars:
            print(
                f"Processing member {n+1}, lead time {state['date']}, variable {key}...",
                flush=True,
            )
            var_field = state["fields"].get(key, None)
            if var_field is not None:
                # save to the netCDF variable
                # valid time in hours since 1970-01-01 00:00:00
                valid_time = (
                    np.datetime64(state["date"].replace(tzinfo=None))
                    .astype("datetime64[ns]")
                    .astype("f8")
                    / 1e9
                    / 3600
                )
                # find the index of the valid time
                valid_time_idx = int((valid_time - initial_time_var[0]) // 6) - 1
                inter_field = ekr.interpolate(
                    var_field,
                    {"grid": "N320"},
                    {"grid": (0.25, 0.25)},
                )

                data_vars[key][0, n, valid_time_idx] = inter_field.astype("f4")
                if n == 0:
                    valid_time_var[valid_time_idx] = valid_time
                ncfile.sync()

ncfile.close()

# %%
