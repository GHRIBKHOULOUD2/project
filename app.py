#!/usr/bin/env python3
# =============================================================
# app.py — Flask Admin Dashboard (Multi-Page + Dark/Light Mode)
# Updated: dual ESP8266, VLAN policy admin panel
# FIXED: Jinja2 template syntax errors
# =============================================================

import time, os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, render_template_string
from config import (
    HOST_INFO, HOST_VLAN, HOST_QOS, QOS_QUEUES,
    VLAN_NAMES, VLAN_DEFAULT_POLICY, FLASK_PORT, CONTROLLER_IP,
)
from shared_state import (
    read_state, write_state, add_alert,
    get_vlan_policy, set_vlan_policy, set_host_policy, reset_vlan_policy,
)

app = Flask(__name__)
_cam = {"data": None, "timestamp": None, "ip": None}

# =============================================================
# HTML TEMPLATE
# =============================================================
HTML = r"""
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NetTwin -- {{ page_title }}</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --primary:#2563eb;--primary-lt:#eff6ff;--primary-md:#dbeafe;--accent:#0ea5e9;
  --green:#10b981;--green-lt:#ecfdf5;--red:#ef4444;--red-lt:#fef2f2;
  --orange:#f59e0b;--orange-lt:#fffbeb;--purple:#8b5cf6;--purple-lt:#f5f3ff;
  --sidebar-w:220px;--topbar-h:60px;--radius:12px;--radius-sm:8px;
  --sans:'Plus Jakarta Sans',sans-serif;--mono:'JetBrains Mono',monospace;
}
[data-theme="light"]{--bg:#f1f5f9;--surface:#ffffff;--surface2:#f8fafc;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--text3:#94a3b8;--text4:#cbd5e1;--shadow-sm:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);--shadow:0 4px 6px rgba(0,0,0,.05),0 2px 4px rgba(0,0,0,.04);--shadow-lg:0 10px 25px rgba(0,0,0,.08);}
[data-theme="dark"]{--bg:#0f172a;--surface:#1e293b;--surface2:#162032;--border:#334155;--text:#f1f5f9;--text2:#94a3b8;--text3:#64748b;--text4:#475569;--shadow-sm:0 1px 3px rgba(0,0,0,.3);--shadow:0 4px 6px rgba(0,0,0,.25);--shadow-lg:0 10px 25px rgba(0,0,0,.4);--primary-lt:rgba(37,99,235,.15);--primary-md:rgba(37,99,235,.25);--green-lt:rgba(16,185,129,.15);--red-lt:rgba(239,68,68,.15);--orange-lt:rgba(245,158,11,.15);--purple-lt:rgba(139,92,246,.15);}
body{font-family:var(--sans);background:var(--bg);color:var(--text);display:flex;min-height:100vh;font-size:14px;line-height:1.5;transition:background .2s,color .2s;}
.sidebar{width:var(--sidebar-w);background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:200;box-shadow:var(--shadow-sm);transition:background .2s;}
.sidebar-brand{padding:20px 20px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border);}
.brand-icon{width:34px;height:34px;background:var(--primary);border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.brand-icon svg{width:18px;height:18px;stroke:white;fill:none;}
.brand-name{font-size:1rem;font-weight:700;color:var(--text);letter-spacing:-.5px;}
.brand-sub{font-size:.6rem;color:var(--text3);font-family:var(--mono);letter-spacing:1.5px;text-transform:uppercase;}
.sidebar-nav{flex:1;padding:16px 12px;display:flex;flex-direction:column;gap:2px;overflow-y:auto;}
.nav-label{font-size:.58rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text4);padding:10px 8px 6px;}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:var(--radius-sm);font-size:.82rem;font-weight:500;color:var(--text2);cursor:pointer;transition:all .15s;text-decoration:none;border:none;background:none;width:100%;}
.nav-item:hover{background:var(--bg);color:var(--text);}
.nav-item.active{background:var(--primary-lt);color:var(--primary);font-weight:600;}
.nav-item svg{width:15px;height:15px;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:2;opacity:.75;}
.nav-item.active svg{opacity:1;}
.nav-badge{margin-left:auto;background:var(--red);color:white;font-size:.55rem;font-weight:700;padding:1px 6px;border-radius:10px;font-family:var(--mono);}
.sidebar-footer{padding:12px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:2px;}
.settings-overlay{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,.3);}
.settings-overlay.open{display:block;}
.settings-panel{position:fixed;right:0;top:0;bottom:0;width:300px;background:var(--surface);border-left:1px solid var(--border);z-index:301;padding:24px 20px;display:flex;flex-direction:column;gap:20px;transform:translateX(100%);transition:transform .25s ease;box-shadow:var(--shadow-lg);}
.settings-panel.open{transform:translateX(0);}
.settings-panel-header{display:flex;align-items:center;justify-content:space-between;padding-bottom:16px;border-bottom:1px solid var(--border);}
.settings-panel-header h2{font-size:.95rem;font-weight:700;}
.close-btn{width:28px;height:28px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);display:flex;align-items:center;justify-content:center;cursor:pointer;}
.close-btn svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2.5;}
.setting-section h3{font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:var(--text3);margin-bottom:10px;}
.theme-options{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.theme-option{border:1.5px solid var(--border);border-radius:var(--radius-sm);padding:12px 10px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:7px;transition:all .15s;background:var(--surface2);}
.theme-option:hover{border-color:var(--primary);}
.theme-option.selected{border-color:var(--primary);background:var(--primary-lt);}
.theme-option svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.5;}
.theme-option span{font-size:.72rem;font-weight:600;color:var(--text2);}
.theme-option.selected span{color:var(--primary);}
.main-wrap{margin-left:var(--sidebar-w);flex:1;display:flex;flex-direction:column;min-height:100vh;}
.topbar{height:var(--topbar-h);background:var(--surface);border-bottom:1px solid var(--border);padding:0 28px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:100;box-shadow:var(--shadow-sm);}
.topbar-title{font-size:1.05rem;font-weight:700;color:var(--text);letter-spacing:-.3px;}
.search-box{flex:1;max-width:300px;margin-left:20px;position:relative;}
.search-box input{width:100%;padding:7px 12px 7px 32px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.78rem;font-family:var(--sans);background:var(--bg);color:var(--text);outline:none;transition:border-color .2s;}
.search-box input:focus{border-color:var(--primary);background:var(--surface);}
.search-box svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);width:13px;height:13px;color:var(--text3);stroke:currentColor;fill:none;stroke-width:2;}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:8px;}
.icon-btn{width:34px;height:34px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--surface);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .15s;position:relative;color:var(--text2);}
.icon-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-lt);}
.icon-btn svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2;}
.badge-dot{position:absolute;top:6px;right:6px;width:7px;height:7px;background:var(--red);border-radius:50%;border:1.5px solid var(--surface);}
.user-pill{display:flex;align-items:center;gap:8px;padding:4px 10px 4px 4px;border:1px solid var(--border);border-radius:20px;cursor:pointer;transition:all .15s;}
.user-pill:hover{border-color:var(--primary);background:var(--primary-lt);}
.user-avatar{width:28px;height:28px;background:linear-gradient(135deg,var(--primary),var(--accent));border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.6rem;font-weight:700;color:white;letter-spacing:.5px;}
.user-name{font-size:.78rem;font-weight:600;color:var(--text);}
.page-content{padding:24px 28px 32px;display:flex;flex-direction:column;gap:20px;}
.welcome-text{font-size:1.1rem;font-weight:700;color:var(--text);letter-spacing:-.3px;}
.welcome-sub{font-size:.75rem;color:var(--text3);margin-top:2px;}
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px;box-shadow:var(--shadow-sm);position:relative;overflow:hidden;transition:box-shadow .2s,transform .2s;animation:fadeUp .4s ease both;}
.stat-card:nth-child(1){animation-delay:.05s;}.stat-card:nth-child(2){animation-delay:.10s;}.stat-card:nth-child(3){animation-delay:.15s;}.stat-card:nth-child(4){animation-delay:.20s;}
.stat-card:hover{box-shadow:var(--shadow-lg);transform:translateY(-2px);}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.sc-blue::before{background:var(--primary);}.sc-green::before{background:var(--green);}.sc-orange::before{background:var(--orange);}.sc-purple::before{background:var(--purple);}
.stat-icon{width:36px;height:36px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;margin-bottom:12px;}
.stat-icon svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;}
.sc-blue .stat-icon{background:var(--primary-lt);color:var(--primary);}.sc-green .stat-icon{background:var(--green-lt);color:var(--green);}.sc-orange .stat-icon{background:var(--orange-lt);color:var(--orange);}.sc-purple .stat-icon{background:var(--purple-lt);color:var(--purple);}
.stat-label{font-size:.65rem;color:var(--text3);font-weight:500;text-transform:uppercase;letter-spacing:.9px;}
.stat-value{font-size:1.8rem;font-weight:700;color:var(--text);letter-spacing:-1.5px;line-height:1.1;margin:4px 0 8px;font-family:var(--mono);}
.stat-footer{display:flex;align-items:center;justify-content:space-between;}
.stat-delta{font-size:.68rem;font-weight:600;}.delta-up{color:var(--green);}.delta-down{color:var(--red);}
.stat-link{font-size:.65rem;color:var(--primary);font-weight:600;cursor:pointer;text-decoration:none;}
.stat-link:hover{text-decoration:underline;}
.panel-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow-sm);animation:fadeUp .4s ease .2s both;}
.panel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border);}
.panel-title{font-size:.82rem;font-weight:700;color:var(--text);}
.panel-count{font-size:.6rem;font-family:var(--mono);color:var(--text3);background:var(--bg);padding:2px 8px;border-radius:10px;border:1px solid var(--border);}
.sp{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:20px;font-size:.6rem;font-weight:600;font-family:var(--mono);border:1px solid transparent;white-space:nowrap;flex-shrink:0;}
.sp-online{background:var(--green-lt);color:#065f46;border-color:#a7f3d0;}.sp-offline{background:var(--bg);color:var(--text3);border-color:var(--border);}.sp-blocked{background:var(--red-lt);color:#991b1b;border-color:#fca5a5;}
.sp-dot{width:5px;height:5px;border-radius:50%;}.sp-online .sp-dot{background:var(--green);}.sp-offline .sp-dot{background:var(--text4);}.sp-blocked .sp-dot{background:var(--red);}
.dev-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);}
.dev-row:last-child{border-bottom:none;}
.dev-initials{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.58rem;font-weight:700;letter-spacing:.3px;flex-shrink:0;}
.di-blue{background:var(--primary-lt);color:var(--primary);}.di-green{background:var(--green-lt);color:var(--green);}.di-orange{background:var(--orange-lt);color:var(--orange);}.di-purple{background:var(--purple-lt);color:var(--purple);}
.dev-info{flex:1;min-width:0;}
.dev-name{font-size:.78rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.dev-ip{font-size:.62rem;color:var(--text3);font-family:var(--mono);}
.action-btn{display:inline-flex;align-items:center;padding:3px 9px;border-radius:6px;font-size:.6rem;font-weight:600;cursor:pointer;border:1px solid;font-family:var(--sans);transition:all .15s;white-space:nowrap;flex-shrink:0;}
.btn-block{color:#991b1b;border-color:#fca5a5;background:var(--red-lt);}.btn-block:hover{background:#fee2e2;}
.btn-unblock{color:#065f46;border-color:#6ee7b7;background:var(--green-lt);}.btn-unblock:hover{background:#d1fae5;}
.btn-primary{color:white;border-color:var(--primary);background:var(--primary);}.btn-primary:hover{background:#1d4ed8;}
.btn-danger{color:white;border-color:var(--red);background:var(--red);}.btn-danger:hover{background:#dc2626;}
.btn-sm{padding:4px 10px;font-size:.65rem;}
.vt{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.58rem;font-weight:700;font-family:var(--mono);}
.vt-10{background:var(--primary-lt);color:var(--primary);}.vt-20{background:var(--green-lt);color:var(--green);}.vt-30{background:var(--orange-lt);color:var(--orange);}
.policy-matrix{width:100%;border-collapse:collapse;}
.policy-matrix th,.policy-matrix td{padding:8px 12px;border:1px solid var(--border);font-size:.72rem;text-align:center;}
.policy-matrix th{background:var(--surface2);font-weight:600;color:var(--text2);font-size:.62rem;text-transform:uppercase;letter-spacing:.8px;}
.policy-matrix td.row-header{text-align:left;font-weight:600;color:var(--text);background:var(--surface2);}
.policy-cell-allow{background:var(--green-lt);color:#065f46;font-weight:700;font-family:var(--mono);font-size:.6rem;}
.policy-cell-deny{background:var(--red-lt);color:#991b1b;font-weight:700;font-family:var(--mono);font-size:.6rem;}
.policy-cell-same{background:var(--primary-lt);color:var(--primary);font-weight:700;font-family:var(--mono);font-size:.6rem;}
.policy-toggle{display:inline-flex;align-items:center;gap:4px;cursor:pointer;padding:3px 8px;border-radius:6px;border:1px solid;font-size:.58rem;font-weight:700;font-family:var(--mono);transition:all .15s;}
.policy-toggle.allow{background:var(--green-lt);color:#065f46;border-color:#6ee7b7;}.policy-toggle.allow:hover{background:#d1fae5;}
.policy-toggle.deny{background:var(--red-lt);color:#991b1b;border-color:#fca5a5;}.policy-toggle.deny:hover{background:#fee2e2;}
.sensor-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border);}
.sensor-row:last-child{border-bottom:none;}
.sensor-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;}
.sensor-label{font-size:.72rem;color:var(--text2);}
.sensor-value{margin-left:auto;font-family:var(--mono);font-size:.85rem;font-weight:700;color:var(--text);}
.sensor-unit{font-size:.6rem;color:var(--text3);margin-left:2px;}
.tbl{width:100%;border-collapse:collapse;}
.tbl th{font-size:.6rem;font-weight:600;text-transform:uppercase;letter-spacing:.9px;color:var(--text3);padding:0 12px 10px;text-align:left;border-bottom:1.5px solid var(--border);}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}
.tbl tr:last-child td{border-bottom:none;}
.tbl tr:hover td{background:var(--bg);}
.tbl-ip{font-family:var(--mono);font-size:.68rem;color:var(--primary);}
.qos-section{display:flex;flex-direction:column;gap:9px;}
.qos-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border);}
.qos-row:last-child{border-bottom:none;}
.qos-name{width:130px;font-size:.78rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text);}
.qos-badge{width:72px;font-family:var(--mono);font-size:.56rem;font-weight:700;padding:3px 6px;border-radius:4px;text-align:center;border:1px solid transparent;flex-shrink:0;}
.qos-bar-bg{flex:1;background:var(--border);border-radius:3px;height:8px;overflow:hidden;}
.qos-bar{height:8px;border-radius:3px;transition:width .6s cubic-bezier(.4,0,.2,1);}
.q0 .qos-badge{background:var(--red-lt);color:var(--red);border-color:#fca5a5;}.q1 .qos-badge{background:var(--orange-lt);color:var(--orange);border-color:#fcd34d;}.q2 .qos-badge{background:#fefce8;color:#b45309;border-color:#fde68a;}.q3 .qos-badge{background:var(--primary-lt);color:var(--primary);border-color:var(--primary-md);}.q4 .qos-badge{background:var(--bg);color:var(--text3);border-color:var(--border);}
.q0 .qos-bar{background:var(--red);}.q1 .qos-bar{background:var(--orange);}.q2 .qos-bar{background:#eab308;}.q3 .qos-bar{background:var(--primary);}.q4 .qos-bar{background:var(--text4);}
.qos-ip{font-family:var(--mono);font-size:.62rem;color:var(--text3);width:120px;flex-shrink:0;}
.alert-rows{display:flex;flex-direction:column;gap:6px;}
.alert-row{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-radius:var(--radius-sm);border-left:3px solid;transition:transform .1s;}
.alert-row:hover{transform:translateX(2px);}
.alert-row.CRITICAL{border-color:var(--red);background:var(--red-lt);}.alert-row.HIGH{border-color:var(--orange);background:var(--orange-lt);}.alert-row.MEDIUM{border-color:var(--orange);background:var(--orange-lt);}.alert-row.LOW{border-color:var(--green);background:var(--green-lt);}
.a-sev{font-family:var(--mono);font-size:.58rem;font-weight:700;letter-spacing:.5px;min-width:60px;padding-top:2px;}
.alert-row.CRITICAL .a-sev{color:var(--red);}.alert-row.HIGH .a-sev{color:var(--orange);}.alert-row.MEDIUM .a-sev{color:#d97706;}.alert-row.LOW .a-sev{color:var(--green);}
.a-body{flex:1;min-width:0;}
.a-type{font-size:.75rem;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.a-msg{font-size:.65rem;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px;}
.a-ts{font-family:var(--mono);font-size:.58rem;color:var(--text3);white-space:nowrap;flex-shrink:0;}
#cam-img{width:100%;border-radius:var(--radius-sm);border:1px solid var(--border);}
.no-cam{height:240px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:4px;background:var(--bg);border-radius:var(--radius-sm);border:1.5px dashed var(--border);color:var(--text3);}
.cam-meta{font-family:var(--mono);font-size:.58rem;color:var(--text3);margin-top:5px;}
.dash-mid{display:grid;grid-template-columns:1fr 320px;gap:16px;}
.summary-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;box-shadow:var(--shadow-sm);}
.summary-item{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);}
.summary-item:last-child{border-bottom:none;}
.summary-lbl{font-size:.78rem;color:var(--text2);font-weight:500;}
.summary-val{font-size:.82rem;font-weight:700;color:var(--text);font-family:var(--mono);}
.donut-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;box-shadow:var(--shadow-sm);display:flex;flex-direction:column;}
.donut-wrap{display:flex;align-items:center;justify-content:center;margin:12px 0;position:relative;}
.donut-svg{width:140px;height:140px;}
.donut-center{position:absolute;text-align:center;}
.donut-center-num{font-size:1.6rem;font-weight:700;color:var(--text);line-height:1;letter-spacing:-1px;font-family:var(--mono);}
.donut-center-label{font-size:.6rem;color:var(--text3);text-transform:uppercase;letter-spacing:.8px;margin-top:2px;}
.donut-legend{display:flex;flex-direction:column;gap:8px;}
.donut-leg-item{display:flex;align-items:center;gap:8px;font-size:.72rem;}
.donut-leg-dot{width:10px;height:10px;border-radius:3px;flex-shrink:0;}
.donut-leg-label{flex:1;color:var(--text2);}
.donut-leg-pct{font-weight:700;color:var(--text);font-family:var(--mono);font-size:.7rem;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.three-col{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
footer{padding:14px 28px 20px;display:flex;gap:8px;align-items:center;border-top:1px solid var(--border);background:var(--surface);}
.ext-btn{padding:5px 12px;border-radius:6px;font-size:.7rem;font-weight:500;text-decoration:none;color:var(--text2);border:1px solid var(--border);background:var(--surface);transition:all .15s;}
.ext-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-lt);}
.footer-sp{margin-left:auto;font-family:var(--mono);font-size:.6rem;color:var(--text3);}
.refresh-bar{position:fixed;bottom:0;left:0;right:0;height:2px;background:var(--border);z-index:999;}
.refresh-inner{height:100%;background:linear-gradient(90deg,var(--primary),var(--accent));animation:refill 12s linear forwards;}
@keyframes refill{from{width:100%}to{width:0%}}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.no-data{text-align:center;padding:32px;color:var(--text3);font-size:.75rem;}
.info-box{padding:10px 14px;background:var(--primary-lt);border-radius:var(--radius-sm);border:1px solid var(--primary-md);font-size:.7rem;color:var(--primary);font-weight:500;line-height:1.5;}
select{background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:var(--radius-sm);padding:4px 8px;font-size:.72rem;font-family:var(--sans);outline:none;cursor:pointer;}
select:focus{border-color:var(--primary);}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-icon"><svg viewBox="0 0 24 24" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></div>
    <div><div class="brand-name">NetTwin</div><div class="brand-sub">SDN · AI · IoT</div></div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-label">Main</div>
    <a class="nav-item {% if current_page=='dashboard' %}active{% endif %}" href="/"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Dashboard</a>
    <a class="nav-item {% if current_page=='devices' %}active{% endif %}" href="/devices"><svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>Devices<span class="nav-badge">{{ total_devices }}</span></a>
    <a class="nav-item {% if current_page=='sensors' %}active{% endif %}" href="/sensors"><svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 6v4l3 3"/></svg>Sensors</a>
    <a class="nav-item {% if current_page=='policy' %}active{% endif %}" href="/policy"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>VLAN Policy</a>
    <a class="nav-item {% if current_page=='qos' %}active{% endif %}" href="/qos"><svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>QoS Monitor</a>
    <a class="nav-item {% if current_page=='alerts' %}active{% endif %}" href="/alerts"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>AI Alerts{% if alert_count > 0 %}<span class="nav-badge">{{ alert_count }}</span>{% endif %}</a>
    <a class="nav-item {% if current_page=='camera' %}active{% endif %}" href="/camera"><svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M7 21v-2a5 5 0 0110 0v2"/></svg>Camera</a>
    <div class="nav-label" style="margin-top:8px">External</div>
    <a class="nav-item" href="http://localhost:3000" target="_blank"><svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Grafana</a>
    <a class="nav-item" href="/api/twin" target="_blank"><svg viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>State JSON</a>
  </nav>
  <div class="sidebar-footer">
    <button class="nav-item" onclick="openSettings()"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>Settings</button>
  </div>
</aside>

<div class="settings-overlay" id="settings-overlay" onclick="closeSettings()"></div>
<div class="settings-panel" id="settings-panel">
  <div class="settings-panel-header"><h2>Settings</h2><div class="close-btn" onclick="closeSettings()"><svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></div></div>
  <div class="setting-section">
    <h3>Appearance</h3>
    <div class="theme-options">
      <div class="theme-option" id="opt-light" onclick="setTheme('light')"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><span>Light</span></div>
      <div class="theme-option" id="opt-dark" onclick="setTheme('dark')"><svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg><span>Dark</span></div>
    </div>
  </div>
  <div class="setting-section" style="margin-top:8px">
    <h3>System</h3>
    <div style="font-size:.72rem;color:var(--text2);line-height:1.7">
      <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>Controller IP</span><span style="font-family:var(--mono);color:var(--primary)">{{ controller_ip }}</span></div>
      <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>Total Hosts</span><span style="font-family:var(--mono);font-weight:700">{{ total_devices }}</span></div>
      <div style="display:flex;justify-content:space-between;padding:6px 0"><span>Auto-refresh</span><span style="font-family:var(--mono);color:var(--green)">12s</span></div>
    </div>
  </div>
</div>

<div class="main-wrap">
  <header class="topbar">
    <div class="topbar-title">{{ page_title }}</div>
    <div class="search-box"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><input type="text" placeholder="Search devices, alerts..." id="search-input"></div>
    <div class="topbar-right">
      <div class="icon-btn" title="Refresh" onclick="location.reload()"><svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg></div>
      <div class="icon-btn" title="Alerts" onclick="window.location='/alerts'"><svg viewBox="0 0 24 24"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>{% if alert_count > 0 %}<div class="badge-dot"></div>{% endif %}</div>
      <div class="icon-btn" title="Settings" onclick="openSettings()"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg></div>
      <div class="user-pill"><div class="user-avatar">NT</div><div class="user-name">Admin</div></div>
    </div>
  </header>

  <div class="page-content">

  {% if current_page == 'dashboard' %}
    <div><div class="welcome-text">Welcome back, Admin!</div><div class="welcome-sub">{{ last_updated or 'Network Digital Twin -- Live Monitor' }}</div></div>
    <div class="stat-row">
      <div class="stat-card sc-blue"><div class="stat-icon"><svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg></div><div class="stat-label">Total Devices</div><div class="stat-value">{{ total_devices }}</div><div class="stat-footer"><span class="stat-delta delta-up">Active network</span><a class="stat-link" href="/devices">View all</a></div></div>
      <div class="stat-card sc-green"><div class="stat-icon"><svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div><div class="stat-label">Online</div><div class="stat-value">{{ online_count }}</div><div class="stat-footer"><span class="stat-delta delta-up">Reachable</span><a class="stat-link" href="/devices">View report</a></div></div>
      <div class="stat-card sc-orange"><div class="stat-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div class="stat-label">Blocked</div><div class="stat-value">{{ blocked_count }}</div><div class="stat-footer"><span class="stat-delta {% if blocked_count > 0 %}delta-down{% else %}delta-up{% endif %}">{% if blocked_count > 0 %}Action needed{% else %}All clear{% endif %}</span><a class="stat-link" href="/devices">View report</a></div></div>
      <div class="stat-card sc-purple"><div class="stat-icon"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div><div class="stat-label">AI Alerts</div><div class="stat-value">{{ alert_count }}</div><div class="stat-footer"><span class="stat-delta {% if alert_count > 0 %}delta-down{% else %}delta-up{% endif %}">{% if alert_count > 0 %}Review needed{% else %}All clear{% endif %}</span><a class="stat-link" href="/alerts">View report</a></div></div>
    </div>
    <div class="dash-mid">
      <div class="summary-card">
        <div class="panel-header"><div class="panel-title">Network Overview</div></div>
        {% set v10 = vlan_hosts.values()|selectattr('vlan','equalto',10)|list|length %}
        {% set v20 = vlan_hosts.values()|selectattr('vlan','equalto',20)|list|length %}
        {% set v30 = vlan_hosts.values()|selectattr('vlan','equalto',30)|list|length %}
        <div class="summary-item"><span class="summary-lbl">VLAN 10 -- IT</span><span class="summary-val">{{ v10 }} hosts</span></div>
        <div class="summary-item"><span class="summary-lbl">VLAN 20 -- WiFi</span><span class="summary-val">{{ v20 }} hosts</span></div>
        <div class="summary-item"><span class="summary-lbl">VLAN 30 -- IoT</span><span class="summary-val">{{ v30 }} hosts</span></div>
        <div class="summary-item"><span class="summary-lbl">ESP8266 devices</span><span class="summary-val">2 nodes</span></div>
        <div class="summary-item"><span class="summary-lbl">Blocked IPs</span><span class="summary-val" style="color:{% if blocked_count > 0 %}var(--red){% else %}var(--green){% endif %}">{{ blocked_count }}</span></div>
        <div class="summary-item"><span class="summary-lbl">Active Alerts</span><span class="summary-val" style="color:{% if alert_count > 0 %}var(--orange){% else %}var(--green){% endif %}">{{ alert_count }}</span></div>
        <div class="info-box" style="margin-top:16px">Use the sidebar Sensors for live ESP8266 readings, VLAN Policy for access control.</div>
      </div>
      <div class="donut-card">
        <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:0">VLAN Distribution</div>
        {% set v10 = vlan_hosts.values()|selectattr('vlan','equalto',10)|list|length %}
        {% set v20 = vlan_hosts.values()|selectattr('vlan','equalto',20)|list|length %}
        {% set v30 = vlan_hosts.values()|selectattr('vlan','equalto',30)|list|length %}
        {% set tot = v10 + v20 + v30 %}
        {% set p10 = ((v10/tot)*100)|int if tot > 0 else 0 %}
        {% set p20 = ((v20/tot)*100)|int if tot > 0 else 0 %}
        {% set p30 = 100 - p10 - p20 %}
        <div class="donut-wrap">
          <svg class="donut-svg" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="46" fill="none" stroke="#e2e8f0" stroke-width="14"/>
            <circle cx="60" cy="60" r="46" fill="none" stroke="#2563eb" stroke-width="14" stroke-dasharray="{{ (p10*2.89)|int }} 289" stroke-dashoffset="72" stroke-linecap="round" transform="rotate(-90 60 60)"/>
            <circle cx="60" cy="60" r="46" fill="none" stroke="#10b981" stroke-width="14" stroke-dasharray="{{ (p20*2.89)|int }} 289" stroke-dashoffset="{{ 72-(p10*2.89)|int }}" stroke-linecap="round" transform="rotate(-90 60 60)"/>
            <circle cx="60" cy="60" r="46" fill="none" stroke="#f59e0b" stroke-width="14" stroke-dasharray="{{ (p30*2.89)|int }} 289" stroke-dashoffset="{{ 72-(p10*2.89)|int-(p20*2.89)|int }}" stroke-linecap="round" transform="rotate(-90 60 60)"/>
          </svg>
          <div class="donut-center"><div class="donut-center-num">{{ tot }}</div><div class="donut-center-label">Hosts</div></div>
        </div>
        <div class="donut-legend">
          <div class="donut-leg-item"><div class="donut-leg-dot" style="background:#2563eb"></div><div class="donut-leg-label">VLAN 10 -- IT</div><div class="donut-leg-pct">{{ p10 }}%</div></div>
          <div class="donut-leg-item"><div class="donut-leg-dot" style="background:#10b981"></div><div class="donut-leg-label">VLAN 20 -- WiFi</div><div class="donut-leg-pct">{{ p20 }}%</div></div>
          <div class="donut-leg-item"><div class="donut-leg-dot" style="background:#f59e0b"></div><div class="donut-leg-label">VLAN 30 -- IoT</div><div class="donut-leg-pct">{{ p30 }}%</div></div>
        </div>
      </div>
    </div>

  {% elif current_page == 'devices' %}
    <div><div class="welcome-text">Devices</div><div class="welcome-sub">All network hosts, VLANs, and access control</div></div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Infrastructure</div><div class="panel-count">3 nodes</div></div>
      {% for key in ['OVS-SWITCH','AP-RPI'] %}
      {% set info = all_hosts[key] %}
      <div class="dev-row"><div class="dev-initials di-purple">{{ info.name[:2]|upper }}</div><div class="dev-info"><div class="dev-name">{{ info.name }}</div><div class="dev-ip">Infrastructure device</div></div><span class="sp sp-online"><span class="sp-dot"></span>Online</span><span style="font-size:.58rem;font-weight:700;color:#6d28d9;background:var(--purple-lt);padding:2px 7px;border-radius:4px;font-family:var(--mono)">INFRA</span></div>
      {% endfor %}
      {% set ctrl = all_hosts[controller_ip] %}
      <div class="dev-row"><div class="dev-initials di-orange">{{ ctrl.name[:2]|upper }}</div><div class="dev-info"><div class="dev-name">{{ ctrl.name }}</div><div class="dev-ip">{{ controller_ip }}</div></div><span class="sp sp-online"><span class="sp-dot"></span>Online</span><span style="font-size:.58rem;font-weight:700;color:#0f766e;background:var(--green-lt);padding:2px 7px;border-radius:4px;font-family:var(--mono)">CTRL</span></div>
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">VLAN Membership</div><div class="panel-count">{{ vlan_hosts|length }} hosts</div></div>
      <table class="tbl" id="vlan-table">
        <thead><tr><th>Device</th><th>IP Address</th><th>VLAN</th><th>Status</th><th>QoS</th><th>Sensors</th><th>Action</th></tr></thead>
        <tbody>
          {% set di = ['di-blue','di-green','di-orange','di-purple'] %}
          {% for ip, h in vlan_hosts.items() %}
          <tr>
            <td><div style="display:flex;align-items:center;gap:8px"><div class="dev-initials {{ di[loop.index0 % 4] }}">{{ h.name[:2]|upper }}</div><div><div style="font-size:.78rem;font-weight:600;color:var(--text)">{{ h.name }}</div><div style="font-size:.62rem;color:var(--text3)">{{ h.role[:28] }}</div></div></div></td>
            <td class="tbl-ip">{{ ip }}</td>
            <td><span class="vt vt-{{ h.vlan }}">VLAN {{ h.vlan }} -- {{ vlan_names.get(h.vlan,'') }}</span></td>
            <td>{% if ip in blocked %}<span class="sp sp-blocked"><span class="sp-dot"></span>Blocked</span>{% elif h.status == 'online' %}<span class="sp sp-online"><span class="sp-dot"></span>Online</span>{% else %}<span class="sp sp-offline"><span class="sp-dot"></span>Offline</span>{% endif %}</td>
            <td><span class="qos-badge q{{ h.queue_id }}" style="display:inline-block">{{ h.qos_level }}</span></td>
            <td style="font-size:.62rem;color:var(--text3)">{{ h.sensors|join(', ') if h.sensors else '—' }}</td>
            <td>{% if ip in blocked %}<button class="action-btn btn-unblock" onclick="act('{{ ip }}','unblock')">Unblock</button>{% else %}<button class="action-btn btn-block" onclick="act('{{ ip }}','block')">Block</button>{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

  {% elif current_page == 'sensors' %}
    <div><div class="welcome-text">Sensor Readings</div>
    <div class="welcome-sub">Live data via MQTT SmartGuard -- Broker: 192.168.1.20</div></div>
    <div class="three-col">
      <div class="stat-card sc-orange">
        <div class="stat-label">LED Temperature</div>
        <div class="stat-value" style="font-size:1.2rem;color:{% if leds.led_temp == 'ON' %}var(--orange){% else %}var(--green){% endif %}">{{ leds.led_temp }}</div>
        <div class="stat-footer"><span class="stat-delta">Seuil: &gt; 28 C</span></div>
      </div>
      <div class="stat-card sc-blue">
        <div class="stat-label">LED Humidite</div>
        <div class="stat-value" style="font-size:1.2rem;color:{% if leds.led_hum == 'ON' %}var(--orange){% else %}var(--green){% endif %}">{{ leds.led_hum }}</div>
        <div class="stat-footer"><span class="stat-delta">Seuil: &lt; 20% ou &gt; 80%</span></div>
      </div>
      <div class="stat-card sc-purple">
        <div class="stat-label">Dernier acces RFID</div>
        <div class="stat-value" style="font-size:1rem;color:{% if mqtt_data.last_rfid_status == 'GRANTED' %}var(--green){% else %}var(--red){% endif %}">{{ mqtt_data.last_rfid_status or '—' }}</div>
        <div class="stat-footer"><span class="stat-delta">UID: {{ mqtt_data.last_rfid_uid or '—' }}</span></div>
      </div>
    </div>
    <div class="two-col">
      <div class="panel-card">
        <div class="panel-header">
          <div class="panel-title">ESP8266-DHT <span style="font-size:.6rem;color:var(--text3);font-family:var(--mono);margin-left:6px">smartguard/env</span></div>
          {% if sensor_env %}<span class="sp sp-online"><span class="sp-dot"></span>Live</span>{% else %}<span class="sp sp-offline"><span class="sp-dot"></span>No data</span>{% endif %}
        </div>
        {% if sensor_env %}
        <div class="sensor-row">
          <div class="sensor-icon" style="background:#fff7ed">🌡</div>
          <div><div class="sensor-label">Temperature (DHT11)</div></div>
          <div class="sensor-value">{{ sensor_env.get('temperature','—') }}<span class="sensor-unit">°C</span></div>
        </div>
        <div class="sensor-row">
          <div class="sensor-icon" style="background:#eff6ff">💧</div>
          <div><div class="sensor-label">Humidite (DHT11)</div></div>
          <div class="sensor-value">{{ sensor_env.get('humidity','—') }}<span class="sensor-unit">%</span></div>
        </div>
        <div class="sensor-row">
          <div class="sensor-icon" style="background:var(--surface2)">⏱</div>
          <div><div class="sensor-label">Derniere mise a jour</div></div>
          <div class="sensor-value" style="font-size:.65rem">{{ sensor_env.get('timestamp','—') }}</div>
        </div>
        {% else %}
        <div class="no-data">En attente de donnees ESP8266-DHT<br>Topic: smartguard/env</div>
        {% endif %}
      </div>
      <div class="panel-card">
        <div class="panel-header">
          <div class="panel-title">ESP8266-RFID <span style="font-size:.6rem;color:var(--text3);font-family:var(--mono);margin-left:6px">smartguard/rfid</span></div>
          {% if sensor_rfid %}<span class="sp sp-online"><span class="sp-dot"></span>Live</span>{% else %}<span class="sp sp-offline"><span class="sp-dot"></span>No data</span>{% endif %}
        </div>
        {% if sensor_rfid %}
        <div class="sensor-row">
          <div class="sensor-icon" style="background:var(--primary-lt)">🔖</div>
          <div><div class="sensor-label">Dernier UID scanne</div><div style="font-family:var(--mono);font-size:.82rem;font-weight:700;color:var(--text)">{{ sensor_rfid.get('rfid_tag','—') }}</div></div>
          <div class="sensor-value" style="color:{% if sensor_rfid.get('rfid_status') == 'GRANTED' %}var(--green){% else %}var(--red){% endif %}">{{ sensor_rfid.get('rfid_status','—') }}</div>
        </div>
        <div class="sensor-row">
          <div class="sensor-icon" style="background:var(--purple-lt)">👤</div>
          <div><div class="sensor-label">Identite</div></div>
          <div class="sensor-value" style="font-size:.75rem">{{ sensor_rfid.get('rfid_name','—') }}</div>
        </div>
        <div class="sensor-row">
          <div class="sensor-icon" style="background:var(--green-lt)">📊</div>
          <div><div class="sensor-label">Total acces</div></div>
          <div class="sensor-value">{{ sensor_rfid.get('access_count',0) }}<span class="sensor-unit">events</span></div>
        </div>
        {% else %}
        <div class="no-data">En attente de donnees ESP8266-RFID<br>Topic: smartguard/rfid</div>
        {% endif %}
      </div>
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Journal des acces RFID</div><div class="panel-count">{{ access_log|length }} entrees</div></div>
      {% if access_log %}
      <table class="tbl">
        <thead><tr><th>Heure</th><th>UID</th><th>Identite</th><th>Statut</th></tr></thead>
        <tbody>
        {% for entry in access_log|reverse %}
        <tr>
          <td style="font-family:var(--mono);font-size:.65rem">{{ entry.timestamp }}</td>
          <td class="tbl-ip">{{ entry.uid }}</td>
          <td style="font-size:.75rem;font-weight:600">{{ entry.name }}</td>
          <td><span class="sp {% if entry.status == 'GRANTED' %}sp-online{% else %}sp-blocked{% endif %}"><span class="sp-dot"></span>{{ entry.status }}</span></td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="no-data">Aucun acces enregistre</div>
      {% endif %}
    </div>

  {% elif current_page == 'policy' %}
    <div style="display:flex;align-items:center;justify-content:space-between">
      <div><div class="welcome-text">VLAN Policy</div><div class="welcome-sub">Inter-VLAN access control -- click a cell to toggle allow/deny</div></div>
      <button class="action-btn btn-block btn-sm" onclick="resetPolicy()">Reset to defaults</button>
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Inter-VLAN Matrix</div><div class="panel-count">src to dst</div></div>
      <p style="font-size:.72rem;color:var(--text3);margin-bottom:16px">Rows = source VLAN, Columns = destination VLAN. Click any cell to toggle.</p>
      <table class="policy-matrix" id="vlan-matrix">
        <thead>
          <tr>
            <th>SRC \ DST</th>
            {% for vid in [10,20,30] %}<th>VLAN {{ vid }}<br><span style="font-weight:400;text-transform:none">{{ vlan_names.get(vid,'') }}</span></th>{% endfor %}
          </tr>
        </thead>
        <tbody>
          {% for sv in [10,20,30] %}
          <tr>
            <td class="row-header">VLAN {{ sv }} -- {{ vlan_names.get(sv,'') }}</td>
            {% for dv in [10,20,30] %}
            {% if sv == dv %}
            <td class="policy-cell-same">SAME</td>
            {% else %}
            {% set pol = vlan_policy_matrix.get((sv,dv),'deny') %}
            <td class="{% if pol == 'allow' %}policy-cell-allow{% else %}policy-cell-deny{% endif %}" style="cursor:pointer" onclick="togglePolicy({{ sv }},{{ dv }},'{% if pol == 'allow' %}deny{% else %}allow{% endif %}')">
              <span class="policy-toggle {{ pol }}">{% if pol == 'allow' %}ALLOW{% else %}DENY{% endif %}</span>
            </td>
            {% endif %}
            {% endfor %}
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Per-Host Policy Override</div><div class="panel-count">{{ vlan_hosts|length }} hosts</div></div>
      <table class="tbl" id="host-policy-table">
        <thead><tr><th>Device</th><th>IP</th><th>Current VLAN</th><th>Allow VLANs</th><th>Deny VLANs</th><th>Apply</th></tr></thead>
        <tbody>
          {% for ip, h in vlan_hosts.items() %}
          {% set hp = host_policies.get(ip,{}) %}
          <tr>
            <td><div style="font-size:.78rem;font-weight:600">{{ h.name }}</div></td>
            <td class="tbl-ip">{{ ip }}</td>
            <td><span class="vt vt-{{ h.vlan }}">VLAN {{ h.vlan }}</span></td>
            <td>
              <div style="display:flex;gap:4px;flex-wrap:wrap">
                {% for vid in [10,20,30] %}
                <label style="display:flex;align-items:center;gap:3px;font-size:.62rem;cursor:pointer">
                  <input type="checkbox" id="allow_{{ ip|replace('.','_') }}_{{ vid }}" value="{{ vid }}" {% if vid in hp.get('allow_vlans',[]) %}checked{% endif %} style="width:12px;height:12px">
                  <span class="vt vt-{{ vid }}" style="padding:1px 4px">{{ vid }}</span>
                </label>
                {% endfor %}
              </div>
            </td>
            <td>
              <div style="display:flex;gap:4px;flex-wrap:wrap">
                {% for vid in [10,20,30] %}
                <label style="display:flex;align-items:center;gap:3px;font-size:.62rem;cursor:pointer">
                  <input type="checkbox" id="deny_{{ ip|replace('.','_') }}_{{ vid }}" value="{{ vid }}" {% if vid in hp.get('deny_vlans',[]) %}checked{% endif %} style="width:12px;height:12px">
                  <span class="vt vt-{{ vid }}" style="padding:1px 4px">{{ vid }}</span>
                </label>
                {% endfor %}
              </div>
            </td>
            <td><button class="action-btn btn-primary btn-sm" onclick="applyHostPolicy('{{ ip }}')">Apply</button></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Current Active Rules</div></div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        {% for (sv,dv), pol in vlan_policy_matrix.items() %}
        {% if sv != dv %}
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.68rem">
          <span style="font-family:var(--mono)">VLAN{{ sv }} to VLAN{{ dv }}</span>
          <span class="sp {% if pol == 'allow' %}sp-online{% else %}sp-blocked{% endif %}"><span class="sp-dot"></span>{{ pol|upper }}</span>
        </div>
        {% endif %}
        {% endfor %}
      </div>
    </div>

  {% elif current_page == 'qos' %}
    <div><div class="welcome-text">QoS Monitor</div><div class="welcome-sub">Queue assignment and bandwidth priority per host</div></div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">
      {% for qid, q in qos_queues.items() %}
      <div class="stat-card {% if qid == 0 %}sc-orange{% elif qid == 3 %}sc-blue{% else %}sc-green{% endif %}" style="padding:14px 16px">
        <div class="stat-label">{{ q.name }}</div>
        <div class="stat-value" style="font-size:1rem;margin:6px 0 4px;letter-spacing:0">Q{{ qid }}</div>
        <div style="font-size:.62rem;color:var(--text3);font-family:var(--mono)">{{ q.min }}–{{ q.max }}</div>
      </div>
      {% endfor %}
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">Host Queue Assignments</div><div class="panel-count">{{ vlan_hosts|length }} hosts</div></div>
      <div class="qos-section">
        {% for ip, h in vlan_hosts.items() %}
        <div class="qos-row q{{ h.queue_id }}">
          <div class="qos-name" title="{{ h.name }}">{{ h.name }}</div>
          <div class="qos-ip">{{ ip }}</div>
          <div class="qos-badge">{{ h.qos_level }}</div>
          <div class="qos-bar-bg"><div class="qos-bar" style="width:{{ [100-h.queue_id*20,10]|max }}%"></div></div>
          <span style="font-size:.6rem;font-family:var(--mono);color:var(--text3);flex-shrink:0">Q{{ h.queue_id }}</span>
        </div>
        {% endfor %}
      </div>
    </div>

  {% elif current_page == 'alerts' %}
    <div style="display:flex;align-items:center;justify-content:space-between">
      <div><div class="welcome-text">AI Security Alerts</div><div class="welcome-sub">Anomaly detection and security events</div></div>
      {% if alert_count > 0 %}<span class="sp sp-blocked" style="font-size:.7rem;padding:5px 14px"><span class="sp-dot"></span>{{ alert_count }} Active</span>{% else %}<span class="sp sp-online" style="font-size:.7rem;padding:5px 14px"><span class="sp-dot"></span>All Clear</span>{% endif %}
    </div>
    <div class="panel-card">
      <div class="panel-header"><div class="panel-title">All Alerts</div><div class="panel-count">{{ alerts|length }} total</div></div>
      <div class="alert-rows">
        {% if alerts %}
        {% for a in alerts|reverse %}
        <div class="alert-row {{ a.severity }}"><div class="a-sev">{{ a.severity }}</div><div class="a-body"><div class="a-type">{{ a.type }}</div><div class="a-msg">{{ a.message }}</div></div><div class="a-ts">{{ a.timestamp }}</div></div>
        {% endfor %}
        {% else %}
        <div class="no-data">No alerts -- network is clear.</div>
        {% endif %}
      </div>
    </div>

  {% elif current_page == 'camera' %}
    <div><div class="welcome-text">Camera Feed</div><div class="welcome-sub">Live frame from RPi-Camera (192.168.30.1)</div></div>
    <div class="panel-card" style="max-width:640px">
      <div class="panel-header"><div class="panel-title">Live Feed</div>{% if camera.data %}<span class="sp sp-online"><span class="sp-dot"></span>Signal</span>{% else %}<span class="sp sp-offline"><span class="sp-dot"></span>No Signal</span>{% endif %}</div>
      {% if camera.data %}
      <img id="cam-img" src="data:image/jpeg;base64,{{ camera.data }}" alt="Camera Feed"/>
      <div class="cam-meta" style="margin-top:10px">Source: {{ camera.ip }} &nbsp;·&nbsp; {{ camera.timestamp }}</div>
      {% else %}
      <div class="no-cam"><div style="font-size:.65rem;font-weight:600;letter-spacing:.8px;text-transform:uppercase">No Signal</div><div style="font-size:.6rem">Waiting for frame from RPi-Camera</div></div>
      {% endif %}
    </div>

  {% endif %}

  </div>
  <footer>
    <a class="ext-btn" href="http://localhost:3000" target="_blank">Grafana</a>
    <a class="ext-btn" href="/api/twin" target="_blank">State JSON</a>
    <div class="footer-sp">Digital Twin Network Monitor · auto-refresh 12s</div>
  </footer>
</div>

<div class="refresh-bar"><div class="refresh-inner"></div></div>

<script>
function act(ip, action) {
  fetch('/api/'+action+'/'+ip,{method:'POST'}).then(r=>r.json()).then(d=>{alert(d.message);location.reload();});
}
function togglePolicy(sv,dv,newAction) {
  fetch('/api/policy/vlan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({src_vlan:sv,dst_vlan:dv,action:newAction})})
    .then(r=>r.json()).then(d=>{if(d.status==='ok')location.reload();else alert(d.error);});
}
function resetPolicy() {
  if(!confirm('Reset all VLAN policies to defaults?'))return;
  fetch('/api/policy/reset',{method:'POST'}).then(r=>r.json()).then(()=>location.reload());
}
function applyHostPolicy(ip) {
  const safe=ip.replace(/\./g,'_');
  const allow=[10,20,30].filter(v=>document.getElementById('allow_'+safe+'_'+v)?.checked);
  const deny=[10,20,30].filter(v=>document.getElementById('deny_'+safe+'_'+v)?.checked);
  fetch('/api/policy/host',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip,allow_vlans:allow,deny_vlans:deny})})
    .then(r=>r.json()).then(d=>{alert(d.message||d.error);});
}
function openSettings(){document.getElementById('settings-overlay').classList.add('open');document.getElementById('settings-panel').classList.add('open');}
function closeSettings(){document.getElementById('settings-overlay').classList.remove('open');document.getElementById('settings-panel').classList.remove('open');}
function setTheme(t){
  const root=document.documentElement;
  root.setAttribute('data-theme',t==='auto'?(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t);
  localStorage.setItem('nettwin-theme',t);
  ['light','dark'].forEach(id=>{const e=document.getElementById('opt-'+id);if(e)e.classList.toggle('selected',t===id);});
}
(function(){setTheme(localStorage.getItem('nettwin-theme')||'light');})();
const si=document.getElementById('search-input');
if(si)si.addEventListener('input',function(){
  const q=this.value.toLowerCase();
  document.querySelectorAll('#vlan-table tbody tr,#host-policy-table tbody tr').forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?'':'none');
  document.querySelectorAll('.alert-row').forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?'':'none');
});
setTimeout(()=>location.reload(),12000);
</script>
</body>
</html>
"""

