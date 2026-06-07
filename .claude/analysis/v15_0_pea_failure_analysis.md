# V15.0 PEA 方案失败复盘

## 失败原因（力学分析）

V15.0 采用 MuJoCo fixed tendon + stiffness 实现髋关节弹性，物理上等价于**并联弹簧（PEA）**，在关节处产生 τ_spring = -k·q_hip 的恢复力矩。

**核心矛盾**：V13.6.1 FSM 控制律设计假设为直驱关节（τ_commanded = τ_joint），但 PEA 引入未建模的并联刚度项：

```
τ_total = τ_FSM - k·q_hip
```

当 k>0 时，关节偏离中立位置会产生额外恢复力矩，与 FSM 的能量泵+PD 控制策略耦合，打破原有工作点。

**实测结果**（from `v15_vs_v14c.json`）：
- k=0：成功 3/36（8.3%），与 V14c 基线一致 ✓
- k=10：成功 0/36，全部 fall_down ✗
- k=30：成功 0/36，全部 fall_down ✗
- k=100：成功 0/36，30 格数值爆炸 ✗

**Verdict**: `v15_pea_breaks_v14c_fsm_at_all_nonzero_k`

## PEA vs SEA 对比表

| 特性 | PEA（并联弹性）| SEA（串联弹性）|
|------|----------------|----------------|
| 拓扑 | 电机与弹簧并联驱动关节 | 电机-弹簧-关节串联 |
| 力矩方程 | τ_joint = τ_motor - k·q | τ_link = -k·(q_motor - q_link) |
| 控制解耦 | 弹簧直接影响关节，控制器无法补偿 | 电机控制弹簧形变，间接控制力 |
| 对 FSM 兼容性 | **失败**：未建模刚度破坏控制律 | **成功**：电机可直接接收 FSM 指令 |
| 能量存储 | 关节偏转即储能（被动） | 电机-负载相对运动储能（主动可控）|
| 准被动行走适用性 | **不适用**（刚度与步态耦合） | **适用**（缓冲+透明力控）|

## 教训总结

1. **拓扑决定控制兼容性**：PEA 的并联刚度直接作用于关节，与基于位置/速度反馈的 FSM 控制律产生不可调和的耦合。准被动行走需要控制器"看到"关节真实状态，PEA 引入的恢复力矩相当于隐藏的干扰项。

2. **退化测试的价值**：V15.0 smoke test 在 k=0 时严格复现 V14c（3/36 成功格完全重合），证明 scaffold 实现正确，失败归因于 PEA 拓扑本身而非代码 bug。

3. **快速试错策略验证**：V15.0 没有独立目录名，在 `v15_hip_sea_scaffold` 中快速实现+测试+否定（<1 天），立即转向 V15.1 真正 SEA 拓扑（motor_rotor body + series hinge spring），后者成功复现 V14c 性能（k=5000 时 5/36 = 13.9%）。

4. **物理直觉需仿真验证**："弹性元件有助于步态"的直觉在并联配置下不成立。SEA 的成功在于其串联拓扑允许电机独立控制弹簧形变，而 PEA 将弹簧与关节刚性耦合，失去控制自由度。

## V15.1 SEA 的成功

转向串联拓扑后：
- k=5000/10000：成功 5/36 = 13.9%（精确复现 V14c）
- k=500 最佳格：forward=4.92 m（spring deflection 1.6°）

## 与 ROADMAP 关系

ROADMAP 记录："V15.0 PEA 失败；V15.1 SEA direct-drive 成功"

V15.0 的快速失败是项目健康迭代的体现：
1. 快速测试（<1 天）
2. 清晰判定（k=0 通过，k>0 全失败）
3. 立即转向（V15.1）
4. 最终成功（V15.1 复现 V14c）

## 参考文献

- Pratt, G. A., & Williamson, M. M. (1995). Series elastic actuators. IEEE/RSJ IROS.
- Robinson, D. W. (2000). Design and analysis of series elasticity in closed-loop actuator force control. MIT PhD thesis. — 解释 SEA vs PEA 控制差异

## 文件位置

- `v15_hip_sea_scaffold/README.md` — V15.0 PEA 原型文档
- `v15_hip_sea_scaffold/out/v15_vs_v14c.json` — 失败 verdict
- `v15_1_sea_direct/README.md` — 成功的 SEA 实现
