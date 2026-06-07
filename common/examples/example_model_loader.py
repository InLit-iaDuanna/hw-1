"""model_loader 模块使用示例。

展示 MuJoCo 模型加载、验证、信息查询的典型工作流。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 设置 UTF-8 输出（Windows 兼容）
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.model_loader import (
    get_model_info,
    load_model_from_file,
    load_model_from_string_with_cache,
    load_model_from_xml,
    validate_model,
)


def example_1_load_from_xml_string():
    """示例 1：从 XML 字符串加载模型。"""
    print("=== 示例 1：从 XML 字符串加载 ===")

    xml = """<mujoco model="simple_pendulum">
      <option timestep="0.001" gravity="0 0 -9.81"/>
      <worldbody>
        <body name="bob" pos="0 0 0">
          <joint name="hinge" type="hinge" axis="0 1 0"/>
          <geom name="bob_geom" type="sphere" size="0.05" mass="1.0"/>
        </body>
        <geom name="ground" type="plane" size="2 2 0.1"/>
      </worldbody>
      <actuator>
        <motor name="torque" joint="hinge" gear="1"/>
      </actuator>
    </mujoco>"""

    try:
        model = load_model_from_xml(xml)
        print(f"[OK] 模型加载成功：{model.nq} 自由度，{model.nu} 执行器")
    except ValueError as e:
        print(f"[ERROR] 加载失败: {e}")
    print()


def example_2_load_from_file():
    """示例 2：从文件加载模型（需要现有模型文件）。"""
    print("=== 示例 2：从文件加载 ===")

    # 尝试加载 v10 的模型（如果存在）
    model_path = (
        Path(__file__).parent.parent.parent
        / "v10_rolling_foot_biomimetic_gait"
        / "models"
        / "rolling_foot_walker.xml"
    )

    if model_path.exists():
        try:
            model = load_model_from_file(model_path)
            print(f"[OK] 从文件加载成功: {model_path.name}")
            print(f"  关节数: {model.njnt}, 执行器数: {model.nu}")
        except ValueError as e:
            print(f"[ERROR] 加载失败: {e}")
    else:
        print(f"模型文件不存在: {model_path}")
        print("（这是正常的，示例仅用于演示）")
    print()


def example_3_get_model_info():
    """示例 3：提取模型信息。"""
    print("=== 示例 3：模型信息查询 ===")

    xml = """<mujoco model="walker_simplified">
      <option timestep="0.002" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="10 1 0.1"/>
        <body name="hip" pos="0 0 1">
          <joint name="hip_x" type="slide" axis="1 0 0"/>
          <joint name="hip_z" type="slide" axis="0 0 1"/>
          <geom name="hip_mass" type="sphere" size="0.08" mass="5.0"/>
          <body name="left_leg" pos="0 -0.05 0">
            <joint name="left_hip" type="hinge" axis="0 1 0" range="-90 90"/>
            <geom name="left_thigh" type="capsule" fromto="0 0 0 0 0 -0.4" size="0.02" mass="0.5"/>
          </body>
          <body name="right_leg" pos="0 0.05 0">
            <joint name="right_hip" type="hinge" axis="0 1 0" range="-90 90"/>
            <geom name="right_thigh" type="capsule" fromto="0 0 0 0 0 -0.4" size="0.02" mass="0.5"/>
          </body>
        </body>
      </worldbody>
      <actuator>
        <motor name="left_motor" joint="left_hip" gear="1"/>
        <motor name="right_motor" joint="right_hip" gear="1"/>
      </actuator>
    </mujoco>"""

    model = load_model_from_xml(xml)
    info = get_model_info(model)

    print(f"关节数: {info.n_joints}")
    print(f"  关节列表: {info.joint_names}")
    print(f"执行器数: {info.n_actuators}")
    print(f"  执行器列表: {info.actuator_names}")
    print(f"Body 数: {info.n_bodies}")
    print(f"  Body 列表: {info.body_names}")
    print(f"总质量: {info.total_mass:.2f} kg")
    print(f"时间步长: {info.timestep} s")
    print(f"状态空间维度: qpos={info.qpos_dim}, qvel={info.qvel_dim}")
    print()


def example_4_validate_model():
    """示例 4：验证模型包含所需组件。"""
    print("=== 示例 4：模型验证 ===")

    xml = """<mujoco model="test_walker">
      <option timestep="0.001"/>
      <worldbody>
        <geom name="floor" type="plane" size="5 1 0.1"/>
        <body name="torso" pos="0 0 1">
          <joint name="slide_x" type="slide" axis="1 0 0"/>
          <geom name="torso_mass" type="box" size="0.1 0.05 0.2" mass="10"/>
        </body>
      </worldbody>
      <actuator>
        <motor name="push" joint="slide_x" gear="1"/>
      </actuator>
    </mujoco>"""

    model = load_model_from_xml(xml)

    # 测试 1：验证存在的组件
    ok, errors = validate_model(
        model,
        required_joints=["slide_x"],
        required_actuators=["push"],
        required_bodies=["torso"],
    )
    print(f"验证测试 1（应该通过）: {'[OK] 通过' if ok else '[FAIL] 失败'}")
    if errors:
        for err in errors:
            print(f"  - {err}")

    # 测试 2：验证不存在的组件
    ok, errors = validate_model(
        model,
        required_joints=["hip_z", "knee"],  # 这些不存在
        required_actuators=["hip_motor"],
    )
    print(f"验证测试 2（应该失败）: {'[OK] 通过' if ok else '[FAIL] 失败'}")
    if errors:
        for err in errors:
            print(f"  - {err}")
    print()


def example_5_cached_loading():
    """示例 5：带缓存的模型加载（参数扫描场景）。"""
    print("=== 示例 5：缓存加载 ===")

    cache_dir = Path("out/model_cache")

    def build_xml(mass: float) -> str:
        return f"""<mujoco model="pendulum_m{mass}">
          <option timestep="0.001"/>
          <worldbody>
            <body name="bob" pos="0 0 0">
              <joint name="hinge" type="hinge" axis="0 1 0"/>
              <geom name="mass" type="sphere" size="0.05" mass="{mass}"/>
            </body>
          </worldbody>
        </mujoco>"""

    # 第一次加载（会写入缓存）
    xml1 = build_xml(1.0)
    model1 = load_model_from_string_with_cache(xml1, cache_dir, "pendulum")
    print(f"首次加载质量=1.0 模型，缓存目录: {cache_dir}")

    # 第二次加载相同配置（直接从缓存读取）
    model2 = load_model_from_string_with_cache(xml1, cache_dir, "pendulum")
    print("再次加载相同配置（命中缓存）")

    # 加载不同配置（生成新缓存文件）
    xml3 = build_xml(2.5)
    model3 = load_model_from_string_with_cache(xml3, cache_dir, "pendulum")
    print("加载不同质量=2.5 模型（生成新缓存）")

    print(f"缓存目录中的文件数: {len(list(cache_dir.glob('*.xml')))}")
    print()


if __name__ == "__main__":
    Path("out").mkdir(exist_ok=True)

    example_1_load_from_xml_string()
    example_2_load_from_file()
    example_3_get_model_info()
    example_4_validate_model()
    example_5_cached_loading()

    print("所有示例运行完成。")
