"""Batched interpolation with the earthkit-regrid matrices.

Same weights as ``earthkit.regrid.interpolate`` (method "linear"), but:
- all fields are interpolated in a single sparse product;
- the output can be restricted to the rows of a box of a regular output grid.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import scipy.sparse as sp

GRIDS = {"N320": {"grid": "N320"}, "LL025": {"grid": (0.25, 0.25)}}


@lru_cache(maxsize=4)
def load_matrix(in_key: str, out_key: str, method: str = "linear") -> tuple[sp.csr_matrix, tuple[int, ...]]:
    """Sparse matrix (n_out, n_in) and output shape, from the earthkit-regrid database."""
    from earthkit.regrid.db import find

    z, shape = find(GRIDS[in_key], GRIDS[out_key], method)
    if z is None:
        raise ValueError(f"No earthkit-regrid matrix for {in_key} -> {out_key} ({method})")
    return sp.csr_matrix(z), tuple(shape)


class Regridder:
    """Interpolate stacks of fields (n, *in_shape) with a fixed sparse matrix."""

    def __init__(self, z: sp.spmatrix, out_shape: tuple[int, ...], box: tuple[slice, slice] | None = None):
        z = sp.csr_matrix(z)
        if box is not None:
            if len(out_shape) != 2:
                raise ValueError("box requires a regular 2-D output grid")
            i, j = box
            # Row-major flat indices of the box in the (nlat, nlon) output grid
            rows = (np.arange(i.start, i.stop)[:, None] * out_shape[1] + np.arange(j.start, j.stop)[None, :]).ravel()
            z = z[rows]
            out_shape = (i.stop - i.start, j.stop - j.start)
        self.z = z
        self.out_shape = tuple(out_shape)

    @classmethod
    def from_grids(cls, in_key: str, out_key: str, box: tuple[slice, slice] | None = None, method: str = "linear"):
        z, shape = load_matrix(in_key, out_key, method)
        return cls(z, shape, box)

    def __call__(self, stack, dtype=None) -> np.ndarray:
        x = np.asarray(stack)
        n = x.shape[0]
        x = x.reshape(n, -1)
        if x.shape[1] != self.z.shape[1]:
            raise ValueError(f"Expected {self.z.shape[1]} input points per field, got {x.shape[1]}")
        y = (self.z @ np.ascontiguousarray(x.T)).T  # (n, n_out)
        y = y.reshape(n, *self.out_shape)
        return y if dtype is None else y.astype(dtype, copy=False)
