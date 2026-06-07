# hw-1 视频高清化快速开始指南

**目标**: 将 V10, V13.7, V17 三个核心动画升级为 1920×1080 高清版本  
**预计时间**: 30-40 分钟  
**生成时间**: 2026/06/05

---

## 一键执行（推荐）

```powershell
# 1. 进入项目目录
cd D:\Dunna\Documents\hw-1

# 2. 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 3. 安装依赖（如果缺失）
pip install imageio-ffmpeg

# 4. 渲染核心展示动画（优先级 A）
python batch_render_hd.py --priority A

# 5. 验证生成的视频
python verify_hd_videos.py --all
```

---

## 分步执行（详细）

### 步骤 1: 环境准备

```powershell
# 进入项目目录
cd D:\Dunna\Documents\hw-1

# 激活虚拟环境
.\.venv-mujoco\Scripts\Activate.ps1

# 检查环境依赖
python batch_render_hd.py --list

# 预期输出：
# ============================================================
# hw-1 高清渲染任务清单
# ============================================================
# 
# 优先级 A: 4 个任务
# ------------------------------------------------------------
# 1. [V10] 足踝滚动仿生步态 - 最推荐展示
#    脚本: render_rolling_foot_gait_v10.py
#    标签: v10_rolling_foot_walk_HD
# 2. [V13.7] 摩擦补偿 ON - MX64AR电机
# 3. [V13.7] 摩擦补偿 ON - EC-i40电机
# 4. [V17] 状态估计 + 传感器噪声 - 硬件落地关键
```

### 步骤 2: 安装视频编码器（如果提示缺失）

```powershell
pip install imageio-ffmpeg
```

**验证安装**:
```powershell
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_version())"
# 预期输出: ffmpeg version 4.x.x 或更高
```

### 步骤 3: 归档 720p 原版（可选但推荐）

```powershell
python batch_render_hd.py --archive
```

**效果**: 将原始 720p 视频复制到 `D:\Dunna\Documents\hw-1\archive_720p\` 目录，避免覆盖丢失。

### 步骤 4: 渲染优先级 A（核心动画）

```powershell
python batch_render_hd.py --priority A
```

**预期输出**:
```
============================================================
准备渲染 4 个任务
============================================================

进度: [1/4]
============================================================
[A] V10: 足踝滚动仿生步态 - 最推荐展示
============================================================
脚本路径: D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\render_rolling_foot_gait_v10.py
输出标签: v10_rolling_foot_walk_HD
执行命令: python render_rolling_foot_gait_v10.py
------------------------------------------------------------
Rendered: D:\Dunna\Documents\hw-1\v10_rolling_foot_biomimetic_gait\out\v10_rolling_foot_walk_HD.mp4
✓ 渲染成功！耗时: 8.2 秒

进度: [2/4]
[A] V13.7: 摩擦补偿 ON - MX64AR电机
...
```

**生成文件**:
- `v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_HD.mp4`
- `v13_7_friction_compensation/out/v13_7_smoke_compensated_mx64ar_HD.mp4`
- `v13_7_friction_compensation/out/v13_7_smoke_compensated_ec_i40_HD.mp4`
- `v17_state_estimation/out/v17_mx64ar_noise1_HD.mp4`
- 对应的 `*_preview.png` 预览图

### 步骤 5: 验证视频质量

```powershell
python verify_hd_videos.py --all
```

**预期输出**:
```
============================================================
验证所有 HD 视频 (共 4 个)
============================================================

标签                                      分辨率           大小 (MB)    状态
--------------------------------------------------------------------------------
v10_rolling_foot_walk_HD                  1920×1080          2.05      ✓ 通过
v13_7_smoke_compensated_mx64ar_HD         1920×1080          2.38      ✓ 通过
v13_7_smoke_compensated_ec_i40_HD         1920×1080          2.41      ✓ 通过
v17_mx64ar_noise1_HD                      1920×1080          2.12      ✓ 通过

============================================================
验证完成: 4 通过, 0 失败
============================================================
```

### 步骤 6: 对比 720p vs 1080p（可选）

```powershell
python verify_hd_videos.py --compare
```

**预期输出**:
```
============================================================
对比 720p vs 1080p 版本
============================================================

版本                           分辨率           大小 (MB)    码率 (kbps)
--------------------------------------------------------------------------------

v10_rolling_foot_walk
  720p:  1280×720          0.69          1024.5
  1080p: 1920×1080         2.05          2850.3
  增长:  2.97x

