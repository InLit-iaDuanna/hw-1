"""示例：控制器使用演示。

展示如何使用 PassiveController 和 PDController。
"""

from common.controllers import PassiveController, PDController


def example_passive_controller():
    """演示被动控制器的使用。"""
    print("=== 被动控制器示例 ===")
    controller = PassiveController()

    # 被动控制器始终返回零力矩
    print(f"控制力矩 (q=0.1, qd=0.5): {controller.compute_torque(0.1, 0.5):.3f} N·m")
    print(f"控制力矩 (q=1.0, qd=-0.2): {controller.compute_torque(1.0, -0.2):.3f} N·m")
    print()


def example_basic_pd_controller():
    """演示基本 PD 控制器的使用。"""
    print("=== 基本 PD 控制器示例 ===")
    controller = PDController(kp=100.0, kd=10.0)
    print(f"控制器配置: {controller}")

    # 位置误差 = -0.1 rad，速度 = 0
    q, qd, target = 0.1, 0.0, 0.0
    torque = controller.compute_torque(q, qd, target)
    print(f"状态: q={q:.2f}, qd={qd:.2f}, target={target:.2f}")
    print(f"控制力矩: {torque:.3f} N·m")
    print()

    # 位置误差 = 0，速度 = 1.0 rad/s
    q, qd, target = 0.0, 1.0, 0.0
    torque = controller.compute_torque(q, qd, target)
    print(f"状态: q={q:.2f}, qd={qd:.2f}, target={target:.2f}")
    print(f"控制力矩: {torque:.3f} N·m")
    print()


def example_limited_pd_controller():
    """演示带力矩限幅的 PD 控制器。"""
    print("=== 带限幅 PD 控制器示例 ===")
    controller = PDController(kp=200.0, kd=20.0, torque_limit=50.0)
    print(f"控制器配置: {controller}")

    # 小误差，未饱和
    q, qd, target = 0.1, 0.0, 0.0
    torque = controller.compute_torque(q, qd, target)
    print(f"小误差 (q={q:.2f}): {torque:.3f} N·m (未饱和)")

    # 大误差，饱和
    q, qd, target = 1.0, 0.0, 0.0
    torque = controller.compute_torque(q, qd, target)
    print(f"大误差 (q={q:.2f}): {torque:.3f} N·m (饱和到限制)")
    print()


def example_dynamic_gains():
    """演示动态调整控制增益。"""
    print("=== 动态调整增益示例 ===")
    controller = PDController(kp=100.0, kd=10.0)

    q, qd, target = 0.1, 0.5, 0.0

    # 使用初始增益
    torque1 = controller.compute_torque(q, qd, target)
    print(f"初始增益 (kp=100, kd=10): {torque1:.3f} N·m")

    # 临时覆盖增益（不改变控制器配置）
    torque2 = controller.compute_torque(q, qd, target, kp=200.0, kd=20.0)
    print(f"临时增益 (kp=200, kd=20): {torque2:.3f} N·m")

    # 验证原始增益未改变
    torque3 = controller.compute_torque(q, qd, target)
    print(f"恢复原始增益: {torque3:.3f} N·m")

    # 永久更新增益
    controller.set_gains(kp=50.0, kd=5.0)
    torque4 = controller.compute_torque(q, qd, target)
    print(f"更新后增益 (kp=50, kd=5): {torque4:.3f} N·m")
    print()


def example_trajectory_tracking():
    """演示轨迹跟踪场景。"""
    print("=== 轨迹跟踪示例 ===")
    import numpy as np

    controller = PDController(kp=100.0, kd=20.0, torque_limit=30.0)

    # 模拟简单的正弦轨迹跟踪
    dt = 0.01
    t_array = np.arange(0, 2.0, dt)

    print("跟踪正弦轨迹（周期 1.0s，幅值 0.2 rad）")
    print("时间 (s) | 目标 (rad) | 当前 (rad) | 速度 (rad/s) | 力矩 (N·m)")
    print("-" * 70)

    # 初始状态
    q, qd = 0.0, 0.0

    for i, t in enumerate(t_array):
        # 目标轨迹：正弦波
        target = 0.2 * np.sin(2 * np.pi * t)

        # 计算控制力矩
        torque = controller.compute_torque(q, qd, target)

        # 每 0.25 秒打印一次
        if i % 25 == 0:
            print(
                f"{t:8.2f} | {target:10.4f} | {q:10.4f} | {qd:12.4f} | {torque:10.3f}"
            )

        # 简化的动力学更新（假设单位惯量）
        qdd = torque
        qd += qdd * dt
        q += qd * dt

    print()


if __name__ == "__main__":
    example_passive_controller()
    example_basic_pd_controller()
    example_limited_pd_controller()
    example_dynamic_gains()
    example_trajectory_tracking()
