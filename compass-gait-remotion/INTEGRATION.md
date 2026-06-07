# Remotion 与 Python 仿真集成指南

本文档说明如何将 Python MuJoCo 仿真数据导入 Remotion 动画。

## 数据流向

```
Python 仿真 (MuJoCo)
    ↓ CSV 导出
v10_rolling_foot_walk_data.csv
    ↓ 数据转换
utils/export_for_remotion.py
    ↓ JSON 输出
public/data/v10_data.json
    ↓ Remotion 加载
DataDrivenExample.tsx
    ↓ 视频渲染
out/data_driven_example.mp4
```

## 方法 1：自动化批量导出（推荐）

### 步骤 1：运行批量导出脚本

```powershell
cd D:\Dunna\Documents\hw-1\compass-gait-remotion
..\.venv-mujoco\Scripts\python.exe utils\batch_export.py
```

这会自动导出：
- V10 数据 → `public/data/v10_data.json`
- V10 指标 → `public/data/v10_metrics.json`
- V13.6 数据 → `public/data/v13_6_data.json`
- V13.6 指标 → `public/data/v13_6_metrics.json`

### 步骤 2：启动 Remotion 预览

```bash
npm start
```

在浏览器中选择 `DataDrivenExample` 查看数据驱动的动画。

### 步骤 3：渲染视频

```bash
npx remotion render DataDrivenExample out/data_driven.mp4
```

## 方法 2：手动单独导出

### 导出 V10 数据

```powershell
..\.venv-mujoco\Scripts\python.exe utils\export_for_remotion.py `
  --input ../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv `
  --output public/data/v10_data.json `
  --sample-rate 2 `
  --summary ../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_summary.json `
  --summary-output public/data/v10_metrics.json
```

### 导出 V13.6 数据

```powershell
..\.venv-mujoco\Scripts\python.exe utils\export_for_remotion.py `
  --input ../v13_6_event_driven_fsm/out/v13_6_baseline_data.csv `
  --output public/data/v13_6_data.json `
  --sample-rate 2 `
  --summary ../v13_6_event_driven_fsm/out/v13_6_baseline_summary.json `
  --summary-output public/data/v13_6_metrics.json
```

### 参数说明

- `--input`: 输入 CSV 文件路径（Python 仿真输出）
- `--output`: 输出 JSON 文件路径（Remotion 读取）
- `--sample-rate`: 采样率，2 表示每 2 帧取 1 帧（减小文件大小）
- `--summary`: 可选，summary.json 路径
- `--summary-output`: 可选，导出的指标 JSON 路径

## 数据格式说明

### CSV 格式（Python 输出）

```csv
time,hip_x,hip_z,left_hip,left_knee,left_ankle,right_hip,right_knee,right_ankle,left_contact,right_contact,...
0.0,0.164,1.027,0.165,-0.0002,-0.002,-0.731,0.933,0.00004,1,0,...
0.006,0.165,1.030,0.168,-0.001,-0.035,-0.721,0.917,0.0009,1,0,...
...
```

### JSON 格式（Remotion 输入）

```json
[
  {
    "time": 0.0,
    "hip_x": 0.164,
    "hip_z": 1.027,
    "left_hip": 0.165,
    "left_knee": -0.0002,
    "left_ankle": -0.002,
    "right_hip": -0.731,
    "right_knee": 0.933,
    "right_ankle": 0.00004,
    "left_contact": true,
    "right_contact": false
  },
  ...
]
```

## 在 Remotion 中使用数据

### 基本加载模式

```tsx
import {staticFile, continueRender, delayRender} from 'remotion';
import {useEffect, useState} from 'react';

export const MyAnimation: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    fetch(staticFile('data/v10_data.json'))
      .then((res) => res.json())
      .then((jsonData) => {
        setData(jsonData);
        continueRender(handle);
      });
  }, [handle]);

  if (data.length === 0) return null;

  // 使用 data 渲染动画
  const frame = useCurrentFrame();
  const progress = frame / durationInFrames;
  const index = Math.floor(progress * (data.length - 1));
  const currentPoint = data[index];

  return (
    <AbsoluteFill>
      <div>Hip Angle: {currentPoint.left_hip.toFixed(2)}°</div>
    </AbsoluteFill>
  );
};
```

### 添加错误处理

```tsx
useEffect(() => {
  fetch(staticFile('data/v10_data.json'))
    .then((res) => res.json())
    .then((jsonData) => {
      setData(jsonData);
      continueRender(handle);
    })
    .catch((error) => {
      console.error('Failed to load data:', error);
      // 使用回退数据或模拟数据
      setData(generateMockData());
      continueRender(handle);
    });
}, [handle]);
```

