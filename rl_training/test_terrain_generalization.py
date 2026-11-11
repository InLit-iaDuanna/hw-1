"""测试 100k RL 在不同地形下的泛化能力

测试场景：
1. 平地 (0度)
2. 上坡 (+5度, +10度, +15度)
3. 下坡 (-5度, -10度, -15度)
"""

import sys
from pathlib import Path
import numpy as np
from stable_baselines3 import PPO
import gymnasium as gym
from gymnasium import spaces
from dataclasses import replace

HW1_ROOT = Path(__file__).resolve().parent.parent
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from train_residual_rl_v2 import ResidualRLEnvV2
from simulate_v13_7 import V137Params, make_v137_fsm
from simulate_passive_arms_v14 import PassiveArmsParams
from common.motor_dynamics import PRESETS as MOTOR_PRESETS


class ResidualPriorWrapper(gym.ActionWrapper):
    """与训练时相同的 wrapper"""

    def __init__(self, env: gym.Env, prior_action: np.ndarray, delta_scale: float):
        super().__init__(env)
        self.prior_action = np.asarray(prior_action, dtype=np.float32)
        self.delta_scale = float(delta_scale)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        self.last_actual_action = self.prior_action.copy()

    def action(self, action: np.ndarray) -> np.ndarray:
        delta = np.asarray(action, dtype=np.float32)
        actual = np.clip(self.prior_action + self.delta_scale * delta, -1.0, 1.0)
        self.last_actual_action = actual.astype(np.float32)
        return self.last_actual_action


def create_env_with_slope(slope_deg: float):
    """创建指定坡度的环境"""
    base0 = PassiveArmsParams()
    overrides = dict(
        duration=12.0,
        slope_deg=slope_deg,  # 修改坡度
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        thigh_length=float(base0.thigh_length * 1.02),
        shank_length=float(base0.shank_length * 1.02),
        step_length=float(base0.step_length * 1.02),
        foot_radius=0.042,
    )
    base = replace(base0, **overrides)
    fsm = make_v137_fsm(base)
    motor = MOTOR_PRESETS["mx64ar"]

    params = V137Params(
        base=base,
        fsm=fsm,
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=True,
    )

    return ResidualRLEnvV2(
        params=params,
        residual_scale=0.2,
        inner_steps=5,
        max_steps=2400,
    )


def test_rl_on_slope(model, slope_deg: float, episodes: int = 5):
    """测试 RL 在指定坡度上的性能"""
    prior_action = np.array([0.5, 1.0], dtype=np.float32)
    delta_scale = 0.3

    distances = []
    successes = []

    for ep in range(episodes):
        base_env = create_env_with_slope(slope_deg)
        env = ResidualPriorWrapper(
            base_env, prior_action=prior_action, delta_scale=delta_scale
        )

        obs, info = env.reset(seed=ep)
        done = False
        step = 0

        while not done and step < 2400:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            step += 1

        final_distance = float(base_env.data.qpos[0])
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        env.close()

    return {
        "slope_deg": slope_deg,
        "mean_distance": float(np.mean(distances)),
        "std_distance": float(np.std(distances)),
        "success_rate": float(np.mean(successes)),
        "distances": distances,
    }


def test_constant_on_slope(slope_deg: float, episodes: int = 5):
    """测试 Constant 在指定坡度上的性能"""
    constant_action = np.array([0.5, 1.0], dtype=np.float32)

    distances = []
    successes = []

    for ep in range(episodes):
        env = create_env_with_slope(slope_deg)

        obs, info = env.reset(seed=ep)
        done = False
        step = 0

        while not done and step < 2400:
            obs, reward, terminated, truncated, info = env.step(constant_action)
            done = terminated or truncated
            step += 1

        final_distance = float(env.data.qpos[0])
        success = truncated and not terminated

        distances.append(final_distance)
        successes.append(success)

        env.close()

    return {
        "slope_deg": slope_deg,
        "mean_distance": float(np.mean(distances)),
        "std_distance": float(np.std(distances)),
        "success_rate": float(np.mean(successes)),
        "distances": distances,
    }


