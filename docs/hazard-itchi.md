# Blocks 3 and 4 · Wind hazard and forecast ITCHI

Last updated: 2026-11-08. Status: scheme decided (follow ITCHI); intensity correction and
exact wind normalisation open. No code yet.

Reference implementation: [`apereze/itchi-core`](https://github.com/apereze/itchi-core),
tag `v0.2.1` (2026-10-30), and its v0.3 plan (`contexto_itchi_v0.3.md`). Read those before
coding; this document only fixes what AITCHazard must produce for them.

## ITCHI in one paragraph

ITCHI is a bounded (0–1 or leveled) TC hazard index on a grid at synoptic times. It splits
the area around the storm into a **direct** region (r ≤ R_direct, from R34 per quadrant), an
**indirect** region (up to ROCLOUD per quadrant, with R_W06 as a floor) and an exterior
region. Precipitation hazard comes from the local rarity of P6 (6 h, window (T−6 h, T]),
R24 and A72 (antecedent, (T−78 h, T−6 h]) against MSWEP V3.16 percentiles (v0.2) or return
periods (v0.3). Wind hazard comes from a Willoughby et al. (2006) profile per quadrant
calibrated to R34; R_W06 is the radius where that profile falls to 2 m/s (Pérez-Alarcón et
al. 2021). In v0.2 the components combine as a probabilistic union; in v0.3 the plan is the
maximum of precipitation and wind levels.

## Block 3 · Wind hazard (decision D11)

Inputs per track point, as ITCHI expects them:

| ITCHI field | Source in AITCHazard |
|---|---|
| `storm_id`, `time` | Matched IBTrACS system; valid time = init + lead |
| `lat`, `lon` (`center_lat`, `center_lon`) | TempestExtremes centre |
| `vmax_kt` | AIFS Vmax after intensity correction (O11) |
| `pmin_hpa` | AIFS Pmin after intensity correction |
| `rmw_km` | W06 parametric RMW from Vmax and latitude (`w06_rmax_km` in ITCHI) |
| `R34_NE/SE/SW/NW` (nm) | From the AIFS 10 m wind field or parametric (O12) |
| `ROCLOUD_*` (km) | Parametric (`build_parametric_rocloud_record`), with R_W06 floor |

Scheme:

1. W06 profile per quadrant calibrated to R34 (ITCHI `parametric_radii.py`, `wind_profiles.py`).
2. Outer limit R_W06 = radius where the profile reaches **2 m/s** (`V_OUTER_PA21_MS = 2.0`).
3. Hazard normalised to **Saffir-Simpson categories** of the local wind (ITCHI v0.3, P4).
   Example with four levels from the v0.3 plan: 0 below 34 kt; 1 tropical storm (34–63 kt);
   2 categories 1–2 (64–95 kt); 3 major hurricane (≥ 96 kt). The v0.2.1 code normalises
   with the storm's own Vmax (`H_W = h34 + (1 − h34)(V − 34)/(Vmax − 34)`, tail to R_W06,
   `h34 = 0.2`); confirm the exact form and the tail cut (17 kt or 12 m/s) before
   implementing (O13).

### Why intensity correction is required (O11)

Emily 2005-07-17: AIFS (and ERA5 at t0) gives Pmin 971–993 hPa and Vmax 22–31 m s⁻¹
(maximum on the 0.25° grid) against 929–984 hPa and 33–72 m s⁻¹ in IBTrACS. The gap is
already present at t0, so it comes from the initial conditions. Saffir-Simpson levels
computed from raw AIFS would almost never exceed tropical storm.

Options to evaluate:

1. Post-processed intensity of [Gomez et al. (2025)](https://arxiv.org/abs/2508.17903)
   (ask Milton whether it applies to AIFS 1.1 with ERA5).
2. Lead-dependent statistical correction of Pmin and Vmax against IBTrACS on the hindcasts
   (quantile mapping or regression), validated out of sample.
3. Correct Pmin and derive Vmax with a wind–pressure relationship.

### R34 per quadrant (O12)

1. From the AIFS 10 m wind field: physically consistent with the forecast, but AIFS rarely
   reaches 34 kt at 0.25°, so R34 is often missing or too small.
2. Parametric from corrected Vmax and latitude (PA21), as ITCHI already does when R34 is
   missing: consistent with the observed ITCHI, ignores the forecast structure.
3. Hybrid: forecast wind shape scaled to the corrected intensity.

## Block 4 · Forecast ITCHI (decision D12)

AITCHazard produces, for each initialisation and lead:

- the track table above;
- P6 on the MSWEP 0.1° grid (Block 2 output, or raw AIFS, see O10);
- R24 and A72 windows. R24 = (T−24 h, T] is fully forecast from +24 h; at earlier leads it
  includes hours before t0. A72 = (T−78 h, T−6 h] mixes **observed MSWEP before t0** and
  forecast after t0 at every lead up to 72 h (O14).

ITCHI is then computed per lead and compared with the observed ITCHI (ITCHI v0.3 F5):
lead time at which each level is detected, and levels with skill.

## References

- Willoughby, H. E., Darling, R. W. R., and Rahn, M. E. (2006). Mon. Wea. Rev., 134,
  1102–1120. https://doi.org/10.1175/MWR3106.1 — the radial wind profile.
- Pérez-Alarcón, A., et al. (2021). Weather Clim. Extremes, 33, 100366.
  https://doi.org/10.1016/j.wace.2021.100366 — W06-based wind radii and the 2 m/s outer size.
