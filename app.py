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
import pypdf
from google import genai
from google.genai import types

st.set_page_config(
    page_title="UAE Enterprise Engineering Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- فحص مفتاح الـ API وتأمينه -----------------
secret_key = st.secrets.get("GEMINI_API_KEY", "")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": "Admin"}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# التحقق من تسجيل الدخول
if "admin_key" in st.query_params and st.query_params["admin_key"] == "arafa_master_2026":
    st.session_state.auth = {"logged_in": True, "user": "Super Admin"}

if not st.session_state.auth["logged_in"]:
    st.title("🔒 المنظومة الهندسية الاستشارية المعتمدة - دولة الإمارات")
    c_l1, c_l2 = st.columns(2)
    with c_l1:
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.button("دخول المنظومة"):
            if u == "admin" and p == "admin@2026":
                st.session_state.auth = {"logged_in": True, "user": "Super Admin"}
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة.")
    with c_l2:
        st.info("منصة موحدة للتصميم المعماري، المخططات الإنشائية بالمحاور والأبعاد، المخططات الكهروميكانيكية، وجداول الكميات.")
    st.stop()

# ----------------- الشريط الجانبي والتحكم -----------------
st.sidebar.markdown(f"**👤 المشترك:** `{st.session_state.auth['user']}`")
c_sb1, c_sb2 = st.sidebar.columns(2)
with c_sb1:
    if st.button("🔄 تصفير الجلسة"):
        st.session_state.chat_history = []
        st.rerun()
with c_sb2:
    if st.button("🚪 خروج"):
        st.session_state.auth["logged_in"] = False
        st.rerun()

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين (ADIBC)", "دبي (Dubai Building Code)", "عجمان / الفجيرة"]
)

# معايير الارتدادات ونسب التغطية
if "أبوظبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 5.0, 3.0, 2.0, 0.50, 0.35
elif "الشارقة" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.5, 3.0, 1.5, 0.55, 0.40
elif "دبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.50, 0.35
else:
    front_sb, rear_sb, side_sb, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.55, 0.40

# حقل احتياطي للمفتاح في حال حدوث خطأ بالمفتاح المخزن
override_key = st.sidebar.text_input("مفتاح Gemini API (اختياري لتحديث المفتاح):", type="password")
active_api_key = override_key if override_key else secret_key

st.sidebar.markdown("---")
st.sidebar.subheader("📐 أبعاد القسيمة والتأسيس")
plot_w = st.sidebar.number_input("عرض واجهة القسيمة (W بالمتر):", 14.0, 250.0, 30.0, 0.5)
plot_l = st.sidebar.number_input("عمق القسيمة الداخلي (L بالمتر):", 16.0, 350.0, 50.0, 0.5)
actual_sbc = st.sidebar.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 450.0, 150.0, 10.0)

# الحسابات الهندسية الصافية
plot_area = round(plot_w * plot_l, 2)
net_w = max(0.0, plot_w - (2 * side_sb))
net_l = max(0.0, plot_l - (front_sb + rear_sb))
max_ground = round(plot_area * max_cov, 2)
effective_ground = min(round(net_w * net_l, 2), max_ground)
buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
first_floor_area = round(effective_ground * 0.90, 1)
roof_floor_area = round(effective_ground * roof_cov, 1)
total_bua = round(effective_ground + first_floor_area + roof_floor_area, 1)

# ----------------- واجهة التبويبات الرئيسية -----------------
st.title("🏛️ المنظومة الهندسية الاستشارية التنفيذية - مشاريع الإمارات")
st.caption(f"الكود المعتمد: {emirate} | مساحة القسيمة: {plot_area} م² | أقصى بناء أرضي: {effective_ground} م² | إجمالي البناء (G+1+R): {total_bua} م²")

tabs = st.tabs([
    "1. المساقط المعمارية (أرضي + أول + روف)",
    "2. المنظور المعماري الإبداعي 3D",
    "3. المخطط الإنشائي وأبعاد المحاور",
    "4. كراسة الكميات وجدول التشطيبات المعتمد",
    "5. المستشار الهندسي الذكي (AI Copilot)"
])

