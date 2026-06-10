# 算法工具快速开始指南

> 5 分钟上手新创建的算法工具

---

## 🎯 你现在有什么？

3 个大型工具包，37 个 Python 文件，涵盖从仿真优化到硬件部署的完整流程。

---

## 🚀 立即开始（3 个命令）

### 1️⃣ 测试实物控制器（MuJoCo 仿真）

```powershell
cd D:\Dunna\Documents\hw-1\hardware_ready_controller\examples
..\..\.venv-mujoco\Scripts\python.exe run_in_mujoco.py
```

**期望输出**：
- MuJoCo 窗口显示步行动画
- 控制台输出：前进距离、步数、CoT
- 自动生成图表：力矩曲线、相位转换、能量分析

**这证明了**：基于 V13.7 的控制器在新框架中工作正常

---

### 2️⃣ 训练一个 RL 智能体

```powershell
cd D:\Dunna\Documents\hw-1\rl_training
..\\.venv-mujoco\Scripts\python.exe train_ppo.py
```

**期望输出**：
- 训练进度条
- TensorBoard 日志（打开浏览器访问 http://localhost:6006）
- 每 10k 步保存一个检查点
- 最终模型：`ppo_compass_final.zip`

**训练时间**：4-6 小时（CPU），1-2 小时（GPU）

**注意**：第一次运行可能需要安装依赖：
```powershell
pip install stable-baselines3 gymnasium tensorboard
```

---

### 3️⃣ 参数优化（改进 V13.7）

```powershell
cd D:\Dunna\Documents\hw-1\parameter_tuning
..\\.venv-mujoco\Scripts\python.exe bayesian_optimization.py
```

**期望输出**：
- 50-100 次仿真迭代
- 优化历史保存到 `optimization_history.json`
- 最佳参数保存到 `best_parameters.json`
- 可视化：优化曲线、参数重要性

**优化时间**：1-2 小时（100 次迭代）

---

## 📊 运行完整基准测试

**警告**：这会运行所有算法，需要 6-8 小时

```powershell
cd D:\Dunna\Documents\hw-1\algorithm_comparison
..\\.venv-mujoco\Scripts\python.exe run_all_benchmarks.py
```

**会测试**：
- V10 PD 控制
- V13.7 FSM 控制
- RL (PPO)
- RL (SAC)
- 轨迹优化
- 虚拟约束

**输出**：
```
算法对比表（algorithm_comparison_results.csv）:
┌─────────────────┬──────────┬──────┬───────┬──────────┐
│ 算法            │ 距离(m)  │ 步数 │ CoT   │ 训练时间 │
├─────────────────┼──────────┼──────┼───────┼──────────┤
│ V10 PD          │ 3.2±0.5  │ 7±1  │ 0.080 │ 0 (人工) │
│ V13.7 FSM       │ 4.63±0.2 │ 10±1 │ 0.066 │ 0 (人工) │
│ RL (PPO)        │ ?        │ ?    │ ?     │ 4 小时   │
│ RL (SAC)        │ ?        │ ?    │ ?     │ 2 小时   │
│ Traj Opt        │ ?        │ ?    │ ?     │ 10 分钟  │
│ Virtual Const   │ ?        │ ?    │ ?     │ 1 小时   │
└─────────────────┴──────────┴──────┴───────┴──────────┘
```

---

## 🔧 如果遇到错误

### 错误 1：找不到模块
```
ModuleNotFoundError: No module named 'stable_baselines3'
```

**解决**：
```powershell
.\.venv-mujoco\Scripts\pip.exe install stable-baselines3 gymnasium tensorboard
```

### 错误 2：找不到模型文件
```
FileNotFoundError: model.xml not found
```

**解决**：检查脚本中的模型路径，可能需要改为：
```python
model_path = "../../v13_7_friction_compensation/model.xml"
```

### 错误 3：CasADi 未安装（轨迹优化需要）
```
ModuleNotFoundError: No module named 'casadi'
```

**解决**：
```powershell
.\.venv-mujoco\Scripts\pip.exe install casadi
```

---

## 📖 详细文档

- **总览**：`ALGORITHM_TOOLKIT_OVERVIEW.md`
- **实物控制器**：`hardware_ready_controller/README.md`
- **RL 训练**：`rl_training/README.md`
- **使用指南**：`hardware_ready_controller/USAGE_GUIDE.md`

---

## 🎯 推荐流程

### 新手（1 天）
1. ✅ 运行 `run_in_mujoco.py`（验证基线）
2. ✅ 运行 `bayesian_optimization.py`（看看能否改进）
3. ✅ 查看生成的图表

### 进阶（1 周）
1. ✅ 训练 RL 模型（`train_ppo.py`）
2. ✅ 评估 RL vs V13.7（`evaluate.py`）
3. ✅ 尝试轨迹优化（`run_optimization.py`）

### 高级（1-2 周）
1. ✅ 运行完整基准测试（`run_all_benchmarks.py`）
2. ✅ 生成对比报告（`generate_comparison_report.py`）
3. ✅ 撰写论文/答辩材料

---

## ❓ 常见问题

**Q: RL 训练需要多久？**  
A: CPU 4-6 小时，GPU 1-2 小时。可以先用 `--total_timesteps 100000` 快速测试。

**Q: 能否在不同机器上训练？**  
A: 可以，训练完后把 `ppo_compass_final.zip` 复制回来即可。

**Q: 如何可视化 RL 学习过程？**  
A: 训练时会自动记录到 TensorBoard，运行 `tensorboard --logdir logs/` 查看。

**Q: 需要改代码吗？**  
A: 大部分情况不需要，但可能需要调整模型路径。

**Q: 如何使用自己的模型？**  
A: 修改 `model_path` 变量指向你的 XML 文件。

---

## 🎉 下一步

选择一个开始：
- 🔥 **最简单**：`run_in_mujoco.py`（1 分钟）
- 🚀 **最有趣**：`train_ppo.py`（让 AI 学习走路）
- 📊 **最全面**：`run_all_benchmarks.py`（完整对比）

**祝探索愉快！** 🎊
