"""优化建议工具 - 综合所有分析结果，生成可执行的优化任务清单。

整合热点分析、内存分析、并行化和复杂度分析的结果。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HW1_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Optimization:
    """优化建议。"""

    id: str
    title: str
    category: str  # hotspot/memory/parallel/complexity
    impact: str  # high/medium/low
    effort: str  # low/medium/high
    priority_score: float  # 0-100
    expected_speedup: str
    description: str
    implementation_steps: list[str]
    code_example: str
    affected_files: list[str]
    dependencies: list[str]  # 其他优化的 ID
    risks: list[str]


class OptimizationAdvisor:
    """优化建议顾问。"""

    def __init__(self):
        self.optimizations: list[Optimization] = []

    def add_optimization(self, opt: Optimization) -> None:
        """添加优化建议。"""
        self.optimizations.append(opt)

    def compute_priority_score(self, impact: str, effort: str, speedup: float) -> float:
        """计算优化优先级分数。

        Args:
            impact: 影响力 (high/medium/low)
            effort: 实现难度 (low/medium/high)
            speedup: 预期加速比

        Returns:
            优先级分数 (0-100)
        """
        impact_scores = {"high": 50, "medium": 30, "low": 10}
        effort_penalties = {"low": 1.0, "medium": 0.7, "high": 0.4}

        base_score = impact_scores.get(impact, 10)
        effort_mult = effort_penalties.get(effort, 0.5)
        speedup_bonus = min(30, speedup * 5)

        return base_score * effort_mult + speedup_bonus

    def create_standard_optimizations(self) -> None:
        """创建 hw-1 项目的标准优化建议。"""

        # 1. 并行化参数扫描
        self.add_optimization(
            Optimization(
                id="opt_001",
                title="并行化参数扫描",
                category="parallel",
                impact="high",
                effort="low",
                priority_score=self.compute_priority_score("high", "low", 6.0),
                expected_speedup="4-8x",
                description="使用 joblib 并行化 scan_*.py 中的参数扫描循环，充分利用多核 CPU",
                implementation_steps=[
                    "1. 安装 joblib: pip install joblib",
                    "2. 导入: from joblib import Parallel, delayed",
                    "3. 将单次仿真封装为独立函数",
                    "4. 使用 Parallel(n_jobs=-1) 替换 for 循环",
                    "5. 验证结果一致性",
                ],
                code_example="""from joblib import Parallel, delayed

def run_single(params):
    rows, summary = run_simulation(params, sample_hz=20.0)
    return summary

