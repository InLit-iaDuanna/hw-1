"""
阶段1：收集V13.7专家轨迹

运行完整的1kHz V13.7 FSM仿真循环，每20个timestep（对应RL的20ms）记录一次(obs, action)
不使用RL环境的step()方法，避免频率不匹配导致FSM状态机失效
"""

from __future__ import annotations

import json
import pickle
import sys
from dataclasses import dataclass
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
sys.path.insert(0, str(RL_TRAINING_DIR))

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
class ExpertTransition:
    """专家轨迹中的单个转换（RL频率：50Hz = 20ms）"""

    observation: np.ndarray  # 环境观测（20维）
    action: np.ndarray  # FSM控制输出（4维）
    next_observation: np.ndarray  # 下一个观测
    reward: float  # 奖励
    terminated: bool  # 是否摔倒
    truncated: bool  # 是否截断


@dataclass
class ExpertEpisode:
    """专家轨迹的一个完整episode"""

    episode_id: int
    transitions: List[ExpertTransition]
    total_reward: float
    forward_distance: float
    simulated_time: float
    alternating_touchdowns: int
    success: bool


class V137ExpertCollector:
    """V13.7专家轨迹收集器 - 运行完整1kHz仿真，下采样到RL频率"""

    def __init__(self):
        """初始化V13.7参数和电机模型"""
        # 构建V13.7参数（与test_v137_identity.py一致）
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

        from dataclasses import replace

        base = replace(base0, **overrides)
        fsm_params = make_v137_fsm(base)
        motor = MOTOR_PRESETS["mx64ar"]

        self.params = V137Params(
            base=base,
            fsm=fsm_params,
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

        # qvel地址
        self.qvel_addr = {
            "left_hip": 2,
            "left_knee": 3,
            "right_hip": 5,
            "right_knee": 6,
        }

        # 提取RL观测所需的索引（从environment.py复用）
        self._setup_observation_indices()

    def _setup_observation_indices(self):
        """设置RL观测提取所需的索引"""
        # Joint names for observation
        self.joint_names = [
            "left_hip",
            "left_knee",
            "left_ankle",
            "right_hip",
            "right_knee",
            "right_ankle",
        ]
        self.joint_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in self.joint_names
        ]
        self.joint_qposadr = [
            int(self.model.jnt_qposadr[jid]) for jid in self.joint_ids
        ]
        self.joint_dofadr = [int(self.model.jnt_dofadr[jid]) for jid in self.joint_ids]

        # Hip body for position/velocity
        self.hip_body_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "hip"
        )

        # Foot geoms for contact detection
        self.foot_geom_names = ["left_heel", "left_toe", "right_heel", "right_toe"]
        self.foot_geom_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, name)
            for name in self.foot_geom_names
        ]

    def _get_rl_observation(self) -> np.ndarray:
        """
        提取RL环境的20维观测向量

        Returns:
            20维观测: [joint_angles(6), joint_velocities(6), hip_pos(2), hip_vel(2), contact(4)]
        """
        # Joint angles (6)
        joint_angles = np.array(
            [self.data.qpos[self.joint_qposadr[i]] for i in range(6)]
        )

        # Joint velocities (6)
        joint_velocities = np.array(
            [self.data.qvel[self.joint_dofadr[i]] for i in range(6)]
        )

        # Hip position (2): x and z
        hip_pos = self.data.xpos[self.hip_body_id][[0, 2]]

        # Hip velocity (2): vx and vz
        hip_vel_full = np.zeros(6)  # [linear_vel(3), angular_vel(3)]
        mujoco.mj_objectVelocity(
            self.model,
            self.data,
            mujoco.mjtObj.mjOBJ_BODY,
            self.hip_body_id,
            hip_vel_full,
            0,
        )
        hip_vel = hip_vel_full[[0, 2]]  # Extract x and z components

        # Contact states (4): binary flags for each foot geom
        contact_states = self._detect_contacts()

        # Concatenate all components
        obs = np.concatenate(
            [joint_angles, joint_velocities, hip_pos, hip_vel, contact_states]
        ).astype(np.float32)

        return obs

    def _detect_contacts(self) -> np.ndarray:
        """检测足部接触状态（4维二值向量）"""
        contacts = np.zeros(4, dtype=np.float32)
        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            geom1 = contact.geom1
            geom2 = contact.geom2

            for j, foot_geom_id in enumerate(self.foot_geom_ids):
                if geom1 == foot_geom_id or geom2 == foot_geom_id:
                    contacts[j] = 1.0
                    break

        return contacts

    def _compute_reward(
        self, prev_hip_x: float, current_hip_x: float, action: np.ndarray, dt: float
    ) -> float:
        """
        计算RL奖励（energy_efficient类型）

        Args:
            prev_hip_x: 上一时刻hip x坐标
            current_hip_x: 当前hip x坐标
            action: 执行的动作（4维扭矩）
            dt: 时间步长（0.02s）

        Returns:
            奖励值
        """
        # Forward velocity reward
        forward_velocity = (current_hip_x - prev_hip_x) / dt
        velocity_reward = forward_velocity

        # Energy penalty (torque squared)
        energy_penalty = 0.001 * np.sum(action**2) * dt

        # Total reward
        reward = velocity_reward - energy_penalty

        return float(reward)

    def run_episode(self) -> ExpertEpisode | None:
        """
        运行单个episode，使用完整的1kHz V13.7仿真循环
        每20个timestep（0.02s）记录一次RL观测和动作

        Returns:
            成功则返回ExpertEpisode，失败则返回None
        """
        p = self.params.base
        fsm = self.params.fsm

        # === 1. 初始化（使用V13.7的initialize()函数）===
        initialize(self.model, self.data, p)

        # 重置电机饱和计数器
        for act in self.actuators.values():
            act.saturation_count = 0

        # === 2. FSM状态机初始化 ===
        start_x = float(self.data.qpos[0])
        max_x = start_x
        support_foot = "left"
        accepted_contact = ""
        candidate_start_t: Dict[str, float | None] = {"left": None, "right": None}
        contact_reported = {"left": False, "right": False}
        last_event_t = -1.0
        burst_start_t = -p.gait_period
        alternations = 0

        failure = ""
        transitions: List[ExpertTransition] = []
        total_reward = 0.0

        # RL频率采样
        RL_FRAME_SKIP = 20  # 每20个1ms step = 1个RL step (0.02s)
        prev_obs = None
        prev_action = None
        prev_hip_x = start_x

        # === 3. 1kHz控制循环 ===
        n_steps = int(p.duration / p.timestep)  # 12秒 * 1000Hz = 12000步

        for step in range(n_steps):
            t = step * p.timestep

            # 计算当前机械能
            E_current = _mechanical_energy(p, self.data)

            # 调用V13.6 FSM控制律
            tau = control_v136(
                fsm, self.data, t, support_foot, burst_start_t, E_current
            )
            l_hip_des, l_knee_des, r_hip_des, r_knee_des = (
                tau[0],
                tau[1],
                tau[2],
                tau[3],
            )

            # === V13.7核心：前馈摩擦补偿 ===
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

            # L1电机模型（饱和 + 库仑摩擦）
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

            action = np.array(
                [l_hip_out, l_knee_out, r_hip_out, r_knee_out], dtype=np.float32
            )
            self.data.ctrl[:] = action

            # MuJoCo step
            mujoco.mj_step(self.model, self.data)

            # === 每20步记录一次RL transition ===
            if step % RL_FRAME_SKIP == 0:
                current_obs = self._get_rl_observation()
                current_hip_x = float(self.data.qpos[0])

                # 如果有前一个观测，保存transition
                if prev_obs is not None and prev_action is not None:
                    reward = self._compute_reward(
                        prev_hip_x,
                        current_hip_x,
                        prev_action,
                        RL_FRAME_SKIP * p.timestep,
                    )
                    total_reward += reward

                    terminated = bool(failure)
                    truncated = False

                    transition = ExpertTransition(
                        observation=prev_obs,
                        action=prev_action,
                        next_observation=current_obs.copy(),
                        reward=reward,
                        terminated=terminated,
                        truncated=truncated,
                    )
                    transitions.append(transition)

                prev_obs = current_obs.copy()
                prev_action = action.copy()
                prev_hip_x = current_hip_x

            # 接触检测
            left_contact, right_contact = contact_flags(self.model, self.data)
            max_x = max(max_x, float(self.data.qpos[0]))

            # === FSM状态更新（与V13.7完全一致）===
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
                    break

            # === 失败检测（使用V13.7的classify_failure）===
            failure = classify_failure(self.model, self.data, p, start_x, t)
            if failure:
                break

        # === 4. 结果统计 ===
        simulated_time = t
        forward_distance = max_x - start_x

        # 判断成功（与V13.7标准一致）
        SUCCESS_TIME = 10.0
        SUCCESS_TOUCHDOWNS = 8  # 稍微放宽，因为有些episode可能是9次
        SUCCESS_FORWARD = 0.8

        success = (
            simulated_time >= SUCCESS_TIME
            and alternations >= SUCCESS_TOUCHDOWNS
            and forward_distance >= SUCCESS_FORWARD
            and not failure
        )

        if success:
            return ExpertEpisode(
                episode_id=0,  # 外部会重新设置
                transitions=transitions,
                total_reward=total_reward,
                forward_distance=forward_distance,
                simulated_time=simulated_time,
                alternating_touchdowns=alternations,
                success=True,
            )
        else:
            return None

    def _compensate(self, tau_fsm: float, omega_joint: float, motor) -> float:
        """前馈摩擦补偿（与V13.7一致）"""
        tau_C_eff = motor.joint_tau_C_eff()
        return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor.omega_eps)


