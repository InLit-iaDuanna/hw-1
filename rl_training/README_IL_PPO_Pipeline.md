# Imitation Learning + PPO微调方案

完整的强化学习流水线，使用V13.7 FSM专家控制器进行行为克隆预训练，然后通过PPO微调。

## 流程概览

```
V13.7 FSM专家 → 收集轨迹 → 行为克隆(BC) → PPO微调 → 评估对比
   (4.6m)      (50 eps)    (50 epochs)   (5M steps)   (3模型)
```

## 四个阶段

### 阶段1: 收集V13.7专家轨迹
**脚本**: `collect_expert_trajectories.py`

在RL环境中运行V13.7 FSM控制器，收集成功episode的(观测, 动作)数据。

**参数**:
- `--episodes`: 收集的episode数量（默认50）
- `--max-steps`: 每个episode最大步数（默认600）

**输出**:
- `v137_expert_trajectories.pkl` - 专家轨迹数据（包含observations, actions）
- `v137_expert_trajectories.json` - 统计信息

**预期结果**:
- 50个成功episodes
- 约30,000个transitions
- 平均距离: ~4.5m
- 平均触地: ~10次

**运行**:
```bash
python collect_expert_trajectories.py --episodes 50 --max-steps 600
```

---

### 阶段2: 行为克隆预训练
**脚本**: `train_behavioral_cloning.py`

使用收集的专家轨迹训练MLP策略网络（监督学习）。

**网络架构**:
- 输入: 20维观测向量
- 隐藏层: [128, 128] (Tanh激活)
- 输出: 4维动作向量
- 损失函数: MSE

**参数**:
- `--epochs`: 训练轮数（默认50）
- `--batch-size`: 批大小（默认256）
- `--lr`: 学习率（默认1e-3）

**输出**:
- `bc_policy_weights.pth` - 最终模型权重
- `best_bc_policy_weights.pth` - 最佳模型权重（验证损失最低）
- `bc_training_curve.png` - 训练曲线
- `bc_training_history.json` - 训练历史

**预期结果**:
- 验证损失: < 0.1
- 训练时间: ~2-5分钟

**运行**:
```bash
python train_behavioral_cloning.py --epochs 50 --batch-size 256
```

---

### 阶段3: PPO Warm-Start训练
**脚本**: `train_ppo_with_bc_init.py`

将BC预训练权重加载到PPO policy，然后继续强化学习训练。

**关键特性**:
- BC权重初始化PPO的actor网络
- 8个并行环境（SubprocVecEnv）
- TensorBoard实时监控
- 定期保存检查点

**参数**:
- `--timesteps`: 总训练步数（默认5,000,000）
- `--envs`: 并行环境数（默认8）
- `--lr`: 学习率（默认3e-4）

**输出**:
- `./models_bc_warmstart/ppo_bc_warmstart_final.zip` - 最终模型
- `./logs_bc_warmstart/tensorboard/` - TensorBoard日志
- `./logs_bc_warmstart/checkpoints/` - 训练检查点

**预期结果**:
- 训练时间: 2-4小时（取决于硬件）
- 平均奖励: 持续提升
- 成功率: > 80%

**运行**:
```bash
python train_ppo_with_bc_init.py --timesteps 5000000 --envs 8

# 监控训练进度
tensorboard --logdir ./logs_bc_warmstart/tensorboard
```

---

### 阶段4: 对比评估
**脚本**: `evaluate_and_compare.py`

评估并对比3个模型的性能：
1. **纯BC模型** - 仅监督学习
2. **BC+PPO模型** - BC初始化 + RL微调
3. **原始PPO模型** - 从零开始训练（对照组）

**参数**:
- `--episodes`: 每个模型评估的episode数（默认20）

**输出**:
- `./evaluation_results/comparison_results.json` - 详细结果
- `./evaluation_results/comparison_plot.png` - 对比图表

**评估指标**:
- 平均奖励
- 平均前进距离
- 成功率
- 平均能量消耗

**运行**:
```bash
python evaluate_and_compare.py --episodes 20
```

---

## 快速开始

### 方式1: 完整自动化流水线
```bash
python run_automated_pipeline.py
```

此脚本会：
1. 自动执行所有4个阶段
2. 监控后台任务进度
3. 生成完整报告

### 方式2: 分步执行
```bash
# 阶段1
python collect_expert_trajectories.py

# 阶段2
python train_behavioral_cloning.py

# 阶段3
python train_ppo_with_bc_init.py

# 阶段4
python evaluate_and_compare.py
```

