#!/usr/bin/env python3
# gen_pres.py  —  writes presentation.html
import pathlib

OUT = pathlib.Path(r"D:\Dunna\Documents\hw-1\presentation.html")
parts = []
w = parts.append

# ── HEAD + CSS ────────────────────────────────────────────────────────────────
w("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>步态重塑 — 偏瘫康复感知平台</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reset.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#fff;--bg2:#f8fafc;--bg3:#f1f5f9;
  --t0:#0f172a;--t1:#334155;--t2:#64748b;--t3:#94a3b8;
  --bd:#e2e8f0;--bd2:#cbd5e1;
  --blue:#2563eb;--blue-d:#1d4ed8;--blue-l:#eff6ff;
  --teal:#0d9488;--teal-l:#f0fdfa;
  --green:#059669;--green-l:#ecfdf5;
  --amber:#d97706;--amber-l:#fffbeb;
  --red:#dc2626;--red-l:#fef2f2;
  --sh:0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.05);
  --r:12px;--sans:"Inter",system-ui,sans-serif;--mono:"DM Mono",monospace;
}
*{box-sizing:border-box}
.reveal-viewport,.reveal{background:#fff}
.reveal{font-family:var(--sans);color:var(--t0);font-size:16px}
.reveal h1,.reveal h2,.reveal h3{font-family:var(--sans);text-transform:none;
  letter-spacing:-.03em;line-height:1.1;color:var(--t0);font-weight:700;margin:0}
.reveal section{padding:0!important}
.reveal .progress{height:3px;background:rgba(37,99,235,.12)}
.reveal .progress span{background:var(--blue)}
.reveal .controls button{color:var(--t3)}
.reveal .slide-number{font-family:var(--mono);font-size:11px;color:var(--t3)}

/* slide */
.s{width:100%;height:100vh;display:flex;flex-direction:column;justify-content:center;
  padding:48px 80px;background:#fff;position:relative;overflow:hidden}
.s::before{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 60% 60% at 100% 0%,rgba(37,99,235,.04) 0%,transparent 60%),
             radial-gradient(ellipse 40% 40% at 0% 100%,rgba(13,148,136,.03) 0%,transparent 50%)}

/* type */
.h-xl{font-size:clamp(34px,5vw,62px);font-weight:800;letter-spacing:-.035em;line-height:1.05}
.h-lg{font-size:clamp(24px,3.2vw,40px);font-weight:700;letter-spacing:-.03em}
.lead{font-size:clamp(14px,1.5vw,17px);color:var(--t1);line-height:1.7;margin-top:12px;max-width:680px}
.small{font-size:13px;color:var(--t2);line-height:1.6}
.caption{font-size:11px;color:var(--t3);letter-spacing:.04em}
.mono{font-family:var(--mono);font-size:12px;color:var(--t2)}

/* labels */
.sec-label{display:inline-flex;align-items:center;gap:8px;font-size:11px;font-weight:600;
  letter-spacing:.12em;text-transform:uppercase;color:var(--blue);margin-bottom:16px}
.sec-label::before{content:"";width:16px;height:1.5px;background:var(--blue);flex-shrink:0}
.accent-line{width:0;height:3px;background:var(--blue);border-radius:2px;margin-bottom:22px}

/* layout */
.cols{display:grid;gap:24px;width:100%}
.c2{grid-template-columns:1fr 1fr}
.c3{grid-template-columns:1fr 1fr 1fr}
.c12{grid-template-columns:1.15fr 1fr}
.c21{grid-template-columns:1fr 1.15fr}
.stack{display:flex;flex-direction:column;gap:14px}
.row{display:flex;align-items:center;gap:14px}

/* card */
.card{background:#fff;border:1px solid var(--bd);border-radius:var(--r);
  padding:20px 24px;box-shadow:var(--sh);position:relative}
.card.tint{background:var(--bg2);box-shadow:none;border-color:var(--bd)}
.card.blue{background:var(--blue-l);border-color:rgba(37,99,235,.18);box-shadow:none}
.card.teal{background:var(--teal-l);border-color:rgba(13,148,136,.18);box-shadow:none}
.card.amber{background:var(--amber-l);border-color:rgba(217,119,6,.18);box-shadow:none}
.card.lbdr{border-left:2.5px solid var(--blue)}
.card.ltdr{border-left:2.5px solid var(--teal)}
.card-lbl{font-size:11px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--t2);margin-bottom:7px}
.card-title{font-size:14px;font-weight:600;color:var(--t0);margin-bottom:5px}
.card-body{font-size:13px;color:var(--t1);line-height:1.65}
.card-body strong{color:var(--t0);font-weight:600}