def collect_expert_trajectories(
    num_episodes: int = 50, save_path: str = "v137_expert_trajectories.pkl"
) -> Dict[str, Any]:
    """
    收集V13.7专家轨迹（运行完整1kHz仿真，下采样到RL频率）

    Args:
        num_episodes: 收集的episode数量
        save_path: 保存路径

    Returns:
        统计信息字典
    """
    print("=" * 80)
    print("收集V13.7专家轨迹（1kHz仿真 → 50Hz采样）")
    print("=" * 80)
    print(f"目标episodes: {num_episodes}")
    print("仿真频率: 1000 Hz (1ms timestep)")
    print("采样频率: 50 Hz (20ms, 每20步采样一次)")
    print("预期transitions/episode: ~600 (12s / 0.02s)")
    print()

    # 创建专家收集器
    print("初始化V13.7专家收集器...")
    collector = V137ExpertCollector()
    print("[OK] 收集器初始化完成")
    print(f"  - 模型路径: {MODEL_PATH}")
    print(f"  - 摩擦补偿: {'ON' if collector.params.compensate_friction else 'OFF'}")
    print(f"  - 电机型号: {collector.params.hip_motor.name}")
    print()

    successful_episodes: List[ExpertEpisode] = []
    failed_episodes = 0

    print("开始收集轨迹...")
    print("-" * 80)

    episode_count = 0
    while len(successful_episodes) < num_episodes and episode_count < num_episodes * 3:
        episode_count += 1

        # 运行episode
        episode = collector.run_episode()

        if episode is not None:
            # 成功
            episode.episode_id = len(successful_episodes)
            successful_episodes.append(episode)

            print(
                f"[SUCCESS] Episode {episode_count} | "
                f"收集 {len(successful_episodes)}/{num_episodes} | "
                f"distance={episode.forward_distance:.3f}m | "
                f"time={episode.simulated_time:.2f}s | "
                f"touchdowns={episode.alternating_touchdowns} | "
                f"transitions={len(episode.transitions)}"
            )
        else:
            # 失败
            failed_episodes += 1
            print(f"[FAIL] Episode {episode_count} | " f"失败（未满足成功条件）")

            failed_episodes += 1
            print(f"[FAIL] Episode {episode_count} | " f"失败（未满足成功条件）")

    print()
    print("=" * 80)
    print("收集完成")
    print("=" * 80)

    # 统计信息
    total_transitions = sum(len(ep.transitions) for ep in successful_episodes)
    avg_distance = np.mean([ep.forward_distance for ep in successful_episodes])
    avg_time = np.mean([ep.simulated_time for ep in successful_episodes])
    avg_touchdowns = np.mean([ep.alternating_touchdowns for ep in successful_episodes])
    avg_reward = np.mean([ep.total_reward for ep in successful_episodes])

    print(f"成功episodes: {len(successful_episodes)}/{episode_count}")
    print(f"失败episodes: {failed_episodes}")
    print(f"总transitions: {total_transitions}")
    print(
        f"平均transitions/episode: {total_transitions / len(successful_episodes):.1f}"
    )
    print(f"平均距离: {avg_distance:.3f}m")
    print(f"平均时间: {avg_time:.2f}s")
    print(f"平均触地次数: {avg_touchdowns:.1f}")
    print(f"平均总奖励: {avg_reward:.2f}")
    print()

    # 保存数据
    save_path_full = RL_TRAINING_DIR / save_path
    data = {
        "episodes": successful_episodes,
        "statistics": {
            "num_episodes": len(successful_episodes),
            "total_transitions": total_transitions,
            "avg_transitions_per_episode": float(
                total_transitions / len(successful_episodes)
            ),
            "avg_distance": float(avg_distance),
            "avg_time": float(avg_time),
            "avg_touchdowns": float(avg_touchdowns),
            "avg_reward": float(avg_reward),
        },
        "config": {
            "simulation_frequency_hz": 1000,
            "sampling_frequency_hz": 50,
            "frame_skip": 20,
            "reward_type": "energy_efficient",
        },
    }

    with open(save_path_full, "wb") as f:
        pickle.dump(data, f)

    print(f"轨迹数据已保存到: {save_path_full}")
    print(f"文件大小: {save_path_full.stat().st_size / 1024 / 1024:.2f} MB")

    # 保存统计信息（JSON格式）
    stats_path = save_path_full.with_suffix(".json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(data["statistics"], f, ensure_ascii=False, indent=2)

    print(f"统计信息已保存到: {stats_path}")
    print()

    return data["statistics"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="收集V13.7专家轨迹")
    parser.add_argument("--episodes", type=int, default=50, help="收集的episode数量")
    parser.add_argument(
        "--save", type=str, default="v137_expert_trajectories.pkl", help="保存路径"
    )

    args = parser.parse_args()

    stats = collect_expert_trajectories(num_episodes=args.episodes, save_path=args.save)