### 方式3: 自定义流水线
```bash
# 从阶段2开始（假设已有专家轨迹）
python run_full_pipeline.py --start-from 2

# 只执行阶段1和2
python run_full_pipeline.py --end-at 2

# 自定义参数
python run_full_pipeline.py --episodes 100 --bc-epochs 100 --ppo-timesteps 10000000
```

---

## 环境依赖

确保已安装以下依赖：
```bash
pip install stable-baselines3 gymnasium mujoco torch matplotlib
```

项目结构：
```
hw-1/
├── rl_training/
│   ├── collect_expert_trajectories.py
│   ├── train_behavioral_cloning.py
│   ├── train_ppo_with_bc_init.py
│   ├── evaluate_and_compare.py
│   ├── run_full_pipeline.py
│   ├── run_automated_pipeline.py
│   ├── environment.py
│   └── test_v137_identity.py
├── v13_7_friction_compensation/
│   └── simulate_v13_7.py
└── common/
    └── motor_dynamics.py
```

---

## 预期时间线

| 阶段 | 任务 | 预计时间 |
|-----|------|---------|
| 1 | 收集专家轨迹 | 10-20分钟 |
| 2 | 行为克隆训练 | 2-5分钟 |
| 3 | PPO训练 | 2-4小时 |
| 4 | 评估对比 | 5-10分钟 |
| **总计** | | **2.5-4.5小时** |

---

## 监控训练进度

### TensorBoard监控
```bash
tensorboard --logdir ./logs_bc_warmstart/tensorboard
```

关注指标：
- `rollout/ep_rew_mean` - 平均episode奖励
- `rollout/ep_len_mean` - 平均episode长度
- `train/policy_loss` - 策略损失
- `train/value_loss` - 价值损失

### 检查点管理
检查点保存在 `./logs_bc_warmstart/checkpoints/`，每50,000步保存一次。

加载检查点继续训练：
```python
from stable_baselines3 import PPO

model = PPO.load("./logs_bc_warmstart/checkpoints/ppo_bc_warmstart_100000_steps.zip")
model.learn(total_timesteps=1000000)  # 继续训练
```

---

## 故障排除

### 问题1: 专家轨迹收集失败率高
**原因**: 环境参数与V13.7不匹配

**解决**:
- 检查 `fall_height_threshold` 设置（应为0.2）
- 验证 `frame_skip=20`（对应50Hz控制频率）
- 确认FSM初始化正确

### 问题2: BC训练损失不收敛
**原因**: 学习率过高或数据质量差

**解决**:
- 降低学习率到 `1e-4`
- 增加训练epochs到100
- 检查专家轨迹数据质量

### 问题3: PPO训练不稳定
**原因**: BC初始化权重不佳或探索不足

**解决**:
- 增加 `ent_coef`（熵系数）到0.01
- 调整学习率到 `1e-4`
- 使用更多并行环境（16个）

### 问题4: 多进程环境启动失败（Windows）
**原因**: Windows需要 `spawn` 方式启动多进程

**解决**: 所有训练脚本已自动处理
```python
import multiprocessing
multiprocessing.set_start_method('spawn')
```

---

## 性能优化建议

### CPU优化
- 增加并行环境数: `--envs 16`
- 减少检查点频率: `checkpoint_freq=100000`

### GPU优化
- 确保PyTorch使用CUDA: `device="cuda"`
- 增加批大小: `--batch-size 128`

### 内存优化
- 减少专家轨迹数量: `--episodes 30`
- 减小replay buffer大小

---

## 预期结果对比

| 模型 | 平均距离 | 成功率 | 平均能量 |
|-----|---------|-------|---------|
| V13.7 FSM（基线） | 4.63m | 100% | N/A |
| 纯BC模型 | 3.5-4.0m | 60-70% | 中等 |
| BC+PPO模型 | 4.5-5.0m | 85-95% | 低 |
| 原始PPO模型 | 2.0-3.0m | 30-50% | 高 |

**结论**: BC warm-start显著提升PPO训练效率和最终性能。

---

## 参考文献

1. **行为克隆**: Pomerleau, D. A. (1989). "ALVINN: An autonomous land vehicle in a neural network."
2. **PPO算法**: Schulman, J. et al. (2017). "Proximal Policy Optimization Algorithms."
3. **V13.7控制器**: hw-1项目文档

---

## 联系与支持

如有问题，请检查：
1. 日志文件: `ppo_training.log`
2. TensorBoard: `./logs_bc_warmstart/tensorboard/`
3. 评估结果: `./evaluation_results/comparison_results.json`

---

**最后更新**: 2026-06-08
**版本**: 1.0
