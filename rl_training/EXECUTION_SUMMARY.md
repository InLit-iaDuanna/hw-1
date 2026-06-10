# Imitation Learning + PPO 微调方案 - 执行总结

## 方案概述

实现完整的**Imitation Learning (IL) → PPO微调**流水线，使用V13.7 FSM专家控制器作为教师模型。

### 核心思路
1. **专家示范**: V13.7 FSM控制器（已验证4.6m性能）
2. **监督学习**: 行为克隆(BC)学习专家策略
3. **强化学习**: PPO在BC基础上继续优化
4. **对比评估**: BC vs BC+PPO vs 纯PPO

---

## 已创建文件清单

### 主要脚本（在 `rl_training/` 目录）

1. **collect_expert_trajectories.py** - 阶段1：收集专家轨迹
2. **train_behavioral_cloning.py** - 阶段2：BC训练
3. **train_ppo_with_bc_init.py** - 阶段3：PPO warm-start训练
4. **evaluate_and_compare.py** - 阶段4：模型对比评估

### 辅助脚本

5. **run_full_pipeline.py** - 完整流水线执行器（交互式）
6. **run_automated_pipeline.py** - 自动化流水线（后台运行）
7. **monitor_progress.py** - 进度监控工具
8. **diagnose_environment.py** - 环境诊断工具

### 文档

9. **README_IL_PPO_Pipeline.md** - 详细文档（参数说明、故障排除）

---

## 快速执行指南

### 重要：使用正确的Python环境

项目使用虚拟环境：`.venv-mujoco`

**所有命令前缀**：
```powershell
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe"
```

### 方式1：分步执行（推荐）

```powershell
cd "D:\Dunna\Documents\hw-1\rl_training"

# 阶段1：收集专家轨迹（10-20分钟）
& "..\\.venv-mujoco\Scripts\python.exe" collect_expert_trajectories.py --episodes 50

# 阶段2：行为克隆训练（2-5分钟）
& "..\\.venv-mujoco\Scripts\python.exe" train_behavioral_cloning.py --epochs 50

# 阶段3：PPO训练（2-4小时，后台运行）
& "..\\.venv-mujoco\Scripts\python.exe" train_ppo_with_bc_init.py --timesteps 5000000

# 监控PPO训练进度
tensorboard --logdir ./logs_bc_warmstart/tensorboard

# 阶段4：评估对比（5-10分钟）
& "..\\.venv-mujoco\Scripts\python.exe" evaluate_and_compare.py --episodes 20
```

### 方式2：自动化流水线

```powershell
cd "D:\Dunna\Documents\hw-1\rl_training"
& "..\\.venv-mujoco\Scripts\python.exe" run_automated_pipeline.py
```

---

## 当前执行状态

### ✅ 环境诊断完成
- Python 3.10.11
- 所有依赖已安装：NumPy, MuJoCo, PyTorch, Gymnasium, SB3
- 环境功能验证通过

### 🔄 阶段1：收集专家轨迹（进行中）
- **后台任务ID**: bvz47zbuf
- **目标**: 50个成功episodes
- **预计时间**: 10-20分钟
- **输出文件**: `v137_expert_trajectories.pkl`

**监控进度**：
```powershell
& "..\\.venv-mujoco\Scripts\python.exe" monitor_progress.py
```

### ⏳ 阶段2-4：等待阶段1完成

---

## 预期输出文件

```
rl_training/
├── v137_expert_trajectories.pkl          # 专家轨迹数据
├── v137_expert_trajectories.json         # 统计信息
├── bc_policy_weights.pth                 # BC最终权重
├── best_bc_policy_weights.pth            # BC最佳权重
├── bc_training_curve.png                 # BC训练曲线
├── bc_training_history.json              # BC训练历史
├── models_bc_warmstart/
│   └── ppo_bc_warmstart_final.zip        # PPO最终模型
├── logs_bc_warmstart/
│   ├── tensorboard/                      # TensorBoard日志
│   └── checkpoints/                      # PPO检查点
└── evaluation_results/
    ├── comparison_results.json           # 评估结果
    └── comparison_plot.png               # 对比图表
```

---

