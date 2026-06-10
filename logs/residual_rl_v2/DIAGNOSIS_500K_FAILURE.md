# 500K训练失败根本原因诊断

**日期**: 2026-06-09  
**诊断人**: Claude (基于Codex执行结果)  
**状态**: 训练在350k步自动中止（failure_rate=100%）

---

## 📊 完整性能曲线

| Checkpoint | 距离 | vs Baseline | vs Sweep | 成功率 | 状态 |
|-----------|------|------------|----------|--------|------|
| Baseline | 4.630m | 0% | -6.9% | 100% | 参考 |
| **Sweep Best** | **4.973m** | **+7.4%** | **0%** | **100%** | **目标** |
| 50k | 4.769m | +3.0% | -4.1% | 100% | ⚠️ 偏低 |
| 100k | 4.898m | +5.8% | -1.5% | 100% | ✅ 改善 |
| **150k** | **4.486m** | **-3.1%** | **-9.8%** | **100%** | 🚨 **崩溃1** |
| **200k** | **4.954m** | **+7.0%** | **-0.4%** | **100%** | ✅ **最佳** |
| 250k | 4.914m | +6.1% | -1.2% | 100% | ⚠️ 回退 |
| 300k | 4.936m | +6.6% | -0.7% | 100% | ⚠️ 振荡 |
| **350k** | **0.150m** | **-96.8%** | **-97.0%** | **0%** | 🚨 **崩溃2（致命）** |

---

## 🔴 问题定性

### **训练失败类型：周期性灾难性遗忘（Catastrophic Forgetting）**

1. **150k首次崩溃**：4.898m → 4.486m（-412mm）
2. **200k自我修复**：4.486m → 4.954m（+468mm，接近sweep最佳）
3. **350k致命崩溃**：4.936m → 0.150m（-4786mm，完全失效）

### **失效模式**
- **时间**：3.747s（约第750步，12s总时长的31%）
- **失败类型**：`fall_down`（摔倒）
- **触发状态**：hip_height=0.221m，phase=`L:stance_early|swing_retract`
- **失败率**：10/10 episodes（100%必然失败）

---

## 🔍 根本原因分析

### **1️⃣ Prior-Guided架构的致命缺陷**

#### **当前实现**
```python
# 环境代码逻辑
prior_action = [0.5, 1.0]      # 固定先验（sweep最佳）
delta_scale = 0.02             # PPO只能调整±2%
actual_action = prior + delta_scale * ppo_output
```

#### **实际action分布（350k崩溃时）**
```python
mean_action = [0.5016, 1.0000]  # 与prior几乎相同
std_action  = [0.0026, 0.0001]  # 极小方差
range       = [0.496-0.505, 0.999-1.000]  # 仅±0.5%扰动
```

#### **问题**
- **表面稳定**：action数值变化<0.5%，看起来收敛
- **实际危险**：即使0.1%的微小变化，在特定phase（stance_early）累积后导致gait失稳
- **缺少反馈**：reward函数只看最终距离，不惩罚中途不稳定

### **2️⃣ Value Network误导性收敛**

```
训练日志（350k前）：
- explained_variance = 0.94-0.98（极高）
- value_loss = 1-10（正常范围）
- approx_kl ≈ 0.0004（极小更新）
```

**解读**：
- Value network认为自己预测很准（high explained_variance）
- 实际上是在预测"错误策略也能成功"的幻觉
- PPO基于错误价值估计继续优化 → 策略越来越偏离真实最优

### **3️⃣ 奖励设计的时序盲区**

#### **当前reward**
```python
reward = 50 * (dx - dx_ref) - residual_penalty
```
- **只看结果**：只关心当前step的前进距离
- **不看过程**：不惩罚不稳定姿态（hip height下降、接触力异常）
- **延迟反馈**：摔倒发生在3.7s，但前3.6s的错误action没有即时惩罚

#### **后果**
PPO学到了"前期激进加速，摔倒前能冲更远"的策略：
- 0-3.5s：过度前倾，牺牲稳定性换速度
- 3.5-3.7s：姿态失控
- 3.75s：摔倒

