"""
特征提取模块
提取步态周期、能量、稳定性、接触等特征
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import signal

from data_loader import GaitData


@dataclass
class GaitFeatures:
    """步态特征容器"""

    version: str
    label: str

    # 步态周期特征
    period_length: float | None = None
    stride_length: float | None = None
    stride_frequency: float | None = None
    duty_factor: float | None = None
    double_support_ratio: float | None = None
    single_support_ratio: float | None = None
    left_right_symmetry: float | None = None
    num_strides: int = 0

    # 能量特征
    cost_of_transport: float | None = None
    mechanical_work: float | None = None
    input_energy: float | None = None
    actuator_work: float | None = None
    collision_loss: float | None = None
    damping_loss: float | None = None
    power_mean: float | None = None
    power_peak: float | None = None
    power_std: float | None = None

    # 稳定性特征
    convergence_rate: float | None = None
    limit_cycle_radius: float | None = None
    phase_margin: float | None = None

    # 接触特征
    left_contact_duration: float | None = None
    right_contact_duration: float | None = None
    left_force_peak: float | None = None
    right_force_peak: float | None = None
    ground_clearance_mean: float | None = None
    ground_clearance_min: float | None = None

    # 运动学特征
    hip_excursion: float | None = None
    knee_flexion_max_left: float | None = None
    knee_flexion_max_right: float | None = None
    hip_velocity_peak: float | None = None
    knee_velocity_peak: float | None = None

    # 原始数据引用
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FeatureExtractor:
    """特征提取器"""

    def __init__(self, config: dict):
        """
        初始化特征提取器

        Args:
            config: feature_extraction 配置字典
        """
        self.config = config

    def detect_heel_strikes(self, contact: np.ndarray, time: np.ndarray) -> np.ndarray:
        """
        检测脚跟着地事件（接触信号上升沿）

        Args:
            contact: 接触状态数组 (0/1)
            time: 时间数组

        Returns:
            脚跟着地时间点数组
        """
        # 确保 contact 和 time 长度一致
        min_len = min(len(contact), len(time))
        contact = contact[:min_len]
        time = time[:min_len]

        # 找到上升沿（0 -> 1）
        contact_binary = (contact > 0.5).astype(int)
        diff = np.diff(contact_binary)
        heel_strike_indices = np.where(diff > 0)[0] + 1

        if len(heel_strike_indices) == 0:
            return np.array([])

        heel_strike_times = time[heel_strike_indices]
        return heel_strike_times

    def detect_toe_offs(self, contact: np.ndarray, time: np.ndarray) -> np.ndarray:
        """
        检测脚趾离地事件（接触信号下降沿）

        Args:
            contact: 接触状态数组 (0/1)
            time: 时间数组

        Returns:
            脚趾离地时间点数组
        """
        # 确保 contact 和 time 长度一致
        min_len = min(len(contact), len(time))
        contact = contact[:min_len]
        time = time[:min_len]

        # 找到下降沿（1 -> 0）
        contact_binary = (contact > 0.5).astype(int)
        diff = np.diff(contact_binary)
        toe_off_indices = np.where(diff < 0)[0] + 1

        if len(toe_off_indices) == 0:
            return np.array([])

        toe_off_times = time[toe_off_indices]
        return toe_off_times

    def extract_gait_cycle_features(self, gait_data: GaitData) -> dict[str, Any]:
        """
        提取步态周期特征

        Args:
            gait_data: 步态数据

        Returns:
            特征字典
        """
        features = {}

        # 检测脚跟着地事件
        left_contact = gait_data.contact_states.get("left_contact", np.array([]))
        right_contact = gait_data.contact_states.get("right_contact", np.array([]))

        if len(left_contact) == 0 or len(right_contact) == 0:
            return features

        left_strikes = self.detect_heel_strikes(left_contact, gait_data.time)
        right_strikes = self.detect_heel_strikes(right_contact, gait_data.time)

        # 计算步态周期
        if len(left_strikes) > 1:
            left_periods = np.diff(left_strikes)
            features["period_length"] = float(np.mean(left_periods))
            features["stride_frequency"] = 1.0 / features["period_length"]
            features["num_strides"] = len(left_strikes) - 1
        else:
            features["num_strides"] = 0

        # 计算步长
        if len(left_strikes) > 1:
            stride_distances = []
            for i in range(len(left_strikes) - 1):
                t1 = left_strikes[i]
                t2 = left_strikes[i + 1]
                idx1 = np.argmin(np.abs(gait_data.time - t1))
                idx2 = np.argmin(np.abs(gait_data.time - t2))
                distance = gait_data.hip_x[idx2] - gait_data.hip_x[idx1]
                stride_distances.append(distance)

            if stride_distances:
                features["stride_length"] = float(np.mean(stride_distances))

        # 计算接触时间比例
        left_toe_offs = self.detect_toe_offs(left_contact, gait_data.time)
        right_toe_offs = self.detect_toe_offs(right_contact, gait_data.time)

        if len(left_strikes) > 1 and len(left_toe_offs) > 0:
            contact_durations = []
            for strike in left_strikes[:-1]:
                # 找到对应的 toe-off
                future_toe_offs = left_toe_offs[left_toe_offs > strike]
                if len(future_toe_offs) > 0:
                    contact_durations.append(future_toe_offs[0] - strike)

            if contact_durations and "period_length" in features:
                mean_contact = np.mean(contact_durations)
                features["duty_factor"] = mean_contact / features["period_length"]
                features["left_contact_duration"] = float(mean_contact)

        # 计算双支撑比例
        double_support = (left_contact > 0.5) & (right_contact > 0.5)
        single_support = (left_contact > 0.5) ^ (right_contact > 0.5)
        total_time = gait_data.duration

        features["double_support_ratio"] = float(
            np.sum(double_support) / len(double_support)
        )
        features["single_support_ratio"] = float(
            np.sum(single_support) / len(single_support)
        )

        # 计算左右对称性
        if len(left_strikes) > 1 and len(right_strikes) > 1:
            left_period = np.mean(np.diff(left_strikes))
            right_period = np.mean(np.diff(right_strikes))
            features["left_right_symmetry"] = 1.0 - abs(
                left_period - right_period
            ) / max(left_period, right_period)

        return features

    def extract_energy_features(self, gait_data: GaitData) -> dict[str, Any]:
        """
        提取能量特征

        Args:
            gait_data: 步态数据

        Returns:
            特征字典
        """
        features = {}

        # 功率统计
        if gait_data.power is not None:
            power = gait_data.power
            features["power_mean"] = float(np.mean(power))
            features["power_peak"] = float(np.max(np.abs(power)))
            features["power_std"] = float(np.std(power))

        # 总输入能量
        if gait_data.energy is not None:
            energy = gait_data.energy
            features["input_energy"] = float(energy[-1] - energy[0])

        # 机械功（所有力矩的功率积分）
        if gait_data.torques and gait_data.joint_velocities:
            total_work = 0.0
            dt = np.mean(np.diff(gait_data.time))

            for joint in ["left_hip", "left_knee", "right_hip", "right_knee"]:
                tau_key = f"{joint}_tau"
                vel_key = f"{joint}_vel"

                if (
                    tau_key in gait_data.torques
                    and vel_key in gait_data.joint_velocities
                ):
                    torque = gait_data.torques[tau_key]
                    velocity = gait_data.joint_velocities[vel_key]
                    power = torque * velocity
                    work = np.sum(np.abs(power)) * dt
                    total_work += work

            features["mechanical_work"] = total_work
            features["actuator_work"] = total_work

        # 计算 CoT（Cost of Transport）
        if "input_energy" in features:
            distance = gait_data.hip_x[-1] - gait_data.hip_x[0]
            # 假设质量为 5kg（从配置或数据中获取）
            mass = 5.0
            gravity = 9.81

            if distance > 0:
                features["cost_of_transport"] = features["input_energy"] / (
                    mass * gravity * distance
                )

        return features

    def extract_stability_features(self, gait_data: GaitData) -> dict[str, Any]:
        """
        提取稳定性特征

        Args:
            gait_data: 步态数据

        Returns:
            特征字典
        """
        features = {}

        # 检测周期事件
        left_contact = gait_data.contact_states.get("left_contact", np.array([]))
        if len(left_contact) == 0:
            return features

        left_strikes = self.detect_heel_strikes(left_contact, gait_data.time)

        if len(left_strikes) < 3:
            return features

        # 提取 Poincare 点（每个周期的状态）
        poincare_states = []
        for strike_time in left_strikes:
            idx = np.argmin(np.abs(gait_data.time - strike_time))
            state = {
                "hip_x": gait_data.hip_x[idx],
                "hip_z": gait_data.hip_z[idx],
                "left_hip": gait_data.joint_angles.get("left_hip", np.array([0]))[idx],
                "right_hip": gait_data.joint_angles.get("right_hip", np.array([0]))[
                    idx
                ],
            }
            poincare_states.append(state)

        # 计算收敛率（相邻周期状态差异的衰减）
        if len(poincare_states) >= 3:
            diffs = []
            for i in range(len(poincare_states) - 1):
                s1 = poincare_states[i]
                s2 = poincare_states[i + 1]
                diff = np.sqrt(
                    (s2["left_hip"] - s1["left_hip"]) ** 2
                    + (s2["right_hip"] - s1["right_hip"]) ** 2
                )
                diffs.append(diff)

            if len(diffs) >= 2:
                # 拟合指数衰减
                diffs_array = np.array(diffs)
                if np.all(diffs_array > 0):
                    log_diffs = np.log(diffs_array)
                    x = np.arange(len(log_diffs))
                    coeffs = np.polyfit(x, log_diffs, 1)
                    features["convergence_rate"] = -float(coeffs[0])

        # 计算极限环半径（状态空间中的振幅）
        if len(poincare_states) >= 2:
            # 计算平均状态
            mean_left_hip = np.mean([s["left_hip"] for s in poincare_states])
            mean_right_hip = np.mean([s["right_hip"] for s in poincare_states])

            # 计算到平均状态的距离
            radii = []
            for s in poincare_states:
                radius = np.sqrt(
                    (s["left_hip"] - mean_left_hip) ** 2
                    + (s["right_hip"] - mean_right_hip) ** 2
                )
                radii.append(radius)

            features["limit_cycle_radius"] = float(np.mean(radii))

        return features

    def extract_contact_features(self, gait_data: GaitData) -> dict[str, Any]:
        """
        提取接触特征

        Args:
            gait_data: 步态数据

        Returns:
            特征字典
        """
        features = {}

        # 计算地面间隙
        ground_clearances = []
        left_contact = gait_data.contact_states.get("left_contact", np.array([]))
        right_contact = gait_data.contact_states.get("right_contact", np.array([]))

        # 摆动腿的最低点高度
        if len(left_contact) > 0:
            left_swing = left_contact < 0.5
            if np.any(left_swing):
                # 假设足部在髋部下方约 1m
                left_foot_z = gait_data.hip_z - 1.0  # 简化估计
                swing_clearance = left_foot_z[left_swing]
                if len(swing_clearance) > 0:
                    ground_clearances.extend(swing_clearance)

        if len(right_contact) > 0:
            right_swing = right_contact < 0.5
            if np.any(right_swing):
                right_foot_z = gait_data.hip_z - 1.0
                swing_clearance = right_foot_z[right_swing]
                if len(swing_clearance) > 0:
                    ground_clearances.extend(swing_clearance)

        if ground_clearances:
            features["ground_clearance_mean"] = float(np.mean(ground_clearances))
            features["ground_clearance_min"] = float(np.min(ground_clearances))

        return features

    def extract_kinematics_features(self, gait_data: GaitData) -> dict[str, Any]:
        """
        提取运动学特征

        Args:
            gait_data: 步态数据

        Returns:
            特征字典
        """
        features = {}

        # 髋部位移
        if len(gait_data.hip_x) > 0:
            features["hip_excursion"] = float(gait_data.hip_x[-1] - gait_data.hip_x[0])

        # 膝关节最大屈曲
        if "left_knee" in gait_data.joint_angles:
            left_knee = gait_data.joint_angles["left_knee"]
            features["knee_flexion_max_left"] = float(np.max(np.abs(left_knee)))

        if "right_knee" in gait_data.joint_angles:
            right_knee = gait_data.joint_angles["right_knee"]
            features["knee_flexion_max_right"] = float(np.max(np.abs(right_knee)))

        # 速度峰值
        if "left_hip_vel" in gait_data.joint_velocities:
            hip_vels = []
            for key in ["left_hip_vel", "right_hip_vel"]:
                if key in gait_data.joint_velocities:
                    hip_vels.extend(gait_data.joint_velocities[key])
            if hip_vels:
                features["hip_velocity_peak"] = float(np.max(np.abs(hip_vels)))

        if "left_knee_vel" in gait_data.joint_velocities:
            knee_vels = []
            for key in ["left_knee_vel", "right_knee_vel"]:
                if key in gait_data.joint_velocities:
                    knee_vels.extend(gait_data.joint_velocities[key])
            if knee_vels:
                features["knee_velocity_peak"] = float(np.max(np.abs(knee_vels)))

        return features

    def extract_all_features(self, gait_data: GaitData) -> GaitFeatures:
        """
        提取所有特征

        Args:
            gait_data: 步态数据

        Returns:
            GaitFeatures 对象
        """
        print(f"Extracting features for {gait_data.version}: {gait_data.label}")

        # 提取各类特征
        gait_cycle = self.extract_gait_cycle_features(gait_data)
        energy = self.extract_energy_features(gait_data)
        stability = self.extract_stability_features(gait_data)
        contact = self.extract_contact_features(gait_data)
        kinematics = self.extract_kinematics_features(gait_data)

        # 合并所有特征
        all_features = {
            **gait_cycle,
            **energy,
            **stability,
            **contact,
            **kinematics,
        }

        # 创建 GaitFeatures 对象
        features = GaitFeatures(
            version=gait_data.version,
            label=gait_data.label,
            **all_features,
        )

        print(
            f"  Extracted {len([k for k, v in all_features.items() if v is not None])} features"
        )

        return features


def main():
    """测试特征提取"""
    from pathlib import Path
    import yaml
    from data_loader import DataLoader
    from preprocessor import DataPreprocessor

    config_path = Path(__file__).parent / "pipeline_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    loader = DataLoader(config_path)
    preprocessor = DataPreprocessor(config["preprocessing"])
    extractor = FeatureExtractor(config["feature_extraction"])

    print("=" * 60)
    print("Feature Extractor Test")
    print("=" * 60)

    # 加载和预处理数据
    gait_data = loader.load_version("v09_stable")
    processed = preprocessor.preprocess_gait_data(gait_data)

    # 提取特征
    features = extractor.extract_all_features(processed)

    print(f"\nExtracted features:")
    print(
        f"  Period: {features.period_length:.3f}s"
        if features.period_length
        else "  Period: N/A"
    )
    print(
        f"  Stride length: {features.stride_length:.3f}m"
        if features.stride_length
        else "  Stride length: N/A"
    )
    print(
        f"  CoT: {features.cost_of_transport:.4f}"
        if features.cost_of_transport
        else "  CoT: N/A"
    )
    print(
        f"  Duty factor: {features.duty_factor:.3f}"
        if features.duty_factor
        else "  Duty factor: N/A"
    )
    print(
        f"  Symmetry: {features.left_right_symmetry:.3f}"
        if features.left_right_symmetry
        else "  Symmetry: N/A"
    )


if __name__ == "__main__":
    main()
