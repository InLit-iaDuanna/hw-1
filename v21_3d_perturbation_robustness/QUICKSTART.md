# V21 可视化快速参考

## 快速生成视频

```powershell
cd D:\Dunna\Documents\hw-1\v21_3d_perturbation_robustness

# 扰动梯度动画（0.5°, 1.0°, 1.5°）- 论文主图
..\.venv-mujoco\Scripts\python.exe render_v21.py --mode cascade --output v21_perturbation_cascade.mp4

# 失败模式集合（0°, +1°, +2°, +3°）- 论文补充
..\.venv-mujoco\Scripts\python.exe render_v21.py --mode failures --output v21_failure_modes.mp4

# 单个配置（用于详细分析）
..\.venv-mujoco\Scripts\python.exe render_v21.py --mode single --init-roll 2.0 --output v21_roll_2deg.mp4
```

## 输出文件

| 文件 | 大小 | 用途 |
|------|------|------|
| `v21_perturbation_cascade.mp4` | ~300 KB | 扰动梯度展示 |
| `v21_failure_modes.mp4` | ~489 KB | 失败模式集合 |
| `v21_roll_Xdeg.mp4` | 变化 | 单配置详细分析 |

## 核心发现

**扰动容差**：< 1.0°（初始 roll 扰动）  
**失败时间**：< 2.5s（所有配置）  
**失败模式**：lateral_drift（100%）  
**非单调性**：+3° 反而比 +1° 表现更好

## 论文使用

**图 3.4a**：扰动梯度响应（使用 `v21_perturbation_cascade.mp4`）  
**图 3.4b**：失败模式演化（使用 `v21_failure_modes.mp4`）  

详见 `RENDER_GUIDE.md` 获取完整文档。
