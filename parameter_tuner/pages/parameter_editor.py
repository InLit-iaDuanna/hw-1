"""参数编辑页面 - 支持多版本参数配置"""

import sys
from dataclasses import asdict, fields
from pathlib import Path

import streamlit as st
import yaml

# 添加项目路径
HW1_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HW1_ROOT))


def load_default_params(version_key: str):
    """加载版本的默认参数"""
    try:
        if version_key == "V10":
            from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
                RollingFootParams,
            )

            return RollingFootParams()
        elif version_key == "V13.6":
            from v13_6_event_driven_fsm.simulate_v13_6 import V136Params

            return V136Params()
        elif version_key == "V13.7":
            from v13_7_friction_compensation.simulate_v13_7 import V137Params

            return V137Params()
        elif version_key == "V14":
            from v14_passive_arms.simulate_passive_arms_v14 import PassiveArmsParams

            return PassiveArmsParams()
        elif version_key == "V16":
            from v14c_arm_mass_lightening.simulate_v14c import make_v14c_params
            from v16_motor_dynamics.simulate_v16 import (
                PassiveArmsParams,
                V16Params,
            )

            base = PassiveArmsParams()
            fsm = make_v14c_params(base)
            return V16Params(base=base, fsm=fsm)
        elif version_key == "V17":
            from v17_state_estimation.simulate_v17 import (
                PassiveArmsParams,
                V17Params,
                make_v17_fsm,
            )

            base = PassiveArmsParams()
            fsm = make_v17_fsm(base)
            return V17Params(base=base, fsm=fsm)
    except Exception as e:
        st.error(f"加载默认参数失败: {e}")
        return None


def render_param_editor(params, prefix=""):
    """递归渲染参数编辑器"""
    if hasattr(params, "__dataclass_fields__"):
        # 是 dataclass
        edited = {}
        for field in fields(params):
            field_name = field.name
            field_value = getattr(params, field_name)
            field_type = field.type

            full_key = f"{prefix}.{field_name}" if prefix else field_name

            # 递归处理嵌套 dataclass
            if hasattr(field_value, "__dataclass_fields__"):
                with st.expander(f"📦 {field_name}", expanded=False):
                    edited[field_name] = render_param_editor(field_value, full_key)
            else:
                # 基础类型参数
                if isinstance(field_value, bool):
                    edited[field_name] = st.checkbox(
                        field_name, value=field_value, key=full_key
                    )
                elif isinstance(field_value, int):
                    edited[field_name] = st.number_input(
                        field_name, value=field_value, step=1, key=full_key
                    )
                elif isinstance(field_value, float):
                    # 根据参数名推断合理范围
                    if "mass" in field_name.lower():
                        min_val, max_val = 0.0, 20.0
                        step = 0.1
                    elif (
                        "length" in field_name.lower() or "height" in field_name.lower()
                    ):
                        min_val, max_val = 0.0, 2.0
                        step = 0.01
                    elif "radius" in field_name.lower():
                        min_val, max_val = 0.0, 0.2
                        step = 0.001
                    elif (
                        "stiffness" in field_name.lower() or "_k" in field_name.lower()
                    ):
                        min_val, max_val = 0.0, 100.0
                        step = 0.1
                    elif "damping" in field_name.lower() or "_d" in field_name.lower():
                        min_val, max_val = 0.0, 20.0
                        step = 0.01
                    elif "deg" in field_name.lower():
                        min_val, max_val = -180.0, 180.0
                        step = 1.0
                    elif "friction" in field_name.lower():
                        min_val, max_val = 0.0, 3.0
                        step = 0.05
                    elif "torque" in field_name.lower() or "tau" in field_name.lower():
                        min_val, max_val = 0.0, 50.0
                        step = 0.5
                    else:
                        min_val, max_val = None, None
                        step = 0.01

                    if min_val is not None:
                        edited[field_name] = st.slider(
                            field_name,
                            min_value=min_val,
                            max_value=max_val,
                            value=float(field_value),
                            step=step,
                            key=full_key,
                        )
                    else:
                        edited[field_name] = st.number_input(
                            field_name,
                            value=float(field_value),
                            step=step,
                            key=full_key,
                            format="%.6f",
                        )
                elif isinstance(field_value, str):
                    edited[field_name] = st.text_input(
                        field_name, value=field_value, key=full_key
                    )
                elif isinstance(field_value, tuple):
                    st.text(f"{field_name}: {field_value} (tuple, 不可编辑)")
                    edited[field_name] = field_value
                else:
                    st.text(
                        f"{field_name}: {field_value} (类型 {type(field_value).__name__})"
                    )
                    edited[field_name] = field_value

        # 重建 dataclass
        return type(params)(**edited)
    else:
        return params


