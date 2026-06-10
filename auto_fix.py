#!/usr/bin/env python3
"""
自动修复工具 - 修复代码质量问题
"""

import re
import shutil
from pathlib import Path
from collections import defaultdict

class AutoFixer:
    def __init__(self, root_dir=".", dry_run=True):
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.changes = defaultdict(list)

    def fix_all(self):
        """执行所有自动修复"""
        print("=" * 80)
        print("AUTO-FIXER - Automatic Code Quality Fixes")
        print(f"Mode: {'DRY RUN (preview only)' if self.dry_run else 'LIVE (will modify files)'}")
        print("=" * 80)
        print()

        self.fix_hardcoded_paths()
        self.fix_import_star()
        self.consolidate_requirements()

        self.print_summary()

    def fix_hardcoded_paths(self):
        """修复硬编码路径"""
        print("[1/3] Fixing hardcoded paths...")

        pattern = re.compile(r'["\']D:\\\\Dunna\\\\Documents\\\\hw-1')

        py_files = [f for f in self.root_dir.rglob("*.py")
                   if not self._should_skip(f)]

        fixed_count = 0
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')

                if pattern.search(content):
                    # 记录修复
                    matches = pattern.findall(content)
                    self.changes['hardcoded_paths'].append({
                        'file': str(py_file),
                        'matches': len(matches)
                    })

                    if not self.dry_run:
                        # 实际修复
                        # 替换为相对路径获取
                        new_content = pattern.sub(
                            'str(Path(__file__).resolve().parent.parent)',
                            content
                        )

                        # 确保导入 Path
                        if 'from pathlib import Path' not in new_content:
                            # 在文件开头添加导入
                            lines = new_content.split('\n')
                            # 找到第一个非注释非空行
                            insert_pos = 0
                            for i, line in enumerate(lines):
                                if line.strip() and not line.strip().startswith('#'):
                                    if line.strip().startswith('import') or line.strip().startswith('from'):
                                        continue
                                    insert_pos = i
                                    break

                            lines.insert(insert_pos, 'from pathlib import Path')
                            new_content = '\n'.join(lines)

                        py_file.write_text(new_content, encoding='utf-8')

                    fixed_count += 1

            except Exception as e:
                print(f"  Error processing {py_file}: {e}")

        print(f"  Found {fixed_count} files with hardcoded paths")
        if self.dry_run:
            print(f"  [DRY RUN] Would fix {fixed_count} files")
        else:
            print(f"  Fixed {fixed_count} files")
        print()

    def fix_import_star(self):
        """修复 import * 用法"""
        print("[2/3] Fixing import * usage...")

        # 这个修复比较复杂，需要分析实际使用了哪些名称
        # 这里只做标记，需要手动修复

        import_star_pattern = re.compile(r'from\s+(\S+)\s+import\s+\*')

        py_files = [f for f in self.root_dir.rglob("*.py")
                   if not self._should_skip(f)]

        found_count = 0
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                matches = import_star_pattern.findall(content)

                if matches:
                    self.changes['import_star'].append({
                        'file': str(py_file),
                        'modules': matches
                    })
                    found_count += 1

            except Exception:
                pass

        print(f"  Found {found_count} files with import *")
        print(f"  [INFO] import * requires manual review (analyzing usage)")
        print()

    def consolidate_requirements(self):
        """整合 requirements.txt"""
        print("[3/3] Analyzing requirements.txt files...")

        req_files = [f for f in self.root_dir.rglob("requirements.txt")
                    if not self._should_skip(f)]

        # 分析内容
        req_contents = {}
        for req_file in req_files:
            try:
                content = req_file.read_text(encoding='utf-8', errors='ignore').strip()
                if content not in req_contents:
                    req_contents[content] = []
                req_contents[content].append(req_file)
            except Exception:
                pass

        # 找出重复
        duplicates = {k: v for k, v in req_contents.items() if len(v) > 1}

        print(f"  Found {len(req_files)} requirements.txt files")
        print(f"  Found {len(duplicates)} duplicate content groups")

        self.changes['requirements'] = {
            'total': len(req_files),
            'unique': len(req_contents),
            'duplicates': len(duplicates)
        }

        if duplicates:
            print(f"  [INFO] Consider consolidating to single requirements.txt")
        print()

    def _should_skip(self, path):
        """判断是否跳过该路径"""
        path_str = str(path)
        skip_patterns = [
            '.venv-',
            '.git',
            '__pycache__',
            'node_modules'
        ]
        return any(pattern in path_str for pattern in skip_patterns)

    def print_summary(self):
        """打印修复摘要"""
        print("=" * 80)
        print("FIX SUMMARY")
        print("=" * 80)
        print()

        # 硬编码路径
        if self.changes['hardcoded_paths']:
            print(f"## Hardcoded Paths: {len(self.changes['hardcoded_paths'])} files")
            for change in self.changes['hardcoded_paths'][:5]:
                print(f"  - {change['file']} ({change['matches']} occurrences)")
            if len(self.changes['hardcoded_paths']) > 5:
                print(f"  ... and {len(self.changes['hardcoded_paths']) - 5} more")
            print()

        # import *
        if self.changes['import_star']:
            print(f"## Import *: {len(self.changes['import_star'])} files (manual fix needed)")
            for change in self.changes['import_star']:
                print(f"  - {change['file']}")
                print(f"    Modules: {', '.join(change['modules'])}")
            print()

        # requirements
        if self.changes['requirements']:
            print(f"## Requirements.txt:")
            print(f"  - Total files: {self.changes['requirements']['total']}")
            print(f"  - Unique contents: {self.changes['requirements']['unique']}")
            print(f"  - Duplicate groups: {self.changes['requirements']['duplicates']}")
            print()

        if self.dry_run:
            print("=" * 80)
            print("[DRY RUN] No files were modified.")
            print("Run with --live to apply fixes.")
            print("=" * 80)
        else:
            print("=" * 80)
            print("[LIVE] Files have been modified.")
            print("Review changes with: git diff")
            print("=" * 80)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-fix code quality issues")
    parser.add_argument('--live', action='store_true',
                       help='Apply fixes (default is dry-run)')

    args = parser.parse_args()

    fixer = AutoFixer(dry_run=not args.live)
    fixer.fix_all()

if __name__ == "__main__":
    main()
