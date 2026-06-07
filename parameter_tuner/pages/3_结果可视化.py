"""结果可视化页面 - 绘制轨迹、关节角度、能量等图表。"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly 未安装，图表功能受限。运行: pip install plotly")

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))

from parameter_tuner.version_adapter import get_version_adapter

st.set_page_config(page_title="结果可视化", page_icon="📈", layout="wide")

st.title("📈 结果可视化")

version = st.session_state.get("version", "V13.7")
adapter = get_version_adapter(version)

st.info(f"当前版本: {version}")

# 检查是否有可用结果
if not st.session_state.get("simulation_complete", False):
    st.warning("⚠️ 请先运行仿真")
    st.stop()

results_path = st.session_state.get("results_path")
if not results_path or not Path(results_path).exists():
    st.error("❌ 结果文件不存在")
    st.stop()

st.markdown("---")

# 加载数据
try:
    df = pd.read_csv(results_path)
    st.success(f"✅ 已加载结果: {results_path.name}")
except Exception as e:
    st.error(f"❌ 加载失败: {e}")
    st.stop()

# 数据预览
with st.expander("📋 数据预览"):
    st.dataframe(df.head(20))
    st.write(f"总行数: {len(df)}, 总列数: {len(df.columns)}")

st.markdown("---")

# 可视化选项卡
if PLOTLY_AVAILABLE:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🚶 轨迹图", "🦵 关节角度", "⚡ 能量分析", "📊 统计信息", "🎬 动画"]
    )

    with tab1:
        st.header("运动轨迹")

        col1, col2 = st.columns(2)

        with col1:
            # X-Z 轨迹
            if "hip_x" in df.columns and "hip_z" in df.columns:
                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=df["hip_x"],
                        y=df["hip_z"],
                        mode="lines",
                        name="髋部轨迹",
                        line=dict(color="blue", width=2),
                    )
                )

                # 标记起点和终点
                fig.add_trace(
                    go.Scatter(
                        x=[df["hip_x"].iloc[0]],
                        y=[df["hip_z"].iloc[0]],
                        mode="markers",
                        name="起点",
                        marker=dict(color="green", size=12, symbol="circle"),
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=[df["hip_x"].iloc[-1]],
                        y=[df["hip_z"].iloc[-1]],
                        mode="markers",
                        name="终点",
                        marker=dict(color="red", size=12, symbol="square"),
                    )
                )

                fig.update_layout(
                    title="髋部 X-Z 平面轨迹",
                    xaxis_title="X 位置 (m)",
                    yaxis_title="Z 高度 (m)",
                    hovermode="closest",
                    height=500,
                )

                fig.update_yaxis(scaleanchor="x", scaleratio=1)

                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 速度曲线
            if "hip_x_vel" in df.columns and "t" in df.columns:
                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=df["t"],
                        y=df["hip_x_vel"],
                        mode="lines",
                        name="前向速度",
                        line=dict(color="blue", width=2),
                    )
                )

                if "hip_z_vel" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["t"],
                            y=df["hip_z_vel"],
                            mode="lines",
                            name="垂直速度",
                            line=dict(color="red", width=2),
                        )
                    )

                fig.update_layout(
                    title="速度时间曲线",
                    xaxis_title="时间 (s)",
                    yaxis_title="速度 (m/s)",
                    hovermode="x unified",
                    height=500,
                )

                st.plotly_chart(fig, use_container_width=True)

        # 高度时间曲线
        if "hip_z" in df.columns and "t" in df.columns:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=df["t"],
                    y=df["hip_z"],
                    mode="lines",
                    name="髋部高度",
                    line=dict(color="purple", width=2),
                )
            )

            fig.update_layout(
                title="髋部高度随时间变化",
                xaxis_title="时间 (s)",
                yaxis_title="高度 (m)",
                hovermode="x unified",
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("关节角度分析")

        # 髋关节角度
        hip_cols = [
            c
            for c in df.columns
            if "hip" in c.lower()
            and "vel" not in c.lower()
            and c != "hip_x"
            and c != "hip_z"
        ]
        knee_cols = [
            c for c in df.columns if "knee" in c.lower() and "vel" not in c.lower()
        ]

        col1, col2 = st.columns(2)

        with col1:
            if hip_cols and "t" in df.columns:
                fig = go.Figure()

                for col in hip_cols:
                    fig.add_trace(
                        go.Scatter(x=df["t"], y=df[col], mode="lines", name=col)
                    )

                fig.update_layout(
                    title="髋关节角度",
                    xaxis_title="时间 (s)",
                    yaxis_title="角度 (rad)",
                    hovermode="x unified",
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if knee_cols and "t" in df.columns:
                fig = go.Figure()

                for col in knee_cols:
                    fig.add_trace(
                        go.Scatter(x=df["t"], y=df[col], mode="lines", name=col)
                    )

                fig.update_layout(
                    title="膝关节角度",
                    xaxis_title="时间 (s)",
                    yaxis_title="角度 (rad)",
                    hovermode="x unified",
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

        # 相位平面图
        if "left_hip" in df.columns and "left_hip_vel" in df.columns:
            col1, col2 = st.columns(2)

            with col1:
                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=df["left_hip"],
                        y=df["left_hip_vel"],
                        mode="lines",
                        name="左髋",
                        line=dict(width=2),
                    )
                )

                fig.update_layout(
                    title="左髋相位平面",
                    xaxis_title="角度 (rad)",
                    yaxis_title="角速度 (rad/s)",
                    hovermode="closest",
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                if "left_knee" in df.columns and "left_knee_vel" in df.columns:
                    fig = go.Figure()

                    fig.add_trace(
                        go.Scatter(
                            x=df["left_knee"],
                            y=df["left_knee_vel"],
                            mode="lines",
                            name="左膝",
                            line=dict(width=2),
                        )
                    )

                    fig.update_layout(
                        title="左膝相位平面",
                        xaxis_title="角度 (rad)",
                        yaxis_title="角速度 (rad/s)",
                        hovermode="closest",
                        height=400,
                    )

                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.header("能量分析")

        if "E_mech" in df.columns and "t" in df.columns:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=df["t"],
                    y=df["E_mech"],
                    mode="lines",
                    name="机械能",
                    line=dict(color="blue", width=2),
                )
            )

            if "E_input_cumul" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["t"],
                        y=df["E_input_cumul"],
                        mode="lines",
                        name="累积输入能量",
                        line=dict(color="red", width=2),
                    )
                )

            fig.update_layout(
                title="能量随时间变化",
                xaxis_title="时间 (s)",
                yaxis_title="能量 (J)",
                hovermode="x unified",
                height=500,
            )

            st.plotly_chart(fig, use_container_width=True)

            # 能量统计
            col1, col2, col3 = st.columns(3)

            with col1:
                E_start = df["E_mech"].iloc[0]
                st.metric("初始机械能", f"{E_start:.2f} J")

            with col2:
                E_end = df["E_mech"].iloc[-1]
                st.metric("最终机械能", f"{E_end:.2f} J")

            with col3:
                E_delta = E_end - E_start
                st.metric("机械能变化", f"{E_delta:.2f} J", delta=f"{E_delta:.2f} J")

            if "E_input_cumul" in df.columns:
                E_input = df["E_input_cumul"].iloc[-1]
                efficiency = (E_delta / E_input * 100) if E_input > 0 else 0

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("累积输入能量", f"{E_input:.2f} J")
                with col2:
                    st.metric("能量效率", f"{efficiency:.1f}%")

    with tab4:
        st.header("统计信息")

        # 基本统计
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if "t" in df.columns:
                duration = df["t"].iloc[-1] - df["t"].iloc[0]
                st.metric("仿真时长", f"{duration:.2f} s")

        with col2:
            if "hip_x" in df.columns:
                distance = df["hip_x"].iloc[-1] - df["hip_x"].iloc[0]
                st.metric("前进距离", f"{distance:.2f} m")

        with col3:
            if "hip_x_vel" in df.columns:
                avg_speed = df["hip_x_vel"].mean()
                st.metric("平均速度", f"{avg_speed:.3f} m/s")

        with col4:
            if "touchdown_count" in df.columns:
                touchdowns = df["touchdown_count"].iloc[-1]
                st.metric("着地次数", f"{int(touchdowns)}")

        st.markdown("---")

        # 数值统计表
        st.subheader("关键参数统计")

        stats_cols = [
            c
            for c in df.columns
            if c not in ["t", "frame"]
            and not c.endswith("_contact")
            and not c.startswith("phase")
        ]

        if stats_cols:
            stats_df = df[stats_cols].describe().T
            stats_df = stats_df[["mean", "std", "min", "max"]]
            stats_df.columns = ["均值", "标准差", "最小值", "最大值"]

            st.dataframe(stats_df, use_container_width=True)

    with tab5:
        st.header("动画预览")
        st.info("💡 提示: 使用原始仿真脚本的 view_*.py 或 render_*.py 查看完整动画")

        # 显示关键帧
        if "hip_x" in df.columns and "hip_z" in df.columns:
            st.subheader("关键帧快照")

            # 选择几个关键时刻
            n_frames = len(df)
            frame_indices = [0, n_frames // 4, n_frames // 2, 3 * n_frames // 4, -1]

            cols = st.columns(5)

            for i, idx in enumerate(frame_indices):
                with cols[i]:
                    t = df["t"].iloc[idx]
                    x = df["hip_x"].iloc[idx]
                    z = df["hip_z"].iloc[idx]

                    st.write(f"**t={t:.2f}s**")
                    st.write(f"x={x:.2f}m")
                    st.write(f"z={z:.2f}m")

else:
    st.error("❌ Plotly 未安装，无法显示图表")
    st.info("安装命令: pip install plotly")

# 导出功能
st.markdown("---")
st.subheader("导出数据")

col1, col2 = st.columns(2)

with col1:
    # 下载CSV
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 下载完整CSV",
        data=csv_data,
        file_name=f"{results_path.stem}_export.csv",
        mime="text/csv",
    )

with col2:
    # 下载统计摘要
    if PLOTLY_AVAILABLE:
        summary = df.describe().to_csv()
        st.download_button(
            label="📊 下载统计摘要",
            data=summary.encode("utf-8"),
            file_name=f"{results_path.stem}_summary.csv",
            mime="text/csv",
        )
