"""HW-1 交互式参数调优工具 - Streamlit 应用主入口

支持版本: V10, V13.6, V13.7, V14, V16, V17
核心功能: 参数编辑、实时仿真、结果可视化、批量扫描
"""

import sys
from pathlib import Path

import streamlit as st

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(HW1_ROOT))

# 页面配置
st.set_page_config(
    page_title="HW-1 参数调优工具",
    page_icon="🦿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .version-badge {
        background-color: #e8f4f8;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 侧边栏 - 版本选择
st.sidebar.markdown("## 🦿 HW-1 参数调优")
st.sidebar.markdown("---")

VERSION_INFO = {
    "V10": {
        "name": "V10 - 滚动足被动步态",
        "description": "基础滚动足机制，准被动稳定行走",
        "module": "v10_rolling_foot_biomimetic_gait",
        "color": "#2ca02c",
    },
    "V13.6": {
        "name": "V13.6 - 事件驱动FSM",
        "description": "4相位状态机（stance_early/late, swing_thrust/retract）",
        "module": "v13_6_event_driven_fsm",
        "color": "#ff7f0e",
    },
    "V13.7": {
        "name": "V13.7 - 摩擦补偿",
        "description": "V13.6 + 库仑摩擦补偿",
        "module": "v13_7_friction_compensation",
        "color": "#d62728",
    },
    "V14": {
        "name": "V14 - 被动手臂",
        "description": "添加被动摆臂提升稳定性",
        "module": "v14_passive_arms",
        "color": "#9467bd",
    },
    "V16": {
        "name": "V16 - 电机动力学",
        "description": "L1电机模型（转子惯量、库仑摩擦、电流饱和）",
        "module": "v16_motor_dynamics",
        "color": "#8c564b",
    },
    "V17": {
        "name": "V17 - 状态估计",
        "description": "传感器噪声 + 状态估计器",
        "module": "v17_state_estimation",
        "color": "#e377c2",
    },
}

selected_version = st.sidebar.selectbox(
    "选择版本",
    options=list(VERSION_INFO.keys()),
    format_func=lambda x: VERSION_INFO[x]["name"],
)

st.sidebar.markdown(
    f"""
<div class="version-badge" style="background-color: {VERSION_INFO[selected_version]['color']}20;">
    {VERSION_INFO[selected_version]['description']}
</div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

# 导航
page = st.sidebar.radio(
    "导航",
    ["📊 仪表盘", "⚙️ 参数编辑", "▶️ 运行仿真", "📈 结果分析", "🔍 批量扫描"],
    label_visibility="collapsed",
)

# 主页面
st.markdown(
    '<div class="main-header">HW-1 步态训练设备参数调优工具</div>',
    unsafe_allow_html=True,
)

if page == "📊 仪表盘":
    from pages import dashboard

    dashboard.show(selected_version, VERSION_INFO[selected_version])

elif page == "⚙️ 参数编辑":
    from pages import parameter_editor

    parameter_editor.show(selected_version, VERSION_INFO[selected_version])

elif page == "▶️ 运行仿真":
    from pages import simulation_runner

    simulation_runner.show(selected_version, VERSION_INFO[selected_version])

elif page == "📈 结果分析":
    from pages import results_viewer

    results_viewer.show(selected_version, VERSION_INFO[selected_version])

elif page == "🔍 批量扫描":
    from pages import batch_scanner

    batch_scanner.show(selected_version, VERSION_INFO[selected_version])

# 页脚
st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 使用提示
1. 选择版本
2. 编辑参数
3. 运行仿真
4. 查看结果
5. 导出配置

### 📚 快捷键
- `Ctrl+R`: 重新运行
- `Ctrl+S`: 保存配置
""")
