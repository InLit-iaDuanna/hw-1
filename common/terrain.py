"""Rugged terrain helpers for MuJoCo hfield generation."""

from __future__ import annotations

import numpy as np

HFIELD_NAME = "rugged_terrain"
HFIELD_NROW = 8
HFIELD_NCOL = 256


def build_rugged_assets_xml(
    amplitude_m: float, length_m: float = 90.0, width_m: float = 3.6
) -> str:
    """Return the hfield asset XML, or an empty string for flat terrain."""
    if amplitude_m <= 0.0:
        return ""
    base = 0.08
    return (
        f'    <hfield name="{HFIELD_NAME}" nrow="{HFIELD_NROW}" '
        f'ncol="{HFIELD_NCOL}" size="{length_m / 2.0:.4f} '
        f'{width_m / 2.0:.4f} {amplitude_m:.4f} {base:.4f}"/>\n'
    )


def build_rugged_geom_xml(amplitude_m: float, slope_deg: float = 0.0) -> str:
    """Return terrain geom XML. Flat terrain uses the original plane."""
    if amplitude_m <= 0.0:
        return (
            f'    <geom name="ramp" type="plane" pos="0 0 0" '
            f'euler="0 {slope_deg} 0" size="45 1.8 0.08" '
            f'material="ramp_mat" contype="1" conaffinity="1"/>\n'
        )
    return (
        f'    <geom name="ramp" type="hfield" hfield="{HFIELD_NAME}" '
        f'pos="0 0 0" material="ramp_mat" contype="1" conaffinity="1"/>\n'
    )


def generate_profile(
    amplitude_m: float, wavelength_m: float, length_m: float, seed: int
) -> np.ndarray:
    """Generate a normalized ``(HFIELD_NROW, HFIELD_NCOL)`` height profile."""
    rng = np.random.default_rng(seed)
    x = np.linspace(-length_m / 2.0, length_m / 2.0, HFIELD_NCOL)

    components = np.zeros_like(x)
    n_modes = 4
    for _ in range(n_modes):
        wl = wavelength_m * (0.6 + 0.7 * rng.random())
        phase = rng.uniform(0.0, 2.0 * np.pi)
        components += np.sin(2.0 * np.pi * x / wl + phase) / n_modes
    components += 0.25 * rng.standard_normal(size=x.shape)

    profile = components - components.min()
    if profile.max() > 0:
        profile = profile / profile.max()

    flat_zone = 1.5
    ramp_zone = 0.5
    weight = np.clip((x - flat_zone) / ramp_zone, 0.0, 1.0)
    weight = np.where(x < 0, 0.0, weight)
    profile = profile * weight
    return np.tile(profile, (HFIELD_NROW, 1))


def fill_hfield_data(model, profile: np.ndarray) -> None:
    """Write a generated profile into ``model.hfield_data``."""
    flat = profile.astype(np.float32).ravel()
    if flat.size != model.hfield_data.size:
        raise ValueError(
            f"hfield data size mismatch: profile={flat.size}, "
            f"model={model.hfield_data.size}"
        )
    model.hfield_data[:] = flat
