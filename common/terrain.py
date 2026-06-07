"""崎岖地形：MuJoCo hfield 生成。

设计原则：
- 当 amplitude == 0 时返回原 V10 平地 XML 片段（保证零扰动复现 V10 基线）
- 当 amplitude > 0 时返回 hfield 资产声明 + hfield 类型 geom（geom name 保持 'ramp'，
  以便 V10 的 foot_contact_detail / contact_flags 不变即可识别接触）
- hfield 数据通过 fill_hfield_data 在模型加载后写入（XML 只声明几何，数据用 numpy 注入）

接口：
- build_rugged_assets_xml(amplitude, length, width) -> str   # <hfield .../>
- build_rugged_geom_xml(amplitude, length, width)   -> str   # <geom name="ramp" .../>
- fill_hfield_data(model, profile_xz)                        # 写入高度数据
- generate_profile(nrow, ncol, length, amplitude, wavelength, seed) -> np.ndarray
"""

from __future__ import annotations

import numpy as np

HFIELD_NAME = "rugged_terrain"
HFIELD_NROW = 8  # y 方向（保持平整）
HFIELD_NCOL = 256  # x 方向（沿前进方向密采样）


def build_rugged_assets_xml(
    amplitude_m: float, length_m: float = 90.0, width_m: float = 3.6
) -> str:
    """返回需要插入到 <asset> 内的 hfield 声明。amplitude=0 时返回空串。

    size = (x 半长, y 半长, 最大正高度, 基底厚度)
    """
    if amplitude_m <= 0.0:
        return ""
    base = 0.08
    return (
        f'    <hfield name="{HFIELD_NAME}" nrow="{HFIELD_NROW}" ncol="{HFIELD_NCOL}" '
        f'size="{length_m / 2.0:.4f} {width_m / 2.0:.4f} {amplitude_m:.4f} {base:.4f}"/>\n'
    )


def build_rugged_geom_xml(amplitude_m: float, slope_deg: float = 0.0) -> str:
    """ramp geom 行。amplitude=0 -> 平面；>0 -> hfield。geom name 始终为 'ramp'。"""
    if amplitude_m <= 0.0:
        return (
            f'    <geom name="ramp" type="plane" pos="0 0 0" euler="0 {slope_deg} 0" '
            f'size="45 1.8 0.08" material="ramp_mat" contype="1" conaffinity="1"/>\n'
        )
    return (
        f'    <geom name="ramp" type="hfield" hfield="{HFIELD_NAME}" pos="0 0 0" '
        f'material="ramp_mat" contype="1" conaffinity="1"/>\n'
    )


def generate_profile(
    amplitude_m: float, wavelength_m: float, length_m: float, seed: int
) -> np.ndarray:
    """生成 (HFIELD_NROW, HFIELD_NCOL) 的归一化高度数组（值域 [0,1]）。

    沿 x 方向叠加多个正弦 + 高斯噪声，y 方向常值，确保仿真处于矢状面。
    起步 1.5 m 强制平地，避免初始化破坏（V10 初始足在 x≈0）。
    """
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
    """把生成的 profile 写入 model.hfield_data。profile shape = (nrow, ncol), 值域 [0,1]。"""
    flat = profile.astype(np.float32).ravel()
    assert (
        flat.size == model.hfield_data.size
    ), f"hfield 尺寸不匹配：profile={flat.size}, model={model.hfield_data.size}"
    model.hfield_data[:] = flat
