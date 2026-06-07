"""L1 一阶电机模型：J_rotor + 库仑/粘滞摩擦 + 电流饱和。V16 起填充。

L1 假设电气暂态可忽略（L=0），电机扭矩瞬时跟随电流指令，仅约束峰值。这适合
仿生步行（带宽 ~5 Hz）的 MuJoCo 时间步（dt=1 ms），无需 sub-step。粘滞摩擦
和转子惯量通过 XML <joint damping/armature> 让 MuJoCo 隐式积分器处理；本模
块只在 Python 端做电流饱和与库仑摩擦（带 sign 平滑）。

折算口径：MotorParams 字段为电机侧 spec，joint_*() 方法返回关节侧派生量。
joint_J_eff = J_rotor·N²    joint_b_eff = b_visc·N²
joint_tau_C_eff = τ_C·N·η   joint_tau_sat = N·η·Kt·I_max
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotorParams:
    """L1 电机参数。所有字段按电机侧（motor-shaft）命名。"""

    name: str = "MX-64AR"
    Kt: float = 0.0109  # N·m/A，电机侧扭矩常数
    J_rotor: float = 7.0e-8  # kg·m²，电机侧转子惯量
    N: float = 200.0  # 减速比
    eta: float = 0.67  # 减速效率
    I_max: float = 4.1  # A，峰值/stall 电流
    I_cont: float = 1.2  # A，连续可用电流
    R_arm: float = 1.0  # Ω，电枢电阻（用于 P_elec 估计）
    tau_C_motor: float = 1.5e-3  # N·m，电机侧库仑摩擦
    b_visc_motor: float = 1.25e-6  # N·m·s/rad，电机侧粘滞摩擦
    omega_eps: float = 0.01  # rad/s，sign_smooth 平滑因子

    def joint_J_eff(self) -> float:
        """计算折算到关节侧的等效转动惯量。

        公式：J_joint = J_rotor · N²

        物理解释：电机侧转子惯量通过减速比的平方折算到关节侧。
        当关节转动 Δθ 时，电机转子转动 N·Δθ，动能增加为
        ½·J_rotor·(N·ω_joint)² = ½·(J_rotor·N²)·ω_joint²

        Returns:
            关节侧等效惯量（kg·m²），写入 MuJoCo XML <joint armature="...">

        Example:
            >>> motor = PRESETS['mx64ar']
            >>> motor.joint_J_eff()
            0.0028  # = 7.0e-8 * 200² kg·m²
        """
        return self.J_rotor * self.N * self.N

    def joint_b_eff(self) -> float:
        """计算折算到关节侧的等效粘滞摩擦系数。

        公式：b_joint = b_visc_motor · N²

        物理解释：粘滞摩擦扭矩 τ_friction = b·ω，当电机侧角速度为 N·ω_joint 时，
        电机侧摩擦扭矩 b_visc_motor·(N·ω_joint) 折算到关节侧为 b_visc_motor·N²·ω_joint

        Returns:
            关节侧等效粘滞阻尼（N·m·s/rad），写入 MuJoCo XML <joint damping="...">

        Example:
            >>> motor = PRESETS['mx64ar']
            >>> motor.joint_b_eff()
            0.05  # = 1.25e-6 * 200² N·m·s/rad
        """
        return self.b_visc_motor * self.N * self.N

    def joint_tau_C_eff(self) -> float:
        """计算折算到关节侧的等效库仑摩擦扭矩。

        公式：τ_C_joint = τ_C_motor · N · η

        物理解释：库仑摩擦是与速度方向相反的恒定扭矩。电机侧库仑摩擦 τ_C_motor
        通过减速比 N 放大，再乘以效率 η（考虑齿轮传动损耗）得到关节侧等效值。

        Why:
            库仑摩擦源于轴承/换向器的干摩擦，与速度无关（只与符号相关）。
            V16 实验发现 τ_C 与 FSM 控制律存在共振耦合，需要 V13.7 前馈补偿修复。

        Returns:
            关节侧等效库仑摩擦（N·m），用于控制器补偿或动力学计算

        Example:
            >>> motor = PRESETS['mx64ar']
            >>> motor.joint_tau_C_eff()
            0.201  # = 1.5e-3 * 200 * 0.67 N·m
        """
        return self.tau_C_motor * self.N * self.eta

    def joint_tau_sat_peak(self) -> float:
        """计算关节侧峰值扭矩饱和限制（对应电机 I_max）。

        公式：τ_sat_peak = N · η · Kt · I_max

        物理解释：电机 stall 电流 I_max 产生的最大扭矩经减速比放大和效率折减后
        的关节侧输出。这是短时（<1s）可用的峰值扭矩，用于控制器扭矩限幅。

        Returns:
            关节侧峰值扭矩（N·m），用于 np.clip(tau_des, -tau_sat, tau_sat)

        Example:
            >>> motor = PRESETS['mx64ar']
            >>> motor.joint_tau_sat_peak()
            5.98  # = 200 * 0.67 * 0.0109 * 4.1 N·m
        """
        return self.N * self.eta * self.Kt * self.I_max

    def joint_tau_sat_cont(self) -> float:
        """计算关节侧连续扭矩限制（对应电机 I_cont）。

        公式：τ_sat_cont = N · η · Kt · I_cont

        物理解释：电机连续额定电流产生的扭矩。长时间运行（>10s）应限制在此值
        以内，避免过热。步态仿真通常使用 joint_tau_sat_peak()，因为单步周期短。

        Returns:
            关节侧连续扭矩（N·m）

        Example:
            >>> motor = PRESETS['mx64ar']
            >>> motor.joint_tau_sat_cont()
            1.75  # = 200 * 0.67 * 0.0109 * 1.2 N·m
        """
        return self.N * self.eta * self.Kt * self.I_cont


PRESETS: dict[str, MotorParams] = {
    "mx64ar": MotorParams(
        name="Dynamixel MX-64AR @12V",
        Kt=0.0109,
        J_rotor=7.0e-8,
        N=200.0,
        eta=0.67,
        I_max=4.1,
        I_cont=1.2,
        R_arm=1.0,
        tau_C_motor=1.5e-3,
        b_visc_motor=1.25e-6,
    ),
    "ec_i40_53": MotorParams(
        name="Maxon EC-i 40 70W + GP32 53:1",
        Kt=0.0252,
        J_rotor=3.33e-6,
        N=53.0,
        eta=0.72,
        I_max=14.0,
        I_cont=2.5,
        R_arm=0.34,
        tau_C_motor=2.0e-3,
        b_visc_motor=4.0e-6,
    ),
    "ideal": MotorParams(
        name="ideal_v14c_degenerate",
        Kt=1.0,
        J_rotor=0.0,
        N=1.0,
        eta=1.0,
        I_max=1.0e9,
        I_cont=1.0e9,
        R_arm=0.0,
        tau_C_motor=0.0,
        b_visc_motor=0.0,
    ),
}


def _sign_smooth(omega: float, eps: float) -> float:
    """ω / (|ω| + ε)，避免 sign 在 ω=0 处的强非线性触发隐式积分震荡。"""
    return omega / (abs(omega) + eps)


class L1MotorActuator:
    """单关节 L1 电机：期望力矩 → 实际输出力矩 + 估计电流/电功。

    粘滞摩擦不在本类计算（已折到 XML <joint damping>）；本类只做电流饱和
    与库仑摩擦的关节侧扣减。
    """

    def __init__(self, motor: MotorParams):
        self.motor = motor
        self._tau_sat = motor.joint_tau_sat_peak()
        self._tau_C_eff = motor.joint_tau_C_eff()
        self._kt_joint = motor.N * motor.eta * motor.Kt
        self.saturation_count = 0

    def compute_actual_torque(
        self, tau_desired: float, omega_joint: float
    ) -> tuple[float, float]:
        """返回 (tau_out_joint_side, I_motor_estimated)。

        tau_out = clip(tau_desired, ±τ_sat) - τ_C_eff·sign_smooth(ω)
        I_motor = tau_after_sat / (N·η·Kt)
        """
        if tau_desired > self._tau_sat:
            tau_after_sat = self._tau_sat
            self.saturation_count += 1
        elif tau_desired < -self._tau_sat:
            tau_after_sat = -self._tau_sat
            self.saturation_count += 1
        else:
            tau_after_sat = tau_desired

        tau_friction_C = self._tau_C_eff * _sign_smooth(
            omega_joint, self.motor.omega_eps
        )
        tau_out = tau_after_sat - tau_friction_C

        i_motor = tau_after_sat / self._kt_joint if self._kt_joint > 0.0 else 0.0
        return tau_out, i_motor

    def electrical_power(self, tau_after_sat: float, omega_joint: float) -> float:
        """P_elec ≈ max(0, τ·ω) + I²·R。L1 忽略 di/dt。

        机械功用 tau_after_sat（电机实际输出，未扣库仑摩擦）×关节角速度；
        库仑摩擦本身是机械损耗，不在此处再扣。
        """
        p_mech = max(0.0, tau_after_sat * omega_joint)
        if self._kt_joint <= 0.0:
            return p_mech
        i_motor = tau_after_sat / self._kt_joint
        p_resistive = i_motor * i_motor * self.motor.R_arm
        return p_mech + p_resistive


def joint_armature_with_motor(base_armature: float, motor: MotorParams) -> float:
    """计算 MuJoCo <joint armature> 的合并惯量值。

    折算公式：J_total = J_base + N² · J_rotor_motor

    其中：
    - J_base: 关节基础转动惯量（kg·m²），来自连杆质量分布（通过 <inertial> 推导）
    - N: 减速比（电机侧→关节侧）
    - J_rotor_motor: 电机转子惯量（kg·m²）

    物理意义：
        MuJoCo 的 <joint armature> 是附加到关节的"额外惯量"，用于模拟电机转子
        惯量对动力学的影响。当关节加速时，电机转子以 N 倍角速度加速，因此消耗
        的扭矩为 (J_rotor · N²) · α_joint。

    Why:
        不能直接在 <body> 上增加质量来模拟电机，因为那会同时增加重力和碰撞质量。
        armature 只影响转动惯量，不影响重力/碰撞。

    Args:
        base_armature: 关节基础转动惯量（kg·m²），来自 link 质量分布或经验值
        motor: 电机参数（包含 J_rotor 和 N）

    Returns:
        折算后的总惯量（kg·m²），直接写入 XML <joint armature="...">

    Example:
        >>> motor = PRESETS['mx64ar']
        >>> joint_armature_with_motor(0.001, motor)
        0.0038  # = 0.001 + 200² × 7.0e-8

        在 V16 XML 中使用：
        >>> armature_val = joint_armature_with_motor(0.001, PRESETS['mx64ar'])
        >>> xml = f'<joint name="left_hip" armature="{armature_val:.6f}"/>'
    """
    return base_armature + motor.joint_J_eff()


def joint_damping_with_motor(base_damping: float, motor: MotorParams) -> float:
    """计算 MuJoCo <joint damping> 的合并阻尼值。

    折算公式：b_total = b_base + N² · b_visc_motor

    其中：
    - b_base: 关节基础粘滞阻尼（N·m·s/rad），来自轴承摩擦、空气阻力等
    - N: 减速比
    - b_visc_motor: 电机粘滞摩擦系数（N·m·s/rad），来自电机规格或实测

    物理意义：
        粘滞摩擦扭矩与角速度成正比：τ_friction = b · ω
        当关节以 ω_joint 转动时，电机以 N·ω_joint 转动，产生摩擦扭矩
        b_visc_motor · (N·ω_joint)，折算到关节侧为 (b_visc_motor · N²) · ω_joint

    Why:
        MuJoCo 的隐式积分器会自动处理粘滞阻尼，将其折入雅可比矩阵，比在 Python
        端手动计算更稳定。库仑摩擦（非线性）必须在 Python 端处理。

    Args:
        base_damping: 关节基础阻尼（N·m·s/rad），通常取 0.01-0.1 范围
        motor: 电机参数（包含 b_visc_motor 和 N）

    Returns:
        折算后的总阻尼（N·m·s/rad），直接写入 XML <joint damping="...">

    Example:
        >>> motor = PRESETS['mx64ar']
        >>> joint_damping_with_motor(0.01, motor)
        0.06  # = 0.01 + 200² × 1.25e-6

        在 V16 XML 中使用：
        >>> damping_val = joint_damping_with_motor(0.01, PRESETS['mx64ar'])
        >>> xml = f'<joint name="left_hip" damping="{damping_val:.6f}"/>'
    """
    return base_damping + motor.joint_b_eff()
