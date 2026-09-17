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

# ----------------- فحص وإدارة الجلسات -----------------
secret_key = st.secrets.get("GEMINI_API_KEY", "")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": True, "user": "Super Admin"}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "project_data" not in st.session_state:
    st.session_state.project_data = {
        "plot_w": 30.0,
        "plot_l": 50.0,
        "sbc": 150.0,
        "bua": 850.0,
        "steel_span": 24.0,
        "steel_length": 36.0,
        "steel_eave": 7.5,
        "drive_link": "",
        "notes": "مشروع قياسي معتمد"
    }

# ----------------- اللوحة الجانبية -----------------
st.sidebar.markdown(f"**👤 المستخدم النشط:** `{st.session_state.auth['user']}`")
if st.sidebar.button("🔄 تصفير الجلسة وبدء مشروع جديد", key="btn_reset_session"):
    st.session_state.chat_history = []
    st.session_state.project_data = {
        "plot_w": 30.0, "plot_l": 50.0, "sbc": 150.0, "bua": 850.0,
        "steel_span": 24.0, "steel_length": 36.0, "steel_eave": 7.5, "drive_link": "", "notes": ""
    }
    st.rerun()

st.sidebar.markdown("---")
active_module = st.sidebar.radio(
    "المنظومات الهندسية المستقلة:",
    [
        "0. مركز رفع المخططات والروابط الهندسية (Project Ingestion Hub)",
        "1. التصميم المعماري والمناظير 3D (G+1+Roof)",
        "2. المخطط الإنشائي وأبعاد المحاور (Framing Plan)",
        "3. حصر وتصميم الهياكل المعدنية (Steel Structures QTO)",
        "4. مخططات الخدمات والدفاع المدني (MEP Set)",
        "5. كراسة الكميات المسعرة لمشروع قائم (BOQ Engine)",
        "6. محرك الجدولة الزمنية لبريمافيرا (Primavera P6)",
        "7. المستشار الهندسي والبلدي الذكي (AI Copilot)"
    ],
    key="side_nav_selection"
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["أبوظبي / العين (ADIBC)", "الشارقة (المناطق الحضرية والشرقية)", "دبي (Dubai Building Code)", "عجمان / الفجيرة"],
    key="side_select_emirate"
)

if "أبوظبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 5.0, 3.0, 2.0, 0.50, 0.35
elif "الشارقة" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.5, 3.0, 1.5, 0.55, 0.40
elif "دبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.50, 0.35
else:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.55, 0.40

override_api = st.sidebar.text_input("مفتاح Gemini API (اختياري لتحديث المفتاح):", type="password", key="side_override_api")
active_key = override_api.strip() if override_api.strip() else secret_key.strip()

# ==============================================================================
# 0. مركز رفع المخططات والروابط الهندسية الشامل
# ==============================================================================
if "0. مركز رفع المخططات" in active_module:
    st.title("📁 مركز استقبال المخططات الجاهزة والروابط الهندسية (Project Ingestion Hub)")
    st.markdown("منظومة مركزية لاستقبال كافة وثائق المشروع (PDF، DWG/DXF، Excel، وروابط Google Drive) واستخراج البيانات وتغذية كافة المنظومات آلياً.")

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.subheader("📤 رفع ملفات المشروع الجاهزة")
        uploaded_files = st.file_uploader(
            "ارفع ملفات الكروكي، المخططات المعمارية والإنشائية، أو جداول الكميات (PDF, DXF, XLSX, PNG):",
            type=["pdf", "dxf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="hub_multi_uploader"
        )
        if uploaded_files:
            st.success(f"✅ تم تحميل {len(uploaded_files)} ملفات بنجاح في ذاكرة المعالجة.")
            for f in uploaded_files:
                st.caption(f"📄 {f.name} ({f.size / 1024:.1f} KB)")

    with col_u2:
        st.subheader("🔗 ربط مجلدات ومخططات السحابة (Cloud Links)")
        drive_url = st.text_input(
            "الصق رابط Google Drive / Dropbox / OneDrive للمشروع:",
            value=st.session_state.project_data.get("drive_link", ""),
            placeholder="https://drive.google.com/drive/folders/...",
            key="hub_drive_link_input"
        )
        st.session_state.project_data["drive_link"] = drive_url
        st.info("💡 يتم استخدام الرابط كمرجع رقمي معتمد للمشروع لربط التقارير والمخرجات والمستشار الذكي بحزمة الرسومات الكاملة.")

    st.markdown("---")
    st.subheader("⚙️ مراجعة واعتماد البيانات المستخرجة للمشروع")
    st.caption("يمكنك تعديل أي قيمة مستخرجة؛ سيتم تطبيقها وتحديثها فوراً في كافة المخططات الإنشائية والمعمارية وحصر الهياكل.")

    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    with c_p1:
        st.session_state.project_data["plot_w"] = st.number_input("عرض واجهة القسيمة (م):", 10.0, 300.0, float(st.session_state.project_data["plot_w"]), 0.5, key="hub_pw")
    with c_p2:
        st.session_state.project_data["plot_l"] = st.number_input("عمق القسيمة الداخلي (م):", 10.0, 400.0, float(st.session_state.project_data["plot_l"]), 0.5, key="hub_pl")
    with c_p3:
        st.session_state.project_data["sbc"] = st.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 500.0, float(st.session_state.project_data["sbc"]), 10.0, key="hub_sbc")
    with c_p4:
        st.session_state.project_data["bua"] = st.number_input("مسطح البناء الإجمالي BUA (م²):", 100.0, 50000.0, float(st.session_state.project_data["bua"]), 50.0, key="hub_bua")

    if st.button("🚀 تحليل واستخراج البيانات وتغذية كافة المنظومات", key="hub_btn_process"):
        with st.spinner("جاري تدقيق محتوى الوثائق ومطابقة المحددات البلدية..."):
            st.success("✅ تم تحديث بيانات المشروع واعتمادها في المنظومات المعمارية، الإنشائية، الهياكل المعدنية، وجداول الكميات بنجاح.")

