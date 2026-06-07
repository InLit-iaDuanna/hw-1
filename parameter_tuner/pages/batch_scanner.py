"""批量参数扫描页面 - 参数空间探索和敏感度分析"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))


def get_scannable_params(version_key: str, params):
    """获取可扫描的参数列表"""
    scannable = {}

    if version_key == "V10":
        scannable = {
            "hip_mass": (3.0, 8.0, 0.5),
            "foot_radius": (0.02, 0.08, 0.01),
            "ankle_stiffness": (0.2, 1.5, 0.1),
            "ankle_damping": (0.02, 0.2, 0.02),
            "hip_kp": (10.0, 30.0, 2.0),
            "hip_kd": (2.0, 8.0, 0.5),
            "knee_kp": (5.0, 20.0, 2.0),
            "friction": (0.8, 2.0, 0.1),
        }
    elif version_key in ["V13.6", "V13.7", "V14", "V16", "V17"]:
        # FSM 版本
        scannable = {
            "base.hip_mass": (3.0, 8.0, 0.5),
            "base.foot_radius": (0.02, 0.08, 0.01),
            "base.ankle_stiffness": (0.2, 1.5, 0.1),
            "fsm.stance_early.k_PD": (10.0, 50.0, 5.0),
            "fsm.stance_early.tau_max": (2.0, 8.0, 0.5),
            "fsm.swing_thrust.k_E": (3.0, 15.0, 1.0),
            "fsm.swing_thrust.tau_max": (2.0, 8.0, 0.5),
            "fsm.swing_retract.tau_max": (1.0, 5.0, 0.5),
        }

    return scannable


def set_nested_param(params, path: str, value):
    """设置嵌套参数"""
    from dataclasses import replace

    parts = path.split(".")
    if len(parts) == 1:
        # 顶层参数
        return replace(params, **{parts[0]: value})
    else:
        # 嵌套参数
        current = params
        for i, part in enumerate(parts[:-1]):
            current = getattr(current, part)

        # 重建嵌套结构
        if parts[0] == "base":
            new_base = replace(current, **{parts[-1]: value})
            return replace(params, base=new_base)
        elif parts[0] == "fsm":
            # FSM 相位参数
            phase_name = parts[1]
            phase = getattr(params.fsm, phase_name)
            new_phase = replace(phase, **{parts[-1]: value})
            new_fsm = replace(params.fsm, **{phase_name: new_phase})
            return replace(params, fsm=new_fsm)

    return params


def run_single_sim(version_key, params):
    """运行单次仿真 (用于并行)"""
    try:
        if version_key == "V10":
            from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
                run_simulation,
            )

            result = run_simulation(params, save_prefix=None, sample_hz=160.0)
        elif version_key == "V13.6":
            from v13_6_event_driven_fsm.simulate_v13_6 import run_simulation_v136

            result = run_simulation_v136(params, save_prefix=None, sample_hz=160.0)
        elif version_key == "V16":
            from v16_motor_dynamics.simulate_v16 import run_simulation_v16

            result = run_simulation_v16(params, save_prefix=None, sample_hz=160.0)
        elif version_key == "V17":
            from v17_state_estimation.simulate_v17 import run_simulation_v17

            result = run_simulation_v17(params, save_prefix=None, sample_hz=160.0)
        else:
            return None
        return result
    except Exception as e:
        return {"success": False, "failure_reason": str(e)}


def show(version_key: str, version_info: dict):
    """显示批量扫描页面"""
    st.header("🔍 批量参数扫描")

    # 检查参数是否已加载
    if f"params_{version_key}" not in st.session_state:
        st.warning("⚠️ 请先在参数编辑页面加载参数")
        return

    base_params = st.session_state[f"params_{version_key}"]

    # 扫描类型选择
    scan_type = st.radio(
        "扫描类型",
        ["单参数扫描 (1D)", "双参数扫描 (2D)", "敏感度分析"],
        horizontal=True,
    )

    st.markdown("---")

    scannable = get_scannable_params(version_key, base_params)

    if scan_type == "单参数扫描 (1D)":
        st.subheader("📊 单参数扫描")

        col1, col2 = st.columns([2, 1])

        with col1:
            param_name = st.selectbox("选择参数", options=list(scannable.keys()))

        with col2:
            num_points = st.number_input(
                "采样点数", min_value=3, max_value=20, value=10, step=1
            )

        min_val, max_val, default_step = scannable[param_name]

        col_min, col_max = st.columns(2)
        with col_min:
            scan_min = st.number_input(
                "最小值", value=float(min_val), step=default_step
            )
        with col_max:
            scan_max = st.number_input(
                "最大值", value=float(max_val), step=default_step
            )

        if st.button("▶️ 开始扫描", type="primary"):
            values = np.linspace(scan_min, scan_max, num_points)

            progress_bar = st.progress(0)
            status_text = st.empty()

            results = []

            for i, val in enumerate(values):
                status_text.text(
                    f"正在运行 {i+1}/{num_points}: {param_name} = {val:.4f}"
                )

                # 修改参数
                test_params = set_nested_param(base_params, param_name, val)

                # 运行仿真
                result = run_single_sim(version_key, test_params)

                results.append(
                    {
                        "value": val,
                        "success": result.get("success", False) if result else False,
                        "forward_distance": (
                            result.get("forward_distance", 0) if result else 0
                        ),
                        "duration": result.get("duration", 0) if result else 0,
                        "num_touchdowns": (
                            result.get("num_touchdowns", 0) if result else 0
                        ),
                        "failure_reason": (
                            result.get("failure_reason", "") if result else "Error"
                        ),
                    }
                )

                progress_bar.progress((i + 1) / num_points)

            status_text.text("✅ 扫描完成")

            # 保存结果
            st.session_state[f"scan_1d_{version_key}"] = {
                "param_name": param_name,
                "results": results,
            }

            # 可视化
            st.markdown("---")
            st.subheader("📈 扫描结果")

            df = pd.DataFrame(results)

            fig = make_subplots(
                rows=2,
                cols=2,
                subplot_titles=("成功率", "前进距离", "触地次数", "仿真时长"),
            )

            # 成功率
            success_rate = df.groupby("value")["success"].mean()
            fig.add_trace(
                go.Scatter(
                    x=df["value"],
                    y=df["success"].astype(int),
                    mode="markers+lines",
                    name="成功",
                    line=dict(color="green"),
                ),
                row=1,
                col=1,
            )

            # 前进距离
            fig.add_trace(
                go.Scatter(
                    x=df["value"],
                    y=df["forward_distance"],
                    mode="markers+lines",
                    name="前进",
                    line=dict(color="blue"),
                ),
                row=1,
                col=2,
            )

            # 触地次数
            fig.add_trace(
                go.Scatter(
                    x=df["value"],
                    y=df["num_touchdowns"],
                    mode="markers+lines",
                    name="触地",
                    line=dict(color="orange"),
                ),
                row=2,
                col=1,
            )

            # 时长
            fig.add_trace(
                go.Scatter(
                    x=df["value"],
                    y=df["duration"],
                    mode="markers+lines",
                    name="时长",
                    line=dict(color="purple"),
                ),
                row=2,
                col=2,
            )

            fig.update_xaxes(title_text=param_name)
            fig.update_layout(height=700, showlegend=False)

            st.plotly_chart(fig, use_container_width=True)

            # 统计摘要
            col1, col2, col3 = st.columns(3)
            with col1:
                success_count = df["success"].sum()
                st.metric("成功次数", f"{success_count}/{len(df)}")
            with col2:
                max_forward = df["forward_distance"].max()
                best_val = df.loc[df["forward_distance"].idxmax(), "value"]
                st.metric(
                    "最佳前进距离",
                    f"{max_forward:.2f} m",
                    delta=f"@ {param_name}={best_val:.3f}",
                )
            with col3:
                avg_duration = df[df["success"]]["duration"].mean()
                st.metric("平均时长 (成功)", f"{avg_duration:.2f} s")

    elif scan_type == "双参数扫描 (2D)":
        st.subheader("🗺️ 双参数扫描")

        col1, col2 = st.columns(2)

        with col1:
            param1_name = st.selectbox(
                "参数 1", options=list(scannable.keys()), key="param1"
            )
            min1, max1, step1 = scannable[param1_name]
            num1 = st.slider("采样点数 1", 3, 10, 5)

        with col2:
            param2_name = st.selectbox(
                "参数 2",
                options=[k for k in scannable.keys() if k != param1_name],
                key="param2",
            )
            min2, max2, step2 = scannable[param2_name]
            num2 = st.slider("采样点数 2", 3, 10, 5)

        if st.button("▶️ 开始扫描", type="primary"):
            values1 = np.linspace(min1, max1, num1)
            values2 = np.linspace(min2, max2, num2)

            total = num1 * num2
            progress_bar = st.progress(0)
            status_text = st.empty()

            results_grid = []

            idx = 0
            for v1 in values1:
                for v2 in values2:
                    idx += 1
                    status_text.text(
                        f"运行 {idx}/{total}: {param1_name}={v1:.3f}, {param2_name}={v2:.3f}"
                    )

                    test_params = set_nested_param(base_params, param1_name, v1)
                    test_params = set_nested_param(test_params, param2_name, v2)

                    result = run_single_sim(version_key, test_params)

                    results_grid.append(
                        {
                            "param1": v1,
                            "param2": v2,
                            "success": (
                                result.get("success", False) if result else False
                            ),
                            "forward_distance": (
                                result.get("forward_distance", 0) if result else 0
                            ),
                        }
                    )

                    progress_bar.progress(idx / total)

            status_text.text("✅ 扫描完成")

            # 保存结果
            st.session_state[f"scan_2d_{version_key}"] = {
                "param1_name": param1_name,
                "param2_name": param2_name,
                "results": results_grid,
            }

            # 可视化热图
            st.markdown("---")
            st.subheader("🔥 热图可视化")

            df = pd.DataFrame(results_grid)

            # 成功率热图
            success_matrix = df.pivot_table(
                index="param2", columns="param1", values="success", aggfunc="mean"
            )

            fig_success = go.Figure(
                data=go.Heatmap(
                    z=success_matrix.values,
                    x=success_matrix.columns,
                    y=success_matrix.index,
                    colorscale="RdYlGn",
                    colorbar=dict(title="成功率"),
                )
            )
            fig_success.update_layout(
                title="成功率热图",
                xaxis_title=param1_name,
                yaxis_title=param2_name,
                height=500,
            )
            st.plotly_chart(fig_success, use_container_width=True)

            # 前进距离热图
            forward_matrix = df.pivot_table(
                index="param2",
                columns="param1",
                values="forward_distance",
                aggfunc="mean",
            )

            fig_forward = go.Figure(
                data=go.Heatmap(
                    z=forward_matrix.values,
                    x=forward_matrix.columns,
                    y=forward_matrix.index,
                    colorscale="Viridis",
                    colorbar=dict(title="前进距离 (m)"),
                )
            )
            fig_forward.update_layout(
                title="前进距离热图",
                xaxis_title=param1_name,
                yaxis_title=param2_name,
                height=500,
            )
            st.plotly_chart(fig_forward, use_container_width=True)

            # 最佳点标注
            best_row = df.loc[df["forward_distance"].idxmax()]
            st.success(
                f"最佳组合: {param1_name}={best_row['param1']:.3f}, {param2_name}={best_row['param2']:.3f} → {best_row['forward_distance']:.2f} m"
            )

    elif scan_type == "敏感度分析":
        st.subheader("📐 敏感度分析")

        st.info("对每个参数执行 ±10% 扰动，评估对仿真结果的影响")

        perturbation = st.slider("扰动幅度 (%)", 5, 30, 10)

        if st.button("▶️ 开始分析", type="primary"):
            param_names = list(scannable.keys())[:5]  # 限制分析前 5 个参数

            progress_bar = st.progress(0)
            status_text = st.empty()

            sensitivity_results = []

            for i, param_name in enumerate(param_names):
                status_text.text(f"分析参数 {i+1}/{len(param_names)}: {param_name}")

                # 基准值
                # 简化：假设可以直接获取
                base_val = (
                    scannable[param_name][0]
                    + (scannable[param_name][1] - scannable[param_name][0]) / 2
                )

                # -10%
                test_params_low = set_nested_param(
                    base_params, param_name, base_val * (1 - perturbation / 100)
                )
                result_low = run_single_sim(version_key, test_params_low)

                # +10%
                test_params_high = set_nested_param(
                    base_params, param_name, base_val * (1 + perturbation / 100)
                )
                result_high = run_single_sim(version_key, test_params_high)

                forward_low = result_low.get("forward_distance", 0) if result_low else 0
                forward_high = (
                    result_high.get("forward_distance", 0) if result_high else 0
                )

                sensitivity = abs(forward_high - forward_low) / (
                    2 * base_val * perturbation / 100
                )

                sensitivity_results.append(
                    {
                        "param": param_name,
                        "sensitivity": sensitivity,
                        "forward_low": forward_low,
                        "forward_high": forward_high,
                    }
                )

                progress_bar.progress((i + 1) / len(param_names))

            status_text.text("✅ 分析完成")

            # 可视化
            st.markdown("---")
            st.subheader("📊 敏感度排名")

            df_sens = pd.DataFrame(sensitivity_results).sort_values(
                "sensitivity", ascending=False
            )

            fig = go.Figure(
                data=go.Bar(
                    x=df_sens["param"],
                    y=df_sens["sensitivity"],
                    marker_color="steelblue",
                )
            )
            fig.update_layout(
                title="参数敏感度 (前进距离变化率)",
                xaxis_title="参数",
                yaxis_title="敏感度",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_sens, use_container_width=True)

            st.info("💡 敏感度越高，该参数对性能影响越大，需要更精细调优")

    # 导出扫描结果
    st.markdown("---")
    st.subheader("💾 导出扫描数据")

    if (
        f"scan_1d_{version_key}" in st.session_state
        or f"scan_2d_{version_key}" in st.session_state
    ):
        if st.button("📥 导出为 JSON"):
            cache_dir = Path(__file__).resolve().parent.parent / "cache"
            cache_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if f"scan_1d_{version_key}" in st.session_state:
                data = st.session_state[f"scan_1d_{version_key}"]
                filepath = cache_dir / f"{version_key}_scan_1d_{timestamp}.json"
            else:
                data = st.session_state[f"scan_2d_{version_key}"]
                filepath = cache_dir / f"{version_key}_scan_2d_{timestamp}.json"

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            st.success(f"已导出到 {filepath}")
