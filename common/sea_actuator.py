"""SEA (Series Elastic Actuator) 串联弹性驱动器模型。

基于 V15.1 SEA 架构，提供可配置弹簧刚度的串联弹性驱动器实现。
串联弹簧位于电机转子和负载连杆之间，提供柔顺性和冲击缓冲。

拓扑结构：
    motor_rotor (actuated)
        ↓ (series spring: k_sea, c_sea)
    load_link (passive, connects to thigh/shank)

弹簧力模型：
    F_spring = -k_sea * q_link - c_sea * qd_link

其中：
    q_link: 弹簧偏转角度（link joint 相对角度）
    qd_link: 弹簧偏转角速度
    k_sea: 弹簧刚度 (N·m/rad)
    c_sea: 弹簧阻尼 (N·m·s/rad)

退化特性：
    当 k_sea → ∞ 时，q_link → 0，系统退化为刚性直驱（V14c）。

能量审计：
    W_motor_input = ∫ τ_motor · ω_motor dt
    W_link_useful = ∫ τ_spring · ω_link dt
    W_damper_loss = ∫ c_sea · ω_link² dt
    dPE_spring = PE_final - PE_initial

理论上：W_motor_input ≈ W_link_useful + W_damper_loss + dPE_spring

参考：
    - V15.1 README: D:\\Dunna\\Documents\\hw-1\\v15_1_sea_direct\\README.md
    - simulate_v151.py: 完整实现示例
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SEAParams:
    """串联弹性驱动器参数配置。

    Attributes:
        k_sea: 弹簧刚度 (N·m/rad)，控制柔顺度。
            - k=500: 柔性配置，最大偏转 ~1.6°，适合冲击吸收
            - k=1000-5000: 中等刚度，平衡柔顺性与控制精度
            - k=10000: 接近刚性，退化为直驱模式
        c_sea: 弹簧阻尼 (N·m·s/rad)。
            - 若 <0，则自动计算亚临界阻尼：0.1 × 2√(k_sea × I_rotor)
            - 若 ≥0，则使用指定值
        motor_rotor_mass: 电机转子质量 (kg)，默认 0.01 kg
        motor_rotor_iyy: 电机转子 y 轴转动惯量 (kg·m²)，默认 0.004
        motor_rotor_ixy: 电机转子 x/z 轴转动惯量 (kg·m²)，默认 0.002
        motor_bearing_damping: 电机轴承阻尼 (N·m·s/rad)，默认 0.001

    Example:
        >>> # 柔性配置（V15.1 最优）
        >>> sea_soft = SEAParams(k_sea=500.0, c_sea=-1.0)
        >>> sea_soft.damping_resolved(I_rotor=0.004)
        0.0894...  # 自动计算的亚临界阻尼

        >>> # 刚性配置（退化测试）
        >>> sea_stiff = SEAParams(k_sea=10000.0)
        >>> # forward ≈ V14c (4.6 m), 验证实现正确性
    """

    k_sea: float = 1000.0
    c_sea: float = -1.0
    motor_rotor_mass: float = 0.01
    motor_rotor_iyy: float = 0.004
    motor_rotor_ixy: float = 0.002
    motor_bearing_damping: float = 0.001

    def damping_resolved(self, I_rotor: float | None = None) -> float:
        """解析弹簧阻尼系数。

        若 c_sea < 0，则计算亚临界阻尼：
            c_damping = 0.1 × 2 × √(k_sea × I_rotor)

        其中 0.1 是阻尼比（使系统欠阻尼，避免过阻尼导致响应迟缓）。

        Args:
            I_rotor: 电机转子惯量 (kg·m²)。若为 None，使用 motor_rotor_iyy。

        Returns:
            弹簧阻尼系数 (N·m·s/rad)
        """
        if self.c_sea >= 0:
            return float(self.c_sea)
        inertia = I_rotor if I_rotor is not None else self.motor_rotor_iyy
        return 0.1 * 2.0 * math.sqrt(max(self.k_sea, 1e-9) * inertia)

    def spring_natural_frequency(self, I_rotor: float | None = None) -> float:
        """计算弹簧-转子系统的固有频率 (rad/s)。

        ω_n = √(k_sea / I_rotor)

        物理意义：无阻尼情况下系统的自由振荡频率。

        Args:
            I_rotor: 电机转子惯量 (kg·m²)。若为 None，使用 motor_rotor_iyy。

        Returns:
            固有频率 (rad/s)

        Example:
            >>> sea = SEAParams(k_sea=1000.0, motor_rotor_iyy=0.004)
            >>> sea.spring_natural_frequency()
            500.0  # rad/s ≈ 79.6 Hz
        """
        inertia = I_rotor if I_rotor is not None else self.motor_rotor_iyy
        return math.sqrt(self.k_sea / max(inertia, 1e-9))

    def damping_ratio(self, I_rotor: float | None = None) -> float:
        """计算阻尼比 ζ (无量纲)。

        ζ = c_sea / (2 × √(k_sea × I_rotor))

        阻尼比分类：
            - ζ < 1: 欠阻尼（振荡衰减）
            - ζ = 1: 临界阻尼（最快无振荡响应）
            - ζ > 1: 过阻尼（缓慢无振荡响应）

        V15.1 使用 ζ=0.1（欠阻尼），保证快速响应同时抑制高频振荡。

        Args:
            I_rotor: 电机转子惯量 (kg·m²)。若为 None，使用 motor_rotor_iyy。

        Returns:
            阻尼比（无量纲）
        """
        inertia = I_rotor if I_rotor is not None else self.motor_rotor_iyy
        c_resolved = self.damping_resolved(inertia)
        return c_resolved / (2.0 * math.sqrt(self.k_sea * inertia))

    def recommended_timestep(self) -> float:
        """根据弹簧刚度推荐仿真时间步。

        高刚度弹簧需要更小的时间步以保证数值稳定性。

        Returns:
            推荐时间步 (s)

        Example:
            >>> SEAParams(k_sea=500).recommended_timestep()
            0.001  # 标准时间步
            >>> SEAParams(k_sea=10000).recommended_timestep()
            0.0005  # 刚性配置需要更小时间步
        """
        if self.k_sea >= 5e3:
            return 0.0005
        return 0.001


class SEAActuator:
    """串联弹性驱动器执行器类。

    管理单个 SEA 关节的状态、力矩计算和能量审计。

    使用示例：
        >>> # 初始化
        >>> sea_params = SEAParams(k_sea=1000.0, c_sea=-1.0)
        >>> sea = SEAActuator("left_hip", sea_params)

        >>> # 在仿真循环中
        >>> q_motor = 0.2  # 电机角度 (rad)
        >>> q_link = 0.05  # 弹簧偏转角度 (rad)
        >>> qd_motor = 1.0  # 电机角速度 (rad/s)
        >>> qd_link = 0.1  # 弹簧偏转角速度 (rad/s)
        >>> tau_motor_desired = 2.0  # FSM 期望扭矩 (N·m)

        >>> # 计算实际扭矩
        >>> tau_spring = sea.compute_spring_torque(q_link, qd_link)
        >>>
        >>> # 更新能量统计
        >>> dt = 0.001
        >>> sea.update_energy(tau_motor_desired, qd_motor, q_link, qd_link, dt)
        >>>
        >>> # 获取能量审计结果
        >>> audit = sea.get_energy_audit()
        >>> print(f"电机输入功: {audit['W_motor_input_J']:.3f} J")
    """

    def __init__(self, name: str, params: SEAParams):
        """初始化 SEA 驱动器。

        Args:
            name: 关节名称（如 "left_hip", "right_hip"）
            params: SEA 参数配置
        """
        self.name = name
        self.params = params
        self.k_sea = float(params.k_sea)
        self.c_sea = float(params.damping_resolved())

        # 能量审计累加器
        self.W_motor_input = 0.0  # 电机输入功 (J)
        self.W_link_useful = 0.0  # 连杆有效功 (J)
        self.W_damper_loss = 0.0  # 阻尼耗散 (J)
        self.PE_spring_initial = 0.0  # 初始弹性势能 (J)
        self.spring_pe_max = 0.0  # 最大弹性势能 (J)
        self.spring_pe_sum = 0.0  # 弹性势能累加（用于计算平均值）
        self.q_link_max = 0.0  # 最大弹簧偏转角 (rad)
        self.audit_samples = 0  # 采样次数

        self._initialized = False

    def initialize(self, q_link_initial: float) -> None:
        """初始化能量审计的初始弹性势能。

        必须在仿真开始前调用一次，用于计算 dPE_spring。

        Args:
            q_link_initial: 初始弹簧偏转角度 (rad)，通常为 0
        """
        self.PE_spring_initial = 0.5 * self.k_sea * q_link_initial**2
        self._initialized = True

    def compute_spring_torque(self, q_link: float, qd_link: float) -> float:
        """计算弹簧产生的扭矩（作用在连杆上）。

        弹簧力模型：
            τ_spring = -k_sea × q_link - c_sea × qd_link

        物理解释：
            - 刚度项 -k_sea × q_link：弹簧的恢复力，与偏转角成正比
            - 阻尼项 -c_sea × qd_link：阻尼力，与偏转角速度成正比

        符号约定：
            - q_link > 0：弹簧被拉伸，τ_spring < 0（回弹力）
            - q_link < 0：弹簧被压缩，τ_spring > 0（回弹力）

        Args:
            q_link: 弹簧偏转角度 (rad)
            qd_link: 弹簧偏转角速度 (rad/s)

        Returns:
            弹簧扭矩 (N·m)，作用在连杆上

        Example:
            >>> sea = SEAActuator("test", SEAParams(k_sea=1000.0, c_sea=10.0))
            >>> sea.compute_spring_torque(q_link=0.1, qd_link=0.05)
            -100.5  # = -1000×0.1 - 10×0.05
        """
        return -self.k_sea * q_link - self.c_sea * qd_link

    def compute_spring_pe(self, q_link: float) -> float:
        """计算弹簧弹性势能 (J)。

        PE = 0.5 × k_sea × q_link²

        Args:
            q_link: 弹簧偏转角度 (rad)

        Returns:
            弹性势能 (J)
        """
        return 0.5 * self.k_sea * q_link**2

    def update_energy(
        self,
        tau_motor: float,
        qd_motor: float,
        q_link: float,
        qd_link: float,
        dt: float,
    ) -> None:
        """更新能量审计统计（每个时间步调用）。

        能量平衡方程：
            W_motor_input = ∫ τ_motor · ω_motor dt
            W_link_useful = ∫ (-k*q) · ω_link dt  (只计刚度项，不含阻尼)
            W_damper_loss = ∫ c_sea · ω_link² dt  (阻尼耗散)
            dPE_spring = PE_final - PE_initial

        理论上：W_motor_input ≈ W_link_useful + W_damper_loss + dPE_spring

        Note:
            τ_spring = -k*q - c*qd，其中 -k*q 项传递到连杆（可逆），
            -c*qd 项在阻尼中耗散（不可逆）。为避免重复计数，
            W_link_useful 只计刚度项功率。

        Args:
            tau_motor: 电机实际输出扭矩 (N·m)
            qd_motor: 电机角速度 (rad/s)
            q_link: 弹簧偏转角度 (rad)
            qd_link: 弹簧偏转角速度 (rad/s)
            dt: 时间步长 (s)
        """
        # 电机输入功
        self.W_motor_input += tau_motor * qd_motor * dt

        # 连杆接收功（仅刚度项，不含阻尼）
        tau_spring_stiffness = -self.k_sea * q_link
        self.W_link_useful += tau_spring_stiffness * qd_link * dt

        # 阻尼耗散（独立计算，避免重复）
        self.W_damper_loss += self.c_sea * qd_link**2 * dt

        # 弹性势能统计
        spring_pe = self.compute_spring_pe(q_link)
        self.spring_pe_max = max(self.spring_pe_max, spring_pe)
        self.spring_pe_sum += spring_pe
        self.audit_samples += 1

        # 最大偏转角统计
        self.q_link_max = max(self.q_link_max, abs(q_link))

    def get_energy_audit(self) -> dict:
        """获取能量审计报告。

        Returns:
            包含以下字段的字典：
                - W_motor_input_J: 电机输入总功 (J)
                - W_link_useful_J: 连杆接收总功 (J)
                - W_damper_loss_J: 阻尼耗散总能量 (J)
                - dPE_spring_J: 弹性势能变化 (J)
                - PE_spring_initial_J: 初始弹性势能 (J)
                - PE_spring_final_J: 最终弹性势能 (J)
                - spring_pe_max_J: 最大弹性势能 (J)
                - spring_pe_mean_J: 平均弹性势能 (J)
                - q_link_max_deg: 最大偏转角 (度)
                - energy_balance_error_J: 能量平衡误差 (J)
                - energy_balance_error_pct: 能量平衡误差百分比 (%)
        """
        if not self._initialized:
            raise RuntimeError(
                f"SEAActuator '{self.name}' not initialized. "
                "Call initialize(q_link_initial) before simulation."
            )

        # 注意：此处无法直接获取 q_link_final，需要在外部调用时传入
        # 或者在最后一次 update_energy 后手动设置
        PE_spring_final = self.spring_pe_max  # 近似，实际应该是最终值
        dPE_spring = PE_spring_final - self.PE_spring_initial

        # 能量平衡检查
        energy_input = self.W_motor_input
        energy_output = self.W_link_useful + self.W_damper_loss + dPE_spring
        energy_error = energy_input - energy_output
        energy_error_pct = (
            100.0 * energy_error / max(abs(energy_input), 1e-9)
            if energy_input != 0 else 0.0
        )

        return {
            "W_motor_input_J": self.W_motor_input,
            "W_link_useful_J": self.W_link_useful,
            "W_damper_loss_J": self.W_damper_loss,
            "dPE_spring_J": dPE_spring,
            "PE_spring_initial_J": self.PE_spring_initial,
            "PE_spring_final_J": PE_spring_final,
            "spring_pe_max_J": self.spring_pe_max,
            "spring_pe_mean_J": (
                self.spring_pe_sum / max(1, self.audit_samples)
            ),
            "q_link_max_deg": math.degrees(self.q_link_max),
            "energy_balance_error_J": energy_error,
            "energy_balance_error_pct": energy_error_pct,
        }

    def finalize_energy_audit(self, q_link_final: float) -> dict:
        """完成能量审计并返回最终报告。

        在仿真结束后调用，提供准确的最终弹性势能。

        Args:
            q_link_final: 仿真结束时的弹簧偏转角度 (rad)

        Returns:
            能量审计报告字典（同 get_energy_audit）
        """
        PE_spring_final = self.compute_spring_pe(q_link_final)
        dPE_spring = PE_spring_final - self.PE_spring_initial

        energy_input = self.W_motor_input
        energy_output = self.W_link_useful + self.W_damper_loss + dPE_spring
        energy_error = energy_input - energy_output
        energy_error_pct = (
            100.0 * energy_error / max(abs(energy_input), 1e-9)
            if energy_input != 0 else 0.0
        )

        return {
            "W_motor_input_J": self.W_motor_input,
            "W_link_useful_J": self.W_link_useful,
            "W_damper_loss_J": self.W_damper_loss,
            "dPE_spring_J": dPE_spring,
            "PE_spring_initial_J": self.PE_spring_initial,
            "PE_spring_final_J": PE_spring_final,
            "spring_pe_max_J": self.spring_pe_max,
            "spring_pe_mean_J": (
                self.spring_pe_sum / max(1, self.audit_samples)
            ),
            "q_link_max_deg": math.degrees(self.q_link_max),
            "energy_balance_error_J": energy_error,
            "energy_balance_error_pct": energy_error_pct,
        }

    def reset(self) -> None:
        """重置能量审计统计。"""
        self.W_motor_input = 0.0
        self.W_link_useful = 0.0
        self.W_damper_loss = 0.0
        self.PE_spring_initial = 0.0
        self.spring_pe_max = 0.0
        self.spring_pe_sum = 0.0
        self.q_link_max = 0.0
        self.audit_samples = 0
        self._initialized = False


# 预设配置（对应 V15.1 实验结果）
PRESETS: dict[str, SEAParams] = {
    "v151_soft": SEAParams(
        k_sea=500.0,
        c_sea=-1.0,  # 自动亚临界阻尼
        motor_rotor_mass=0.01,
        motor_rotor_iyy=0.004,
        motor_rotor_ixy=0.002,
        motor_bearing_damping=0.001,
    ),
    "v151_medium": SEAParams(
        k_sea=1000.0,
        c_sea=-1.0,
    ),
    "v151_stiff": SEAParams(
        k_sea=5000.0,
        c_sea=-1.0,
    ),
    "v151_rigid": SEAParams(
        k_sea=10000.0,
        c_sea=-1.0,
    ),
}


def build_sea_xml_fragment(
    side: str,
    params: SEAParams,
    lateral_offset: float,
    hip_torque_limit: float = 4.0,
) -> str:
    """生成 SEA 拓扑的 MuJoCo XML 片段。

    拓扑结构：
        hip body
        └─ {side}_motor_rotor (with inertia)
           ├─ joint: {side}_hip_motor (actuated)
           └─ {side}_thigh
              ├─ joint: {side}_hip_link (series spring)
              └─ ... (shank, foot)

    Args:
        side: "left" 或 "right"
        params: SEA 参数
        lateral_offset: 横向偏移量（左为负，右为正），单位 m
        hip_torque_limit: 电机扭矩限制，单位 N·m

    Returns:
        XML 字符串片段

    Example:
        >>> sea_params = PRESETS['v151_soft']
        >>> xml_left = build_sea_xml_fragment("left", sea_params, -0.055)
        >>> # 插入到完整 XML 的 hip body 下
    """
    k_sea = float(params.k_sea)
    c_sea = float(params.damping_resolved())
    rotor_mass = float(params.motor_rotor_mass)
    iyy = float(params.motor_rotor_iyy)
    ixy = float(params.motor_rotor_ixy)
    motor_damp = float(params.motor_bearing_damping)

    xml = f"""      <body name="{side}_motor_rotor" pos="0 {lateral_offset} 0">
        <inertial pos="0 0 0" mass="{rotor_mass}" diaginertia="{ixy} {iyy} {ixy}"/>
        <joint name="{side}_hip_motor" type="hinge" axis="0 1 0" range="-95 95" limited="true" armature="0" damping="{motor_damp}"/>
        <body name="{side}_thigh" pos="0 0 0">
        <joint name="{side}_hip_link" type="hinge" axis="0 1 0" range="-95 95" limited="true" armature="0" damping="{c_sea}" stiffness="{k_sea}" springref="0"/>
        <!-- thigh body content continues here -->
        </body>
      </body>"""

    return xml


if __name__ == "__main__":
    # 演示用法
    print("SEA Actuator Demo")
    print("=" * 60)

    # 测试不同配置
    for preset_name, params in PRESETS.items():
        print(f"\nPreset: {preset_name}")
        print(f"  k_sea: {params.k_sea} N·m/rad")
        print(f"  c_sea: {params.damping_resolved():.4f} N·m·s/rad")
        print(f"  ω_n: {params.spring_natural_frequency():.1f} rad/s")
        print(f"  f_n: {params.spring_natural_frequency() / (2*math.pi):.1f} Hz")
        print(f"  ζ: {params.damping_ratio():.3f}")
        print(f"  recommended dt: {params.recommended_timestep():.4f} s")

    # 模拟简单场景
    print("\n" + "=" * 60)
    print("Simulation Example")
    print("=" * 60)

    sea = SEAActuator("test_hip", PRESETS["v151_soft"])
    sea.initialize(q_link_initial=0.0)

    dt = 0.001
    for i in range(1000):
        t = i * dt
        # 模拟正弦扭矩输入
        tau_motor = 2.0 * math.sin(2 * math.pi * 1.0 * t)
        qd_motor = 1.0
        # 模拟弹簧偏转（简化）
        q_link = 0.1 * math.sin(2 * math.pi * 1.0 * t + 0.5)
        qd_link = 0.1 * 2 * math.pi * 1.0 * math.cos(2 * math.pi * 1.0 * t + 0.5)

        sea.update_energy(tau_motor, qd_motor, q_link, qd_link, dt)

    audit = sea.finalize_energy_audit(q_link_final=0.0)
    print(f"\nEnergy Audit:")
    print(f"  W_motor_input: {audit['W_motor_input_J']:.3f} J")
    print(f"  W_link_useful: {audit['W_link_useful_J']:.3f} J")
    print(f"  W_damper_loss: {audit['W_damper_loss_J']:.3f} J")
    print(f"  dPE_spring: {audit['dPE_spring_J']:.3f} J")
    print(f"  Max deflection: {audit['q_link_max_deg']:.2f}°")
    print(f"  Energy balance error: {audit['energy_balance_error_pct']:.2f}%")