# =============================================================
EXCLUDE_IPS = {CONTROLLER_IP, "192.168.10.254", "192.168.20.254", "192.168.30.254"}

def _build_context(page="dashboard"):
    state   = read_state()
    blocked = set(state.get("blocked", []))
    hosts   = state.get("hosts", {})
    mqtt    = state.get("mqtt_data", {})

    vlan_hosts = {}
    for ip, info in HOST_INFO.items():
        if not ip.startswith("192.168"):
            continue
        if ip in EXCLUDE_IPS:
            continue
        hd = hosts.get(ip, {})
        vlan_hosts[ip] = {
            "name":      info["name"],
            "role":      info["role"],
            "vlan":      HOST_VLAN.get(ip, 0),
            "status":    hd.get("status", "offline"),
            "qos_level": HOST_QOS.get(ip, {}).get("level", "NORMAL"),
            "queue_id":  HOST_QOS.get(ip, {}).get("queue", 3),
            "sensors":   info.get("sensors", []),
        }

    PAGE_TITLES = {
        "dashboard": "Dashboard", "devices": "Devices",
        "sensors": "Sensors", "policy": "VLAN Policy",
        "qos": "QoS Monitor", "alerts": "AI Alerts",
        "camera": "Camera", "settings": "Settings",
    }

    online_count  = sum(1 for ip, h in vlan_hosts.items() if h["status"] == "online" and ip not in blocked)
    blocked_count = len(blocked)
    alert_count   = len(state.get("alerts", []))
    total_devices = len(vlan_hosts) + 3

    sensor_data = state.get("sensor_data", {})
    sensor_env  = sensor_data.get("192.168.1.36") or mqtt.get("env")
    sensor_rfid = sensor_data.get("192.168.1.37") or mqtt.get("rfid")
    leds        = mqtt.get("leds", {"led_temp": "OFF", "led_hum": "OFF"})
    access_log  = mqtt.get("access_log", [])

    vlans = [10, 20, 30]
    vlan_policy_matrix = {}
    for sv in vlans:
        for dv in vlans:
            vlan_policy_matrix[(sv, dv)] = get_vlan_policy(state, sv, dv)

    return dict(
        current_page       = page,
        page_title         = PAGE_TITLES.get(page, "Dashboard"),
        vlan_hosts         = vlan_hosts,
        all_hosts          = HOST_INFO,
        blocked            = blocked,
        alerts             = state.get("alerts", []),
        camera             = state.get("camera", _cam),
        vlan_names         = VLAN_NAMES,
        qos_queues         = QOS_QUEUES,
        last_updated       = state.get("last_updated", ""),
        online_count       = online_count,
        blocked_count      = blocked_count,
        alert_count        = alert_count,
        total_devices      = total_devices,
        controller_ip      = CONTROLLER_IP,
        sensor_data        = sensor_data,
        vlan_policy_matrix = vlan_policy_matrix,
        host_policies      = state.get("host_policy", {}),
        sensor_env         = sensor_env,
        sensor_rfid        = sensor_rfid,
        leds               = leds,
        access_log         = access_log,
        mqtt_data          = mqtt,
    )


