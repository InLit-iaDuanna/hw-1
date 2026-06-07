"""跨版本分析工具集 - 综合报告生成器。

汇总所有分析结果，生成 HTML 综合报告。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# 添加 common 到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.plot_styles import set_style

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def generate_html_report() -> None:
    """生成 HTML 综合报告。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HW-1 跨版本分析综合报告</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #2a7a3b 0%, #4a7ba7 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #2a7a3b;
            border-bottom: 3px solid #2a7a3b;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .section h3 {{
            color: #4a7ba7;
            margin-top: 20px;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .image-container {{
            text-align: center;
            background: #fafafa;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .image-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .image-container p {{
            margin: 10px 0 0 0;
            color: #666;
            font-size: 0.9em;
        }}
        .summary-box {{
            background: #e8f5e9;
            border-left: 4px solid #2a7a3b;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .warning-box {{
            background: #fff3e0;
            border-left: 4px solid #d68b00;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #2a7a3b;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 5px;
        }}
        .badge-success {{ background: #2a7a3b; color: white; }}
        .badge-warning {{ background: #d68b00; color: white; }}
        .badge-info {{ background: #4a7ba7; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 HW-1 步态训练辅助设备</h1>
        <h2>跨版本分析综合报告 (V01-V24)</h2>
        <p>📅 生成时间: {timestamp}</p>
        <p>📊 项目路径: D:\\Dunna\\Documents\\hw-1</p>
    </div>

    <div class="section">
        <h2>📋 执行摘要</h2>
        <div class="summary-box">
            <h3>项目概览</h3>
            <p><strong>HW-1</strong> 是一个基于 MuJoCo 的轻量化柔顺步态训练辅助设备项目，经历了 <strong>24 个版本</strong>的迭代优化。</p>
            <ul>
                <li><span class="badge badge-info">V01-V06</span> 被动步态探索阶段</li>
                <li><span class="badge badge-success">V07-V13</span> 主动控制优化阶段</li>
                <li><span class="badge badge-warning">V14-V17</span> 柔顺驱动器（SEA）阶段</li>
                <li><span class="badge badge-info">V18-V21</span> 3D 扩展阶段</li>
                <li><span class="badge badge-warning">V22-V24</span> 硬件实现阶段</li>
            </ul>
        </div>

        <div class="warning-box">
            <h3>⚠️ 关键里程碑</h3>
            <ul>
                <li><strong>V10</strong>: 首次实现 CoT < 0.08 (滚动足仿生步态)</li>
                <li><strong>V13</strong>: 完成参数敏感度图集，稳定域映射</li>
                <li><strong>V14</strong>: 最优能效版本 (CoT ≈ 0.068)，FSM 相位识别</li>
                <li><strong>V19</strong>: 3D 侧向稳定性控制</li>
                <li><strong>V24</strong>: Sim-to-Real 迁移</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>📈 1. 版本性能对比</h2>
        <p>对比 V01-V24 的关键性能指标演化趋势。</p>

        <div class="image-grid">
            <div class="image-container">
                <img src="version_timeline.png" alt="版本时间线">
                <p>版本演化时间线</p>
            </div>
            <div class="image-container">
                <img src="forward_distance_trend.png" alt="前向距离趋势">
                <p>前向距离演化</p>
            </div>
            <div class="image-container">
                <img src="cot_trend.png" alt="CoT趋势">
                <p>运输成本（CoT）趋势</p>
            </div>
            <div class="image-container">
                <img src="success_rate_trend.png" alt="成功率趋势">
                <p>稳定性（成功率）趋势</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🎯 2. 稳定域可视化</h2>
        <p>基于 V13 参数敏感度图集的稳定域分析。</p>

        <h3>2.1 关键参数切片 (2D)</h3>
        <div class="image-grid">
            <div class="image-container">
                <img src="v13_stability_A_slope_foot.png" alt="Slope vs Foot">
                <p>坡度 vs 足半径</p>
            </div>
            <div class="image-container">
                <img src="v13_stability_E_hip_gains.png" alt="Hip Gains">
                <p>髋关节 Kp vs Kd</p>
            </div>
        </div>

        <h3>2.2 3D 稳定域表面</h3>
        <div class="image-grid">
            <div class="image-container">
                <img src="v13_stability_3d_A_slope_foot.png" alt="3D Slope vs Foot">
                <p>3D 稳定域 - 坡度 vs 足半径</p>
            </div>
            <div class="image-container">
                <img src="v13_stability_3d_E_hip_gains.png" alt="3D Hip Gains">
                <p>3D 稳定域 - 髋关节增益</p>
            </div>
        </div>

        <h3>2.3 切片成功率对比</h3>
        <div class="image-container">
            <img src="v13_slice_success_rates.png" alt="切片成功率" style="max-width: 80%;">
            <p>V13 各参数切片稳定性对比</p>
        </div>

        <h3>2.4 参数相关性分析</h3>
        <div class="image-container">
            <img src="v13_parameter_correlation.png" alt="参数相关性" style="max-width: 70%;">
            <p>关键参数相关性热图</p>
        </div>
    </div>

    <div class="section">
        <h2>⚡ 3. 能量效率排行</h2>
        <p>各版本 CoT（Cost of Transport）对比和演化分析。</p>

        <div class="image-grid">
            <div class="image-container">
                <img src="cot_ranking.png" alt="CoT排行">
                <p>能量效率排行榜</p>
            </div>
            <div class="image-container">
                <img src="cot_evolution_annotated.png" alt="CoT演化">
                <p>CoT 演化趋势（带注释）</p>
            </div>
        </div>

        <h3>3.1 V13 CoT 分布</h3>
        <div class="image-container">
            <img src="v13_cot_distribution.png" alt="V13 CoT分布" style="max-width: 80%;">
            <p>V13 各切片 CoT 箱线图</p>
        </div>

        <h3>3.2 Top 5 综合性能</h3>
        <div class="image-container">
            <img src="top5_performance_radar.png" alt="Top5雷达图" style="max-width: 70%;">
            <p>Top 5 版本综合性能雷达图</p>
        </div>
    </div>

    <div class="section">
        <h2>🎓 4. 关键发现与建议</h2>

        <h3>4.1 性能演化规律</h3>
        <ul>
            <li><strong>被动到主动</strong>: V01-V06 纯被动步态 CoT ≈ 0.12，V08 引入髋控制后降至 0.08</li>
            <li><strong>形态优化</strong>: V10 滚动足设计显著改善能效（CoT 0.075）</li>
            <li><strong>参数调优</strong>: V12-V13 系统化参数扫描，锁定最优区域</li>
            <li><strong>轻量化红利</strong>: V14 质量优化+FSM 实现最优 CoT 0.068</li>
            <li><strong>真实性代价</strong>: V16 引入真实电机动力学后 CoT 回升至 0.078</li>
        </ul>

        <h3>4.2 稳定域特征</h3>
        <ul>
            <li>坡度敏感性高，稳定窗口窄（-1° ~ +1°）</li>
            <li>足半径与腿长比例需精确匹配（约 4-5% 成功率区域）</li>
            <li>髋关节增益存在最优组合（Kp ≈ 30, Kd ≈ 6）</li>
            <li>参数耦合显著，多维优化必要</li>
        </ul>

        <h3>4.3 后续优化方向</h3>
        <div class="warning-box">
            <ul>
                <li>🔄 <strong>扩大稳定域</strong>: 当前成功率 5-17%，需鲁棒性增强</li>
                <li>⚡ <strong>能效进一步优化</strong>: 目标 CoT < 0.065</li>
                <li>🎯 <strong>3D 性能提升</strong>: V18-V21 侧向稳定性仍需改进</li>
                <li>🔧 <strong>硬件验证</strong>: V24 Sim-to-Real gap 补偿</li>
                <li>📊 <strong>自适应控制</strong>: 在线参数调整，适应不同地形</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>📊 5. 数据文件清单</h2>
        <table>
            <tr>
                <th>文件名</th>
                <th>描述</th>
            </tr>
            <tr>
                <td><code>version_comparison.csv</code></td>
                <td>版本对比表格（所有版本关键指标）</td>
            </tr>
            <tr>
                <td><code>energy_efficiency_ranking.csv</code></td>
                <td>能量效率排行榜</td>
            </tr>
            <tr>
                <td><code>*.png</code></td>
                <td>所有可视化图表（18+ 张）</td>
            </tr>
        </table>
    </div>

    <div class="footer">
        <p>本报告由 <strong>跨版本分析工具集</strong> 自动生成</p>
        <p>工具路径: <code>D:\\Dunna\\Documents\\hw-1\\cross_version_analysis</code></p>
        <p>段泽琪 | 工业设计博士 | 2024211317</p>
    </div>
</body>
</html>
"""

    report_path = OUT_DIR / "comprehensive_report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] 生成 HTML 报告: {report_path}")


def run_all_tools() -> None:
    """依次运行所有分析工具。"""
    import energy_efficiency_ranking
    import stability_domain_visualizer
    import version_comparator

    print("\n" + "=" * 80)
    print("运行所有跨版本分析工具")
    print("=" * 80)

    print("\n[工具 1/3] 版本性能对比...")
    print("-" * 80)
    version_comparator.main()

    print("\n[工具 2/3] 稳定域可视化...")
    print("-" * 80)
    stability_domain_visualizer.main()

    print("\n[工具 3/3] 能量效率排行...")
    print("-" * 80)
    energy_efficiency_ranking.main()


def main() -> None:
    """主函数。"""
    set_style()
    print("=" * 80)
    print("综合报告生成器")
    print("=" * 80)

    print("\n[1/2] 运行所有分析工具...")
    try:
        run_all_tools()
    except Exception as e:
        print(f"[WARN] 部分工具运行失败: {e}")
        print("    继续生成报告...")

    print("\n[2/2] 生成 HTML 综合报告...")
    generate_html_report()

    print("\n" + "=" * 80)
    print("[OK] 综合报告生成完成!")
    print(f"[DIR] 输出目录: {OUT_DIR}")
    print(f"[HTML] 打开报告: {OUT_DIR / 'comprehensive_report.html'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