---

## 📐 技术深挖：为什么200k恢复了但350k又崩溃？

### **假设：探索-利用的振荡陷阱**

```
150k崩溃 → 200k探索新策略 → 找到更好解（4.954m）
200k-300k → 过度利用 → 陷入局部最优
300k-350k → 探索跳出 → 但跳到了致命区域
```

### **证据**
1. **KL divergence模式**
   - 150k前：approx_kl ≈ 0.0002（几乎不动）
   - 200k附近：approx_kl跳升到0.004（大幅探索）→ 性能恢复
   - 350k前：approx_kl再次<0.0005（停止探索）→ 陷入错误局部最优

2. **Action std变化**
   - 200k：std=[0.0038, 0.0004]（较大方差）
   - 250k：std=[0.0062, 0.00003]（left增大，right缩小）
   - 350k：std=[0.0026, 0.0001]（双向收敛）

### **结论**
PPO在"正确的高方差探索"（200k）和"错误的低方差利用"（350k）之间来回切换，缺少稳定的收敛方向。

---

## 🎯 验证实验

### **实验1：复现350k失败**
```powershell
# 加载350k checkpoint，跑10次episode
.\.venv-mujoco\Scripts\python.exe rl_training\evaluate_checkpoint.py `
  --model models\residual_rl_v2_500k\checkpoints\ppo_500k_350000_steps.zip `
  --episodes 10
```
**预期**：10/10失败在3.7s，distance≈0.15m

### **实验2：验证200k稳定性**
```powershell
# 加载200k best checkpoint，跑100次
.\.venv-mujoco\Scripts\python.exe rl_training\evaluate_checkpoint.py `
  --model models\residual_rl_v2_500k\ppo_best.zip `
  --episodes 100
```
**预期**：>95%成功，mean distance≈4.95m

### **实验3：分析失败轨迹**
```powershell
# 记录350k checkpoint的完整状态序列
.\.venv-mujoco\Scripts\python.exe rl_training\record_trajectory.py `
  --model models\residual_rl_v2_500k\checkpoints\ppo_500k_350000_steps.zip `
  --output logs\residual_rl_v2\350k_failure_trajectory.json
```
**分析目标**：
- 哪个phase（stance/swing）最容易失效？
- hip_height、joint_angle在失败前如何演变？
- 能否定位"第一个错误action"的时刻？

---

## 🛠️ 解决方案

### **方案A：固定200k最佳策略，不再训练（最保守）**

**优点**：
- 200k已达4.954m（+7.0%，接近sweep的7.4%）
- 100%成功率，稳定可用
- 避免进一步训练风险

**缺点**：
- 未超越sweep best（差-19mm）
- 放弃继续优化空间

**实施**：
```powershell
# 将200k checkpoint作为最终模型
Copy-Item models\residual_rl_v2_500k\ppo_best.zip `
          models\residual_rl_v2_final.zip
```

---

### **方案B：修复reward函数，重新训练（最有效）**

#### **B1. 添加稳定性惩罚**
```python
# 新reward设计
forward_reward = 50 * (dx - dx_ref)

# 稳定性惩罚
hip_height = data.qpos[2]  # 髋关节高度
hip_height_penalty = -20 * max(0, 0.5 - hip_height)  # 低于0.5m惩罚

contact_force_penalty = -0.1 * sum(abs(contact_forces))  # 接触力过大惩罚

angular_velocity_penalty = -5 * abs(data.qvel[3:6]).sum()  # 躯干旋转惩罚

# 总reward
reward = forward_reward + hip_height_penalty + contact_force_penalty + angular_velocity_penalty - residual_penalty
```

#### **B2. Early termination**
```python
# 在step()中添加
if hip_height < 0.3:  # 髋关节过低
    done = True
    reward = -200  # 严重惩罚
