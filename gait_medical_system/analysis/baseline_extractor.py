"""
从V01-V24仿真研究中提取健康步态基准参数
用于医疗步态检测系统的对比分析
"""

import json
from pathlib import Path


class HealthyGaitBaseline:
    """健康步态基准模型（从仿真提取）"""

    def __init__(self):
        # V10 足踝滚动仿生步态的标准参数
        self.v10_baseline = {
            "stride_length": 1.05,  # m (V10 typical)
            "stride_time": 1.0,  # s
            "cadence": 60.0,  # steps/min (120 alternations/min)
            "walking_speed": 0.5,  # m/s
            "knee_rom": {"mean": 60.0, "std": 5.0},  # degrees
            "hip_rom": {"mean": 40.0, "std": 4.0},  # degrees
            "ankle_rom": {"mean": 25.0, "std": 3.0},  # degrees (被动踝关节)
        }

        # V13.7 能量效率基准
        self.v137_energy = {
            "CoT_mechanical": 0.072,  # V13.7 摩擦补偿结果
            "energy_per_step": 5.2,  # J (基于V13b极限环)
        }

        # V11 鲁棒性边界（正常范围）
        self.v11_robustness = {
            "terrain_amplitude_max": 0.0286,  # m (28.6 mm)
            "impulse_tolerance": 17.1,  # N
            "disturbance_recovery_time": 0.5,  # s
        }

        # V12 稳定性指标
        self.v12_stability = {
            "floquet_multiplier_max": 0.944,  # V13b长程辨识
            "limit_cycle_energy": 52.66,  # J
            "collision_loss_per_step": 2.3,  # J
        }

        # 对称性基准（理想情况）
        self.symmetry = {
            "stride_length_symmetry": 0.0,  # % (完全对称)
            "stride_time_symmetry": 0.0,
            "stance_time_symmetry": 0.0,
            "swing_time_symmetry": 0.0,
        }

        # V10 足底接触模式（滚动足）
        self.foot_contact_pattern = {
            "heel_strike_phase": 0.0,  # 归一化相位
            "foot_flat_phase": 0.15,
            "heel_off_phase": 0.40,
            "toe_off_phase": 0.60,
            "contact_duration_ratio": 0.60,  # 支撑相占比
        }

    def get_baseline_dict(self):
        """返回完整基准字典"""
        return {
            "v10_kinematics": self.v10_baseline,
            "v137_energy": self.v137_energy,
            "v11_robustness": self.v11_robustness,
            "v12_stability": self.v12_stability,
            "symmetry": self.symmetry,
            "foot_contact": self.foot_contact_pattern,
            "metadata": {
                "source": "hw-1 V01-V24 simulation research",
                "model_type": "passive_dynamic_walking",
                "validation": "10+ continuous steps in simulation",
            },
        }

    def save_to_json(self, output_path="baseline_healthy_gait.json"):
        """保存基准参数到JSON文件"""
        baseline = self.get_baseline_dict()
        output_file = Path(__file__).parent.parent / "config" / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)

        print(f"健康步态基准已保存到: {output_file}")
        return output_file

    def compare_with_patient(self, patient_data):
        """
        对比患者数据与健康基准

        Parameters:
        -----------
        patient_data : dict
            患者步态参数，键值需与baseline一致

        Returns:
        --------
        dict : 对比结果和偏差百分比
        """
        deviations = {}

        # 步长对比
        if (
            "stride_length_left" in patient_data
            and "stride_length_right" in patient_data
        ):
            left = patient_data["stride_length_left"]
            right = patient_data["stride_length_right"]
            baseline = self.v10_baseline["stride_length"]

            deviations["stride_length"] = {
                "left_deviation": (left - baseline) / baseline * 100,
                "right_deviation": (right - baseline) / baseline * 100,
                "asymmetry_index": abs(left - right) / (0.5 * (left + right)) * 100,
            }

        # 步频对比
        if "cadence" in patient_data:
            baseline_cadence = self.v10_baseline["cadence"]
            deviation = (
                (patient_data["cadence"] - baseline_cadence) / baseline_cadence * 100
            )
            deviations["cadence"] = {
                "value": patient_data["cadence"],
                "baseline": baseline_cadence,
                "deviation_percent": deviation,
            }

        # 关节活动度对比
        for joint in ["knee", "hip", "ankle"]:
            rom_key = f"{joint}_rom"
            if rom_key in patient_data:
                baseline_rom = self.v10_baseline[f"{joint}_rom"]["mean"]
                patient_rom = patient_data[rom_key]
                deviation = (patient_rom - baseline_rom) / baseline_rom * 100

                deviations[rom_key] = {
                    "value": patient_rom,
                    "baseline": baseline_rom,
                    "deviation_percent": deviation,
                    "status": self._classify_rom_deviation(deviation),
                }

        return deviations

    def _classify_rom_deviation(self, deviation_percent):
        """分类关节活动度偏差程度"""
        abs_dev = abs(deviation_percent)
        if abs_dev < 10:
            return "normal"
        elif abs_dev < 20:
            return "mild_limitation"
        elif abs_dev < 40:
            return "moderate_limitation"
        else:
            return "severe_limitation"


def extract_v10_data_from_simulation():
    """
    从V10仿真输出文件中提取实际数据
    （如果V10 out/目录有数据文件，可以解析）
    """
    v10_data_path = (
        Path(__file__).parent.parent.parent / "v10_rolling_foot_biomimetic_gait" / "out"
    )

    if v10_data_path.exists():
        print(f"检测到V10数据目录: {v10_data_path}")
        # TODO: 解析v10_data.csv或summary.json
        # 提取实际的步长、步频、ROM等参数
        pass
    else:
        print("未找到V10仿真数据，使用理论基准值")

    return None


if __name__ == "__main__":
    # 创建健康步态基准
    baseline = HealthyGaitBaseline()

    # 保存到配置文件
    output_file = baseline.save_to_json()

    # 显示基准参数
    print("\n=== 健康步态基准参数（从V01-V24仿真提取）===")
    baseline_dict = baseline.get_baseline_dict()

    print("\n[V10 运动学基准]")
    for key, value in baseline_dict["v10_kinematics"].items():
        print(f"  {key}: {value}")

    print("\n[V13.7 能量效率]")
    for key, value in baseline_dict["v137_energy"].items():
        print(f"  {key}: {value}")

    print("\n[V11 鲁棒性边界]")
    for key, value in baseline_dict["v11_robustness"].items():
        print(f"  {key}: {value}")

    # 示例：对比患者数据
    print("\n=== 示例：患者数据对比 ===")
    mock_patient_data = {
        "stride_length_left": 0.85,  # 患侧步长明显缩短
        "stride_length_right": 1.08,  # 健侧接近正常
        "cadence": 75,  # 步频偏慢
        "knee_rom": 45,  # 膝关节活动受限
        "hip_rom": 35,
    }

    deviations = baseline.compare_with_patient(mock_patient_data)

    print("\n偏差分析:")
    for key, value in deviations.items():
        print(f"\n{key}:")
        for subkey, subval in value.items():
            print(f"  {subkey}: {subval}")
