# 强化学习训练框架

> 让 AI 自己学习如何实现极限环步态

## 为什么用 RL？

### 动机
1. **突破人工设计局限**：V13.7 FSM 是人工设计的，RL 可能发现更好的策略
2. **自适应**：RL 可以学会适应不同地形、速度
3. **对比研究**：RL vs 手工控制，哪个更好？
4. **学术价值**：展示"数据驱动 vs 模型驱动"的对比

### 项目中的定位
```
V05 纯被动 → V10 PD → V13.7 FSM → ??? RL ???
  (理论)     (经典)     (工程)        (AI)
```

## 算法选择

### 推荐：Proximal Policy Optimization (PPO)
- **优势**：稳定、样本效率高、易调参
- **适用**：连续控制、物理仿真
- **库**：Stable-Baselines3

### 备选：Soft Actor-Critic (SAC)
- **优势**：更高样本效率、off-policy
- **适用**：需要快速训练时

### 备选：Twin Delayed DDPG (TD3)
- **优势**：确定性策略、简单
- **适用**：需要可解释性时

## 训练框架

### 环境设计

```python
import gymnasium as gym
import mujoco
import numpy as np

class CompassGaitEnv(gym.Env):
    """Compass Gait 强化学习环境"""
    
    def __init__(self, reward_type="forward", enable_early_termination=True):
        # 动作空间：4 个关节力矩
        self.action_space = gym.spaces.Box(
            low=-6.0, high=6.0, shape=(4,), dtype=np.float32
        )
        
        # 观测空间：关节角度、角速度、躯干位置、速度
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(14,), dtype=np.float32
        )
        
        # 加载 MuJoCo 模型（基于 V13.7）
        self.model = mujoco.MjModel.from_xml_path("v13_7_model.xml")
        self.data = mujoco.MjData(self.model)
        
        self.reward_type = reward_type
    
    def reset(self, seed=None, options=None):
        # 重置到初始状态（小随机扰动）
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.initial_qpos + np.random.randn(self.model.nq) * 0.01
        return self._get_obs(), {}
    
    def step(self, action):
        # 应用动作
        self.data.ctrl[:] = np.clip(action, -6.0, 6.0)
        
        # 步进仿真（每次 RL step = 10ms，10 个 MuJoCo steps）
        for _ in range(10):
            mujoco.mj_step(self.model, self.data)
        
        # 计算奖励
        reward = self._compute_reward()
        
        # 检查终止条件
        terminated = self._is_terminated()
        truncated = self.data.time > 12.0
        
        return self._get_obs(), reward, terminated, truncated, {}
    
    def _get_obs(self):
        """观测：关节状态 + 躯干状态"""
        return np.concatenate([
            self.data.qpos,      # 关节角度
            self.data.qvel,      # 关节角速度
            [self.data.time]     # 时间（可选）
        ])
    
    def _compute_reward(self):
        """奖励函数设计"""
        if self.reward_type == "forward":
            # 简单：奖励前进距离
            return self.data.qpos[0]  # hip_x
        
        elif self.reward_type == "energy_efficient":
            # 复杂：前进 - 能量消耗
            forward = self.data.qpos[0]
            energy = np.sum(np.abs(self.data.ctrl * self.data.qvel[-4:]))
            return forward - 0.01 * energy
        
        elif self.reward_type == "limit_cycle":
            # 高级：鼓励形成极限环（Poincaré 返回误差小）
            # TODO: 需要跟踪上一周期状态
            pass
    
    def _is_terminated(self):
        """终止条件：跌倒"""
        hip_height = self.data.qpos[1]
        return hip_height < 0.3  # 髋关节高度过低
```

### 训练脚本

```python
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

# 1. 创建并行环境（加速训练）
def make_env():
    return CompassGaitEnv(reward_type="forward")

env = SubprocVecEnv([make_env for _ in range(8)])  # 8 个并行环境

# 2. 创建 PPO 智能体
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    verbose=1,
    tensorboard_log="./logs/"
)

# 3. 设置回调（保存检查点）
checkpoint_callback = CheckpointCallback(
    save_freq=10000,
    save_path="./checkpoints/",
    name_prefix="ppo_compass"
)

# 4. 开始训练
model.learn(
    total_timesteps=2_000_000,
    callback=checkpoint_callback
)

# 5. 保存最终模型
model.save("ppo_compass_final")
```

