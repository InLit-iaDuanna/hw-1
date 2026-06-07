"""Poincaré 截面：以触地事件为截面提取 (q, qdot) 序列。

Floquet 乘子估计采用 Goswami et al. (1996) 'experimental Floquet' 方法：
对截面点序列 x_k 取末段均值作不动点 x*，对 (x_k - x*) 与 (x_{k+1} - x*) 做最小二乘
线性回归得到 return-map Jacobian 估计 J，乘子即 J 的特征值。
参见 references/passive_dynamic_walking/02_Goswami_Thuilot_Espiau_1996_Compass_Like_Biped_Robot_Part_I.pdf。
"""

from __future__ import annotations

import numpy as np


def collect_section(rows: list[dict], state_keys: tuple[str, ...]) -> np.ndarray:
    """从 simulate 输出 rows 中，提取 mode 切换或 support_foot 切换处的状态。

    简化口径：取每次 support_foot 字段变化的样点为截面点。
    返回 shape = (N, len(state_keys)) 的数组。
    """
    if not rows:
        return np.empty((0, len(state_keys)))
    pts: list[list[float]] = []
    last_support = rows[0].get("support_foot", "")
    for r in rows[1:]:
        cur = r.get("support_foot", "")
        if cur != last_support and cur in {"left", "right"}:
            pts.append([float(r[k]) for k in state_keys])
            last_support = cur
    return np.array(pts) if pts else np.empty((0, len(state_keys)))


def plot_section(
    ax, pts: np.ndarray, x_label: str, y_label: str, title: str = ""
) -> None:
    if pts.size == 0:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.scatter(pts[:, 0], pts[:, 1], s=22, alpha=0.75)
        ax.plot(pts[:, 0], pts[:, 1], "-", lw=0.8, alpha=0.4)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.3)


def floquet_multipliers(
    section_pts: np.ndarray,
    fixed_point: np.ndarray | None = None,
    tail_frac: float = 0.4,
    skip_head: int = 0,
) -> dict:
    """从 Poincaré 截面点序列估计 return-map Jacobian 的特征值（实验 Floquet 乘子）。

    section_pts: shape (N, d) 数组。
    fixed_point: 若为 None，取后 max(2, tail_frac*N) 个点的均值。
    skip_head: 跳过前若干个点（暂态）。
    返回 dict: jacobian (d,d), eigvals (d,), fixed_point (d,), n_pairs。
    样本不足（<d+1 对）时 jacobian 用 lstsq 仍可解，但谱可能不可靠；调用方应自查 n_pairs。
    """
    pts = np.asarray(section_pts, dtype=float)
    if skip_head > 0:
        pts = pts[skip_head:]
    n, d = pts.shape if pts.ndim == 2 else (0, 0)
    if n < 2:
        return {
            "jacobian": np.full((d, d), np.nan) if d else np.empty((0, 0)),
            "eigvals": np.full(d, np.nan + 0j) if d else np.empty(0, dtype=complex),
            "fixed_point": np.full(d, np.nan) if d else np.empty(0),
            "n_pairs": 0,
        }
    if fixed_point is None:
        n_tail = max(2, int(round(tail_frac * n)))
        fixed_point = pts[-n_tail:].mean(axis=0)
    fp = np.asarray(fixed_point, dtype=float)
    X = pts[:-1] - fp  # shape (n-1, d)，输入扰动
    Y = pts[1:] - fp  # shape (n-1, d)，下一周期扰动
    # 解 Y ≈ X @ J^T  =>  J^T = lstsq(X, Y)
    Jt, *_ = np.linalg.lstsq(X, Y, rcond=None)
    J = Jt.T
    eigvals = np.linalg.eigvals(J)
    return {
        "jacobian": J,
        "eigvals": eigvals,
        "fixed_point": fp,
        "n_pairs": int(X.shape[0]),
    }
