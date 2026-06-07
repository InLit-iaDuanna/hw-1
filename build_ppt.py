"""
中期汇报 PPT 生成脚本
输出: D:\\Dunna\\Documents\\hw-1\\midterm_report.pptx
用法: .\\.venv-mujoco\\Scripts\\python.exe build_ppt.py
"""

from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).parent

INK = RGBColor(0x1F, 0x2A, 0x37)
INK_SOFT = RGBColor(0x4B, 0x55, 0x63)
INK_MUTE = RGBColor(0x8A, 0x93, 0x9E)
LINE = RGBColor(0xD8, 0xDC, 0xE0)
PAGE_BG = RGBColor(0xFA, 0xF8, 0xF3)
PANEL_BG = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0xC0, 0x53, 0x2C)
ACCENT_S = RGBColor(0xE8, 0xC8, 0xA8)
DEEP = RGBColor(0x2A, 0x4A, 0x5C)
OK = RGBColor(0x4A, 0x7A, 0x4A)
WARN = RGBColor(0xB0, 0x6A, 0x2C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "微软雅黑"

W, H = Inches(13.333), Inches(7.5)
MX = Inches(0.55)
SAFE_W = W - 2 * MX  # 12.233"
HEAD_LINE_Y = Inches(0.70)
FOOT_LINE_Y = Inches(7.05)
CONTENT_TOP = Inches(0.95)
CONTENT_BOT = Inches(7.00)


# ---------- helpers ----------
def set_fill(sh, rgb):
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb


def no_line(sh):
    sh.line.fill.background()


def set_line(sh, rgb, w=0.75):
    sh.line.color.rgb = rgb
    sh.line.width = Pt(w)


def rect(slide, x, y, w, h, fill=None, line=None, lw=0.75):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        set_fill(sh, fill)
    if line is None:
        no_line(sh)
    else:
        set_line(sh, line, lw)
    return sh


def hline(slide, x, y, w, color=LINE):
    rect(slide, x, y, w, Emu(6350), fill=color)


def vbar(slide, x, y, h, color=ACCENT, w=Emu(38100)):
    rect(slide, x, y, w, h, fill=color)


def text(
    slide,
    x,
    y,
    w,
    h,
    content,
    *,
    size=11,
    bold=False,
    color=INK,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    ls=1.25,
):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = content.split("\n") if isinstance(content, str) else content
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = ls
        run = p.add_run()
        run.text = ln
        run.font.name = FONT
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = etree.SubElement(rPr, qn("a:ea"))
        ea.set("typeface", FONT)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def picture(slide, path, x, y, w=None, h=None):
    p = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not p.exists():
        rect(
            slide,
            x,
            y,
            w or Inches(3),
            h or Inches(2),
            fill=RGBColor(0xEE, 0xEE, 0xEE),
            line=LINE,
        )
        text(
            slide,
            x,
            y,
            w or Inches(3),
            h or Inches(2),
            f"[图片缺失]\n{p.name}",
            size=10,
            color=INK_MUTE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        return None
    if w and h:
        return slide.shapes.add_picture(str(p), x, y, w, h)
    if w:
        return slide.shapes.add_picture(str(p), x, y, width=w)
    return slide.shapes.add_picture(str(p), x, y, height=h)


def chip(slide, x, y, w, h, label, *, fill=ACCENT_S, color=DEEP, size=10):
    rect(slide, x, y, w, h, fill=fill)
    text(
        slide,
        x,
        y,
        w,
        h,
        label,
        size=size,
        bold=True,
        color=color,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )


# ---------- page frame ----------
prs = Presentation()
prs.slide_width = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]
TOTAL = 14


def page_bg(slide):
    rect(slide, 0, 0, W, H, fill=PAGE_BG)


def header(slide, idx, section, en):
    text(
        slide,
        MX,
        Inches(0.32),
        Inches(6),
        Inches(0.30),
        f"{idx:02d} / {TOTAL:02d}    {section}",
        size=10,
        color=INK_MUTE,
    )
    text(
        slide,
        Inches(7.0),
        Inches(0.32),
        Inches(5.78),
        Inches(0.30),
        en,
        size=10,
        color=INK_MUTE,
        align=PP_ALIGN.RIGHT,
    )
    hline(slide, MX, HEAD_LINE_Y, SAFE_W)


def footer(slide, note=""):
    hline(slide, MX, FOOT_LINE_Y, SAFE_W)
    text(
        slide,
        MX,
        Inches(7.15),
        Inches(8.0),
        Inches(0.25),
        "下肢步态训练辅助设备  ·  中期汇报  ·  2026.06",
        size=9,
        color=INK_MUTE,
    )
    if note:
        text(
            slide,
            Inches(7.0),
            Inches(7.15),
            Inches(5.78),
            Inches(0.25),
            note,
            size=9,
            color=INK_MUTE,
            align=PP_ALIGN.RIGHT,
        )


def page(idx, section, en):
    s = prs.slides.add_slide(BLANK)
    page_bg(s)
    header(s, idx, section, en)
    footer(s, section)
    return s


def section_title(slide, main, sub):
    text(
        slide,
        MX,
        CONTENT_TOP,
        SAFE_W,
        Inches(0.55),
        main,
        size=24,
        bold=True,
        color=INK,
    )
    text(slide, MX, Inches(1.55), SAFE_W, Inches(0.32), sub, size=11, color=ACCENT)


# ============================================================
# 封面
# ============================================================
def slide_cover():
    s = prs.slides.add_slide(BLANK)
    page_bg(s)
    rect(s, 0, 0, Inches(5.2), H, fill=DEEP)
    rect(s, Inches(0.7), Inches(2.0), Inches(0.55), Emu(12700), fill=ACCENT)
    text(
        s,
        Inches(0.7),
        Inches(2.20),
        Inches(4.3),
        Inches(0.32),
        "MIDTERM REPORT  ·  GAIT REHAB DEVICE",
        size=10,
        color=ACCENT_S,
    )
    text(
        s,
        Inches(0.7),
        Inches(2.60),
        Inches(4.3),
        Inches(2.0),
        "面向康复机构的\n下肢步态训练\n辅助设备",
        size=32,
        bold=True,
        color=WHITE,
        ls=1.18,
    )
    text(
        s,
        Inches(0.7),
        Inches(5.20),
        Inches(4.3),
        Inches(0.4),
        "一台会读懂步态相位的助行器",
        size=14,
        color=ACCENT_S,
    )
    text(
        s,
        Inches(0.7),
        Inches(6.70),
        Inches(4.3),
        Inches(0.32),
        "中期汇报    ·    2026.06",
        size=11,
        color=RGBColor(0xCF, 0xD8, 0xDC),
    )

    picture(
        s,
        "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_preview.png",
        Inches(5.6),
        Inches(1.5),
        w=Inches(7.2),
    )
    text(
        s,
        Inches(5.6),
        Inches(6.55),
        Inches(7.2),
        Inches(0.30),
        "图   仿生滚动足步态仿真——本设备的机械原型",
        size=9,
        color=INK_MUTE,
        align=PP_ALIGN.RIGHT,
    )


# ============================================================
# 目录
# ============================================================
def slide_toc():
    s = prs.slides.add_slide(BLANK)
    page_bg(s)
    text(
        s,
        MX,
        Inches(0.65),
        Inches(6),
        Inches(0.55),
        "汇报提纲",
        size=26,
        bold=True,
        color=INK,
    )
    text(
        s, MX, Inches(1.20), Inches(6), Inches(0.32), "Contents", size=11, color=ACCENT
    )
    hline(s, MX, Inches(1.65), SAFE_W)

    items = [
        ("01", "前期调研", "临床痛点 / 现有方案 / 学术原理"),
        ("02", "用户画像", "偏瘫患者 + 康复治疗师"),
        ("03", "设计目标", "五条可量化指标"),
        ("04", "功能定义", "感知 / 决策 / 执行 / 交互 / 安全"),
        ("05", "产品结构", "三视图 + 模块布置"),
        ("06", "故事框架", "训练前 / 中 / 后"),
        ("07", "草图与结构图", "整体 + 关键剖视"),
        ("08", "MuJoCo 仿真验证", "V05 至 V16 证据链"),
    ]
    col_w = Inches(5.95)
    base_y = Inches(2.0)
    row_h = Inches(0.65)
    for i, (no, name, desc) in enumerate(items):
        col = i // 4
        row = i % 4
        x = MX + (col_w + Inches(0.2)) * col
        y = base_y + row_h * row
        text(s, x, y, Inches(0.7), Inches(0.45), no, size=22, bold=True, color=ACCENT)
        text(
            s,
            x + Inches(0.75),
            y - Inches(0.02),
            col_w - Inches(0.8),
            Inches(0.32),
            name,
            size=14,
            bold=True,
            color=INK,
        )
        text(
            s,
            x + Inches(0.75),
            y + Inches(0.30),
            col_w - Inches(0.8),
            Inches(0.30),
            desc,
            size=10,
            color=INK_MUTE,
        )

    text(
        s,
        MX,
        Inches(5.10),
        SAFE_W,
        Inches(0.30),
        "贯穿主线",
        size=11,
        bold=True,
        color=ACCENT,
    )
    rect(s, MX, Inches(5.45), SAFE_W, Inches(0.55), fill=PANEL_BG, line=LINE)
    text(
        s,
        MX + Inches(0.20),
        Inches(5.45),
        SAFE_W - Inches(0.4),
        Inches(0.55),
        "临床痛点 → 学术原理 → 仿真验证 → 产品转译",
        size=12,
        bold=True,
        color=DEEP,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    text(
        s,
        MX,
        Inches(6.15),
        SAFE_W,
        Inches(0.32),
        "已完成 V01 至 V16 的仿真链,本次汇报核心是产品定义。",
        size=10.5,
        color=INK_SOFT,
    )


# ============================================================
# 1 调研 · 痛点
# ============================================================
def slide_research_pain():
    s = page(1, "前期调研", "Clinical Pain Points")
    section_title(
        s, "康复科里有三个一直没解决的麻烦", "走访三家三甲医院康复科与文献综述梳理出来"
    )

    pains = [
        (
            "01",
            "治疗师扛人扛到自己受伤",
            "一对一徒手辅助走 40 分钟,\n一天要陪 6 到 8 个患者,\n下班腰背要靠贴膏药。",
            "六成以上",
            "治疗师有慢性腰背痛",
        ),
        (
            "02",
            "黄金恢复期偏偏没人手",
            "脑卒中后头三到六个月最关键,\n但人手不够,\n每周训练量经常达不到指南推荐。",
            "每周 5 次",
            "才能改善步态",
        ),
        (
            "03",
            "训练数据全靠手写笔记",
            "对称性、推蹬力、步频\n几乎不留下数字,\n康复评估只能打主观分。",
            "0 条",
            "结构化数据",
        ),
    ]
    base_y = Inches(2.05)
    card_h = Inches(4.55)
    card_w = Inches(3.95)
    gap = Inches(0.12)
    for i, (no, h1, body, num, lbl) in enumerate(pains):
        x = MX + (card_w + gap) * i
        rect(s, x, base_y, card_w, card_h, fill=PANEL_BG, line=LINE)
        vbar(s, x, base_y, card_h, color=ACCENT)
        text(
            s,
            x + Inches(0.25),
            base_y + Inches(0.20),
            Inches(0.6),
            Inches(0.45),
            no,
            size=22,
            bold=True,
            color=ACCENT,
        )
        text(
            s,
            x + Inches(0.25),
            base_y + Inches(0.75),
            card_w - Inches(0.4),
            Inches(0.55),
            h1,
            size=14,
            bold=True,
            color=INK,
            ls=1.2,
        )
        rect(
            s,
            x + Inches(0.25),
            base_y + Inches(1.40),
            Inches(0.5),
            Emu(6350),
            fill=ACCENT,
        )
        text(
            s,
            x + Inches(0.25),
            base_y + Inches(1.55),
            card_w - Inches(0.4),
            Inches(1.55),
            body,
            size=11,
            color=INK_SOFT,
            ls=1.5,
        )
        text(
            s,
            x + Inches(0.25),
            base_y + Inches(3.20),
            card_w - Inches(0.4),
            Inches(0.75),
            num,
            size=32,
            bold=True,
            color=DEEP,
        )
        text(
            s,
            x + Inches(0.25),
            base_y + Inches(4.00),
            card_w - Inches(0.4),
            Inches(0.30),
            lbl,
            size=10,
            color=INK_MUTE,
        )

    text(
        s,
        MX,
        Inches(6.70),
        SAFE_W,
        Inches(0.30),
        "数据来源:2024 中国脑卒中流调蓝皮书、三家三甲医院康复科访谈,正式稿件中逐条标注引用。",
        size=9,
        color=INK_MUTE,
    )


# ============================================================
# 2 调研 · 现有方案
# ============================================================
def slide_research_compare():
    s = page(2, "前期调研", "Competitive Landscape")
    section_title(s, "市面上的方案,要么太重,要么不懂步态", "拉开五个维度看,缺口很清楚")

    headers = ["", "重量", "辅助方式", "相位识别", "可量化", "临床部署"]
    rows = [
        ("Lokomat 跑台外骨骼", "约 600 kg", "刚性牵引", "跑台时序", "有", "需专用机房"),
        ("ReWalk 行走外骨骼", "约 23 kg", "电机直驱", "按钮触发", "部分", "需平地"),
        ("徒手 + 平行杠", "—", "治疗师人力", "肉眼观察", "笔记", "占用治疗师"),
        ("本作品", "目标 ≤ 6 kg", "髋部 SEA 柔顺", "FSM 实时", "曲线导出", "可入科室"),
    ]
    col_x = [
        MX,
        Inches(3.3),
        Inches(5.2),
        Inches(7.0),
        Inches(8.7),
        Inches(10.4),
        Inches(12.78),
    ]
    head_y = Inches(2.10)
    rect(s, MX, head_y, SAFE_W, Inches(0.46), fill=DEEP)
    for i, h in enumerate(headers):
        text(
            s,
            col_x[i] + Inches(0.10),
            head_y,
            col_x[i + 1] - col_x[i] - Inches(0.10),
            Inches(0.46),
            h,
            size=11,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.LEFT if i == 0 else PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

    row_y = head_y + Inches(0.46)
    for r, row in enumerate(rows):
        rh = Inches(0.78)
        is_self = r == len(rows) - 1
        rect(
            s, MX, row_y, SAFE_W, rh, fill=ACCENT_S if is_self else PANEL_BG, line=LINE
        )
        for i, cell in enumerate(row):
            text(
                s,
                col_x[i] + Inches(0.10),
                row_y,
                col_x[i + 1] - col_x[i] - Inches(0.10),
                rh,
                cell,
                size=10.5,
                bold=(i == 0) or is_self,
                color=DEEP if is_self else INK,
                align=PP_ALIGN.LEFT if i == 0 else PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE,
            )
        row_y += rh

    conc_y = row_y + Inches(0.18)
    rect(s, MX, conc_y, SAFE_W, Inches(0.55), fill=PANEL_BG, line=ACCENT, lw=1.2)
    text(
        s,
        MX + Inches(0.25),
        conc_y,
        Inches(0.7),
        Inches(0.55),
        "结论",
        size=11,
        bold=True,
        color=ACCENT,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    text(
        s,
        MX + Inches(1.0),
        conc_y,
        SAFE_W - Inches(1.2),
        Inches(0.55),
        "市场缺口 = 「轻」「柔」「懂相位」「给数据」四件事同时做到的产品。",
        size=12,
        bold=True,
        color=INK,
        anchor=MSO_ANCHOR.MIDDLE,
    )


# ============================================================
# 3 调研 · 学术原理
# ============================================================
def slide_research_theory():
    s = page(3, "前期调研", "Theoretical Foundation")
    section_title(
        s,
        "「低力矩辅助」不是想出来的,是被动动力学算出来的",
        "三条物理事实,直接成了产品的设计前提",
    )

    L = MX
    LW = Inches(5.7)
    text(
        s,
        L,
        Inches(2.05),
        LW,
        Inches(0.35),
        "决定设计哲学的三条事实",
        size=13,
        bold=True,
        color=DEEP,
    )

    facts = [
        (
            "重力 + 几何就能走路",
            "斜面上没有任何主动驱动,腿和躯干仍然能走出周期步态。\n"
            "推论:辅助力矩只补缺口,不替代肌肉。",
        ),
        (
            "能量主要在触地瞬间被吃掉",
            "无论 Rimless wheel 还是 Compass 模型,碰撞那一下的损耗最大。\n"
            "推论:推蹬与触地准备这两个相位是辅助介入的最佳窗口。",
        ),
        (
            "滚动足比平足更接近真人",
            "把足底改成滚动曲面后,极限环更宽,对参数也不那么挑剔。\n"
            "推论:足底辅助件做仿生滚动,而不是平鞋底。",
        ),
    ]
    fy = Inches(2.50)
    for h1, body in facts:
        rect(s, L, fy, Emu(50800), Inches(1.30), fill=ACCENT)
        text(
            s,
            L + Inches(0.32),
            fy + Inches(0.05),
            LW - Inches(0.4),
            Inches(0.35),
            h1,
            size=12,
            bold=True,
            color=INK,
        )
        text(
            s,
            L + Inches(0.32),
            fy + Inches(0.42),
            LW - Inches(0.4),
            Inches(0.85),
            body,
            size=10.5,
            color=INK_SOFT,
            ls=1.4,
        )
        fy += Inches(1.42)

    R = Inches(6.80)
    RW = Inches(6.0)
    rect(s, R, Inches(2.05), RW, Inches(4.45), fill=PANEL_BG, line=LINE)
    picture(
        s,
        "v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png",
        R + Inches(0.10),
        Inches(2.20),
        w=RW - Inches(0.20),
        h=Inches(3.95),
    )
    text(
        s,
        R + Inches(0.10),
        Inches(6.18),
        RW - Inches(0.20),
        Inches(0.30),
        "图   纯被动极限环 Poincaré 收敛  ·  V05 已完成的仿真",
        size=9.5,
        color=INK_MUTE,
        align=PP_ALIGN.CENTER,
    )


# ============================================================
# 4 用户画像
# ============================================================
def slide_personas():
    s = page(4, "用户画像", "Personas")
    section_title(
        s,
        "两个人,两本帐,要同时满足才进得了科室",
        "主用户决定产品形态,次用户决定能不能落地",
    )

    L = MX
    LW = Inches(6.05)
    rect(s, L, Inches(2.05), LW, Inches(4.85), fill=PANEL_BG, line=LINE)
    vbar(s, L, Inches(2.05), Inches(4.85), color=ACCENT)
    text(
        s,
        L + Inches(0.25),
        Inches(2.18),
        Inches(2.5),
        Inches(0.30),
        "主用户  /  PRIMARY",
        size=10,
        bold=True,
        color=ACCENT,
    )
    text(
        s,
        L + Inches(0.25),
        Inches(2.50),
        LW - Inches(0.4),
        Inches(0.45),
        "陈先生  ·  58 岁  ·  脑卒中后 4 个月",
        size=17,
        bold=True,
        color=INK,
    )
    text(
        s,
        L + Inches(0.25),
        Inches(3.00),
        LW - Inches(0.4),
        Inches(0.30),
        "Brunnstrom IV 期  /  肌力 3-4 级  /  能短距独立行走但跛行明显",
        size=10,
        color=INK_SOFT,
    )

    chip(
        s,
        L + Inches(0.25),
        Inches(3.45),
        Inches(0.7),
        Inches(0.30),
        "目标",
        fill=DEEP,
        color=WHITE,
    )
    text(
        s,
        L + Inches(1.05),
        Inches(3.45),
        LW - Inches(1.25),
        Inches(0.30),
        "想在六个月内尽量恢复对称步态,回到社区生活",
        size=11,
        color=INK,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    chip(
        s,
        L + Inches(0.25),
        Inches(3.92),
        Inches(0.7),
        Inches(0.30),
        "痛点",
        fill=ACCENT,
        color=WHITE,
    )
    pps = [
        "患侧推蹬不足,健侧代偿,越走越歪",
        "怕摔,所以走得慢,训练量上不去",
        "每周治疗时间有限,在家不敢自己练",
    ]
    for i, t in enumerate(pps):
        text(
            s,
            L + Inches(1.05),
            Inches(3.92) + Inches(0.32) * i,
            LW - Inches(1.25),
            Inches(0.32),
            "·  " + t,
            size=10.5,
            color=INK_SOFT,
        )

    chip(
        s,
        L + Inches(0.25),
        Inches(5.00),
        Inches(0.7),
        Inches(0.30),
        "金句",
        fill=PAGE_BG,
        color=DEEP,
    )
    text(
        s,
        L + Inches(1.05),
        Inches(5.05),
        LW - Inches(1.25),
        Inches(1.65),
        "「我不是想让它替我走,我是想自己走对,\n" "  快摔的时候它稍微帮一下就行。」",
        size=12,
        color=DEEP,
        ls=1.5,
    )

    R = Inches(7.00)
    RW = Inches(6.05)
    rect(s, R, Inches(2.05), RW, Inches(4.85), fill=PANEL_BG, line=LINE)
    vbar(s, R, Inches(2.05), Inches(4.85), color=DEEP)
    text(
        s,
        R + Inches(0.25),
        Inches(2.18),
        Inches(2.5),
        Inches(0.30),
        "次用户  /  SECONDARY",
        size=10,
        bold=True,
        color=DEEP,
    )
    text(
        s,
        R + Inches(0.25),
        Inches(2.50),
        RW - Inches(0.4),
        Inches(0.45),
        "李治疗师  ·  31 岁  ·  康复科 6 年",
        size=17,
        bold=True,
        color=INK,
    )
    text(
        s,
        R + Inches(0.25),
        Inches(3.00),
        RW - Inches(0.4),
        Inches(0.30),
        "三甲医院康复科  /  每日 6-8 名患者  /  腰椎间盘突出",
        size=10,
        color=INK_SOFT,
    )

    chip(
        s,
        R + Inches(0.25),
        Inches(3.45),
        Inches(0.7),
        Inches(0.30),
        "目标",
        fill=DEEP,
        color=WHITE,
    )
    text(
        s,
        R + Inches(1.05),
        Inches(3.45),
        RW - Inches(1.25),
        Inches(0.30),
        "把重复体力活交出去,自己专注评估和方案调整",
        size=11,
        color=INK,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    chip(
        s,
        R + Inches(0.25),
        Inches(3.92),
        Inches(0.7),
        Inches(0.30),
        "痛点",
        fill=ACCENT,
        color=WHITE,
    )
    pts = [
        "扶腰托腿一整天,下班腰背全是冷敷贴",
        "评估靠 Tinetti、FAC 主观打分,数据不连续",
        "调参全凭经验,新人很难快速上手",
    ]
    for i, t in enumerate(pts):
        text(
            s,
            R + Inches(1.05),
            Inches(3.92) + Inches(0.32) * i,
            RW - Inches(1.25),
            Inches(0.32),
            "·  " + t,
            size=10.5,
            color=INK_SOFT,
        )

    chip(
        s,
        R + Inches(0.25),
        Inches(5.00),
        Inches(0.7),
        Inches(0.30),
        "金句",
        fill=PAGE_BG,
        color=DEEP,
    )
    text(
        s,
        R + Inches(1.05),
        Inches(5.05),
        RW - Inches(1.25),
        Inches(1.65),
        "「最好我看一眼平板,就知道这周\n" "  患者哪个相位还差,然后只调一个旋钮。」",
        size=12,
        color=DEEP,
        ls=1.5,
    )


# ============================================================
# 5 设计目标
# ============================================================
def slide_goals():
    s = page(5, "设计目标", "Design Targets")
    section_title(
        s, "把「想做好」翻译成五个能验收的数", "每条数字背后都对应一段已经在跑的仿真"
    )

    targets = [
        (
            "安全",
            "辅助力矩",
            "≤ 8",
            "N·m",
            "覆盖患者推蹬缺口 5-7 N·m,\n但低于致伤阈值",
            "V14c 摆臂质量扫描",
        ),
        (
            "精准",
            "相位识别",
            "≥ 90",
            "%",
            "FSM 在四相位上的识别正确率,\n失败相位自动降级",
            "V13.6 事件驱动 FSM",
        ),
        (
            "渐进",
            "辅助强度",
            "0–100",
            "%",
            "治疗师按周下调,\n用「撤辅助」量化恢复进度",
            "V08 准被动补能",
        ),
        (
            "可量化",
            "训练指标",
            "5",
            "类",
            "对称性 / 步频 / 推蹬力 /\n触地冲击 / 摆腿幅度",
            "V12 能量与 CoT",
        ),
        (
            "临床友好",
            "穿戴时间",
            "≤ 5",
            "min",
            "单人完成穿戴,\n不需要把患者吊起来",
            "结构方案 V15 SEA",
        ),
    ]
    base_y = Inches(2.05)
    card_w = Inches(2.40)
    gap = Inches(0.06)
    card_h = Inches(4.65)
    for i, (tag, name, num, unit, body, evi) in enumerate(targets):
        x = MX + (card_w + gap) * i
        rect(s, x, base_y, card_w, card_h, fill=PANEL_BG, line=LINE)
        rect(s, x, base_y, card_w, Inches(0.42), fill=DEEP)
        text(
            s,
            x,
            base_y,
            card_w,
            Inches(0.42),
            tag,
            size=12,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

        text(
            s,
            x + Inches(0.18),
            base_y + Inches(0.55),
            card_w - Inches(0.36),
            Inches(0.30),
            name,
            size=10,
            color=INK_MUTE,
        )

        text(
            s,
            x + Inches(0.18),
            base_y + Inches(0.90),
            card_w - Inches(0.6),
            Inches(0.95),
            num,
            size=36,
            bold=True,
            color=ACCENT,
        )
        text(
            s,
            x + Inches(1.85),
            base_y + Inches(1.45),
            Inches(0.55),
            Inches(0.32),
            unit,
            size=11,
            color=ACCENT,
        )

        rect(
            s,
            x + Inches(0.18),
            base_y + Inches(2.05),
            Inches(0.5),
            Emu(6350),
            fill=ACCENT,
        )
        text(
            s,
            x + Inches(0.18),
            base_y + Inches(2.20),
            card_w - Inches(0.36),
            Inches(1.55),
            body,
            size=10,
            color=INK_SOFT,
            ls=1.45,
        )

        text(
            s,
            x + Inches(0.18),
            base_y + Inches(3.85),
            card_w - Inches(0.36),
            Inches(0.30),
            "支撑证据",
            size=9,
            color=ACCENT,
            bold=True,
        )
        text(
            s,
            x + Inches(0.18),
            base_y + Inches(4.15),
            card_w - Inches(0.36),
            Inches(0.45),
            evi,
            size=9.5,
            color=DEEP,
            ls=1.3,
        )


# ============================================================
# 6 功能定义
# ============================================================
def slide_functions():
    s = page(6, "功能定义", "System Architecture")
    section_title(
        s,
        "五层架构:从足底压力一路传到治疗师的平板",
        "每一层都对应一些硬件 + 一段验证过的算法",
    )

    layers = [
        (
            "L5",
            "感知层",
            "FSR 鞋垫 ×8 区  +  髋膝 IMU/编码器  +  躯干姿态",
            "采样 200 Hz,触地、推蹬、摆腿三类事件检测延迟 < 20 ms",
        ),
        (
            "L4",
            "决策层",
            "事件驱动 FSM:HS → FF → MS → HO → TO 四相位",
            "V13.6 已实测:切片 C 通过率 11.1%,失败相位自动降级",
        ),
        (
            "L3",
            "执行层",
            "髋部 SEA(电机 + 串联弹性) + 力矩饱和限幅",
            "V15 仿真支架已搭好,正在扫不同弹性系数下的冲击损耗",
        ),
        (
            "L2",
            "交互层",
            "治疗师 Pad:本周相位曲线  +  单旋钮辅助强度",
            "图形化展示触地冲击、推蹬力、对称性,导出 CSV",
        ),
        (
            "L1",
            "安全层",
            "硬件力矩限位  +  紧急释放扣  +  跌倒姿态检测",
            "三重串联,任意一层触发即切断辅助",
        ),
    ]
    base_y = Inches(2.05)
    row_h = Inches(0.92)
    for i, (lv, name, hw, sw) in enumerate(layers):
        y = base_y + row_h * i
        text(
            s,
            MX,
            y,
            Inches(0.55),
            row_h - Inches(0.08),
            lv,
            size=20,
            bold=True,
            color=ACCENT_S,
            anchor=MSO_ANCHOR.MIDDLE,
            align=PP_ALIGN.CENTER,
        )
        rect(s, MX + Inches(0.55), y, Inches(1.85), row_h - Inches(0.10), fill=DEEP)
        text(
            s,
            MX + Inches(0.55),
            y,
            Inches(1.85),
            row_h - Inches(0.10),
            name,
            size=14,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        rect(
            s,
            MX + Inches(2.45),
            y,
            SAFE_W - Inches(2.45),
            row_h - Inches(0.10),
            fill=PANEL_BG,
            line=LINE,
        )
        text(
            s,
            MX + Inches(2.65),
            y + Inches(0.08),
            SAFE_W - Inches(2.85),
            Inches(0.36),
            hw,
            size=11.5,
            bold=True,
            color=INK,
        )
        text(
            s,
            MX + Inches(2.65),
            y + Inches(0.46),
            SAFE_W - Inches(2.85),
            Inches(0.38),
            sw,
            size=10,
            color=INK_MUTE,
        )


# ============================================================
# 7 产品结构
# ============================================================
def slide_structure():
    s = page(7, "产品结构", "Component Layout")
    section_title(
        s,
        "重的贴近躯干,感的贴近地面",
        "布置直接来自 V14c(质量约束)和 V15(髋部 SEA)的仿真结论",
    )

    L = MX
    LW = Inches(5.5)
    rect(s, L, Inches(2.05), LW, Inches(4.85), fill=PANEL_BG, line=LINE)

    cx = L + Inches(2.75)
    cy_head = Inches(2.30)
    head = s.shapes.add_shape(
        MSO_SHAPE.OVAL, cx - Inches(0.28), cy_head, Inches(0.55), Inches(0.55)
    )
    set_fill(head, INK_SOFT)
    no_line(head)
    body = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        cx - Inches(0.42),
        cy_head + Inches(0.55),
        Inches(0.85),
        Inches(1.35),
    )
    set_fill(body, INK_SOFT)
    no_line(body)
    legL = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        cx - Inches(0.40),
        cy_head + Inches(1.92),
        Inches(0.30),
        Inches(1.85),
    )
    set_fill(legL, INK_SOFT)
    no_line(legL)
    legR = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        cx + Inches(0.10),
        cy_head + Inches(1.92),
        Inches(0.30),
        Inches(1.85),
    )
    set_fill(legR, INK_SOFT)
    no_line(legR)
    bag = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        cx + Inches(0.55),
        cy_head + Inches(0.65),
        Inches(0.55),
        Inches(0.95),
    )
    set_fill(bag, ACCENT)
    no_line(bag)
    text(
        s,
        cx + Inches(0.55),
        cy_head + Inches(0.65),
        Inches(0.55),
        Inches(0.95),
        "MCU",
        size=10,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    hip = s.shapes.add_shape(
        MSO_SHAPE.OVAL,
        cx - Inches(0.55),
        cy_head + Inches(1.78),
        Inches(1.1),
        Inches(0.32),
    )
    set_fill(hip, ACCENT)
    no_line(hip)
    footL = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        cx - Inches(0.50),
        cy_head + Inches(3.78),
        Inches(0.42),
        Inches(0.18),
    )
    set_fill(footL, DEEP)
    no_line(footL)
    footR = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        cx + Inches(0.10),
        cy_head + Inches(3.78),
        Inches(0.42),
        Inches(0.18),
    )
    set_fill(footR, DEEP)
    no_line(footR)

    annots = [
        (
            "① 髋部 SEA 模组",
            "BLDC + 串联弹簧 + 编码器",
            L + Inches(0.10),
            cy_head + Inches(1.65),
            True,
        ),
        (
            "② 背包电控",
            "电池 + MCU + 蓝牙",
            cx + Inches(1.20),
            cy_head + Inches(0.65),
            False,
        ),
        (
            "③ 大腿 / 小腿连杆",
            "碳纤维管 + 快拆扣",
            cx + Inches(1.20),
            cy_head + Inches(2.40),
            False,
        ),
        (
            "④ 8 区 FSR 鞋垫",
            "触地 / 推蹬事件检测",
            L + Inches(0.10),
            cy_head + Inches(3.78),
            True,
        ),
    ]
    for label, desc, ax, ay, left in annots:
        text(
            s,
            ax,
            ay,
            Inches(2.05),
            Inches(0.30),
            label,
            size=11,
            bold=True,
            color=ACCENT,
            align=PP_ALIGN.RIGHT if left else PP_ALIGN.LEFT,
        )
        text(
            s,
            ax,
            ay + Inches(0.28),
            Inches(2.05),
            Inches(0.30),
            desc,
            size=9.5,
            color=INK_MUTE,
            align=PP_ALIGN.RIGHT if left else PP_ALIGN.LEFT,
        )

    R = Inches(6.30)
    RW = Inches(6.55)
    text(
        s,
        R,
        Inches(2.05),
        RW,
        Inches(0.35),
        "关键 BOM 与重量预算",
        size=13,
        bold=True,
        color=DEEP,
    )

    bom = [
        ("髋部 SEA × 2", "电机 + 弹簧 + 编码器", "2.4 kg"),
        ("电池 + MCU 背包", "20 V 4 Ah Li-ion", "1.2 kg"),
        ("结构连杆 / 绑带", "碳纤维 + 尼龙", "1.6 kg"),
        ("FSR 鞋垫 × 2", "8 区压力 + 蓝牙", "0.4 kg"),
        ("总重(目标)", "≤ 6 kg", "—"),
    ]
    by = Inches(2.45)
    rect(s, R, by, RW, Inches(0.36), fill=DEEP)
    headers_bom = ["模块", "核心件", "重量"]
    bom_x = [Inches(0.10), Inches(2.50), Inches(5.50)]
    for i, h in enumerate(headers_bom):
        text(
            s,
            R + bom_x[i],
            by,
            Inches(2.5),
            Inches(0.36),
            h,
            size=10.5,
            bold=True,
            color=WHITE,
            anchor=MSO_ANCHOR.MIDDLE,
        )
    by += Inches(0.36)
    for i, (m, c, w) in enumerate(bom):
        is_total = i == len(bom) - 1
        rh = Inches(0.40)
        rect(s, R, by, RW, rh, fill=ACCENT_S if is_total else PANEL_BG, line=LINE)
        text(
            s,
            R + bom_x[0],
            by,
            Inches(2.4),
            rh,
            m,
            size=10.5,
            bold=is_total,
            color=INK,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        text(
            s,
            R + bom_x[1],
            by,
            Inches(3.0),
            rh,
            c,
            size=10,
            color=INK_SOFT,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        text(
            s,
            R + bom_x[2],
            by,
            Inches(1.0),
            rh,
            w,
            size=10.5,
            bold=is_total,
            color=ACCENT,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        by += rh

    text(
        s,
        R,
        by + Inches(0.20),
        RW,
        Inches(0.32),
        "三条布置原则",
        size=12,
        bold=True,
        color=DEEP,
    )
    rules = [
        "重物贴近躯干重心,减少摆腿惯量",
        "感测件贴近事件源:FSR 在足底,IMU 在小腿与髋",
        "电气与机械解耦,紧急释放只需拔扣,不靠软件",
    ]
    for i, r in enumerate(rules):
        text(
            s,
            R + Inches(0.12),
            by + Inches(0.55) + Inches(0.32) * i,
            RW - Inches(0.2),
            Inches(0.30),
            "·  " + r,
            size=10,
            color=INK_SOFT,
        )


# ============================================================
# 8 故事框架
# ============================================================
def slide_story():
    s = page(8, "故事框架", "User Journey")
    section_title(
        s,
        "把一次康复训练拆成三幕,看设备在每幕里做什么",
        "训练前 / 训练中 / 训练后,患者-治疗师-设备 三方",
    )

    # 标题条
    bar_y = Inches(2.05)
    bar_h = Inches(0.42)
    sects = ["训练前  ·  穿戴与基线", "训练中  ·  相位辅助", "训练后  ·  数据复盘"]
    seg_w = SAFE_W / 3
    for i, t in enumerate(sects):
        rect(
            s,
            MX + seg_w * i + Emu(12700) * (1 if i > 0 else 0),
            bar_y,
            seg_w - (Emu(12700) if i > 0 else 0),
            bar_h,
            fill=DEEP,
        )
        text(
            s,
            MX + seg_w * i,
            bar_y,
            seg_w,
            bar_h,
            t,
            size=12.5,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

    # 三角色行
    actor_w = Inches(1.30)
    body_x = MX + actor_w + Inches(0.05)
    body_w = SAFE_W - actor_w - Inches(0.05)
    body_seg = body_w / 3

    actors = [
        (
            "患者",
            INK_SOFT,
            [
                "签到坐下,治疗师帮忙穿戴下肢部分",
                "按自己节奏走,跟着设备的轻推蹬节拍",
                "在 Pad 上看对称性曲线,知道今天进步在哪",
            ],
        ),
        (
            "治疗师",
            ACCENT,
            [
                "调辅助强度旋钮,设定本次目标步数",
                "站旁边观察姿态,设备替自己发力",
                "导出 CSV 写进电子病历,一周后看趋势",
            ],
        ),
        (
            "设备",
            DEEP,
            [
                "FSR 自检,标定患者站立基线,绿灯",
                "FSM 实时识别相位,推蹬窗口给一段柔顺力矩",
                "断电进入回顾,生成本次训练 5 项指标",
            ],
        ),
    ]
    row_y = bar_y + bar_h + Inches(0.18)
    row_h = Inches(1.30)
    for r, (name, color, cells) in enumerate(actors):
        y = row_y + row_h * r
        rect(s, MX, y, actor_w, row_h - Inches(0.10), fill=PANEL_BG, line=LINE)
        vbar(s, MX, y, row_h - Inches(0.10), color=color)
        text(
            s,
            MX,
            y,
            actor_w,
            row_h - Inches(0.10),
            name,
            size=14,
            bold=True,
            color=color,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        for i, c in enumerate(cells):
            cx = body_x + body_seg * i
            rect(
                s,
                cx,
                y,
                body_seg - Inches(0.05),
                row_h - Inches(0.10),
                fill=PANEL_BG,
                line=LINE,
            )
            text(
                s,
                cx + Inches(0.18),
                y + Inches(0.08),
                body_seg - Inches(0.30),
                row_h - Inches(0.25),
                c,
                size=10.5,
                color=INK,
                ls=1.4,
            )

    tip_y = row_y + row_h * 3 + Inches(0.05)
    rect(s, MX, tip_y, SAFE_W, Inches(0.50), fill=ACCENT_S)
    text(
        s,
        MX + Inches(0.20),
        tip_y,
        SAFE_W - Inches(0.4),
        Inches(0.50),
        "三幕之间的关键交接 ── 穿戴对了才识别得准,识别准了数据才有效。所以 L1 感知层是整条体验的起点。",
        size=11,
        bold=True,
        color=DEEP,
        anchor=MSO_ANCHOR.MIDDLE,
    )


# ============================================================
# 9 草图与结构图
# ============================================================
def slide_sketch():
    s = page(9, "草图与结构图", "Sketches & Mechanism")
    section_title(
        s,
        "三张图说清楚:它长什么样、怎么穿、怎么发力",
        "整体效果图 + 髋部 SEA 剖视 + 步态相位时序",
    )

    col_w = Inches(4.00)
    gap = Inches(0.075)
    base_y = Inches(2.05)
    titles = ["① 整体穿戴效果", "② 髋部 SEA 剖视", "③ 步态相位时序"]
    captions = [
        "穿上后髋膝处只多两片薄壳,\n背包贴腰,鞋垫嵌在鞋里。\n外观更像运动护具而不是外骨骼。",
        "电机 → 谐波减速 → SEA 弹簧 → 输出端,\n弹簧形变作力矩反馈,自带柔顺。\nV15 仿真支架已搭好。",
        "横轴时间,纵轴髋角 + 足底压力 + FSM,\n四相位用色块标出辅助介入窗口。\n直接复用 V13.6 的输出。",
    ]
    sources = [
        "手绘 → 后期 KeyShot 渲染",
        "SolidWorks 剖视 / V15 装配占位",
        "V13.6 baseline_report",
    ]
    img_paths = [
        "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_preview.png",
        "v15_hip_sea_scaffold/out/v15_smoke_k0100_preview.png",
        "v13_6_event_driven_fsm/out/v13_6_baseline_report.png",
    ]
    card_h = Inches(4.85)
    for i in range(3):
        x = MX + (col_w + gap) * i
        rect(s, x, base_y, col_w, card_h, fill=PANEL_BG, line=LINE)
        text(
            s,
            x + Inches(0.20),
            base_y + Inches(0.10),
            col_w - Inches(0.4),
            Inches(0.32),
            titles[i],
            size=13,
            bold=True,
            color=DEEP,
        )
        picture(
            s,
            img_paths[i],
            x + Inches(0.20),
            base_y + Inches(0.50),
            w=col_w - Inches(0.4),
            h=Inches(2.30),
        )
        text(
            s,
            x + Inches(0.20),
            base_y + Inches(2.95),
            col_w - Inches(0.4),
            Inches(0.30),
            "来源 · " + sources[i],
            size=9,
            color=ACCENT,
            bold=True,
        )
        rect(
            s,
            x + Inches(0.20),
            base_y + Inches(3.25),
            Inches(0.4),
            Emu(6350),
            fill=ACCENT,
        )
        text(
            s,
            x + Inches(0.20),
            base_y + Inches(3.35),
            col_w - Inches(0.4),
            Inches(1.40),
            captions[i],
            size=10.5,
            color=INK_SOFT,
            ls=1.4,
        )

    text(
        s,
        MX,
        Inches(6.95),
        SAFE_W,
        Inches(0.30),
        "①、② 当前为占位,正式答辩时替换为手绘 + 渲染图;③ 直接来自 V13.6 仿真输出。",
        size=9,
        color=INK_MUTE,
    )


# ============================================================
# 10 仿真总览
# ============================================================
def slide_sim_overview():
    s = page(10, "MuJoCo 仿真验证", "Verification Overview")
    section_title(
        s,
        "16 个版本拼成一条「机械-控制-电机」的证据链",
        "每一段都对应产品上的一个具体设计决定",
    )

    nodes = [
        ("V05", "纯被动极限环", "证明步态本身能稳定", OK),
        ("V10", "滚动足仿生", "确定足底机械形态", OK),
        ("V11", "鲁棒性边界", "划出失败地形", OK),
        ("V12", "能量与 CoT", "确定辅助介入窗口", OK),
        ("V13", "参数容差", "给设计公差打底", OK),
        ("V13.6", "事件驱动 FSM", "决策层算法", OK),
        ("V14c", "摆臂质量约束", "限定背包/连杆质量", OK),
        ("V15", "髋部 SEA", "执行层硬件原型", WARN),
        ("V16", "电机动力学", "驱动选型红线", WARN),
    ]
    n = len(nodes)
    line_y = Inches(3.85)
    line_x0 = MX + Inches(0.45)
    line_w = SAFE_W - Inches(0.90)
    rect(s, line_x0, line_y, line_w, Emu(19050), fill=DEEP)
    seg = line_w / (n - 1)

    for i, (ver, name, role, color) in enumerate(nodes):
        cx = line_x0 + seg * i
        ox = cx - Inches(0.20)
        oy = line_y - Inches(0.18)
        node = s.shapes.add_shape(MSO_SHAPE.OVAL, ox, oy, Inches(0.40), Inches(0.40))
        set_fill(node, color)
        set_line(node, WHITE, 1.5)

        # 上方:版本号 + 名称(版本号紧贴节点上,名称在更上面)
        ver_y = oy - Inches(0.42)
        name_y = oy - Inches(0.78)
        text(
            s,
            cx - Inches(0.95),
            name_y,
            Inches(1.9),
            Inches(0.30),
            name,
            size=10,
            color=INK,
            align=PP_ALIGN.CENTER,
        )
        text(
            s,
            cx - Inches(0.95),
            ver_y,
            Inches(1.9),
            Inches(0.28),
            ver,
            size=10.5,
            bold=True,
            color=ACCENT,
            align=PP_ALIGN.CENTER,
        )
        # 下方:角色
        role_y = oy + Inches(0.50)
        text(
            s,
            cx - Inches(1.05),
            role_y,
            Inches(2.1),
            Inches(0.40),
            role,
            size=9.5,
            color=INK_SOFT,
            align=PP_ALIGN.CENTER,
            ls=1.3,
        )

    # 图例
    leg_y = Inches(5.55)
    text(
        s,
        MX,
        leg_y,
        Inches(1.0),
        Inches(0.30),
        "图例",
        size=10.5,
        bold=True,
        color=INK_SOFT,
    )
    legs = [("已完成", OK), ("进行中 / 有发现", WARN)]
    for i, (t, c) in enumerate(legs):
        bx = MX + Inches(0.7) + Inches(2.0) * i
        dot = s.shapes.add_shape(
            MSO_SHAPE.OVAL, bx, leg_y + Inches(0.06), Inches(0.18), Inches(0.18)
        )
        set_fill(dot, c)
        no_line(dot)
        text(
            s,
            bx + Inches(0.30),
            leg_y,
            Inches(2),
            Inches(0.30),
            t,
            size=10,
            color=INK_SOFT,
        )

    box_y = Inches(6.25)
    rect(s, MX, box_y, SAFE_W, Inches(0.55), fill=ACCENT_S)
    text(
        s,
        MX + Inches(0.20),
        box_y,
        SAFE_W - Inches(0.4),
        Inches(0.55),
        "V16 最新发现:MX-64AR 库仑摩擦 τ_C 落入 FSM 失败带正中央,选型必须做实测,不能查 spec。",
        size=11,
        bold=True,
        color=DEEP,
        anchor=MSO_ANCHOR.MIDDLE,
    )


# ============================================================
# 11 已完成的硬证据
# ============================================================
def slide_sim_done():
    s = page(11, "MuJoCo 仿真验证", "Completed Evidence")
    section_title(s, "已经拿到的四块硬证据", "支撑「设计目标」可行性的核心仿真")

    cells = [
        (
            "V05  纯被动极限环",
            "v05_hybrid_compass_proof/out/hybrid_compass_poincare_report.png",
            "Poincaré 截面收敛到不动点,说明步态周期稳定。\n含义:辅助力矩做小不做大。",
        ),
        (
            "V10  滚动足准被动行走",
            "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_report.png",
            "连续多步真实接触下行走稳定。\n含义:足底鞋垫采用仿生滚动曲面。",
        ),
        (
            "V13.6  事件驱动 FSM",
            "v13_6_event_driven_fsm/out/v13_6_baseline_report.png",
            "四相位时序划分,切片 C 通过率 11.1%。\n含义:决策层算法选型确认。",
        ),
        (
            "V14c  摆臂质量约束",
            "v14c_arm_mass_lightening/out/v14c_C_heatmaps.png",
            "m=0.05 通过 3/36,m=0.01 升至 5/36。\n含义:背包+连杆总质量必须严控。",
        ),
    ]
    gw = Inches(6.05)
    gh = Inches(2.30)
    gap_x = Inches(0.12)
    gap_y = Inches(0.20)
    base_y = Inches(2.05)
    for i, (title, img, cap) in enumerate(cells):
        col = i % 2
        row = i // 2
        x = MX + (gw + gap_x) * col
        y = base_y + (gh + gap_y) * row
        rect(s, x, y, gw, gh, fill=PANEL_BG, line=LINE)
        rect(s, x, y, Inches(0.5), Emu(6350), fill=ACCENT)
        text(
            s,
            x + Inches(0.15),
            y + Inches(0.05),
            gw - Inches(0.3),
            Inches(0.30),
            title,
            size=12,
            bold=True,
            color=DEEP,
        )
        picture(
            s,
            img,
            x + Inches(3.05),
            y + Inches(0.10),
            w=gw - Inches(3.20),
            h=gh - Inches(0.20),
        )
        text(
            s,
            x + Inches(0.15),
            y + Inches(0.45),
            Inches(2.85),
            gh - Inches(0.55),
            cap,
            size=10.5,
            color=INK_SOFT,
            ls=1.5,
        )


# ============================================================
# 12 进行中与下一步
# ============================================================
def slide_sim_next():
    s = page(12, "MuJoCo 仿真验证", "Ongoing & Next")
    section_title(
        s, "正在做的两件事 + 接下来的路线", "把仿真链接到样机,先要解决 V16 的电机难题"
    )

    # V15
    L = MX
    LW = Inches(6.20)
    rect(s, L, Inches(2.05), LW, Inches(2.45), fill=PANEL_BG, line=LINE)
    rect(s, L, Inches(2.05), Inches(0.5), Emu(6350), fill=WARN)
    text(
        s,
        L + Inches(0.20),
        Inches(2.13),
        LW - Inches(0.4),
        Inches(0.32),
        "V15  髋部 SEA 仿真支架  ·  进行中",
        size=12,
        bold=True,
        color=DEEP,
    )
    picture(
        s,
        "v15_hip_sea_scaffold/out/v15_C_heatmaps.png",
        L + Inches(0.25),
        Inches(2.50),
        w=Inches(2.30),
        h=Inches(1.85),
    )
    text(
        s,
        L + Inches(2.70),
        Inches(2.50),
        LW - Inches(2.85),
        Inches(2.0),
        "已搭好 SEA 装配 + 弹性扫描框架,\n"
        "smoke 通过 (k=0/100 可对比)。\n\n"
        "下一步:\n"
        "·  扫 k ∈ [50, 500] N/rad 取最优\n"
        "·  对比有/无 SEA 的触地冲击曲线\n"
        "·  锁定弹簧选型",
        size=10,
        color=INK_SOFT,
        ls=1.4,
    )

    # V16
    rect(s, L, Inches(4.65), LW, Inches(2.30), fill=PANEL_BG, line=LINE)
    rect(s, L, Inches(4.65), Inches(0.5), Emu(6350), fill=ACCENT)
    text(
        s,
        L + Inches(0.20),
        Inches(4.73),
        LW - Inches(0.4),
        Inches(0.32),
        "V16  电机动力学  ·  关键发现",
        size=12,
        bold=True,
        color=ACCENT,
    )
    text(
        s,
        L + Inches(0.20),
        Inches(5.10),
        LW - Inches(0.4),
        Inches(1.80),
        "MX-64AR 一阶模型显示库仑摩擦 τ_C 与 FSM 形成耦合共振,扫描结果非单调:\n"
        "成功带 ∈ {0, 0.034, ≥0.27} N·m,失败带 ∈ [0.013, 0.20] N·m。\n"
        "MX-64 spec 落在 0.20 正中央。\n\n"
        "三选一:\n"
        "·  方案 A:换低摩擦关节  ·  方案 B:V13.7 摩擦补偿(推荐先试)  ·  方案 C:选恢复带电机",
        size=10,
        color=INK_SOFT,
        ls=1.4,
    )

    # 路线图
    R = Inches(7.05)
    RW = Inches(5.78)
    text(
        s,
        R,
        Inches(2.05),
        RW,
        Inches(0.35),
        "下一阶段路线图",
        size=13,
        bold=True,
        color=DEEP,
    )

    steps = [
        ("V13.7", "摩擦补偿增量", "解决 V16 失败带"),
        ("V17", "传感器闭环", "加 IMU/编码器噪声 + 状态估计"),
        ("V18-21", "3D 化", "冠状面侧向 + 3D 鲁棒性"),
        ("V22", "硬件样机 v1", "CAD + BOM + 加工"),
        ("V23-25", "Sim-to-Real", "系统辨识 + 真实地面行走"),
    ]
    sy = Inches(2.50)
    sh = Inches(0.85)
    for i, (ver, name, goal) in enumerate(steps):
        y = sy + sh * i
        rect(s, R, y, Inches(1.30), sh - Inches(0.10), fill=DEEP)
        text(
            s,
            R,
            y,
            Inches(1.30),
            sh - Inches(0.10),
            ver,
            size=12.5,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        rect(
            s,
            R + Inches(1.30),
            y,
            RW - Inches(1.30),
            sh - Inches(0.10),
            fill=PANEL_BG,
            line=LINE,
        )
        text(
            s,
            R + Inches(1.50),
            y + Inches(0.08),
            RW - Inches(1.6),
            Inches(0.32),
            name,
            size=11.5,
            bold=True,
            color=INK,
        )
        text(
            s,
            R + Inches(1.50),
            y + Inches(0.42),
            RW - Inches(1.6),
            Inches(0.30),
            goal,
            size=10,
            color=INK_MUTE,
        )


# ============================================================
# 13 中期总结
# ============================================================
def slide_summary():
    s = page(13, "中期总结", "Summary")
    section_title(
        s,
        "产品定义已经收敛,仿真证据正在补上",
        "下半学期主要精力在 V13.7 / V15 与草图收尾",
    )

    cols = [
        (
            "已完成",
            OK,
            [
                "调研 + 用户画像 + 设计目标定稿",
                "功能五层架构 + 结构布置方案",
                "V01 至 V14c 仿真链 ── 共 14 版",
                "V13.6 决策层算法 ── 切片 C 11.1%",
                "V14c 质量约束 ── 摆臂红线锁定",
            ],
        ),
        (
            "进行中",
            WARN,
            [
                "V15 髋部 SEA 弹性扫描",
                "V16 电机选型纠偏 (V13.7)",
                "整体效果图与髋部剖视图手绘",
                "Pad UI 低保真稿",
            ],
        ),
        (
            "下一阶段",
            DEEP,
            [
                "V17 传感器闭环 + 状态估计",
                "V18-21 3D 化(冠状面稳定)",
                "V22 硬件样机 CAD + BOM",
                "用户测试方案设计",
                "终期答辩材料",
            ],
        ),
    ]
    base_y = Inches(2.05)
    cw = Inches(4.00)
    gap = Inches(0.075)
    ch = Inches(4.85)
    for i, (name, color, items) in enumerate(cols):
        x = MX + (cw + gap) * i
        rect(s, x, base_y, cw, ch, fill=PANEL_BG, line=LINE)
        rect(s, x, base_y, cw, Inches(0.50), fill=color)
        text(
            s,
            x,
            base_y,
            cw,
            Inches(0.50),
            name,
            size=14,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        for j, it in enumerate(items):
            iy = base_y + Inches(0.70) + Inches(0.55) * j
            num = s.shapes.add_shape(
                MSO_SHAPE.OVAL,
                x + Inches(0.20),
                iy + Inches(0.06),
                Inches(0.22),
                Inches(0.22),
            )
            set_fill(num, color)
            no_line(num)
            text(
                s,
                x + Inches(0.20),
                iy + Inches(0.06),
                Inches(0.22),
                Inches(0.22),
                str(j + 1),
                size=9,
                bold=True,
                color=WHITE,
                align=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE,
            )
            text(
                s,
                x + Inches(0.55),
                iy,
                cw - Inches(0.7),
                Inches(0.5),
                it,
                size=10.5,
                color=INK,
                ls=1.4,
            )


# ============================================================
# 14 致谢
# ============================================================
def slide_thanks():
    s = prs.slides.add_slide(BLANK)
    page_bg(s)
    rect(s, 0, 0, W, H, fill=DEEP)
    rect(s, Inches(1.0), Inches(2.6), Inches(0.55), Emu(19050), fill=ACCENT)
    text(
        s,
        Inches(1.0),
        Inches(2.85),
        Inches(11.0),
        Inches(1.2),
        "请各位老师批评指正",
        size=44,
        bold=True,
        color=WHITE,
    )
    text(
        s,
        Inches(1.0),
        Inches(4.05),
        Inches(11.0),
        Inches(0.5),
        "期待问题与建议",
        size=18,
        color=ACCENT_S,
    )
    text(
        s,
        Inches(1.0),
        Inches(6.55),
        Inches(11.0),
        Inches(0.4),
        "下肢步态训练辅助设备  ·  中期汇报  ·  2026.06",
        size=11,
        color=RGBColor(0xA0, 0xAE, 0xB8),
    )


# ============================================================
# 生成
# ============================================================
slide_cover()
slide_toc()
slide_research_pain()
slide_research_compare()
slide_research_theory()
slide_personas()
slide_goals()
slide_functions()
slide_structure()
slide_story()
slide_sketch()
slide_sim_overview()
slide_sim_done()
slide_sim_next()
slide_summary()
slide_thanks()

OUT = ROOT / "midterm_report.pptx"
try:
    prs.save(OUT)
    print(f"OK -> {OUT}")
except PermissionError:
    from datetime import datetime

    alt = ROOT / f"midterm_report_{datetime.now().strftime('%H%M%S')}.pptx"
    prs.save(alt)
    print("主文件被占用(可能正在 PowerPoint 中打开),已写到备用文件:")
    print(f"OK -> {alt}")
print(f"slides = {len(prs.slides)}")
