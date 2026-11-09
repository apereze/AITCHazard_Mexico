# TC tracking · TempestExtremes with the TCBench protocol

Last updated: 2026-11-08. Status: decided; not implemented. The current figures use an
illustrative minimum-MSLP follower (`scripts/block1/plot_case.py`), not TempestExtremes.

References: TCBench ([Gomez et al. 2026](https://arxiv.org/abs/2601.23268); code
[Zenodo 20323591](https://zenodo.org/records/20323591); data
[doi:10.57967/hf/8882](https://doi.org/10.57967/hf/8882)),
[TempestExtremes](https://github.com/ClimateGlobalChange/tempestextremes),
[Ullrich et al. 2021](https://doi.org/10.5194/gmd-14-5023-2021).

## Decisions

- Track only systems that exist at t0, matched to IBTrACS (TCBench protocol).
- Use the fields of Gomez et al.: `msl`, `10u`, `10v`, `z_300`, `z_500` (+ `zs`), i.e. the
  Block 1 extended domain (decision D10).
- Outputs per forecast: centre, track, Vmax and Pmin.

## Parameters (TCBench table 2; verify in their `track_processing` code)

| Criterion | Value |
|---|---|
| MSLP closed contour | 200 Pa within 6.5° |
| Warm core | z300 − z500 contour −58.8 m² s⁻² within 5.5°, at most 1.0° from the centre |
| Minimum duration | 12 h (3 nodes at 6 h) |
| Wind | Vmax ≥ 10 m s⁻¹ |
| Latitude | \|lat\| ≤ 50° |
| Topography filter | none |

To check in the TCBench code: how the wind threshold is counted, `--range`, `--maxgap`,
and the 6.5°/5.5° inversion relative to Ullrich et al. (2021).

## TempestExtremes options (checked in the code, commit of 2026-08-10)

- `DetectNodes`: `--regional` (required on a cropped domain, otherwise longitude wraps),
  `--closedcontourcmd`, `--mergedist`, `--outputcmd`, `--timefilter`.
- `StitchNodes`: `--range` (default 5°), `--mintime` (default 3), `--maxgap` (default 0),
  `--threshold`, `--min_endpoint_dist`, `--min_path_dist`.

## Steps

1. Compile TempestExtremes on Curnagl (CMake + NetCDF), pin the commit.
2. **Read test before the campaign**: run `DetectNodes` on one extended file. If it
   requires a CF `time` dimension instead of `lead_time`, change the Block 1 writer now.
3. Configure `DetectNodes --regional` (thickness with `_DIFF(z_300,z_500)`, wind with
   `_VECMAG(u10,v10)`) and `StitchNodes --mintime 12h`.
4. Match to IBTrACS at t0 (HuracanPy, as in TCBench).
5. Metrics: track error (km), Pmin and Vmax errors per lead, against persistence and
   MT-LB; persistence-filled and raw coverage; compare with the 00/12 subset of TCBench.
6. Test cases: Emily 2005-07-17 (done with the simple follower) and a Pacific case.

## Open (O15)

- Genesis inside the 72 h window.
- Spurious minima over high terrain at landfall (Sierra Madre).
- Possible Eugene 2005 (eastern Pacific) visible at the western edge of the Emily figures;
  check in the IBTrACS EP file.
