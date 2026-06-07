"""
从文档提取版本依赖关系并生成图数据结构
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class VersionNode:
    """版本节点"""
    id: str
    name: str
    stage: int  # 1-4
    type: str  # 理论证明/机械转译/真实接触/分析层/硬件/探索层
    status: str  # 已完成/纯被动/准被动/失败/设计文档/否定结果
    description: str
    key_metrics: Dict[str, str]  # 关键指标
    is_main_line: bool  # 是否主线版本

@dataclass
class VersionEdge:
    """版本依赖边"""
    source: str
    target: str
    type: str  # 直接继承/参考对照/分支探索/并行分支
    description: str

def extract_version_graph():
    """提取完整版本依赖图"""

    # 定义所有版本节点
    nodes = [
        # 阶段1: 理论证明 V1-V13
        VersionNode("V01", "初始 MuJoCo 指南针步态", 1, "理论证明", "已完成",
                   "早期探索，接触参数敏感",
                   {"纯被动": "否", "动画": "有", "MATLAB": "有"}, False),
        VersionNode("V02", "Rimless wheel 对照", 1, "理论证明", "纯被动",
                   "展示重力补能和碰撞损耗",
                   {"纯被动": "是", "用途": "解释重力补能"}, False),
        VersionNode("V03", "指南针极限环对照", 1, "理论证明", "纯被动",
                   "基础极限环相图和 Poincare 点",
                   {"纯被动": "是", "用途": "解释极限环"}, False),
        VersionNode("V04", "带膝极限环对照", 1, "理论证明", "部分纯被动",
                   "带膝趋势对照，稳定性不足",
                   {"纯被动": "部分", "用途": "带膝趋势"}, False),
        VersionNode("V05", "混合动力学证明版", 1, "理论证明", "纯被动",
                   "纯被动极限环证明主证据",
                   {"纯被动": "是", "证明": "混合动力学"}, True),
        VersionNode("V06", "MVE 作业表达版", 1, "机械转译", "已完成",
                   "机制转译为最小机械结构",
                   {"纯被动": "展示层", "用途": "PPT 主图"}, True),
        VersionNode("V07", "真实接触纯被动探索", 1, "真实接触", "失败",
                   "真实接触失败，敏感性分析",
                   {"纯被动": "是", "结论": "失败"}, False),
        VersionNode("V08", "准被动补能探索", 1, "真实接触", "准被动",
                   "生物式补能讨论",
                   {"纯被动": "否", "补能": "准被动"}, False),
        VersionNode("V09", "准被动稳定行走", 1, "真实接触", "准被动",
                   "真实接触下稳定连续行走",
                   {"纯被动": "否", "稳定": "是"}, False),
        VersionNode("V10", "足踝滚动仿生步态", 1, "真实接触", "准被动",
                   "加入被动踝关节和滚动足，PD baseline",
                   {"成功率": "16.7% (切片C)", "CoT": "~0.08", "控制": "PD"}, True),
        VersionNode("V11", "地形与扰动鲁棒性", 1, "真实接触", "准被动",
                   "小幅地形成功，强扰动失败边界",
                   {"鲁棒性": "小幅通过", "扰动": "强扰动失败"}, True),
        VersionNode("V12", "能量与 CoT 分析", 1, "分析层", "已完成",
                   "能量输入、CoT、碰撞损耗和收敛指标",
                   {"分析": "能量/Floquet", "用途": "附录"}, True),
        VersionNode("V13", "参数敏感性图谱", 1, "分析层", "已完成",
                   "设计容差、成功率和失败模式边界",
                   {"分析": "参数容差", "用途": "附录"}, True),

        # V13 分支
        VersionNode("V13.5", "hip 控制律重设计探索", 1, "探索层", "失败",
                   "方案 A/A' 否决，揭示 V10 隐式 bang-bang",
                   {"方案A": "否决", "方案A'": "否决", "发现": "bang-bang"}, False),
        VersionNode("V13b", "长程极限环辨识", 1, "分析层", "已完成",
                   "20s 长程 Floquet 谱，极限环能量 E*=52.66 J",
                   {"Floquet": "max|λ|=0.944", "E*": "52.66±0.53 J"}, False),
        VersionNode("V13.6", "事件驱动 FSM hip 控制律", 1, "准被动", "已完成",
                   "4 phase FSM 显式时序，解构 V10 bang-bang",
                   {"成功率": "11.1% (切片C)", "forward": "4.86m", "CoT": "0.072"}, True),
        VersionNode("V13.6.1", "FSM phase 参数精调", 1, "准被动", "已完成",
                   "独立搜索每 phase 参数，部分恢复",
                   {"成功率": "13.9% (切片C)", "切片A": "11.1%"}, True),

        # 阶段2: 2D 机械升级 V14-V17
        VersionNode("V14", "被动摆臂", 2, "机构维度", "已完成",
                   "arm_mass≥0.05 kg 破坏 V10 稳定",
                   {"成功率": "5/35 (14.3%)", "结论": "质量≥0.05即失败"}, False),
        VersionNode("V14b", "FSM + 被动摆臂", 2, "机构维度", "已完成",
                   "V13.6 FSM 恢复摆臂空间 40%",
                   {"成功率": "14/35 (40%)", "关键行": "5/5 (m=0.05)"}, False),
        VersionNode("V14c", "arm_mass 减重扫描", 2, "机构维度", "已完成",
                   "确认 arm_mass 为根因，V15 解封",
                   {"m=0.05": "3/36", "m=0.01": "5/36", "结论": "根因确认"}, True),

        # V15 分支
        VersionNode("V15.0", "PEA 探索", 2, "弹性肌腱", "失败",
                   "并联弹性执行器失败",
                   {"结论": "PEA 打破 FSM"}, False),
        VersionNode("V15.1", "SEA direct-drive", 2, "弹性肌腱", "已完成",
                   "串联弹性，k=500 最优 (4.92m)",
                   {"k=500": "forward=4.92m", "k=5000": "5/36", "spring_defl": "1.6 deg"}, False),
        VersionNode("V15.1L1", "SEA + L1 电机", 2, "弹性肌腱", "已完成",
                   "SEA 部分缓冲电机动力学",
                   {"k=500+comp": "4.90m PASS", "结论": "需补偿"}, False),
        VersionNode("V15.2", "Pratt 内环 SEA", 2, "弹性肌腱", "失败",
                   "内环与 FSM 冲突",
                   {"结论": "内环不适用 FSM"}, False),

        # V16-V17 主线
        VersionNode("V16", "L1 电机动力学", 2, "真实电机", "已完成",
                   "发现 τ_C 与 FSM 非单调共振",
                   {"mx64ar": "失败 (0.19m)", "τ_C_spec": "0.20 (失败带)", "失败带": "[0.013, 0.20]"}, True),
        VersionNode("V13.7", "前馈摩擦补偿", 2, "准被动", "已完成",
                   "τ_comp 精确对消库仑摩擦，完全恢复",
                   {"mx64ar": "4.63m PASS", "τ_C扫描": "10/10 全通过", "CoT": "0.066"}, True),
        VersionNode("V17", "传感器闭环状态估计", 2, "准被动", "已完成",
                   "编码器量化+Kalman+FK，阶段2闭环",
                   {"noise=1.0": "4.67m PASS", "rmse_vx": "0.079", "容限": "3× critical"}, True),

        # 阶段3: 3D 化 V18-V21 (全否定)
        VersionNode("V18", "3D 侧向被动稳定探索", 3, "探索层", "否定结果",
                   "被动侧向稳定不存在",
                   {"roll_k<200": "发散", "roll_k≥500": "等效2D", "结论": "需主动控制"}, False),
        VersionNode("V19", "髋外展主动稳定", 3, "探索层", "否定结果",
                   "abd 修正能力不足 5-10×",
                   {"最佳": "7 alt/2.97s", "目标": "10 alt/12s (未达标)", "漂移率": "5-10× 超过修正"}, False),
        VersionNode("V20", "步宽控制探索", 3, "探索层", "否定结果",
                   "架构完成但控制未集成",
                   {"smoke": "0 alt (失败)", "架构": "3D IK+规划器", "结论": "未验证"}, False),
        VersionNode("V21", "3D 扰动鲁棒性", 3, "探索层", "跳过",
                   "综合 V18/V19/V20 否定，跳过直接进 V22",
                   {"决策": "跳过", "原因": "3D 全否定"}, False),

        # 阶段4: 硬件落地 V22-V25
        VersionNode("V22", "硬件设计 v1", 4, "硬件", "设计文档",
                   "基于 V13.7+V17 的 2D 样机完整设计",
                   {"电机": "MX-64AR×4", "预算": "6500-8000元", "质量": "5-6kg"}, True),
        VersionNode("V23", "系统辨识", 4, "硬件", "方法论文档",
                   "从硬件数据反推物理参数",
                   {"辨识": "摩擦/惯量/弹簧", "误差": "<10%"}, True),
        VersionNode("V24", "Sim-to-real 迁移", 4, "硬件", "策略文档",
                   "域随机化和鲁棒控制器设计",
                   {"随机化": "质量±10%/摩擦1.0-1.6", "目标": "成功率>50%"}, True),
        VersionNode("V25", "实地行走", 4, "硬件", "待实施",
                   "真实硬件地面行走测试",
                   {"状态": "等待硬件制作", "周期": "2-3个月"}, True),
    ]

    # 定义所有依赖边
    edges = [
        # 阶段1主线
        VersionEdge("V01", "V02", "参考对照", "理论对照：从复杂到简化"),
        VersionEdge("V01", "V03", "参考对照", "理论对照：指南针极限环"),
        VersionEdge("V03", "V04", "直接继承", "扩展：加入膝关节"),
        VersionEdge("V03", "V05", "直接继承", "理论证明：混合动力学"),
        VersionEdge("V05", "V06", "直接继承", "转译：理论到机械结构"),
        VersionEdge("V06", "V07", "直接继承", "探索：真实接触纯被动"),
        VersionEdge("V07", "V08", "直接继承", "修正：失败后加补能"),
        VersionEdge("V08", "V09", "直接继承", "改进：稳定行走"),
        VersionEdge("V09", "V10", "直接继承", "扩展：足踝滚动仿生"),
        VersionEdge("V10", "V11", "直接继承", "分析：地形扰动鲁棒性"),
        VersionEdge("V10", "V12", "参考对照", "分析：能量 CoT Floquet"),
        VersionEdge("V10", "V13", "参考对照", "分析：参数敏感性图谱"),

        # V13 分支
        VersionEdge("V13", "V13.5", "分支探索", "探索：hip 控制律重设计"),
        VersionEdge("V13.5", "V13b", "参考对照", "分析：为方案C提供极限环目标"),
        VersionEdge("V13.5", "V13.6", "直接继承", "修正：方案A/A'否决后的FSM"),
        VersionEdge("V13.6", "V13.6.1", "直接继承", "优化：phase参数精调"),

        # 阶段2: V14 分支
        VersionEdge("V10", "V14", "分支探索", "探索：被动摆臂可行性"),
        VersionEdge("V13.6", "V14b", "并行分支", "合并：FSM + 被动摆臂"),
        VersionEdge("V14", "V14b", "并行分支", "合并：FSM恢复摆臂稳定性"),
        VersionEdge("V13.6.1", "V14c", "直接继承", "探索：arm_mass减重扫描"),
        VersionEdge("V14b", "V14c", "参考对照", "对照：确认arm_mass为根因"),

        # V15 分支
        VersionEdge("V14c", "V15.0", "分支探索", "探索：PEA (失败)"),
        VersionEdge("V14c", "V15.1", "分支探索", "探索：SEA direct-drive"),
        VersionEdge("V14c", "V15.2", "分支探索", "探索：Pratt内环SEA (失败)"),
        VersionEdge("V15.2", "V15.1", "直接继承", "修正：去内环改直传"),
        VersionEdge("V15.1", "V15.1L1", "直接继承", "合并：SEA + L1电机"),

        # V16-V17 主线
        VersionEdge("V14c", "V16", "并行分支", "并行：L1电机动力学 (不依赖V15)"),
        VersionEdge("V16", "V13.7", "直接继承", "修复：前馈摩擦补偿"),
        VersionEdge("V13.6.1", "V13.7", "并行分支", "合并：FSM + 摩擦补偿"),
        VersionEdge("V13.7", "V17", "直接继承", "扩展：传感器闭环估计"),
        VersionEdge("V16", "V15.1L1", "并行分支", "合并：电机动力学 + SEA"),

        # 阶段3: 3D 化
        VersionEdge("V10", "V18", "分支探索", "探索：3D侧向被动稳定"),
        VersionEdge("V18", "V19", "直接继承", "修正：引入髋外展主动"),
        VersionEdge("V19", "V20", "直接继承", "扩展：步宽控制"),
        VersionEdge("V20", "V21", "直接继承", "计划：3D扰动鲁棒性 (跳过)"),

        # 阶段4: 硬件
        VersionEdge("V17", "V22", "直接继承", "应用：2D主线硬件设计"),
        VersionEdge("V13.7", "V22", "并行分支", "应用：摩擦补偿控制律"),
        VersionEdge("V22", "V23", "直接继承", "支持：系统辨识方法"),
        VersionEdge("V23", "V24", "直接继承", "支持：Sim-to-real策略"),
        VersionEdge("V24", "V25", "直接继承", "实施：实地行走"),
    ]

    return nodes, edges

def save_graph_data():
    """保存图数据为 JSON"""
    nodes, edges = extract_version_graph()

    graph_data = {
        "nodes": [asdict(node) for node in nodes],
        "edges": [asdict(edge) for edge in edges],
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "stages": {
                "1": "理论证明与2D步态 (V1-V13)",
                "2": "2D机械升级 (V14-V17)",
                "3": "3D化探索 (V18-V21)",
                "4": "硬件落地 (V22-V25)"
            },
            "main_line": ["V05", "V06", "V10", "V11", "V12", "V13", "V13.6", "V13.6.1",
                         "V14c", "V16", "V13.7", "V17", "V22", "V23", "V24", "V25"],
            "decision_gates": [
                {"version": "V13", "decision": "机构升级优先于控制堆叠"},
                {"version": "V14", "decision": "V10为孤立点解，摆臂破坏稳定"},
                {"version": "V14c", "decision": "arm_mass为根因，V15解封"},
                {"version": "V16", "decision": "电机摩擦破坏FSM，需V13.7补偿"},
                {"version": "V18", "decision": "侧向被动不存在，需主动控制"},
                {"version": "V20", "decision": "3D全否定，跳过V21直接V22硬件"}
            ]
        }
    }

    with open("D:/Dunna/Documents/hw-1/version_graph/graph_data.json", "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"已保存图数据：{len(nodes)} 个节点，{len(edges)} 条边")
    print(f"主线版本：{len([n for n in nodes if n.is_main_line])} 个")
    print(f"否定结果：{len([n for n in nodes if '否定' in n.status or '失败' in n.status])} 个")

if __name__ == "__main__":
    save_graph_data()
