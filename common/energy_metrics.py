"""Energy metrics for gait simulation analysis."""

from __future__ import annotations

import mujoco
import numpy as np


def cost_of_transport(
    input_energy_j: float, mass_kg: float, distance_m: float, g: float = 9.81
) -> float:
    """Return dimensionless CoT = E / (m g d)."""
    denom = mass_kg * g * max(distance_m, 1e-9)
    if denom <= 0.0:
        return float("inf")
    return input_energy_j / denom


def spring_potential_energy(k: float, extension: float, ref: float = 0.0) -> float:
    """Return linear spring potential energy: 0.5 * k * (extension - ref)^2."""
    delta = extension - ref
    return 0.5 * k * delta * delta


def compute_power_components(
    time: np.ndarray,
    total_energy: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute positive input and dissipated power from total energy."""
    time = np.asarray(time, dtype=float)
    total_energy = np.asarray(total_energy, dtype=float)
    if time.shape != total_energy.shape:
        raise ValueError("time and total_energy must have the same shape")
    if len(time) < 2:
        zeros = np.zeros_like(time)
        return zeros, zeros

    dt = np.diff(time)
    if np.any(dt <= 0.0):
        raise ValueError("time samples must be strictly increasing")

    dE_dt = np.zeros_like(total_energy)
    dE_dt[0] = (total_energy[1] - total_energy[0]) / dt[0]
    dE_dt[-1] = (total_energy[-1] - total_energy[-2]) / dt[-1]
    for i in range(1, len(time) - 1):
        dE_dt[i] = (total_energy[i + 1] - total_energy[i - 1]) / (
            time[i + 1] - time[i - 1]
        )

    power_input = np.maximum(dE_dt, 0.0)
    power_dissipation = np.maximum(-dE_dt, 0.0)
    return power_input, power_dissipation


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
    """Compute approximate hip-body mechanical energy time series from rows."""
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
        for spring in springs:
            k = float(spring["k"])
            ref = float(spring.get("ref", 0.0))
            key = spring["key"]
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
    """Estimate energy drop around support-foot transitions."""
    if not rows:
        return []

    series = mechanical_energy_series(rows, mass_kg=mass_kg, g=g, **energy_kwargs)
    total = series["total"]
    t = series["time"]
    events: list[dict] = []
    last_support = rows[0].get(support_key, "")
    step = 0

    for i in range(1, len(rows)):
        cur = rows[i].get(support_key, "")
        if (
            cur != last_support
            and cur in {"left", "right"}
            and last_support in {"left", "right"}
        ):
            i_pre = max(0, i - window)
            i_post = min(len(rows) - 1, i + window)
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


class EnergyAnalyzer:
    """Analyze mechanical energy, power flow, collision losses and CoT."""

    def __init__(self, model: mujoco.MjModel, g: float = 9.81):
        self.model = model
        self.g = g
        self.mass_kg = float(np.sum(model.body_mass))

    def analyze_trajectory(
        self,
        trajectory: dict[str, np.ndarray],
        vx_key: str = "hip_x_vel",
        vz_key: str = "hip_z_vel",
        z_key: str = "hip_z",
        t_key: str = "time",
        support_key: str = "support_foot",
        ctrl_key: str = "ctrl",
        springs: list[dict] | None = None,
    ) -> dict:
        """Analyze trajectory energy flow."""
        if not trajectory or t_key not in trajectory:
            return self._empty_result()

        n_steps = len(trajectory[t_key])
        rows = []
        for i in range(n_steps):
            row = {}
            for key, values in trajectory.items():
                if isinstance(values, np.ndarray) and len(values) == n_steps:
                    row[key] = values[i]
                elif isinstance(values, (list, tuple)) and len(values) == n_steps:
                    row[key] = values[i]
            rows.append(row)

        energy_series = mechanical_energy_series(
            rows,
            mass_kg=self.mass_kg,
            g=self.g,
            vx_key=vx_key,
            vz_key=vz_key,
            z_key=z_key,
            t_key=t_key,
            springs=springs,
        )

        time = energy_series["time"]
        kinetic = energy_series["ke"]
        potential = energy_series["pe"]
        total = energy_series["total"]
        power_input, power_dissipation = self._compute_power(
            time, total, trajectory.get(ctrl_key)
        )

        collision_events = collision_loss_per_step(
            rows,
            mass_kg=self.mass_kg,
            g=self.g,
            support_key=support_key,
            vx_key=vx_key,
            vz_key=vz_key,
            z_key=z_key,
            t_key=t_key,
            springs=springs,
        )

        collision_times = np.array([e["time"] for e in collision_events])
        collision_losses = np.array([e["dE_J"] for e in collision_events])
        total_energy_input = self._compute_total_energy_input(time, power_input)
        distance = self._compute_distance(trajectory)
        cot_value = cost_of_transport(
            total_energy_input, self.mass_kg, distance, self.g
        )

        return {
            "time": time,
            "kinetic": kinetic,
            "potential": potential,
            "total": total,
            "power_input": power_input,
            "power_dissipation": power_dissipation,
            "collision_times": collision_times,
            "collision_losses": collision_losses,
            "cot": cot_value,
            "total_energy_input": total_energy_input,
            "distance": distance,
        }

    def _compute_power(
        self, time: np.ndarray, total_energy: np.ndarray, ctrl: np.ndarray | None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute input and dissipated power for a trajectory."""
        return compute_power_components(time, total_energy)

    def _compute_total_energy_input(
        self, time: np.ndarray, power_input: np.ndarray
    ) -> float:
        """Integrate positive input power."""
        if len(time) < 2:
            return 0.0
        return float(np.trapz(power_input, time))

    def _compute_distance(self, trajectory: dict[str, np.ndarray]) -> float:
        """Compute forward distance from hip_x or qpos."""
        if "hip_x" in trajectory:
            x = trajectory["hip_x"]
            return float(x[-1] - x[0]) if len(x) > 0 else 0.0
        if "qpos" in trajectory:
            qpos = trajectory["qpos"]
            if isinstance(qpos, np.ndarray) and qpos.ndim == 2 and qpos.shape[0] > 0:
                return float(qpos[-1, 0] - qpos[0, 0])
        return 0.0

    def _empty_result(self) -> dict:
        """Return an empty analysis result."""
        empty = np.empty(0)
        return {
            "time": empty,
            "kinetic": empty,
            "potential": empty,
            "total": empty,
            "power_input": empty,
            "power_dissipation": empty,
            "collision_times": empty,
            "collision_losses": empty,
            "cot": float("inf"),
            "total_energy_input": 0.0,
            "distance": 0.0,
        }
