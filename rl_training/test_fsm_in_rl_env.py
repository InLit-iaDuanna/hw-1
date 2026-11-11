"""
测试脚本：在 RL 环境中对比 4 种控制策略

目标：诊断 V13.7 FSM 在 RL 环境中的表现，判断失败原因是：
  1. 环境/初始化不一致
  2. Reward 设计错误
  3. 其他物理参数差异

控制策略：
  - Zero action（基线）
  - Random action（探索上界）
  - V13.7 FSM 控制器（原始控制律）
  - PPO 训练模型（RL 策略）

记录数据：
  - 距离、步数、持续时间、成功/失败
  - 终止原因（需修改 environment.py 添加 termination_reason）
  - Reward 分解（forward/energy/smoothness）
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# 添加路径以导入环境和 FSM 控制器
RL_TRAINING_DIR = Path(__file__).resolve().parent
HW1_ROOT = RL_TRAINING_DIR.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14_DIR = HW1_ROOT / "v14_passive_arms"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"

sys.path.insert(0, str(RL_TRAINING_DIR))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V14C_DIR))
sys.path.insert(0, str(HW1_ROOT))

from environment import CompassGaitEnv
from simulate_v13_6 import _mechanical_energy, control_v136
from simulate_v13_7 import (
    PassiveArmsParams,
    make_v137_fsm,
)

from common.motor_dynamics import PRESETS as MOTOR_PRESETS
from common.motor_dynamics import _sign_smooth


@dataclass
class EpisodeResult:
    """单个 episode 的结果记录"""

    strategy: str
    episode_id: int
    distance: float
    steps: int
    duration: float
    success: bool
    termination_reason: str
    final_height: float
    final_velocity: float
    total_reward: float
    forward_reward: float
    energy_cost: float
    smoothness_cost: float
    avg_action_magnitude: float


class FSMController:
    """将 V13.7 FSM 封装为 RL-compatible 控制器"""

    def __init__(self):
        # 构建 V13.7 参数
        base = PassiveArmsParams()
        fsm = make_v137_fsm(base)
        hip_motor = MOTOR_PRESETS["mx64ar"]
        knee_motor = MOTOR_PRESETS["mx64ar"]

        self.params_base = base
        self.params_fsm = fsm
        self.hip_motor = hip_motor
        self.knee_motor = knee_motor

        # FSM 状态
        self.support_foot = "left"
        self.burst_start_t = -base.gait_period
        self.last_event_t = -1.0
        self.accepted_contact = ""
        self.candidate_start_t = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}

        # 用于摩擦补偿
        self.compensate_friction = True

    def reset(self):
        """重置 FSM 状态"""
        self.support_foot = "left"
        self.burst_start_t = -self.params_base.gait_period
        self.last_event_t = -1.0
        self.accepted_contact = ""
        self.candidate_start_t = {"left": None, "right": None}
        self.contact_reported = {"left": False, "right": False}

    def _get_contact_flags(self, env: CompassGaitEnv) -> Tuple[bool, bool]:
        """从环境获取接触状态"""
        contact_states = env._get_contact_states()
        # left_heel, left_toe, right_heel, right_toe
        left_contact = bool(contact_states[0] or contact_states[1])
        right_contact = bool(contact_states[2] or contact_states[3])
        return left_contact, right_contact

    def _update_fsm_state(self, t: float, left_contact: bool, right_contact: bool):
        """更新 FSM 状态机（接触事件检测）"""
        p = self.params_base
        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: List[str] = []

        for foot, has_contact in contacts.items():
            if has_contact:
                if self.candidate_start_t[foot] is None:
                    self.candidate_start_t[foot] = t
                    self.contact_reported[foot] = False
                if t - float(self.candidate_start_t[foot]) >= p.stable_contact_time:
                    stable_feet.append(foot)
            else:
                self.candidate_start_t[foot] = None
                self.contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not self.contact_reported[foot]
                and foot != self.accepted_contact
                and t - self.last_event_t > p.min_event_interval
            ):
                self.accepted_contact = foot
                self.support_foot = foot
                self.burst_start_t = t
                self.last_event_t = t
                self.contact_reported[foot] = True
                break

    def compute_action(self, env: CompassGaitEnv, t: float) -> np.ndarray:
        """
        计算 FSM 控制动作

        Args:
            env: RL 环境实例
            t: 当前时间（秒）

        Returns:
            4 维动作向量 [left_hip, left_knee, right_hip, right_knee]
        """
        data = env.data

        # 更新接触状态
        left_contact, right_contact = self._get_contact_flags(env)
        self._update_fsm_state(t, left_contact, right_contact)

        # 计算当前机械能
        E_current = _mechanical_energy(self.params_base, data)

        # 调用 V13.6 FSM 控制律
        tau = control_v136(
            self.params_fsm, data, t, self.support_foot, self.burst_start_t, E_current
        )
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        # V13.7 摩擦补偿
        if self.compensate_friction:
            # qvel 地址（与 environment.py 中 joint_dofadr 对应）
            qvel_addr = {
                "left_hip": env.joint_dofadr[0],
                "left_knee": env.joint_dofadr[1],
                "right_hip": env.joint_dofadr[3],
                "right_knee": env.joint_dofadr[4],
            }

            l_hip_des = self._compensate(
                l_hip_des, float(data.qvel[qvel_addr["left_hip"]]), self.hip_motor
            )
            l_knee_des = self._compensate(
                l_knee_des, float(data.qvel[qvel_addr["left_knee"]]), self.knee_motor
            )
            r_hip_des = self._compensate(
                r_hip_des, float(data.qvel[qvel_addr["right_hip"]]), self.hip_motor
            )
            r_knee_des = self._compensate(
                r_knee_des, float(data.qvel[qvel_addr["right_knee"]]), self.knee_motor
            )

        # 返回 4 维动作
        action = np.array(
            [l_hip_des, l_knee_des, r_hip_des, r_knee_des], dtype=np.float32
        )
        return action

    def _compensate(self, tau_fsm: float, omega_joint: float, motor) -> float:
        """前馈摩擦补偿"""
        tau_C_eff = motor.joint_tau_C_eff()
        return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor.omega_eps)


def run_episode(
    env: CompassGaitEnv,
    strategy: str,
    episode_id: int,
    controller=None,
    ppo_model=None,
) -> EpisodeResult:
    """
    运行单个 episode

    Args:
        env: RL 环境
        strategy: 控制策略名称 ('zero', 'random', 'fsm', 'ppo')
        episode_id: Episode 编号
        controller: FSM 控制器（strategy='fsm' 时使用）
        ppo_model: PPO 模型（strategy='ppo' 时使用）

    Returns:
        EpisodeResult 记录
    """
    obs, info = env.reset()

    if strategy == "fsm" and controller is not None:
        controller.reset()

    total_reward = 0.0
    forward_reward = 0.0
    energy_cost = 0.0
    smoothness_cost = 0.0
    action_magnitudes = []

    terminated = False
    truncated = False
    step_count = 0
    last_action = None

    while not (terminated or truncated):
        # 选择动作
        if strategy == "zero":
            action = np.zeros(4, dtype=np.float32)
        elif strategy == "random":
            action = env.action_space.sample()
        elif strategy == "fsm":
            t = step_count * env.frame_skip * env.model.opt.timestep
            action = controller.compute_action(env, t)
            # Clip to action space
            action = np.clip(action, env.action_space.low, env.action_space.high)
        elif strategy == "ppo":
            action, _ = ppo_model.predict(obs, deterministic=True)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # 执行动作
        obs, reward, terminated, truncated, info = env.step(action)

        # 记录 reward 分解
        total_reward += reward

        # 手动计算 reward 组件（模拟 environment.py 的 _reward_energy_efficient）
        hip_vel_x = info.get("hip_vel_x", 0.0)
        forward_reward += 5.0 * hip_vel_x

        step_energy = np.sum(action**2)
        energy_cost += 0.01 * step_energy

        if last_action is not None:
            smoothness_cost += 0.001 * np.sum((action - last_action) ** 2)

        action_magnitudes.append(np.mean(np.abs(action)))
        last_action = action.copy()
        step_count += 1

    # 判断终止原因
    if terminated:
        hip_height = info.get("hip_height", 0.0)
        if hip_height < env.fall_height_threshold:
            termination_reason = "fall_low_height"
        else:
            termination_reason = "fall_lateral"
    elif truncated:
        termination_reason = "max_steps_reached"
    else:
        termination_reason = "unknown"

    # 判断成功（简化标准：走过 5m 且未摔倒）
    distance = info.get("hip_x", 0.0)
    success = distance >= 5.0 and not terminated

    duration = step_count * env.frame_skip * env.model.opt.timestep

    return EpisodeResult(
        strategy=strategy,
        episode_id=episode_id,
        distance=distance,
        steps=step_count,
        duration=duration,
        success=success,
        termination_reason=termination_reason,
        final_height=info.get("hip_height", 0.0),
        final_velocity=info.get("hip_vel_x", 0.0),
        total_reward=total_reward,
        forward_reward=forward_reward,
        energy_cost=energy_cost,
        smoothness_cost=smoothness_cost,
        avg_action_magnitude=np.mean(action_magnitudes) if action_magnitudes else 0.0,
    )


def run_comparison_experiment(
    num_episodes_per_strategy: int = 5,
    max_steps: int = 1000,
    save_results: bool = True,
) -> Dict[str, List[EpisodeResult]]:
    """
    运行对比实验

    Args:
        num_episodes_per_strategy: 每个策略运行的 episode 数
        max_steps: 每个 episode 最大步数
        save_results: 是否保存结果到文件

    Returns:
        结果字典，key 为策略名，value 为 EpisodeResult 列表
    """
    print("=" * 80)
    print("V13.7 FSM 在 RL 环境中的诊断实验")
    print("=" * 80)
    print(f"每策略 episode 数: {num_episodes_per_strategy}")
    print(f"最大步数: {max_steps}")
    print()

    # 创建环境（使用 energy_efficient reward 以便分解）
    env = CompassGaitEnv(
        reward_type="energy_efficient",
        max_steps=max_steps,
        reset_noise_scale=0.01,
    )

    # 初始化 FSM 控制器
    fsm_controller = FSMController()

    # 加载 PPO 模型
    print("加载 PPO 模型...")
    try:
        from stable_baselines3 import PPO

        ppo_model = PPO.load(r"C:\Users\duanj\models\ppo_gait_final.zip")
        print("[OK] PPO 模型加载成功")
    except Exception as e:
        print(f"[FAIL] PPO 模型加载失败: {e}")
        ppo_model = None

    print()

    # 定义策略列表
    strategies = [
        ("zero", "Zero Action", None, None),
        ("random", "Random Action", None, None),
        ("fsm", "V13.7 FSM", fsm_controller, None),
    ]

    if ppo_model is not None:
        strategies.append(("ppo", "PPO Model", None, ppo_model))

    # 运行实验
    results = {}

    for strategy_key, strategy_name, controller, model in strategies:
        print(f"运行策略: {strategy_name}")
        print("-" * 80)

        strategy_results = []

        for ep in range(num_episodes_per_strategy):
            result = run_episode(
                env,
                strategy_key,
                ep,
                controller=controller,
                ppo_model=model,
            )
            strategy_results.append(result)

            # 打印每个 episode 的简要信息
            status = "[SUCCESS]" if result.success else "[FAIL]"
            print(
                f"  Episode {ep+1}: {status} | "
                f"距离={result.distance:.2f}m | "
                f"步数={result.steps} | "
                f"时长={result.duration:.2f}s | "
                f"终止原因={result.termination_reason}"
            )

        results[strategy_key] = strategy_results
        print()

    env.close()

    # 打印统计摘要
    print_summary_table(results)

    # 保存结果
    if save_results:
        save_path = RL_TRAINING_DIR / "fsm_comparison_results.json"
        save_results_to_file(results, save_path)
        print(f"\n结果已保存到: {save_path}")

    return results


def print_summary_table(results: Dict[str, List[EpisodeResult]]):
    """打印对比表格"""
    print("=" * 80)
    print("对比结果统计")
    print("=" * 80)
    print()

    # 表头
    header = (
        f"{'策略':<15} | "
        f"{'成功率':<10} | "
        f"{'平均距离':<12} | "
        f"{'平均步数':<10} | "
        f"{'平均时长':<12} | "
        f"{'主要失败原因':<20}"
    )
    print(header)
    print("-" * len(header))

    for strategy_key, strategy_results in results.items():
        num_episodes = len(strategy_results)
        num_success = sum(1 for r in strategy_results if r.success)
        success_rate = num_success / num_episodes if num_episodes > 0 else 0.0

        avg_distance = np.mean([r.distance for r in strategy_results])
        avg_steps = np.mean([r.steps for r in strategy_results])
        avg_duration = np.mean([r.duration for r in strategy_results])

        # 统计最常见的失败原因
        failure_reasons = [
            r.termination_reason for r in strategy_results if not r.success
        ]
        if failure_reasons:
            from collections import Counter

            most_common_reason = Counter(failure_reasons).most_common(1)[0][0]
        else:
            most_common_reason = "N/A"

        strategy_name = {
            "zero": "Zero Action",
            "random": "Random Action",
            "fsm": "V13.7 FSM",
            "ppo": "PPO Model",
        }.get(strategy_key, strategy_key)

        print(
            f"{strategy_name:<15} | "
            f"{success_rate*100:>8.1f}% | "
            f"{avg_distance:>10.2f}m | "
            f"{avg_steps:>10.0f} | "
            f"{avg_duration:>10.2f}s | "
            f"{most_common_reason:<20}"
        )

    print()
    print("=" * 80)
    print("关键诊断问题回答：")
    print("=" * 80)

    if "fsm" in results:
        fsm_results = results["fsm"]
        fsm_avg_distance = np.mean([r.distance for r in fsm_results])
        fsm_avg_duration = np.mean([r.duration for r in fsm_results])
        fsm_max_distance = max([r.distance for r in fsm_results])
        fsm_max_duration = max([r.duration for r in fsm_results])

        print("\n问题: V13.7 FSM 在 RL 环境中能走多远？")
        print(f"答案: 平均 {fsm_avg_distance:.2f}m，最远 {fsm_max_distance:.2f}m")
        print("\n问题: V13.7 FSM 是否也在约 1.3 秒失败？")
        print(f"答案: 平均持续 {fsm_avg_duration:.2f}s，最长 {fsm_max_duration:.2f}s")

        # 判断失败模式
        early_failures = sum(
            1 for r in fsm_results if r.duration < 2.0 and not r.success
        )
        if early_failures >= len(fsm_results) * 0.5:
            print(
                f"\n诊断: FSM 在 RL 环境中也表现出早期失败（{early_failures}/{len(fsm_results)} episodes < 2s）"
            )
            print("可能原因:")
            print("  1. 环境初始化不一致（qpos/qvel 初始化差异）")
            print("  2. FSM 状态机初始状态设置错误")
            print("  3. 物理参数不匹配（armature/damping/friction）")
        else:
            print("\n诊断: FSM 在 RL 环境中表现正常（大部分 episodes > 2s）")
            print("可能原因:")
            print("  1. RL reward 设计可能与 FSM 目标不匹配")
            print("  2. RL 训练可能受困于局部最优")
            print("  3. PPO 模型可能需要更多训练或不同 hyperparameters")


def save_results_to_file(results: Dict[str, List[EpisodeResult]], save_path: Path):
    """保存结果到 JSON 文件"""
    output = {}
    for strategy_key, strategy_results in results.items():
        output[strategy_key] = [
            {
                "episode_id": int(r.episode_id),
                "distance": float(r.distance),
                "steps": int(r.steps),
                "duration": float(r.duration),
                "success": bool(r.success),
                "termination_reason": str(r.termination_reason),
                "final_height": float(r.final_height),
                "final_velocity": float(r.final_velocity),
                "total_reward": float(r.total_reward),
                "forward_reward": float(r.forward_reward),
                "energy_cost": float(r.energy_cost),
                "smoothness_cost": float(r.smoothness_cost),
                "avg_action_magnitude": float(r.avg_action_magnitude),
            }
            for r in strategy_results
        ]

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试 FSM 在 RL 环境中的表现")
    parser.add_argument(
        "--episodes", type=int, default=5, help="每策略运行的 episode 数"
    )
    parser.add_argument(
        "--max-steps", type=int, default=1000, help="每个 episode 最大步数"
    )
    parser.add_argument("--no-save", action="store_true", help="不保存结果到文件")

    args = parser.parse_args()

    run_comparison_experiment(
        num_episodes_per_strategy=args.episodes,
        max_steps=args.max_steps,
        save_results=not args.no_save,
    )


if __name__ == "__main__":
    main()
