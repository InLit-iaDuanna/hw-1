"""仿真运行页面 - 执行仿真并显示进度"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))


def run_simulation(version_key: str, params):
    """运行仿真并返回结果"""
    try:
        if version_key == "V10":
            from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
                run_simulation,
            )

            result = run_simulation(params, save_prefix=None, sample_hz=160.0)

        elif version_key == "V13.6":
            from v13_6_event_driven_fsm.simulate_v13_6 import run_simulation_v136

            result = run_simulation_v136(params, save_prefix=None, sample_hz=160.0)

        elif version_key == "V13.7":
            from v13_7_friction_compensation.simulate_v13_7 import run_simulation_v137

            result = run_simulation_v137(params, save_prefix=None, sample_hz=160.0)

        elif version_key == "V14":
            from v14_passive_arms.simulate_passive_arms_v14 import run_simulation

            result = run_simulation(params, save_prefix=None, sample_hz=160.0)

        elif version_key == "V16":
            from v16_motor_dynamics.simulate_v16 import run_simulation_v16

            result = run_simulation_v16(params, save_prefix=None, sample_hz=160.0)

        elif version_key == "V17":
            from v17_state_estimation.simulate_v17 import run_simulation_v17

            result = run_simulation_v17(params, save_prefix=None, sample_hz=160.0)
        else:
            return None, "不支持的版本"

        return result, None
    except Exception as e:
        return None, str(e)


def save_to_history(version_key: str, result: dict):
    """保存运行历史"""
    cache_dir = Path(__file__).resolve().parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    history_file = cache_dir / f"{version_key}_history.json"

    # 读取现有历史
    if history_file.exists():
        with open(history_file, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {"runs": []}

    # 添加新记录
    history["runs"].append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": result.get("success", False),
            "duration": result.get("duration", 0),
            "forward_distance": result.get("forward_distance", 0),
            "failure_reason": result.get("failure_reason", ""),
            "num_touchdowns": result.get("num_touchdowns", 0),
        }
    )

    # 只保留最近 50 次
    history["runs"] = history["runs"][-50:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def show(version_key: str, version_info: dict):
    """显示仿真运行页面"""
    st.header("▶️ 运行仿真")

    # 检查参数是否已加载
    if f"params_{version_key}" not in st.session_state:
        st.warning("⚠️ 请先在参数编辑页面加载或编辑参数")
        return

    params = st.session_state[f"params_{version_key}"]

    # 仿真配置
    st.subheader("⚙️ 仿真配置")

    col1, col2, col3 = st.columns(3)

    with col1:
        # 从参数中读取默认值
        if hasattr(params, "duration"):
            default_duration = params.duration
        elif hasattr(params, "base") and hasattr(params.base, "duration"):
            default_duration = params.base.duration
        else:
            default_duration = 12.0

        duration = st.number_input(
            "仿真时长 (秒)",
            min_value=1.0,
            max_value=30.0,
            value=float(default_duration),
            step=1.0,
        )

    with col2:
        sample_hz = st.number_input(
            "采样频率 (Hz)", min_value=50.0, max_value=500.0, value=160.0, step=10.0
        )

    with col3:
        save_results = st.checkbox("保存结果到文件", value=False)

    st.markdown("---")

    # 运行按钮
    col_run, col_stop = st.columns([1, 3])

    with col_run:
        run_button = st.button("▶️ 开始仿真", type="primary", use_container_width=True)

    if run_button:
        # 更新参数中的 duration
        if hasattr(params, "duration"):
            from dataclasses import replace

            params = replace(params, duration=duration)
        elif hasattr(params, "base"):
            from dataclasses import replace

            params = replace(params, base=replace(params.base, duration=duration))

        st.session_state[f"params_{version_key}"] = params

        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("🔧 正在构建模型...")
        progress_bar.progress(10)
        time.sleep(0.5)

        status_text.text("⚙️ 正在初始化仿真...")
        progress_bar.progress(20)
        time.sleep(0.5)

        status_text.text("🏃 正在运行仿真...")
        progress_bar.progress(30)

        # 执行仿真
        start_time = time.time()
        result, error = run_simulation(version_key, params)
        elapsed = time.time() - start_time

        progress_bar.progress(100)

        if error:
            status_text.text("❌ 仿真失败")
            st.error(f"仿真错误: {error}")
        else:
            status_text.text("✅ 仿真完成")

            # 保存结果到会话
            st.session_state[f"result_{version_key}"] = result

            # 保存到历史
            save_to_history(version_key, result)

            # 显示结果摘要
            st.markdown("---")
            st.subheader("📊 仿真结果")

            success = result.get("success", False)

            if success:
                st.markdown(
                    """
                <div class="success-box">
                    <h3>✅ 仿真成功！</h3>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                <div class="error-box">
                    <h3>❌ 仿真失败</h3>
                    <p><strong>失败原因:</strong> {result.get('failure_reason', 'Unknown')}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # 指标卡片
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("仿真时长", f"{result.get('duration', 0):.2f} s", delta=None)

            with col2:
                st.metric(
                    "前进距离",
                    f"{result.get('forward_distance', 0):.2f} m",
                    delta=(
                        "达标" if result.get("forward_distance", 0) > 0.8 else "未达标"
                    ),
                )

            with col3:
                st.metric(
                    "触地次数",
                    f"{result.get('num_touchdowns', 0)}",
                    delta="达标" if result.get("num_touchdowns", 0) >= 10 else "未达标",
                )

            with col4:
                st.metric("计算时间", f"{elapsed:.2f} s", delta=None)

            # 额外指标
            if "final_energy" in result:
                st.info(f"最终能量: {result['final_energy']:.2f} J")

            if "peak_torque_hip" in result:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.metric("峰值髋力矩", f"{result['peak_torque_hip']:.2f} Nm")
                with col_t2:
                    st.metric(
                        "峰值膝力矩", f"{result.get('peak_torque_knee', 0):.2f} Nm"
                    )

            # 快速可视化预览
            if "trajectory" in result and len(result["trajectory"]) > 0:
                st.markdown("---")
                st.subheader("📈 快速预览")

                import pandas as pd
                import plotly.graph_objects as go

                traj = result["trajectory"]
                df = pd.DataFrame(traj)

                # 髋部轨迹
                fig_traj = go.Figure()
                fig_traj.add_trace(
                    go.Scatter(
                        x=df["hip_x"],
                        y=df["hip_z"],
                        mode="lines",
                        name="髋部轨迹",
                        line=dict(color="blue", width=2),
                    )
                )

                fig_traj.update_layout(
                    title="髋部轨迹 (x-z 平面)",
                    xaxis_title="前进方向 (m)",
                    yaxis_title="高度 (m)",
                    height=400,
                    hovermode="closest",
                )

                st.plotly_chart(fig_traj, use_container_width=True)

                st.info("💡 前往 '📈 结果分析' 页面查看完整分析")

            # 保存选项
            if save_results:
                cache_dir = Path(__file__).resolve().parent.parent / "cache"
                cache_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = cache_dir / f"{version_key}_result_{timestamp}.json"

                # 转换 numpy 类型为 Python 原生类型
                def convert_types(obj):
                    if isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, dict):
                        return {k: convert_types(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_types(item) for item in obj]
                    return obj

                result_serializable = convert_types(result)

                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(result_serializable, f, indent=2, ensure_ascii=False)

                st.success(f"结果已保存到 {result_file}")

    # 显示历史运行
    st.markdown("---")
    st.subheader("📜 本次会话历史")

    if f"result_{version_key}" in st.session_state:
        result = st.session_state[f"result_{version_key}"]

        st.json(
            {
                "成功": result.get("success", False),
                "时长": f"{result.get('duration', 0):.2f} s",
                "前进": f"{result.get('forward_distance', 0):.2f} m",
                "触地": result.get("num_touchdowns", 0),
                "失败原因": result.get("failure_reason", "N/A"),
            }
        )
    else:
        st.info("暂无运行结果")
