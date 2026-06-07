"""统一的 MuJoCo 模型加载接口。

设计原则：
- 支持从 XML 字符串、文件路径、临时文件加载
- 提供模型信息查询接口（关节、执行器、传感器等）
- 统一错误处理和验证
- 向后兼容现有版本的加载模式

接口：
- load_model_from_xml(xml_string) -> MjModel
- load_model_from_file(path) -> MjModel
- load_model_from_string_with_cache(xml, cache_dir, name) -> MjModel
- get_model_info(model) -> ModelInfo
- validate_model(model, required_joints, required_actuators) -> bool
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np


@dataclass
class ModelInfo:
    """MuJoCo 模型结构信息摘要。"""

    n_joints: int
    n_actuators: int
    n_sensors: int
    n_bodies: int
    n_geoms: int
    timestep: float

    joint_names: list[str]
    actuator_names: list[str]
    body_names: list[str]
    geom_names: list[str]

    total_mass: float
    qpos_dim: int
    qvel_dim: int


def load_model_from_xml(xml_string: str, *, validate: bool = True) -> mujoco.MjModel:
    """从 XML 字符串直接加载模型（通过临时文件）。

    Args:
        xml_string: 完整的 MuJoCo XML 内容
        validate: 是否在加载后进行基本验证

    Returns:
        MjModel 实例

    Raises:
        ValueError: XML 无效或验证失败
    """
    if not xml_string or not xml_string.strip():
        raise ValueError("XML 字符串为空")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(xml_string)
            tmp_path = tmp.name

        model = mujoco.MjModel.from_xml_path(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        if validate:
            _basic_validation(model)

        return model
    except Exception as e:
        raise ValueError(f"MuJoCo 模型加载失败: {e}") from e


def load_model_from_file(path: str | Path, *, validate: bool = True) -> mujoco.MjModel:
    """从文件路径加载模型。

    Args:
        path: XML 文件路径
        validate: 是否在加载后进行基本验证

    Returns:
        MjModel 实例

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 加载或验证失败
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"模型文件不存在: {path}")

    try:
        model = mujoco.MjModel.from_xml_path(str(path))
        if validate:
            _basic_validation(model)
        return model
    except Exception as e:
        raise ValueError(f"从 {path} 加载模型失败: {e}") from e


