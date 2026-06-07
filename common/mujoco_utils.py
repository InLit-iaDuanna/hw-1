"""MuJoCo 工具函数：关节地址解析、接触检测。

简化 MuJoCo 模型查询操作，避免在每个版本中重复实现。
"""

from __future__ import annotations

import mujoco


def get_joint_address(model: mujoco.MjModel, name: str) -> tuple[int, int]:
    """获取关节的 qpos 和 qvel 地址索引。

    Args:
        model: MuJoCo 模型对象
        name: 关节名称（在 XML 中定义的 joint name）

    Returns:
        (qpos_addr, dof_addr): 位置和速度数组的索引

    Raises:
        KeyError: 如果关节名称不存在

    Examples:
        >>> qpos_idx, qvel_idx = get_joint_address(model, "left_hip")
        >>> q = data.qpos[qpos_idx]
        >>> qd = data.qvel[qvel_idx]
    """
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return model.jnt_qposadr[jid], model.jnt_dofadr[jid]


def get_contact_flags(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    ramp_name: str,
    left_geoms: list[str],
    right_geoms: list[str],
) -> tuple[bool, bool]:
    """检测左右脚与斜坡的接触状态。

    遍历当前时间步的所有接触对，判断左右脚是否与斜坡有接触。

    Args:
        model: MuJoCo 模型对象
        data: MuJoCo 数据对象（包含当前接触信息）
        ramp_name: 斜坡几何体名称（通常为 "ramp"）
        left_geoms: 左脚几何体名称列表，如 ["left_heel", "left_sole", "left_toe"]
        right_geoms: 右脚几何体名称列表，如 ["right_heel", "right_sole", "right_toe"]

    Returns:
        (left_contact, right_contact): 左右脚接触标志

    Examples:
        >>> left_geoms = ["left_heel", "left_sole", "left_toe", "left_sole_lat"]
        >>> right_geoms = ["right_heel", "right_sole", "right_toe", "right_sole_lat"]
        >>> left_c, right_c = get_contact_flags(model, data, "ramp", left_geoms, right_geoms)
        >>> if left_c:
        ...     print("Left foot in contact")
    """
    ramp_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, ramp_name)
    left_ids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in left_geoms
    ]
    right_ids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in right_geoms
    ]

    left_contact = False
    right_contact = False

    for i in range(data.ncon):
        pair = {data.contact[i].geom1, data.contact[i].geom2}
        if ramp_id in pair:
            if any(g in pair for g in left_ids):
                left_contact = True
            if any(g in pair for g in right_ids):
                right_contact = True

    return left_contact, right_contact
