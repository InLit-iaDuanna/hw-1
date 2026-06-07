"""能量度量：CoT、机械能流、碰撞损耗。V12 填充。"""

from __future__ import annotations

import numpy as np


def cost_of_transport(
    input_energy_j: float, mass_kg: float, distance_m: float, g: float = 9.81
) -> float:
    """无量纲 CoT = E / (m g d)。距离/能量为 0 时返回 inf。"""
    denom = mass_kg * g * max(distance_m, 1e-9)
    if denom <= 0.0:
        return float("inf")
    return input_energy_j / denom


def spring_potential_energy(k: float, extension: float, ref: float = 0.0) -> float:
    """线性弹簧弹性势能 0.5 * k * (extension - ref)^2。

    k: 弹簧刚度（N·m/rad 或 N/m）。extension: 当前形变（rad 或 m）。ref: 自然长度。
    标量输入返回标量；用于 V15 SEA 在 hip / knee / tendon 上的弹性储能项。
    """
    delta = extension - ref
    return 0.5 * k * delta * delta


def mechanical_energy_series(
    rows: list[dict],
    mass_kg: float,
    g: float = 9.81,
    vx_key: str = "hip_x_vel",
    vz_key: str = "hip_z_vel",
    z_key: str = "hip_z",
    t_key: str = "time",
    springs: list[dict] | None = None,
) -> dict:
    """从 simulate 输出 rows 计算机械能时序。

    近似：只用 hip body 平动 KE = 0.5 m (vx^2 + vz^2)，PE = m g z。
    腿部转动惯量与摆动 link 的能量未展开（需要完整质量分布），故 V12 仅作'整机平动能量近似'。
    springs (V15 起): list of {k: float, ref: float, key: str}，每项把
    rows[i][key] - ref 视作弹簧形变并累加 0.5 * k * δ² 到 PE 列。
    springs=None 时与 V12-V14c 调用完全等价。
    返回 dict: time, ke, pe, total（均为 numpy array）。
    """
    if not rows:
        empty = np.empty(0)
        return {"time": empty, "ke": empty, "pe": empty, "total": empty}
    t = np.array([float(r[t_key]) for r in rows])
    vx = np.array([float(r.get(vx_key, 0.0)) for r in rows])
    vz = np.array([float(r.get(vz_key, 0.0)) for r in rows])
    z = np.array([float(r.get(z_key, 0.0)) for r in rows])
    ke = 0.5 * mass_kg * (vx**2 + vz**2)
    pe = mass_kg * g * z
    if springs:
        for s in springs:
            k = float(s["k"])
            ref = float(s.get("ref", 0.0))
            key = s["key"]
            ext = np.array([float(r.get(key, ref)) for r in rows])
            pe = pe + 0.5 * k * (ext - ref) ** 2
    return {"time": t, "ke": ke, "pe": pe, "total": ke + pe}


def collision_loss_per_step(
    rows: list[dict],
    mass_kg: float,
    g: float = 9.81,
    support_key: str = "support_foot",
    window: int = 1,
    **energy_kwargs,
) -> list[dict]:
    """在 support_foot 翻转的样点附近取总能量跳变 ΔE，作为'每步碰撞损耗'近似。

    返回 list of {step, time, support_from, support_to, dE_J}。dE_J 为正值 = 能量减小。
    window: 取 support 切换前/后第 window 个样点的能量差。
    """
    if not rows:
        return []
    series = mechanical_energy_series(rows, mass_kg=mass_kg, g=g, **energy_kwargs)
    total = series["total"]
    t = series["time"]
    events: list[dict] = []
    last_support = rows[0].get(support_key, "")
    n = len(rows)
    step = 0
    for i in range(1, n):
        cur = rows[i].get(support_key, "")
        if (
            cur != last_support
            and cur in {"left", "right"}
            and last_support in {"left", "right"}
        ):
            i_pre = max(0, i - window)
            i_post = min(n - 1, i + window)
            dE = float(total[i_pre] - total[i_post])
            events.append(
                {
                    "step": step,
                    "time": float(t[i]),
                    "support_from": last_support,
                    "support_to": cur,
                    "dE_J": dE,
                }
            )
            step += 1
        if cur in {"left", "right"}:
            last_support = cur
    return events
