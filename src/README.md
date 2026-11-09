# Source package `aitchazard`

| Module | Content |
|---|---|
| `block1/dates.py` | Initialisation calendar, ERA5 analysis times, year-month tasks |
| `block1/era5_params.py` | CDS parameter mapping and monthly requests, field-name normalisation |
| `block1/era5_inputs.py` | `ERA5Local`: AIFS input states from monthly GRIB (batched 0.25° → N320) |
| `block1/regrid.py` | `Regridder`: earthkit-regrid matrices in one sparse product, optionally on a box |