## 关键参数说明

### 阶段1参数
- `--episodes 50`: 收集50个成功的episodes
- `--max-steps 600`: 每个episode最多600步（12秒@50Hz）

### 阶段2参数
- `--epochs 50`: BC训练50轮
- `--batch-size 256`: 批大小256
- `--lr 0.001`: 学习率1e-3

### 阶段3参数
- `--timesteps 5000000`: PPO训练500万步（约2-4小时）
- `--envs 8`: 8个并行环境
- `--lr 0.0003`: 学习率3e-4

### 阶段4参数
- `--episodes 20`: 每个模型评估20个episodes

---

## 预期结果

### 阶段1统计
- 成功episodes: 50
- 总transitions: ~30,000
- 平均距离: 4.5m
- 平均触地次数: 10

### 阶段2统计
- 最佳验证损失: < 0.1
- 训练时间: 2-5分钟

### 阶段3统计
- 训练时间: 2-4小时
- 平均奖励: 持续提升
- 成功率: > 80%

### 阶段4对比

| 模型 | 平均距离 | 成功率 | 平均能量 |
|-----|---------|-------|---------|
| V13.7 FSM（基线） | 4.63m | 100% | N/A |
| 纯BC模型 | 3.5-4.0m | 60-70% | 中等 |
| BC+PPO模型 | 4.5-5.0m | 85-95% | 低 |
| 原始PPO模型 | 2.0-3.0m | 30-50% | 高 |

**结论**: BC warm-start显著提升PPO训练效率和最终性能。

---

## 故障排除

### 问题1: Python找不到模块
**解决**: 确保使用虚拟环境Python
```powershell
& "D:\Dunna\Documents\hw-1\.venv-mujoco\Scripts\python.exe"
```

### 问题2: Unicode编码错误
**解决**: 已在所有脚本中添加UTF-8输出设置

### 问题3: 多进程启动失败
**解决**: 已在训练脚本中设置 `multiprocessing.set_start_method('spawn')`

### 问题4: 专家轨迹收集失败率高
**检查**:
- `fall_height_threshold=0.2`
- `frame_skip=20`
- FSM初始化参数

---

## 监控与调试

### 监控进度
```powershell
# 单次检查
& "..\\.venv-mujoco\Scripts\python.exe" monitor_progress.py

# 循环监控（每60秒）
& "..\\.venv-mujoco\Scripts\python.exe" monitor_progress.py --loop --interval 60
```

### TensorBoard监控
```bash
tensorboard --logdir ./logs_bc_warmstart/tensorboard
```

关键指标：
- `rollout/ep_rew_mean` - 平均奖励
- `rollout/ep_len_mean` - 平均步数
- `train/policy_loss` - 策略损失

### 检查文件生成
```powershell
Get-ChildItem | Where-Object { $_.Name -like "*expert*" -or $_.Name -like "*bc_*" }
```

---

## 下一步行动

1. ✅ **已完成**: 环境诊断
2. 🔄 **进行中**: 阶段1（专家轨迹收集）
3. ⏳ **待执行**: 阶段2-4

**等待阶段1完成后**，执行：
```powershell
# 阶段2
& "..\\.venv-mujoco\Scripts\python.exe" train_behavioral_cloning.py

# 阶段3
& "..\\.venv-mujoco\Scripts\python.exe" train_ppo_with_bc_init.py

# 阶段4
& "..\\.venv-mujoco\Scripts\python.exe" evaluate_and_compare.py
```

---

## 技术细节

### BC网络架构
```
Input (20) → Dense(128, Tanh) → Dense(128, Tanh) → Output(4)
```

### PPO超参数
- `learning_rate`: 3e-4
- `n_steps`: 2048
- `batch_size`: 64
- `gamma`: 0.99
- `gae_lambda`: 0.95
- `clip_range`: 0.2

### 环境配置
- `reward_type`: "energy_efficient"
- `fall_height_threshold`: 0.2
- `max_steps`: 1000
- `frame_skip`: 20 (50Hz控制)

---

**创建时间**: 2026-06-08 21:47
**项目**: hw-1步态训练辅助设备
**方案**: Imitation Learning + PPO微调
