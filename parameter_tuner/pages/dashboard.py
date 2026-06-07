"""仪表盘页面 - 显示版本信息和最近运行历史"""

import json
from pathlib import Path

import streamlit as st


def show(version_key: str, version_info: dict):
    """显示仪表盘"""
    st.header("📊 仪表盘")

    # 版本信息卡片
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>当前版本</h3>
            <h2 style="color: {version_info['color']};">{version_key}</h2>
            <p>{version_info['description']}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div class="metric-card">
            <h3>模块路径</h3>
            <p style="font-family: monospace; font-size: 0.9rem;">
            """
            + version_info["module"]
            + """
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        # 统计最近运行
        cache_dir = Path(__file__).resolve().parent.parent / "cache"
        history_file = cache_dir / f"{version_key}_history.json"

        run_count = 0
        if history_file.exists():
            try:
                with open(history_file, encoding="utf-8") as f:
                    history = json.load(f)
                    run_count = len(history.get("runs", []))
            except:
                pass

        st.markdown(
            f"""
        <div class="metric-card">
            <h3>历史运行</h3>
            <h2>{run_count}</h2>
            <p>次仿真</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 版本特性说明
    st.subheader("📋 版本特性")

    version_features = {
        "V10": [
            "✓ 滚动足机制（足底半径 + 脚尖半径）",
            "✓ 踝关节刚度与阻尼",
            "✓ 膝关节限位与 PD 控制",
            "✓ 髋关节 PD 跟踪控制",
            "✓ 成功判据：前进 > 0.8m, 时长 > 10s, 触地 > 10 次",
        ],
        "V13.6": [
            "✓ 4 相位事件驱动 FSM",
            "  - stance_early: 支撑腿前期（强 PD 跟踪）",
            "  - stance_late: 支撑腿后期（push-off 准备）",
            "  - swing_thrust: 摆动腿前半段（能量注入）",
            "  - swing_retract: 摆动腿后半段（被动摆回）",
            "✓ 每相位独立参数：k_E, k_PD, tau_max, kd",
            "✓ 能量整形 + PD 平滑过渡",
        ],
        "V13.7": [
            "✓ 继承 V13.6 全部特性",
            "✓ 库仑摩擦补偿（tau_C_eff）",
            "✓ 符号平滑函数（避免抖振）",
        ],
        "V14": [
            "✓ 继承 V13.6 FSM 控制",
            "✓ 添加被动手臂（质量、长度可调）",
            "✓ 提升横向稳定性",
        ],
        "V16": [
            "✓ 继承 V14 机械结构",
            "✓ L1 一阶电机动力学模型",
            "✓ 转子惯量折算到关节",
            "✓ 库仑摩擦 + 粘滞摩擦",
            "✓ 电流饱和限制（I_max, I_cont）",
            "✓ 电机预设：mx64ar, mx106t 等",
        ],
        "V17": [
            "✓ 继承 V16 电机动力学",
            "✓ 传感器噪声模型",
            "  - 编码器量化噪声",
            "  - FK 髋部位置估计",
            "  - 接触抖动",
            "✓ 状态估计器（低通滤波）",
        ],
    }

    features = version_features.get(version_key, ["该版本特性待补充"])
    for feature in features:
        st.markdown(feature)

    st.markdown("---")

    # 最近运行历史
    st.subheader("🕐 最近运行")

    if history_file.exists():
        try:
            with open(history_file, encoding="utf-8") as f:
                history = json.load(f)
                runs = history.get("runs", [])

                if runs:
                    # 显示最近 5 次
                    for run in runs[-5:][::-1]:
                        timestamp = run.get("timestamp", "Unknown")
                        success = run.get("success", False)
                        duration = run.get("duration", 0)
                        forward = run.get("forward_distance", 0)

                        status_color = "#d4edda" if success else "#f8d7da"
                        status_text = "✓ 成功" if success else "✗ 失败"

                        st.markdown(
                            f"""
                        <div style="background-color: {status_color}; padding: 0.5rem; border-radius: 0.3rem; margin: 0.5rem 0;">
                            <strong>{timestamp}</strong> - {status_text} |
                            前进: {forward:.2f}m | 时长: {duration:.2f}s
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("暂无运行历史")
        except Exception as e:
            st.warning(f"无法加载历史记录: {e}")
    else:
        st.info("暂无运行历史，请先运行仿真")

    # 快速开始指南
    st.markdown("---")
    st.subheader("🚀 快速开始")

    st.markdown("""
    1. **参数编辑**: 在左侧选择 "⚙️ 参数编辑" 调整参数
    2. **运行仿真**: 切换到 "▶️ 运行仿真" 执行仿真
    3. **查看结果**: 在 "📈 结果分析" 查看轨迹和指标
    4. **批量扫描**: 使用 "🔍 批量扫描" 进行参数空间探索

    **提示**: 修改参数后会自动保存到会话状态，切换页面不会丢失
    """)