v13_7_smoke_compensated_mx64ar
  720p:  1280×720          0.84          1156.7
  1080p: 1920×1080         2.38          3201.2
  增长:  2.83x
...
```

---

## 常见问题

### Q1: 提示 "imageio-ffmpeg 未安装"

**解决**:
```powershell
pip install imageio-ffmpeg
```

### Q2: 渲染速度很慢

**原因**: 1080p 像素数是 720p 的 2.25 倍，渲染时间正常增加 2-3 倍。

**优化**: 
- 关闭其他大型程序释放内存
- 单个 12 秒视频约需 6-10 分钟
- 可以后台运行，去做其他工作

### Q3: 验证提示 "ffprobe 不可用"

**影响**: 无法获取详细的分辨率、帧率、编码器信息，但不影响渲染本身。

**解决** (可选):
1. 下载 ffmpeg: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg\`
3. 添加到 PATH: `$env:Path += ";C:\ffmpeg\bin"`
4. 验证: `ffmpeg -version`

### Q4: 某个视频渲染失败

**排查步骤**:
1. 检查错误信息（查看 STDERR 输出）
2. 确认原始数据文件存在（`*_data.csv` 和 `*_summary.json`）
3. 手动运行单个脚本测试：
   ```powershell
   cd v10_rolling_foot_biomimetic_gait
   python render_rolling_foot_gait_v10.py
   ```

### Q5: 文件大小异常（<1 MB 或 >5 MB）

**原因**:
- < 1 MB: 可能仿真失败，时长过短
- \> 5 MB: 编码器质量设置过高

**解决**:
1. 检查原始仿真是否成功（查看 `*_summary.json` 中的 `success` 字段）
2. 调整 `quality=8` 参数（范围 0-51，值越小质量越高）

---

## 可选：渲染优先级 B（推荐升级）

完成优先级 A 后，可以继续渲染优先级 B:

```powershell
python batch_render_hd.py --priority B
```

**额外生成**:
- `v13_6_baseline_walk_HD.mp4` (事件驱动 FSM)
- `v14_baseline_HD.mp4` (被动摆臂)
- `v16_smoke_ideal_HD.mp4` (电机动力学理想情况)
- `v9_stable_walk_HD.mp4` (准被动稳定步态)

**预计时间**: 30-40 分钟

---

## 验证清单

渲染完成后，请确认：

- [ ] V10 HD 视频存在且播放正常
- [ ] V13.7 两个变体（mx64ar + ec_i40）都已生成
- [ ] V17 HD 视频存在且播放正常
- [ ] 所有视频分辨率为 1920×1080
- [ ] 文件大小在 1.5-3 MB 范围
- [ ] 标注文字清晰无模糊
- [ ] 预览图（*_preview.png）已生成

---

## 下一步

### 使用场景

1. **学术会议投影**:
   - 推荐: V10 (足踝滚动)
   - 使用 1080p HD 版本，投影清晰

2. **论文补充材料**:
   - 推荐: V10, V13.7, V17
   - 符合出版标准，H.264 编码兼容性好

3. **硬件落地展示**:
   - 推荐: V17 (传感器噪声 + 状态估计)
   - 展示实际硬件约束下的步态鲁棒性

### 文档更新

```powershell
# 更新项目记忆（CLAUDE.md 会自动同步）
# 记录 HD 版本生成时间和路径
```

---

## 技术参数总结

| 参数 | 720p 原版 | 1080p HD |
|------|-----------|----------|
| 分辨率 | 1280×720 | 1920×1080 |
| 帧率 | 60 fps | 60 fps |
| 编码器 | 默认 | H.264 (quality=8) |
| 标题字号 | 28-30pt | 42-45pt |
| 正文字号 | 20pt | 30pt |
| 文件大小 | 0.7-0.9 MB | 1.8-2.5 MB |
| 渲染时间 | 3-5 分钟 | 6-10 分钟 |

---

## 支持与反馈

**项目路径**: `D:\Dunna\Documents\hw-1`  
**脚本文件**:
- `batch_render_hd.py` - 批量渲染
- `verify_hd_videos.py` - 质量验证
- `render_hd_upgrade_template.py` - 脚本升级模板

**相关文档**:
- `VIDEO_OPTIMIZATION_SUMMARY.md` - 完整优化报告
- `video_quality_optimization_plan.txt` - 详细技术方案

**生成时间**: 2026/06/05  
**作者**: 段泽琪
