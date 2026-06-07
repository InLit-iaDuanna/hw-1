"""结果可视化页面 - 显示仿真结果的详细分析"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))


def show(version_key: str, version_info: dict):
    """显示结果分析页面"""
    st.header("📈 结果分析")

    # 检查是否有结果
    if f"result_{version_key}" not in st.session_state:
        st.warning("⚠️ 暂无仿真结果，请先运行仿真")
        return

    result = st.session_state[f"result_{version_key}"]

    # 结果摘要
    success = result.get("success", False)

    if success:
        st.success("✅ 仿真成功")
    else:
        st.error(f"❌ 仿真失败: {result.get('failure_reason', 'Unknown')}")

    # 核心指标
    st.subheader("📊 核心指标")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("仿真时长", f"{result.get('duration', 0):.2f} s")

    with col2:
        forward = result.get("forward_distance", 0)
        st.metric("前进距离", f"{forward:.2f} m", delta="✓" if forward > 0.8 else "✗")

    with col3:
        touchdowns = result.get("num_touchdowns", 0)
        st.metric("触地次数", f"{touchdowns}", delta="✓" if touchdowns >= 10 else "✗")

    with col4:
        if "final_energy" in result:
            st.metric("最终能量", f"{result['final_energy']:.2f} J")
        else:
            st.metric("最终能量", "N/A")

    with col5:
        if "avg_speed" in result:
            st.metric("平均速度", f"{result['avg_speed']:.2f} m/s")
        elif result.get("duration", 0) > 0:
            avg_speed = result.get("forward_distance", 0) / result["duration"]
            st.metric("平均速度", f"{avg_speed:.2f} m/s")
        else:
            st.metric("平均速度", "N/A")

    st.markdown("---")

    # 轨迹数据
    if "trajectory" not in result or len(result["trajectory"]) == 0:
        st.warning("无轨迹数据")
        return

    traj = result["trajectory"]
    df = pd.DataFrame(traj)

    # 可视化选项
    st.subheader("📊 可视化选项")

    viz_type = st.selectbox(
        "选择图表类型",
        [
            "髋部轨迹",
            "关节角度",
            "关节速度",
            "力矩输出",
            "能量演化",
            "触地相位",
            "全局概览",
        ],
    )

    st.markdown("---")

    # 根据选择显示不同图表
    if viz_type == "髋部轨迹":
        st.subheader("🏃 髋部运动轨迹")

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=("X-Z 平面轨迹", "X 方向位移", "Z 方向位移", "速度分量"),
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "scatter"}],
            ],
        )

        # X-Z 平面
        fig.add_trace(
            go.Scatter(
                x=df["hip_x"],
                y=df["hip_z"],
                mode="lines",
                name="轨迹",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )

        # X 方向
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["hip_x"],
                mode="lines",
                name="X 位置",
                line=dict(color="red"),
            ),
            row=1,
            col=2,
        )

        # Z 方向
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["hip_z"],
                mode="lines",
                name="Z 位置",
                line=dict(color="green"),
            ),
            row=2,
            col=1,
        )

        # 速度
        if "hip_vx" in df.columns and "hip_vz" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["hip_vx"],
                    mode="lines",
                    name="Vx",
                    line=dict(color="red", dash="dash"),
                ),
                row=2,
                col=2,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["hip_vz"],
                    mode="lines",
                    name="Vz",
                    line=dict(color="green", dash="dash"),
                ),
                row=2,
                col=2,
            )

        fig.update_xaxes(title_text="X (m)", row=1, col=1)
        fig.update_yaxes(title_text="Z (m)", row=1, col=1)
        fig.update_xaxes(title_text="时间 (s)", row=1, col=2)
        fig.update_xaxes(title_text="时间 (s)", row=2, col=1)
        fig.update_xaxes(title_text="时间 (s)", row=2, col=2)

        fig.update_layout(height=700, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "关节角度":
        st.subheader("🦵 关节角度时间序列")

        fig = make_subplots(
            rows=2, cols=2, subplot_titles=("左髋", "右髋", "左膝", "右膝")
        )

        joints = [
            ("left_hip", 1, 1, "blue"),
            ("right_hip", 1, 2, "red"),
            ("left_knee", 2, 1, "cyan"),
            ("right_knee", 2, 2, "orange"),
        ]

        for joint_name, row, col, color in joints:
            if joint_name in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df[joint_name],
                        mode="lines",
                        name=joint_name,
                        line=dict(color=color, width=2),
                    ),
                    row=row,
                    col=col,
                )

        fig.update_xaxes(title_text="时间 (s)")
        fig.update_yaxes(title_text="角度 (rad)")
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "关节速度":
        st.subheader("⚡ 关节角速度")

        fig = go.Figure()

        velocity_cols = [
            col for col in df.columns if "_vel" in col and "hip" not in col
        ]
        colors = ["blue", "red", "cyan", "orange"]

        for i, col in enumerate(velocity_cols[:4]):
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df[col],
                    mode="lines",
                    name=col,
                    line=dict(color=colors[i % len(colors)]),
                )
            )

        fig.update_layout(
            title="关节角速度",
            xaxis_title="时间 (s)",
            yaxis_title="角速度 (rad/s)",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "力矩输出":
        st.subheader("💪 力矩输出")

        torque_cols = [
            col for col in df.columns if "tau" in col.lower() or "torque" in col.lower()
        ]

        if torque_cols:
            fig = go.Figure()

            colors = ["blue", "red", "green", "orange", "purple", "brown"]
            for i, col in enumerate(torque_cols):
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df[col],
                        mode="lines",
                        name=col,
                        line=dict(color=colors[i % len(colors)]),
                    )
                )

            fig.update_layout(
                title="力矩时间序列",
                xaxis_title="时间 (s)",
                yaxis_title="力矩 (Nm)",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("无力矩数据")

    elif viz_type == "能量演化":
        st.subheader("⚡ 能量演化")

        if "energy" in df.columns or "E" in df.columns:
            energy_col = "energy" if "energy" in df.columns else "E"

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df[energy_col],
                    mode="lines",
                    name="机械能",
                    line=dict(color="purple", width=2),
                )
            )

            fig.update_layout(
                title="系统机械能",
                xaxis_title="时间 (s)",
                yaxis_title="能量 (J)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            # 能量统计
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("初始能量", f"{df[energy_col].iloc[0]:.2f} J")
            with col2:
                st.metric("最终能量", f"{df[energy_col].iloc[-1]:.2f} J")
            with col3:
                energy_loss = df[energy_col].iloc[0] - df[energy_col].iloc[-1]
                st.metric("能量变化", f"{energy_loss:.2f} J")
        else:
            st.info("无能量数据")

    elif viz_type == "触地相位":
        st.subheader("👣 触地相位分析")

        contact_cols = [col for col in df.columns if "contact" in col.lower()]

        if contact_cols:
            fig = go.Figure()

            for col in contact_cols[:2]:  # 左右脚
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df[col],
                        mode="lines",
                        name=col,
                        line=dict(width=2),
                    )
                )

            fig.update_layout(
                title="触地状态",
                xaxis_title="时间 (s)",
                yaxis_title="触地 (0/1)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("无触地数据")

    elif viz_type == "全局概览":
        st.subheader("🌐 全局概览")

        # 创建 6 个子图
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                "髋部 X-Z 轨迹",
                "髋部 X 位移",
                "左髋角度",
                "右髋角度",
                "左膝角度",
                "右膝角度",
            ),
            vertical_spacing=0.1,
        )

        # 轨迹
        fig.add_trace(
            go.Scatter(
                x=df["hip_x"],
                y=df["hip_z"],
                mode="lines",
                name="轨迹",
                line=dict(color="blue"),
            ),
            row=1,
            col=1,
        )

        # X 位移
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["hip_x"],
                mode="lines",
                name="X",
                line=dict(color="red"),
            ),
            row=1,
            col=2,
        )

        # 关节角度
        if "left_hip" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["left_hip"],
                    mode="lines",
                    name="左髋",
                    line=dict(color="blue"),
                ),
                row=2,
                col=1,
            )

        if "right_hip" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["right_hip"],
                    mode="lines",
                    name="右髋",
                    line=dict(color="red"),
                ),
                row=2,
                col=2,
            )

        if "left_knee" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["left_knee"],
                    mode="lines",
                    name="左膝",
                    line=dict(color="cyan"),
                ),
                row=3,
                col=1,
            )

        if "right_knee" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["right_knee"],
                    mode="lines",
                    name="右膝",
                    line=dict(color="orange"),
                ),
                row=3,
                col=2,
            )

        fig.update_layout(height=900, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # 数据导出
    st.markdown("---")
    st.subheader("💾 数据导出")

    col1, col2 = st.columns(2)

    with col1:
        # CSV 下载
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 下载 CSV",
            data=csv,
            file_name=f"{version_key}_trajectory.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        # JSON 下载
        import json

        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="📥 下载 JSON",
            data=json_str,
            file_name=f"{version_key}_result.json",
            mime="application/json",
            use_container_width=True,
        )
