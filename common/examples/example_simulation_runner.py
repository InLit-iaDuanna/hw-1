"""simulation_runner 模块使用示例。

展示通用仿真循环、回调、早停条件的使用方法。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import mujoco

from common.model_loader import load_model_from_xml
from common.simulation_runner import (
    Callback,
    ControllerCallback,
    DataRecorder,
    HeightThreshold,
    NaNDetector,
    SimulationRunner,
)


def example_1_basic_simulation():
    """示例 1：最简单的仿真循环。"""
    print("=== 示例 1：基础仿真循环 ===")

    xml = """<mujoco model="free_fall">
      <option timestep="0.01" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="5 5 0.1" pos="0 0 0"/>
        <body name="ball" pos="0 0 2">
          <joint name="free" type="free"/>
          <geom name="sphere" type="sphere" size="0.1" mass="1.0"/>
        </body>
      </worldbody>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)

    # 不添加任何回调或早停条件
    runner = SimulationRunner(model, data)
    result = runner.run(duration=2.0)

    print(f"仿真时间: {result.simulated_time:.2f} s")
    print(f"总步数: {result.total_steps}")
    print(f"成功: {result.success}")
    print(f"停止原因: {result.stop_reason}")
    print(f"最终球高度: {data.qpos[2]:.3f} m")
    print()


def example_2_with_data_recorder():
    """示例 2：使用数据记录器。"""
    print("=== 示例 2：数据记录 ===")

    xml = """<mujoco model="pendulum">
      <option timestep="0.005" gravity="0 0 -9.81"/>
      <worldbody>
        <body name="bob" pos="0 0 0">
          <joint name="hinge" type="hinge" axis="0 1 0"/>
          <geom name="rod" type="capsule" fromto="0 0 0 0 0 -0.5" size="0.01" mass="0.1"/>
          <geom name="mass" type="sphere" pos="0 0 -0.5" size="0.08" mass="1.0"/>
        </body>
      </worldbody>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)

    # 初始角度 45 度
    data.qpos[0] = np.pi / 4

    # 创建数据记录器
    recorder = DataRecorder(
        sample_hz=100.0,
        extractors={
            "angle": lambda m, d: float(d.qpos[0]),
            "angular_velocity": lambda m, d: float(d.qvel[0]),
            "kinetic_energy": lambda m, d: 0.5 * float(d.qvel[0]) ** 2,
        },
    )

    runner = SimulationRunner(model, data, callbacks=[recorder])
    result = runner.run(duration=3.0)

    # 提取数据
    recorded_data = recorder.get_data()
    print(f"记录了 {len(recorded_data['time'])} 个样本")
    print(
        f"角度范围: [{min(recorded_data['angle']):.3f}, {max(recorded_data['angle']):.3f}] rad"
    )
    print(f"最大动能: {max(recorded_data['kinetic_energy']):.4f} J")
    print()


def example_3_with_controller():
    """示例 3：添加控制器。"""
    print("=== 示例 3：PD 控制器 ===")

    xml = """<mujoco model="actuated_pendulum">
      <option timestep="0.002" gravity="0 0 -9.81"/>
      <worldbody>
        <body name="bob" pos="0 0 0">
          <joint name="hinge" type="hinge" axis="0 1 0"/>
          <geom name="rod" type="capsule" fromto="0 0 0 0 0 -0.5" size="0.01" mass="0.1"/>
          <geom name="mass" type="sphere" pos="0 0 -0.5" size="0.08" mass="1.0"/>
        </body>
      </worldbody>
      <actuator>
        <motor name="torque" joint="hinge" gear="1" ctrllimited="true" ctrlrange="-5 5"/>
      </actuator>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)

    # 初始偏移
    data.qpos[0] = np.pi / 3

    # PD 控制器回调
    kp, kd = 8.0, 2.0
    target_angle = 0.0

    def pd_controller(model, data, t):
        error = target_angle - float(data.qpos[0])
        error_dot = -float(data.qvel[0])
        data.ctrl[0] = kp * error + kd * error_dot

    # 数据记录
    recorder = DataRecorder(
        sample_hz=200.0,
        extractors={
            "angle": lambda m, d: float(d.qpos[0]),
            "control": lambda m, d: float(d.ctrl[0]),
        },
    )

    runner = SimulationRunner(
        model,
        data,
        callbacks=[
            ControllerCallback(pd_controller),
            recorder,
        ],
    )
    result = runner.run(duration=5.0)

    recorded_data = recorder.get_data()
    final_error = abs(recorded_data["angle"][-1] - target_angle)
    print(f"仿真完成，最终误差: {final_error:.4f} rad")
    print(
        f"控制力矩范围: [{min(recorded_data['control']):.2f}, {max(recorded_data['control']):.2f}] Nm"
    )
    print()


def example_4_with_early_stop():
    """示例 4：早停条件。"""
    print("=== 示例 4：早停条件 ===")

    xml = """<mujoco model="falling_walker">
      <option timestep="0.01" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="10 1 0.1" pos="0 0 0"/>
        <body name="hip" pos="0 0 1.0">
          <joint name="hip_x" type="slide" axis="1 0 0"/>
          <joint name="hip_z" type="slide" axis="0 0 1"/>
          <geom name="hip_mass" type="sphere" size="0.08" mass="5.0"/>
        </body>
      </worldbody>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)

    # 初始速度（会摔倒）
    data.qvel[0] = 0.5
    data.qvel[1] = -0.2

    # 添加高度检测早停条件
    runner = SimulationRunner(
        model,
        data,
        early_stop_conditions=[
            NaNDetector(),
            HeightThreshold("hip", min_height=0.3, max_height=3.0),
        ],
    )

    result = runner.run(duration=10.0)

    print(f"仿真时间: {result.simulated_time:.2f} s")
    print(f"停止原因: {result.stop_reason}")
    print(f"最终高度: {data.qpos[1]:.3f} m")
    print("（因为 hip 高度低于 0.3 m，触发早停）")
    print()


def example_5_custom_callback():
    """示例 5：自定义回调类。"""
    print("=== 示例 5：自定义回调 ===")

    class EventCounter(Callback):
        """统计接触事件的自定义回调。"""

        def __init__(self):
            self.contact_count = 0

        def on_step(self, model, data, t, step):
            if data.ncon > 0:
                self.contact_count += 1
                # 使用 efc_force 获取接触力（约束力）
                for i in range(data.ncon):
                    # MuJoCo 接触力在 data.efc_force 中，但这是所有约束力
                    # 简化：只统计接触数
                    pass

        def on_finish(self, model, data, result):
            result.custom_data["contact_steps"] = self.contact_count
            result.custom_data["total_contacts"] = data.ncon

    xml = """<mujoco model="bouncing_ball">
      <option timestep="0.005" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="5 5 0.1" pos="0 0 0"/>
        <body name="ball" pos="0 0 2">
          <joint name="free" type="free"/>
          <geom name="sphere" type="sphere" size="0.1" mass="0.5" solref="0.02 1"/>
        </body>
      </worldbody>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)

    event_counter = EventCounter()
    runner = SimulationRunner(model, data, callbacks=[event_counter])
    result = runner.run(duration=3.0)

    print(f"接触步数: {result.custom_data['contact_steps']}")
    print(f"当前接触数: {result.custom_data['total_contacts']}")
    print()


if __name__ == "__main__":
    Path("out").mkdir(exist_ok=True)

    example_1_basic_simulation()
    example_2_with_data_recorder()
    example_3_with_controller()
    example_4_with_early_stop()
    example_5_custom_callback()

    print("所有示例运行完成。")
