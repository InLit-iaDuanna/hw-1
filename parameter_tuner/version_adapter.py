"""版本适配器 - 统一不同版本的参数接口。

为不同版本提供统一的参数获取、保存、运行接口。
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import yaml

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))


class VersionAdapter:
    """版本适配器基类"""

    def __init__(self, version_key: str):
        self.version_key = version_key

    def get_default_params(self):
        """获取默认参数"""
        raise NotImplementedError

    def get_param_specs(self) -> dict:
        """获取参数规格（用于生成UI控件）"""
        raise NotImplementedError

    def get_param_summary(self, params) -> dict:
        """获取参数摘要"""
        raise NotImplementedError

    def params_to_yaml(self, params) -> str:
        """将参数转换为YAML字符串"""
        raise NotImplementedError

    def yaml_to_params(self, config: dict):
        """从YAML配置创建参数对象"""
        raise NotImplementedError

    def get_simulation_script(self) -> Path:
        """获取仿真脚本路径"""
        raise NotImplementedError

    def get_simulation_args(self, params) -> list[str]:
        """获取仿真命令行参数"""
        return []


class V137Adapter(VersionAdapter):
    """V13.7 版本适配器"""

    def __init__(self):
        super().__init__("V13.7")

    def get_default_params(self):
        from common.motor_dynamics import PRESETS as MOTOR_PRESETS
        from v13_7_friction_compensation.simulate_v13_7 import V137Params
        from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
        from v14c_arm_mass_lightening.simulate_v14c import make_v14c_params

        base = PassiveArmsParams()
        fsm = make_v14c_params(base)
        return V137Params(
            base=base,
            fsm=fsm,
            hip_motor=MOTOR_PRESETS["mx64ar"],
            knee_motor=MOTOR_PRESETS["mx64ar"],
            compensate_friction=True,
        )

    def get_param_specs(self) -> dict:
        return {
            "mechanical": {
                "hip_mass": {
                    "label": "髋部质量 (kg)",
                    "min": 3.0,
                    "max": 10.0,
                    "step": 0.1,
                    "help": "髋部body的质量",
                },
                "torso_mass": {
                    "label": "躯干质量 (kg)",
                    "min": 0.01,
                    "max": 1.0,
                    "step": 0.01,
                    "help": "上躯干质量",
                },
                "thigh_length": {
                    "label": "大腿长度 (m)",
                    "min": 0.3,
                    "max": 0.6,
                    "step": 0.01,
                    "help": "大腿link长度",
                },
                "shank_length": {
                    "label": "小腿长度 (m)",
                    "min": 0.3,
                    "max": 0.7,
                    "step": 0.01,
                    "help": "小腿link长度",
                },
                "foot_radius": {
                    "label": "足底半径 (m)",
                    "min": 0.02,
                    "max": 0.08,
                    "step": 0.001,
                    "help": "滚动足圆弧半径",
                },
                "foot_length": {
                    "label": "足底长度 (m)",
                    "min": 0.08,
                    "max": 0.20,
                    "step": 0.01,
                    "help": "足底capsule长度",
                },
            },
            "control": {
                "hip_kp": {
                    "label": "髋关节 Kp",
                    "min": 5.0,
                    "max": 60.0,
                    "step": 1.0,
                    "help": "髋关节PD控制比例增益",
                },
                "hip_kd": {
                    "label": "髋关节 Kd",
                    "min": 1.0,
                    "max": 15.0,
                    "step": 0.5,
                    "help": "髋关节PD控制微分增益",
                },
                "knee_kp": {
                    "label": "膝关节 Kp",
                    "min": 5.0,
                    "max": 40.0,
                    "step": 1.0,
                    "help": "膝关节PD控制比例增益",
                },
                "knee_kd": {
                    "label": "膝关节 Kd",
                    "min": 0.5,
                    "max": 10.0,
                    "step": 0.5,
                    "help": "膝关节PD控制微分增益",
                },
                "hip_torque_limit": {
                    "label": "髋关节力矩限制 (N·m)",
                    "min": 2.0,
                    "max": 10.0,
                    "step": 0.5,
                    "help": "髋关节最大输出力矩",
                },
                "knee_torque_limit": {
                    "label": "膝关节力矩限制 (N·m)",
                    "min": 1.0,
                    "max": 8.0,
                    "step": 0.5,
                    "help": "膝关节最大输出力矩",
                },
            },
            "simulation": {
                "duration": {
                    "label": "仿真时长 (s)",
                    "min": 5.0,
                    "max": 30.0,
                    "step": 1.0,
                    "help": "仿真总时长",
                },
                "timestep": {
                    "label": "时间步长 (s)",
                    "min": 0.0001,
                    "max": 0.005,
                    "step": 0.0001,
                    "help": "MuJoCo仿真时间步",
                },
                "initial_vx": {
                    "label": "初始速度 (m/s)",
                    "min": 0.0,
                    "max": 0.2,
                    "step": 0.01,
                    "help": "初始前向速度",
                },
            },
        }

    def get_param_summary(self, params) -> dict:
        return {
            "髋部质量": f"{params.base.hip_mass:.1f} kg",
            "腿长": f"{params.base.thigh_length + params.base.shank_length:.2f} m",
            "髋Kp/Kd": f"{params.base.hip_kp:.1f} / {params.base.hip_kd:.1f}",
            "膝Kp/Kd": f"{params.base.knee_kp:.1f} / {params.base.knee_kd:.1f}",
            "电机": params.hip_motor.name.split()[0],
            "摩擦补偿": "开" if params.compensate_friction else "关",
        }

    def params_to_yaml(self, params) -> str:
        """导出为V13.7 benchmark格式的YAML"""
        config = {
            "base_params": asdict(params.base),
            "motor_params": {"preset": "mx64ar"},  # 简化，只保存预设名
            "compensate_friction": params.compensate_friction,
        }
        return yaml.dump(config, allow_unicode=True, sort_keys=False)

    def yaml_to_params(self, config: dict):
        from common.motor_dynamics import PRESETS as MOTOR_PRESETS
        from v13_7_friction_compensation.simulate_v13_7 import V137Params
        from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams
        from v14c_arm_mass_lightening.simulate_v14c import make_v14c_params

        base = PassiveArmsParams(**config.get("base_params", {}))
        fsm = make_v14c_params(base)

        motor_preset = config.get("motor_params", {}).get("preset", "mx64ar")
        return V137Params(
            base=base,
            fsm=fsm,
            hip_motor=MOTOR_PRESETS[motor_preset],
            knee_motor=MOTOR_PRESETS[motor_preset],
            compensate_friction=config.get("compensate_friction", True),
        )

    def get_simulation_script(self) -> Path:
        return HW1_ROOT / "v13_7_friction_compensation" / "simulate_v13_7.py"

    def get_simulation_args(self, params) -> list[str]:
        return []


class V10Adapter(VersionAdapter):
    """V10 版本适配器"""

    def __init__(self):
        super().__init__("V10")

    def get_default_params(self):
        from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
            RollingFootParams,
        )

        return RollingFootParams()

    def get_param_specs(self) -> dict:
        return {
            "mechanical": {
                "hip_mass": {
                    "label": "髋部质量 (kg)",
                    "min": 3.0,
                    "max": 10.0,
                    "step": 0.1,
                },
                "thigh_length": {
                    "label": "大腿长度 (m)",
                    "min": 0.3,
                    "max": 0.6,
                    "step": 0.01,
                },
                "shank_length": {
                    "label": "小腿长度 (m)",
                    "min": 0.3,
                    "max": 0.7,
                    "step": 0.01,
                },
                "foot_radius": {
                    "label": "足底半径 (m)",
                    "min": 0.02,
                    "max": 0.08,
                    "step": 0.001,
                },
            },
            "control": {
                "hip_kp": {"label": "髋关节 Kp", "min": 5.0, "max": 40.0, "step": 1.0},
                "hip_kd": {"label": "髋关节 Kd", "min": 1.0, "max": 10.0, "step": 0.5},
                "knee_kp": {"label": "膝关节 Kp", "min": 5.0, "max": 30.0, "step": 1.0},
                "knee_kd": {"label": "膝关节 Kd", "min": 0.5, "max": 5.0, "step": 0.5},
            },
            "simulation": {
                "duration": {
                    "label": "仿真时长 (s)",
                    "min": 5.0,
                    "max": 30.0,
                    "step": 1.0,
                },
                "timestep": {
                    "label": "时间步长 (s)",
                    "min": 0.0001,
                    "max": 0.005,
                    "step": 0.0001,
                },
            },
        }

    def get_param_summary(self, params) -> dict:
        return {
            "髋部质量": f"{params.hip_mass:.1f} kg",
            "腿长": f"{params.thigh_length + params.shank_length:.2f} m",
            "髋Kp/Kd": f"{params.hip_kp:.1f} / {params.hip_kd:.1f}",
            "膝Kp/Kd": f"{params.knee_kp:.1f} / {params.knee_kd:.1f}",
        }

    def params_to_yaml(self, params) -> str:
        config = {"params": asdict(params)}
        return yaml.dump(config, allow_unicode=True, sort_keys=False)

    def yaml_to_params(self, config: dict):
        from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
            RollingFootParams,
        )

        return RollingFootParams(**config.get("params", {}))

    def get_simulation_script(self) -> Path:
        return (
            HW1_ROOT
            / "v10_rolling_foot_biomimetic_gait"
            / "simulate_rolling_foot_gait_v10.py"
        )


# 版本注册表
_ADAPTERS = {
    "V10": V10Adapter,
    "V13.7": V137Adapter,
    # 可扩展其他版本
    "V13.6": V137Adapter,  # 临时使用V137适配器
    "V14": V137Adapter,  # 临时使用V137适配器
    "V16": V137Adapter,  # 临时使用V137适配器
    "V17": V137Adapter,  # 临时使用V137适配器
}


def get_version_adapter(version_key: str) -> VersionAdapter:
    """获取版本适配器实例"""
    adapter_class = _ADAPTERS.get(version_key)
    if adapter_class is None:
        raise ValueError(f"不支持的版本: {version_key}")
    return adapter_class()
