#!/usr/bin/env python3
"""
Git 提交助手 - 帮助整理和提交未提交的文件
"""

import subprocess
from pathlib import Path
from collections import defaultdict


def get_git_status():
    """获取 git status"""
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    return result.stdout.strip().split("\n") if result.stdout else []


def categorize_changes(status_lines):
    """分类更改"""
    categories = defaultdict(list)

    for line in status_lines:
        if not line.strip():
            continue

        status = line[:2]
        filepath = line[3:]

        # 分类
        if "test" in filepath.lower():
            categories["tests"].append((status, filepath))
        elif "doc" in filepath.lower() or filepath.endswith(".md"):
            categories["docs"].append((status, filepath))
        elif filepath.startswith("v"):
            categories["versions"].append((status, filepath))
        elif filepath.startswith("rl_training"):
            categories["rl"].append((status, filepath))
        elif filepath.startswith("common"):
            categories["common"].append((status, filepath))
        elif filepath.endswith(".py"):
            categories["scripts"].append((status, filepath))
        else:
            categories["other"].append((status, filepath))

    return categories


def print_summary(categories):
    """打印摘要"""
    print("=" * 80)
    print("GIT COMMIT HELPER")
    print("=" * 80)
    print()

    total = sum(len(files) for files in categories.values())
    print(f"Total files: {total}")
    print()

    for category, files in sorted(categories.items()):
        if not files:
            continue

        print(f"## {category.upper()}: {len(files)} files")
        for status, filepath in files[:3]:
            status_symbol = {
                "A ": "[ADD]",
                "M ": "[MOD]",
                "D ": "[DEL]",
                "??": "[NEW]",
                "MM": "[MOD]",
                "AM": "[ADD]",
            }.get(status, status)
            print(f"  {status_symbol} {filepath}")

        if len(files) > 3:
            print(f"  ... and {len(files) - 3} more")
        print()


def generate_commit_message(categories):
    """生成建议的提交信息"""
    lines = []

    # 主标题
    if categories["rl"]:
        lines.append("Complete RL training and analysis tools")
    elif categories["docs"]:
        lines.append("Update documentation and reports")
    elif categories["versions"]:
        lines.append("Add new version implementations")
    else:
        lines.append("Project updates and improvements")

    lines.append("")

    # 详细描述
    if categories["docs"]:
        lines.append(f"Documentation:")
        lines.append(f"- Add {len(categories['docs'])} documentation files")

    if categories["rl"]:
        lines.append(f"RL Training:")
        lines.append(f"- Add {len(categories['rl'])} RL training scripts and tools")

    if categories["scripts"]:
        lines.append(f"Scripts:")
        lines.append(f"- Add {len(categories['scripts'])} analysis and utility scripts")

    if categories["common"]:
        lines.append(f"Common Library:")
        lines.append(f"- Update {len(categories['common'])} common library files")

    if categories["versions"]:
        lines.append(f"Versions:")
        lines.append(f"- Update {len(categories['versions'])} version directories")

    lines.append("")
    lines.append("Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>")

    return "\n".join(lines)


def main():
    print("Analyzing git status...")
    print()

    status_lines = get_git_status()

    if not status_lines or not any(status_lines):
        print("No changes to commit!")
        return

    categories = categorize_changes(status_lines)
    print_summary(categories)

    print("=" * 80)
    print("SUGGESTED COMMIT MESSAGE")
    print("=" * 80)
    print()

    commit_msg = generate_commit_message(categories)
    print(commit_msg)
    print()

    print("=" * 80)
    print("SUGGESTED COMMANDS")
    print("=" * 80)
    print()
    print("# Review changes:")
    print("git status")
    print()
    print("# Stage all files:")
    print("git add .")
    print()
    print("# Commit with message:")
    print('git commit -m "' + commit_msg.split("\n")[0] + '"')
    print()
    print("# Or use the full message from a file:")
    print("# Save message to commit_msg.txt, then:")
    print("# git commit -F commit_msg.txt")
    print()

    # 保存提交信息到文件
    commit_msg_file = Path("suggested_commit_msg.txt")
    commit_msg_file.write_text(commit_msg, encoding="utf-8")
    print(f"Commit message saved to: {commit_msg_file}")
    print()


if __name__ == "__main__":
    main()
