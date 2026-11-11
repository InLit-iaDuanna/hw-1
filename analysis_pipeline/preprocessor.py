"""
数据预处理模块
包括异常值检测、滤波、插值、时间对齐等
"""

from __future__ import annotations

import numpy as np
from data_loader import GaitData
from scipy import interpolate, signal
from scipy.stats import zscore


class DataPreprocessor:
    """数据预处理器"""

    def __init__(self, config: dict):
        """
        初始化预处理器

        Args:
            config: preprocessing 配置字典
        """
        self.config = config
        self.outlier_config = config.get("outlier_detection", {})
        self.filter_config = config.get("filtering", {})
        self.interp_config = config.get("interpolation", {})
        self.align_config = config.get("time_alignment", {})

    def detect_outliers_iqr(self, data: np.ndarray, factor: float = 1.5) -> np.ndarray:
        """
        使用 IQR 方法检测异常值

        Args:
            data: 输入数据
            factor: IQR 倍数因子

        Returns:
            布尔数组，True 表示异常值
        """
        q1 = np.nanpercentile(data, 25)
        q3 = np.nanpercentile(data, 75)
        iqr = q3 - q1
        lower = q1 - factor * iqr
        upper = q3 + factor * iqr
        return (data < lower) | (data > upper)

    def detect_outliers_zscore(
        self, data: np.ndarray, threshold: float = 3.0
    ) -> np.ndarray:
        """
        使用 Z-score 方法检测异常值

        Args:
            data: 输入数据
            threshold: Z-score 阈值

        Returns:
            布尔数组，True 表示异常值
        """
        z_scores = np.abs(zscore(data, nan_policy="omit"))
        return z_scores > threshold

    def detect_outliers(self, data: np.ndarray) -> np.ndarray:
        """
        检测异常值（根据配置选择方法）

        Args:
            data: 输入数据

        Returns:
            布尔数组，True 表示异常值
        """
        method = self.outlier_config.get("method", "iqr")

        if method == "iqr":
            factor = self.outlier_config.get("iqr_factor", 1.5)
            return self.detect_outliers_iqr(data, factor)
        elif method == "zscore":
            threshold = self.outlier_config.get("zscore_threshold", 3.0)
            return self.detect_outliers_zscore(data, threshold)
        else:
            return np.zeros(len(data), dtype=bool)

    def remove_outliers(self, data: np.ndarray) -> np.ndarray:
        """
        移除异常值（替换为 NaN）

        Args:
            data: 输入数据

        Returns:
            处理后的数据
        """
        outliers = self.detect_outliers(data)
        cleaned = data.copy()
        cleaned[outliers] = np.nan
        num_outliers = np.sum(outliers)
        if num_outliers > 0:
            print(
                f"    Removed {num_outliers} outliers ({100*num_outliers/len(data):.2f}%)"
            )
        return cleaned

    def filter_savgol(
        self, data: np.ndarray, window_length: int = 11, polyorder: int = 3
    ) -> np.ndarray:
        """
        Savitzky-Golay 滤波

        Args:
            data: 输入数据
            window_length: 窗口长度（必须为奇数）
            polyorder: 多项式阶数

        Returns:
            滤波后的数据
        """
        # 确保窗口长度为奇数
        if window_length % 2 == 0:
            window_length += 1

        # 确保窗口长度不超过数据长度
        window_length = min(window_length, len(data))
        if window_length < polyorder + 2:
            return data

        # 处理 NaN 值
        mask = ~np.isnan(data)
        if np.sum(mask) < window_length:
            return data

        filtered = data.copy()
        filtered[mask] = signal.savgol_filter(data[mask], window_length, polyorder)
        return filtered

    def filter_butterworth(
        self, data: np.ndarray, cutoff: float = 10.0, fs: float = 1000.0, order: int = 4
    ) -> np.ndarray:
        """
        Butterworth 低通滤波

        Args:
            data: 输入数据
            cutoff: 截止频率 (Hz)
            fs: 采样频率 (Hz)
            order: 滤波器阶数

        Returns:
            滤波后的数据
        """
        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist
        b, a = signal.butter(order, normal_cutoff, btype="low", analog=False)

        # 处理 NaN 值
        mask = ~np.isnan(data)
        if np.sum(mask) < 2 * order:
            return data

        filtered = data.copy()
        filtered[mask] = signal.filtfilt(b, a, data[mask])
        return filtered

    def filter_median(self, data: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        中值滤波

        Args:
            data: 输入数据
            kernel_size: 核大小

        Returns:
            滤波后的数据
        """
        if kernel_size % 2 == 0:
            kernel_size += 1

        return signal.medfilt(data, kernel_size=kernel_size)

    def filter_signal(self, data: np.ndarray, fs: float = 1000.0) -> np.ndarray:
        """
        信号滤波（根据配置选择方法）

        Args:
            data: 输入数据
            fs: 采样频率 (Hz)

        Returns:
            滤波后的数据
        """
        if not self.filter_config.get("enabled", True):
            return data

        method = self.filter_config.get("method", "savgol")

        if method == "savgol":
            window_length = self.filter_config.get("window_length", 11)
            polyorder = self.filter_config.get("polyorder", 3)
            return self.filter_savgol(data, window_length, polyorder)
        elif method == "butterworth":
            cutoff = self.filter_config.get("cutoff", 10.0)
            order = self.filter_config.get("order", 4)
            return self.filter_butterworth(data, cutoff, fs, order)
        elif method == "median":
            kernel_size = self.filter_config.get("kernel_size", 5)
            return self.filter_median(data, kernel_size)
        else:
            return data

    def interpolate_gaps(self, time: np.ndarray, data: np.ndarray) -> np.ndarray:
        """
        插值填补缺失值

        Args:
            time: 时间数组
            data: 数据数组

        Returns:
            插值后的数据
        """
        if not self.interp_config.get("fill_gaps", True):
            return data

        method = self.interp_config.get("method", "cubic")

        # 找到非 NaN 的数据点
        mask = ~np.isnan(data)
        if np.sum(mask) < 2:
            return data

        valid_time = time[mask]
        valid_data = data[mask]

        # 插值
        if method == "linear":
            f = interpolate.interp1d(
                valid_time, valid_data, kind="linear", fill_value="extrapolate"
            )
        elif method == "cubic":
            if len(valid_time) < 4:
                f = interpolate.interp1d(
                    valid_time, valid_data, kind="linear", fill_value="extrapolate"
                )
            else:
                f = interpolate.interp1d(
                    valid_time, valid_data, kind="cubic", fill_value="extrapolate"
                )
        elif method == "spline":
            if len(valid_time) < 4:
                f = interpolate.interp1d(
                    valid_time, valid_data, kind="linear", fill_value="extrapolate"
                )
            else:
                f = interpolate.UnivariateSpline(valid_time, valid_data, s=0)
        else:
            return data

        interpolated = data.copy()
        nan_mask = np.isnan(data)
        if np.any(nan_mask):
            interpolated[nan_mask] = f(time[nan_mask])
            print(f"    Filled {np.sum(nan_mask)} gaps with {method} interpolation")

        return interpolated

    def resample_uniform(
        self, time: np.ndarray, data: np.ndarray, target_rate: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        重采样到均匀时间网格

        Args:
            time: 时间数组
            data: 数据数组
            target_rate: 目标采样率 (Hz)

        Returns:
            (新时间数组, 新数据数组)
        """
        dt = 1.0 / target_rate
        new_time = np.arange(time[0], time[-1], dt)

        # 插值到新时间网格
        f = interpolate.interp1d(time, data, kind="cubic", fill_value="extrapolate")
        new_data = f(new_time)

        return new_time, new_data

    def preprocess_array(
        self, time: np.ndarray, data: np.ndarray, fs: float | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        完整预处理流程：异常值 -> 插值 -> 滤波

        Args:
            time: 时间数组
            data: 数据数组
            fs: 采样频率 (Hz)，如果为 None 则从 time 推断

        Returns:
            (处理后的时间, 处理后的数据)
        """
        # 推断采样频率
        if fs is None and len(time) > 1:
            fs = 1.0 / np.mean(np.diff(time))

        # 1. 移除异常值
        cleaned = self.remove_outliers(data)

        # 2. 插值填补缺失值
        interpolated = self.interpolate_gaps(time, cleaned)

        # 3. 滤波
        filtered = self.filter_signal(interpolated, fs or 1000.0)

        # 4. 时间对齐（可选）
        if self.align_config.get("enabled", False):
            target_rate = self.align_config.get("resample_frequency", 1000)
            new_time, filtered = self.resample_uniform(time, filtered, target_rate)
        else:
            new_time = time

        return new_time, filtered

    def preprocess_gait_data(self, gait_data: GaitData) -> GaitData:
        """
        预处理完整的 GaitData 对象

        Args:
            gait_data: 输入步态数据

        Returns:
            预处理后的步态数据
        """
        print(f"Preprocessing {gait_data.version}: {gait_data.label}")

        time = gait_data.time
        fs = gait_data.sampling_rate

        # 预处理位置
        print("  Processing positions...")
        _, hip_x = self.preprocess_array(time, gait_data.hip_x, fs)
        _, hip_z = self.preprocess_array(time, gait_data.hip_z, fs)

        # 预处理关节角度
        print("  Processing joint angles...")
        joint_angles = {}
        for key, data in gait_data.joint_angles.items():
            _, joint_angles[key] = self.preprocess_array(time, data, fs)

        # 预处理关节速度
        print("  Processing joint velocities...")
        joint_velocities = {}
        for key, data in gait_data.joint_velocities.items():
            _, joint_velocities[key] = self.preprocess_array(time, data, fs)

        # 预处理力矩
        print("  Processing torques...")
        torques = {}
        for key, data in gait_data.torques.items():
            _, torques[key] = self.preprocess_array(time, data, fs)

        # 预处理功率和能量
        power = None
        if gait_data.power is not None:
            print("  Processing power...")
            _, power = self.preprocess_array(time, gait_data.power, fs)

        energy = gait_data.energy  # 能量通常是累积量，不滤波

        # 时间对齐（如果启用，重采样所有信号）
        if self.align_config.get("enabled", False):
            target_rate = self.align_config.get("resample_frequency", 1000)
            old_time = time
            time, hip_x = self.resample_uniform(old_time, hip_x, target_rate)
            _, hip_z = self.resample_uniform(old_time, hip_z, target_rate)

            # 重采样关节角度
            for key in joint_angles:
                _, joint_angles[key] = self.resample_uniform(
                    old_time, joint_angles[key], target_rate
                )

            # 重采样关节速度
            for key in joint_velocities:
                _, joint_velocities[key] = self.resample_uniform(
                    old_time, joint_velocities[key], target_rate
                )

            # 重采样力矩
            for key in torques:
                _, torques[key] = self.resample_uniform(
                    old_time, torques[key], target_rate
                )

            # 重采样功率
            if power is not None:
                _, power = self.resample_uniform(old_time, power, target_rate)

            print(f"  Resampled to {target_rate}Hz, {len(time)} samples")

        # 接触状态：重采样后需要重新插值（离散信号）
        contact_states = {}
        for key, data in gait_data.contact_states.items():
            if self.align_config.get("enabled", False):
                # 最近邻插值（保持离散性）
                from scipy import interpolate

                f = interpolate.interp1d(
                    gait_data.time, data, kind="nearest", fill_value="extrapolate"
                )
                contact_states[key] = f(time)
            else:
                contact_states[key] = data

        # 创建新的 GaitData 对象
        return GaitData(
            version=gait_data.version,
            label=gait_data.label,
            time=time,
            hip_x=hip_x,
            hip_z=hip_z,
            joint_angles=joint_angles,
            joint_velocities=joint_velocities,
            contact_states=contact_states,
            torques=torques,
            power=power,
            energy=energy,
            metadata={
                **gait_data.metadata,
                "preprocessed": True,
                "preprocessing_config": self.config,
            },
        )


def main():
    """测试预处理"""
    from pathlib import Path

    import yaml
    from data_loader import DataLoader

    config_path = Path(__file__).parent / "pipeline_config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    loader = DataLoader(config_path)
    preprocessor = DataPreprocessor(config["preprocessing"])

    print("=" * 60)
    print("Preprocessor Test")
    print("=" * 60)

    # 加载一个版本进行测试
    gait_data = loader.load_version("v09_stable")

    # 预处理
    processed = preprocessor.preprocess_gait_data(gait_data)

    print("\nPreprocessing complete:")
    print(f"  Original samples: {gait_data.num_samples}")
    print(f"  Processed samples: {processed.num_samples}")
    print(f"  Original duration: {gait_data.duration:.2f}s")
    print(f"  Processed duration: {processed.duration:.2f}s")


if __name__ == "__main__":
    main()
