"""
诊断脚本 - 检查环境和依赖
"""

import io
import sys
from pathlib import Path

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 80)
print("环境诊断")
print("=" * 80)
print()

# 1. Python版本
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")
print()

# 2. 检查关键依赖
dependencies = [
    ("NumPy", "numpy"),
    ("MuJoCo", "mujoco"),
    ("PyTorch", "torch"),
    ("Gymnasium", "gymnasium"),
    ("Stable-Baselines3", "stable_baselines3"),
    ("Matplotlib", "matplotlib"),
]

print("依赖检查:")
for name, module in dependencies:
    try:
        mod = __import__(module)
        version = getattr(mod, "__version__", "未知")
        print(f"  [OK] {name}: {version}")
    except ImportError as e:
        print(f"  [FAIL] {name}: 未安装 ({e})")

print()

# 3. 检查项目路径
RL_DIR = Path(__file__).resolve().parent
HW1_ROOT = RL_DIR.parent

print("项目路径:")
print(f"  RL训练目录: {RL_DIR}")
print(f"  hw-1根目录: {HW1_ROOT}")
print()

# 4. 检查关键文件
key_files = [
    HW1_ROOT / "v13_7_friction_compensation" / "simulate_v13_7.py",
    HW1_ROOT / "v13_6_event_driven_fsm" / "simulate_v13_6.py",
    HW1_ROOT / "common" / "motor_dynamics.py",
    RL_DIR / "environment.py",
]

print("关键文件检查:")
for file_path in key_files:
    if file_path.exists():
        print(f"  [OK] {file_path.relative_to(HW1_ROOT)}")
    else:
        print(f"  [FAIL] {file_path.relative_to(HW1_ROOT)} - 不存在")

print()

# 5. 尝试导入环境
print("尝试导入环境...")
try:
    sys.path.insert(0, str(RL_DIR))
    from environment import CompassGaitEnv

    print("  [OK] CompassGaitEnv导入成功")

    # 尝试创建环境
    env = CompassGaitEnv(reward_type="forward", max_steps=10)
    print("  [OK] 环境创建成功")

    obs, info = env.reset()
    print(f"  [OK] 环境重置成功 (观测维度: {obs.shape})")

    action = env.action_space.sample()
    print(f"  [OK] 动作空间采样成功 (动作维度: {action.shape})")

    env.close()
    print("  [OK] 所有基础功能正常")

except Exception as e:
    print(f"  [FAIL] 错误: {e}")
    import traceback

    traceback.print_exc()

print()
print("=" * 80)
print("诊断完成")
print("=" * 80)
