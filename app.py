import streamlit as st
import pandas as pd
import json
import io
import datetime
import hashlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Circle, Polygon
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(
    page_title="UAE Enterprise Engineering Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- مفتاح الـ API وتأمينه -----------------
secret_key = st.secrets.get("GEMINI_API_KEY", "")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": True, "user": "Super Admin"}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ----------------- الشريط الجانبي: اختيار المنظومة -----------------
st.sidebar.markdown(f"**👤 المستخدم:** `{st.session_state.auth['user']}`")
if st.sidebar.button("🔄 تصفير وبدء مشروع جديد", key="btn_reset_all"):
    st.session_state.chat_history = []
    st.rerun()

st.sidebar.markdown("---")
active_app = st.sidebar.radio(
    "المنظومات التخصصية المستقلة:",
    [
        "1. التصميم المعماري والمناظير (G+1+Roof)",
        "2. المخطط الإنشائي وأبعاد المحاور (Framing)",
        "3. مخططات الخدمات والدفاع المدني (MEP Set)",
        "4. حصر كتل وأطوال الهياكل الحديدية (Steel QTO)",
        "5. كراسة الكميات المستقلة لمشروع قائم (BOQ)",
        "6. محرك الجدولة الزمنية لبريمافيرا (Primavera P6)",
        "7. المستشار الهندسي والبلدي الذكي (AI Copilot)"
    ],
    key="nav_engine_selection"
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["أبوظبي / العين (ADIBC)", "الشارقة (المناطق الحضرية والشرقية)", "دبي (Dubai Building Code)", "عجمان / الفجيرة"],
    key="select_emirate"
)

# محددات البناء البلدية
if "أبوظبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 5.0, 3.0, 2.0, 0.50, 0.35
elif "الشارقة" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.5, 3.0, 1.5, 0.55, 0.40
elif "دبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.50, 0.35
else:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.55, 0.40

override_key = st.sidebar.text_input("تحديث مفتاح Gemini API (اختياري):", type="password", key="inp_override_api")
active_api_key = override_key.strip() if override_key.strip() else secret_key.strip()

# ==============================================================================
# 1. التصميم المعماري والمناظير 3D (G+1+Roof)
# ==============================================================================
if "1. التصميم المعماري" in active_app:
    st.title("🏛️ المساقط المعمارية التنفيذية والمنظور الحجمي (G+1+Roof)")
    
    c_in1, c_in2, c_in3 = st.columns(3)
    with c_in1:
        plot_w = st.number_input("عرض واجهة القسيمة (متر):", 14.0, 250.0, 30.0, 0.5, key="arch_pw")
    with c_in2:
        plot_l = st.number_input("عمق القسيمة الداخلي (متر):", 16.0, 350.0, 50.0, 0.5, key="arch_pl")
    with c_in3:
        stair_style = st.selectbox("طراز بيت الدرج الرئيسي:", ["درج حلزوني ببرج زجاجي", "درج مقوس إمبراطوري", "درج تقليدي قلبتين مع بسطة"], key="arch_stair_style")

    plot_area = round(plot_w * plot_l, 2)
    net_w = max(0.0, plot_w - (2 * side_sb))
    net_l = max(0.0, plot_l - (front_sb + rear_sb))
    effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov, 2))
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
    ff_area = round(effective_ground * 0.90, 1)
    roof_area = round(effective_ground * roof_cov, 1)

    t_fl1, t_fl2, t_fl3, t_fl4 = st.tabs(["📐 الطابق الأرضي", "📐 الطابق الأول", "📐 طابق الروف والسطح", "🏛️ المنظور المعماري 3D"])

    corridor_w = 2.4
    corridor_x = side_sb + net_w*0.48 - corridor_w/2
    st_x, st_y, st_w, st_h = corridor_x - 0.4, rear_sb + buildable_l*0.38, 3.2, 4.0

    with t_fl1:
        fig_g, ax_g = plt.subplots(figsize=(9, 12), dpi=180)
        ax_g.set_facecolor('#FFFFFF')
        ax_g.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_g.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.5, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        # ممر التوزيع الرئيسي
        ax_g.add_patch(Rectangle((corridor_x, rear_sb), corridor_w, buildable_l, facecolor='#F1F5F9', edgecolor='#94A3B8', lw=1.0))
        ax_g.text(corridor_x + corridor_w/2, rear_sb + buildable_l*0.5, "ممر التوزيع والبهو الرئيسي\nMain Corridor (W=2.40m)", ha='center', va='center', fontsize=8, weight='bold', color='#475569', rotation=90)

        rooms_g = [
            {"n": "مجلس رجال رسمي\nFormal Majlis\n(7.50 x 5.40m)", "x": side_sb, "y": rear_sb + buildable_l*0.60, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.40, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Hall\n(5.40 x 5.40m)", "x": side_sb, "y": rear_sb + buildable_l*0.30, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ تحضيري ورئيسي\nKitchen Suite\n(4.50 x 5.00m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FED7AA"},
            {"n": "صالة معيشة عائلية بانورامية\nLiving Family Hall\n(7.00 x 8.50m)", "x": corridor_x + corridor_w, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح نوم الضيوف / كبار السن\nGuest Suite (4.80 x 3.80m)", "x": corridor_x + corridor_w, "y": rear_sb, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]
        for r in rooms_g:
            ax_g.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_g.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=8, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', lw=0.8))

        # بيت الدرج بالأرضي
        ax_g.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 14):
            ax_g.plot([st_x, st_x + st_w], [sy, sy], color='#475569', lw=1.2)
        ax_g.annotate('صعود UP (26 Nos)', xy=(st_x + st_w/2, st_y + st_h - 0.3), xytext=(st_x + st_w/2, st_y + 0.4),
                      ha='center', fontsize=8.5, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=2.0))

        # الأبواب مع مسار الفتح
        doors_g = [(side_sb + net_w*0.22, rear_sb + buildable_l, 1.2, 180, 270), (corridor_x + corridor_w/2, rear_sb + buildable_l, 1.4, 270, 360),
                   (corridor_x, rear_sb + buildable_l*0.75, 1.0, 90, 180), (corridor_x + corridor_w, rear_sb + buildable_l*0.25, 1.0, 0, 90)]
        for dx, dy, dr, a1, a2 in doors_g:
            ax_g.add_patch(Arc((dx, dy), dr*2, dr*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax_g.plot([dx, dx + dr], [dy, dy], color='#0F172A', lw=2.0)

        ax_g.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_g.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_g.set_aspect('equal')
        ax_g.axis('off')
        ax_g.set_title(f"مسقط الطابق الأرضي التنفيذي (GF: {effective_ground:.1f} م²)", fontsize=11, weight='bold')
        st.pyplot(fig_g)

    with t_fl2:
        fig_f, ax_f = plt.subplots(figsize=(9, 12), dpi=180)
        ax_f.set_facecolor('#FFFFFF')
        ax_f.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_f.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.5, edgecolor='#DC2626', linestyle='--', facecolor='none'))
        ax_f.add_patch(Rectangle((corridor_x, rear_sb), corridor_w, buildable_l, facecolor='#F1F5F9', edgecolor='#94A3B8', lw=1.0))

        rooms_f = [
            {"n": "جناح النوم الرئيسي الملكي\nMaster Bedroom Suite\n(6.50 x 5.40m)", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.45, "c": "#EDE9FE"},
            {"n": "دريسنج وحمام جاكوزي\nDressing & Ensuite\n(4.50 x 5.00m)", "x": side_sb, "y": rear_sb + buildable_l*0.25, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#DDD6FE"},
            {"n": "جناح نوم الأبناء 1\nBedroom Suite 1\n(4.50 x 5.00m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.25, "c": "#CCFBF1"},
            {"n": "صالة معيشة علوية + بوفيه\nLiving & Pantry\n(5.00 x 6.00m)", "x": corridor_x + corridor_w, "y": rear_sb + buildable_l*0.50, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.50, "c": "#E0F2FE"},
            {"n": "جناح نوم الأبناء 2 + 3\nBedroom Suites 2 & 3\n(5.00 x 7.00m)", "x": corridor_x + corridor_w, "y": rear_sb, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.50, "c": "#FEF3C7"}
        ]
        for r in rooms_f:
            ax_f.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_f.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=8, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', lw=0.8))

        ax_f.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#FEF08A', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 14):
            ax_f.plot([st_x, st_x + st_w], [sy, sy], color='#B45309', lw=1.2, linestyle='--')
        ax_f.annotate('هبوط DN\n(Void Open)', xy=(st_x + st_w/2, st_y + 0.4), xytext=(st_x + st_w/2, st_y + st_h - 0.4),
                      ha='center', fontsize=8.0, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))

        ax_f.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_f.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_f.set_aspect('equal')
        ax_f.axis('off')
        ax_f.set_title(f"مسقط الطابق الأول التنفيذي (FF: {ff_area:.1f} م²)", fontsize=11, weight='bold')
        st.pyplot(fig_f)

    with t_fl3:
        fig_r, ax_r = plt.subplots(figsize=(9, 12), dpi=180)
        ax_r.set_facecolor('#FFFFFF')
        ax_r.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_r.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, lw=2.0, edgecolor='#64748B', facecolor='#F1F5F9'))
        ax_r.text(side_sb + net_w*0.5, rear_sb + buildable_l*0.88, "سطح مبلط (Roof Terrace)", ha='center', fontsize=9, weight='bold', color='#475569')

        rf_w, rf_l = net_w * 0.60, buildable_l * 0.45
        rf_x, rf_y = side_sb + net_w*0.20, rear_sb + buildable_l*0.25
        ax_r.add_patch(Rectangle((rf_x, rf_y), rf_w, rf_l, lw=2.5, edgecolor='#0F172A', facecolor='#FEF3C7'))
        ax_r.plot([rf_x, rf_x + rf_w], [rf_y + rf_l*0.5, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w/2, rf_y + rf_l*0.75, "صالة ألعاب ورياضة\nRoof Gym (5.0 x 6.5m)", ha='center', va='center', fontsize=8, weight='bold')
        ax_r.plot([rf_x + rf_w*0.5, rf_x + rf_w*0.5], [rf_y, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w*0.25, rf_y + rf_l*0.25, "غسيل\nLaundry", ha='center', va='center', fontsize=7.5, weight='bold')
        ax_r.text(rf_x + rf_w*0.75, rf_y + rf_l*0.25, "خادمة + حمام\nMaid's Room", ha='center', va='center', fontsize=7.5, weight='bold')

        ax_r.add_patch(Rectangle((st_x, st_y), st_w, 2.4, facecolor='#CBD5E1', edgecolor='#0F172A', lw=2.0))
        ax_r.text(st_x + st_w/2, st_y + 1.2, "بيت الدرج والمصعد\nStair Core & Lift", ha='center', va='center', fontsize=8, weight='bold')

        ax_r.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_r.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_r.set_aspect('equal')
        ax_r.axis('off')
        ax_r.set_title(f"طابق الروف والملحق (Roof: {roof_area:.1f} م²)", fontsize=11, weight='bold')
        st.pyplot(fig_r)

    with t_fl4:
        fig_3d, ax_3d = plt.subplots(figsize=(11, 7.5), dpi=200)
        ax_3d.set_facecolor('#F0F9FF')
        cos30, sin30 = np.cos(np.radians(30)), np.sin(np.radians(30))
        def iso(x, y, z): return (x - y) * cos30, (x + y) * sin30 + z

        p_ground = [iso(-2, -2, 0), iso(22, -2, 0), iso(22, 20, 0), iso(-2, 20, 0)]
        ax_3d.add_patch(Polygon(p_ground, facecolor='#E2E8F0', edgecolor='#94A3B8', lw=1.5))

        bx, by, bz1 = 15, 12, 4.0
        ax_3d.add_patch(Polygon([iso(0, 0, 0), iso(bx, 0, 0), iso(bx, 0, bz1), iso(0, 0, bz1)], facecolor='#F8FAFC', edgecolor='#334155', lw=1.8))
        ax_3d.add_patch(Polygon([iso(bx, 0, 0), iso(bx, by, 0), iso(bx, by, bz1), iso(bx, 0, bz1)], facecolor='#CBD5E1', edgecolor='#334155', lw=1.8))

        bz2 = 7.5
        ax_3d.add_patch(Polygon([iso(-0.5, -0.5, bz1), iso(bx+0.5, -0.5, bz1), iso(bx+0.5, -0.5, bz2), iso(-0.5, -0.5, bz2)], facecolor='#FFFFFF', edgecolor='#1E293B', lw=2.0))
        ax_3d.add_patch(Polygon([iso(bx+0.5, -0.5, bz1), iso(bx+0.5, by, bz1), iso(bx+0.5, by, bz2), iso(bx+0.5, -0.5, bz2)], facecolor='#94A3B8', edgecolor='#1E293B', lw=2.0))

        bz3 = 10.5
        rx1, ry1, rx2 = 3.0, 2.0, 11.0
        ax_3d.add_patch(Polygon([iso(rx1, ry1, bz2), iso(rx2, ry1, bz2), iso(rx2, ry1, bz3), iso(rx1, ry1, bz3)], facecolor='#FEF3C7', edgecolor='#B45309', lw=1.8))
        ax_3d.add_patch(Polygon([iso(rx2, ry1, bz2), iso(rx2, by-1, bz2), iso(rx2, by-1, bz3), iso(rx2, ry1, bz3)], facecolor='#FDE68A', edgecolor='#B45309', lw=1.8))

        tx, tw, tz_top = 5.5, 3.8, 11.2
        p_tower = [iso(tx, -1.2, 0), iso(tx+tw, -1.2, 0), iso(tx+tw, -1.2, tz_top), iso(tx, -1.2, tz_top)]
        ax_3d.add_patch(Polygon(p_tower, facecolor='#38BDF8', edgecolor='#0F172A', lw=2.2, alpha=0.88))
        for zh in np.arange(1.2, tz_top, 1.2):
            pa, pb = iso(tx, -1.2, zh), iso(tx+tw, -1.2, zh)
            ax_3d.plot([pa[0], pb[0]], [pa[1], pb[1]], color='#0F172A', lw=1.5)

        p_door = [iso(tx+tw+0.6, -0.5, 0), iso(tx+tw+2.6, -0.5, 0), iso(tx+tw+2.6, -0.5, 3.2), iso(tx+tw+0.6, -0.5, 3.2)]
        ax_3d.add_patch(Polygon(p_door, facecolor='#78350F', edgecolor='#451A03', lw=1.8))
        ax_3d.set_aspect('equal')
        ax_3d.axis('off')
        ax_3d.set_title("المنظور المعماري الحجمي (3D Perspective) - فيلا G + 1 + Roof", fontsize=11, weight='bold')
        st.pyplot(fig_3d)

# ==============================================================================
# 2. المخطط الإنشائي وأبعاد المحاور
# ==============================================================================
elif "2. المخطط الإنشائي" in active_app:
    st.title("🏗️ المخطط الإنشائي التنفيذي وخطوط الأبعاد بين المحاور (Framing Plan)")
    
    col_w, col_l, col_sbc = st.columns(3)
    with col_w: pw = st.number_input("عرض البناء الصافي (متر):", 10.0, 100.0, 26.0, 0.5, key="str_pw")
    with col_l: pl = st.number_input("عمق البناء الصافي (متر):", 10.0, 150.0, 32.0, 0.5, key="str_pl")
    with col_sbc: sbc_in = st.number_input("جهد التربة SBC (kN/m²):", 60.0, 400.0, 150.0, 10.0, key="str_sbc")

    col_load_u = 1350.0
    footing_a = (col_load_u / 1.45) / sbc_in
    footing_d = np.sqrt(footing_a)
    footing_th = max(0.50, round(footing_d * 0.25, 2))

    gx = [2.0, 2.0 + pw*0.35, 2.0 + pw*0.70, 2.0 + pw]
    gy = [2.0, 2.0 + pl*0.35, 2.0 + pl*0.70, 2.0 + pl]
    x_tags, y_tags = ["1", "2", "3", "4"], ["A", "B", "C", "D"]

    fig_str, ax_s = plt.subplots(figsize=(10, 13), dpi=180)
    ax_s.set_facecolor('#FFFFFF')

    for idx, x in enumerate(gx):
        ax_s.plot([x, x], [gy[0] - 2.5, gy[-1] + 3.0], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(x, gy[-1] + 3.8, x_tags[idx], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))
    for idx, y in enumerate(gy):
        ax_s.plot([gx[0] - 2.5, gx[-1] + 3.0], [y, y], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(gx[0] - 3.4, y, y_tags[idx], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))

    for x in gx: ax_s.plot([x, x], [gy[0], gy[-1]], color='#475569', lw=3.0)
    for y in gy: ax_s.plot([gx[0], gx[-1]], [y, y], color='#475569', lw=3.0)

    for x in gx:
        for y in gy:
            ax_s.add_patch(Rectangle((x - footing_d/2, y - footing_d/2), footing_d, footing_d, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
            ax_s.add_patch(Rectangle((x - 0.10, y - 0.30), 0.20, 0.60, facecolor='#0F172A', edgecolor='black', lw=1.2))

    # أبعاد المحاور الأفقية
    dim_y = gy[-1] + 1.6
    for i in range(len(gx) - 1):
        ax_s.annotate('', xy=(gx[i], dim_y), xytext=(gx[i+1], dim_y), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_s.text((gx[i] + gx[i+1])/2, dim_y + 0.3, f"{gx[i+1] - gx[i]:.2f} m", ha='center', fontsize=8.5, weight='bold')
    ax_s.annotate('', xy=(gx[0], dim_y + 1.2), xytext=(gx[-1], dim_y + 1.2), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.5))
    ax_s.text((gx[0] + gx[-1])/2, dim_y + 1.5, f"Total = {pw:.2f} m", ha='center', fontsize=9.0, weight='bold', color='#1E3A8A')

    # أبعاد المحاور الرأسية
    dim_x = gx[-1] + 1.6
    for j in range(len(gy) - 1):
        ax_s.annotate('', xy=(dim_x, gy[j]), xytext=(dim_x, gy[j+1]), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_s.text(dim_x + 0.4, (gy[j] + gy[j+1])/2, f"{gy[j+1] - gy[j]:.2f} m", ha='left', va='center', fontsize=8.5, weight='bold', rotation=90)
    ax_s.annotate('', xy=(dim_x + 1.2, gy[0]), xytext=(dim_x + 1.2, gy[-1]), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.5))
    ax_s.text(dim_x + 1.6, (gy[0] + gy[-1])/2, f"Total = {pl:.2f} m", ha='left', va='center', fontsize=9.0, weight='bold', color='#1E3A8A', rotation=90)

    ax_s.set_xlim(gx[0] - 5, gx[-1] + 5)
    ax_s.set_ylim(gy[0] - 4, gy[-1] + 6)
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    st.pyplot(fig_str)
    st.success(f"القاعدة F1: أبعاد {footing_d:.2f} × {footing_d:.2f} × {footing_th:.2f} م | التسليح: 7 T 16mm/m باتجاهين | الميدات: 20 × 60 سم.")

# ==============================================================================
# 3. مخططات الخدمات والدفاع المدني (MEP Set)
# ==============================================================================
elif "3. مخططات الخدمات" in active_app:
    st.title("⚡ مخططات الخدمات الكهروميكانيكية والدفاع المدني (MEP Set)")
    mep_layer = st.radio("اختر شبكة الخدمات لعرضها وتدقيقها على المسقط:", [
        "1. شبكة الصرف الصحي وغرف التفتيش (Plumbing & Drainage)",
        "2. شبكة الكهرباء والإنارة ومأخذ القوى (Electrical & Lighting)",
        "3. مخطط السلامة ومكافحة الحريق (Civil Defence & Life Safety)"
    ], horizontal=True, key="rad_mep_layer")

    fig_m, ax_m = plt.subplots(figsize=(10, 8), dpi=180)
    ax_m.set_facecolor('#FFFFFF')
    ax_m.add_patch(Rectangle((2, 2), 24, 28, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))

    if "الصرف" in mep_layer:
        ax_m.plot([4, 4], [2, 30], color='#92400E', lw=4.0, linestyle='--')
        ax_m.text(4.5, 16, 'خط الصرف الرئيسي Soil Pipe 4" (Slope 1:100)', color='#78350F', fontsize=8.5, weight='bold', rotation=90)
        for y_ic in [4, 12, 20, 28]:
            ax_m.plot(4, y_ic, marker='s', markersize=14, color='#78350F')
            ax_m.text(5.5, y_ic, f"غرفة تفتيش IC (450x450mm)", fontsize=8)
        ax_m.plot(8, 6, marker='^', markersize=14, color='#D97706')
        ax_m.text(9.5, 6, "مصيدة شحوم المطبخ Grease Trap", fontsize=8.5, weight='bold')
        ax_m.set_title("مخطط شبكة الصرف الصحي ومصائد الشحوم وغرف التفتيش", fontsize=11, weight='bold')
    elif "الكهرباء" in mep_layer:
        ax_m.plot([2, 10], [28, 28], color='#1E3A8A', lw=3.0)
        ax_m.text(6, 28.5, "Main Distribution Board (MDB-160A)", ha='center', weight='bold', fontsize=9)
        for lx in [6, 12, 18, 22]:
            for ly in [6, 12, 18, 24]:
                ax_m.plot(lx, ly, marker='o', markersize=10, color='#EAB308')
                ax_m.text(lx, ly+0.8, "LED 60x60", ha='center', fontsize=7)
                ax_m.plot([lx, lx+2], [ly, ly], color='#F59E0B', linestyle=':')
        ax_m.set_title("مخطط توزيع وحدات الإنارة LED ومسارات التغذية الكهربائية", fontsize=11, weight='bold')
    else:
        for sx in [8, 16, 22]:
            for sy in [8, 16, 24]:
                ax_m.plot(sx, sy, marker='o', markersize=10, color='red')
                ax_m.text(sx, sy+0.8, "[SD] كاشف دخان", ha='center', color='red', fontsize=7.5, weight='bold')
        ax_m.plot(14, 2, marker='s', markersize=14, color='darkred')
        ax_m.text(14, 0.8, "مطفأة حريق DCP 6kg + كابينة FHR", ha='center', color='darkred', fontsize=8.5, weight='bold')
        ax_m.annotate('مسار الهروب الآمن للمخرج الرئيسي (Egress <= 20m)', xy=(14, 2), xytext=(14, 8),
                      ha='center', color='green', weight='bold', fontsize=9, arrowprops=dict(arrowstyle="->", color='green', lw=2.5))
        ax_m.set_title("مخطط السلامة ومكافحة الحريق المعتمد (Civil Defence Plan)", fontsize=11, weight='bold')

    ax_m.set_xlim(0, 30); ax_m.set_ylim(0, 32); ax_m.axis('off')
    st.pyplot(fig_m)

# ==============================================================================
# 4. حصر كتل وأطوال الهياكل الحديدية (Steel QTO)
# ==============================================================================
elif "4. حصر كتل وأطوال الهياكل الحديدية" in active_app:
    st.title("🔩 محرك حصر وتفصيل الهياكل الحديدية (Structural Steel QTO)")
    st.caption("حصر أطوال القطاعات، الأوزان الإجمالية، ومساحات الحماية من الحريق للمستودعات والمظلات والجمالونات.")

    c_st1, c_st2, c_st3 = st.columns(3)
    with c_st1: span_s = st.number_input("بحر الهيكل الإنشائي Span (م):", 10.0, 60.0, 24.0, 1.0, key="st_span")
    with c_st2: bays_n = st.number_input("عدد الباكيات (Bay Count):", 2, 30, 6, 1, key="st_bays")
    with c_st3: bay_w = st.number_input("المسافة بين الإطارات Bay Spacing (م):", 4.0, 12.0, 6.0, 0.5, key="st_spacing")

    eave_h = st.number_input("ارتفاع العمود Eave Height (م):", 4.0, 20.0, 7.5, 0.5, key="st_eave")

    frames_count = bays_n + 1
    col_len_total = frames_count * 2 * eave_h
    rafter_len_each = (span_s / 2) / np.cos(np.radians(10))
    rafter_len_total = frames_count * 2 * rafter_len_each
    purlin_lines = int(span_s / 1.5) * 2
    purlin_len_total = purlin_lines * (bays_n * bay_w)

    steel_items = [
        {"العنصر": "الأعمدة الرئيسية (Main Columns)", "القطاع المقترح": "UC 254x254x73 / HEB 260", "العدد": frames_count * 2, "الطول الإجمالي (م)": round(col_len_total, 1), "وزن المتر (kg/m)": 73.0},
        {"العنصر": "الكمرات الرئيسية (Main Rafters)", "القطاع المقترح": "UB 356x171x51 / IPE 360", "العدد": frames_count * 2, "الطول الإجمالي (م)": round(rafter_len_total, 1), "وزن المتر (kg/m)": 51.0},
        {"العنصر": "مدادات السقف (Z-Purlins)", "القطاع المقترح": "Z 200 x 2.0 mm", "العدد": purlin_lines, "الطول الإجمالي (م)": round(purlin_len_total, 1), "وزن المتر (kg/m)": 5.2},
        {"العنصر": "مدادات الجوانب (Side Girts)", "القطاع المقترح": "C 180 x 2.0 mm", "العدد": int(eave_h / 1.5) * 2, "الطول الإجمالي (م)": round((int(eave_h / 1.5) * 2) * (bays_n * bay_w), 1), "وزن المتر (kg/m)": 4.5},
        {"العنصر": "أربطة التقوية والشدادات (Bracing)", "القطاع المقترح": "Round Bar Dia 22mm", "العدد": bays_n * 4, "الطول الإجمالي (م)": round(bays_n * 4 * 8.5, 1), "وزن المتر (kg/m)": 3.0}
    ]

    df_steel = pd.DataFrame(steel_items)
    df_steel["الوزن الكلي (طن)"] = round((df_steel["الطول الإجمالي (م)"] * df_steel["وزن المتر (kg/m)"]) / 1000.0, 2)
    df_steel["مساحة الدهان (م²)"] = round(df_steel["الطول الإجمالي (م)"] * 1.15, 1)

    tot_steel_tons = df_steel["الوزن الكلي (طن)"].sum()
    tot_paint_m2 = df_steel["مساحة الدهان (م²)"].sum()

    m_s1, m_s2, m_s3 = st.columns(3)
    m_s1.metric("إجمالي وزن الحديد الإنشائي", f"{tot_steel_tons:,.2f} طن")
    m_s2.metric("مساحة دهان الحماية من الحريق", f"{tot_paint_m2:,.1f} م²")
    m_s3.metric("مساحة التغطية الأرضية", f"{span_s * (bays_n * bay_w):,.0f} م²")

    st.dataframe(df_steel, use_container_width=True)
    buf_steel = io.StringIO()
    df_steel.to_csv(buf_steel, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كشف حصر قطاعات وأطوال الحديد (CSV)", buf_steel.getvalue().encode('utf-8-sig'), "Steel_Structure_QTO.csv", "text/csv", key="btn_dl_steel")

# ==============================================================================
# 5. كراسة الكميات المستقلة لمشروع قائم (BOQ)
# ==============================================================================
elif "5. كراسة الكميات المستقلة" in active_app:
    st.title("📊 كراسة الكميات والمواصفات التعاقدية لمشروع مصمم مسبقاً (BOQ)")
    
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        bua_existing = st.number_input("مسطح البناء الإجمالي BUA للمشروع القائم (م²):", 100.0, 30000.0, 850.0, 50.0, key="boq_exist_bua")
    with c_b2:
        finish_spec = st.selectbox("مستوى المواصفات وجودة المواد:", ["1. تجاري معتمد (قروض الإسكان)", "2. ديلوكس عصري (Modern Deluxe)", "3. سوبر ديلوكس فندقي", "4. ألترا لوكجري VIP"], key="boq_exist_spec")

    mult = 1.0 if "تجاري" in finish_spec else (1.35 if "ديلوكس" in finish_spec else (1.75 if "سوبر" in finish_spec else 2.40))
    
    boq_records = [
        {"الكود": "01.00", "البند": "الأعمال التحضيرية وتجهيز الموقع وفحص التربة", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 55000.0},
        {"الكود": "02.00", "البند": "الحفر لزوم التأسيس وردم الدفان على طبقات مع الدمك", "الوحدة": "م³", "الكمية": round(bua_existing * 1.5, 1), "السعر (AED)": 15.0},
        {"الكود": "03.10", "البند": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات وأرضية الأرضي", "الوحدة": "م³", "الكمية": round(bua_existing * 0.28, 1), "السعر (AED)": 1200.0},
        {"الكود": "03.20", "البند": "خرسانة مسلحة بورتلاندية OPC للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": round(bua_existing * 0.38, 1), "السعر (AED)": 1250.0},
        {"الكود": "04.00", "البند": "طابوق إسمنتي عازل 20 سم ومفرغ للقواطع الداخلية", "الوحدة": "م²", "الكمية": round(bua_existing * 2.2, 1), "السعر (AED)": 110.0},
        {"الكود": "05.00", "البند": "نظام عزل الأسطح حرارياً ومائياً (كومبو فوم 7 سم مع الضمان)", "الوحدة": "م²", "الكمية": round(bua_existing * 0.45, 1), "السعر (AED)": 125.0},
        {"الكود": "06.00", "البند": "أعمال البورسلان والرخام والدرج والدهانات الداخلية والخارجية", "الوحدة": "م²", "الكمية": round(bua_existing * 1.2, 1), "السعر (AED)": round(140.0 * mult, 1)},
        {"الكود": "07.00", "البند": "أعمال الألومنيوم والزجاج المزدوج العازل واللوفرز", "الوحدة": "م²", "الكمية": round(bua_existing * 0.22, 1), "السعر (AED)": round(750.0 * mult, 1)},
        {"الكود": "08.00", "البند": "الأعمال الكهروميكانيكية والتكييف المخفي Inverter والصحي", "الوحدة": "م²", "الكمية": round(bua_existing, 1), "السعر (AED)": round(320.0 * mult, 1)}
    ]
    df_b = pd.DataFrame(boq_records)
    df_b["الإجمالي (AED)"] = round(df_b["الكمية"] * df_b["السعر (AED)"])
    tot_c = df_b["الإجمالي (AED)"].sum()

    m1, m2 = st.columns(2)
    m1.metric("إجمالي تكلفة المشروع التقديرية", f"{tot_c:,.0f} درهم إماراتي")
    m2.metric("متوسط سعر المتر المربع للبناء", f"{tot_c / bua_existing:,.1f} AED / m²")

    st.dataframe(df_b, use_container_width=True)
    buf_b = io.StringIO()
    df_b.to_csv(buf_b, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات (CSV)", buf_b.getvalue().encode('utf-8-sig'), "Project_BOQ_Existing.csv", "text/csv", key="btn_dl_boq_exist")

# ==============================================================================
# 6. محرك الجدولة الزمنية لبريمافيرا (Primavera P6)
# ==============================================================================
elif "6. محرك الجدولة الزمنية" in active_app:
    st.title("⏱️ محرك الجدولة والمسار الحرج لمشروع مصمم (Primavera P6 Engine)")
    
    cp1, cp2 = st.columns(2)
    with cp1: s_date = st.date_input("تاريخ استلام الموقع وبدء المشروع:", datetime.date.today(), key="p6_date_in")
    with cp2: pace = st.selectbox("وتيرة التنفيذ:", ["قياسي اعتيادي (Standard)", "مسار سريع (Fast-Track)"], key="p6_pace")

    p6_tasks = [
        {"ID": "ACT-1010", "WBS": "1.PRE-CON", "Name": "التراخيص البلدية وفحص التربة وشهادات NOC", "Dur": 28, "Crit": "CRITICAL"},
        {"ID": "ACT-1020", "WBS": "2.SUB-STR", "Name": "أعمال الحفر والإحلال وسند الجوانب ونزح المياه", "Dur": 21, "Crit": "CRITICAL"},
        {"ID": "ACT-1030", "WBS": "2.SUB-STR", "Name": "صبة النظافة والقواعد والرقاب المسلحة SRC", "Dur": 35, "Crit": "CRITICAL"},
        {"ID": "ACT-1040", "WBS": "2.SUB-STR", "Name": "عزل الأساسات والردم واختبار الدمك والميدات", "Dur": 25, "Crit": "CRITICAL"},
        {"ID": "ACT-1050", "WBS": "3.SUP-STR", "Name": "أعمدة وسقف الطابق الأرضي (Flat Slab)", "Dur": 35, "Crit": "CRITICAL"},
        {"ID": "ACT-1060", "WBS": "3.SUP-STR", "Name": "أعمدة وسقف الطابق الأول والمباني العظم", "Dur": 45, "Crit": "CRITICAL"},
        {"ID": "ACT-1070", "WBS": "4.MEP-WKS", "Name": "تأسيسات الكهروميكانيك والتكييف الأولية", "Dur": 45, "Crit": "NON-CRITICAL"},
        {"ID": "ACT-1080", "WBS": "5.FINISH", "Name": "نظام عزل الأسطح (كومبو 7 سم فوم)", "Dur": 20, "Crit": "CRITICAL"},
        {"ID": "ACT-1090", "WBS": "5.FINISH", "Name": "أعمال اللياسة الإسمنتية والبلاستر والتشطيبات", "Dur": 60, "Crit": "NON-CRITICAL"},
        {"ID": "ACT-1100", "WBS": "5.FINISH", "Name": "الواجهات والألومنيوم والزجاج والأسوار", "Dur": 45, "Crit": "CRITICAL"},
        {"ID": "ACT-1110", "WBS": "6.CLO-OUT", "Name": "الفحص وإطلاق التيار وشهادة الإنجاز البلدية", "Dur": 28, "Crit": "CRITICAL"}
    ]

    c_cur = pd.to_datetime(s_date)
    rows_p6 = []
    for t in p6_tasks:
        c_end = c_cur + pd.Timedelta(days=t["Dur"])
        rows_p6.append({"Activity ID": t["ID"], "WBS": t["WBS"], "المرحلة": t["Name"], "البداية": c_cur.strftime('%Y-%m-%d'), "النهاية": c_end.strftime('%Y-%m-%d'), "المدة (يوم)": t["Dur"], "المسار الحرج": t["Crit"]})
        if t["Crit"] == "CRITICAL": c_cur = c_end - pd.Timedelta(days=int(t["Dur"] * 0.20))

    df_p6 = pd.DataFrame(rows_p6)
    st.dataframe(df_p6, use_container_width=True)
    buf_p6 = io.StringIO()
    df_p6.to_csv(buf_p6, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل ملف بريمافيرا (CSV)", buf_p6.getvalue().encode('utf-8-sig'), "Primavera_P6_Import.csv", "text/csv", key="btn_dl_p6")

# ==============================================================================
# 7. المستشار الهندسي والبلدي الذكي (AI Copilot)
# ==============================================================================
else:
    st.title("🤖 المستشار الهندسي والبلدي التفاعلي المباشر (AI Copilot)")
    st.caption("نظام استشاري مباشر لمراجعة المخططات، الكود الإماراتي، ومشاكل التنفيذ بالموقع.")

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    user_query = st.chat_input("اطرح استفسارك الهندسي أو مشكلة المشروع هنا...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            reply_done = False
            # محاولة الاستدعاء عبر Gemini API
            if active_api_key:
                try:
                    client = genai.Client(api_key=active_api_key)
                    sys_prompt = f"You are a Senior UAE Civil and Structural Consulting Engineer in {emirate}. Answer technically, analytically, citing municipal codes (Dubai Building Code, Sharjah Regulations, ADIBC, ACI 318, UAE Fire Code). Provide concise, precise calculations and technical advice."
                    response = client.models.generate_content(model="gemini-2.5-flash", contents=[sys_prompt, user_query])
                    reply_text = response.text
                    reply_done = True
                except Exception as ex:
                    reply_text = ""

            # المحرك الاستشاري الاحتياطي الذاتي (Built-in Rule-Based Engine)
            if not reply_done:
                q_lower = user_query.lower()
                if "تصميم" in user_query or "فيلا" in user_query or "مخطط" in user_query:
                    reply_text = f"طبقاً لاشتراطات كود البناء في ({emirate}):\n- **الارتدادات النظامية:** أمامي {front_sb}م، خلفي {rear_sb}م، جانبي {side_sb}م.\n- **نسبة البناء القصوى:** {int(max_cov*100)}% للأرضي و {int(roof_cov*100)}% للروف.\n- **التوجيه المعماري:** عزل الجدران الخارجية بطابوق عازل حرارياً (U-value <= 0.57 W/m²K)، وتأمين مسار بهو وممر وسطي يربط المجلس بصالة المعيشة والأجنحة."
                elif "تربة" in user_query or "أساس" in user_query or "قواعد" in user_query:
                    reply_text = "في مشاريع الإمارات، إذا كان جهد التربة SBC أقل من 130 kN/m² يُوصى باعتماد لبشة مسلحة Raft، بينما إذا كان SBC >= 150 kN/m² تعتمد قواعد منفصلة مسلحة بخرسانة كبريتية SRC C40 وتربط بميدات جاسئة (Tie Beams) على منسوب 0.00 لحماية الأساسات من الهبوط المتفاوت."
                elif "حديد" in user_query or "تسليح" in user_query:
                    reply_text = "التسليح المعتمد في الدولة هو High Yield Deformed Bars رتبة Grade 500 N/mm²، مع مراعاة الغطاء الخرساني (Concrete Cover): 75 مم للعناصر الملامسة للتربة و 40 مم للأعمدة والكمرات و 25 مم للأسقف Flat Slab."
                else:
                    reply_text = f"بصفتي المستشار الهندسي المعتمد لكود ({emirate})؛ يرجى تحديد هل استفسارك يخص: الاشتراطات التخطيطية البلدية، التصميم الإنشائي وتفاصيل التسليح، متطلبات الدفاع المدني، أو حصر كراسة الكميات لتقديم المذكرة الفنية فوراً."

            st.markdown(reply_text)
            st.session_state.chat_history.append({"role": "assistant", "content": reply_text})