## 性能优化

### 1. 数据采样

减小数据量，提高渲染速度：

```bash
# 采样率 2：每 2 帧取 1 帧
--sample-rate 2

# 采样率 5：每 5 帧取 1 帧（更小的文件）
--sample-rate 5
```

### 2. 数据缓存

使用 `useMemo` 缓存计算结果：

```tsx
const processedData = useMemo(() => {
  return data.map(point => ({
    ...point,
    hipAngle: calculateHipAngle(point),
  }));
}, [data]);
```

### 3. 条件渲染

只在需要时渲染复杂元素：

```tsx
{frame % 5 === 0 && <ExpensiveComponent />}
```

## 自动化工作流

### 方案 1：Python 脚本触发

在 Python 仿真脚本末尾添加：

```python
# simulate_v10.py 末尾
import subprocess

def export_to_remotion():
    subprocess.run([
        'python',
        '../compass-gait-remotion/utils/export_for_remotion.py',
        '--input', 'out/v10_rolling_foot_walk_data.csv',
        '--output', '../compass-gait-remotion/public/data/v10_data.json',
        '--sample-rate', '2'
    ])

if __name__ == '__main__':
    # ... 运行仿真
    export_to_remotion()
```

### 方案 2：PowerShell 流水线

```powershell
# pipeline.ps1
# 1. 运行仿真
..\.venv-mujoco\Scripts\python.exe ..\v10_rolling_foot_biomimetic_gait\simulate_rolling_foot_v10.py

# 2. 导出数据
..\.venv-mujoco\Scripts\python.exe utils\batch_export.py

# 3. 渲染动画
cd compass-gait-remotion
.\scripts\render_all.ps1

# 4. 复制到输出目录
Copy-Item out\*.mp4 ..\outputs\animations\
```

### 方案 3：监听文件变化

使用文件监听工具（如 `chokidar`）自动触发导出和渲染：

```bash
npm install -g chokidar-cli

chokidar "../v10_*/out/*.csv" -c "python utils/batch_export.py"
```

## 常见问题

### Q1: 数据文件找不到

**错误**: `Failed to fetch`

**解决**:
1. 确认文件在 `public/data/` 目录下
2. 文件路径使用相对于 `public/` 的路径：`staticFile('data/v10_data.json')`
3. 检查文件名大小写

### Q2: JSON 解析失败

**错误**: `Unexpected token`

**解决**:
1. 检查 JSON 格式是否正确：`python -m json.tool public/data/v10_data.json`
2. 确保 CSV 导出没有损坏的行
3. 重新运行导出脚本

### Q3: 数据太大导致渲染慢

**解决**:
1. 增加采样率：`--sample-rate 5`
2. 只导出必要的字段
3. 使用数据分片：将长时间仿真分成多个动画

### Q4: 动画与实际数据不同步

**解决**:
1. 检查 FPS 设置：确保 Remotion 的 fps 与数据采样率匹配
2. 使用时间插值而非索引插值：

```tsx
const currentData = useMemo(() => {
  const currentTime = (frame / fps);
  return data.find(d => Math.abs(d.time - currentTime) < 0.01);
}, [frame, data, fps]);
```

## 最佳实践

### 1. 版本控制

- ✅ 将导出脚本加入版本控制
- ✅ 文档化数据格式
- ❌ 不要提交大型 JSON 文件到 git（添加到 .gitignore）

### 2. 数据验证

在导出脚本中添加验证：

```python
def validate_data(df):
    assert not df['time'].isna().any(), "时间列包含 NaN"
    assert df['time'].is_monotonic_increasing, "时间不是递增的"
    assert len(df) > 0, "数据为空"
```

### 3. 命名规范

```
public/data/
  v10_data.json           # 时间序列数据
  v10_metrics.json        # 汇总指标
  v13_6_data.json
  v13_6_metrics.json
```

### 4. 文档注释

在导出的 JSON 中包含元数据：

```json
{
  "_meta": {
    "version": "v10",
    "exported_at": "2026-06-04T10:30:00Z",
    "sample_rate": 2,
    "original_frames": 1000
  },
  "data": [...]
}
```

## 下一步

- 查看 [DataDrivenExample.tsx](src/compositions/DataDrivenExample.tsx) 完整示例
- 阅读 [Remotion 官方文档](https://www.remotion.dev/docs) 了解更多功能
- 尝试创建自定义动画组件