def load_model_from_string_with_cache(
    xml_string: str,
    cache_dir: Path,
    model_name: str,
    *,
    force_rebuild: bool = False,
) -> mujoco.MjModel:
    """从 XML 字符串加载模型，使用磁盘缓存避免重复写入。

    通过 XML 内容哈希判断是否需要重新生成文件。适用于参数扫描等需要
    多次加载相同配置的场景。

    Args:
        xml_string: MuJoCo XML 内容
        cache_dir: 缓存目录（会自动创建）
        model_name: 模型基础名称（不含扩展名）
        force_rebuild: 强制重建缓存文件

    Returns:
        MjModel 实例
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    xml_hash = hashlib.sha256(xml_string.encode("utf-8")).hexdigest()[:12]
    cached_path = cache_dir / f"{model_name}_{xml_hash}.xml"

    if force_rebuild or not cached_path.exists():
        cached_path.write_text(xml_string, encoding="utf-8")

    return load_model_from_file(cached_path, validate=True)


def get_model_info(model: mujoco.MjModel) -> ModelInfo:
    """提取模型结构信息。

    Args:
        model: MuJoCo 模型实例

    Returns:
        ModelInfo 数据类，包含关节、执行器、质量等信息
    """
    joint_names = [
        _get_name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)
    ]
    actuator_names = [
        _get_name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(model.nu)
    ]
    body_names = [
        _get_name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)
    ]
    geom_names = [
        _get_name(model, mujoco.mjtObj.mjOBJ_GEOM, i) for i in range(model.ngeom)
    ]

    # 计算总质量（world body 质量为 0）
    total_mass = float(np.sum(model.body_mass[1:]))

    return ModelInfo(
        n_joints=model.njnt,
        n_actuators=model.nu,
        n_sensors=model.nsensor,
        n_bodies=model.nbody,
        n_geoms=model.ngeom,
        timestep=float(model.opt.timestep),
        joint_names=joint_names,
        actuator_names=actuator_names,
        body_names=body_names,
        geom_names=geom_names,
        total_mass=total_mass,
        qpos_dim=model.nq,
        qvel_dim=model.nv,
    )


def validate_model(
    model: mujoco.MjModel,
    *,
    required_joints: list[str] | None = None,
    required_actuators: list[str] | None = None,
    required_bodies: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """验证模型是否包含所需组件。

    Args:
        model: MuJoCo 模型实例
        required_joints: 必需的关节名列表
        required_actuators: 必需的执行器名列表
        required_bodies: 必需的 body 名列表

    Returns:
        (是否通过, 错误信息列表) 元组
    """
    errors: list[str] = []

    if required_joints:
        for name in required_joints:
            if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) < 0:
                errors.append(f"缺少关节: {name}")

    if required_actuators:
        for name in required_actuators:
            if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name) < 0:
                errors.append(f"缺少执行器: {name}")

    if required_bodies:
        for name in required_bodies:
            if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name) < 0:
                errors.append(f"缺少 body: {name}")

    return (len(errors) == 0, errors)


def get_joint_index(model: mujoco.MjModel, joint_name: str) -> int:
    """获取关节索引，失败时抛出异常（而非返回 -1）。"""
    idx = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if idx < 0:
        raise ValueError(f"关节 '{joint_name}' 不存在")
    return idx


def get_actuator_index(model: mujoco.MjModel, actuator_name: str) -> int:
    """获取执行器索引，失败时抛出异常（而非返回 -1）。"""
    idx = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
    if idx < 0:
        raise ValueError(f"执行器 '{actuator_name}' 不存在")
    return idx


def get_body_index(model: mujoco.MjModel, body_name: str) -> int:
    """获取 body 索引，失败时抛出异常（而非返回 -1）。"""
    idx = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if idx < 0:
        raise ValueError(f"body '{body_name}' 不存在")
    return idx


def get_site_index(model: mujoco.MjModel, site_name: str) -> int:
    """获取 site 索引，失败时抛出异常（而非返回 -1）。"""
    idx = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    if idx < 0:
        raise ValueError(f"site '{site_name}' 不存在")
    return idx


# ============================================================================
# 内部辅助函数
# ============================================================================


def _get_name(model: mujoco.MjModel, obj_type: int, idx: int) -> str:
    """获取 MuJoCo 对象名称，无名对象返回 f"<unnamed_{idx}>"。"""
    try:
        # 使用 MuJoCo 内置的 id2name 函数
        name = mujoco.mj_id2name(model, obj_type, idx)
        if name:
            return name

        # 如果没有名称，返回默认值
        type_names = {
            mujoco.mjtObj.mjOBJ_JOINT: "joint",
            mujoco.mjtObj.mjOBJ_ACTUATOR: "actuator",
            mujoco.mjtObj.mjOBJ_BODY: "body",
            mujoco.mjtObj.mjOBJ_GEOM: "geom",
        }
        prefix = type_names.get(obj_type, "object")
        return f"<unnamed_{prefix}_{idx}>"
    except Exception:
        # 如果出现任何错误，返回默认名称
        return f"<object_{idx}>"


def _basic_validation(model: mujoco.MjModel) -> None:
    """基本的模型完整性检查，失败时抛出 ValueError。"""
    if model.nq <= 0:
        raise ValueError("模型无自由度（nq=0）")
    if model.opt.timestep <= 0:
        raise ValueError(f"无效的时间步长: {model.opt.timestep}")
    if model.nbody < 1:
        raise ValueError("模型至少需要 world body")


__all__ = [
    "ModelInfo",
    "load_model_from_xml",
    "load_model_from_file",
    "load_model_from_string_with_cache",
    "get_model_info",
    "validate_model",
    "get_joint_index",
    "get_actuator_index",
    "get_body_index",
    "get_site_index",
]
