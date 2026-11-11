"""
统一数据加载模块
从不同版本的 CSV 文件加载仿真数据，提供统一接口
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


@dataclass
class GaitData:
    """步态数据容器"""

    version: str
    label: str
    time: np.ndarray
    hip_x: np.ndarray
    hip_z: np.ndarray
    joint_angles: dict[str, np.ndarray]
    joint_velocities: dict[str, np.ndarray]
    contact_states: dict[str, np.ndarray]
    torques: dict[str, np.ndarray]
    power: np.ndarray | None
    energy: np.ndarray | None
    metadata: dict[str, Any]

    @property
    def duration(self) -> float:
        """仿真持续时间"""
        return float(self.time[-1] - self.time[0])

    @property
    def num_samples(self) -> int:
        """数据点数量"""
        return len(self.time)

    @property
    def sampling_rate(self) -> float:
        """采样率 (Hz)"""
        if len(self.time) < 2:
            return 0.0
        return 1.0 / np.mean(np.diff(self.time))

    def get_column(self, name: str) -> np.ndarray | None:
        """通用列访问"""
        if name == "time":
            return self.time
        elif name == "hip_x":
            return self.hip_x
        elif name == "hip_z":
            return self.hip_z
        elif name in self.joint_angles:
            return self.joint_angles[name]
        elif name in self.joint_velocities:
            return self.joint_velocities[name]
        elif name in self.contact_states:
            return self.contact_states[name]
        elif name in self.torques:
            return self.torques[name]
        elif name == "power":
            return self.power
        elif name == "energy":
            return self.energy
        return None


class DataLoader:
    """数据加载器"""

    def __init__(self, config_path: str | Path):
        """
        初始化数据加载器

        Args:
            config_path: pipeline_config.yaml 路径
        """
        self.config_path = Path(config_path)
        with open(self.config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.data_sources = self.config.get("data_sources", {})

    def load_csv(self, csv_path: str | Path) -> dict[str, np.ndarray]:
        """
        加载 CSV 文件为字典

        Args:
            csv_path: CSV 文件路径

        Returns:
            列名到数据数组的字典
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        data: dict[str, list[float]] = {}

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if headers is None:
                raise ValueError(f"No headers found in {csv_path}")

            # 初始化列
            for header in headers:
                data[header] = []

            # 读取数据
            for row in reader:
                for header in headers:
                    try:
                        value = float(row[header]) if row[header] else np.nan
                    except (ValueError, KeyError):
                        value = np.nan
                    data[header].append(value)

        # 转换为 numpy 数组
        return {key: np.array(values) for key, values in data.items()}

    def parse_gait_data(
        self, raw_data: dict[str, np.ndarray], version: str, label: str
    ) -> GaitData:
        """
        将原始 CSV 数据解析为 GaitData 对象

        Args:
            raw_data: 原始数据字典
            version: 版本标识
            label: 版本标签

        Returns:
            GaitData 对象
        """
        # 提取时间序列
        time = raw_data.get("time", np.array([]))

        # 提取位置
        hip_x = raw_data.get("hip_x", np.zeros_like(time))
        hip_z = raw_data.get("hip_z", np.zeros_like(time))

        # 提取关节角度
        joint_angles = {}
        for key in ["left_hip", "left_knee", "right_hip", "right_knee"]:
            if key in raw_data:
                joint_angles[key] = raw_data[key]

        # 提取关节速度
        joint_velocities = {}
        for key in ["left_hip_vel", "left_knee_vel", "right_hip_vel", "right_knee_vel"]:
            if key in raw_data:
                joint_velocities[key] = raw_data[key]

        # 提取接触状态
        contact_states = {}
        for key in ["left_contact", "right_contact"]:
            if key in raw_data:
                contact_states[key] = raw_data[key]

        # 提取力矩
        torques = {}
        for key in ["left_hip_tau", "left_knee_tau", "right_hip_tau", "right_knee_tau"]:
            if key in raw_data:
                torques[key] = raw_data[key]

        # 提取功率和能量
        power = raw_data.get("input_power")
        energy = raw_data.get("input_energy")

        # 元数据
        metadata = {
            "num_columns": len(raw_data),
            "column_names": list(raw_data.keys()),
        }

        return GaitData(
            version=version,
            label=label,
            time=time,
            hip_x=hip_x,
            hip_z=hip_z,
            joint_angles=joint_angles,
            joint_velocities=joint_velocities,
            contact_states=contact_states,
            torques=torques,
            power=power,
            energy=energy,
            metadata=metadata,
        )

    def load_version(self, version_key: str) -> GaitData:
        """
        加载指定版本的数据

        Args:
            version_key: 版本键（如 'v09_stable'）

        Returns:
            GaitData 对象
        """
        if version_key not in self.data_sources:
            raise KeyError(f"Version '{version_key}' not found in configuration")

        source = self.data_sources[version_key]
        csv_path = Path(source["path"])
        label = source["label"]
        version = source["version"]

        print(f"Loading {version_key}: {label} from {csv_path}")
        raw_data = self.load_csv(csv_path)
        gait_data = self.parse_gait_data(raw_data, version, label)

        print(
            f"  Loaded {gait_data.num_samples} samples, "
            f"duration={gait_data.duration:.2f}s, "
            f"rate={gait_data.sampling_rate:.1f}Hz"
        )

        return gait_data

    def load_all(self) -> dict[str, GaitData]:
        """
        加载所有配置的版本数据

        Returns:
            版本键到 GaitData 的字典
        """
        all_data = {}
        for version_key in self.data_sources.keys():
            try:
                all_data[version_key] = self.load_version(version_key)
            except Exception as e:
                print(f"Warning: Failed to load {version_key}: {e}")
                continue

        return all_data

    def load_batch(self, version_keys: list[str]) -> dict[str, GaitData]:
        """
        批量加载指定版本

        Args:
            version_keys: 版本键列表

        Returns:
            版本键到 GaitData 的字典
        """
        batch_data = {}
        for version_key in version_keys:
            try:
                batch_data[version_key] = self.load_version(version_key)
            except Exception as e:
                print(f"Warning: Failed to load {version_key}: {e}")
                continue

        return batch_data


def main():
    """测试数据加载"""
    config_path = Path(__file__).parent / "pipeline_config.yaml"
    loader = DataLoader(config_path)

    print("=" * 60)
    print("Data Loader Test")
    print("=" * 60)

    # 加载所有数据
    all_data = loader.load_all()

    print(f"\nLoaded {len(all_data)} versions:")
    for key, data in all_data.items():
        print(f"\n{key}: {data.label}")
        print(f"  Duration: {data.duration:.2f}s")
        print(f"  Samples: {data.num_samples}")
        print(f"  Sampling rate: {data.sampling_rate:.1f}Hz")
        print(f"  Joint angles: {list(data.joint_angles.keys())}")
        print(f"  Contacts: {list(data.contact_states.keys())}")
        print(f"  Torques: {list(data.torques.keys())}")
        print(f"  Power available: {data.power is not None}")
        print(f"  Energy available: {data.energy is not None}")


if __name__ == "__main__":
    main()
