# %%
import numpy as np
import pickle
import subprocess
import xarray as xr
import pandas as pd
import os

# %% Load the original ibtracs data
ibtracs_path = os.path.join(
    "/work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/alpha_bench/tracks/ibtracs/",
    "ibtracs.ALL.list.v04r01.csv",
)
df = pd.read_csv(ibtracs_path, dtype=str, skiprows=[1], na_filter=False)
# %% parse the datetimes
df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"])

# Select the years after 2016
df = df[df["ISO_TIME"].dt.year >= 2023]
# %%

# and the "standard" timesteps
hours_to_select = [
    0,
    6,
    12,
    18,
]
df = df[df["ISO_TIME"].dt.hour.isin(hours_to_select)]

# Adding the "negative" lead times to be able to handle genesis
max_lead = 120
step = 6
iso_times = df["ISO_TIME"].unique()
# set up a timedelta64 array for up to negative max_lead time with step hours
timedeltas = np.arange(-np.timedelta64(max_lead, "h"), 0, np.timedelta64(step, "h"))
# create a new array with the original iso_times and the negative lead times
iso_copy = iso_times.copy()
for delta in timedeltas:
    iso_copy = np.hstack([iso_copy, iso_times + delta])
# convert to datetime index
iso_times = pd.to_datetime(iso_copy).unique()

years = iso_times.year.unique()

# overwrite with 2019
years = [2022, 2023]

AIFS_script = "/work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/neural_weather_models/AIFS-ens/state_runner_altCDF.py"
# %%
print("Starting AIFS-ens runs...")
for year in years:
    temp_df = df[df["ISO_TIME"].dt.year == year]
    months = temp_df["ISO_TIME"].dt.month.unique()
    for month in months:
        days = temp_df["ISO_TIME"][
            temp_df["ISO_TIME"].dt.month == month
        ].dt.day.unique()
        for day in days:
            for hour in [00, 12]:
                # skip if 00 jan 1 2019
                if year == 2019 and month == 1 and day == 1 and hour == 0:
                    continue
                print(f"Running year={year}, month={month}, day={day}, hour={hour}")
                # Make the time string, e.g.: "2023-10-01T00:00:00Z"
                time_str = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00Z"

                # Check if the file with the time string exists in our directory:
                # /work/FAC/FGSE/IDYST/tbeucler/default/milton/AIFS_temp/
                # Filename example: AIFS-ens-2020-11-27T00:00:00-ens_10-maxlead_120h.nc
                if os.path.exists(
                    f"/work/FAC/FGSE/IDYST/tbeucler/default/milton/AIFS_temp/AIFS-ens-{time_str[:-1]}-ens_10-maxlead_120h.nc"
                ):
                    print(f"File for {time_str} already exists. Skipping.")
                    continue

                # print(f"Running AIFS script for {time_str}...")

                # run the AIFS script
                subprocess.run(
                    [
                        "python",
                        AIFS_script,
                        "--date",
                        time_str,
                        "--max_lead-time",
                        str(max_lead),
                    ]
                )
                # input("Press Enter to continue...")  # pause between runs

# %%
