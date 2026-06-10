"""Hold频率消融实验：测试V13.7在不同控制频率下的性能。

目标：确定最低可接受的控制频率，为Residual RL方案提供参数依据。

实验设置：
- 使用V13.7原生1kHz循环（dt=0.001s）
- 测试不同hold时间：1ms, 2ms, 5ms, 10ms, 20ms
- 每个配置运行10个episodes
- 记录：forward_distance, success_rate, alternating_touchdowns

运行方式：
    cd D:\Dunna\Documents\hw-1
    .venv-mujoco\Scripts\activate
    python rl_training\test_hold_frequency_ablation.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
from tqdm import tqdm

# 添加路径
HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_v13_7 import (
    MODEL_PATH,
    V137Params,
    _compensate,
    _mechanical_energy,
    write_model_v137,
)
from simulate_v13_6 import control_v136
from simulate_passive_arms_v14 import (
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    contact_flags,
    classify_failure,
)
from common.motor_dynamics import L1MotorActuator, PRESETS as MOTOR_PRESETS


class V137HoldFrequencyTester:
    """V13.7控制器 + Hold频率测试。"""

    def __init__(self, params: V137Params, hold_steps: int = 1):
        """初始化测试器。

        Args:
            params: V13.7参数
            hold_steps: 每个控制命令hold的步数（1=1kHz, 20=50Hz）
        """
        self.params = params
        self.hold_steps = hold_steps
        self.dt = 0.001  # 1kHz仿真步长

        # 加载模型
        write_model_v137(params)
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
        self.data = mujoco.MjData(self.model)

        # 电机执行器
        self.actuators = {
            "left_hip": L1MotorActuator(params.hip_motor),
            "left_knee": L1MotorActuator(params.knee_motor),
            "right_hip": L1MotorActuator(params.hip_motor),
            "right_knee": L1MotorActuator(params.knee_motor),
        }
        self.qvel_addr = {
            "left_hip": 2,
            "left_knee": 3,
            "right_hip": 5,
            "right_knee": 6,
        }

        # FSM状态
        self.support_foot = "left"
        self.burst_start_t = 0.0
        self.touchdowns = []

    def reset(self):
        """重置环境。"""
        mujoco.mj_resetData(self.model, self.data)

        # 初始姿态：髋部高度1m，左腿轻微前倾
        self.data.qpos[0] = 0.0  # hip_x
        self.data.qpos[1] = 1.0  # hip_z
        self.data.qpos[2] = 0.05  # left_hip (5度前倾)
        self.data.qpos[5] = -0.05  # right_hip (5度后倾)

        # 添加小扰动
        noise = np.random.normal(0, 0.01, size=6)
        for i in range(6):
            self.data.qpos[i+2] += noise[i]

        mujoco.mj_forward(self.model, self.data)

        # 重置FSM
        self.support_foot = "left"
        self.burst_start_t = 0.0
        self.touchdowns = []

        # 重置电机饱和计数
        for act in self.actuators.values():
            act.saturation_count = 0

    def _compute_v137_control(self, t: float) -> np.ndarray:
        """计算V13.7控制力矩（完整版本）。

        Returns:
            4维力矩数组 [left_hip, left_knee, right_hip, right_knee]
        """
        E_current = _mechanical_energy(self.params.base, self.data)

        # V13.6 FSM控制律
        tau = control_v136(
            self.params.fsm,
            self.data,
            t,
            self.support_foot,
            self.burst_start_t,
            E_current
        )
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        # 前馈摩擦补偿
        if self.params.compensate_friction:
            l_hip_des = _compensate(
                l_hip_des,
                float(self.data.qvel[self.qvel_addr["left_hip"]]),
                self.params.hip_motor,
            )
            l_knee_des = _compensate(
                l_knee_des,
                float(self.data.qvel[self.qvel_addr["left_knee"]]),
                self.params.knee_motor,
            )
            r_hip_des = _compensate(
                r_hip_des,
                float(self.data.qvel[self.qvel_addr["right_hip"]]),
                self.params.hip_motor,
            )
            r_knee_des = _compensate(
                r_knee_des,
                float(self.data.qvel[self.qvel_addr["right_knee"]]),
                self.params.knee_motor,
            )

        # L1电机模型
        l_hip_out, _ = self.actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(self.data.qvel[self.qvel_addr["left_hip"]])
        )
        l_knee_out, _ = self.actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(self.data.qvel[self.qvel_addr["left_knee"]])
        )
        r_hip_out, _ = self.actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(self.data.qvel[self.qvel_addr["right_hip"]])
        )
        r_knee_out, _ = self.actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(self.data.qvel[self.qvel_addr["right_knee"]])
        )

        return np.array([l_hip_out, l_knee_out, r_hip_out, r_knee_out], dtype=np.float64)

    def _update_contact_events(self, t: float):
        """更新触地事件检测。"""
        left_c, right_c = contact_flags(self.model, self.data)

        # 检测新触地事件
        if left_c and self.support_foot != "left":
            self.support_foot = "left"
            self.burst_start_t = t
            self.touchdowns.append(("left", t))
        elif right_c and self.support_foot != "right":
            self.support_foot = "right"
            self.burst_start_t = t
            self.touchdowns.append(("right", t))

    def _is_fallen(self) -> bool:
        """判断是否摔倒。"""
        hip_z = float(self.data.qpos[1])
        hip_y = float(self.data.xpos[self.model.body("hip").id][1])
        return hip_z < 0.2 or abs(hip_y) > 0.5

    def run_episode(self, max_time: float = 10.0) -> dict[str, Any]:
        """运行一个episode。

        Args:
            max_time: 最大仿真时间（秒）

        Returns:
            结果字典：{forward_distance, final_time, success, alternating_touchdowns}
        """
        self.reset()

        t = 0.0
        step_count = 0
        ctrl_hold = None  # 缓存的控制命令

        while t < max_time:
            # 每hold_steps步更新一次控制命令
            if step_count % self.hold_steps == 0:
                ctrl_hold = self._compute_v137_control(t)

            # 应用控制
            self.data.ctrl[:] = ctrl_hold

            # 仿真步进
            mujoco.mj_step(self.model, self.data)
            t += self.dt
            step_count += 1

            # 更新触地事件
            self._update_contact_events(t)

            # 检查摔倒
            if self._is_fallen():
                break

        # 统计结果
        forward_distance = float(self.data.qpos[0])
        final_time = t

        # 成功判断
        success = (
            forward_distance >= SUCCESS_FORWARD
            and final_time >= SUCCESS_TIME
            and len(self.touchdowns) >= SUCCESS_TOUCHDOWNS
        )

        # 交替触地判断（左右交替）
        alternating = True
        if len(self.touchdowns) >= 2:
            for i in range(1, len(self.touchdowns)):
                if self.touchdowns[i][0] == self.touchdowns[i-1][0]:
                    alternating = False
                    break

        return {
            "forward_distance": forward_distance,
            "final_time": final_time,
            "success": success,
            "alternating_touchdowns": alternating,
            "num_touchdowns": len(self.touchdowns),
        }


def run_ablation_study():
    """运行Hold频率消融实验。"""
    # V13.7默认参数
    from simulate_v14c import make_v14c_params
    base_params = make_v14c_params(slope_deg=0.0)

    # 创建V137Params
    params = V137Params(
        base=base_params,
        fsm=base_params,  # make_v14c_params返回的已经是FSM参数
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
        compensate_friction=True,
    )

    # 测试配置：hold_steps -> 控制频率
    test_configs = [
        (1, 1000),   # 1ms hold = 1kHz
        (2, 500),    # 2ms hold = 500Hz
        (5, 200),    # 5ms hold = 200Hz
        (10, 100),   # 10ms hold = 100Hz
        (20, 50),    # 20ms hold = 50Hz
    ]

    num_episodes = 10
    results = []

    print("=" * 80)
    print("V13.7 Hold频率消融实验")
    print("=" * 80)
    print(f"每个配置运行 {num_episodes} episodes")
    print(f"成功标准: forward ≥ {SUCCESS_FORWARD}m, time ≥ {SUCCESS_TIME}s, touchdowns ≥ {SUCCESS_TOUCHDOWNS}")
    print("=" * 80)

    for hold_steps, freq_hz in test_configs:
        print(f"\n测试配置: hold={hold_steps}ms ({freq_hz}Hz)")
        print("-" * 80)

        tester = V137HoldFrequencyTester(params, hold_steps=hold_steps)

        episode_results = []
        for ep in tqdm(range(num_episodes), desc=f"Hold={hold_steps}ms"):
            result = tester.run_episode(max_time=10.0)
            episode_results.append(result)

        # 统计
        forward_distances = [r["forward_distance"] for r in episode_results]
        success_rate = sum(r["success"] for r in episode_results) / num_episodes
        alternating_rate = sum(r["alternating_touchdowns"] for r in episode_results) / num_episodes
        avg_touchdowns = np.mean([r["num_touchdowns"] for r in episode_results])

        result_summary = {
            "hold_ms": hold_steps,
            "freq_hz": freq_hz,
            "avg_forward_distance": np.mean(forward_distances),
            "std_forward_distance": np.std(forward_distances),
            "min_forward_distance": np.min(forward_distances),
            "max_forward_distance": np.max(forward_distances),
            "success_rate": success_rate,
            "alternating_rate": alternating_rate,
            "avg_touchdowns": avg_touchdowns,
        }
        results.append(result_summary)

        # 打印结果
        print(f"  平均前进距离: {result_summary['avg_forward_distance']:.2f} ± {result_summary['std_forward_distance']:.2f} m")
        print(f"  成功率: {success_rate:.1%}")
        print(f"  交替触地率: {alternating_rate:.1%}")
        print(f"  平均触地次数: {avg_touchdowns:.1f}")

    # 汇总报告
    print("\n" + "=" * 80)
    print("汇总结果")
    print("=" * 80)
    print(f"{'Hold(ms)':<10} {'频率(Hz)':<10} {'平均距离(m)':<15} {'成功率':<10} {'交替触地率':<12}")
    print("-" * 80)

    for r in results:
        print(f"{r['hold_ms']:<10} {r['freq_hz']:<10} "
              f"{r['avg_forward_distance']:.2f}±{r['std_forward_distance']:.2f}       "
              f"{r['success_rate']:.1%}      {r['alternating_rate']:.1%}")

    # 保存结果
    import json
    output_file = HW1_ROOT / "rl_training" / "hold_frequency_ablation_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n结果已保存到: {output_file}")

    # 推荐
    print("\n" + "=" * 80)
    print("推荐方案")
    print("=" * 80)

    # 找到成功率≥80%的最低频率
    acceptable = [r for r in results if r["success_rate"] >= 0.8]
    if acceptable:
        best = min(acceptable, key=lambda x: x["freq_hz"])
        print(f"最低可接受频率: {best['freq_hz']}Hz (hold={best['hold_ms']}ms)")
        print(f"  - 成功率: {best['success_rate']:.1%}")
        print(f"  - 平均前进距离: {best['avg_forward_distance']:.2f}m")
        print(f"\n推荐Residual RL配置:")
        print(f"  - PPO频率: {best['freq_hz']}Hz")
        print(f"  - 内环hold: {best['hold_ms']}个1ms步")
    else:
        print("警告：所有测试配置成功率均<80%，推荐使用1kHz全速控制")


if __name__ == "__main__":
    run_ablation_study()
