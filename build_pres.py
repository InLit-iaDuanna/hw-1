# build_pres.py — generates presentation.html
P = []
a = P.append

a('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>步态重塑 — 偏瘫步态感知系统</title>
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
  --blue:#2563eb;--blue-d:#1d4ed8;--blue-l:#eff6ff;--blue-m:rgba(37,99,235,.08);
  --teal:#0d9488;--teal-l:#f0fdfa;
  --green:#059669;--green-l:#ecfdf5;
  --amber:#d97706;--amber-l:#fffbeb;
  --red:#dc2626;--red-l:#fef2f2;
  --sh:0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.05);
  --sh2:0 2px 8px rgba(0,0,0,.08),0 12px 32px rgba(0,0,0,.07);
  --r:12px;--r2:8px;
  --sans:"Inter",system-ui,sans-serif;--mono:"DM Mono",monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
.reveal-viewport{background:var(--bg)}
.reveal{font-family:var(--sans);color:var(--t0);font-size:16px}
.reveal h1,.reveal h2,.reveal h3,.reveal h4{font-family:var(--sans);text-transform:none;
  letter-spacing:-0.03em;line-height:1.1;color:var(--t0);font-weight:700}
.reveal section{padding:0!important}
.reveal .progress{height:2px;background:rgba(37,99,235,.15)}
.reveal .progress span{background:var(--blue)}
.reveal .controls button{color:var(--t3)}
.reveal .slide-number{font-family:var(--mono);font-size:11px;color:var(--t3);
  bottom:20px;right:28px}
''')