# =============================================================
# ROUTES
# =============================================================
@app.route("/")
def dashboard():    return render_template_string(HTML, **_build_context("dashboard"))
@app.route("/devices")
def page_devices(): return render_template_string(HTML, **_build_context("devices"))
@app.route("/sensors")
def page_sensors(): return render_template_string(HTML, **_build_context("sensors"))
@app.route("/policy")
def page_policy():  return render_template_string(HTML, **_build_context("policy"))
@app.route("/qos")
def page_qos():     return render_template_string(HTML, **_build_context("qos"))
@app.route("/alerts")
def page_alerts():  return render_template_string(HTML, **_build_context("alerts"))
@app.route("/camera")
def page_camera():  return render_template_string(HTML, **_build_context("camera"))

@app.route("/api/twin")
def api_twin():
    return jsonify(read_state())

@app.route("/api/block/<ip>", methods=["POST"])
def api_block(ip):
    state = read_state()
    blocked = set(state.get("blocked", []))
    blocked.add(ip)
    state["blocked"] = list(blocked)
    state.setdefault("alerts", []).append({"type":"ADMIN_BLOCK","message":f"Admin blocked {ip}","severity":"HIGH","timestamp":time.strftime("%Y-%m-%d %H:%M:%S")})
    write_state(state)
    return jsonify({"status": "ok", "message": f"{ip} blocked"})

