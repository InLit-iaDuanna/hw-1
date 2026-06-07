"""参数编辑器页面 - 使用滑块和输入框调整参数。"""

import sys
from dataclasses import replace
from pathlib import Path

import streamlit as st
import yaml

HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))

# 导入版本模块
from parameter_tuner.version_adapter import get_version_adapter

st.set_page_config(page_title="参数编辑器", page_icon="⚙️", layout="wide")

st.title("⚙️ 参数编辑器")

# 获取当前版本
version = st.session_state.get("version", "V13.7")
adapter = get_version_adapter(version)

st.info(f"当前版本: {version}")

# 初始化参数
if f"params_{version}" not in st.session_state:
    st.session_state[f"params_{version}"] = adapter.get_default_params()

params = st.session_state[f"params_{version}"]

st.markdown("---")

# 参数分类显示
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🦿 机械参数", "🎮 控制参数", "⚡ 电机参数", "🔧 仿真设置", "💾 导入/导出"]
)

with tab1:
    st.header("机械参数")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("身体质量与几何")

        param_specs = adapter.get_param_specs()
        mechanical_params = param_specs.get("mechanical", {})

        for param_name, spec in mechanical_params.items():
            if (
                hasattr(params, param_name)
                if version != "V13.7"
                else hasattr(params.base, param_name)
            ):
                current_val = (
                    getattr(params, param_name)
                    if version != "V13.7"
                    else getattr(params.base, param_name)
                )

                new_val = st.slider(
                    spec["label"],
                    min_value=spec["min"],
                    max_value=spec["max"],
                    value=float(current_val),
                    step=spec["step"],
                    help=spec.get("help", ""),
                    key=f"mech_{param_name}",
                )

                # 更新参数
                if version == "V13.7":
                    if new_val != current_val:
                        st.session_state[f"params_{version}"] = replace(
                            params, base=replace(params.base, **{param_name: new_val})
                        )
                else:
                    if new_val != current_val:
                        st.session_state[f"params_{version}"] = replace(
                            params, **{param_name: new_val}
                        )

with tab2:
    st.header("控制参数")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("PD增益")
        control_params = adapter.get_param_specs().get("control", {})

        for param_name, spec in control_params.items():
            if (
                hasattr(params, param_name)
                if version != "V13.7"
                else hasattr(params.base, param_name)
            ):
                current_val = (
                    getattr(params, param_name)
                    if version != "V13.7"
                    else getattr(params.base, param_name)
                )

                new_val = st.slider(
                    spec["label"],
                    min_value=spec["min"],
                    max_value=spec["max"],
                    value=float(current_val),
                    step=spec["step"],
                    help=spec.get("help", ""),
                    key=f"ctrl_{param_name}",
                )

                if version == "V13.7":
                    if new_val != current_val:
                        st.session_state[f"params_{version}"] = replace(
                            params, base=replace(params.base, **{param_name: new_val})
                        )
                else:
                    if new_val != current_val:
                        st.session_state[f"params_{version}"] = replace(
                            params, **{param_name: new_val}
                        )

