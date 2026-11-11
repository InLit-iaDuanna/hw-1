from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = ROOT / "out"


VERSION_META = {
    "v01": (
        "V1 MuJoCo 指南针步态",
        "早期 MuJoCo 指南针模型，用来观察髋部位移、腿角和脚端几何轨迹。",
    ),
    "v02": (
        "V2 Rimless 极限环对照",
        "无膝轮足/rimless wheel 对照，用来说明极限环步态的离散碰撞和周期相位。",
    ),
    "v03": (
        "V3 指南针极限环数据",
        "指南针步态的数学/参数化对照版本，用 Poincare 误差观察周期收敛趋势。",
    ),
    "v04": (
        "V4 带膝极限环对照",
        "加入大腿、小腿、膝关节变量的带膝对照版本，用来解释 MVE 机构升级。",
    ),
    "v05": (
        "V5 混合动力学证明版",
        "最终的纯被动极限环证明层：连续单支撑动力学、触地事件、碰撞换腿、Poincare 收敛。",
    ),
    "v06": (
        "V6 MVE 作业表达版",
        "作业展示层：把被动步态机制转译成带膝 MVE 机械单元和分相动作。",
    ),
    "v07": (
        "V7 真实接触探索版",
        "MuJoCo 真实接触纯被动探索层，用来说明真实接触下参数很敏感。",
    ),
    "v08": (
        "V8 准被动补能探索版",
        "弱髋部补能探索层：不是纯被动，用最小输入补偿碰撞损失，但当前最佳结果仍会跌倒。",
    ),
    "v09": (
        "V9 仿生准被动稳定版",
        "稳定仿生展示层：髋/膝小力矩补能，真实接触中完成长时间交替行走。",
    ),
}

PARAM_JSONS = {
    "v01": REPO / "v01_mujoco_compass_gait/out/best_params.json",
    "v02": REPO / "v02_rugged_rimless_limit_cycle/out/rimless_params.json",
    "v03": REPO / "v03_compass_limit_cycle/out/compass_params.json",
    "v04": REPO / "v04_kneed_limit_cycle/out/kneed_limit_cycle_params.json",
    "v05": REPO / "v05_hybrid_compass_proof/out/hybrid_compass_params.json",
    "v06": REPO / "v06_mve_gait_homework/out/v6_params.json",
    "v07": REPO / "v07_true_contact_exploration/out/v7_best_params.json",
    "v08": REPO / "v08_quasi_passive_assisted/out/debug_v8_fast10_summary.json",
    "v09": REPO / "v09_stable_biomimetic_gait/out/v9_best_params.json",
}


