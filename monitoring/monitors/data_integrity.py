"""
数据完整性监控 - 检查关键文件和数据完整性
"""

import hashlib
import json
from pathlib import Path
from typing import Any


class DataIntegrityMonitor:
    """数据完整性监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def compute_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def check_critical_files(self, critical_files: list[str]) -> dict[str, Any]:
        """检查关键文件完整性"""
        results = {
            "status": "unknown",
            "files_checked": 0,
            "files_missing": [],
            "files_ok": [],
            "files_hash": {},
        }

        try:
            for file_path_str in critical_files:
                file_path = self.project_root / file_path_str
                results["files_checked"] += 1

                if not file_path.exists():
                    results["files_missing"].append(file_path_str)
                else:
                    results["files_ok"].append(file_path_str)
                    # 计算哈希值
                    file_hash = self.compute_file_hash(file_path)
                    results["files_hash"][file_path_str] = file_hash

            if results["files_missing"]:
                results["status"] = "fail"
            else:
                results["status"] = "pass"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def check_critical_directories(self, critical_dirs: list[str]) -> dict[str, Any]:
        """检查关键目录完整性"""
        results = {
            "status": "unknown",
            "directories_checked": 0,
            "directories_missing": [],
            "directories_ok": [],
            "directory_stats": {},
        }

        try:
            for dir_path_str in critical_dirs:
                dir_path = self.project_root / dir_path_str
                results["directories_checked"] += 1

                if not dir_path.exists():
                    results["directories_missing"].append(dir_path_str)
                elif not dir_path.is_dir():
                    results["directories_missing"].append(
                        f"{dir_path_str} (不是目录)"
                    )
                else:
                    results["directories_ok"].append(dir_path_str)

                    # 统计目录信息
                    py_files = list(dir_path.rglob("*.py"))
                    total_size = sum(f.stat().st_size for f in py_files if f.is_file())
                    results["directory_stats"][dir_path_str] = {
                        "python_files": len(py_files),
                        "total_size_bytes": total_size,
                    }

            if results["directories_missing"]:
                results["status"] = "fail"
            else:
                results["status"] = "pass"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def check_data_files(self) -> dict[str, Any]:
        """检查数据文件完整性"""
        results = {
            "status": "unknown",
            "xml_files": 0,
            "json_files": 0,
            "csv_files": 0,
            "corrupted_files": [],
        }

        try:
            # 检查 XML 文件（MuJoCo 模型）
            xml_files = list(self.project_root.rglob("*.xml"))
            results["xml_files"] = len(xml_files)

            # 验证 XML 文件是否可解析
            for xml_file in xml_files:
                try:
                    with open(xml_file, encoding="utf-8") as f:
                        content = f.read()
                        if not content.strip():
                            results["corrupted_files"].append(str(xml_file))
                        elif "<mujoco" not in content.lower():
                            # 可能不是 MuJoCo XML，但不算损坏
                            pass
                except Exception:
                    results["corrupted_files"].append(str(xml_file))

            # 检查 JSON 文件
            json_files = list(self.project_root.rglob("*.json"))
            # 排除监控和缓存目录
            json_files = [
                f
                for f in json_files
                if "monitoring" not in str(f)
                and ".venv" not in str(f)
                and "node_modules" not in str(f)
            ]
            results["json_files"] = len(json_files)

            # 验证 JSON 文件
            for json_file in json_files[:50]:  # 只检查前50个
                try:
                    with open(json_file, encoding="utf-8") as f:
                        json.load(f)
                except Exception:
                    results["corrupted_files"].append(str(json_file))

            # 检查 CSV 文件
            csv_files = list(self.project_root.rglob("*.csv"))
            results["csv_files"] = len(csv_files)

            if results["corrupted_files"]:
                results["status"] = "warning"
            else:
                results["status"] = "pass"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def compare_with_previous(
        self, current_hashes: dict[str, str], previous_hashes: dict[str, str]
    ) -> dict[str, Any]:
        """与之前的哈希值比较"""
        comparison = {"changed_files": [], "new_files": [], "deleted_files": []}

        # 查找变化的文件
        for file_path, current_hash in current_hashes.items():
            if file_path in previous_hashes:
                if current_hash != previous_hashes[file_path]:
                    comparison["changed_files"].append(file_path)
            else:
                comparison["new_files"].append(file_path)

        # 查找删除的文件
        for file_path in previous_hashes:
            if file_path not in current_hashes:
                comparison["deleted_files"].append(file_path)

        return comparison

    def run_monitoring(self, config: dict[str, Any]) -> dict[str, Any]:
        """运行数据完整性监控"""
        print("=" * 60)
        print("数据完整性监控")
        print("=" * 60)

        # 检查关键文件
        print("\n1. 关键文件检查:")
        critical_files = config.get("critical_files", [])
        files_results = self.check_critical_files(critical_files)
        print(f"   状态: {files_results['status']}")
        print(f"   检查: {files_results['files_checked']} 个文件")
        print(f"   正常: {len(files_results['files_ok'])} 个")
        if files_results["files_missing"]:
            print(f"   ⚠️  缺失: {len(files_results['files_missing'])} 个")
            for missing in files_results["files_missing"]:
                print(f"      - {missing}")

        # 检查关键目录
        print("\n2. 关键目录检查:")
        critical_dirs = config.get("critical_directories", [])
        dirs_results = self.check_critical_directories(critical_dirs)
        print(f"   状态: {dirs_results['status']}")
        print(f"   检查: {dirs_results['directories_checked']} 个目录")
        print(f"   正常: {len(dirs_results['directories_ok'])} 个")
        if dirs_results["directories_missing"]:
            print(f"   ⚠️  缺失: {len(dirs_results['directories_missing'])} 个")

        # 检查数据文件
        print("\n3. 数据文件检查:")
        data_results = self.check_data_files()
        print(f"   状态: {data_results['status']}")
        print(f"   XML 文件: {data_results['xml_files']}")
        print(f"   JSON 文件: {data_results['json_files']}")
        print(f"   CSV 文件: {data_results['csv_files']}")
        if data_results["corrupted_files"]:
            print(f"   ⚠️  损坏文件: {len(data_results['corrupted_files'])} 个")
            for corrupted in data_results["corrupted_files"][:5]:
                print(f"      - {corrupted}")

        # 与之前的版本比较
        print("\n4. 文件变化检查:")
        integrity_file = self.project_root / "monitoring" / "integrity_snapshot.json"
        if integrity_file.exists():
            try:
                with open(integrity_file, encoding="utf-8") as f:
                    previous_data = json.load(f)
                    previous_hashes = previous_data.get("files_hash", {})

                comparison = self.compare_with_previous(
                    files_results["files_hash"], previous_hashes
                )

                if comparison["changed_files"]:
                    print(f"   变更: {len(comparison['changed_files'])} 个文件")
                    for changed in comparison["changed_files"]:
                        print(f"      - {changed}")
                else:
                    print("   ✓ 关键文件无变化")
            except Exception as e:
                print(f"   无法比较: {e}")
        else:
            print("   首次运行，建立基线")

        print("=" * 60)

        # 保存当前快照
        snapshot = {
            "files_hash": files_results["files_hash"],
            "directory_stats": dirs_results["directory_stats"],
        }
        with open(integrity_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        # 组合所有结果
        all_results = {
            "critical_files": files_results,
            "critical_directories": dirs_results,
            "data_files": data_results,
        }

        return all_results


if __name__ == "__main__":
    from datetime import datetime

    import yaml

    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / "monitoring" / "config.yaml"

    # 加载配置
    config = {}
    if config_file.exists():
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

    monitor = DataIntegrityMonitor(project_root)
    results = monitor.run_monitoring(config)

    # 添加时间戳
    results["timestamp"] = datetime.now().isoformat()

    # 保存结果
    output_file = project_root / "monitoring" / "integrity_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n详细报告已保存至: {output_file}")
