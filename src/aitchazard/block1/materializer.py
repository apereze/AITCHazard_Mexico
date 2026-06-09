"""Materialize planned AIFS input states for Block 1.

The state planner writes a declarative contract for the two AIFS Single v2
input states. This module opens a configured source dataset, verifies the
planned fields, cuts the Mexico domain, and writes a compact NetCDF artifact
that can become the handoff to Anemoi inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    import pandas as pd
    import xarray as xr

from .state_builder import StatePlan


TIME_COORD_CANDIDATES = ("time", "valid_time", "analysis_time", "date")
LAT_COORD_CANDIDATES = ("latitude", "lat")
LON_COORD_CANDIDATES = ("longitude", "lon")
LEVEL_COORD_CANDIDATES = ("level", "pressure_level", "isobaricInhPa", "plev")


class MaterializationError(RuntimeError):
    """Base error for input-state materialization failures."""


class MissingFieldsError(MaterializationError):
    """Raised when the source dataset does not satisfy the state plan."""

    def __init__(self, missing_fields: Iterable[str]):
        self.missing_fields = tuple(missing_fields)
        joined = ", ".join(self.missing_fields)
        super().__init__(f"Source dataset is missing required field(s): {joined}")


@dataclass(frozen=True)
class MaterializationResult:
    """Summary returned after writing materialized AIFS input states."""

    output_path: Path
    analysis_times: tuple[str, ...]
    variables: tuple[str, ...]
    source_uri: str

    @property
    def variable_count(self) -> int:
        return len(self.variables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": str(self.output_path),
            "analysis_times": list(self.analysis_times),
            "variables": list(self.variables),
            "variable_count": self.variable_count,
            "source_uri": self.source_uri,
        }


class AIFSStateMaterializer:
    """Open planned state sources and write model-ready input states."""

    def __init__(self, plans: Iterable[StatePlan], state_source: dict[str, Any]):
        self.plans = tuple(plans)
        self.state_source = dict(state_source)
        if not self.plans:
            raise ValueError("At least one state plan is required")
        self._validate_shared_contract()

    @property
    def first_plan(self) -> StatePlan:
        return self.plans[0]

    @property
    def analysis_times(self) -> tuple[datetime, ...]:
        seen: set[datetime] = set()
        ordered: list[datetime] = []
        for plan in self.plans:
            for value in plan.analysis_times:
                normalized = value.astimezone(timezone.utc)
                if normalized not in seen:
                    seen.add(normalized)
                    ordered.append(normalized)
        return tuple(ordered)

    @property
    def surface_variables(self) -> tuple[str, ...]:
        return _ordered_unique(
            variable for plan in self.plans for variable in plan.surface_variables
        )

    @property
    def pressure_families(self) -> tuple[str, ...]:
        return _ordered_unique(
            family for plan in self.plans for family in plan.pressure_families
        )

    @property
    def pressure_levels_hpa(self) -> tuple[int, ...]:
        return tuple(
            int(value)
            for value in _ordered_unique(
                level for plan in self.plans for level in plan.pressure_levels_hpa
            )
        )

    def materialize(self, output_path: str | Path) -> MaterializationResult:
        """Write a NetCDF file containing the planned t-6h/t0 state fields."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        source = self.open_source()
        try:
            selected = self._select_domain(source)
            selected = self._select_analysis_times(selected)
            materialized = self._extract_required_fields(selected)
            materialized.attrs.update(self._output_attrs())
            materialized.to_netcdf(output)
        finally:
            source.close()

        return MaterializationResult(
            output_path=output,
            analysis_times=tuple(_format_utc(value) for value in self.analysis_times),
            variables=tuple(materialized.data_vars),
            source_uri=str(self.state_source.get("uri", "")),
        )

    def open_source(self) -> xr.Dataset:
        """Open the configured source dataset."""

        xr = _require_xarray()
        kind = str(self.state_source.get("kind", "")).lower()
        uri = self.state_source.get("uri")
        if not uri:
            raise MaterializationError("state_source.uri is required")

        if kind == "zarr":
            return self._open_zarr(str(uri))
        if kind in {"netcdf", "cdf", "local"}:
            return xr.open_dataset(_as_path_if_local(str(uri)))
        if kind == "mars":
            raise MaterializationError(
                "MARS materialization is not wired yet. Use a zarr, netcdf, cdf "
                "or local state_source while the MARS adapter is implemented."
            )

        raise MaterializationError(f"Unsupported state_source.kind: {kind!r}")

    def _open_zarr(self, uri: str) -> xr.Dataset:
        xr = _require_xarray()
        storage_options = _normalized_storage_options(
            uri, self.state_source.get("storage_options", {})
        )
        try:
            return xr.open_zarr(uri, storage_options=storage_options)
        except TypeError:
            try:
                import fsspec
            except ModuleNotFoundError as exc:
                raise MaterializationError(
                    "Zarr sources require fsspec/s3fs support."
                ) from exc
            mapper = fsspec.get_mapper(uri, **storage_options)
            try:
                return xr.open_zarr(mapper)
            except (FileNotFoundError, OSError, PermissionError, ValueError) as exc:
                raise _zarr_open_error(uri, exc) from exc
        except ModuleNotFoundError as exc:
            raise MaterializationError(
                "Zarr sources require zarr, fsspec and s3fs."
            ) from exc
        except (FileNotFoundError, OSError, PermissionError, ValueError) as exc:
            raise _zarr_open_error(uri, exc) from exc

    def _select_domain(self, dataset: xr.Dataset) -> xr.Dataset:
        latitude_name = _find_coord_name(dataset, LAT_COORD_CANDIDATES)
        longitude_name = _find_coord_name(dataset, LON_COORD_CANDIDATES)

        selected = dataset
        if latitude_name:
            selected = _select_interval(
                selected,
                latitude_name,
                float(self.first_plan.domain["latitude_min"]),
                float(self.first_plan.domain["latitude_max"]),
            )
        if longitude_name:
            selected = _select_interval(
                selected,
                longitude_name,
                float(self.first_plan.domain["longitude_min"]),
                float(self.first_plan.domain["longitude_max"]),
            )
        return selected

    def _select_analysis_times(self, dataset: xr.Dataset) -> xr.Dataset:
        time_name = _find_coord_name(dataset, TIME_COORD_CANDIDATES)
        if not time_name:
            raise MaterializationError(
                "Source dataset must expose one time coordinate: "
                f"{', '.join(TIME_COORD_CANDIDATES)}"
            )

        targets = [_to_naive_utc_timestamp(value) for value in self.analysis_times]
        try:
            return dataset.sel({time_name: targets})
        except KeyError as exc:
            requested = ", ".join(_format_utc(value) for value in self.analysis_times)
            raise MaterializationError(
                f"Source dataset does not contain all requested analysis times: {requested}"
            ) from exc

    def _extract_required_fields(self, dataset: xr.Dataset) -> xr.Dataset:
        fields: dict[str, xr.DataArray] = {}
        missing: list[str] = []

        for variable in self.surface_variables:
            if variable in dataset.data_vars:
                fields[variable] = dataset[variable]
            else:
                missing.append(variable)

        for family in self.pressure_families:
            self._extract_pressure_family(dataset, family, fields, missing)

        if missing:
            raise MissingFieldsError(missing)

        xr = _require_xarray()
        return xr.Dataset(fields)

    def _extract_pressure_family(
        self,
        dataset: xr.Dataset,
        family: str,
        fields: dict[str, xr.DataArray],
        missing: list[str],
    ) -> None:
        level_name = _find_coord_name(dataset, LEVEL_COORD_CANDIDATES)
        has_layered_family = family in dataset.data_vars and level_name is not None

        for level in self.pressure_levels_hpa:
            field_name = f"{family}_{level}"
            if field_name in dataset.data_vars:
                fields[field_name] = dataset[field_name]
                continue

            if has_layered_family and level_name in dataset[family].dims:
                selected = _select_pressure_level(dataset[family], level_name, level)
                if selected is not None:
                    fields[field_name] = selected
                    continue

            missing.append(field_name)

    def _validate_shared_contract(self) -> None:
        domain = self.first_plan.domain
        for plan in self.plans[1:]:
            if plan.domain != domain:
                raise ValueError("All plans must use the same domain")

    def _output_attrs(self) -> dict[str, str]:
        return {
            "schema": "aitchazard.block1.materialized-states.v1",
            "checkpoint": self.first_plan.checkpoint,
            "source_uri": str(self.state_source.get("uri", "")),
            "analysis_times": ",".join(
                _format_utc(value) for value in self.analysis_times
            ),
        }


