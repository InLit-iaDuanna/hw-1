"""综合示例：组合使用 model_loader + simulation_runner + data_io。

场景：加载模型 → 运行仿真 → 保存数据 → 重新加载分析
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import mujoco

from common.data_io import load_timeseries_csv, save_summary_json, save_timeseries_csv
from common.model_loader import get_model_info, load_model_from_xml
from common.simulation_runner import (
    ControllerCallback,
    DataRecorder,
    HeightThreshold,
    NaNDetector,
    SimulationRunner,
)


def main():
    print("=== 综合示例：完整仿真工作流 ===\n")

    # 步骤 1：加载模型
    print("步骤 1：加载模型")
    xml = """<mujoco model="simple_hopper">
      <option timestep="0.002" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="10 1 0.1" pos="0 0 0"/>
        <body name="torso" pos="0 0 0.8">
          <joint name="torso_x" type="slide" axis="1 0 0" damping="0.1"/>
          <joint name="torso_z" type="slide" axis="0 0 1" damping="0.1"/>
          <joint name="torso_pitch" type="hinge" axis="0 1 0" damping="0.05"/>
          <geom name="torso_mass" type="box" size="0.08 0.06 0.12" mass="3.0"/>
          <body name="leg" pos="0 0 -0.12">
            <joint name="hip" type="hinge" axis="0 1 0" range="-120 20" damping="0.1"/>
            <geom name="thigh" type="capsule" fromto="0 0 0 0 0 -0.3" size="0.025" mass="0.4"/>
            <body name="foot_body" pos="0 0 -0.3">
              <joint name="knee" type="hinge" axis="0 1 0" range="0 150" damping="0.08"/>
              <geom name="shank" type="capsule" fromto="0 0 0 0 0 -0.3" size="0.022" mass="0.3"/>
              <geom name="foot" type="sphere" pos="0 0 -0.3" size="0.06" mass="0.2"/>
            </body>
          </body>
        </body>
      </worldbody>
      <actuator>
        <motor name="hip_motor" joint="hip" gear="1" ctrllimited="true" ctrlrange="-20 20"/>
        <motor name="knee_motor" joint="knee" gear="1" ctrllimited="true" ctrlrange="-10 10"/>
      </actuator>
    </mujoco>"""

    model = load_model_from_xml(xml)
    data = mujoco.MjData(model)
    info = get_model_info(model)

    print(f"  模型信息: {info.n_joints} 关节, {info.n_actuators} 执行器")
    print(f"  总质量: {info.total_mass:.2f} kg")
    print(f"  时间步长: {info.timestep} s\n")

    # 步骤 2：初始化状态
    print("步骤 2：初始化")
    data.qpos[0] = 0.0  # torso_x
    data.qpos[1] = 0.8  # torso_z
    data.qpos[2] = 0.0  # torso_pitch
    data.qpos[3] = -30 * np.pi / 180  # hip
    data.qpos[4] = 60 * np.pi / 180  # knee
    print(
        f"  初始位置: hip={data.qpos[3]*180/np.pi:.1f}°, knee={data.qpos[4]*180/np.pi:.1f}°\n"
    )

    # 步骤 3：配置简单控制律（保持姿态 + 前推）
    print("步骤 3：配置控制律")

    def simple_controller(model, data, t):
        # 简单的 PD 控制保持站立姿态
        hip_target = -20 * np.pi / 180
        knee_target = 40 * np.pi / 180

        hip_error = hip_target - float(data.qpos[3])
        knee_error = knee_target - float(data.qpos[4])

        data.ctrl[0] = 15.0 * hip_error - 2.0 * float(data.qvel[3])
        data.ctrl[1] = 8.0 * knee_error - 1.5 * float(data.qvel[4])

        # 前进偏置力
        if t > 0.2:
            data.ctrl[0] += 3.0

    print("  控制律: PD 姿态保持 + 前推偏置\n")

    # 步骤 4：配置数据记录
    print("步骤 4：配置数据记录")
    recorder = DataRecorder(
        sample_hz=100.0,
        extractors={
            "torso_x": lambda m, d: float(d.qpos[0]),
            "torso_z": lambda m, d: float(d.qpos[1]),
            "pitch": lambda m, d: float(d.qpos[2]),
            "hip": lambda m, d: float(d.qpos[3]),
            "knee": lambda m, d: float(d.qpos[4]),
            "vx": lambda m, d: float(d.qvel[0]),
            "ctrl_hip": lambda m, d: float(d.ctrl[0]),
            "ctrl_knee": lambda m, d: float(d.ctrl[1]),
        },
    )
    print("  采样频率: 100 Hz, 8 个数据通道\n")

    # 步骤 5：运行仿真
    print("步骤 5：运行仿真")
    runner = SimulationRunner(
        model,
        data,
        callbacks=[ControllerCallback(simple_controller), recorder],
        early_stop_conditions=[
            NaNDetector(),
            HeightThreshold("torso", min_height=0.2, max_height=2.0),
        ],
    )

    result = runner.run(duration=5.0)
    print(f"  仿真时间: {result.simulated_time:.2f} s")
    print(f"  总步数: {result.total_steps}")
    print(f"  停止原因: {result.stop_reason}\n")

    # 步骤 6：保存数据
    print("步骤 6：保存数据")
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    # 保存时间序列
    sim_data = recorder.get_data()
    save_timeseries_csv(
        out_dir / "integrated_example_data.csv",
        sim_data,
        metadata={
            "controller": "simple_pd",
            "model": "simple_hopper",
            "total_mass_kg": info.total_mass,
        },
    )
    print(f"  时间序列已保存: {len(sim_data['time'])} 个样本")

    # 保存摘要
    final_x = sim_data["torso_x"][-1]
    final_z = sim_data["torso_z"][-1]
    avg_vx = np.mean(sim_data["vx"])

    summary = {
        "success": result.success,
        "simulated_time": result.simulated_time,
        "stop_reason": result.stop_reason,
        "forward_distance": final_x,
        "final_height": final_z,
        "average_velocity": avg_vx,
        "model_info": {
            "n_joints": info.n_joints,
            "n_actuators": info.n_actuators,
            "total_mass": info.total_mass,
        },
    }

    save_summary_json(
        out_dir / "integrated_example_summary.json",
        summary,
        metadata={"experiment": "hopper_forward"},
    )
    print("  摘要已保存\n")

    # 步骤 7：重新加载并分析
    print("步骤 7：重新加载并分析")
    loaded_data, meta = load_timeseries_csv(out_dir / "integrated_example_data.csv")

    print(f"  加载数据: {meta['n_rows']} 行, {len(meta['columns'])} 列")
    print(f"  前进距离: {final_x:.3f} m")
    print(f"  平均速度: {avg_vx:.3f} m/s")
    print(f"  最终高度: {final_z:.3f} m")
    print(
        f"  控制力矩范围: hip=[{min(sim_data['ctrl_hip']):.1f}, {max(sim_data['ctrl_hip']):.1f}] Nm"
    )
    print(
        f"  控制力矩范围: knee=[{min(sim_data['ctrl_knee']):.1f}, {max(sim_data['ctrl_knee']):.1f}] Nm"
    )

    print("\n=== 工作流完成 ===")
    print("所有数据已保存到 out/ 目录")


if __name__ == "__main__":
    main()