def main():
    print("=" * 80)
    print("100k RL 地形泛化能力测试")
    print("=" * 80)
    print()

    # 加载模型
    model_path = (
        HW1_ROOT / "models/residual_rl_v2_500k/checkpoints/ppo_500k_100000_steps.zip"
    )

    if not model_path.exists():
        print(f"错误：模型文件不存在")
        return

    print("正在加载 PPO 模型...")
    model = PPO.load(str(model_path))
    print("[OK] 模型加载成功")
    print()

    # 测试不同坡度
    slopes = [0, -5, -10, -15, 5, 10, 15]  # 平地、下坡、上坡

    print("=" * 80)
    print("开始测试（每个坡度 5 个 episodes）")
    print("=" * 80)
    print()

    rl_results = []
    constant_results = []

    for slope in slopes:
        print(
            f"\n测试坡度: {slope:+3d}度 {'(平地)' if slope == 0 else '(上坡)' if slope > 0 else '(下坡)'}"
        )
        print("-" * 80)

        # 测试 RL
        print("  [RL] 测试中...", end=" ")
        rl_result = test_rl_on_slope(model, slope, episodes=5)
        rl_results.append(rl_result)
        print(
            f"距离: {rl_result['mean_distance']:6.3f}m, 成功率: {rl_result['success_rate']*100:3.0f}%"
        )

        # 测试 Constant
        print("  [Constant] 测试中...", end=" ")
        const_result = test_constant_on_slope(slope, episodes=5)
        constant_results.append(const_result)
        print(
            f"距离: {const_result['mean_distance']:6.3f}m, 成功率: {const_result['success_rate']*100:3.0f}%"
        )

    # 汇总对比
    print("\n" * 2)
    print("=" * 80)
    print("泛化能力汇总")
    print("=" * 80)
    print()

    print(
        f"{'坡度':<10} {'RL 距离':<15} {'RL 成功率':<12} {'Constant 距离':<15} {'Constant 成功率':<12} {'RL vs Const':<15}"
    )
    print("-" * 90)

    for rl_r, const_r in zip(rl_results, constant_results):
        slope = rl_r["slope_deg"]
        rl_dist = rl_r["mean_distance"]
        rl_succ = rl_r["success_rate"]
        const_dist = const_r["mean_distance"]
        const_succ = const_r["success_rate"]

        diff = rl_dist - const_dist
        diff_str = f"{diff:+.3f}m" if abs(diff) < 10 else "FAIL"

        slope_str = f"{slope:+3d}度"
        print(
            f"{slope_str:<10} {rl_dist:6.3f}m       {rl_succ*100:3.0f}%         "
            f"{const_dist:6.3f}m       {const_succ*100:3.0f}%         {diff_str:<15}"
        )

    print()
    print("=" * 80)
    print("结论")
    print("=" * 80)
    print()

    # 分析泛化能力
    rl_success_count = sum(1 for r in rl_results if r["success_rate"] == 1.0)
    const_success_count = sum(1 for r in constant_results if r["success_rate"] == 1.0)

    print(f"1. 泛化能力:")
    print(f"   - RL 在 {rl_success_count}/{len(slopes)} 种地形上达到 100% 成功率")
    print(
        f"   - Constant 在 {const_success_count}/{len(slopes)} 种地形上达到 100% 成功率"
    )
    print()

    # 找出 RL 优于 Constant 的场景
    rl_better = [
        r
        for r, c in zip(rl_results, constant_results)
        if r["mean_distance"] > c["mean_distance"] and r["success_rate"] > 0
    ]

    if len(rl_better) > 0:
        print(f"2. RL 优势地形:")
        for r in rl_better:
            print(f"   - {r['slope_deg']:+3d}度: RL 更优")
    else:
        print(f"2. RL 优势地形: 无（Constant 在所有地形都不差于 RL）")

    print()

    # 训练建议
    if rl_success_count < len(slopes):
        print(f"3. 改进建议:")
        print(f"   - 当前 RL 只在平地（0度）训练")
        print(f"   - 建议：随机化坡度训练（Domain Randomization）")
        print(f"   - 训练时坡度范围: [-15度, +15度]")
        print(f"   - 这将提升 RL 的地形泛化能力")
    else:
        print(f"3. 泛化能力优秀！")
        print(f"   - 在平地训练的 RL 成功泛化到所有测试地形")

    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback

        traceback.print_exc()