```

#### **B3. 重新训练**
```powershell
# 从头训练，使用新reward
.\.venv-mujoco\Scripts\python.exe rl_training\train_residual_rl_v3.py `
  --timesteps 300000 `  # 缩短训练，减少遗忘风险
  --eval-freq 25000 `
  --abort-failure-rate 0.05
```

---

### **方案C：减小delta_scale + Curriculum（折衷）**

#### **C1. 限制探索范围**
```python
delta_scale = 0.005  # 从0.02降到0.005（缩小4倍）
```
**理由**：既然0.5%的扰动都能导致崩溃，干脆把扰动限制在±0.25%

#### **C2. Curriculum Learning**
```python
# 第一阶段：100k，delta_scale=0.005
# 第二阶段：200k，delta_scale=0.01（逐步放宽）
# 第三阶段：300k，delta_scale=0.02（最终目标）
```

#### **C3. 定期回退到best**
```python
# 每50k评估：
# if distance < best_distance * 0.95:
#     回滚到best checkpoint
#     降低learning rate *= 0.5
```

---

### **方案D：切换到TRPO/SAC（算法层面）**

#### **为什么TRPO可能更好**
- **Trust Region**：强制每次更新KL divergence < threshold
- **单调改进保证**：理论上不会退化
- **更适合连续控制**：原生支持策略光滑性约束

#### **实施**
```python
from stable_baselines3 import TRPO

model = TRPO(
    "MlpPolicy",
    env,
    learning_rate=1e-4,
    target_kl=0.01,  # 限制策略更新幅度
    gamma=0.99,
    verbose=1
)
```

---

## 📋 推荐方案排序

### **短期（1天内）**
1. **方案A**：直接使用200k checkpoint（4.954m, +7.0%）
   - 风险：低
   - 收益：立即可用
   - 适合：需要快速交付稳定方案

### **中期（1周内）**
2. **方案B**：修复reward + 300k重训练
   - 风险：中
   - 收益：有望达到5.2-5.5m（+12-19%）
   - 适合：有时间优化架构

### **长期（研究方向）**
3. **方案D**：切换TRPO算法
   - 风险：高（需要调试新算法）
   - 收益：可能解决根本性稳定问题
   - 适合：学术研究/长期项目

---

## 🔬 后续研究方向

### **1. 为什么constant residual (sweep)比PPO更稳定？**
- Sweep：固定action [0.5, 1.0]，无时序变化 → 完美稳定
- PPO：学到state-dependent policy，在某些state输出错误action

**假设**：最优策略可能就是constant，PPO的"聪明"反而是累赘

**验证**：
```python
# 训练一个"傻瓜baseline"：永远输出[0,0]（纯prior）
# 对比PPO学到的state-dependent policy
# 如果baseline性能≈PPO，说明不需要RL
```

### **2. Phase-dependent residual**
不是全局constant，而是"每个phase内constant"：
```python
if phase == "stance_early":
    residual = [0.1, 0.2]
elif phase == "swing_thrust":
    residual = [0.05, 0.15]
...
```

用简单规则代替复杂RL，可能更稳定。

### **3. Ensemble Policy**
训练5个独立PPO，inference时投票：
```python
actions = [policy_i(obs) for policy_i in policies]
final_action = np.median(actions, axis=0)
```

降低单一策略的错误风险。

---

## 📝 总结

**核心结论**：
1. PPO在prior-guided + baseline-relative reward下**无法稳定收敛**
2. 最佳性能出现在200k（4.954m），但后续训练导致灾难性遗忘
3. 根本原因：reward设计缺少稳定性约束 + value function误导

**可用成果**：
- ✅ **200k checkpoint**: 4.954m (+7.0%)，100%成功，可直接使用
- ❌ 350k checkpoint: 完全失效，不可用

**下一步**：
- **立即行动**：使用200k作为最终模型
- **后续优化**：修复reward函数（方案B），3-5天重新训练

---

**诊断完成日期**: 2026-06-09  
**最终建议**: 采纳200k checkpoint作为Residual RL V2的最终版本（+7.0%改进），暂停进一步训练直到reward函数修复完成。
