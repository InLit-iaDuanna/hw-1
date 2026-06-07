"""优化版控制器 - 使用 numpy 向量化。

优化策略:
1. 向量化 PD 控制计算（批量处理 4 个关节）
2. 预分配数组避免重复创建
3. 减少函数调用开销

预期加速: 1.1-1.3x（纯 numpy，无 JIT）
如需更高性能，可安装 numba: pip install numba
"""

from __future__ import annotations

import math

import numpy as np


def limited_pd_vectorized(
    q: np.ndarray,
    qd: np.ndarray,
    target: np.ndarray,
    kp: np.ndarray,
    kd: np.ndarray,
    limit: np.ndarray,
) -> np.ndarray:
    """向量化 PD 控制器（4 个关节同时计算）。

    Args:
        q: 关节位置 [left_hip, left_knee, right_hip, right_knee]
        qd: 关节速度 [left_hip_vel, ...]
        target: 目标位置 [...]
        kp: 比例增益 [...]
        kd: 微分增益 [...]
        limit: 力矩限制 [...]

    Returns:
        tau: 输出力矩 [...]
    """
    tau = kp * (target - q) - kd * qd
    return np.clip(tau, -limit, limit)


class OptimizedController:
    """优化的控制器类 - 预分配缓冲区减少内存分配。"""

    def __init__(self, params):
        """初始化并预分配数组。"""
        self.params = params

        # 预分配数组
        self.q = np.zeros(4)
        self.qd = np.zeros(4)
        self.target = np.zeros(4)
        self.kp = np.array(
            [params.hip_kp, params.knee_kp, params.hip_kp, params.knee_kp]
        )
        self.kd = np.array(
            [params.hip_kd, params.knee_kd, params.hip_kd, params.knee_kd]
        )
        self.limit = np.array(
            [
                params.hip_torque_limit,
                params.knee_torque_limit,
                params.hip_torque_limit,
                params.knee_torque_limit,
            ]
        )

        # 缓存三角函数常量
        self.gamma = params.gamma
        self.stance_front_rad = math.radians(params.stance_front_deg)
        self.stance_back_rad = math.radians(params.stance_back_deg)
        self.swing_back_rad = math.radians(params.swing_back_deg)
        self.swing_front_rad = math.radians(params.swing_front_deg)
        self.swing_knee_flex_rad = math.radians(params.swing_knee_flex_deg)
        self.stance_knee_rad = math.radians(params.stance_knee_deg)

    def smoothstep(self, u: float) -> float:
        """平滑阶跃函数。"""
        u = min(max(u, 0.0), 1.0)
        return u * u * (3.0 - 2.0 * u)

    def compute_targets(self, u: float, support_foot_left: bool):
        """计算目标角度并填充到预分配的 target 数组。"""
        s = self.smoothstep(u)

        stance_hip = (
            self.gamma
            + self.stance_front_rad
            + (self.stance_back_rad - self.stance_front_rad) * s
        )
        swing_hip = (
            self.gamma
            + self.swing_back_rad
            + (self.swing_front_rad - self.swing_back_rad) * s
        )
        swing_knee = self.swing_knee_flex_rad * math.sin(math.pi * u)
        stance_knee = self.stance_knee_rad

        if support_foot_left:
            self.target[0] = stance_hip
            self.target[1] = stance_knee
            self.target[2] = swing_hip
            self.target[3] = swing_knee
        else:
            self.target[0] = swing_hip
            self.target[1] = swing_knee
            self.target[2] = stance_hip
            self.target[3] = stance_knee

    def control(
        self, data, t: float, support_foot: str, burst_start_t: float
    ) -> tuple[float, float, float, float]:
        """优化的控制计算。"""
        hip_x = float(data.qpos[0])
        hip_z = float(data.qpos[1])
        clearance = hip_z - (-math.tan(self.gamma) * hip_x)

        u = min(max((t - burst_start_t) / max(self.params.gait_period, 1e-6), 0.0), 1.0)

        if clearance < self.params.recovery_clearance:
            u = min(u, 0.55)

        # 填充状态向量（复用预分配数组）
        self.q[0] = data.qpos[2]
        self.q[1] = data.qpos[3]
        self.q[2] = data.qpos[5]
        self.q[3] = data.qpos[6]

        self.qd[0] = data.qvel[2]
        self.qd[1] = data.qvel[3]
        self.qd[2] = data.qvel[5]
        self.qd[3] = data.qvel[6]

        # 计算目标
        self.compute_targets(u, support_foot == "left")

        # 向量化 PD 控制
        tau = limited_pd_vectorized(
            self.q, self.qd, self.target, self.kp, self.kd, self.limit
        )

        return float(tau[0]), float(tau[1]), float(tau[2]), float(tau[3])


if __name__ == "__main__":
    print("测试优化控制器（numpy 向量化版本）...")

    # 模拟参数对象
    class DummyParams:
        gait_period = 1.0
        gamma = 0.0
        recovery_clearance = 0.38
        stance_front_deg = -14.0
        stance_back_deg = 22.0
        swing_back_deg = 20.0
        swing_front_deg = -22.0
        swing_knee_flex_deg = 28.0
        stance_knee_deg = 2.0
        hip_kp = 18.0
        hip_kd = 4.0
        knee_kp = 10.0
        knee_kd = 1.2
        hip_torque_limit = 8.0
        knee_torque_limit = 2.0

    # 模拟 MuJoCo data 对象
    class DummyData:
        def __init__(self):
            self.qpos = np.array([0.0, 1.0, 0.1, 0.05, 0.0, -0.1, 0.03, 0.0])
            self.qvel = np.array([0.5, 0.0, 0.2, 0.1, 0.0, -0.15, 0.08, 0.0])

    params = DummyParams()
    controller = OptimizedController(params)
    data = DummyData()

    import time

    n_iter = 10000
    start = time.perf_counter()

    for i in range(n_iter):
        tau = controller.control(
            data, float(i) * 0.001, "left" if i % 2 == 0 else "right", 0.0
        )

    elapsed = time.perf_counter() - start

    print(f"完成 {n_iter} 次控制计算")
    print(f"总耗时: {elapsed:.4f}s")
    print(f"平均每次: {elapsed/n_iter*1e6:.2f}μs")
    print(f"示例输出: {tau}")