@app.route("/api/unblock/<ip>", methods=["POST"])
def api_unblock(ip):
    state = read_state()
    state["blocked"] = [x for x in state.get("blocked", []) if x != ip]
    state.setdefault("alerts", []).append({"type":"ADMIN_UNBLOCK","message":f"Admin unblocked {ip}","severity":"LOW","timestamp":time.strftime("%Y-%m-%d %H:%M:%S")})
    write_state(state)
    return jsonify({"status": "ok", "message": f"{ip} unblocked"})

@app.route("/api/policy/vlan", methods=["POST"])
def api_policy_vlan():
    data = request.get_json(force=True) or {}
    sv   = int(data.get("src_vlan", 0))
    dv   = int(data.get("dst_vlan", 0))
    act  = str(data.get("action", "deny"))
    if sv not in (10, 20, 30) or dv not in (10, 20, 30):
        return jsonify({"error": "invalid VLAN id"}), 400
    if act not in ("allow", "deny"):
        return jsonify({"error": "action must be allow or deny"}), 400
    set_vlan_policy(sv, dv, act)
    add_alert("ADMIN_POLICY", f"VLAN {sv} to {dv} set to {act.upper()} by admin", "LOW")
    return jsonify({"status": "ok", "src_vlan": sv, "dst_vlan": dv, "action": act})