/* stat */
.snum{font-size:clamp(30px,4vw,50px);font-weight:800;letter-spacing:-.03em;line-height:1;color:var(--blue)}
.sunit{font-size:15px;font-weight:500;color:var(--t2);margin-left:2px}
.slbl{font-size:12px;color:var(--t2);margin-top:5px}
.sdelta{font-size:12px;font-weight:600;color:var(--green);margin-top:2px}

/* list */
.ul{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:9px}
.ul li{display:flex;align-items:flex-start;gap:9px;font-size:13px;color:var(--t1);line-height:1.55}
.ul li::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--blue);
  flex-shrink:0;margin-top:6px}
.ul li strong{color:var(--t0);font-weight:600}

/* badge */
.badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;
  padding:2px 9px;border-radius:20px}
.badge::before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor;flex-shrink:0}
.badge.g{background:var(--green-l);color:var(--green)}
.badge.a{background:var(--amber-l);color:var(--amber)}
.badge.r{background:var(--red-l);  color:var(--red)}
.badge.b{background:var(--blue-l); color:var(--blue-d)}
.badge.n{background:var(--bg3);    color:var(--t2)}

/* table */
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--t2);
  border-bottom:1.5px solid var(--bd);padding:8px 14px;text-align:left;background:var(--bg2)}
.tbl td{padding:9px 14px;border-bottom:1px solid var(--bg3);color:var(--t1)}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:var(--bg2)}
.tbl .hl{font-weight:600;color:var(--t0)}
.tbl .bl{color:var(--blue);font-weight:600}

/* progress */
.prog-wrap{display:flex;flex-direction:column;gap:4px}
.prog-lbl{display:flex;justify-content:space-between;font-size:12px;color:var(--t2)}
.prog-lbl strong{color:var(--t0);font-weight:600}
.prog-track{height:5px;border-radius:3px;background:var(--bg3);overflow:hidden}
.prog-bar{height:100%;border-radius:3px;width:0;transition:width 1s cubic-bezier(.22,1,.36,1)}

/* timeline */
.tl{display:flex;flex-direction:column}
.tl-row{display:flex;gap:14px;position:relative}
.tl-row:not(:last-child)::before{content:"";position:absolute;left:7px;top:18px;bottom:0;
  width:1.5px;background:var(--bd)}
.tl-dot{width:16px;height:16px;border-radius:50%;flex-shrink:0;margin-top:2px;border:2px solid}
.tl-dot.done{border-color:var(--teal);background:var(--teal)}
.tl-dot.now {border-color:var(--blue);background:var(--blue-l)}
.tl-dot.next{border-color:var(--bd2);background:#fff}
.tl-body{padding-bottom:18px}
.tl-head{font-size:13px;font-weight:600;color:var(--t0);margin-bottom:2px}
.tl-desc{font-size:12px;color:var(--t2);line-height:1.55}

/* step circle */
.step{width:36px;height:36px;border-radius:50%;border:1.5px solid var(--bd);
  display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;
  color:var(--blue);flex-shrink:0;background:#fff;font-family:var(--mono)}

/* divider */
.div-line{width:32px;height:1.5px;background:var(--bd2);display:inline-block}

/* ── ANIMATIONS ────────────────────────────────── */
.av,.al,.ar{opacity:0;transition:opacity .55s cubic-bezier(.22,1,.36,1),transform .55s cubic-bezier(.22,1,.36,1)}
.av{transform:translateY(18px)}
.al{transform:translateX(-18px)}
.ar{transform:translateX(18px)}
.reveal .slides section.present .av,
.reveal .slides section.present .al,
.reveal .slides section.present .ar{opacity:1;transform:none}
.d0{transition-delay:.00s}.d1{transition-delay:.08s}.d2{transition-delay:.16s}
.d3{transition-delay:.24s}.d4{transition-delay:.32s}.d5{transition-delay:.40s}
.d6{transition-delay:.48s}.d7{transition-delay:.56s}.d8{transition-delay:.64s}
.d9{transition-delay:.72s}

@keyframes heroIn{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
.h1{animation:heroIn .7s cubic-bezier(.22,1,.36,1) .05s both}
.h2{animation:heroIn .7s cubic-bezier(.22,1,.36,1) .20s both}
.h3{animation:heroIn .7s cubic-bezier(.22,1,.36,1) .35s both}
.h4{animation:heroIn .7s cubic-bezier(.22,1,.36,1) .50s both}
.h5{animation:heroIn .7s cubic-bezier(.22,1,.36,1) .65s both}
@keyframes lineGrow{from{width:0}to{width:48px}}
.accent-line{animation:lineGrow .5s cubic-bezier(.22,1,.36,1) .05s both}
</style>
</head>
<body>
<div class="reveal"><div class="slides">
""")
