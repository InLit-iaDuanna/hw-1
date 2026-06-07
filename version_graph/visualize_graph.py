"""
使用 Graphviz 生成静态依赖图
"""

import json
from graphviz import Digraph

def load_graph_data():
    """加载图数据"""
    with open("D:/Dunna/Documents/hw-1/version_graph/graph_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def create_graphviz():
    """创建 Graphviz 图"""
    data = load_graph_data()

    # 创建有向图
    dot = Digraph(comment='hw-1 版本依赖关系图', format='png')
    dot.attr(rankdir='TB', size='20,30', dpi='150')
    dot.attr('node', fontname='Microsoft YaHei', fontsize='10')
    dot.attr('edge', fontname='Microsoft YaHei', fontsize='8')

    # 阶段颜色映射
    stage_colors = {
        1: '#E3F2FD',  # 浅蓝 - 理论证明
        2: '#FFF3E0',  # 浅橙 - 2D机械升级
        3: '#FCE4EC',  # 浅粉 - 3D探索
        4: '#E8F5E9'   # 浅绿 - 硬件落地
    }

    # 状态样式映射
    status_styles = {
        '纯被动': {'shape': 'ellipse', 'style': 'filled'},
        '准被动': {'shape': 'box', 'style': 'filled'},
        '已完成': {'shape': 'box', 'style': 'filled'},
        '失败': {'shape': 'box', 'style': 'filled,dashed', 'color': '#FFCDD2'},
        '否定结果': {'shape': 'box', 'style': 'filled,dashed', 'color': '#FFCDD2'},
        '设计文档': {'shape': 'folder', 'style': 'filled'},
        '方法论文档': {'shape': 'note', 'style': 'filled'},
        '策略文档': {'shape': 'note', 'style': 'filled'},
        '待实施': {'shape': 'diamond', 'style': 'filled'},
        '跳过': {'shape': 'box', 'style': 'filled,dotted', 'color': '#BDBDBD'}
    }

    # 边类型样式
    edge_styles = {
        '直接继承': {'style': 'solid', 'penwidth': '2.0', 'color': '#1976D2'},
        '参考对照': {'style': 'dashed', 'penwidth': '1.5', 'color': '#757575'},
        '分支探索': {'style': 'dotted', 'penwidth': '1.5', 'color': '#F57C00'},
        '并行分支': {'style': 'solid', 'penwidth': '1.5', 'color': '#388E3C'}
    }

    # 创建子图按阶段分组
    with dot.subgraph(name='cluster_1') as c:
        c.attr(label='阶段1: 理论证明与2D步态 (V1-V13)', style='rounded', color='#1976D2')
        for node in data['nodes']:
            if node['stage'] == 1:
                add_node(c, node, stage_colors, status_styles, data['metadata']['main_line'])

    with dot.subgraph(name='cluster_2') as c:
        c.attr(label='阶段2: 2D机械升级 (V14-V17)', style='rounded', color='#F57C00')
        for node in data['nodes']:
            if node['stage'] == 2:
                add_node(c, node, stage_colors, status_styles, data['metadata']['main_line'])

    with dot.subgraph(name='cluster_3') as c:
        c.attr(label='阶段3: 3D化探索 (V18-V21) - 全否定', style='rounded', color='#C2185B')
        for node in data['nodes']:
            if node['stage'] == 3:
                add_node(c, node, stage_colors, status_styles, data['metadata']['main_line'])

    with dot.subgraph(name='cluster_4') as c:
        c.attr(label='阶段4: 硬件落地 (V22-V25)', style='rounded', color='#388E3C')
        for node in data['nodes']:
            if node['stage'] == 4:
                add_node(c, node, stage_colors, status_styles, data['metadata']['main_line'])

    # 添加边
    for edge in data['edges']:
        style = edge_styles.get(edge['type'], {'style': 'solid'})
        dot.edge(edge['source'], edge['target'],
                label=edge['description'],
                **style)

    return dot

def add_node(graph, node, stage_colors, status_styles, main_line):
    """添加节点到图中"""
    # 基础颜色
    fillcolor = stage_colors[node['stage']]

    # 状态样式
    style_dict = status_styles.get(node['status'], {'shape': 'box', 'style': 'filled'})

    # 主线高亮
    if node['id'] in main_line:
        penwidth = '3.0'
        color = '#D32F2F'
    else:
        penwidth = '1.0'
        color = 'black'

    # 如果状态有特定颜色，覆盖填充色
    if 'color' in style_dict:
        fillcolor = style_dict['color']

    # 构建标签
    label = f"{node['id']}: {node['name']}\n"
    label += f"类型: {node['type']}\n"
    label += f"状态: {node['status']}\n"

    # 添加关键指标
    if node['key_metrics']:
        label += "---\n"
        for k, v in list(node['key_metrics'].items())[:3]:  # 最多显示3个指标
            label += f"{k}: {v}\n"

    graph.node(node['id'],
              label=label,
              shape=style_dict['shape'],
              style=style_dict['style'],
              fillcolor=fillcolor,
              color=color,
              penwidth=penwidth)

def create_main_line_only():
    """创建仅主线的简化图"""
    data = load_graph_data()
    main_line = data['metadata']['main_line']

    dot = Digraph(comment='hw-1 主线演化路径', format='png')
    dot.attr(rankdir='TB', size='15,20', dpi='150')
    dot.attr('node', fontname='Microsoft YaHei', fontsize='11')
    dot.attr('edge', fontname='Microsoft YaHei', fontsize='9')

    stage_colors = {
        1: '#E3F2FD',
        2: '#FFF3E0',
        3: '#FCE4EC',
        4: '#E8F5E9'
    }

    # 只添加主线节点
    for node in data['nodes']:
        if node['id'] in main_line:
            fillcolor = stage_colors[node['stage']]

            label = f"<b>{node['id']}</b>: {node['name']}<br/>"
            label += f"<i>{node['description']}</i><br/>"

            # 添加关键指标
            if node['key_metrics']:
                label += "<br/>"
                for k, v in list(node['key_metrics'].items())[:2]:
                    label += f"{k}: {v}<br/>"

            dot.node(node['id'],
                    label=f"<{label}>",
                    shape='box',
                    style='filled,rounded',
                    fillcolor=fillcolor,
                    color='#D32F2F',
                    penwidth='2.5')

    # 只添加主线之间的边
    main_line_edges = [
        edge for edge in data['edges']
        if edge['source'] in main_line and edge['target'] in main_line
    ]

    for edge in main_line_edges:
        dot.edge(edge['source'], edge['target'],
                label=edge['description'],
                style='solid',
                penwidth='2.0',
                color='#1976D2')

    return dot

def generate_all_graphs():
    """生成所有图形"""

    print("正在生成完整依赖图...")
    dot_full = create_graphviz()
    dot_full.render('D:/Dunna/Documents/hw-1/version_graph/full_graph',
                    cleanup=True, view=False)
    print("✓ 完整依赖图已生成: full_graph.png")

    print("\n正在生成主线简化图...")
    dot_main = create_main_line_only()
    dot_main.render('D:/Dunna/Documents/hw-1/version_graph/main_line_graph',
                    cleanup=True, view=False)
    print("✓ 主线简化图已生成: main_line_graph.png")

if __name__ == "__main__":
    generate_all_graphs()
