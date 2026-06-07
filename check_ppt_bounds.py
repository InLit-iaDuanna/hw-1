"""检查 pptx 中所有形状是否在 13.333 x 7.5 in 页面内,列出越界元素。"""

import sys

from pptx import Presentation

PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else r"D:\Dunna\Documents\hw-1\midterm_report_150347.pptx"
)
W = int(13.333 * 914400)
H = int(7.5 * 914400)

prs = Presentation(PATH)
issues = 0
for idx, slide in enumerate(prs.slides, 1):
    for sh in slide.shapes:
        try:
            x, y, w, h = sh.left, sh.top, sh.width, sh.height
            if x is None:
                continue
            r, b = x + w, y + h
            ox = max(0, r - W)
            oy = max(0, b - H)
            ux = max(0, -x)
            uy = max(0, -y)
            if ox or oy or ux or uy:
                issues += 1
                # 显示文本前 20 字
                txt = ""
                if sh.has_text_frame:
                    txt = sh.text_frame.text[:25].replace("\n", " ")
                print(
                    f"P{idx:02d}  {sh.shape_type}  "
                    f"x={x/914400:.2f} y={y/914400:.2f} w={w/914400:.2f} h={h/914400:.2f}  "
                    f"右溢={ox/914400:.2f} 下溢={oy/914400:.2f}  '{txt}'"
                )
        except Exception:
            pass
print(f"\n共 {issues} 个越界形状" if issues else "\n全部在边界内")