def materialize_state_plans(
    plans: Iterable[StatePlan],
    state_source: dict[str, Any],
    output_path: str | Path,
) -> MaterializationResult:
    """Materialize one or more state plans into a compact NetCDF file."""

    return AIFSStateMaterializer(plans, state_source).materialize(output_path)


def _find_coord_name(dataset: xr.Dataset | xr.DataArray, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in dataset.coords or name in dataset.dims:
            return name
    return None


def _select_interval(
    dataset: xr.Dataset, coord_name: str, lower: float, upper: float
) -> xr.Dataset:
    coord = dataset[coord_name]
    if coord.size == 0:
        return dataset

    first = float(coord.values[0])
    last = float(coord.values[-1])
    if first <= last:
        sliced = dataset.sel({coord_name: slice(lower, upper)})
    else:
        sliced = dataset.sel({coord_name: slice(upper, lower)})

    if sliced.sizes.get(coord_name, 0) > 0:
        return sliced

    mask = (coord >= lower) & (coord <= upper)
    return dataset.where(mask, drop=True)


def _select_pressure_level(
    array: xr.DataArray, level_name: str, level_hpa: int
) -> xr.DataArray | None:
    candidates = (level_hpa, level_hpa * 100)
    for candidate in candidates:
        try:
            return array.sel({level_name: candidate}, drop=True)
        except KeyError:
            continue
    return None


def _normalized_storage_options(uri: str, raw_options: Any) -> dict[str, Any]:
    options = dict(raw_options or {})
    endpoint_url = options.pop("endpoint_url", None)
    if endpoint_url:
        client_kwargs = dict(options.get("client_kwargs", {}))
        client_kwargs.setdefault("endpoint_url", endpoint_url)
        options["client_kwargs"] = client_kwargs

    if uri.startswith("s3://") and not _has_explicit_s3_credentials(options):
        options.setdefault("anon", True)

    return options


def _has_explicit_s3_credentials(options: dict[str, Any]) -> bool:
    credential_keys = {"key", "secret", "token", "username", "password"}
    return any(options.get(key) for key in credential_keys)


def _zarr_open_error(uri: str, exc: Exception) -> MaterializationError:
    return MaterializationError(
        "Could not open the configured Zarr state source "
        f"{uri!r}. Check that the URI, endpoint and S3 credentials/public "
        f"access are valid. Original error: {exc}"
    )


def _as_path_if_local(uri: str) -> str | Path:
    if "://" in uri:
        return uri
    return Path(uri)


def _to_naive_utc_timestamp(value: datetime) -> pd.Timestamp:
    pd = _require_pandas()
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp
    return timestamp.tz_convert("UTC").tz_localize(None)


def _format_utc(value: datetime) -> str:
    dt = value.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds") + "Z"


def _ordered_unique(values: Iterable[Any]) -> tuple[Any, ...]:
    seen: set[Any] = set()
    ordered: list[Any] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def _require_xarray() -> Any:
    try:
        import xarray as xr
    except ModuleNotFoundError as exc:
        raise MaterializationError(
            "State materialization requires xarray."
        ) from exc
    return xr


def _require_pandas() -> Any:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise MaterializationError(
            "State materialization requires pandas."
        ) from exc
    return pd
