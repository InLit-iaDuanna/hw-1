"""共享测试夹具和工具函数。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

HW1_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def hw1_root():
    """hw-1 项目根目录。"""
    return HW1_ROOT


@pytest.fixture
def common_path():
    """common 库路径。"""
    return HW1_ROOT / "common"


def assert_simulation_valid(data):
    """验证仿真数据有效性（无 NaN/Inf）。

    Args:
        data: MuJoCo MjData 对象
    """
    assert not np.any(np.isnan(data.qpos)), "qpos 包含 NaN"
    assert not np.any(np.isnan(data.qvel)), "qvel 包含 NaN"
    assert not np.any(np.isinf(data.qpos)), "qpos 包含 Inf"
    assert not np.any(np.isinf(data.qvel)), "qvel 包含 Inf"


def assert_robot_upright(data, model, min_height: float = 0.5):
    """验证机器人保持直立（hip 高度检查）。

    Args:
        data: MuJoCo MjData 对象
        model: MuJoCo MjModel 对象
        min_height: hip 最小高度（米）
    """
    import mujoco

    hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
    if hip_id < 0:
        pytest.skip("模型不包含 hip body")

    hip_z = data.xpos[hip_id, 2]
    assert hip_z > min_height, f"机器人倒地: hip_z={hip_z} < {min_height}"


def simulate_n_steps(model, data, n_steps: int):
    """运行 n 步仿真并验证数据有效性。

    Args:
        model: MuJoCo MjModel 对象
        data: MuJoCo MjData 对象
        n_steps: 仿真步数

    Returns:
        data: 更新后的 MjData 对象
    """
    import mujoco

    for _ in range(n_steps):
        mujoco.mj_step(model, data)
        assert_simulation_valid(data)

    return data


def get_hip_position(data, model):
    """获取 hip 位置。

    Args:
        data: MuJoCo MjData 对象
        model: MuJoCo MjModel 对象

    Returns:
        tuple: (x, z) hip 位置
    """
    import mujoco

    hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
    if hip_id < 0:
        raise ValueError("模型不包含 hip body")

    return data.xpos[hip_id, 0], data.xpos[hip_id, 2]


def calculate_forward_displacement(data_initial, data_final, model):
    """计算前向位移。

    Args:
        data_initial: 初始 MjData
        data_final: 终止 MjData
        model: MuJoCo MjModel 对象

    Returns:
        float: x 方向位移（米）
    """
    x_initial, _ = get_hip_position(data_initial, model)
    x_final, _ = get_hip_position(data_final, model)
    return x_final - x_initial


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录（用于测试生成的文件）。"""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir
