"""
生成依赖关系图
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def create_dependency_graph():
    """创建依赖关系图"""

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # 颜色方案
    colors = {
        'core': '#FF6B6B',          # 红色 - 核心
        'visualization': '#4ECDC4', # 青色 - 可视化
        'analysis': '#95E1D3',      # 浅绿 - 分析
        'optimization': '#FFE66D',  # 黄色 - 优化
        'ui': '#A8E6CF',           # 淡绿 - UI
        'dev': '#C7CEEA',          # 紫色 - 开发
        'external': '#D3D3D3',     # 灰色 - 外部
    }

    # 定义各层级的包
    layers = {
        'core': {
            'title': '核心仿真依赖\n(requirements-core.txt)',
            'packages': ['mujoco==3.3.7', 'numpy==2.2.6', 'scipy>=1.10.0',
                        'imageio==2.37.2', 'imageio-ffmpeg==0.6.0'],
            'y': 10,
            'color': colors['core']
        },
        'visualization': {
            'title': '可视化依赖\n(requirements-viz.txt)',
            'packages': ['matplotlib==3.10.7', 'pillow', 'seaborn>=0.12.0', 'plotly>=5.17.0'],
            'y': 7.5,
            'color': colors['visualization']
        },
        'analysis': {
            'title': '数据分析依赖\n(requirements-analysis.txt)',
            'packages': ['pandas>=2.0.0', 'pyyaml>=6.0'],
            'y': 5.5,
            'color': colors['analysis']
        },
        'optimization': {
            'title': '参数优化依赖\n(requirements-opt.txt)',
            'packages': ['scikit-optimize>=0.9.0', 'deap>=1.3.1', 'cma>=3.2.2',
                        'scikit-learn>=1.3.0', 'pymoo>=0.6.0', 'salib>=1.4.7', 'joblib>=1.3.0'],
            'y': 3,
            'color': colors['optimization']
        },
        'ui': {
            'title': 'UI工具依赖\n(requirements-ui.txt)',
            'packages': ['streamlit>=1.28.0'],
            'y': 1,
            'color': colors['ui']
        },
        'dev': {
            'title': '开发测试依赖\n(requirements-dev.txt)',
            'packages': ['pytest>=7.4.0', 'pytest-cov>=4.1.0',
                        'pytest-xdist>=3.3.0', 'pytest-timeout>=2.1.0'],
            'y': 1,
            'color': colors['dev']
        },
    }

    # 绘制层级
    box_width = 4
    box_height = 1.2

    for layer_name, layer_data in layers.items():
        y = layer_data['y']
        color = layer_data['color']

        if layer_name in ['ui', 'dev']:
            # UI 和 Dev 并排显示
            if layer_name == 'ui':
                x = 1
            else:
                x = 5.5
            box_width_small = 3.5
        else:
            x = 3
            box_width_small = box_width

        # 绘制主框
        box = FancyBboxPatch(
            (x, y), box_width_small, box_height,
            boxstyle="round,pad=0.1",
            edgecolor='black',
            facecolor=color,
            alpha=0.3,
            linewidth=2
        )
        ax.add_patch(box)

        # 标题
        ax.text(
            x + box_width_small / 2, y + box_height - 0.15,
            layer_data['title'],
            ha='center', va='top',
            fontsize=11, fontweight='bold'
        )

        # 包列表
        packages_text = '\n'.join(layer_data['packages'])
        ax.text(
            x + box_width_small / 2, y + 0.5,
            packages_text,
            ha='center', va='center',
            fontsize=8,
            family='monospace'
        )

    # 绘制依赖箭头
    arrow_props = dict(
        arrowstyle='->',
        lw=2,
        color='gray',
        alpha=0.6,
        connectionstyle='arc3,rad=0'
    )

    # core -> visualization
    ax.annotate('', xy=(5, 7.5 + box_height), xytext=(5, 10),
                arrowprops=arrow_props)

    # visualization -> analysis
    ax.annotate('', xy=(5, 5.5 + box_height), xytext=(5, 7.5),
                arrowprops=arrow_props)

    # analysis -> optimization
    ax.annotate('', xy=(5, 3 + box_height), xytext=(5, 5.5),
                arrowprops=arrow_props)

    # analysis -> ui
    ax.annotate('', xy=(2.75, 1 + box_height), xytext=(4, 5.5),
                arrowprops=arrow_props)

    # analysis -> dev
    ax.annotate('', xy=(7.25, 1 + box_height), xytext=(6, 5.5),
                arrowprops=arrow_props)

    # 添加标题
    ax.text(5, 11.5, 'hw-1 项目依赖关系图',
            ha='center', va='center', fontsize=18, fontweight='bold')

    # 添加图例
    legend_elements = [
        mpatches.Patch(facecolor=colors['core'], alpha=0.3, edgecolor='black', label='核心仿真'),
        mpatches.Patch(facecolor=colors['visualization'], alpha=0.3, edgecolor='black', label='可视化'),
        mpatches.Patch(facecolor=colors['analysis'], alpha=0.3, edgecolor='black', label='数据分析'),
        mpatches.Patch(facecolor=colors['optimization'], alpha=0.3, edgecolor='black', label='参数优化'),
        mpatches.Patch(facecolor=colors['ui'], alpha=0.3, edgecolor='black', label='UI工具'),
        mpatches.Patch(facecolor=colors['dev'], alpha=0.3, edgecolor='black', label='开发测试'),
    ]

    ax.legend(handles=legend_elements, loc='lower left', fontsize=10,
             framealpha=0.9, ncol=3)

    # 添加说明
    note_text = (
        "依赖层级说明:\n"
        "• 核心依赖：MuJoCo仿真必需，所有版本共用\n"
        "• 可视化依赖：图表、动画生成（依赖核心）\n"
        "• 数据分析依赖：数据处理、统计分析（依赖可视化）\n"
        "• 参数优化依赖：自动调参工具（依赖分析）\n"
        "• UI/开发依赖：可选工具集（依赖分析）"
    )

    ax.text(0.2, 0.2, note_text, fontsize=9,
           verticalalignment='bottom', family='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # 保存
    output_path = Path(__file__).parent / 'DEPENDENCY_GRAPH.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    print(f"依赖关系图已保存到: {output_path}")

    return output_path


def create_version_matrix():
    """创建版本兼容性矩阵图"""

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    # 包和版本信息
    packages = [
        ('mujoco', '3.3.7', '==', '核心仿真引擎'),
        ('numpy', '2.2.6', '==', '数值计算基础'),
        ('scipy', '1.10.0', '>=', '科学计算'),
        ('matplotlib', '3.10.7', '==', '2D绘图'),
        ('imageio', '2.37.2', '==', '图像/视频IO'),
        ('imageio-ffmpeg', '0.6.0', '==', '视频编码'),
        ('pillow', 'latest', '>=', '图像处理'),
        ('seaborn', '0.12.0', '>=', '统计可视化'),
        ('plotly', '5.17.0', '>=', '交互式图表'),
        ('pandas', '2.0.0', '>=', '数据处理'),
        ('pyyaml', '6.0', '>=', 'YAML解析'),
        ('streamlit', '1.28.0', '>=', 'Web UI'),
        ('pytest', '7.4.0', '>=', '测试框架'),
        ('scikit-learn', '1.3.0', '>=', '机器学习'),
        ('scikit-optimize', '0.9.0', '>=', '贝叶斯优化'),
        ('deap', '1.3.1', '>=', '遗传算法'),
        ('cma', '3.2.2', '>=', 'CMA-ES优化'),
        ('pymoo', '0.6.0', '>=', '多目标优化'),
        ('salib', '1.4.7', '>=', '敏感性分析'),
        ('joblib', '1.3.0', '>=', '并行计算'),
    ]

    # 准备数据
    package_names = [p[0] for p in packages]
    versions = [p[1] for p in packages]
    operators = [p[2] for p in packages]
    descriptions = [p[3] for p in packages]

    # 创建表格
    ax.axis('tight')
    ax.axis('off')

    # 表格数据
    table_data = []
    for i, (name, ver, op, desc) in enumerate(packages):
        # 颜色编码
        if i < 6:
            color = '#FFE6E6'  # 核心 - 浅红
        elif i < 11:
            color = '#E6F3FF'  # 可视化/分析 - 浅蓝
        elif i < 13:
            color = '#E6FFE6'  # UI/测试 - 浅绿
        else:
            color = '#FFF9E6'  # 优化 - 浅黄

        version_str = f"{op}{ver}"
        table_data.append([name, version_str, desc])

    table = ax.table(
        cellText=table_data,
        colLabels=['包名', '版本', '说明'],
        cellLoc='left',
        loc='center',
        colWidths=[0.25, 0.15, 0.6]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # 设置表头样式
    for i in range(3):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # 设置行颜色
    for i in range(1, len(packages) + 1):
        if i <= 6:
            color = '#FFE6E6'
        elif i <= 11:
            color = '#E6F3FF'
        elif i <= 13:
            color = '#E6FFE6'
        else:
            color = '#FFF9E6'

        for j in range(3):
            table[(i, j)].set_facecolor(color)

    # 标题
    plt.suptitle('hw-1 依赖版本兼容性矩阵',
                fontsize=16, fontweight='bold', y=0.98)

    # 图例
    legend_text = (
        "颜色说明:\n"
        "浅红色 = 核心仿真依赖 (固定版本)\n"
        "浅蓝色 = 可视化/分析依赖\n"
        "浅绿色 = UI/测试工具\n"
        "浅黄色 = 参数优化工具\n\n"
        "版本符号:\n"
        "== : 精确版本（推荐用于核心依赖）\n"
        ">= : 最低版本（允许兼容更新）"
    )

    plt.figtext(0.12, 0.02, legend_text, fontsize=8,
               verticalalignment='bottom',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # 保存
    output_path = Path(__file__).parent / 'DEPENDENCY_VERSION_MATRIX.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    print(f"版本兼容性矩阵已保存到: {output_path}")

    return output_path


if __name__ == '__main__':
    print("生成依赖关系图...")
    create_dependency_graph()

    print("\n生成版本兼容性矩阵...")
    create_version_matrix()

    print("\n完成!")