with tab3:
    st.header("电机参数")

    if version in ["V13.7", "V16", "V17"]:
        st.subheader("电机预设选择")

        motor_presets = ["mx64ar", "ec_i40_53", "ideal"]
        current_motor = (
            params.hip_motor.name.split()[0].lower().replace("-", "").replace("_", "")
        )

        # 尝试匹配当前电机
        motor_index = 0
        for i, preset in enumerate(motor_presets):
            if preset.replace("_", "") in current_motor:
                motor_index = i
                break

        motor_preset = st.selectbox(
            "髋关节电机预设",
            motor_presets,
            index=motor_index,
            format_func=lambda x: {
                "mx64ar": "MX-64AR (默认)",
                "ec_i40_53": "Maxon EC-i 40 + GP32",
                "ideal": "理想电机 (无摩擦/惯量)",
            }[x],
            key="motor_hip_preset",
        )

        knee_motor_preset = st.selectbox(
            "膝关节电机预设",
            motor_presets,
            index=motor_index,
            format_func=lambda x: {
                "mx64ar": "MX-64AR (默认)",
                "ec_i40_53": "Maxon EC-i 40 + GP32",
                "ideal": "理想电机 (无摩擦/惯量)",
            }[x],
            key="motor_knee_preset",
        )

        # 应用电机预设
        from common.motor_dynamics import PRESETS as MOTOR_PRESETS

        if motor_preset != motor_index or knee_motor_preset != motor_index:
            st.session_state[f"params_{version}"] = replace(
                params,
                hip_motor=MOTOR_PRESETS[motor_preset],
                knee_motor=MOTOR_PRESETS[knee_motor_preset],
            )

        # 显示电机参数
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**髋关节电机**")
            st.write(f"- Kt: {params.hip_motor.Kt:.4f} N·m/A")
            st.write(f"- N: {params.hip_motor.N:.1f}")
            st.write(f"- η: {params.hip_motor.eta:.2f}")
            st.write(f"- τ_max: {params.hip_motor.joint_tau_sat_peak():.2f} N·m")

        with col2:
            st.markdown("**膝关节电机**")
            st.write(f"- Kt: {params.knee_motor.Kt:.4f} N·m/A")
            st.write(f"- N: {params.knee_motor.N:.1f}")
            st.write(f"- η: {params.knee_motor.eta:.2f}")
            st.write(f"- τ_max: {params.knee_motor.joint_tau_sat_peak():.2f} N·m")

        # 摩擦补偿开关
        if version in ["V13.7", "V17"]:
            compensate = st.checkbox(
                "启用摩擦补偿",
                value=params.compensate_friction,
                help="前馈补偿库仑摩擦",
            )
            if compensate != params.compensate_friction:
                st.session_state[f"params_{version}"] = replace(
                    params, compensate_friction=compensate
                )
    else:
        st.info("此版本不支持电机参数调整")

with tab4:
    st.header("仿真设置")

    sim_params = adapter.get_param_specs().get("simulation", {})

    for param_name, spec in sim_params.items():
        if (
            hasattr(params, param_name)
            if version != "V13.7"
            else hasattr(params.base, param_name)
        ):
            current_val = (
                getattr(params, param_name)
                if version != "V13.7"
                else getattr(params.base, param_name)
            )

            new_val = st.slider(
                spec["label"],
                min_value=spec["min"],
                max_value=spec["max"],
                value=float(current_val),
                step=spec["step"],
                help=spec.get("help", ""),
                key=f"sim_{param_name}",
            )

            if version == "V13.7":
                if new_val != current_val:
                    st.session_state[f"params_{version}"] = replace(
                        params, base=replace(params.base, **{param_name: new_val})
                    )
            else:
                if new_val != current_val:
                    st.session_state[f"params_{version}"] = replace(
                        params, **{param_name: new_val}
                    )

with tab5:
    st.header("参数导入/导出")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("导出参数")

        yaml_data = adapter.params_to_yaml(st.session_state[f"params_{version}"])

        st.download_button(
            label="📥 下载 YAML",
            data=yaml_data,
            file_name=f"{version.lower()}_custom_params.yaml",
            mime="text/yaml",
        )

        with st.expander("预览 YAML"):
            st.code(yaml_data, language="yaml")

    with col2:
        st.subheader("导入参数")

        uploaded_file = st.file_uploader("上传 YAML 配置", type=["yaml", "yml"])

        if uploaded_file is not None:
            try:
                config = yaml.safe_load(uploaded_file)
                imported_params = adapter.yaml_to_params(config)

                st.success("✅ 参数导入成功")

                if st.button("应用导入的参数"):
                    st.session_state[f"params_{version}"] = imported_params
                    st.session_state.params_modified = True
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 导入失败: {e}")

# 底部操作按钮
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔄 重置为默认值", use_container_width=True):
        st.session_state[f"params_{version}"] = adapter.get_default_params()
        st.session_state.params_modified = False
        st.rerun()

with col2:
    if st.button("✅ 应用参数", use_container_width=True, type="primary"):
        st.session_state.params_modified = True
        st.success("参数已应用，可以进入仿真运行器执行仿真")

with col3:
    st.info(f"当前参数状态: {'已修改' if st.session_state.params_modified else '默认'}")