### 评估脚本

```python
from stable_baselines3 import PPO
import numpy as np

# 加载训练好的模型
model = PPO.load("ppo_compass_final")

# 创建测试环境
env = CompassGaitEnv(reward_type="forward")

# 运行测试
obs, _ = env.reset()
for _ in range(12000):  # 12s @ 100Hz
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    
    if terminated or truncated:
        break

print(f"前进距离: {obs[0]:.2f} m")
print(f"步数: {env.step_count}")
```

## 奖励函数设计

关键：如何定义"好的步态"？

### 方案 1：简单前进（推荐起步）
```python
reward = forward_distance
```
- ✅ 简单、直观
- ✅ 训练快
- ❌ 可能学会"作弊"（不是步行，而是跳跃）

### 方案 2：能量效率
```python
reward = forward_distance - λ * energy_cost
# λ = 0.01 (权重)
```
- ✅ 更自然的步态
- ✅ 接近 CoT 优化
- ❌ 需要调 λ

### 方案 3：极限环奖励（高级）
```python
# 鼓励周期性步态
reward = forward + α * cycle_stability - β * energy
# cycle_stability = -||x_poincare - x_poincare_prev||
```
- ✅ 直接优化极限环
- ✅ 学术价值高
- ❌ 实现复杂

### 方案 4：模仿学习（基于 V13.7）
```python
# 先用 V13.7 生成示范轨迹
# 然后让 RL 学习：模仿 + 改进
reward = forward - ||action - action_v137|| * λ_imitate
```
- ✅ 利用已有知识
- ✅ 训练更快
- ✅ 可对比"学到的 vs 人工的"

## 对比实验设计

训练完成后，对比：

| 指标 | V10 PD | V13.7 FSM | RL (PPO) | RL (模仿) |
|------|--------|-----------|----------|-----------|
| 前进距离 (m) | ? | 4.63 | ? | ? |
| 步数 | ? | 10 | ? | ? |
| CoT | ? | 0.066 | ? | ? |
| 参数敏感性 | 高 | 中 | ? | ? |
| 地形适应性 | 差 | 中 | ? | ? |

## 可视化分析

训练完成后分析：

1. **学习曲线**：奖励 vs 训练步数（TensorBoard）
2. **策略可视化**：RL 学到的控制律是什么样的？
3. **相图对比**：RL 步态 vs V13.7 步态
4. **Poincaré 分析**：RL 是否也形成极限环？
5. **鲁棒性测试**：扰动、地形

## 预期结果

### 可能性 1：RL 更好
- 前进更远、能耗更低
- **结论**：数据驱动优于人工设计
- **论文价值**：展示 RL 在步态优化中的潜力

### 可能性 2：RL 相当
- 性能接近 V13.7
- **结论**：人工设计已接近最优
- **论文价值**：验证 V13.7 设计的合理性

### 可能性 3：RL 更差
- RL 难以稳定训练，或学到奇怪策略
- **结论**：被动/准被动步态需要结构化控制
- **论文价值**：讨论 RL 的局限性

**无论哪种结果，都有学术价值！**

## 实施计划

### Week 1：基础环境
- [ ] 实现 CompassGaitEnv
- [ ] 测试环境（手动控制）
- [ ] 验证奖励函数

### Week 2：训练 PPO
- [ ] 简单奖励（前进）训练
- [ ] 调参（学习率、批量大小等）
- [ ] 训练到收敛（~2M steps）

### Week 3：优化奖励
- [ ] 能量效率奖励
- [ ] 极限环奖励
- [ ] 模仿学习（基于 V13.7）

### Week 4：对比分析
- [ ] 运行所有对比实验
- [ ] 生成可视化
- [ ] 撰写分析报告

## 计算资源

- **CPU 训练**：~24 小时（8 核并行）
- **GPU 训练**：~4-6 小时（如果用 GPU 加速网络）
- **推荐**：先用 CPU 跑通，确认可行后再优化

## 相关工具

- **Stable-Baselines3**：RL 算法库
- **Gymnasium**：环境接口标准
- **TensorBoard**：训练监控
- **MuJoCo**：物理仿真

## 参考文献

- PPO 原文：Schulman et al. (2017)
- MuJoCo RL Benchmarks: Todorov et al. (2012)
- 步行 RL：Heess et al. (2017) "Emergence of Locomotion"
