"""
V13.7 Identity Reproduction Test

目标：在 RL 环境设置中完整复现 V13.7 仿真循环，验证能否达到 4.63m 基线。

测试策略：
1. 使用 V13.7 的 initialize() 函数初始化（包含 initial_vx=0.03 等参数）
2. 1kHz 控制循环（timestep=0.001）
3. 完整的 FSM 状态机（support_foot, burst_start_t, accepted_contact 等）
4. 摩擦补偿（friction compensation）
5. L1 电机模型
6. V13.7 的 classify_failure() 终止条件

验收标准：
- 如果能复现 ≈4.6m → 环境正确，可以训练 PPO
- 如果不能 → 列出所有差异，逐个修复

参考基线（来自 v13_7_smoke_compensated_mx64ar_summary.json）：
- forward_distance: 4.63m
- simulated_time: 11.99s
- alternating_touchdowns: 10
- success: True
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import mujoco
import numpy as np

# 添加路径
RL_TRAINING_DIR = Path(__file__).resolve().parent
HW1_ROOT = RL_TRAINING_DIR.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14_DIR = HW1_ROOT / "v14_passive_arms"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V14C_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v14 import (
    classify_failure,
    contact_flags,
    initialize,
)
from simulate_v13_6 import _mechanical_energy, control_v136
from simulate_v13_7 import (
    MODEL_PATH,
    PassiveArmsParams,
    V137Params,
    make_v137_fsm,
    write_model_v137,
)

from common.motor_dynamics import (
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (
    L1MotorActuator,
    _sign_smooth,
)


@dataclass
class EpisodeResult:
    """单个 episode 的结果记录"""

    episode_id: int
    forward_distance: float
    simulated_time: float
    alternating_touchdowns: int
    success: bool
    failure_reason: str
    final_hip_x: float
    final_hip_z: float
    final_hip_vx: float
    contact_events: List[Dict[str, Any]]
    matches_baseline: bool
    deviation_from_baseline_m: float


class V137IdentitySimulator:
    """完整复现 V13.7 仿真循环的模拟器"""

    def __init__(self):
        """初始化 V13.7 参数和电机模型"""
        # 构建 V13.7 参数（与 simulate_v13_7.py 中 main() 一致）
        base0 = PassiveArmsParams()
        overrides = dict(
            duration=12.0,
            slope_deg=0.0,
            arm_mass=0.01,
            arm_length=0.40,
            arm_damping=0.02,
            arm_stiffness=0.0,
            thigh_length=float(base0.thigh_length * 1.02),
            shank_length=float(base0.shank_length * 1.02),
            step_length=float(base0.step_length * 1.02),
            foot_radius=0.042,
        )

        # 使用 dataclass replace
        from dataclasses import replace

        base = replace(base0, **overrides)
        fsm = make_v137_fsm(base)
        motor = MOTOR_PRESETS["mx64ar"]

        self.params = V137Params(
            base=base,
            fsm=fsm,
            hip_motor=motor,
            knee_motor=motor,
            compensate_friction=True,
        )

        # 构建模型
        write_model_v137(self.params)
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
        self.data = mujoco.MjData(self.model)

        # 电机模型
        self.actuators = {
            "left_hip": L1MotorActuator(self.params.hip_motor),
            "left_knee": L1MotorActuator(self.params.knee_motor),
            "right_hip": L1MotorActuator(self.params.hip_motor),
            "right_knee": L1MotorActuator(self.params.knee_motor),
        }

        # qvel 地址（与 V13.7 一致）
        self.qvel_addr = {
            "left_hip": 2,
            "left_knee": 3,
            "right_hip": 5,
            "right_knee": 6,
        }

    def run_episode(self, episode_id: int) -> EpisodeResult:
        """
        运行单个 episode，完整复现 V13.7 仿真循环

        Returns:
            EpisodeResult 包含距离、时间、步数等信息
        """
        p = self.params.base
        fsm = self.params.fsm

        # === 1. 初始化（使用 V13.7 的 initialize() 函数）===
        initialize(self.model, self.data, p)

        # 重置电机饱和计数器
        for act in self.actuators.values():
            act.saturation_count = 0

        # === 2. FSM 状态机初始化 ===
        start_x = float(self.data.qpos[0])
        max_x = start_x
        support_foot = "left"
        accepted_contact = ""
        candidate_start_t: Dict[str, float | None] = {"left": None, "right": None}
        contact_reported = {"left": False, "right": False}
        last_event_t = -1.0
        burst_start_t = -p.gait_period
        alternations = 0
        contact_events: List[Dict] = []

        failure = ""

        # === 3. 1kHz 控制循环 ===
        n_steps = int(p.duration / p.timestep)

        for step in range(n_steps):
            t = step * p.timestep

            # 计算当前机械能
            E_current = _mechanical_energy(p, self.data)

            # 调用 V13.6 FSM 控制律
            tau = control_v136(
                fsm, self.data, t, support_foot, burst_start_t, E_current
            )
            l_hip_des, l_knee_des, r_hip_des, r_knee_des = (
                tau[0],
                tau[1],
                tau[2],
                tau[3],
            )

            # === V13.7 核心：前馈摩擦补偿 ===
            if self.params.compensate_friction:
                l_hip_des = self._compensate(
                    l_hip_des,
                    float(self.data.qvel[self.qvel_addr["left_hip"]]),
                    self.params.hip_motor,
                )
                l_knee_des = self._compensate(
                    l_knee_des,
                    float(self.data.qvel[self.qvel_addr["left_knee"]]),
                    self.params.knee_motor,
                )
                r_hip_des = self._compensate(
                    r_hip_des,
                    float(self.data.qvel[self.qvel_addr["right_hip"]]),
                    self.params.hip_motor,
                )
                r_knee_des = self._compensate(
                    r_knee_des,
                    float(self.data.qvel[self.qvel_addr["right_knee"]]),
                    self.params.knee_motor,
                )

            # L1 电机模型（饱和 + 库仑摩擦）
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

            self.data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

            # MuJoCo step
            mujoco.mj_step(self.model, self.data)

            # 接触检测
            left_contact, right_contact = contact_flags(self.model, self.data)
            max_x = max(max_x, float(self.data.qpos[0]))

            # === FSM 状态更新（与 V13.7 完全一致）===
            contacts = {"left": left_contact, "right": right_contact}
            stable_feet: List[str] = []

            for foot, has_contact in contacts.items():
                if has_contact:
                    if candidate_start_t[foot] is None:
                        candidate_start_t[foot] = t
                        contact_reported[foot] = False
                    if t - float(candidate_start_t[foot]) >= p.stable_contact_time:
                        stable_feet.append(foot)
                else:
                    candidate_start_t[foot] = None
                    contact_reported[foot] = False

            for foot in stable_feet:
                if (
                    not contact_reported[foot]
                    and foot != accepted_contact
                    and t - last_event_t > p.min_event_interval
                ):
                    if accepted_contact in {"left", "right"}:
                        alternations += 1
                    accepted_contact = foot
                    support_foot = foot
                    burst_start_t = t
                    last_event_t = t
                    contact_reported[foot] = True
                    contact_events.append({"time": t, "foot": foot, "E": E_current})
                    break

            # === 失败检测（使用 V13.7 的 classify_failure）===
            failure = classify_failure(self.model, self.data, p, start_x, t)
            if failure:
                break

        # === 4. 结果统计 ===
        simulated_time = t
        forward_distance = max_x - start_x

        # 判断成功（与 V13.7 标准一致）
        SUCCESS_TIME = 10.0
        SUCCESS_TOUCHDOWNS = 10
        SUCCESS_FORWARD = 0.8

        success = (
            simulated_time >= SUCCESS_TIME
            and alternations >= SUCCESS_TOUCHDOWNS
            and forward_distance >= SUCCESS_FORWARD
            and not failure
        )

        # 与基线对比（基线：4.63m, 12s, 10 touchdowns）
        BASELINE_DISTANCE = 4.63
        deviation = abs(forward_distance - BASELINE_DISTANCE)
        matches_baseline = deviation < 0.3  # 允许 30cm 误差

        return EpisodeResult(
            episode_id=episode_id,
            forward_distance=forward_distance,
            simulated_time=simulated_time,
            alternating_touchdowns=alternations,
            success=success,
            failure_reason=failure or "completed",
            final_hip_x=float(self.data.qpos[0]),
            final_hip_z=float(self.data.qpos[1]),
            final_hip_vx=float(self.data.qvel[0]),
            contact_events=contact_events,
            matches_baseline=matches_baseline,
            deviation_from_baseline_m=deviation,
        )

    def _compensate(self, tau_fsm: float, omega_joint: float, motor) -> float:
        """前馈摩擦补偿（与 V13.7 一致）"""
        tau_C_eff = motor.joint_tau_C_eff()
        return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor.omega_eps)


def run_identity_test(num_episodes: int = 5) -> Dict[str, Any]:
    """
    运行身份复现测试

    Args:
        num_episodes: 运行的 episode 数（用于统计稳定性）

    Returns:
        测试结果字典
    """
    print("=" * 80)
    print("V13.7 Identity Reproduction Test")
    print("=" * 80)
    print("Goal: Reproduce V13.7 baseline of 4.63m in isolated environment")
    print(f"Number of episodes: {num_episodes}")
    print()

    # 初始化模拟器
    print("Initializing V13.7 simulator...")
    simulator = V137IdentitySimulator()
    print("[OK] Simulator initialized")
    print(f"  - Model path: {MODEL_PATH}")
    print(f"  - Control frequency: {1.0 / simulator.params.base.timestep:.0f} Hz")
    print(f"  - Motor model: {simulator.params.hip_motor.name}")
    print(
        f"  - Friction compensation: {'ON' if simulator.params.compensate_friction else 'OFF'}"
    )
    print()

    # 运行多个 episodes
    results: List[EpisodeResult] = []

    print("Running test episodes...")
    print("-" * 80)

    for ep in range(num_episodes):
        result = simulator.run_episode(ep)
        results.append(result)

        # 打印单个 episode 结果
        status = "[SUCCESS]" if result.success else "[FAIL]"
        baseline_match = "[MATCH]" if result.matches_baseline else "[MISMATCH]"

        print(
            f"Episode {ep + 1}: {status} {baseline_match} | "
            f"distance={result.forward_distance:.3f}m | "
            f"time={result.simulated_time:.2f}s | "
            f"touchdowns={result.alternating_touchdowns} | "
            f"failure={result.failure_reason}"
        )

    print()

    # === 统计分析 ===
    print("=" * 80)
    print("STATISTICAL ANALYSIS")
    print("=" * 80)

    distances = [r.forward_distance for r in results]
    times = [r.simulated_time for r in results]
    touchdowns = [r.alternating_touchdowns for r in results]
    successes = [r.success for r in results]
    matches = [r.matches_baseline for r in results]

    avg_distance = np.mean(distances)
    std_distance = np.std(distances)
    max_distance = np.max(distances)
    min_distance = np.min(distances)

    avg_time = np.mean(times)
    avg_touchdowns = np.mean(touchdowns)

    success_rate = sum(successes) / len(successes)
    match_rate = sum(matches) / len(matches)

    print("Distance Statistics:")
    print(f"  Average: {avg_distance:.3f} +/- {std_distance:.3f} m")
    print(f"  Range: [{min_distance:.3f}, {max_distance:.3f}] m")
    print("  Baseline: 4.630 m")
    print(
        f"  Deviation: {avg_distance - 4.63:+.3f} m ({(avg_distance / 4.63 - 1) * 100:+.1f}%)"
    )
    print()

    print("Time Statistics:")
    print(f"  Average: {avg_time:.2f} s")
    print("  Baseline: 11.99 s")
    print()

    print("Touchdown Statistics:")
    print(f"  Average: {avg_touchdowns:.1f} touchdowns")
    print("  Baseline: 10 touchdowns")
    print()

    print(
        f"Success Rate: {success_rate * 100:.0f}% ({sum(successes)}/{len(successes)})"
    )
    print(
        f"Baseline Match Rate: {match_rate * 100:.0f}% ({sum(matches)}/{len(matches)})"
    )
    print()

    # === 诊断结论 ===
    print("=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    BASELINE_DISTANCE = 4.63
    tolerance = 0.3  # 30cm

    if match_rate >= 0.8:  # 80% 的 episodes 匹配基线
        print("[PASS] Successfully reproduced V13.7 baseline!")
        print(
            f"  - Average distance {avg_distance:.3f}m within {tolerance}m of baseline {BASELINE_DISTANCE}m"
        )
        print(f"  - {match_rate * 100:.0f}% of episodes match baseline")
        print()
        print(
            "Conclusion: Environment setup is correct, V13.7 controller works stably."
        )
        print("Recommendation: Ready to train PPO model.")
        diagnosis = "PASS"
    else:
        print("[FAIL] Failed to reproduce V13.7 baseline")
        print(
            f"  - Average distance {avg_distance:.3f}m differs from baseline {BASELINE_DISTANCE}m by {abs(avg_distance - BASELINE_DISTANCE):.3f}m"
        )
        print(f"  - Only {match_rate * 100:.0f}% of episodes match baseline")
        print()

        # 详细差异分析
        print("Possible Causes:")

        # 检查是否所有 episodes 都早期失败
        early_failures = sum(
            1 for r in results if r.simulated_time < 2.0 and not r.success
        )
        if early_failures >= len(results) * 0.5:
            print("  1. [HIGH] Early failure pattern detected")
            print(f"     - {early_failures}/{len(results)} episodes failed within 2s")
            print("     - Possibly wrong initialization (qpos/qvel)")
            print("     - Possibly wrong FSM initial state")

        # 检查是否距离偏差过大但时间正常
        if avg_time > 10.0 and avg_distance < BASELINE_DISTANCE * 0.8:
            print("  2. [HIGH] Normal duration but insufficient distance")
            print("     - Possibly excessive friction coefficient")
            print("     - Possibly wrong motor torque limits")
            print("     - Possibly mismatched physical parameters")

        # 检查是否不稳定（标准差过大）
        if std_distance > 1.0:
            print("  3. [MEDIUM] Unstable results (high std dev)")
            print(f"     - Std dev {std_distance:.3f}m > 1.0m")
            print("     - Possibly unfixed random seed")
            print("     - Possibly numerical integration error accumulation")

        diagnosis = "FAIL"

        print()
        print("Recommended Actions:")
        print(
            "  1. Compare initialize() in simulate_v13_7.py with current implementation"
        )
        print("  2. Check if model XML matches V13.7 (armature/damping)")
        print(
            "  3. Print first 100 steps qpos/qvel/ctrl and compare with original V13.7"
        )
        print("  4. Verify FSM state transition times match original")

    print()

    # 构建返回结果
    summary = {
        "diagnosis": diagnosis,
        "num_episodes": num_episodes,
        "baseline": {
            "forward_distance": 4.63,
            "simulated_time": 11.99,
            "alternating_touchdowns": 10,
        },
        "statistics": {
            "avg_distance": float(avg_distance),
            "std_distance": float(std_distance),
            "max_distance": float(max_distance),
            "min_distance": float(min_distance),
            "avg_time": float(avg_time),
            "avg_touchdowns": float(avg_touchdowns),
            "success_rate": float(success_rate),
            "baseline_match_rate": float(match_rate),
        },
        "episodes": [asdict(r) for r in results],
    }

    return summary


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V13.7 Identity Reproduction Test")
    parser.add_argument("--episodes", type=int, default=5, help="运行的 episode 数")
    parser.add_argument(
        "--save",
        type=str,
        default="v137_identity_test_report.json",
        help="保存结果的文件名",
    )

    args = parser.parse_args()

    # 运行测试
    summary = run_identity_test(num_episodes=args.episodes)

    # 保存结果
    save_path = RL_TRAINING_DIR / args.save
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Test results saved to: {save_path}")
    print()

    # 返回退出码（用于 CI/CD）
    exit_code = 0 if summary["diagnosis"] == "PASS" else 1
    return exit_code


if __name__ == "__main__":
    exit(main())