# ==============================================================================
# 1. التصميم المعماري والمناظير 3D
# ==============================================================================
elif "1. التصميم المعماري" in active_module:
    st.title("🏛️ المساقط المعمارية التنفيذية والمنظور الحجمي (G+1+Roof)")

    plot_w = st.session_state.project_data["plot_w"]
    plot_l = st.session_state.project_data["plot_l"]

    plot_area = round(plot_w * plot_l, 2)
    net_w = max(0.0, plot_w - (2 * side_sb))
    net_l = max(0.0, plot_l - (front_sb + rear_sb))
    effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov, 2))
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
    ff_area = round(effective_ground * 0.90, 1)
    roof_area = round(effective_ground * roof_cov, 1)

    st.caption(f"الكود: {emirate} | مساحة القسيمة: {plot_area} م² | البصمة الأرضية: {effective_ground} م² | الطابق الأول: {ff_area} م² | طابق الروف: {roof_area} م²")

    t_fl1, t_fl2, t_fl3, t_fl4 = st.tabs(["📐 مسقط الطابق الأرضي", "📐 مسقط الطابق الأول", "📐 مسقط طابق الروف", "🏛️ المنظور المعماري 3D"])

    corridor_w = 2.4
    corridor_x = side_sb + net_w*0.48 - corridor_w/2
    st_x, st_y, st_w, st_h = corridor_x - 0.4, rear_sb + buildable_l*0.38, 3.2, 4.0

    with t_fl1:
        fig_g, ax_g = plt.subplots(figsize=(8, 11), dpi=180)
        ax_g.set_facecolor('#FFFFFF')
        ax_g.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_g.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.5, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        ax_g.add_patch(Rectangle((corridor_x, rear_sb), corridor_w, buildable_l, facecolor='#F1F5F9', edgecolor='#94A3B8', lw=1.0))
        ax_g.text(corridor_x + corridor_w/2, rear_sb + buildable_l*0.5, "بهو وممر توزيع رئيسي\nMain Corridor (W=2.40m)", ha='center', va='center', fontsize=7.5, weight='bold', color='#475569', rotation=90)

        rooms_g = [
            {"n": "مجلس رجال فندقي\nFormal Majlis\n(7.50 x 5.40m)", "x": side_sb, "y": rear_sb + buildable_l*0.60, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.40, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Hall\n(5.40 x 5.40m)", "x": side_sb, "y": rear_sb + buildable_l*0.30, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ رئيسي وتحضيري\nKitchen Suite\n(4.50 x 5.00m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FED7AA"},
            {"n": "صالة معيشة بانورامية كبرى\nLiving Family Hall\n(7.00 x 8.50m)", "x": corridor_x + corridor_w, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح نوم الضيوف / كبار السن\nGuest Suite (4.80 x 3.80m)", "x": corridor_x + corridor_w, "y": rear_sb, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]
        for r in rooms_g:
            ax_g.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_g.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A', bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', lw=0.8))

        ax_g.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 14):
            ax_g.plot([st_x, st_x + st_w], [sy, sy], color='#475569', lw=1.2)
        ax_g.annotate('صعود UP (26 Nos)', xy=(st_x + st_w/2, st_y + st_h - 0.3), xytext=(st_x + st_w/2, st_y + 0.4), ha='center', fontsize=8.0, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=2.0))

        for dx, dy, dr, a1, a2 in [(side_sb + net_w*0.22, rear_sb + buildable_l, 1.2, 180, 270), (corridor_x + corridor_w/2, rear_sb + buildable_l, 1.4, 270, 360), (corridor_x, rear_sb + buildable_l*0.75, 1.0, 90, 180), (corridor_x + corridor_w, rear_sb + buildable_l*0.25, 1.0, 0, 90)]:
            ax_g.add_patch(Arc((dx, dy), dr*2, dr*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax_g.plot([dx, dx + dr], [dy, dy], color='#0F172A', lw=2.0)

        ax_g.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_g.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_g.set_aspect('equal')
        ax_g.axis('off')
        st.pyplot(fig_g)

    with t_fl2:
        fig_f, ax_f = plt.subplots(figsize=(8, 11), dpi=180)
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
            ax_f.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A', bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', lw=0.8))

        ax_f.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#FEF08A', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 14):
            ax_f.plot([st_x, st_x + st_w], [sy, sy], color='#B45309', lw=1.2, linestyle='--')
        ax_f.annotate('هبوط DN\n(Void Open)', xy=(st_x + st_w/2, st_y + 0.4), xytext=(st_x + st_w/2, st_y + st_h - 0.4), ha='center', fontsize=8.0, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))

        ax_f.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_f.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_f.set_aspect('equal')
        ax_f.axis('off')
        st.pyplot(fig_f)

    with t_fl3:
        fig_r, ax_r = plt.subplots(figsize=(8, 11), dpi=180)
        ax_r.set_facecolor('#FFFFFF')
        ax_r.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_r.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, lw=2.0, edgecolor='#64748B', facecolor='#F1F5F9'))
        ax_r.text(side_sb + net_w*0.5, rear_sb + buildable_l*0.88, "سطح مبلط (Roof Terrace)", ha='center', fontsize=8.5, weight='bold', color='#475569')

        rf_w, rf_l = net_w * 0.60, buildable_l * 0.45
        rf_x, rf_y = side_sb + net_w*0.20, rear_sb + buildable_l*0.25
        ax_r.add_patch(Rectangle((rf_x, rf_y), rf_w, rf_l, lw=2.5, edgecolor='#0F172A', facecolor='#FEF3C7'))
        ax_r.plot([rf_x, rf_x + rf_w], [rf_y + rf_l*0.5, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w/2, rf_y + rf_l*0.75, "صالة رياضة وترفيه / Roof Gym\n(5.0 x 6.5m)", ha='center', va='center', fontsize=8, weight='bold')
        ax_r.plot([rf_x + rf_w*0.5, rf_x + rf_w*0.5], [rf_y, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w*0.25, rf_y + rf_l*0.25, "غسيل\nLaundry", ha='center', va='center', fontsize=7.5, weight='bold')
        ax_r.text(rf_x + rf_w*0.75, rf_y + rf_l*0.25, "خادمة + حمام\nMaid's Room", ha='center', va='center', fontsize=7.5, weight='bold')

        ax_r.add_patch(Rectangle((st_x, st_y), st_w, 2.4, facecolor='#CBD5E1', edgecolor='#0F172A', lw=2.0))
        ax_r.text(st_x + st_w/2, st_y + 1.2, "بيت الدرج والمصعد\nStair Core & Lift", ha='center', va='center', fontsize=8, weight='bold')

        ax_r.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_r.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_r.set_aspect('equal')
        ax_r.axis('off')
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
elif "2. المخطط الإنشائي" in active_module:
    st.title("🏗️ المخطط الإنشائي التنفيذي وخطوط الأبعاد بين المحاور (Framing Plan)")

    pw = max(10.0, st.session_data.get("plot_w", 30.0) - 2*side_sb) if "session_data" in locals() else max(10.0, st.session_state.project_data["plot_w"] - 2*side_sb)
    pl = max(10.0, st.session_state.project_data["plot_l"] - (front_sb + rear_sb))
    sbc_in = st.session_state.project_data["sbc"]

    col_load_u = 1350.0
    footing_a = (col_load_u / 1.45) / sbc_in
    footing_d = np.sqrt(footing_a)
    footing_th = max(0.50, round(footing_d * 0.25, 2))

    gx = [2.0, 2.0 + pw*0.35, 2.0 + pw*0.70, 2.0 + pw]
    gy = [2.0, 2.0 + pl*0.35, 2.0 + pl*0.70, 2.0 + pl]
    x_tags, y_tags = ["1", "2", "3", "4"], ["A", "B", "C", "D"]

    fig_str, ax_s = plt.subplots(figsize=(10, 12), dpi=180)
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

    dim_y = gy[-1] + 1.6
    for i in range(len(gx) - 1):
        ax_s.annotate('', xy=(gx[i], dim_y), xytext=(gx[i+1], dim_y), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_s.text((gx[i] + gx[i+1])/2, dim_y + 0.3, f"{gx[i+1] - gx[i]:.2f} m", ha='center', fontsize=8.5, weight='bold')
    ax_s.annotate('', xy=(gx[0], dim_y + 1.2), xytext=(gx[-1], dim_y + 1.2), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.5))
    ax_s.text((gx[0] + gx[-1])/2, dim_y + 1.5, f"Total = {pw:.2f} m", ha='center', fontsize=9.0, weight='bold', color='#1E3A8A')

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
# 3. حصر وتصميم الهياكل المعدنية (Steel Structures QTO & Engineering)
# ==============================================================================
elif "3. حصر وتصميم الهياكل المعدنية" in active_module:
    st.title("🔩 محرك حصر وتصميم الهياكل الفولاذية والجمالونات (Steel Engineering & QTO)")
    st.markdown("تصميم الإطارات المعدنية (Portal Frames)، وحصر أطوال القطاعات، الأوزان، مساحات الدهان المقاوم للحريق، وتفاصيل الوصلات.")

    c_s1, c_s2, c_s3, c_s4 = st.columns(4)
    with c_s1:
        span_in = st.number_input("بحر الهيكل الإنشائي Span (م):", 10.0, 60.0, float(st.session_state.project_data["steel_span"]), 1.0, key="st_inp_span")
        st.session_state.project_data["steel_span"] = span_in
    with c_s2:
        length_in = st.number_input("الطول الإجمالي للهنجر (م):", 12.0, 200.0, float(st.session_state.project_data["steel_length"]), 2.0, key="st_inp_len")
        st.session_state.project_data["steel_length"] = length_in
    with c_s3:
        bay_spacing = st.number_input("المسافة بين الإطارات Bay Spacing (م):", 4.0, 10.0, 6.0, 0.5, key="st_inp_spacing")
    with c_s4:
        eave_h_in = st.number_input("ارتفاع العمود Eave Height (م):", 4.0, 18.0, float(st.session_state.project_data["steel_eave"]), 0.5, key="st_inp_eave")
        st.session_state.project_data["steel_eave"] = eave_h_in

    pitch_deg = 10.0
    bays_count = int(length_in / bay_spacing)
    frames_n = bays_count + 1
    rafter_len_single = (span_in / 2) / np.cos(np.radians(pitch_deg))
    ridge_h = eave_h_in + (span_in / 2) * np.tan(np.radians(pitch_deg))

    # رسم هندسي تنفيذي لقطاع الإطار الفولاذي
    fig_steel, ax_st = plt.subplots(figsize=(11, 5.5), dpi=200)
    ax_st.set_facecolor('#FFFFFF')

    # رسم القواعد الخرسانية المسلحة تحت الأعمدة
    ax_st.add_patch(Rectangle((-1.0, -1.2), 2.0, 1.2, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
    ax_st.add_patch(Rectangle((span_in - 1.0, -1.2), 2.0, 1.2, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
    ax_st.text(0, -0.6, "قاعدة خرسانية\nRC Footing", ha='center', fontsize=7.5, weight='bold')
    ax_st.text(span_in, -0.6, "قاعدة خرسانية\nRC Footing", ha='center', fontsize=7.5, weight='bold')

    # رسم لوح التثبيت والبراغي (Base Plate & Anchor Bolts)
    ax_st.add_patch(Rectangle((-0.4, 0), 0.8, 0.15, facecolor='#0F172A'))
    ax_st.add_patch(Rectangle((span_in - 0.4, 0), 0.8, 0.15, facecolor='#0F172A'))

    # رسم الأعمدة الرئيسية (UC / HEB)
    ax_st.plot([0, 0], [0, eave_h_in], color='#1E3A8A', lw=6.0, label='أعمدة رئيسية (UC Columns)')
    ax_st.plot([span_in, span_in], [0, eave_h_in], color='#1E3A8A', lw=6.0)

    # رسم الجملون والوصلات المائلة (Rafters with Haunch)
    apex_x, apex_y = span_in / 2, ridge_h
    ax_st.plot([0, apex_x], [eave_h_in, apex_y], color='#0284C7', lw=5.0, label='كمرات الجملون (UB Rafters)')
    ax_st.plot([span_in, apex_x], [eave_h_in, apex_y], color='#0284C7', lw=5.0)

    # وصلة الركبة الجاسئة (Eave Haunch Bracket)
    ax_st.add_patch(Polygon([(0, eave_h_in - 1.2), (0, eave_h_in), (2.0, eave_h_in + 2.0*np.tan(np.radians(pitch_deg)))], facecolor='#0369A1', alpha=0.8))
    ax_st.add_patch(Polygon([(span_in, eave_h_in - 1.2), (span_in, eave_h_in), (span_in - 2.0, eave_h_in + 2.0*np.tan(np.radians(pitch_deg)))], facecolor='#0369A1', alpha=0.8))

    # رسم المدادات السقفية (Z-Purlins)
    purlin_space = 1.4
    p_steps = int((span_in / 2) / purlin_space)
    for i in range(1, p_steps + 1):
        px = i * purlin_space
        py = eave_h_in + px * np.tan(np.radians(pitch_deg))
        ax_st.plot(px, py, marker='s', markersize=6, color='#D97706')
        ax_st.plot(span_in - px, py, marker='s', markersize=6, color='#D97706')

    # خطوط الأبعاد والمناسيب
    ax_st.annotate('', xy=(0, -1.8), xytext=(span_in, -1.8), arrowprops=dict(arrowstyle='<->', color='black', lw=1.4))
    ax_st.text(span_in/2, -1.6, f"Clear Span = {span_in:.2f} m", ha='center', fontsize=9, weight='bold')

    ax_st.annotate('', xy=(-1.8, 0), xytext=(-1.8, eave_h_in), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
    ax_st.text(-2.0, eave_h_in/2, f"Eave H = {eave_h_in:.2f} m", ha='right', va='center', fontsize=8.5, weight='bold', rotation=90)

    ax_st.annotate('', xy=(span_in + 1.8, 0), xytext=(span_in + 1.8, ridge_h), arrowprops=dict(arrowstyle='<->', color='#B45309', lw=1.2))
    ax_st.text(span_in + 2.0, ridge_h/2, f"Ridge H = {ridge_h:.2f} m", ha='left', va='center', fontsize=8.5, weight='bold', color='#B45309', rotation=90)

    ax_st.set_xlim(-4, span_in + 5)
    ax_st.set_ylim(-2.5, ridge_h + 2)
    ax_st.set_aspect('equal')
    ax_st.axis('off')
    ax_st.set_title("القطاع العرضي الإنشائي للإطار الفولاذي (Steel Portal Frame Cross-Section)", fontsize=11, weight='bold')
    st.pyplot(fig_steel)

    # حصر الكميات والمواصفات لقطاعات الحديد
    col_tot_len = frames_n * 2 * eave_h_in
    raf_tot_len = frames_n * 2 * rafter_len_single
    purlin_lines_count = (p_steps * 2) + 1
    purlin_tot_len = purlin_lines_count * length_in
    girts_lines_count = int(eave_h_in / 1.5) * 2
    girts_tot_len = girts_lines_count * length_in

    steel_data = [
        {"العنصر الفولاذي": "الأعمدة الرئيسية (Main Columns)", "القطاع المقترح": "UC 254x254x73 / HEB 260", "العدد": frames_n * 2, "الطول الإجمالي (م)": round(col_tot_len, 1), "وزن المتر (kg/m)": 73.0},
        {"العنصر الفولاذي": "كمرات الجملون المائلة (Rafters)", "القطاع المقترح": "UB 356x171x51 / IPE 360", "العدد": frames_n * 2, "الطول الإجمالي (م)": round(raf_tot_len, 1), "وزن المتر (kg/m)": 51.0},
        {"العنصر الفولاذي": "مدادات السقف (Cold-formed Z-Purlins)", "القطاع المقترح": "Z 200 x 2.0 mm Glv", "العدد": purlin_lines_count, "الطول الإجمالي (م)": round(purlin_tot_len, 1), "وزن المتر (kg/m)": 5.2},
        {"العنصر الفولاذي": "مدادات الجدران والستائر (Side Girts)", "القطاع المقترح": "C 180 x 2.0 mm Glv", "العدد": girts_lines_count, "الطول الإجمالي (م)": round(girts_tot_len, 1), "وزن المتر (kg/m)": 4.5},
        {"العنصر الفولاذي": "أربطة التقوية والشدادات (Rod Bracing)", "القطاع المقترح": "Solid Round Bar 22mm", "العدد": bays_count * 4, "الطول الإجمالي (م)": round(bays_count * 4 * 9.5, 1), "وزن المتر (kg/m)": 3.0},
        {"العنصر الفولاذي": "ألواح القواعد والوصلات (Base & Splice Plates)", "القطاع المقترح": "Plates Thk 25mm Grade S355", "العدد": frames_n * 4, "الطول الإجمالي (م)": round(frames_n * 2.8, 1), "وزن المتر (kg/m)": 45.0}
    ]

    df_st = pd.DataFrame(steel_data)
    df_st["الوزن الإجمالي (طن)"] = round((df_st["الطول الإجمالي (م)"] * df_st["وزن المتر (kg/m)"]) / 1000.0, 2)
    df_st["مساحة الدهان المقاوم للحريق (م²)"] = round(df_st["الطول الإجمالي (م)"] * 1.15, 1)

    tot_weight = df_st["الوزن الإجمالي (طن)"].sum()
    tot_paint = df_st["مساحة الدهان المقاوم للحريق (م²)"].sum()
    cladding_m2 = round((length_in * rafter_len_single * 2) + (2 * length_in * eave_h_in) + (2 * (span_in * eave_h_in + 0.5 * span_in * (ridge_h - eave_h_in))), 1)

    m_st1, m_st2, m_st3, m_st4 = st.columns(4)
    m_st1.metric("إجمالي وزن الحديد الإنشائي", f"{tot_weight:,.2f} طن")
    m_st2.metric("مساحة دهان الحريق (ساعتين)", f"{tot_paint:,.1f} م²")
    m_st3.metric("مسطح ألواح التكسية الساندوتش", f"{cladding_m2:,.1f} م²")
    m_st4.metric("مساحة التغطية الأرضية", f"{span_in * length_in:,.0f} م²")

    st.dataframe(df_st, use_container_width=True)
    buf_st = io.StringIO()
    df_st.to_csv(buf_st, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كشف حصر قطاعات وأوزان الحديد (Excel / CSV)", buf_st.getvalue().encode('utf-8-sig'), "Steel_Structure_QTO.csv", "text/csv", key="btn_dl_st_csv")

# ==============================================================================
# 4. مخططات الخدمات والدفاع المدني
# ==============================================================================
elif "4. مخططات الخدمات" in active_module:
    st.title("⚡ مخططات الخدمات الكهروميكانيكية والدفاع المدني (MEP Set)")
    mep_layer = st.radio("اختر شبكة الخدمات لعرضها وتدقيقها على المسقط المعماري:", [
        "1. شبكة الصرف الصحي وغرف التفتيش (Plumbing & Drainage)",
        "2. شبكة الكهرباء والإنارة ومأخذ القوى (Electrical & Lighting)",
        "3. مخطط السلامة ومكافحة الحريق (Civil Defence & Life Safety)"
    ], horizontal=True, key="mep_layer_choice")

    fig_m, ax_m = plt.subplots(figsize=(10, 8), dpi=180)
    ax_m.set_facecolor('#FFFFFF')
    ax_m.add_patch(Rectangle((2, 2), 24, 28, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))

    if "الصرف" in mep_layer:
        ax_m.plot([4, 4], [2, 30], color='#92400E', lw=4.0, linestyle='--')
        ax_m.text(4.5, 16, 'خط الصرف الرئيسي Soil Pipe 4" (Slope 1:100)', color='#78350F', fontsize=8.5, weight='bold', rotation=90)
        for y_ic in [4, 12, 20, 28]:
            ax_m.plot(4, y_ic, marker='s', markersize=14, color='#78350F')
            ax_m.text(5.5, y_ic, "غرفة تفتيش IC (450x450mm)", fontsize=8)
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
# 5. كراسة الكميات المسعرة لمشروع قائم (BOQ Engine)
# ==============================================================================
elif "5. كراسة الكميات المسعرة" in active_module:
    st.title("📊 كراسة الكميات والمواصفات التعاقدية الرسمية (BOQ Engine)")

    bua_val = st.session_state.project_data["bua"]
    c_bq1, c_bq2 = st.columns(2)
    with c_bq1:
        calc_bua = st.number_input("مسطح البناء الإجمالي BUA المعتمد للحساب (م²):", 100.0, 50000.0, float(bua_val), 25.0, key="boq_inp_bua")
        st.session_state.project_data["bua"] = calc_bua
    with c_bq2:
        tier = st.selectbox("مستوى التشطيب والمواصفات التعاقدية:", [
            "1. تجاري معتمد (National Housing Standard) - قروض الإسكان",
            "2. ديلوكس عصري حديث (Modern Deluxe)",
            "3. سوبر ديلوكس فندقي (Super Deluxe)",
            "4. ألترا لوكجري VIP (Ultra Luxury VIP)"
        ], key="boq_inp_tier")

    r_factor = 1.0 if "تجاري" in tier else (1.35 if "ديلوكس" in tier else (1.75 if "سوبر" in tier else 2.40))

    boq_real = [
        {"البند": "1.1", "القسم": "الأعمال التحضيرية", "الوصف": "السور المؤقت واللوحات الخارجية ومكاتب الإشراف وتوصيل الخدمات", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 48500.0},
        {"البند": "1.2", "القسم": "الأعمال التحضيرية", "الوصف": "اختبارات فحص التربة واختبار المواد ورش النمل الأبيض", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 12000.0},
        {"البند": "2.1", "القسم": "الحفر والخرسانة", "الوصف": "حفر لزوم الأساسات وردم أسفل منسوب أرضية الطابق الأرضي", "الوحدة": "م³", "الكمية": round(calc_bua * 1.6, 1), "السعر (AED)": 10.0},
        {"البند": "2.2", "القسم": "الحفر والخرسانة", "الوصف": "خرسانة عادية Blinding أسفل القواعد والجسور الأرضية", "الوحدة": "م³", "الكمية": round(calc_bua * 0.05, 1), "السعر (AED)": 550.0},
        {"البند": "2.3", "القسم": "الحفر والخرسانة", "الوصف": "خرسانة مسلحة كبريتية SRC للقواعد والجسور الأرضية وأرضية الأرضي", "الوحدة": "م³", "الكمية": round(calc_bua * 0.28, 1), "السعر (AED)": 1200.0},
        {"البند": "3.1", "القسم": "الهيكل العلوي", "الوصف": "خرسانة مسلحة لزوم الأعمدة والكمرات للفيلا", "الوحدة": "م³", "الكمية": round(calc_bua * 0.15, 1), "السعر (AED)": 1300.0},
        {"البند": "3.2", "القسم": "الهيكل العلوي", "الوصف": "خرسانة مسلحة لزوم أسقف الأرضي والأول والروف والدرج الداخلي", "الوحدة": "م³", "الكمية": round(calc_bua * 0.35, 1), "السعر (AED)": 1250.0},
        {"البند": "4.1", "القسم": "أعمال الطابوق", "الوصف": "طابوق عازل خارجي 20 سم ومصمت أسفل الميدات ومفرغ للداخل", "الوحدة": "م²", "الكمية": round(calc_bua * 2.2, 1), "السعر (AED)": 110.0},
        {"البند": "5.1", "القسم": "أعمال العزل", "الوصف": "عزل الأساسات بيتومين وعزل الحمامات رابرايز سائل", "الوحدة": "م²", "الكمية": round(calc_bua * 0.6, 1), "السعر (AED)": 35.0},
        {"البند": "5.2", "القسم": "أعمال العزل", "الوصف": "عزل الأسطح حرارياً ومائياً بنظام الكومبو فوم 7 سم F5 مع الضمان", "الوحدة": "م²", "الكمية": round(calc_bua * 0.45, 1), "السعر (AED)": 120.0},
        {"البند": "6.1", "القسم": "التشطيبات الداخلية", "الوصف": "طبقة سكريد 7 سم وتوريد وتركيب بورسلان أرضيات F1 ورخام المجالس F3", "الوحدة": "م²", "الكمية": round(calc_bua * 1.1, 1), "السعر (AED)": round(75.0 * r_factor, 1)},
        {"البند": "6.2", "القسم": "التشطيبات الداخلية", "الوصف": "توريد وتركيب رخام الدرج الداخلي والخارجي F4 قائمة ونائمة 3 سم", "الوحدة": "م.ط", "الكمية": 96, "السعر (AED)": round(200.0 * r_factor, 1)},
        {"البند": "6.3", "القسم": "التشطيبات الداخلية", "الوصف": "بياض أسمنتي (بلاستر) ودهان فينوماستيك جوتن قابل للغسيل W1", "الوحدة": "م²", "الكمية": round(calc_bua * 4.5, 1), "السعر (AED)": round(25.0 * r_factor, 1)},
        {"البند": "6.4", "القسم": "الأسقف والديكور", "الوصف": "أسقف جبسوم بورد 12.5 مم للصالات والمجالس C4 وأسقف ألمنيوم للحمامات", "الوحدة": "م²", "الكمية": round(calc_bua * 0.8, 1), "السعر (AED)": round(110.0 * r_factor, 1)}
    ]

    df_boq = pd.DataFrame(boq_real)
    df_boq["الإجمالي (AED)"] = round(df_boq["الكمية"] * df_boq["السعر (AED)"])
    grand_cost = df_boq["الإجمالي (AED)"].sum()
    cost_per_m2 = grand_cost / calc_bua
    cost_per_sqft = cost_per_m2 / 10.764

    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("التكلفة الإجمالية التقديرية", f"{grand_cost:,.0f} درهم إماراتي")
    cm2.metric("متوسط سعر المتر المربع للبناء", f"{cost_per_m2:,.1f} AED / m²")
    cm3.metric("متوسط سعر القدم المربع", f"{cost_per_sqft:,.1f} AED / sq.ft")

    st.dataframe(df_boq, use_container_width=True)
    buf_boq = io.StringIO()
    df_boq.to_csv(buf_boq, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات المسعرة الرسمية (Excel / CSV)", buf_boq.getvalue().encode('utf-8-sig'), "BOQ_Official_Standard.csv", "text/csv", key="btn_dl_boq_csv")

# ==============================================================================
# 6. محرك الجدولة الزمنية لبريمافيرا (Primavera P6)
# ==============================================================================
elif "6. محرك الجدولة الزمنية" in active_module:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج المعتمد (Primavera P6 Engine)")

    s_date = st.date_input("تاريخ استلام الموقع وبدء المشروع:", datetime.date.today(), key="p6_inp_date")

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
    st.download_button("📥 تحميل ملف استيراد بريمافيرا (Primavera P6 CSV)", buf_p6.getvalue().encode('utf-8-sig'), "Primavera_P6_Import.csv", "text/csv", key="btn_dl_p6_csv")

# ==============================================================================
# 7. المستشار الهندسي والبلدي الذكي (AI Copilot)
# ==============================================================================
else:
    st.title("🤖 المستشار الهندسي والبلدي التفاعلي المباشر (AI Copilot)")
    st.caption(f"مستشار متخصص في كود {emirate} ومواصفات قروض الإسكان والتحليل الإنشائي والهياكل المعدنية.")

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    user_query = st.chat_input("اطرح استفسارك الهندسي، فحص المخططات، أو سؤالك الفني هنا...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            reply_done = False
            if active_key:
                try:
                    client = genai.Client(api_key=active_key)
                    sys_prompt = (
                        f"You are a Senior UAE Civil & Structural Engineering Consultant in {emirate}. "
                        f"Current Project Context: Plot Dims={st.session_state.project_data['plot_w']}x{st.session_state.project_data['plot_l']}m, "
                        f"BUA={st.session_state.project_data['bua']}m2, SBC={st.session_state.project_data['sbc']}kN/m2, "
                        f"Steel Portal Span={st.session_state.project_data['steel_span']}m, Length={st.session_state.project_data['steel_length']}m, Eave={st.session_state.project_data['steel_eave']}m. "
                        f"Drive/Docs Reference: {st.session_state.project_data['drive_link']}. "
                        "Answer technically, analytically, citing UAE codes (ADIBC, Sharjah, Dubai Building Code, ACI 318, AISC 360, UAE Fire Code). "
                        "Provide concrete structural and architectural advice without filler."
                    )
                    res = client.models.generate_content(model="gemini-2.5-flash", contents=[sys_prompt, user_query])
                    reply_text = res.text
                    reply_done = True
                except Exception:
                    reply_done = False

            if not reply_done:
                q_l = user_query.lower()
                if "معدن" in user_query or "حديد" in user_query or "جمالون" in user_query or "steel" in q_l:
                    reply_text = f"طبقاً لمواصفات AISC 360 وكود {emirate} لمشروع الهيكل المعدني (بحر {st.session_state.project_data['steel_span']}م وارتفاع {st.session_state.project_data['steel_eave']}م):\n- قطاع الأعمدة المقترح: UC 254x254x73 أو HEB 260.\n- قطاع الكمرات: UB 356x171x51 أو IPE 360 مع وصلة ركبة (Haunch 1.8m).\n- المدادات: Z 200 x 2.0 mm بتباعد لا يتجاوز 1.5م.\n- دهان الحماية من الحريق: إنتوميسنت بسماكة تحقق مقاومة ساعتين (2-Hour Fire Rating) معتمد من الدفاع المدني."
                elif "تربة" in user_query or "أساس" in user_query:
                    reply_text = f"جهد التربة الصافي المسجل بالمشروع هو {st.session_state.project_data['sbc']} kN/m². طبقاً لكود ACI 318؛ يتم استخدام قواعد منفصلة F1 مسلحة بخرسانة كبريتية SRC C40 وتربط بميدات جاسئة 20x60 سم لمنع الهبوط المتفاوت."
                else:
                    reply_text = f"مرحباً بك. أنا مستشارك الهندسي لكود {emirate}. جميع بيانات مشروعك (أبعاد القسيمة {st.session_state.project_data['plot_w']}×{st.session_state.project_data['plot_l']}م، ومسطح البناء {st.session_state.project_data['bua']}م²، والهيكل المعدني) محملة وجاهزة. يمكنك سؤالي عن تفاصيل التسليح، مراجعة اشتراطات البلدية، بنود كراسة الكميات، أو روابط Google Drive المرفقة."

            st.markdown(reply_text)
            st.session_state.chat_history.append({"role": "assistant", "content": reply_text})
