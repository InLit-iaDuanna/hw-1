"""测试脚本 - 验证 parameter_tuner 是否正常工作"""

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

print("=== Parameter Tuner 测试 ===\n")

# 测试 1: 导入版本适配器
try:
    from parameter_tuner.version_adapter import get_version_adapter

    print("✓ version_adapter 导入成功")
except Exception as e:
    print(f"✗ version_adapter 导入失败: {e}")
    sys.exit(1)

# 测试 2: 获取 V13.7 适配器
try:
    adapter = get_version_adapter("V13.7")
    print(f"✓ V13.7 适配器创建成功: {adapter.__class__.__name__}")
except Exception as e:
    print(f"✗ V13.7 适配器创建失败: {e}")
    sys.exit(1)

# 测试 3: 加载默认参数
try:
    params = adapter.get_default_params()
    print(f"✓ 默认参数加载成功: {type(params).__name__}")
except Exception as e:
    print(f"✗ 默认参数加载失败: {e}")
    sys.exit(1)

# 测试 4: 获取参数规格
try:
    specs = adapter.get_param_specs()
    print(f"✓ 参数规格获取成功: {len(specs)} 个类别")
    for category, items in specs.items():
        print(f"  - {category}: {len(items)} 个参数")
except Exception as e:
    print(f"✗ 参数规格获取失败: {e}")
    sys.exit(1)

# 测试 5: 参数摘要
try:
    summary = adapter.get_param_summary(params)
    print(f"✓ 参数摘要生成成功:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")
except Exception as e:
    print(f"✗ 参数摘要生成失败: {e}")
    sys.exit(1)

# 测试 6: YAML 导出
try:
    yaml_data = adapter.params_to_yaml(params)
    print(f"✓ YAML 导出成功: {len(yaml_data)} 字符")
except Exception as e:
    print(f"✗ YAML 导出失败: {e}")
    sys.exit(1)

# 测试 7: 仿真脚本路径
try:
    script_path = adapter.get_simulation_script()
    print(f"✓ 仿真脚本路径: {script_path}")
    print(f"  文件存在: {script_path.exists()}")
except Exception as e:
    print(f"✗ 仿真脚本路径获取失败: {e}")
    sys.exit(1)

print("\n=== 所有测试通过 ===")
print("\n可以运行 Streamlit 应用了:")
print("  .\\parameter_tuner\\run_tuner.ps1")