# 并行执行
results = Parallel(n_jobs=-1)(
    delayed(run_single)(p) for p in candidate_params
)""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/scan_rolling_foot_params_v10.py",
                    "v13_7_friction_compensation/scan_v13_7_tauC_verify.py",
                    "v17_state_estimation/scan_v17_noise.py",
                ],
                dependencies=[],
                risks=["并行执行可能导致内存峰值增加", "需要确保函数无副作用"],
            )
        )

        # 2. 降低数据采样率
        self.add_optimization(
            Optimization(
                id="opt_002",
                title="降低数据采样率",
                category="hotspot",
                impact="medium",
                effort="low",
                priority_score=self.compute_priority_score("medium", "low", 1.3),
                expected_speedup="1.2-1.5x",
                description="减少 sample_hz 以降低数据记录开销，同时保持足够的分析精度",
                implementation_steps=[
                    "1. 分析当前 sample_hz 使用情况",
                    "2. 确定最小可接受采样率（基于 Nyquist 定理）",
                    "3. 更新默认 sample_hz 参数",
                    "4. 验证分析结果质量",
                ],
                code_example="""# V10: 120 Hz → 60 Hz (足够用于轨迹分析)
run_simulation(params, sample_hz=60.0)

# V17: 160 Hz → 80 Hz (仍满足 Nyquist 要求)
run_simulation_v17(params, sample_hz=80.0)""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                    "v17_state_estimation/simulate_v17.py",
                ],
                dependencies=[],
                risks=["可能丢失高频细节", "需要验证分析结果不受影响"],
            )
        )

        # 3. 数组预分配
        self.add_optimization(
            Optimization(
                id="opt_003",
                title="使用 numpy 数组预分配",
                category="memory",
                impact="medium",
                effort="medium",
                priority_score=self.compute_priority_score("medium", "medium", 1.2),
                expected_speedup="1.1-1.3x",
                description="预分配 numpy 数组存储仿真数据，减少内存分配开销和内存占用",
                implementation_steps=[
                    "1. 计算所需数组大小: n_samples = int(duration / timestep / sample_stride)",
                    "2. 预分配数组: data_array = np.zeros((n_samples, n_fields))",
                    "3. 在循环中直接写入数组",
                    "4. 结束后转换为 list[dict]",
                    "5. 对比性能和内存使用",
                ],
                code_example="""import numpy as np

n_steps = int(params.duration / params.timestep)
n_samples = n_steps // sample_stride
n_fields = len(QPOS_KEYS) + len(QVEL_KEYS) + 20  # 预估字段数

# 预分配
data_array = np.zeros((n_samples, n_fields), dtype=np.float64)

for step in range(n_steps):
    # ... 仿真步进 ...
    if step % sample_stride == 0:
        idx = step // sample_stride
        data_array[idx, :] = [...] # 直接写入

# 转换为 list[dict]
rows = [dict(zip(keys, data_array[i])) for i in range(n_samples)]""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                    "v13_7_friction_compensation/simulate_v13_7.py",
                    "v17_state_estimation/simulate_v17.py",
                ],
                dependencies=[],
                risks=["增加代码复杂度", "需要预先知道字段数量"],
            )
        )

        # 4. 缓存三角函数
        self.add_optimization(
            Optimization(
                id="opt_004",
                title="缓存重复的三角函数计算",
                category="hotspot",
                impact="low",
                effort="low",
                priority_score=self.compute_priority_score("low", "low", 1.1),
                expected_speedup="1.05-1.15x",
                description="在循环外预计算不变的三角函数值，避免重复计算",
                implementation_steps=[
                    "1. 识别循环中的重复三角函数调用",
                    "2. 检查参数是否在循环中不变",
                    "3. 将计算移到循环外",
                    "4. 使用缓存的值",
                ],
                code_example="""# Before
for step in range(n_steps):
    offset = params.gamma  # 不变
    target = offset + math.radians(angle_deg)  # angle_deg 不变

# After
gamma = params.gamma
angle_rad = math.radians(angle_deg)
for step in range(n_steps):
    target = gamma + angle_rad""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                ],
                dependencies=[],
                risks=["收益较小"],
            )
        )

        # 5. 使用 numba JIT
        self.add_optimization(
            Optimization(
                id="opt_005",
                title="使用 numba JIT 加速控制器",
                category="hotspot",
                impact="medium",
                effort="medium",
                priority_score=self.compute_priority_score("medium", "medium", 1.3),
                expected_speedup="1.2-1.5x",
                description="使用 numba 对热点函数进行 JIT 编译，加速数值计算",
                implementation_steps=[
                    "1. 安装 numba: pip install numba",
                    "2. 识别纯数值计算的热点函数",
                    "3. 添加 @jit(nopython=True) 装饰器",
                    "4. 调整函数以兼容 numba",
                    "5. 验证结果一致性和性能提升",
                ],
                code_example="""from numba import jit

@jit(nopython=True)
def limited_pd(q, qd, target, kp, kd, limit):
    tau = kp * (target - q) - kd * qd
    if tau > limit:
        return limit
    elif tau < -limit:
        return -limit
    return tau

@jit(nopython=True)
def smoothstep(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                    "v17_state_estimation/simulate_v17.py",
                ],
                dependencies=[],
                risks=["numba 不支持所有 Python 特性", "首次编译有开销"],
            )
        )

        # 6. 优化接触检测
        self.add_optimization(
            Optimization(
                id="opt_006",
                title="优化接触检测频率",
                category="hotspot",
                impact="low",
                effort="low",
                priority_score=self.compute_priority_score("low", "low", 1.05),
                expected_speedup="1.05-1.1x",
                description="减少不必要的接触检测调用，只在需要时检测",
                implementation_steps=[
                    "1. 分析 foot_contact_detail() 调用频率",
                    "2. 识别可以复用结果的场景",
                    "3. 缓存接触状态",
                    "4. 只在状态可能改变时重新检测",
                ],
                code_example="""# 在 contact_flags 中已经检测过，不需要在 make_row 中再次检测
left_contact, right_contact = contact_flags(model, data)

# make_row 中复用结果
row = make_row(..., left_contact, right_contact, cached_detail)""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                ],
                dependencies=[],
                risks=["收益很小"],
            )
        )

        # 7. 早停策略
        self.add_optimization(
            Optimization(
                id="opt_007",
                title="参数扫描早停策略",
                category="complexity",
                impact="medium",
                effort="low",
                priority_score=self.compute_priority_score("medium", "low", 1.5),
                expected_speedup="1.3-2.0x",
                description="在参数扫描中尽早终止失败的仿真，避免浪费时间",
                implementation_steps=[
                    "1. 在 run_simulation 中添加 early_stop_time 参数",
                    "2. 如果在早期检测到失败，立即返回",
                    "3. 在参数扫描中使用较短的 early_stop_time",
                    "4. 对候选参数进行快速筛选",
                ],
                code_example="""def run_simulation(params, early_stop_time=None):
    for step in range(int(params.duration / params.timestep)):
        t = step * params.timestep

        # 早停检查
        if early_stop_time and t >= early_stop_time:
            failure = classify_failure(...)
            if failure:
                return [], {"failure": failure, "early_stopped": True}

        # ... 继续仿真 ...""",
                affected_files=[
                    "v10_rolling_foot_biomimetic_gait/simulate_rolling_foot_gait_v10.py",
                    "v10_rolling_foot_biomimetic_gait/scan_rolling_foot_params_v10.py",
                ],
                dependencies=[],
                risks=["可能过早淘汰潜在的好参数"],
            )
        )

    def generate_report(self) -> dict[str, Any]:
        """生成优化建议报告。"""
        # 按优先级排序
        sorted_opts = sorted(
            self.optimizations, key=lambda x: x.priority_score, reverse=True
        )

        report = {
            "total_optimizations": len(self.optimizations),
            "by_category": self._group_by_category(),
            "by_impact": self._group_by_impact(),
            "by_effort": self._group_by_effort(),
            "recommended_order": [opt.id for opt in sorted_opts],
            "quick_wins": self._find_quick_wins(),
            "high_impact": self._find_high_impact(),
            "optimization_details": [asdict(opt) for opt in sorted_opts],
        }

        return report

    def _group_by_category(self) -> dict[str, int]:
        """按类别分组。"""
        categories = {}
        for opt in self.optimizations:
            categories[opt.category] = categories.get(opt.category, 0) + 1
        return categories

    def _group_by_impact(self) -> dict[str, int]:
        """按影响力分组。"""
        impacts = {}
        for opt in self.optimizations:
            impacts[opt.impact] = impacts.get(opt.impact, 0) + 1
        return impacts

    def _group_by_effort(self) -> dict[str, int]:
        """按难度分组。"""
        efforts = {}
        for opt in self.optimizations:
            efforts[opt.effort] = efforts.get(opt.effort, 0) + 1
        return efforts

    def _find_quick_wins(self) -> list[str]:
        """找到快速见效的优化（高影响、低难度）。"""
        quick_wins = [
            opt.id
            for opt in self.optimizations
            if opt.impact in ["high", "medium"] and opt.effort == "low"
        ]
        return quick_wins

    def _find_high_impact(self) -> list[str]:
        """找到高影响力优化。"""
        return [opt.id for opt in self.optimizations if opt.impact == "high"]

    def print_report(self) -> None:
        """打印优化建议报告。"""
        print("\n" + "=" * 80)
        print("优化建议报告")
        print("=" * 80)

        report = self.generate_report()

        print(f"\n总计: {report['total_optimizations']} 个优化建议")
        print(f"\n按类别:")
        for cat, count in report["by_category"].items():
            print(f"  {cat}: {count}")

        print(f"\n按影响力:")
        for imp, count in report["by_impact"].items():
            print(f"  {imp}: {count}")

        print(f"\n按难度:")
        for eff, count in report["by_effort"].items():
            print(f"  {eff}: {count}")

        # 快速见效的优化
        quick_wins = report["quick_wins"]
        print(f"\n[快速见效] (高影响 + 低难度): {len(quick_wins)} 个")
        for opt_id in quick_wins:
            opt = next(o for o in self.optimizations if o.id == opt_id)
            print(f"  - {opt.title} ({opt.expected_speedup})")

        # 按优先级排序的详细建议
        print("\n\n推荐实施顺序:\n")
        sorted_opts = sorted(
            self.optimizations, key=lambda x: x.priority_score, reverse=True
        )

        for i, opt in enumerate(sorted_opts, 1):
            print(f"{i}. [{opt.impact.upper()}] {opt.title}")
            print(f"   预期加速: {opt.expected_speedup}")
            print(f"   难度: {opt.effort}")
            print(f"   优先级分数: {opt.priority_score:.1f}")
            print(f"   {opt.description}")
            print()

    def save_report(self, output_path: Path) -> None:
        """保存详细报告。"""
        report = self.generate_report()

        # 保存 JSON
        json_path = output_path.with_suffix(".json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 保存文本报告
        lines = []
        lines.append("=" * 80)
        lines.append("HW-1 项目优化建议报告")
        lines.append("=" * 80)
        lines.append(f"\n总计: {report['total_optimizations']} 个优化建议\n")

        sorted_opts = sorted(
            self.optimizations, key=lambda x: x.priority_score, reverse=True
        )

        for i, opt in enumerate(sorted_opts, 1):
            lines.append(f"\n{'='*80}")
            lines.append(f"优化 #{i}: {opt.title}")
            lines.append(f"{'='*80}")
            lines.append(f"ID: {opt.id}")
            lines.append(f"类别: {opt.category}")
            lines.append(f"影响力: {opt.impact}")
            lines.append(f"难度: {opt.effort}")
            lines.append(f"优先级分数: {opt.priority_score:.1f}")
            lines.append(f"预期加速: {opt.expected_speedup}")
            lines.append(f"\n描述:")
            lines.append(f"  {opt.description}")
            lines.append(f"\n实施步骤:")
            for step in opt.implementation_steps:
                lines.append(f"  {step}")
            lines.append(f"\n代码示例:")
            for line in opt.code_example.split("\n"):
                lines.append(f"  {line}")
            lines.append(f"\n影响的文件:")
            for file in opt.affected_files:
                lines.append(f"  - {file}")
            if opt.risks:
                lines.append(f"\n风险:")
                for risk in opt.risks:
                    lines.append(f"  - {risk}")
            lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n详细报告已保存: {output_path}")
        print(f"JSON 数据已保存: {json_path}")


if __name__ == "__main__":
    print("生成 HW-1 项目优化建议")

    advisor = OptimizationAdvisor()
    advisor.create_standard_optimizations()
    advisor.print_report()

    # 保存报告
    output_dir = HW1_ROOT / "advanced_profiling" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    advisor.save_report(output_dir / "optimization_recommendations.txt")
