"""Batched regridding: same result as one sparse product per field (no network, no GPU)."""
import numpy as np
import scipy.sparse as sp

from aitchazard.block1.regrid import Regridder


def _random_matrix(n_out, n_in, seed=0):
    rng = np.random.default_rng(seed)
    return sp.random(n_out, n_in, density=0.05, random_state=rng, format="csr")


def test_batched_equals_per_field():
    z = _random_matrix(4 * 6, 30)
    x = np.random.default_rng(1).normal(size=(5, 30))
    out = Regridder(z, (4, 6))(x)
    ref = np.stack([(z @ xi).reshape(4, 6) for xi in x])
    np.testing.assert_allclose(out, ref, rtol=1e-12)


def test_box_equals_crop_of_global():
    z = _random_matrix(7 * 9, 40)
    x = np.random.default_rng(2).normal(size=(3, 40))
    box = (slice(2, 5), slice(3, 8))
    out = Regridder(z, (7, 9), box=box)(x)
    ref = Regridder(z, (7, 9))(x)[:, box[0], box[1]]
    assert out.shape == (3, 3, 5)
    np.testing.assert_allclose(out, ref, rtol=1e-12)


def test_input_is_flattened_and_dtype_cast():
    z = _random_matrix(2 * 3, 4 * 5)
    x = np.random.default_rng(3).normal(size=(2, 4, 5))
    out = Regridder(z, (2, 3))(x, dtype=np.float32)
    assert out.dtype == np.float32 and out.shape == (2, 2, 3)
