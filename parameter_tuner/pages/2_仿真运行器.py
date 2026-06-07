"""仿真运行器页面 - 执行仿真并显示实时进度。"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))

from parameter_tuner.version_adapter import get_version_adapter

st.set_page_config(page_title="仿真运行器", page_icon="▶️", layout="wide")

st.title("▶️ 仿真运行器")

version = st.session_state.get("version", "V13.7")
adapter = get_version_adapter(version)

st.info(f"当前版本: {version}")

# 检查参数是否已配置
if f"params_{version}" not in st.session_state:
    st.warning("⚠️ 请先在参数编辑器中配置参数")
    st.stop()

params = st.session_state[f"params_{version}"]

st.markdown("---")

# 仿真配置
col1, col2 = st.columns(2)

with col1:
    st.subheader("仿真配置")

    save_prefix = st.text_input(
        "结果文件前缀",
        value=f"tuner_{version.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="仿真结果将保存为 {prefix}.csv 和 {prefix}.json",
    )

    sample_hz = st.number_input(
        "采样频率 (Hz)",
        min_value=10.0,
        max_value=1000.0,
        value=160.0,
        step=10.0,
        help="数据记录频率",
    )

with col2:
    st.subheader("当前参数摘要")

    summary = adapter.get_param_summary(params)
    for key, value in summary.items():
        st.write(f"**{key}**: {value}")

st.markdown("---")

# 运行仿真按钮
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    run_button = st.button("🚀 运行仿真", use_container_width=True, type="primary")

with col2:
    if st.session_state.get("simulation_running", False):
        if st.button("⏹️ 停止", use_container_width=True):
            st.session_state.simulation_running = False
            st.warning("仿真已取消")

with col3:
    show_log = st.checkbox("显示详细日志", value=False)

# 运行仿真
if run_button:
    st.session_state.simulation_running = True
    st.session_state.simulation_complete = False

    # 创建临时参数文件
    temp_dir = HW1_ROOT / "parameter_tuner" / "temp"
    temp_dir.mkdir(exist_ok=True)

    config_path = temp_dir / f"{save_prefix}_config.yaml"
    yaml_data = adapter.params_to_yaml(params)
    config_path.write_text(yaml_data, encoding="utf-8")

    st.info(f"📝 参数已保存到: {config_path}")

    # 准备运行命令
    python_exe = HW1_ROOT / ".venv-mujoco" / "Scripts" / "python.exe"
    script_path = adapter.get_simulation_script()

    # 构建命令
    cmd = [
        str(python_exe),
        str(script_path),
        "--save-prefix",
        save_prefix,
        "--sample-hz",
        str(sample_hz),
    ]

    # 添加版本特定参数
    cmd.extend(adapter.get_simulation_args(params))

    st.code(" ".join(cmd), language="bash")

    # 执行仿真
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.expander("运行日志", expanded=show_log)

    try:
        status_text.text("🔄 初始化仿真...")

        with log_container:
            log_area = st.empty()
            log_lines = []

        # 运行进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(script_path.parent),
        )

        # 读取输出
        start_time = time.time()
        last_update = start_time

        for line in process.stdout:
            if not st.session_state.get("simulation_running", True):
                process.terminate()
                break

            log_lines.append(line.strip())

            # 每0.5秒更新一次日志显示
            current_time = time.time()
            if current_time - last_update > 0.5:
                with log_container:
                    log_area.code("\n".join(log_lines[-50:]))  # 只显示最后50行
                last_update = current_time

            # 解析进度
            if "t=" in line or "step" in line.lower():
                # 尝试估计进度
                elapsed = current_time - start_time
                duration = getattr(
                    params.base if version == "V13.7" else params, "duration", 12.0
                )

                # 简单估计：假设仿真时间与实际时间成比例
                progress = min(elapsed / (duration * 0.5), 0.95)  # 最多显示95%
                progress_bar.progress(progress)
                status_text.text(f"🔄 仿真运行中... ({elapsed:.1f}s)")

        process.wait()

        # 检查结果
        if process.returncode == 0:
            progress_bar.progress(1.0)
            status_text.text("✅ 仿真完成")

            # 查找结果文件
            out_dir = script_path.parent / "out"
            result_csv = out_dir / f"{save_prefix}.csv"
            result_json = out_dir / f"{save_prefix}.json"

            if result_csv.exists():
                st.session_state.results_path = result_csv
                st.session_state.simulation_complete = True
                st.success(f"✅ 仿真成功完成！结果保存至: {result_csv}")

                # 显示结果摘要
                if result_json.exists():
                    with open(result_json) as f:
                        result_data = json.load(f)

                    st.subheader("仿真结果摘要")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("状态", result_data.get("status", "unknown"))
                    with col2:
                        st.metric("仿真时间", f"{result_data.get('t_end', 0):.2f} s")
                    with col3:
                        st.metric("前进距离", f"{result_data.get('forward', 0):.2f} m")
            else:
                st.error("❌ 未找到结果文件")
        else:
            st.error(f"❌ 仿真失败 (退出码: {process.returncode})")
            with log_container:
                log_area.code("\n".join(log_lines))

    except Exception as e:
        st.error(f"❌ 运行出错: {e}")
        st.exception(e)

    finally:
        st.session_state.simulation_running = False

# 显示历史运行
st.markdown("---")
st.subheader("历史运行记录")

out_dir = HW1_ROOT / adapter.get_simulation_script().parent / "out"
if out_dir.exists():
    json_files = sorted(
        out_dir.glob("tuner_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if json_files:
        for json_file in json_files[:10]:  # 显示最近10次
            with open(json_file) as f:
                data = json.load(f)

            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])

            with col1:
                st.text(json_file.stem)
            with col2:
                st.text(f"状态: {data.get('status', 'unknown')}")
            with col3:
                st.text(f"时间: {data.get('t_end', 0):.2f}s")
            with col4:
                st.text(f"前进: {data.get('forward', 0):.2f}m")
            with col5:
                csv_file = json_file.with_suffix(".csv")
                if csv_file.exists() and st.button("📊", key=f"view_{json_file.stem}"):
                    st.session_state.results_path = csv_file
                    st.session_state.simulation_complete = True
    else:
        st.info("暂无历史记录")
else:
    st.info("输出目录不存在")