def show(version_key: str, version_info: dict):
    """显示参数编辑页面"""
    st.header("⚙️ 参数编辑器")

    # 初始化会话状态
    if f"params_{version_key}" not in st.session_state:
        st.session_state[f"params_{version_key}"] = load_default_params(version_key)

    params = st.session_state[f"params_{version_key}"]

    if params is None:
        st.error(f"无法加载 {version_key} 的参数")
        return

    # 操作按钮行
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 重置为默认", use_container_width=True):
            st.session_state[f"params_{version_key}"] = load_default_params(version_key)
            st.rerun()

    with col2:
        if st.button("📥 从文件加载", use_container_width=True):
            st.session_state["show_load_dialog"] = True

    with col3:
        if st.button("💾 保存到文件", use_container_width=True):
            st.session_state["show_save_dialog"] = True

    with col4:
        if st.button("📋 复制为 JSON", use_container_width=True):
            st.session_state["show_json_dialog"] = True

    st.markdown("---")

    # 参数分组显示
    if version_key in ["V16", "V17"]:
        # 复杂嵌套结构
        tab1, tab2, tab3, tab4 = st.tabs(
            ["🏃 基础参数", "🧠 FSM 控制", "⚡ 电机参数", "🔧 高级设置"]
        )

        with tab1:
            st.subheader("基础机械参数")
            params.base = render_param_editor(params.base, f"params_{version_key}.base")

        with tab2:
            st.subheader("FSM 控制律参数")
            st.info("4 相位事件驱动状态机")
            params.fsm = render_param_editor(params.fsm, f"params_{version_key}.fsm")

        with tab3:
            st.subheader("电机动力学参数")
            col_hip, col_knee = st.columns(2)

            with col_hip:
                st.markdown("**髋关节电机**")
                # 电机预设选择
                from v16_motor_dynamics.simulate_v16 import MOTOR_PRESETS

                motor_names = list(MOTOR_PRESETS.keys())
                current_hip_name = (
                    params.hip_motor.name
                    if hasattr(params.hip_motor, "name")
                    else motor_names[0]
                )

                selected_hip = st.selectbox(
                    "髋电机预设",
                    motor_names,
                    index=(
                        motor_names.index(current_hip_name)
                        if current_hip_name in motor_names
                        else 0
                    ),
                    key=f"params_{version_key}.hip_motor_preset",
                )

                if selected_hip != current_hip_name:
                    params.hip_motor = MOTOR_PRESETS[selected_hip]

                st.json(
                    {
                        "名称": params.hip_motor.name,
                        "力矩常数 Kt": f"{params.hip_motor.Kt:.4f}",
                        "减速比 N": params.hip_motor.N,
                        "最大电流 I_max": f"{params.hip_motor.I_max:.2f} A",
                        "峰值力矩": f"{params.hip_motor.joint_tau_sat_peak():.2f} Nm",
                    }
                )

            with col_knee:
                st.markdown("**膝关节电机**")
                current_knee_name = (
                    params.knee_motor.name
                    if hasattr(params.knee_motor, "name")
                    else motor_names[0]
                )

                selected_knee = st.selectbox(
                    "膝电机预设",
                    motor_names,
                    index=(
                        motor_names.index(current_knee_name)
                        if current_knee_name in motor_names
                        else 0
                    ),
                    key=f"params_{version_key}.knee_motor_preset",
                )

                if selected_knee != current_knee_name:
                    params.knee_motor = MOTOR_PRESETS[selected_knee]

                st.json(
                    {
                        "名称": params.knee_motor.name,
                        "力矩常数 Kt": f"{params.knee_motor.Kt:.4f}",
                        "减速比 N": params.knee_motor.N,
                        "最大电流 I_max": f"{params.knee_motor.I_max:.2f} A",
                        "峰值力矩": f"{params.knee_motor.joint_tau_sat_peak():.2f} Nm",
                    }
                )

        with tab4:
            if version_key == "V16":
                st.subheader("摩擦补偿")
                params.compensate_friction = st.checkbox(
                    "启用库仑摩擦补偿",
                    value=params.compensate_friction,
                    key=f"params_{version_key}.compensate_friction",
                )
            elif version_key == "V17":
                st.subheader("传感器与状态估计")
                col_comp, col_noise = st.columns(2)

                with col_comp:
                    params.compensate_friction = st.checkbox(
                        "启用库仑摩擦补偿",
                        value=params.compensate_friction,
                        key=f"params_{version_key}.compensate_friction",
                    )

                with col_noise:
                    st.markdown("**传感器噪声**")
                    params.sensor_noise = render_param_editor(
                        params.sensor_noise, f"params_{version_key}.sensor_noise"
                    )

    elif version_key == "V13.6":
        tab1, tab2 = st.tabs(["🏃 基础参数", "🧠 FSM 相位"])

        with tab1:
            st.subheader("基础机械参数")
            params.base = render_param_editor(params.base, f"params_{version_key}.base")

        with tab2:
            st.subheader("4 相位参数")
            st.info("stance_early → stance_late → swing_thrust → swing_retract")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Stance Early** (支撑前期)")
                params.stance_early = render_param_editor(
                    params.stance_early, f"params_{version_key}.stance_early"
                )

                st.markdown("**Swing Thrust** (摆动推进)")
                params.swing_thrust = render_param_editor(
                    params.swing_thrust, f"params_{version_key}.swing_thrust"
                )

            with col2:
                st.markdown("**Stance Late** (支撑后期)")
                params.stance_late = render_param_editor(
                    params.stance_late, f"params_{version_key}.stance_late"
                )

                st.markdown("**Swing Retract** (摆动收缩)")
                params.swing_retract = render_param_editor(
                    params.swing_retract, f"params_{version_key}.swing_retract"
                )

    else:
        # 简单参数结构 (V10, V13.7, V14)
        st.subheader("参数列表")
        params = render_param_editor(params, f"params_{version_key}")

    # 更新会话状态
    st.session_state[f"params_{version_key}"] = params

    # 对话框处理
    if st.session_state.get("show_save_dialog"):
        with st.expander("💾 保存参数", expanded=True):
            filename = st.text_input(
                "文件名", value=f"{version_key}_custom_params.yaml"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("确认保存"):
                    try:
                        cache_dir = Path(__file__).resolve().parent.parent / "cache"
                        cache_dir.mkdir(exist_ok=True)
                        filepath = cache_dir / filename

                        # 转换为字典
                        params_dict = asdict(params)

                        with open(filepath, "w", encoding="utf-8") as f:
                            yaml.dump(
                                params_dict,
                                f,
                                default_flow_style=False,
                                allow_unicode=True,
                            )

                        st.success(f"参数已保存到 {filepath}")
                        st.session_state["show_save_dialog"] = False
                    except Exception as e:
                        st.error(f"保存失败: {e}")

            with col2:
                if st.button("取消"):
                    st.session_state["show_save_dialog"] = False

    if st.session_state.get("show_json_dialog"):
        with st.expander("📋 JSON 格式", expanded=True):
            params_dict = asdict(params)
            st.json(params_dict)

            if st.button("关闭"):
                st.session_state["show_json_dialog"] = False
