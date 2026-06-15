"""Realtime IMU gait-event detection and rolling metrics."""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field

from .models import GaitEvent, JointAngles, RollingMetrics


def robinson_si(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    denom = 0.5 * (abs(left) + abs(right))
    if denom <= 1e-9:
        return 0.0
    return abs(left - right) / denom * 100.0


def mean_or_none(values: list[float]) -> float | None:
    return float(statistics.fmean(values)) if values else None


@dataclass
class FootEventDetector:
    """Heuristic online detector for HS/TO from foot acceleration and gyro."""

    side: str
    heel_accel_threshold_g: float = 1.22
    toe_off_gyro_threshold_dps: float = 80.0
    min_heel_interval_s: float = 0.22
    min_toe_interval_s: float = 0.12
    last_heel_s: float | None = None
    last_toe_s: float | None = None
    prev_gyro_pitch_dps: float = 0.0
    armed_for_heel: bool = True

    def update(self, t_s: float, foot_sample: dict[str, float]) -> list[GaitEvent]:
        ax = foot_sample["ax_g"]
        ay = foot_sample["ay_g"]
        az = foot_sample["az_g"]
        accel_norm = (ax * ax + ay * ay + az * az) ** 0.5
        gyro_pitch = float(foot_sample.get("gy_dps", 0.0))
        events: list[GaitEvent] = []

        heel_due = (
            self.last_heel_s is None
            or t_s - self.last_heel_s >= self.min_heel_interval_s
        )
        impact = accel_norm >= self.heel_accel_threshold_g
        swing_to_stance = self.prev_gyro_pitch_dps < -5.0 <= gyro_pitch
        if self.armed_for_heel and heel_due and (impact or swing_to_stance):
            events.append(GaitEvent(self.side, "heel_strike", t_s))
            self.last_heel_s = t_s
            self.armed_for_heel = False

        toe_due = (
            self.last_toe_s is None
            or t_s - self.last_toe_s >= self.min_toe_interval_s
        )
        after_heel = self.last_heel_s is not None and t_s - self.last_heel_s >= 0.08
        if (not self.armed_for_heel) and after_heel and toe_due:
            if gyro_pitch >= self.toe_off_gyro_threshold_dps:
                events.append(GaitEvent(self.side, "toe_off", t_s))
                self.last_toe_s = t_s
                self.armed_for_heel = True

        self.prev_gyro_pitch_dps = gyro_pitch
        return events


@dataclass
class RollingGaitMetrics:
    """Rolling step, stance/swing, ROM and asymmetry metrics."""

    window_s: float = 12.0
    heel_strikes: dict[str, deque[float]] = field(
        default_factory=lambda: {"left": deque(), "right": deque()}
    )
    toe_offs: dict[str, deque[float]] = field(
        default_factory=lambda: {"left": deque(), "right": deque()}
    )
    joint_history: deque[tuple[float, JointAngles]] = field(default_factory=deque)

    def update(
        self, t_s: float, joints: JointAngles, events: tuple[GaitEvent, ...]
    ) -> RollingMetrics:
        self.joint_history.append((t_s, joints))
        for event in events:
            target = self.heel_strikes if event.kind == "heel_strike" else self.toe_offs
            target[event.side].append(event.time_s)

        self._trim(t_s)
        return RollingMetrics(
            cadence_spm=self._cadence(),
            left_stance_s=self._stance("left"),
            right_stance_s=self._stance("right"),
            left_swing_s=self._swing("left"),
            right_swing_s=self._swing("right"),
            left_knee_rom_deg=self._rom("left_knee"),
            right_knee_rom_deg=self._rom("right_knee"),
            left_hip_rom_deg=self._rom("left_hip"),
            right_hip_rom_deg=self._rom("right_hip"),
        )

    def _trim(self, now_s: float) -> None:
        cutoff = now_s - self.window_s
        for queues in (self.heel_strikes, self.toe_offs):
            for queue in queues.values():
                while queue and queue[0] < cutoff:
                    queue.popleft()
        while self.joint_history and self.joint_history[0][0] < cutoff:
            self.joint_history.popleft()

    def _cadence(self) -> float:
        strikes = sorted([*self.heel_strikes["left"], *self.heel_strikes["right"]])
        if len(strikes) < 2:
            return 0.0
        elapsed = strikes[-1] - strikes[0]
        return 60.0 * (len(strikes) - 1) / elapsed if elapsed > 0.0 else 0.0

    def _stance(self, side: str) -> float | None:
        durations: list[float] = []
        toes = list(self.toe_offs[side])
        for heel in self.heel_strikes[side]:
            future_toes = [toe for toe in toes if toe > heel]
            if future_toes:
                durations.append(future_toes[0] - heel)
        return mean_or_none(durations)

    def _swing(self, side: str) -> float | None:
        durations: list[float] = []
        heels = list(self.heel_strikes[side])
        for toe in self.toe_offs[side]:
            future_heels = [heel for heel in heels if heel > toe]
            if future_heels:
                durations.append(future_heels[0] - toe)
        return mean_or_none(durations)

    def _rom(self, field_name: str) -> float | None:
        values = [getattr(joints, field_name) for _, joints in self.joint_history]
        if len(values) < 2:
            return None
        return max(values) - min(values)