def load_table(path: Path) -> tuple[list[str], list[dict[str, float | str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, float | str]] = []
        for row in reader:
            parsed: dict[str, float | str] = {}
            for key, value in row.items():
                if value is None or value == "":
                    parsed[key] = ""
                    continue
                try:
                    parsed[key] = float(value)
                except ValueError:
                    parsed[key] = value
            rows.append(parsed)
        return reader.fieldnames or [], rows


def finite_values(rows: list[dict[str, float | str]], name: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(name)
        if isinstance(value, (int, float)) and math.isfinite(value):
            values.append(float(value))
    return values


def stat_range(rows: list[dict[str, float | str]], name: str) -> str | None:
    values = finite_values(rows, name)
    if not values:
        return None
    return f"{min(values):.3f} 到 {max(values):.3f}"


def first_last_delta(rows: list[dict[str, float | str]], name: str) -> float | None:
    values = finite_values(rows, name)
    if len(values) < 2:
        return None
    return values[-1] - values[0]


def count_contact_segments(rows: list[dict[str, float | str]], name: str) -> int | None:
    values = finite_values(rows, name)
    if not values:
        return None
    count = 0
    prev = False
    for value in values:
        active = value > 0.5
        if active and not prev:
            count += 1
        prev = active
    return count


def count_discrete_changes(rows: list[dict[str, float | str]], name: str) -> int | None:
    values = finite_values(rows, name)
    if len(values) < 2:
        return None
    count = 0
    prev = values[0]
    for value in values[1:]:
        if value != prev:
            count += 1
            prev = value
    return count


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def fmt(value, unit: str = "") -> str:
    if value is None:
        return "无数据"
    if isinstance(value, float):
        return f"{value:.3f}{unit}"
    return f"{value}{unit}"


def version_verdict(version: str, params: dict) -> str:
    if version == "v05":
        err = params.get("final_speed_error")
        steps = params.get("valid_touchdowns") or params.get("steps")
        return (
            f"这一版可以作为纯被动极限环证明材料。参数文件记录 valid_touchdowns={steps}，"
            f"final_speed_error={fmt(err)}，且 no_actuators={params.get('no_actuators')}、"
            f"no_reward_function={params.get('no_reward_function')}。"
        )
    if version in {"v08", "v09"}:
        return (
            f"这一版不能说成纯被动。参数文件记录 quasi_passive={params.get('quasi_passive')}，"
            f"uses_reward_function={params.get('uses_reward_function')}，主动输入能量约 "
            f"{fmt(params.get('active_input_energy_j'), ' J')}。它适合解释生物式最小补能。"
        )
    if version == "v07":
        return (
            f"这一版是纯被动真实接触探索，no_actuators={params.get('no_actuators')}，"
            f"但最佳结果 failure={params.get('failure')}，说明仅靠接触和重力很难稳定多步。"
        )
    if version == "v06":
        return "这一版主要用于作业表达和机构解释，不把 MuJoCo 回放本身当作极限环证明。"
    return "这一版主要是中间建模/对照材料，适合说明模型演进，不建议单独作为最终证明。"


def build_markdown(version: str) -> str:
    title, role = VERSION_META[version]
    csv_path = OUT / version / f"{version}_data_table.csv"
    report_path = OUT / version / f"{version}_report.png"
    report_link = report_path.as_posix()
    header, rows = load_table(csv_path)
    params = load_json(PARAM_JSONS[version])

    time_values = finite_values(rows, "time")
    duration = (max(time_values) - min(time_values)) if time_values else None
    hip_delta = first_last_delta(rows, "hip_x")
    hip_range = stat_range(rows, "hip_x")
    hip_z_range = stat_range(rows, "hip_z")
    left_contact = count_contact_segments(rows, "left_contact")
    right_contact = count_contact_segments(rows, "right_contact")
    contact_changes = count_discrete_changes(rows, "contact")
    support_changes = count_discrete_changes(rows, "support")
    phase_changes = count_discrete_changes(rows, "phase")
    input_energy = None
    energy_values = finite_values(rows, "input_energy")
    if energy_values:
        input_energy = energy_values[-1] - energy_values[0]

    angle_names = [
        name
        for name in header
        if any(key in name for key in ["angle", "theta", "hip", "knee"])
        and name not in {"hip_x", "hip_z", "hip_vx", "hip_vz", "hip_clearance"}
        and not name.endswith("_vel")
        and not name.endswith("_tau")
        and "power" not in name
        and "energy" not in name
    ]
    angle_text = []
    for name in angle_names[:6]:
        rng = stat_range(rows, name)
        if rng:
            angle_text.append(f"{name}: {rng} rad")
    if not angle_text:
        angle_text.append(
            "本版本没有明确的角度字段，报告图会显示前几个数值变量作为预览。"
        )

    torque_names = [name for name in header if name.endswith("_tau")]
    torque_text = []
    for name in torque_names:
        rng = stat_range(rows, name)
        if rng:
            torque_text.append(f"{name}: {rng} N·m")

    markdown = [
        f"# {version.upper()} 图表解读：{title}",
        "",
        f"![{version} 报告图]({report_link})",
        "",
        "## 版本定位",
        "",
        role,
        "",
        version_verdict(version, params),
        "",
        "## 数据概况",
        "",
        f"- 数据来源：`{csv_path}`",
        f"- 数据规模：{len(rows)} 行，{len(header)} 列",
        f"- 数据时长：{fmt(duration, ' s')}",
        f"- 髋部前进位移：{fmt(hip_delta, ' m')}",
        f"- 髋部 x 范围：{hip_range or '无 hip_x 字段'}",
        f"- 髋部 z 范围：{hip_z_range or '无 hip_z 字段'}",
    ]

    if left_contact is not None and right_contact is not None:
        markdown += [
            f"- 左脚触地段：{left_contact} 次",
            f"- 右脚触地段：{right_contact} 次",
        ]
    if contact_changes is not None:
        markdown.append(f"- contact 字段切换：{contact_changes} 次")
    if support_changes is not None:
        markdown.append(f"- support 字段切换：{support_changes} 次")
    if phase_changes is not None:
        markdown.append(f"- phase 字段切换：{phase_changes} 次")
    if input_energy is not None:
        markdown.append(f"- 输入能量累计变化：{input_energy:.3f} J")

    markdown += [
        "",
        f"## {version.upper()} 髋部前进轨迹",
        "",
    ]
    if hip_delta is None:
        markdown.append(
            "这一栏没有 `hip_x` 字段，因此报告图用可用数值变量代替。它不能直接说明整体前进距离。"
        )
    else:
        markdown.append(
            f"髋部 x 随时间的变化用来判断模型是否真的向前推进。本版本髋部前进约 {hip_delta:.3f} m，"
            "如果曲线持续上升，说明步态具有整体前进趋势；如果曲线平台化或反复回退，则说明模型卡住、跌倒或只是在局部摆动。"
        )

    markdown += [
        "",
        f"## {version.upper()} 脚地接触时序",
        "",
    ]
    if left_contact is not None and right_contact is not None:
        markdown.append(
            f"脚地接触时序用于判断是否形成左右交替支撑。本版本左脚触地段约 {left_contact} 次，"
            f"右脚触地段约 {right_contact} 次。理想步态应表现为左、右脚交替，而不是两脚长时间同时拖地或单脚一直粘住地面。"
        )
    elif contact_changes is not None or support_changes is not None:
        markdown.append(
            f"这一版没有 MuJoCo 左/右脚真实接触布尔量，但有 `contact`、`support` 或 `phase` 等离散事件字段。"
            f"其中 contact 切换约 {contact_changes if contact_changes is not None else '无'} 次，"
            f"support 切换约 {support_changes if support_changes is not None else '无'} 次，可用来表达换腿事件。"
        )
    else:
        markdown.append(
            "这一版没有明确的脚地接触字段，因此这张子图更多是关键变量预览，不能单独证明真实触地换腿。"
        )

    markdown += [
        "",
        f"## {version.upper()} 角度/关节变量",
        "",
        "这张图显示腿角、髋角或膝角随时间变化，用来观察摆腿是否周期性重复、膝关节是否出现不合理反折，以及动作是否突然抖动。",
        "",
        "本版本主要角度范围：",
    ]
    markdown += [f"- {item}" for item in angle_text]

    if torque_text:
        markdown += [
            "",
            f"## {version.upper()} 补能力矩/输入能量",
            "",
            "这部分只在准被动版本中出现。它不是奖励函数，也不是强化学习，而是直接记录施加在关节上的辅助力矩和由此输入的能量。答辩时必须明确：这些版本不是纯被动。",
        ]
        markdown += [f"- {item}" for item in torque_text]
        if input_energy is not None:
            markdown.append(f"- input_energy 累计增加约 {input_energy:.3f} J")

    markdown += [
        "",
        f"## {version.upper()} 相图",
        "",
        "相图把角度和角速度放在同一平面里观察。对极限环步态来说，稳定后轨迹应逐渐靠近一个重复闭合的环；如果轨迹发散、跳变很大或不能回到同一片区域，说明它还不是稳定周期步态。",
    ]

    if version == "v05":
        markdown.append(
            "V5 的相图和 Poincare 误差是证明重点：它说明混合动力学在触地截面上接近固定点，所以可作为纯被动极限环证明。"
        )
    elif version == "v01":
        markdown.append(
            "V1 的相图使用左腿角与左腿角速度绘制。它能看出早期指南针模型的摆动状态，但曲线还没有形成稳定闭合环，因此只能作为早期尝试。"
        )
    elif version == "v02":
        markdown.append(
            "V2 的相图使用 theta 与 theta_dot 绘制。它适合说明 rimless wheel 的周期碰撞思想，是极限环概念的简化对照。"
        )
    elif version == "v03":
        markdown.append(
            "V3 的相图使用腿角与支撑腿角速度绘制，同时结合 poincare_error 看收敛趋势。它比 V1/V2 更接近指南针极限环表达。"
        )
    elif version == "v04":
        markdown.append(
            "V4 的相图使用左大腿角与由数据差分估计的角速度绘制。它主要说明带膝机构的周期趋势，但证明力度仍弱于 V5。"
        )
    elif version in {"v08", "v09"}:
        markdown.append(
            "V8/V9 的相图可说明动作是否稳定重复，但因为存在主动补能力矩，它证明的是准被动仿生行走，不是纯被动极限环。"
        )
    else:
        markdown.append("这一版相图主要用于对照和展示模型演进，证明力度弱于 V5。")

    markdown += [
        "",
        f"## {version.upper()} 可以怎么放进作业",
        "",
    ]
    if version == "v05":
        markdown.append(
            "建议放在“原理验证/极限环证明”页：强调无 actuator、无奖励函数、Poincare 截面收敛。"
        )
    elif version == "v06":
        markdown.append(
            "建议放在“仿生 MVE 结构转译”页：强调髋轴、带膝双腿、支撑相/摆动相/触地换腿的机械表达。"
        )
    elif version == "v07":
        markdown.append(
            "建议放在“真实接触探索与问题”页：说明纯被动真实接触模型容易跌倒或卡住，是后续补能版本的合理动机。"
        )
    elif version == "v08":
        markdown.append(
            "建议放在“准被动补能探索”页：说明生物并非完全无输入，弱髋部补能能改善步态，但该版仍不是最终稳定结果。"
        )
    elif version == "v09":
        markdown.append(
            "建议放在“最终仿生行走展示”页：强调真实接触、连续交替触地、长时间前进，以及补能输入被明确记录。"
        )
    else:
        markdown.append(
            "建议作为版本演进材料：说明从简化模型逐步走向 V5 证明、V6 机构表达和 V9 稳定展示。"
        )

    markdown += [
        "",
        "## 关键表述边界",
        "",
        "- 纯被动极限环证明：优先引用 V5。",
        "- 仿生 MVE 结构表达：优先引用 V6。",
        "- 真实接触纯被动困难：引用 V7。",
        "- 生物式最小补能连续行走：引用 V8/V9，其中 V9 是稳定展示版。",
        "",
    ]
    return "\n".join(markdown)


def main() -> None:
    for version in VERSION_META:
        md = build_markdown(version)
        path = OUT / version / f"{version}_interpretation.md"
        path.write_text(md, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