@app.route("/api/policy/host", methods=["POST"])
def api_policy_host():
    data  = request.get_json(force=True) or {}
    ip    = str(data.get("ip", ""))
    allow = [int(v) for v in data.get("allow_vlans", [])]
    deny  = [int(v) for v in data.get("deny_vlans", [])]
    if not ip:
        return jsonify({"error": "missing ip"}), 400
    set_host_policy(ip, allow, deny)
    add_alert("ADMIN_HOST_POLICY", f"Host {ip}: allow={allow} deny={deny}", "LOW")
    return jsonify({"status": "ok", "message": f"Policy updated for {ip}"})

@app.route("/api/policy/reset", methods=["POST"])
def api_policy_reset():
    reset_vlan_policy()
    add_alert("ADMIN_POLICY_RESET", "All VLAN policies reset to defaults by admin", "MEDIUM")
    return jsonify({"status": "ok", "message": "Policies reset to defaults"})

@app.route("/api/policy/status", methods=["GET"])
def api_policy_status():
    state = read_state()
    return jsonify({
        "vlan_policy": state.get("vlan_policy", {}),
        "host_policy":  state.get("host_policy", {}),
    })

@app.route("/api/camera/frame", methods=["POST"])
def camera_frame():
    raw = request.get_data()
    if not raw:
        return jsonify({"error": "no data"}), 400
    _cam["data"]      = base64.b64encode(raw).decode()
    _cam["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _cam["ip"]        = request.headers.get("X-IP", request.remote_addr)
    state = read_state()
    state["camera"] = _cam
    write_state(state)
    return jsonify({"status": "ok", "bytes": len(raw)})

@app.route("/api/iot/status", methods=["POST"])
def iot_status():
    data = request.get_json(force=True) or {}
    ip   = data.get("ip", request.remote_addr)
    data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state = read_state()
    state.setdefault("sensor_data", {})[ip] = {k: v for k, v in data.items() if k != "ip"}
    if data.get("flame") and int(data.get("flame", 0)):
        add_alert("FLAME_DETECTED", f"Flame sensor triggered on {ip}!", "CRITICAL")
    write_state(state)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print(f"[flask] Dashboard: http://localhost:{FLASK_PORT}")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)
