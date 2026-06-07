"""
生成简化的 DOT 格式文件（不依赖 Graphviz Python 包）
可以手动用 Graphviz 工具或在线工具渲染
"""

import json

def load_graph_data():
    """加载图数据"""
    with open("D:/Dunna/Documents/hw-1/version_graph/graph_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def generate_dot_file():
    """生成 DOT 格式文件"""
    data = load_graph_data()

    # 阶段颜色
    stage_colors = {
        1: '#E3F2FD',
        2: '#FFF3E0',
        3: '#FCE4EC',
        4: '#E8F5E9'
    }

    # 开始 DOT 文件
    dot_lines = []
    dot_lines.append('digraph hw1_versions {')
    dot_lines.append('    rankdir=TB;')
    dot_lines.append('    node [fontname="Microsoft YaHei", fontsize=10, style=filled];')
    dot_lines.append('    edge [fontname="Microsoft YaHei", fontsize=8];')
    dot_lines.append('    bgcolor="#FAFAFA";')
    dot_lines.append('')

    # 按阶段分组
    for stage in range(1, 5):
        stage_nodes = [n for n in data['nodes'] if n['stage'] == stage]
        if not stage_nodes:
            continue

        stage_names = {
            1: '阶段1: 理论证明与2D步态',
            2: '阶段2: 2D机械升级',
            3: '阶段3: 3D化探索',
            4: '阶段4: 硬件落地'
        }

        dot_lines.append(f'    subgraph cluster_{stage} {{')
        dot_lines.append(f'        label="{stage_names[stage]}";')
        dot_lines.append('        style=rounded;')
        dot_lines.append('        color="#1976D2";')
        dot_lines.append('')

        for node in stage_nodes:
            # 确定形状
            shape = 'box'
            if node['status'] == '纯被动':
                shape = 'ellipse'
            elif '文档' in node['status']:
                shape = 'folder'

            # 确定边框
            penwidth = '3.0' if node['is_main_line'] else '1.5'
            color = '#D32F2F' if node['is_main_line'] else '#666666'

            if '否定' in node['status'] or '失败' in node['status']:
                color = '#F44336'

            # 构建标签
            label = f"{node['id']}\\n{node['name']}\\n"
            label += f"{node['type']} | {node['status']}"

            # 添加关键指标（最多2个）
            metrics = list(node['key_metrics'].items())[:2]
            if metrics:
                label += "\\n---\\n"
                for k, v in metrics:
                    label += f"{k}: {v}\\n"

            dot_lines.append(f'        "{node["id"]}" [')
            dot_lines.append(f'            label="{label}",')
            dot_lines.append(f'            shape={shape},')
            dot_lines.append(f'            fillcolor="{stage_colors[stage]}",')
            dot_lines.append(f'            color="{color}",')
            dot_lines.append(f'            penwidth={penwidth}')
            dot_lines.append(f'        ];')

        dot_lines.append('    }')
        dot_lines.append('')

    # 添加边
    dot_lines.append('    // 依赖关系')
    for edge in data['edges']:
        style = 'solid'
        penwidth = '2.0'
        color = '#999999'

        if edge['type'] == '直接继承':
            style = 'solid'
            penwidth = '2.5'
            color = '#1976D2'
        elif edge['type'] == '参考对照':
            style = 'dashed'
            color = '#757575'
        elif edge['type'] == '分支探索':
            style = 'dotted'
            color = '#F57C00'
        elif edge['type'] == '并行分支':
            style = 'solid'
            color = '#388E3C'

        dot_lines.append(f'    "{edge["source"]}" -> "{edge["target"]}" [')
        dot_lines.append(f'        label="{edge["description"]}",')
        dot_lines.append(f'        style={style},')
        dot_lines.append(f'        penwidth={penwidth},')
        dot_lines.append(f'        color="{color}"')
        dot_lines.append(f'    ];')

    dot_lines.append('}')

    # 保存完整图
    with open("D:/Dunna/Documents/hw-1/version_graph/full_graph.dot", "w", encoding="utf-8") as f:
        f.write('\n'.join(dot_lines))

    print("完整依赖图 DOT 文件已生成: full_graph.dot")

    # 生成主线简化图
    generate_mainline_dot(data)

def generate_mainline_dot(data):
    """生成主线简化图的 DOT 文件"""
    main_line = data['metadata']['main_line']

    stage_colors = {
        1: '#E3F2FD',
        2: '#FFF3E0',
        3: '#FCE4EC',
        4: '#E8F5E9'
    }

    dot_lines = []
    dot_lines.append('digraph hw1_mainline {')
    dot_lines.append('    rankdir=TB;')
    dot_lines.append('    node [fontname="Microsoft YaHei", fontsize=11, style="filled,rounded"];')
    dot_lines.append('    edge [fontname="Microsoft YaHei", fontsize=9];')
    dot_lines.append('    bgcolor="#FAFAFA";')
    dot_lines.append('')

    # 只添加主线节点
    for node in data['nodes']:
        if node['id'] not in main_line:
            continue

        label = f"{node['id']}: {node['name']}\\n"
        label += f"{node['description']}"

        # 添加关键指标
        metrics = list(node['key_metrics'].items())[:2]
        if metrics:
            label += "\\n"
            for k, v in metrics:
                label += f"{k}: {v}\\n"

        dot_lines.append(f'    "{node["id"]}" [')
        dot_lines.append(f'        label="{label}",')
        dot_lines.append(f'        shape=box,')
        dot_lines.append(f'        fillcolor="{stage_colors[node["stage"]]}",')
        dot_lines.append(f'        color="#D32F2F",')
        dot_lines.append(f'        penwidth=2.5')
        dot_lines.append(f'    ];')

    dot_lines.append('')

    # 只添加主线边
    for edge in data['edges']:
        if edge['source'] in main_line and edge['target'] in main_line:
            dot_lines.append(f'    "{edge["source"]}" -> "{edge["target"]}" [')
            dot_lines.append(f'        label="{edge["description"]}",')
            dot_lines.append(f'        style=solid,')
            dot_lines.append(f'        penwidth=2.0,')
            dot_lines.append(f'        color="#1976D2"')
            dot_lines.append(f'    ];')

    dot_lines.append('}')

    with open("D:/Dunna/Documents/hw-1/version_graph/main_line_graph.dot", "w", encoding="utf-8") as f:
        f.write('\n'.join(dot_lines))

    print("主线简化图 DOT 文件已生成: main_line_graph.dot")
    print("\n可以使用以下命令渲染图形（需要安装 Graphviz）：")
    print("  dot -Tpng full_graph.dot -o full_graph.png")
    print("  dot -Tpng main_line_graph.dot -o main_line_graph.png")
    print("\n或上传到在线工具：")
    print("  https://dreampuf.github.io/GraphvizOnline/")
    print("  https://edotor.net/")

if __name__ == "__main__":
    generate_dot_file()
