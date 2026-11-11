"""
数据差异对比工具

对比两个版本的数据文件，生成差异报告。
支持 CSV 数值数据、JSON 参数文件、模型文件的差异分析。
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class DataDiffer:
    """数据差异对比器"""

    def __init__(self, project_root: str):
        """
        初始化差异对比器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)

    def compare_csv_files(
        self,
        file1: str,
        file2: str,
        key_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        对比两个 CSV 文件

        Args:
            file1: 第一个 CSV 文件路径
            file2: 第二个 CSV 文件路径
            key_columns: 用于对齐行的键列（如 ['sim_id']）

        Returns:
            差异报告字典
        """
        file1 = self._resolve_path(file1)
        file2 = self._resolve_path(file2)

        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)

        report = {
            "file1": str(file1.relative_to(self.project_root)),
            "file2": str(file2.relative_to(self.project_root)),
            "compared_at": datetime.now().isoformat(),
            "structure_diff": {},
            "statistical_diff": {},
            "row_diff": {},
        }

        # 结构差异
        report["structure_diff"]["rows"] = {
            "file1": len(df1),
            "file2": len(df2),
            "difference": len(df2) - len(df1),
        }

        cols1 = set(df1.columns)
        cols2 = set(df2.columns)

        report["structure_diff"]["columns"] = {
            "file1_only": list(cols1 - cols2),
            "file2_only": list(cols2 - cols1),
            "common": list(cols1 & cols2),
        }

        # 统计差异（数值列）
        common_cols = list(cols1 & cols2)
        numeric_cols = (
            df1[common_cols].select_dtypes(include=[np.number]).columns.tolist()
        )

        statistical_diffs = {}

        for col in numeric_cols:
            val1 = df1[col].dropna()
            val2 = df2[col].dropna()

            if len(val1) == 0 or len(val2) == 0:
                continue

            statistical_diffs[col] = {
                "mean_diff": float(val2.mean() - val1.mean()),
                "mean_pct_change": (
                    float((val2.mean() - val1.mean()) / val1.mean() * 100)
                    if val1.mean() != 0
                    else None
                ),
                "std_diff": float(val2.std() - val1.std()),
                "min_diff": float(val2.min() - val1.min()),
                "max_diff": float(val2.max() - val1.max()),
                "file1_stats": {
                    "mean": float(val1.mean()),
                    "std": float(val1.std()),
                    "min": float(val1.min()),
                    "max": float(val1.max()),
                },
                "file2_stats": {
                    "mean": float(val2.mean()),
                    "std": float(val2.std()),
                    "min": float(val2.min()),
                    "max": float(val2.max()),
                },
            }

        report["statistical_diff"] = statistical_diffs

        # 行级差异（如果提供了键列）
        if key_columns:
            try:
                merged = df1.merge(
                    df2,
                    on=key_columns,
                    how="outer",
                    suffixes=("_file1", "_file2"),
                    indicator=True,
                )

                report["row_diff"]["only_in_file1"] = int(
                    (merged["_merge"] == "left_only").sum()
                )
                report["row_diff"]["only_in_file2"] = int(
                    (merged["_merge"] == "right_only").sum()
                )
                report["row_diff"]["in_both"] = int((merged["_merge"] == "both").sum())

            except Exception as e:
                report["row_diff"]["error"] = str(e)

        return report

    def compare_json_files(
        self,
        file1: str,
        file2: str,
    ) -> Dict[str, Any]:
        """
        对比两个 JSON 文件

        Args:
            file1: 第一个 JSON 文件路径
            file2: 第二个 JSON 文件路径

        Returns:
            差异报告字典
        """
        file1 = self._resolve_path(file1)
        file2 = self._resolve_path(file2)

        with open(file1, "r", encoding="utf-8") as f:
            data1 = json.load(f)

        with open(file2, "r", encoding="utf-8") as f:
            data2 = json.load(f)

        report = {
            "file1": str(file1.relative_to(self.project_root)),
            "file2": str(file2.relative_to(self.project_root)),
            "compared_at": datetime.now().isoformat(),
            "changes": self._deep_diff(data1, data2),
        }

        return report

    def _deep_diff(
        self, obj1: Any, obj2: Any, path: str = "root"
    ) -> List[Dict[str, Any]]:
        """递归对比两个对象"""
        changes = []

        if type(obj1) != type(obj2):
            changes.append(
                {
                    "path": path,
                    "type": "type_change",
                    "old_type": type(obj1).__name__,
                    "new_type": type(obj2).__name__,
                    "old_value": obj1,
                    "new_value": obj2,
                }
            )
            return changes

        if isinstance(obj1, dict):
            all_keys = set(obj1.keys()) | set(obj2.keys())

            for key in all_keys:
                key_path = f"{path}.{key}"

                if key not in obj1:
                    changes.append(
                        {
                            "path": key_path,
                            "type": "added",
                            "new_value": obj2[key],
                        }
                    )
                elif key not in obj2:
                    changes.append(
                        {
                            "path": key_path,
                            "type": "removed",
                            "old_value": obj1[key],
                        }
                    )
                else:
                    changes.extend(self._deep_diff(obj1[key], obj2[key], key_path))

        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                changes.append(
                    {
                        "path": path,
                        "type": "length_change",
                        "old_length": len(obj1),
                        "new_length": len(obj2),
                    }
                )

            for i in range(min(len(obj1), len(obj2))):
                changes.extend(self._deep_diff(obj1[i], obj2[i], f"{path}[{i}]"))

        else:
            if obj1 != obj2:
                change = {
                    "path": path,
                    "type": "value_change",
                    "old_value": obj1,
                    "new_value": obj2,
                }

                # 计算数值变化百分比
                if isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
                    if obj1 != 0:
                        change["pct_change"] = (obj2 - obj1) / obj1 * 100

                changes.append(change)

        return changes

    def compare_text_files(
        self,
        file1: str,
        file2: str,
    ) -> Dict[str, Any]:
        """
        对比两个文本文件（如 XML 模型文件）

        Args:
            file1: 第一个文本文件路径
            file2: 第二个文本文件路径

        Returns:
            差异报告字典
        """
        file1 = self._resolve_path(file1)
        file2 = self._resolve_path(file2)

        with open(file1, "r", encoding="utf-8") as f:
            lines1 = f.readlines()

        with open(file2, "r", encoding="utf-8") as f:
            lines2 = f.readlines()

        import difflib

        diff = list(
            difflib.unified_diff(
                lines1,
                lines2,
                fromfile=str(file1.relative_to(self.project_root)),
                tofile=str(file2.relative_to(self.project_root)),
                lineterm="",
            )
        )

        report = {
            "file1": str(file1.relative_to(self.project_root)),
            "file2": str(file2.relative_to(self.project_root)),
            "compared_at": datetime.now().isoformat(),
            "lines_added": sum(1 for line in diff if line.startswith("+")),
            "lines_removed": sum(1 for line in diff if line.startswith("-")),
            "diff": diff[:100],  # 限制差异行数
        }

        return report

    def compare_assets(
        self,
        asset1: Dict[str, Any],
        asset2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        对比两个资产条目

        Args:
            asset1: 第一个资产字典
            asset2: 第二个资产字典

        Returns:
            差异报告字典
        """
        report = {
            "asset1_id": asset1["asset_id"],
            "asset2_id": asset2["asset_id"],
            "compared_at": datetime.now().isoformat(),
            "differences": {},
        }

        # 元数据差异
        for key in ["size_bytes", "modified_at", "version_tag", "experiment_id"]:
            if asset1.get(key) != asset2.get(key):
                report["differences"][key] = {
                    "asset1": asset1.get(key),
                    "asset2": asset2.get(key),
                }

        # 哈希差异
        if asset1["hash"] != asset2["hash"]:
            report["differences"]["hash"] = {
                "asset1": asset1["hash"][:16],
                "asset2": asset2["hash"][:16],
                "files_identical": False,
            }
        else:
            report["differences"]["hash"] = {
                "files_identical": True,
            }

        # 自动检测文件类型并进行内容对比
        file_path1 = self.project_root / asset1["file_path"]
        file_path2 = self.project_root / asset2["file_path"]

        if file_path1.exists() and file_path2.exists():
            ext = file_path1.suffix.lower()

            try:
                if ext == ".csv":
                    content_diff = self.compare_csv_files(
                        str(file_path1), str(file_path2)
                    )
                    report["content_diff"] = content_diff
                elif ext == ".json":
                    content_diff = self.compare_json_files(
                        str(file_path1), str(file_path2)
                    )
                    report["content_diff"] = content_diff
                elif ext in [".xml", ".txt"]:
                    content_diff = self.compare_text_files(
                        str(file_path1), str(file_path2)
                    )
                    report["content_diff"] = content_diff
            except Exception as e:
                report["content_diff_error"] = str(e)

        return report

    def generate_diff_report(
        self,
        report: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> str:
        """
        生成人类可读的差异报告

        Args:
            report: 差异报告字典
            output_path: 输出文件路径（可选）

        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append("DATA DIFFERENCE REPORT")
        lines.append("=" * 80)
        lines.append("")

        if "file1" in report and "file2" in report:
            lines.append(f"File 1: {report['file1']}")
            lines.append(f"File 2: {report['file2']}")
            lines.append(f"Compared at: {report['compared_at']}")
            lines.append("")

        # 结构差异
        if "structure_diff" in report:
            lines.append("STRUCTURE DIFFERENCES")
            lines.append("-" * 80)

            if "rows" in report["structure_diff"]:
                rows = report["structure_diff"]["rows"]
                lines.append(
                    f"  Rows: {rows['file1']} -> {rows['file2']} (diff: {rows['difference']:+d})"
                )

            if "columns" in report["structure_diff"]:
                cols = report["structure_diff"]["columns"]
                if cols["file1_only"]:
                    lines.append(
                        f"  Columns only in file1: {', '.join(cols['file1_only'])}"
                    )
                if cols["file2_only"]:
                    lines.append(
                        f"  Columns only in file2: {', '.join(cols['file2_only'])}"
                    )
                lines.append(f"  Common columns: {len(cols['common'])}")

            lines.append("")

        # 统计差异
        if "statistical_diff" in report and report["statistical_diff"]:
            lines.append("STATISTICAL DIFFERENCES")
            lines.append("-" * 80)

            for col, stats in report["statistical_diff"].items():
                lines.append(f"  {col}:")

                pct = stats.get("mean_pct_change")
                if pct is not None:
                    lines.append(
                        f"    Mean: {stats['file1_stats']['mean']:.4f} -> {stats['file2_stats']['mean']:.4f} ({pct:+.2f}%)"
                    )
                else:
                    lines.append(
                        f"    Mean: {stats['file1_stats']['mean']:.4f} -> {stats['file2_stats']['mean']:.4f}"
                    )

                lines.append(
                    f"    Std:  {stats['file1_stats']['std']:.4f} -> {stats['file2_stats']['std']:.4f}"
                )
                lines.append("")

        # JSON 变化
        if "changes" in report and report["changes"]:
            lines.append("JSON CHANGES")
            lines.append("-" * 80)

            for change in report["changes"][:20]:  # 限制显示数量
                if change["type"] == "value_change":
                    pct = change.get("pct_change")
                    if pct is not None:
                        lines.append(
                            f"  {change['path']}: {change['old_value']} -> {change['new_value']} ({pct:+.2f}%)"
                        )
                    else:
                        lines.append(
                            f"  {change['path']}: {change['old_value']} -> {change['new_value']}"
                        )
                elif change["type"] == "added":
                    lines.append(f"  {change['path']}: ADDED = {change['new_value']}")
                elif change["type"] == "removed":
                    lines.append(
                        f"  {change['path']}: REMOVED (was {change['old_value']})"
                    )

            if len(report["changes"]) > 20:
                lines.append(f"  ... and {len(report['changes']) - 20} more changes")

            lines.append("")

        # 行级差异
        if "row_diff" in report and report["row_diff"]:
            lines.append("ROW-LEVEL DIFFERENCES")
            lines.append("-" * 80)

            if "in_both" in report["row_diff"]:
                lines.append(f"  Rows in both files: {report['row_diff']['in_both']}")
            if "only_in_file1" in report["row_diff"]:
                lines.append(
                    f"  Rows only in file1: {report['row_diff']['only_in_file1']}"
                )
            if "only_in_file2" in report["row_diff"]:
                lines.append(
                    f"  Rows only in file2: {report['row_diff']['only_in_file2']}"
                )

            lines.append("")

        lines.append("=" * 80)

        text = "\n".join(lines)

        if output_path:
            output_path = self._resolve_path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"Report saved to: {output_path}")

        return text

    def _resolve_path(self, path: str) -> Path:
        """解析路径（支持相对和绝对路径）"""
        path = Path(path)

        if not path.is_absolute():
            path = self.project_root / path

        return path


if __name__ == "__main__":
    # 示例用法
    project_root = r"D:\Dunna\Documents\hw-1"
    differ = DataDiffer(project_root)

    # 对比 CSV 文件
    # report = differ.compare_csv_files(
    #     "out/trial_00.csv",
    #     "out/trial_01.csv",
    # )
    # print(differ.generate_diff_report(report))

    # 对比 JSON 文件
    # report = differ.compare_json_files(
    #     "out/example_summary.json",
    #     "out/integrated_example_summary.json",
    # )
    # print(differ.generate_diff_report(report))

    print(
        "DataDiffer initialized. Use compare_csv_files() or compare_json_files() to compare data."
    )