# ==============================================================================
# TAB 1: المساقط المعمارية التفصيلية (أرضي + أول + روف)
# ==============================================================================
with tabs[0]:
    st.subheader("المساقط المعمارية التنفيذية بالممرات والسلالم المدمجة (G + 1 + Roof)")

    col_f1, col_f2, col_f3 = st.columns(3)

    # 1. الطابق الأرضي (Ground Floor)
    with col_f1:
        st.markdown("##### 📐 مسقط الطابق الأرضي (Ground Floor)")
        fig_g, ax_g = plt.subplots(figsize=(8, 12), dpi=180)
        ax_g.set_facecolor('#FFFFFF')

        # السور والارتدادات
        ax_g.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_g.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.5, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        # ممر التوزيع الرئيسي والبهو (Corridor & Foyer)
        corridor_w = 2.4
        corridor_x = side_sb + net_w*0.48 - corridor_w/2
        ax_g.add_patch(Rectangle((corridor_x, rear_sb), corridor_w, buildable_l, facecolor='#F1F5F9', edgecolor='#94A3B8', lw=1.0))
        ax_g.text(corridor_x + corridor_w/2, rear_sb + buildable_l*0.5, "ممر التوزيع الرئيسي\nMain Corridor\n(W=2.40m)", ha='center', va='center', fontsize=7.5, weight='bold', color='#475569', rotation=90)

        # الغرف مع الفتحات
        rooms_g = [
            {"n": "مجلس رجال رسمي\nFormal Majlis\n(6.0 x 8.5m)", "x": side_sb, "y": rear_sb + buildable_l*0.60, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.40, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Hall\n(4.5 x 6.0m)", "x": side_sb, "y": rear_sb + buildable_l*0.30, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ تحضيري ورئيسي\nKitchen Suite\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#FED7AA"},
            {"n": "صالة معيشة عائلية بانورامية\nLiving Family Hall\n(7.0 x 8.5m)", "x": corridor_x + corridor_w, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح كبار السن / ضيوف\nMaster Suite (G)\n(4.5 x 5.0m)", "x": corridor_x + corridor_w, "y": rear_sb, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]

        for r in rooms_g:
            ax_g.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_g.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', alpha=0.9, lw=0.8))

        # بيت الدرج المدمج ببهو التوزيع (صعود UP)
        st_x = corridor_x - 0.5
        st_y = rear_sb + buildable_l*0.38
        st_w = 3.4
        st_h = 3.8
        ax_g.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 12):
            ax_g.plot([st_x, st_x + st_w], [sy, sy], color='#475569', lw=1.2)
        ax_g.annotate('صعود UP', xy=(st_x + st_w/2, st_y + st_h - 0.3), xytext=(st_x + st_w/2, st_y + 0.4),
                      ha='center', fontsize=8.0, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=2.0))

        # أبواب الغرف الداخلية من الممر
        door_specs = [
            (side_sb + net_w*0.22, rear_sb + buildable_l, 1.2, 180, 270), # باب المجلس
            (corridor_x + corridor_w/2, rear_sb + buildable_l, 1.4, 270, 360), # المدخل الرئيسي
            (corridor_x, rear_sb + buildable_l*0.75, 1.0, 90, 180), # باب طعام
            (corridor_x + corridor_w, rear_sb + buildable_l*0.25, 1.0, 0, 90) # باب جناح الضيوف
        ]
        for dx, dy, dr, a1, a2 in door_specs:
            ax_g.add_patch(Arc((dx, dy), dr*2, dr*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax_g.plot([dx, dx + dr], [dy, dy], color='#0F172A', lw=2.0)

        ax_g.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_g.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_g.set_aspect('equal')
        ax_g.axis('off')
        ax_g.set_title(f"الطابق الأرضي (GF: {effective_ground:.1f} م²)", fontsize=10, weight='bold')
        st.pyplot(fig_g)

    # 2. الطابق الأول (First Floor)
    with col_f2:
        st.markdown("##### 📐 مسقط الطابق الأول (First Floor)")
        fig_f, ax_f = plt.subplots(figsize=(8, 12), dpi=180)
        ax_f.set_facecolor('#FFFFFF')

        ax_f.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_f.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.5, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        # ممر التوزيع العلوي
        ax_f.add_patch(Rectangle((corridor_x, rear_sb), corridor_w, buildable_l, facecolor='#F1F5F9', edgecolor='#94A3B8', lw=1.0))
        ax_f.text(corridor_x + corridor_w/2, rear_sb + buildable_l*0.8, "موزع الأجنحة العلوية\nCorridor", ha='center', va='center', fontsize=7.5, weight='bold', color='#475569', rotation=90)

        rooms_f = [
            {"n": "جناح النوم الرئيسي الملكي\nMaster Bedroom Suite\n(6.0 x 8.5m)", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.45, "c": "#EDE9FE"},
            {"n": "دريسنج وحمام جاكوزي\nDressing & Ensuite\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb + buildable_l*0.25, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.30, "c": "#DDD6FE"},
            {"n": "جناح نوم الأبناء 1\nBedroom Suite 1\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48 - corridor_w/2, "h": buildable_l*0.25, "c": "#CCFBF1"},
            {"n": "صالة معيشة علوية + بوفيه\nLiving & Pantry\n(5.0 x 6.0m)", "x": corridor_x + corridor_w, "y": rear_sb + buildable_l*0.50, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.50, "c": "#E0F2FE"},
            {"n": "جناح نوم الأبناء 2 + 3\nBedroom Suites 2 & 3\n(5.0 x 7.0m)", "x": corridor_x + corridor_w, "y": rear_sb, "w": net_w*0.52 - corridor_w/2, "h": buildable_l*0.50, "c": "#FEF3C7"}
        ]

        for r in rooms_f:
            ax_f.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_f.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#64748B', alpha=0.9, lw=0.8))

        # بيت الدرج بالأول (هبوط DN + فتحة سقف VOID)
        ax_f.add_patch(Rectangle((st_x, st_y), st_w, st_h, facecolor='#FEF08A', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 12):
            ax_f.plot([st_x, st_x + st_w], [sy, sy], color='#B45309', lw=1.2, linestyle='--')
        ax_f.annotate('هبوط DN\n(Void Open)', xy=(st_x + st_w/2, st_y + 0.4), xytext=(st_x + st_w/2, st_y + st_h - 0.4),
                      ha='center', fontsize=8.0, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))

        # تراس وشرفة الواجهة
        ax_f.add_patch(Rectangle((side_sb, rear_sb + buildable_l), net_w*0.48 - corridor_w/2, 1.2, facecolor='#E2E8F0', edgecolor='#0F172A', lw=1.5, linestyle=':'))
        ax_f.text(side_sb + (net_w*0.48 - corridor_w/2)/2, rear_sb + buildable_l + 0.6, "شرفة Balcony", ha='center', fontsize=7.5, weight='bold')

        ax_f.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_f.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_f.set_aspect('equal')
        ax_f.axis('off')
        ax_f.set_title(f"الطابق الأول (FF: {first_floor_area:.1f} م²)", fontsize=10, weight='bold')
        st.pyplot(fig_f)

    # 3. طابق السطح والملحق (Roof Floor)
    with col_f3:
        st.markdown(f"##### 📐 طابق الروف والملحق (Roof Floor: {int(roof_cov*100)}%)")
        fig_r, ax_r = plt.subplots(figsize=(8, 12), dpi=180)
        ax_r.set_facecolor('#FFFFFF')

        ax_r.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.0, edgecolor='#0F172A', facecolor='#F8FAFC'))
        # سترة السطح المحيطة (Parapet Wall)
        ax_r.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, lw=2.0, edgecolor='#64748B', facecolor='#F1F5F9', linestyle='-'))
        ax_r.text(side_sb + net_w*0.5, rear_sb + buildable_l*0.88, "سطح مفتوح مبلط (Tiled Roof Terrace)", ha='center', fontsize=8.5, weight='bold', color='#475569')

        # كتلة ملحق الروف المصرح بها بلدياً (Roof Built-up Area)
        rf_w = net_w * 0.60
        rf_l = buildable_l * 0.45
        rf_x = side_sb + net_w*0.20
        rf_y = rear_sb + buildable_l*0.25

        ax_r.add_patch(Rectangle((rf_x, rf_y), rf_w, rf_l, lw=2.5, edgecolor='#0F172A', facecolor='#FEF3C7'))
        # تقسيمات غرف الروف
        ax_r.plot([rf_x, rf_x + rf_w], [rf_y + rf_l*0.5, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w/2, rf_y + rf_l*0.75, "صالة رياضة وترفيه / Roof Gym\n(5.0 x 6.5m)", ha='center', va='center', fontsize=8, weight='bold')
        ax_r.plot([rf_x + rf_w*0.5, rf_x + rf_w*0.5], [rf_y, rf_y + rf_l*0.5], color='#0F172A', lw=1.8)
        ax_r.text(rf_x + rf_w*0.25, rf_y + rf_l*0.25, "غرفة غسيل\nLaundry", ha='center', va='center', fontsize=7.5, weight='bold')
        ax_r.text(rf_x + rf_w*0.75, rf_y + rf_l*0.25, "غرفة خادمة + حمام\nMaid's Room", ha='center', va='center', fontsize=7.5, weight='bold')

        # خروج بيت الدرج إلى السطح (Roof Bulkhead)
        ax_r.add_patch(Rectangle((st_x, st_y), st_w, 2.4, facecolor='#CBD5E1', edgecolor='#0F172A', lw=2.0))
        ax_r.text(st_x + st_w/2, st_y + 1.2, "بيت الدرج والمصعد\nStair Core & Lift", ha='center', va='center', fontsize=8, weight='bold')

        # جلسة مظللة وبرجولا خارجية (Pergola Terrace)
        ax_r.add_patch(Rectangle((side_sb + 1.5, rear_sb + 1.5), net_w*0.4, buildable_l*0.2, facecolor='#E0F2FE', edgecolor='#0284C7', linestyle='--', lw=1.5))
        ax_r.text(side_sb + 1.5 + (net_w*0.4)/2, rear_sb + 1.5 + (buildable_l*0.2)/2, "جلسة برجولا خشبية\nRoof Pergola Area", ha='center', va='center', fontsize=7.5, weight='bold', color='#0369A1')

        ax_r.set_xlim(-plot_w * 0.08, plot_w * 1.08)
        ax_r.set_ylim(-plot_l * 0.06, plot_l * 1.12)
        ax_r.set_aspect('equal')
        ax_r.axis('off')
        ax_r.set_title(f"طابق الروف والسطح (Roof: {roof_floor_area:.1f} م²)", fontsize=10, weight='bold')
        st.pyplot(fig_r)

# ==============================================================================
# TAB 2: المنظور المعماري الإبداعي 3D
# ==============================================================================
with tabs[1]:
    st.subheader("🏛️ المنظور المعماري الإبداعي ثلاثي الأبعاد (3D Axonometric Perspective)")
    st.caption("محاكاة الكتل المعمارية للطوابق الثلاثة (الأرضي + الأول + الروف) مع البرج الأسطواني والبروزات.")

    fig_3d, ax_3d = plt.subplots(figsize=(11, 7.5), dpi=200)
    ax_3d.set_facecolor('#F0F9FF')

    cos30, sin30 = np.cos(np.radians(30)), np.sin(np.radians(30))
    def iso(x, y, z):
        return (x - y) * cos30, (x + y) * sin30 + z

    # الأرضية والشارع
    p_ground = [iso(-2, -2, 0), iso(22, -2, 0), iso(22, 20, 0), iso(-2, 20, 0)]
    ax_3d.add_patch(Polygon(p_ground, facecolor='#E2E8F0', edgecolor='#94A3B8', lw=1.5))

    # كتلة الطابق الأرضي (GF)
    bx, by, bz1 = 15, 12, 4.0
    ax_3d.add_patch(Polygon([iso(0, 0, 0), iso(bx, 0, 0), iso(bx, 0, bz1), iso(0, 0, bz1)], facecolor='#F8FAFC', edgecolor='#334155', lw=1.8))
    ax_3d.add_patch(Polygon([iso(bx, 0, 0), iso(bx, by, 0), iso(bx, by, bz1), iso(bx, 0, bz1)], facecolor='#CBD5E1', edgecolor='#334155', lw=1.8))

    # كتلة الطابق الأول مع بروز كابولي (FF with Cantilever)
    bz2 = 7.5
    ax_3d.add_patch(Polygon([iso(-0.5, -0.5, bz1), iso(bx+0.5, -0.5, bz1), iso(bx+0.5, -0.5, bz2), iso(-0.5, -0.5, bz2)], facecolor='#FFFFFF', edgecolor='#1E293B', lw=2.0))
    ax_3d.add_patch(Polygon([iso(bx+0.5, -0.5, bz1), iso(bx+0.5, by, bz1), iso(bx+0.5, by, bz2), iso(bx+0.5, -0.5, bz2)], facecolor='#94A3B8', edgecolor='#1E293B', lw=2.0))

    # كتلة ملحق الروف (Roof Floor Setback)
    bz3 = 10.5
    rx1, ry1, rx2 = 3.0, 2.0, 11.0
    ax_3d.add_patch(Polygon([iso(rx1, ry1, bz2), iso(rx2, ry1, bz2), iso(rx2, ry1, bz3), iso(rx1, ry1, bz3)], facecolor='#FEF3C7', edgecolor='#B45309', lw=1.8))
    ax_3d.add_patch(Polygon([iso(rx2, ry1, bz2), iso(rx2, by-1, bz2), iso(rx2, by-1, bz3), iso(rx2, ry1, bz3)], facecolor='#FDE68A', edgecolor='#B45309', lw=1.8))
    # سترة السطح (Roof Parapet)
    ax_3d.add_patch(Polygon([iso(-0.5, -0.5, bz2), iso(bx+0.5, -0.5, bz2), iso(bx+0.5, -0.5, bz2+0.9), iso(-0.5, -0.5, bz2+0.9)], facecolor='#334155', edgecolor='black', alpha=0.5))

    # البرج الزجاجي الأسطواني الأيقوني (Stair Tower) ممتد من الأرضي للسطح
    tx, tw, tz_top = 5.5, 3.8, 11.2
    p_tower = [iso(tx, -1.2, 0), iso(tx+tw, -1.2, 0), iso(tx+tw, -1.2, tz_top), iso(tx, -1.2, tz_top)]
    ax_3d.add_patch(Polygon(p_tower, facecolor='#38BDF8', edgecolor='#0F172A', lw=2.2, alpha=0.88))
    # تقسيمات زجاج الكورتن وول
    for zh in np.arange(1.2, tz_top, 1.2):
        p_a = iso(tx, -1.2, zh)
        p_b = iso(tx+tw, -1.2, zh)
        ax_3d.plot([p_a[0], p_b[0]], [p_a[1], p_b[1]], color='#0F172A', lw=1.5)

    # المدخل الخشبي الفاخر
    p_door = [iso(tx+tw+0.6, -0.5, 0), iso(tx+tw+2.6, -0.5, 0), iso(tx+tw+2.6, -0.5, 3.2), iso(tx+tw+0.6, -0.5, 3.2)]
    ax_3d.add_patch(Polygon(p_door, facecolor='#78350F', edgecolor='#451A03', lw=1.8))

    # النوافذ واللوفرز الخشبية
    p_win = [iso(0.5, -0.5, 1.0), iso(4.5, -0.5, 1.0), iso(4.5, -0.5, 3.2), iso(0.5, -0.5, 3.2)]
    ax_3d.add_patch(Polygon(p_win, facecolor='#7DD3FC', edgecolor='#1E293B', lw=1.8))

    # ظلال المبنى (Shadows)
    p_sh = [iso(0, 0, 0), iso(bx+4, -2.5, 0), iso(bx+by+4, by, 0), iso(bx, 0, 0)]
    ax_3d.add_patch(Polygon(p_sh, facecolor='#0F172A', alpha=0.15))

    ax_3d.set_aspect('equal')
    ax_3d.axis('off')
    ax_3d.set_title("المنظور المعماري الحجمي (3D Perspective) - فيلا G + 1 + Roof بنظام البرج الزجاجي", fontsize=11, weight='bold')
    st.pyplot(fig_3d)

# ==============================================================================
# TAB 3: المخطط الإنشائي وخطوط الأبعاد بين المحاور
# ==============================================================================
with tabs[2]:
    st.subheader("🏗️ المخطط الإنشائي التنفيذي وخطوط الأبعاد بين المحاور (Grid Dimensions)")
    st.caption("مخطط المحاور الإنشائية والقواعد والميدات موضحاً المسافات البينية بالمتر وفق متطلبات مكاتب التدقيق الإنشائي.")

    # حسابات التأسيس
    col_load_u = 1350.0
    footing_a = (col_load_u / 1.45) / actual_sbc
    footing_d = np.sqrt(footing_a)
    footing_th = max(0.50, round(footing_d * 0.25, 2))

    # تحديد إحداثيات المحاور والمسافات البينية
    gx_coords = [side_sb, side_sb + net_w*0.35, side_sb + net_w*0.70, side_sb + net_w]
    gy_coords = [rear_sb, rear_sb + buildable_l*0.35, rear_sb + buildable_l*0.70, rear_sb + buildable_l]
    x_tags = ["1", "2", "3", "4"]
    y_tags = ["A", "B", "C", "D"]

    fig_str, ax_s = plt.subplots(figsize=(10, 13), dpi=180)
    ax_s.set_facecolor('#FFFFFF')

    # رسم المحاور الإنشائية
    for idx, gx in enumerate(gx_coords):
        ax_s.plot([gx, gx], [rear_sb - 2.5, rear_sb + buildable_l + 3.0], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(gx, rear_sb + buildable_l + 3.8, x_tags[idx], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))
    for idx, gy in enumerate(gy_coords):
        ax_s.plot([side_sb - 2.5, side_sb + net_w + 3.0], [gy, gy], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(side_sb - 3.4, gy, y_tags[idx], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))

    # الميدات الرابطة الجاسئة (Tie Beams GB: 20x60 cm)
    for gx in gx_coords:
        ax_s.plot([gx, gx], [rear_sb, rear_sb + buildable_l], color='#475569', lw=3.0)
    for gy in gy_coords:
        ax_s.plot([side_sb, side_sb + net_w], [gy, gy], color='#475569', lw=3.0)

    # القواعد والأعمدة
    for gx in gx_coords:
        for gy in gy_coords:
            ax_s.add_patch(Rectangle((gx - footing_d/2, gy - footing_d/2), footing_d, footing_d, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
            ax_s.add_patch(Rectangle((gx - 0.10, gy - 0.30), 0.20, 0.60, facecolor='#0F172A', edgecolor='black', lw=1.2))

    # خطوط الأبعاد بين المحاور (X-Axis Dimension Chains)
    dim_y_pos = rear_sb + buildable_l + 1.6
    for i in range(len(gx_coords) - 1):
        x1, x2 = gx_coords[i], gx_coords[i+1]
        dist = x2 - x1
        ax_s.annotate('', xy=(x1, dim_y_pos), xytext=(x2, dim_y_pos), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_s.text((x1 + x2)/2, dim_y_pos + 0.4, f"{dist:.2f} m", ha='center', va='bottom', fontsize=8.5, weight='bold', color='black')

    # خط البعد الإجمالي الأفقي (Overall X)
    ax_s.annotate('', xy=(gx_coords[0], dim_y_pos + 1.2), xytext=(gx_coords[-1], dim_y_pos + 1.2), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.5))
    ax_s.text((gx_coords[0] + gx_coords[-1])/2, dim_y_pos + 1.5, f"Total = {net_w:.2f} m", ha='center', va='bottom', fontsize=9.0, weight='bold', color='#1E3A8A')

    # خطوط الأبعاد بين المحاور الرأسية (Y-Axis Dimension Chains)
    dim_x_pos = side_sb + net_w + 1.6
    for j in range(len(gy_coords) - 1):
        y1, y2 = gy_coords[j], gy_coords[j+1]
        dist_y = y2 - y1
        ax_s.annotate('', xy=(dim_x_pos, y1), xytext=(dim_x_pos, y2), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_s.text(dim_x_pos + 0.4, (y1 + y2)/2, f"{dist_y:.2f} m", ha='left', va='center', fontsize=8.5, weight='bold', color='black', rotation=90)

    # خط البعد الإجمالي الرأسي (Overall Y)
    ax_s.annotate('', xy=(dim_x_pos + 1.2, gy_coords[0]), xytext=(dim_x_pos + 1.2, gy_coords[-1]), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.5))
    ax_s.text(dim_x_pos + 1.6, (gy_coords[0] + gy_coords[-1])/2, f"Total = {buildable_l:.2f} m", ha='left', va='center', fontsize=9.0, weight='bold', color='#1E3A8A', rotation=90)

    ax_s.set_xlim(side_sb - 5, side_sb + net_w + 5)
    ax_s.set_ylim(rear_sb - 4, rear_sb + buildable_l + 6)
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    ax_s.set_title("المخطط الإنشائي التنفيذي: المحاور، خطوط الأبعاد البينية، القواعد المسلحة، والأعمدة", fontsize=11, weight='bold')
    st.pyplot(fig_str)

    st.markdown(f"**بيانات القاعدة المسلحة المعتمدة F1:** مساحة القاعدة = **{footing_a:.2f} م²** | الأبعاد = **{footing_d:.2f} × {footing_d:.2f} × {footing_th:.2f} م** | التسليح = **7 T 16mm / m** باتجاهين.")

# ==============================================================================
# TAB 4: كراسة الكميات وتحديد نوع التشطيب والتكلفة النهائية
# ==============================================================================
with tabs[3]:
    st.subheader("📊 كراسة حصر الكميات والمواصفات التفاعلية وحساب التكلفة الإجمالية")

    col_q1, col_q2 = st.columns(2)
    with col_q1:
        finishing_tier = st.selectbox(
            "اختر مستوى التشطيب والمواصفات المطلوبة للمشروع:",
            [
                "1. تشطيب تجاري معتمد (Standard Commercial) - اقتصادي",
                "2. ديلوكس عصري حديث (Modern Deluxe) - مواصفات المواطنين القياسية",
                "3. سوبر ديلوكس فندقي (Super Deluxe) - رخام مستورد وأطقم إيطالية",
                "4. ألترا لوكجري VIP (Ultra Luxury VIP) - قصور ورخام طبيعي وSmart Home"
            ]
        )
    with col_q2:
        calc_bua = st.number_input("مسطح البناء الإجمالي BUA المعتمد للحساب (م²):", 100.0, 30000.0, float(total_bua), 25.0)

    if "تجاري" in finishing_tier:
        rate_factor = 1.0
    elif "ديلوكس" in finishing_tier:
        rate_factor = 1.35
    elif "سوبر" in finishing_tier:
        rate_factor = 1.75
    else:
        rate_factor = 2.40

    fp_area = round(calc_bua * 0.50, 1)
    sub_conc = round(calc_bua * 0.26, 1)
    sup_conc = round(calc_bua * 0.40, 1)
    steel_tons = round(((sub_conc + sup_conc) * 115) / 1000, 1)

    boq_table = [
        {"CSI": "Div 02", "البند الهندسي والمواصفة": "الحفر العام والتسوية وسند الجوانب ونزح المياه لمنسوب التأسيس", "الوحدة": "م³", "الكمية": round(fp_area * 1.8, 1), "سعر الوحدة (AED)": 25.0},
        {"CSI": "Div 03", "البند الهندسي والمواصفة": "خرسانة عادية للنظافة Blinding PCC C20 بسمك 10 سم", "الوحدة": "م³", "الكمية": round(fp_area * 0.12, 1), "سعر الوحدة (AED)": 270.0},
        {"CSI": "Div 03", "البند الهندسي والمواصفة": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات والرقاب", "الوحدة": "م³", "الكمية": sub_conc, "سعر الوحدة (AED)": 340.0},
        {"CSI": "Div 03", "البند الهندسي والمواصفة": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": sup_conc, "سعر الوحدة (AED)": 330.0},
        {"CSI": "Div 03", "البند الهندسي والمواصفة": "حديد تسليح مشوه عالي المقاومة Grade 500 N/mm² مشتملاً القص والتشكيل", "الوحدة": "طن", "الكمية": steel_tons, "سعر الوحدة (AED)": 2750.0},
        {"CSI": "Div 04", "البند الهندسي والمواصفة": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومفرغ للقواطع", "الوحدة": "حبة", "الكمية": round(calc_bua * 4.3), "سعر الوحدة (AED)": 3.6},
        {"CSI": "Div 07", "البند الهندسي والمواصفة": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والرقاب والميدات مع ألواح الحماية", "الوحدة": "م²", "الكمية": round(fp_area * 2.3, 1), "سعر الوحدة (AED)": 45.0},
        {"CSI": "Div 07", "البند الهندسي والمواصفة": "عزل مائي وحراري متكامل للأسطح بنظام الكومبو المعتمد 25 سنة", "الوحدة": "م²", "الكمية": round(fp_area * 1.1, 1), "سعر الوحدة (AED)": round(115.0 * (1 + (rate_factor-1)*0.2), 1)},
        {"CSI": "Div 08", "البند الهندسي والمواصفة": "أعمال الألومنيوم والواجهات الزجاجية المزدوجة العازلة واللوفرز", "الوحدة": "م²", "الكمية": round(calc_bua * 0.22, 1), "سعر الوحدة (AED)": round(750.0 * rate_factor, 1)},
        {"CSI": "Div 09", "البند الهندسي والمواصفة": "لياسة إسمنتية داخلية وخارجية (طرطشة + بلاستر + زوايا وشبك)", "الوحدة": "م²", "الكمية": round(calc_bua * 6.5, 1), "سعر الوحدة (AED)": round(24.0 * (1 + (rate_factor-1)*0.3), 1)},
        {"CSI": "Div 09", "البند الهندسي والمواصفة": "أعمال الأرضيات والرخام والبورسلان والدرج الفاخر والدهانات", "الوحدة": "م²", "الكمية": round(calc_bua * 1.1, 1), "سعر الوحدة (AED)": round(160.0 * rate_factor, 1)},
        {"CSI": "Div 15", "البند الهندسي والمواصفة": "الأعمال الصحية والتغذية وخزانات GRP والأطقم والخلاطات", "الوحدة": "نقطة", "الكمية": round(calc_bua * 0.18), "سعر الوحدة (AED)": round(1200.0 * rate_factor, 1)},
        {"CSI": "Div 15", "البند الهندسي والمواصفة": "أعمال التكييف المخفي Inverter ومجاري الهواء والدكت والعوازل", "الوحدة": "TR", "الكمية": round(calc_bua / 14.5, 1), "سعر الوحدة (AED)": round(3200.0 * (1 + (rate_factor-1)*0.4), 1)},
        {"CSI": "Div 16", "البند الهندسي والمواصفة": "الأعمال الكهربائية، لوحات MDB، الإنارة LED، والتأريض والتيار الخفيف", "الوحدة": "م²", "الكمية": round(calc_bua), "سعر الوحدة (AED)": round(140.0 * rate_factor, 1)}
    ]

    df_b = pd.DataFrame(boq_table)
    df_b["الإجمالي (AED)"] = round(df_b["الكمية"] * df_b["سعر الوحدة (AED)"])
    grand_cost = df_b["الإجمالي (AED)"].sum()
    cost_per_m2 = grand_cost / calc_bua
    cost_per_sqft = cost_per_m2 / 10.764

    st.markdown("---")
    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("التكلفة الإجمالية التقديرية (عظم + تشطيب)", f"{grand_cost:,.0f} درهم إماراتي")
    cm2.metric("متوسط سعر المتر المربع (BUA)", f"{cost_per_m2:,.1f} AED / m²")
    cm3.metric("متوسط سعر القدم المربع", f"{cost_per_sqft:,.1f} AED / sq.ft")

    st.dataframe(df_b, use_container_width=True)

    csv_buf = io.StringIO()
    df_b.to_csv(csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات المسعرة الرسمية (Excel / CSV)", csv_buf.getvalue().encode('utf-8-sig'), f"BOQ_{finishing_tier.split(' ')[1]}.csv", "text/csv")

# ==============================================================================
# TAB 5: المستشار الهندسي الذكي المتجاوب (AI Copilot)
# ==============================================================================
with tabs[4]:
    st.subheader("🤖 المستشار الهندسي والبلدي الذكي (UAE AI Copilot)")
    st.caption(f"مساعد استشاري معتمد بكود {emirate} لمراجعة التسليح، المخططات، والحلول الإنشائية.")

    # عرض سجل المحادثة
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_q = st.chat_input("اطرح استفسارك الهندسي، اشتراطات البلدية، أو فحص المخطط هنا...")
    if user_q:
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)

        with st.chat_message("assistant"):
            if active_api_key:
                client = genai.Client(api_key=active_api_key)
                system_instruction = (
                    f"You are a Senior UAE Civil and Structural Consulting Engineer in {emirate}. "
                    f"Plot specs: Width={plot_w}m, Length={plot_l}m, Area={plot_area}m2, Footprint={effective_ground}m2, Total BUA={total_bua}m2, Soil SBC={actual_sbc}kN/m2. "
                    "Answer directly, technically, analytically, citing municipal codes (Dubai Building Code DBC, Sharjah Municipal Regulations, Abu Dhabi IBC, ACI 318). "
                    "Provide clear calculation verification and structural advice without fluff."
                )
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[system_instruction, user_q]
                    )
                    reply = res.text
                except Exception as e:
                    reply = f"خطأ في استدعاء الذكاء الاصطناعي: {e}. يرجى التحقق من صحة المفتاح المسجل في Secrets."
            else:
                reply = "⚠️ يرجى تزويد المنظومة بمفتاح API Key عبر إعدادات Secrets أو الشريط الجانبي لتفعيل الرد المباشر."

            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
