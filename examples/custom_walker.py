"""示例：创建自定义步行机器人模型和控制器

演示如何通过继承基类来创建：
1. 自定义控制器（继承 Controller）
2. 自定义参数配置（继承 CompassGaitParams）
3. 自定义步态模型（继承 CompassGait）

运行方式：
    python examples/custom_walker.py
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np

# 从 common 模块导入基类
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.controllers import Controller, PDController
from common.compass_gait import CompassGait, CompassGaitParams

# ============================================================================
# 1. 自定义控制器示例
# ============================================================================


class AdaptivePDController(Controller):
    """自适应 PD 控制器

    根据误差大小自动调整增益，误差大时使用高增益快速响应，
    误差小时使用低增益精细控制。

    Args:
        kp_base: 基础比例增益
        kd_base: 基础微分增益
        adaptation_rate: 自适应速率，控制增益变化的陡峭程度
        torque_limit: 力矩限制
    """

    def __init__(
        self,
        kp_base: float = 100.0,
        kd_base: float = 10.0,
        adaptation_rate: float = 5.0,
        torque_limit: float | None = None,
    ):
        self.kp_base = kp_base
        self.kd_base = kd_base
        self.adaptation_rate = adaptation_rate
        self.torque_limit = torque_limit

    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """计算自适应 PD 控制力矩"""
        if target is None:
            raise ValueError("AdaptivePDController requires a target position")

        # 计算误差
        error = target - q

        # 自适应增益：误差越大，增益越高
        # 使用 sigmoid 函数平滑过渡
        adaptation_factor = 1.0 + math.tanh(abs(error) * self.adaptation_rate)
        kp = self.kp_base * adaptation_factor
        kd = self.kd_base * adaptation_factor

        # PD 控制律
        torque = kp * error - kd * qd

        # 应用力矩限幅
        if self.torque_limit is not None:
            torque = float(np.clip(torque, -self.torque_limit, self.torque_limit))

        return float(torque)

    def __repr__(self) -> str:
        limit_str = f"{self.torque_limit:.1f}" if self.torque_limit else "None"
        return (
            f"AdaptivePDController(kp={self.kp_base:.1f}, kd={self.kd_base:.1f}, "
            f"rate={self.adaptation_rate:.1f}, limit={limit_str})"
        )


class GravityCompensatingController(Controller):
    """重力补偿控制器

    在 PD 控制基础上增加重力补偿项，适用于腿部控制。

    Args:
        kp: 比例增益
        kd: 微分增益
        leg_mass: 腿部质量 (kg)
        leg_length: 腿长 (m)
        gravity: 重力加速度 (m/s²)
        torque_limit: 力矩限制
    """

    def __init__(
        self,
        kp: float = 150.0,
        kd: float = 15.0,
        leg_mass: float = 5.0,
        leg_length: float = 1.0,
        gravity: float = 9.81,
        torque_limit: float | None = None,
    ):
        self.kp = kp
        self.kd = kd
        self.leg_mass = leg_mass
        self.leg_length = leg_length
        self.gravity = gravity
        self.torque_limit = torque_limit

    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """计算带重力补偿的控制力矩"""
        if target is None:
            raise ValueError("GravityCompensatingController requires a target position")

        # PD 控制项
        error = target - q
        torque_pd = self.kp * error - self.kd * qd

        # 重力补偿项（简化模型：质点在腿中点）
        # τ_g = m * g * (L/2) * cos(q)
        torque_gravity = (
            self.leg_mass * self.gravity * (self.leg_length / 2.0) * math.cos(q)
        )

        # 总力矩
        torque = torque_pd + torque_gravity

        # 应用力矩限幅
        if self.torque_limit is not None:
            torque = float(np.clip(torque, -self.torque_limit, self.torque_limit))

        return float(torque)

    def __repr__(self) -> str:
        return (
            f"GravityCompensatingController(kp={self.kp:.1f}, kd={self.kd:.1f}, "
            f"m={self.leg_mass:.1f}kg, L={self.leg_length:.2f}m)"
        )


class PhaseBasedController(Controller):
    """基于步态相位的控制器

    根据当前步态相位（支撑相/摆动相）切换不同的控制策略。

    Args:
        stance_controller: 支撑相控制器
        swing_controller: 摆动相控制器
        phase: 当前相位 ('stance' 或 'swing')
    """

    def __init__(
        self,
        stance_controller: Controller,
        swing_controller: Controller,
        phase: str = "stance",
    ):
        self.stance_controller = stance_controller
        self.swing_controller = swing_controller
        self.phase = phase

    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """根据相位选择控制器"""
        # 可以从 kwargs 中动态更新相位
        phase = kwargs.get("phase", self.phase)

        if phase == "stance":
            return self.stance_controller.compute_torque(q, qd, target, **kwargs)
        elif phase == "swing":
            return self.swing_controller.compute_torque(q, qd, target, **kwargs)
        else:
            raise ValueError(f"Unknown phase: {phase}")

    def set_phase(self, phase: str) -> None:
        """更新步态相位"""
        if phase not in ("stance", "swing"):
            raise ValueError(f"Phase must be 'stance' or 'swing', got {phase}")
        self.phase = phase

    def reset(self) -> None:
        """重置所有子控制器"""
        self.stance_controller.reset()
        self.swing_controller.reset()

    def __repr__(self) -> str:
        return (
            f"PhaseBasedController(phase={self.phase}, "
            f"stance={self.stance_controller}, swing={self.swing_controller})"
        )


# ============================================================================
# 2. 自定义参数配置示例
# ============================================================================


@dataclass(frozen=True)
class RobustWalkerParams(CompassGaitParams):
    """鲁棒步行机器人参数

    继承 CompassGaitParams，增加鲁棒性相关参数。
    """

    # 新增参数：扰动鲁棒性
    disturbance_rejection: float = 0.8  # 扰动抑制能力 [0, 1]
    recovery_speed: float = 0.5  # 姿态恢复速度
    max_lean_angle_deg: float = 15.0  # 最大允许倾斜角度

    # 新增参数：能量效率
    energy_efficiency_target: float = 0.9  # 目标能量效率
    regenerative_braking: bool = True  # 是否启用再生制动

    @property
    def max_lean_angle(self) -> float:
        """最大倾斜角度 (rad)"""
        return math.radians(self.max_lean_angle_deg)

    @classmethod
    def from_template(cls, template: str) -> RobustWalkerParams:
        """扩展模板方法，支持新的配置模板"""
        # 先调用父类方法获取基础配置
        base_template = template
        if template in {"robust", "efficient", "aggressive"}:
            base_template = "hybrid"
        base = CompassGaitParams.from_template(base_template)
        base_dict = asdict(base)
        if template == "efficient":
            base_dict.pop("slope_deg", None)
        elif template == "aggressive":
            base_dict.pop("initial_speed", None)

        if template == "robust":
            # 鲁棒配置：高扰动抑制，快速恢复
            return cls(
                **base_dict,
                disturbance_rejection=0.9,
                recovery_speed=0.7,
                max_lean_angle_deg=12.0,
                energy_efficiency_target=0.85,
            )
        elif template == "efficient":
            # 高效配置：优化能量效率
            return cls(
                **base_dict,
                slope_deg=4.0,  # 稍缓的坡度
                disturbance_rejection=0.7,
                recovery_speed=0.4,
                max_lean_angle_deg=10.0,
                energy_efficiency_target=0.95,
                regenerative_braking=True,
            )
        elif template == "aggressive":
            # 激进配置：快速但鲁棒性较低
            return cls(
                **base_dict,
                initial_speed=0.45,
                disturbance_rejection=0.6,
                recovery_speed=0.3,
                max_lean_angle_deg=20.0,
                energy_efficiency_target=0.75,
            )
        else:
            # 使用默认参数
            return cls(**base_dict)


# ============================================================================
# 3. 自定义步态模型示例
# ============================================================================


class RobustWalker(CompassGait):
    """鲁棒步行机器人模型

    继承 CompassGait，增加扰动处理和自适应能力。
    """

    def __init__(self, params: RobustWalkerParams):
        """初始化鲁棒步行器

        Args:
            params: 鲁棒步行器参数
        """
        super().__init__(params)
        self.params: RobustWalkerParams  # 类型提示

        # 扰动状态跟踪
        self.disturbance_history: list[float] = []
        self.max_history_length = 100

        # 自适应参数
        self.adaptive_damping = params.swing_damping
        self.adaptive_stiffness = params.passive_hip_stiffness

    def apply_disturbance_compensation(
        self,
        measured_state: np.ndarray,
        nominal_state: np.ndarray,
    ) -> np.ndarray:
        """应用扰动补偿

        Args:
            measured_state: 测量状态 [q1, q2, dq1, dq2]
            nominal_state: 期望状态 [q1, q2, dq1, dq2]

        Returns:
            补偿后的控制输入
        """
        # 计算状态误差
        state_error = measured_state - nominal_state
        error_norm = np.linalg.norm(state_error)

        # 记录扰动历史
        self.disturbance_history.append(error_norm)
        if len(self.disturbance_history) > self.max_history_length:
            self.disturbance_history.pop(0)

        # 根据扰动历史自适应调整阻尼
        if len(self.disturbance_history) > 10:
            recent_disturbance = np.mean(self.disturbance_history[-10:])
            # 扰动大时增加阻尼以提高稳定性
            self.adaptive_damping = self.params.swing_damping * (
                1.0 + recent_disturbance * self.params.disturbance_rejection
            )

        # 计算补偿控制
        # 使用简单的比例控制，实际应用中可使用更复杂的控制律
        compensation = -self.params.recovery_speed * state_error

        return compensation

    def check_stability(self, lean_angle: float) -> bool:
        """检查稳定性

        Args:
            lean_angle: 当前倾斜角度 (rad)

        Returns:
            True 如果在稳定范围内
        """
        return abs(lean_angle) <= self.params.max_lean_angle

    def compute_energy_efficiency(
        self,
        mechanical_work: float,
        electrical_input: float,
    ) -> float:
        """计算能量效率

        Args:
            mechanical_work: 机械功 (J)
            electrical_input: 电能输入 (J)

        Returns:
            能量效率 [0, 1]
        """
        if electrical_input <= 0:
            return 0.0

        efficiency = mechanical_work / electrical_input

        # 如果启用再生制动，可以增加效率
        if self.params.regenerative_braking and mechanical_work < 0:
            # 负功表示制动，假设可以回收 30% 的能量
            efficiency = min(1.0, efficiency + 0.3)

        return efficiency

    def get_status_report(self) -> dict:
        """获取状态报告

        Returns:
            包含当前状态的字典
        """
        recent_disturbance = 0.0
        if self.disturbance_history:
            recent_disturbance = np.mean(self.disturbance_history[-10:])

        return {
            "model_type": "RobustWalker",
            "params": self.params.to_dict(),
            "adaptive_damping": self.adaptive_damping,
            "adaptive_stiffness": self.adaptive_stiffness,
            "recent_disturbance": recent_disturbance,
            "disturbance_history_length": len(self.disturbance_history),
        }

    def __repr__(self) -> str:
        return (
            f"RobustWalker(slope={self.params.slope_deg:.1f}°, "
            f"disturbance_rejection={self.params.disturbance_rejection:.2f}, "
            f"efficiency_target={self.params.energy_efficiency_target:.2f})"
        )


# ============================================================================
# 4. 使用示例
# ============================================================================


def example_custom_controllers():
    """示例：使用自定义控制器"""
    print("=" * 70)
    print("示例 1: 自定义控制器")
    print("=" * 70)

    # 1. 自适应 PD 控制器
    adaptive_ctrl = AdaptivePDController(
        kp_base=100.0,
        kd_base=10.0,
        adaptation_rate=5.0,
        torque_limit=50.0,
    )
    print(f"\n{adaptive_ctrl}")

    # 测试不同误差下的响应
    q_current = 0.0
    qd_current = 0.0

    for target in [0.1, 0.5, 1.0]:
        torque = adaptive_ctrl.compute_torque(q_current, qd_current, target=target)
        print(f"  目标={target:.1f} rad → 力矩={torque:.2f} N·m")

    # 2. 重力补偿控制器
    gravity_ctrl = GravityCompensatingController(
        kp=150.0,
        kd=15.0,
        leg_mass=5.0,
        leg_length=1.0,
        torque_limit=100.0,
    )
    print(f"\n{gravity_ctrl}")

    # 测试不同关节角度下的重力补偿
    target = 0.2
    for q in [0.0, 0.5, 1.0]:
        torque = gravity_ctrl.compute_torque(q, 0.0, target=target)
        print(f"  q={q:.1f} rad → 力矩={torque:.2f} N·m (含重力补偿)")

    # 3. 基于相位的控制器
    stance_ctrl = PDController(kp=200.0, kd=20.0)
    swing_ctrl = PDController(kp=50.0, kd=5.0)
    phase_ctrl = PhaseBasedController(
        stance_controller=stance_ctrl,
        swing_controller=swing_ctrl,
        phase="stance",
    )
    print(f"\n{phase_ctrl}")

    # 测试相位切换
    target = 0.3
    torque_stance = phase_ctrl.compute_torque(0.1, 0.0, target=target, phase="stance")
    torque_swing = phase_ctrl.compute_torque(0.1, 0.0, target=target, phase="swing")
    print(f"  支撑相力矩: {torque_stance:.2f} N·m")
    print(f"  摆动相力矩: {torque_swing:.2f} N·m")


def example_custom_params():
    """示例：使用自定义参数配置"""
    print("\n" + "=" * 70)
    print("示例 2: 自定义参数配置")
    print("=" * 70)

    # 1. 鲁棒配置
    robust_params = RobustWalkerParams.from_template("robust")
    print(f"\n鲁棒配置:")
    print(f"  坡度: {robust_params.slope_deg:.1f}°")
    print(f"  扰动抑制: {robust_params.disturbance_rejection:.2f}")
    print(f"  恢复速度: {robust_params.recovery_speed:.2f}")
    print(f"  最大倾斜角: {robust_params.max_lean_angle_deg:.1f}°")

    # 2. 高效配置
    efficient_params = RobustWalkerParams.from_template("efficient")
    print(f"\n高效配置:")
    print(f"  坡度: {efficient_params.slope_deg:.1f}°")
    print(f"  目标效率: {efficient_params.energy_efficiency_target:.2f}")
    print(f"  再生制动: {efficient_params.regenerative_braking}")

    # 3. 激进配置
    aggressive_params = RobustWalkerParams.from_template("aggressive")
    print(f"\n激进配置:")
    print(f"  初始速度: {aggressive_params.initial_speed:.2f} m/s")
    print(f"  最大倾斜角: {aggressive_params.max_lean_angle_deg:.1f}°")
    print(f"  扰动抑制: {aggressive_params.disturbance_rejection:.2f}")


def example_custom_walker():
    """示例：使用自定义步态模型"""
    print("\n" + "=" * 70)
    print("示例 3: 自定义步态模型")
    print("=" * 70)

    # 创建鲁棒步行器
    params = RobustWalkerParams.from_template("robust")
    walker = RobustWalker(params)
    print(f"\n{walker}")

    # 模拟扰动补偿
    print("\n模拟扰动补偿:")
    nominal_state = np.array([0.1, -0.1, 0.5, -0.5])

    for i in range(3):
        # 添加随机扰动
        disturbance = np.random.randn(4) * 0.05
        measured_state = nominal_state + disturbance

        # 应用补偿
        compensation = walker.apply_disturbance_compensation(
            measured_state, nominal_state
        )

        print(f"  步骤 {i+1}:")
        print(f"    扰动幅值: {np.linalg.norm(disturbance):.4f}")
        print(f"    补偿幅值: {np.linalg.norm(compensation):.4f}")

    # 检查稳定性
    print("\n稳定性检查:")
    test_angles = [0.0, 0.1, 0.2, 0.3]
    for angle in test_angles:
        stable = walker.check_stability(angle)
        status = "[OK] 稳定" if stable else "[FAIL] 不稳定"
        print(f"  倾斜角 {math.degrees(angle):.1f}°: {status}")

    # 计算能量效率
    print("\n能量效率计算:")
    test_cases = [
        (90.0, 100.0, "正常行走"),
        (80.0, 100.0, "低效行走"),
        (-20.0, 100.0, "制动（再生）"),
    ]
    for mech_work, elec_input, desc in test_cases:
        efficiency = walker.compute_energy_efficiency(mech_work, elec_input)
        print(f"  {desc}: {efficiency:.2%}")

    # 状态报告
    print("\n状态报告:")
    status = walker.get_status_report()
    print(f"  模型类型: {status['model_type']}")
    print(f"  自适应阻尼: {status['adaptive_damping']:.4f}")
    print(f"  近期扰动: {status['recent_disturbance']:.4f}")


def main():
    """主函数：运行所有示例"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "自定义步行机器人示例" + " " * 30 + "║")
    print("║" + " " * 10 + "Custom Walker Models and Controllers" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")

    # 运行示例
    example_custom_controllers()
    example_custom_params()
    example_custom_walker()

    print("\n" + "=" * 70)
    print("总结：")
    print("=" * 70)
    print("""
1. 自定义控制器 (Controller)：
   - 继承 Controller 基类
   - 实现 compute_torque() 方法
   - 可选实现 reset() 方法

2. 自定义参数配置 (CompassGaitParams)：
   - 使用 @dataclass(frozen=True) 装饰器
   - 继承 CompassGaitParams
   - 可扩展 from_template() 类方法

3. 自定义步态模型 (CompassGait)：
   - 继承 CompassGait 基类
   - 调用 super().__init__(params)
   - 添加新的方法和属性

参考文件：
- common/controllers.py - 控制器基类
- common/compass_gait.py - 步态模型基类
- 各版本目录 (v01-v24) - 实际应用示例
    """)
    print("=" * 70)


if __name__ == "__main__":
    main()
