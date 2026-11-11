#!/usr/bin/env python3
# slides_tail.py  — appends slides+script to presentation.html
import pathlib

HTML = pathlib.Path(r"D:\Dunna\Documents\hw-1\presentation.html")

S = []
a = S.append

# S1 COVER
a("""<section>
<div class="s">
<svg style="position:absolute;right:0;top:0;width:46%;height:100%;pointer-events:none" viewBox="0 0 520 700" fill="none">
<circle cx="460" cy="160" r="260" stroke="#2563eb" stroke-width=".7" opacity=".08"/>
<circle cx="460" cy="160" r="170" stroke="#2563eb" stroke-width=".7" opacity=".11"/>
<circle cx="460" cy="160" r="80" fill="rgba(37,99,235,.025)" stroke="#2563eb" stroke-width="1" opacity=".7"/>
<path d="M0 420 C60 385 120 455 180 415 C240 375 300 450 360 408 C420 366 480 440 520 405" stroke="#2563eb" stroke-width="1.2" fill="none" opacity=".13" stroke-dasharray="5 5"/>
<path d="M0 470 C60 440 120 505 180 465 C240 430 300 500 360 460 C420 420 480 490 520 458" stroke="#0d9488" stroke-width="1" fill="none" opacity=".1" stroke-dasharray="5 5"/>
</svg>
<div style="position:relative;z-index:1;max-width:700px">
<div class="accent-line"></div>
<div class="h1" style="font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);margin-bottom:14px">偏瘫步态康复系统 · 2026</div>
<h1 class="h-xl h2" style="margin-bottom:18px">步态重塑<br><span style="color:var(--blue)">偏瘫康复感知平台</span></h1>
<p class="lead h3" style="margin-bottom:40px">基于被动动力学理论驱动的步态检测与康复评估系统<br>V1 硬件 · 7 节点 IMU · 200 Hz 全身动捕 · 感知优先</p>
<div class="h4" style="display:inline-flex;border:1px solid var(--bd);border-radius:var(--r);overflow:hidden;box-shadow:var(--sh)">
<div style="padding:12px 22px;border-right:1px solid var(--bd)"><div class="caption" style="margin-bottom:3px">汇报日期</div><div style="font-size:14px;font-weight:600">2026 / 06 / 16</div></div>
<div style="padding:12px 22px;border-right:1px solid var(--bd)"><div class="caption" style="margin-bottom:3px">当前阶段</div><div style="font-size:14px;font-weight:600;color:var(--blue)">V25 硬件 Bring-Up</div></div>
<div style="padding:12px 22px"><div class="caption" style="margin-bottom:3px">仿真迭代</div><div style="font-size:14px;font-weight:600">V01 — V24 完成</div></div>
</div>
</div>
</div>
</section>""")
