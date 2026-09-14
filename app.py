import streamlit as st
import pandas as pd
import json
import io
import datetime
import hashlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Circle
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(
    page_title="UAE Municipal & Engineering Comprehensive Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# استرداد المفتاح السحابي المشفر تلقائياً
api_key = st.secrets.get("GEMINI_API_KEY", "")

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ----------------- إدارة الجلسات والدخول -----------------
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": "", "role": "admin"}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# رابط التجاوز المباشر للإدارة
if "admin_key" in st.query_params and st.query_params["admin_key"] == "arafa_master_2026":
    st.session_state.auth = {"logged_in": True, "user": "Super Admin", "role": "admin"}

if not st.session_state.auth["logged_in"]:
    st.title("🔒 المنظومة الهندسية الاستشارية المعتمدة - مشاريع الإمارات")
    c1, c2 = st.columns([1, 1])
    with c1:
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.button("دخول المنظومة"):
            if u == "admin" and p == "admin@2026":
                st.session_state.auth = {"logged_in": True, "user": "Super Admin", "role": "admin"}
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة.")
    with c2:
        st.info("نظام هندسي تخصصي موحد لإصدار المخططات المعمارية للطوابق، المخططات الإنشائية، جداول الكميات التفاعلية، والجدولة الزمنية.")
    st.stop()

# ----------------- الشريط الجانبي التفاعلي -----------------
st.sidebar.markdown(f"**👤 المشترك النشط:** `{st.session_state.auth['user']}`")
col_side_btn1, col_side_btn2 = st.sidebar.columns(2)
with col_side_btn1:
    if st.button("🔄 مشروع جديد"):
        for key in list(st.session_state.keys()):
            if key not in ["auth", "chat_history"]:
                del st.session_state[key]
        st.rerun()
with col_side_btn2:
    if st.button("🚪 خروج"):
        st.session_state.auth = {"logged_in": False, "user": "", "role": ""}
        st.rerun()

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين (ADIBC)", "دبي (Dubai Building Code)", "عجمان / الفجيرة / أم القيوين"]
)

if "أبوظبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 5.0, 3.0, 2.0, 0.50
elif "الشارقة" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 4.5, 3.0, 1.5, 0.55
elif "دبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.50
else:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.55

st.sidebar.markdown("---")
st.sidebar.subheader("📐 أبعاد وبيانات القسيمة")
input_mode = st.sidebar.radio("مصدر البيانات:", ["إدخال أبعاد القسيمة يدوياً", "قراءة كروكي الأرض (PDF / صورة)"])

plot_w = st.session_state.get("plot_w", 30.0)
plot_l = st.session_state.get("plot_l", 50.0)
actual_sbc = 150.0

if input_mode == "قراءة كروكي الأرض (PDF / صورة)":
    uploaded_krooki = st.sidebar.file_uploader("رفع الكروكي (PDF/PNG/JPG):", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_krooki and api_key:
        client = genai.Client(api_key=api_key)
        f_bytes = uploaded_krooki.read()
        m_type = "application/pdf" if uploaded_krooki.name.lower().endswith(".pdf") else uploaded_krooki.type
        with st.sidebar.status("جاري مسح واستخراج أبعاد الكروكي..."):
            try:
                p_text = "Extract plot width (frontage) and length (depth) in meters as JSON: {'width': float, 'length': float}."
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Part.from_bytes(data=f_bytes, mime_type=m_type), p_text],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                dims = json.loads(res.text)
                plot_w = float(dims.get("width", 30.0))
                plot_l = float(dims.get("length", 50.0))
                st.session_state.plot_w = plot_w
                st.session_state.plot_l = plot_l
                st.sidebar.success(f"الواجهة: {plot_w}م | العمق: {plot_l}م")
            except Exception:
                st.sidebar.warning("تم اعتماد الأبعاد الافتراضية.")
else:
    plot_w = st.sidebar.number_input("عرض واجهة القسيمة (W بالمتر):", 12.0, 200.0, float(plot_w), 0.5)
    plot_l = st.sidebar.number_input("عمق القسيمة الداخلي (L بالمتر):", 15.0, 300.0, float(plot_l), 0.5)
    actual_sbc = st.sidebar.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 450.0, 150.0, 10.0)
    st.session_state.plot_w = plot_w
    st.session_state.plot_l = plot_l

# ----------------- الحسابات البلدية والتخطيطية -----------------
plot_area = round(plot_w * plot_l, 2)
net_w = max(0.0, plot_w - (2 * side_sb))
net_l = max(0.0, plot_l - (front_sb + rear_sb))
max_ground = round(plot_area * max_cov, 2)
effective_ground = min(round(net_w * net_l, 2), max_ground)
buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
total_bua = round(effective_ground * 1.85, 1)

# ----------------- الشات الذكي التفاعلي المستمر (Sidebar Copilot) -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 المستشار الهندسي الذكي")
user_query_side = st.sidebar.text_input("اطرح سؤالك الهندسي هنا:", key="side_ai_in")
if st.sidebar.button("إرسال الاستفسار") and user_query_side:
    st.session_state.chat_history.append({"role": "user", "content": user_query_side})
    if api_key:
        client = genai.Client(api_key=api_key)
        sys_context = (
            f"You are a Senior UAE Civil & Structural Engineering Consultant in {emirate}. "
            f"Plot specs: Width={plot_w}m, Length={plot_l}m, Area={plot_area}m2, Max Footprint={effective_ground}m2, Total BUA={total_bua}m2, SBC={actual_sbc}kN/m2. "
            "Answer rigorously, technically, citing UAE municipal codes (Sharjah, DBC, ADIBC, ACI 318, DEWA/SEWA). No conversational fluff."
        )
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[sys_context, user_query_side]
            )
            st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
        except Exception as ex:
            st.session_state.chat_history.append({"role": "assistant", "content": f"خطأ بالاتصال: {ex}"})
    else:
        st.session_state.chat_history.append({"role": "assistant", "content": "يرجى التحقق من حفظ GEMINI_API_KEY في Secrets."})

# ----------------- الواجهة التفاعلية الرئيسية -----------------
st.title("🏛️ المنظومة الهندسية المؤسسية المتكاملة - مشاريع الإمارات")
st.caption(f"النظام الإنشائي والمعماري والبلدي المعتمد: {emirate} | مساحة القسيمة: {plot_area:.1f} م² | البصمة الأرضية المصرحة: {effective_ground:.1f} م²")

# الأقسام التخصصية للمنظومة
main_tabs = st.tabs([
    "1. المساقط المعمارية (أرضي + أول)",
    "2. المخطط الإنشائي ومحاور الأعمدة (ETABS)",
    "3. كراسة الكميات وتحديد مستوى التشطيب (BOQ)",
    "4. المخططات الكهروميكانيكية والدفاع المدني (MEP)",
    "5. البرنامج الزمني التنفيذي (Primavera P6)",
    "6. نافذة الاستشارات الهندسية التفاعلية (AI Copilot)"
])

# ==============================================================================
# TAB 1: المساقط المعمارية التفصيلية لكل طابق (Ground + First Floor)
# ==============================================================================
with main_tabs[0]:
    st.subheader("المساقط المعمارية التنفيذية مع تفاصيل السلالم المدمجة لكل طابق")

    stair_option = st.selectbox(
        "تحديد طراز الدرج الرئيسي المدمج في المخطط:",
        [
            "1. درج حلزوني فاخر ببرج زجاجي (Helical Spiral in Glass Tower)",
            "2. درج مقوس إمبراطوري مزدوج (Double Curved Imperial Staircase)",
            "3. درج مودرن كابولي طائر (Floating Cantilevered)",
            "4. درج تقليدي قلبتين مع بسطة استراحة (U-Shaped Dog-Leg with Landing)"
        ]
    )

    col_fl1, col_fl2 = st.columns(2)

    # مسقط الطابق الأرضي (Ground Floor Plan)
    with col_fl1:
        st.markdown("#### 📐 مسقط الطابق الأرضي (Ground Floor Plan)")
        fig_gf, ax_g = plt.subplots(figsize=(10, 13), dpi=180)
        ax_g.set_facecolor('#FFFFFF')

        # الحدود والارتداد
        ax_g.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.5, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_g.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        # غرف الأرضي
        gf_rooms = [
            {"n": "مجلس رجال رسمي فندقي\nFormal Majlis\n(6.0 x 8.5m)", "x": side_sb, "y": rear_sb + buildable_l*0.60, "w": net_w*0.48, "h": buildable_l*0.40, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Room\n(4.5 x 6.0m)", "x": side_sb, "y": rear_sb + buildable_l*0.30, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ تحضيري ورئيسي\nKitchen Suite\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FED7AA"},
            {"n": "صالة معيشة بانورامية كبرى\nFamily Living Hall\n(7.0 x 8.5m)", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح كبار السن / ضيوف\nGround Master Suite\n(4.5 x 5.0m)", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]

        for r in gf_rooms:
            ax_g.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_g.add_patch(Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax_g.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=8.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.0))

        # الدرج في الطابق الأرضي (صعود UP)
        st_cx = side_sb + net_w * 0.48
        st_cy = rear_sb + buildable_l * 0.45
        if "1. درج حلزوني" in stair_option:
            ax_g.add_patch(Circle((st_cx, st_cy), 2.2, facecolor='#E0F2FE', edgecolor='#0369A1', lw=2.2))
            ax_g.add_patch(Circle((st_cx, st_cy), 0.35, facecolor='#0F172A'))
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax_g.plot([st_cx + 0.35*np.cos(rad), st_cx + 2.2*np.cos(rad)], [st_cy + 0.35*np.sin(rad), st_cy + 2.2*np.sin(rad)], color='#0369A1', lw=1.2)
            ax_g.annotate('صعود UP', xy=(st_cx + 1.4, st_cy + 1.0), xytext=(st_cx + 0.3, st_cy - 1.2),
                          ha='center', fontsize=8.0, weight='bold', color='#0369A1', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0369A1', lw=2.0))
        else:
            sw, sh = 3.6, 4.2
            ax_g.add_patch(Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF3C7', edgecolor='#B45309', lw=2.0))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax_g.plot([st_cx - sw/2 + 0.3, st_cx, st_cx + sw/2 - 0.3], [sy, sy + 0.2, sy], color='#B45309', lw=1.4)
            ax_g.annotate('صعود UP', xy=(st_cx, st_cy + sh - 0.3), xytext=(st_cx, st_cy + 0.4),
                          ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))

        # الأبواب والمداخل
        for dx, dy, r, a1, a2 in [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]:
            ax_g.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax_g.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        ax_g.annotate('المدخل الرسمي للضيوف', xy=(side_sb + net_w*0.24, rear_sb + buildable_l), xytext=(side_sb + net_w*0.24, rear_sb + buildable_l + 2.8),
                      ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))
        ax_g.annotate('المدخل العائلي الرئيسي', xy=(side_sb + net_w*0.74, rear_sb + buildable_l), xytext=(side_sb + net_w*0.74, rear_sb + buildable_l + 2.8),
                      ha='center', fontsize=8.5, weight='bold', color='#0284C7', arrowprops=dict(arrowstyle="->", color='#0284C7', lw=2.0))

        ax_g.set_xlim(-plot_w * 0.1, plot_w * 1.1)
        ax_g.set_ylim(-plot_l * 0.08, plot_l * 1.15)
        ax_g.set_aspect('equal')
        ax_g.axis('off')
        ax_g.set_title(f"مسقط الطابق الأرضي (Ground Floor) - مسطح: {effective_ground:.1f} م²", fontsize=10.5, weight='bold')
        st.pyplot(fig_gf)

    # مسقط الطابق الأول (First Floor Plan)
    with col_fl2:
        st.markdown("#### 📐 مسقط الطابق الأول (First Floor Plan)")
        fig_ff, ax_f = plt.subplots(figsize=(10, 13), dpi=180)
        ax_f.set_facecolor('#FFFFFF')

        ax_f.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=2.5, edgecolor='#0F172A', facecolor='#F8FAFC'))
        ax_f.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        # غرف الأول
        ff_rooms = [
            {"n": "جناح النوم الرئيسي الملكي\nMaster Bedroom Suite\n(6.0 x 8.5m)", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": net_w*0.48, "h": buildable_l*0.45, "c": "#EDE9FE"},
            {"n": "دريسنج وحمام جاكوزي\nDressing & Ensuite\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb + buildable_l*0.25, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#DDD6FE"},
            {"n": "جناح نوم الأبناء 1\nBedroom Suite 1\n(4.5 x 5.0m)", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.25, "c": "#CCFBF1"},
            {"n": "صالة معيشة علوية + بوفيه\nFamily Living & Pantry\n(5.0 x 6.0m)", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.50, "w": net_w*0.52, "h": buildable_l*0.50, "c": "#E0F2FE"},
            {"n": "جناح نوم الأبناء 2 + 3\nBedroom Suites 2 & 3\n(5.0 x 7.0m)", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.50, "c": "#FEF3C7"}
        ]

        for r in ff_rooms:
            ax_f.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_f.add_patch(Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax_f.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=8.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.0))

        # الدرج في الطابق الأول (هبوط DOWN + فتحة سقف VOID)
        if "1. درج حلزوني" in stair_option:
            ax_f.add_patch(Circle((st_cx, st_cy), 2.2, facecolor='#BAE6FD', edgecolor='#0284C7', lw=2.2))
            ax_f.add_patch(Circle((st_cx, st_cy), 0.35, facecolor='#0F172A'))
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax_f.plot([st_cx + 0.35*np.cos(rad), st_cx + 2.2*np.cos(rad)], [st_cy + 0.35*np.sin(rad), st_cy + 2.2*np.sin(rad)], color='#0284C7', lw=1.2, linestyle='--')
            ax_f.annotate('هبوط DN\n(Void Open)', xy=(st_cx + 0.3, st_cy - 1.2), xytext=(st_cx + 1.4, st_cy + 1.0),
                          ha='center', fontsize=8.0, weight='bold', color='#0284C7', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0284C7', lw=2.0))
        else:
            sw, sh = 3.6, 4.2
            ax_f.add_patch(Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF08A', edgecolor='#B45309', lw=2.0))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax_f.plot([st_cx - sw/2 + 0.3, st_cx, st_cx + sw/2 - 0.3], [sy, sy + 0.2, sy], color='#B45309', lw=1.4, linestyle='--')
            ax_f.annotate('هبوط DN\n(Void)', xy=(st_cx, st_cy + 0.4), xytext=(st_cx, st_cy + sh - 0.3),
                          ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))

        # تراس وشرفة الواجهة البانورامية
        ax_f.add_patch(Rectangle((side_sb, rear_sb + buildable_l), net_w*0.48, 1.2, facecolor='#E2E8F0', edgecolor='#0F172A', lw=1.5, linestyle=':'))
        ax_f.text(side_sb + net_w*0.24, rear_sb + buildable_l + 0.6, "شرفة بانورامية زجاجية Balcony", ha='center', fontsize=8, color='#1E293B', weight='bold')

        ax_f.set_xlim(-plot_w * 0.1, plot_w * 1.1)
        ax_f.set_ylim(-plot_l * 0.08, plot_l * 1.15)
        ax_f.set_aspect('equal')
        ax_f.axis('off')
        ax_f.set_title(f"مسقط الطابق الأول (First Floor) - مسطح: {effective_ground*0.85:.1f} م²", fontsize=10.5, weight='bold')
        st.pyplot(fig_ff)

# ==============================================================================
# TAB 2: المخطط الإنشائي ومحاور الأعمدة المعتمدة لـ ETABS / SAP2000
# ==============================================================================
with main_tabs[1]:
    st.subheader("🏗️ المخطط الإنشائي التنفيذي: المحاور، القواعد، والميدات (ETABS / SAP2000)")

    col_pu = st.number_input("الحمل الأقصى لأثقل عمود داخلي Ultimate Load Pu (kN):", 500.0, 4000.0, 1350.0, 50.0)
    service_p = col_pu / 1.45
    ftg_area = service_p / actual_sbc
    ftg_dim = np.sqrt(ftg_area)
    ftg_thick = max(0.50, round(ftg_dim * 0.25, 2))
    flat_slab_t = 22.0

    st.info(f"حسابات التأسيس الإنشائي: مساحة القاعدة المطلوبة = **{ftg_area:.2f} م²** | الأبعاد المقترحة = **{ftg_dim:.2f} × {ftg_dim:.2f} × {ftg_thick:.2f} م** | سماكة البلاطة اللاكمرية = **{flat_slab_t:.0f} سم**")

    grid_x = [side_sb, side_sb + net_w*0.33, side_sb + net_w*0.66, side_sb + net_w]
    grid_y = [rear_sb, rear_sb + buildable_l*0.33, rear_sb + buildable_l*0.66, rear_sb + buildable_l]
    lbl_x = ["1", "2", "3", "4"]
    lbl_y = ["A", "B", "C", "D"]

    fig_str, ax_s = plt.subplots(figsize=(10, 12), dpi=180)
    ax_s.set_facecolor('#FFFFFF')

    # رسم المحاور الإنشائية
    for i, gx in enumerate(grid_x):
        ax_s.plot([gx, gx], [rear_sb - 2.5, rear_sb + buildable_l + 2.5], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(gx, rear_sb + buildable_l + 3.2, lbl_x[i], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))
    for j, gy in enumerate(grid_y):
        ax_s.plot([side_sb - 2.5, side_sb + net_w + 2.5], [gy, gy], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(side_sb - 3.2, gy, lbl_y[j], ha='center', fontsize=10, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))

    # الميدات الرابطة الجاسئة
    for gx in grid_x:
        ax_s.plot([gx, gx], [rear_sb, rear_sb + buildable_l], color='#475569', lw=3.0)
    for gy in grid_y:
        ax_s.plot([side_sb, side_sb + net_w], [gy, gy], color='#475569', lw=3.0)

    # القواعد والأعمدة
    for gx in grid_x:
        for gy in grid_y:
            ax_s.add_patch(Rectangle((gx - ftg_dim/2, gy - ftg_dim/2), ftg_dim, ftg_dim, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
            ax_s.add_patch(Rectangle((gx - 0.10, gy - 0.30), 0.20, 0.60, facecolor='#0F172A', edgecolor='black', lw=1.2))

    ax_s.set_xlim(side_sb - 5, side_sb + net_w + 5)
    ax_s.set_ylim(rear_sb - 4, rear_sb + buildable_l + 5)
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    ax_s.set_title("مخطط القواعد والمحاور الإنشائية وتوزيع الأعمدة والميدات", fontsize=11, weight='bold')
    st.pyplot(fig_str)

    # جداول التسليح الإنشائي
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("##### 📋 جدول تسليح الأعمدة (Columns Schedule)")
        st.table(pd.DataFrame([
            {"النموذج": "C1 (أعمدة وسطية)", "الأبعاد (سم)": "20 × 60", "التسليح الرأسي": "10 T 16 mm", "الكانات": "T 8 @ 100 mm (تكثيف) / 150 mm"},
            {"النموذج": "C2 (أعمدة طرفية)", "الأبعاد (سم)": "20 × 70", "التسليح الرأسي": "12 T 16 mm", "الكانات": "T 8 @ 100 mm / 150 mm"},
            {"النموذج": "C3 (أعمدة أركان)", "الأبعاد (سم)": "20 × 80", "التسليح الرأسي": "14 T 16 mm", "الكانات": "T 10 @ 100 mm / 150 mm"}
        ]))
    with col_t2:
        st.markdown("##### 📋 جدول تسليح القواعد المنفصلة (Footings Schedule)")
        st.table(pd.DataFrame([
            {"النموذج": "F1 (قاعدة منفصلة)", "الأبعاد (م)": f"{ftg_dim:.2f} × {ftg_dim:.2f} × {ftg_thick:.2f}", "صبة النظافة": "10 سم C20", "تسليح الفرش والغطاء": "7 T 16 / m (اتجاهين)"},
            {"النموذج": "F2 (قاعدة مشتركة)", "الأبعاد (م)": "4.80 × 2.40 × 0.70", "صبة النظافة": "10 سم C20", "تسليح سفلي وعلوي": "8 T 16 / m (رقتين)"}
        ]))

# ==============================================================================
# TAB 3: كراسة الكميات وتحديد مستوى التشطيب وحساب التكلفة النهائية
# ==============================================================================
with main_tabs[2]:
    st.subheader("📊 كراسة الكميات التفاعلية مع تحديد مستوى التشطيب والسعر النهائي")

    c_b1, c_b2 = st.columns([1, 1])
    with c_b1:
        target_finish = st.selectbox(
            "اختر مستوى المواصفات وجودة التشطيب المطلوبة للمشروع:",
            [
                "1. تشطيب تجاري معتمد (Standard Commercial) - تسعير اقتصادي",
                "2. ديلوكس عصري حديث (Modern Deluxe) - متوسط ومفضل للمواطنين",
                "3. سوبر ديلوكس فندقي (Super Deluxe) - رخام إسباني وأطقم إيطالية",
                "4. ألترا لوكجري VIP (Ultra Luxury VIP) - قصور ورخام طبيعي كامل وSmart Home"
            ]
        )
    with c_b2:
        input_bua = st.number_input("مسطح البناء الإجمالي BUA المراد تسعيره (م²):", 100.0, 30000.0, float(total_bua), 25.0)

    # معاملات التسعير وفق السوق الإماراتي الحالي
    if "تجاري" in target_finish:
        f_mult = 1.0
        m2_rate_desc = "تشطيب اقتصادي قياسي مطابق لمتطلبات البلدية"
    elif "ديلوكس" in target_finish:
        f_mult = 1.35
        m2_rate_desc = "أرضيات بورسلان إسباني، ألمنيوم قطاع حراري، وديكورات جبسية"
    elif "سوبر" in target_finish:
        f_mult = 1.75
        m2_rate_desc = "رخام كريما مارفل / ستاتوريو للصالات، تكييف مخفي Inverter، وحمامات معلقة"
    else:
        f_mult = 2.40
        m2_rate_desc = "رخام طبيعي كامل، نظام منزل ذكي KNX، واجهات زجاجية Structural، ومسبح خاص"

    # بنود كراسة الكميات المفصلة
    conc_sub_v = round(input_bua * 0.26, 1)
    conc_sup_v = round(input_bua * 0.40, 1)
    steel_qty = round(((conc_sub_v + conc_sup_v) * 115) / 1000, 1)
    fp_v = round(input_bua * 0.52, 1)

    boq_records = [
        {"CSI": "Div 02", "البند والمواصفة الفنية": "أعمال الحفر العام والتسوية وسند الجوانب ونزح المياه", "الوحدة": "م³", "الكمية": round(fp_v * 1.8, 1), "سعر الوحدة (AED)": 25.0},
        {"CSI": "Div 03", "البند والمواصفة الفنية": "خرسانة نظافة عادية Blinding PCC C20 بسمك 10 سم", "الوحدة": "م³", "الكمية": round(fp_v * 0.12, 1), "سعر الوحدة (AED)": 270.0},
        {"CSI": "Div 03", "البند والمواصفة الفنية": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات والرقاب", "الوحدة": "م³", "الكمية": conc_sub_v, "سعر الوحدة (AED)": 340.0},
        {"CSI": "Div 03", "البند والمواصفة الفنية": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": conc_sup_v, "سعر الوحدة (AED)": 330.0},
        {"CSI": "Div 03", "البند والمواصفة الفنية": "حديد تسليح مشوه عالي المقاومة Grade 500 مشتملاً على القص والتشكيل", "الوحدة": "طن", "الكمية": steel_qty, "سعر الوحدة (AED)": 2750.0},
        {"CSI": "Div 04", "البند والمواصفة الفنية": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومفرغ للقواطع", "الوحدة": "حبة", "الكمية": round(input_bua * 4.3), "سعر الوحدة (AED)": 3.6},
        {"CSI": "Div 07", "البند والمواصفة الفنية": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والرقاب والميدات", "الوحدة": "م²", "الكمية": round(fp_v * 2.3, 1), "سعر الوحدة (AED)": 45.0},
        {"CSI": "Div 07", "البند والمواصفة الفنية": "عزل مائي وحراري متكامل للأسطح بنظام الكومبو المعتمد 25 سنة", "الوحدة": "م²", "الكمية": round(fp_v * 1.1, 1), "سعر الوحدة (AED)": round(115.0 * (1 + (f_mult-1)*0.2), 1)},
        {"CSI": "Div 08", "البند والمواصفة الفنية": "أعمال الألومنيوم والواجهات الزجاجية المزدوجة العازلة واللوفرز", "الوحدة": "م²", "الكمية": round(input_bua * 0.22, 1), "سعر الوحدة (AED)": round(750.0 * f_mult, 1)},
        {"CSI": "Div 09", "البند والمواصفة الفنية": "لياسة إسمنتية داخلية وخارجية (طرطشة مسمارية + بلاستر + زوايا وشبك)", "الوحدة": "م²", "الكمية": round(input_bua * 6.5, 1), "سعر الوحدة (AED)": round(24.0 * (1 + (f_mult-1)*0.3), 1)},
        {"CSI": "Div 09", "البند والمواصفة الفنية": "أعمال الأرضيات والرخام والبورسلان والدرج الفاخر والدهانات", "الوحدة": "م²", "الكمية": round(input_bua * 1.1, 1), "سعر الوحدة (AED)": round(160.0 * f_mult, 1)},
        {"CSI": "Div 15", "البند والمواصفة الفنية": "الأعمال الصحية والتغذية وخزانات GRP والأطقم والخلاطات", "الوحدة": "نقطة", "الكمية": round(input_bua * 0.18), "سعر الوحدة (AED)": round(1200.0 * f_mult, 1)},
        {"CSI": "Div 15", "البند والمواصفة الفنية": "أعمال التكييف المخفي Inverter ومجاري الهواء والدكت والعوازل", "الوحدة": "TR", "الكمية": round(input_bua / 14.5, 1), "سعر الوحدة (AED)": round(3200.0 * (1 + (f_mult-1)*0.4), 1)},
        {"CSI": "Div 16", "البند والمواصفة الفنية": "الأعمال الكهربائية، لوحات MDB، الإنارة LED، والتأريض والتيار الخفيف", "الوحدة": "م²", "الكمية": round(input_bua), "سعر الوحدة (AED)": round(140.0 * f_mult, 1)}
    ]

    df_boq = pd.DataFrame(boq_records)
    df_boq["الإجمالي (AED)"] = round(df_boq["الكمية"] * df_boq["سعر الوحدة (AED)"])
    final_total_cost = df_boq["الإجمالي (AED)"].sum()
    rate_per_m2 = final_total_cost / input_bua
    rate_per_sqft = rate_per_m2 / 10.764

    st.markdown("---")
    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.metric("التكلفة الإجمالية التقديرية للمشروع", f"{final_total_cost:,.0f} درهم إماراتي")
    m_c2.metric("متوسط سعر المتر المربع للبناء", f"{rate_per_m2:,.1f} AED / m²")
    m_c3.metric("متوسط سعر القدم المربع للبناء", f"{rate_per_sqft:,.1f} AED / sq.ft")

    st.dataframe(df_boq, use_container_width=True)

    csv_buf = io.StringIO()
    df_boq.to_csv(csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات المسعرة الرسمية (Excel / CSV)", csv_buf.getvalue().encode('utf-8-sig'), f"BOQ_{target_finish.split(' ')[1]}.csv", "text/csv")

# ==============================================================================
# TAB 4: المخططات الكهروميكانيكية والدفاع المدني
# ==============================================================================
with main_tabs[3]:
    st.subheader("⚡ المخططات التنفيذية للكهروميكانيك والدفاع المدني (MEP Set)")
    mep_type = st.selectbox("المخطط التنفيذي المطلوب:", ["المخطط الأحادي للكهرباء (Electrical SLD)", "شبكة التكييف والدكت (HVAC Ducting)", "شبكة الصرف الصحي وغرف التفتيش", "مخطط السلامة ومكافحة الحريق (Civil Defence)"])

    fig_m, ax_m = plt.subplots(figsize=(11, 7), dpi=180)
    ax_m.set_facecolor('#FFFFFF')

    if "Electrical" in mep_type:
        ax_m.plot([1, 9], [8.5, 8.5], color='black', lw=3.5)
        ax_m.text(5, 8.8, f"Main MDB: {int(total_bua*0.12*1.5)}A TP&N (ICU=36kA)", ha='center', weight='bold', color='#1E3A8A')
        for name, spec, xp in [("SMDB-GF", "100A, 30mA", 2.0), ("SMDB-FF", "100A, 30mA", 4.0), ("DB-HVAC", "160A, 100mA", 6.0), ("DB-PUMP", "63A, 30mA", 8.0)]:
            ax_m.plot([xp, xp], [8.5, 6.0], color='#1E293B', lw=2.0)
            ax_m.add_patch(Rectangle((xp - 0.7, 4.2), 1.4, 1.8, facecolor='#FEF3C7', edgecolor='#B45309', lw=1.5))
            ax_m.text(xp, 5.2, name, ha='center', weight='bold', fontsize=8.5)
            ax_m.text(xp, 4.6, spec, ha='center', fontsize=7.0)
        ax_m.set_xlim(0, 10); ax_m.set_ylim(1, 10); ax_m.axis('off')
        ax_m.set_title("Electrical Single Line Diagram (SLD) - معتمد وفق هيئات الكهرباء", fontsize=11, weight='bold')
    elif "HVAC" in mep_type:
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))
        ax_m.plot([side_sb + 2, side_sb + net_w - 2], [rear_sb + buildable_l*0.5, rear_sb + buildable_l*0.5], color='#0284C7', lw=6.0)
        ax_m.text(side_sb + net_w*0.5, rear_sb + buildable_l*0.5 + 0.5, f"Main Supply Duct (1400 CFM) | حمل التكييف: {total_bua/14.5:.1f} TR", ha='center', weight='bold', color='#0369A1')
        ax_m.set_xlim(side_sb - 1, side_sb + net_w + 1); ax_m.set_ylim(rear_sb - 1, rear_sb + buildable_l + 2); ax_m.set_aspect('equal'); ax_m.axis('off')
        ax_m.set_title("مخطط مجاري الهواء ومخارج التكييف الطولية (Linear Diffusers)", fontsize=11, weight='bold')
    else:
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))
        ax_m.plot([side_sb + 1, side_sb + 1], [rear_sb, rear_sb + buildable_l], color='#92400E', lw=4.0, linestyle='--')
        ax_m.plot(side_sb + 1, rear_sb, marker='s', markersize=14, color='#78350F')
        ax_m.text(side_sb + 2.5, rear_sb, "غرفة تفتيش رئيسية للربط بالمدينة IC-1", fontsize=8.5, weight='bold')
        ax_m.set_xlim(side_sb - 1, side_sb + net_w + 1); ax_m.set_ylim(rear_sb - 1, rear_sb + buildable_l + 2); ax_m.set_aspect('equal'); ax_m.axis('off')
        ax_m.set_title("مخطط شبكة الصرف الصحي وتصريف مياه الأمطار ومصيدة الشحوم", fontsize=11, weight='bold')
    st.pyplot(fig_m)

# ==============================================================================
# TAB 5: البرنامج الزمني التنفيذي المتوافق مع Primavera P6
# ==============================================================================
with main_tabs[4]:
    st.subheader("⏱️ البرنامج الزمني التنفيذي وحساب المسار الحرج (Primavera P6 WBS)")
    p6_start_d = st.date_input("تاريخ استلام الموقع وبدء المشروع:", datetime.date.today())

    p6_tasks = [
        {"ID": "ACT-1010", "Phase": "1. التراخيص وفحص التربة وشهادات NOC", "Days": 28, "Pred": "", "Crit": "CRITICAL"},
        {"ID": "ACT-1020", "Phase": "2. الحفر العام والإحلال وتحديد الصفر المعماري", "Days": 21, "Pred": "ACT-1010FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1030", "Phase": "3. صبة النظافة والقواعد والرقاب المسلحة SRC", "Days": 35, "Pred": "ACT-1020FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1040", "Phase": "4. عزل الأساسات والردم واختبارات الدمك", "Days": 21, "Pred": "ACT-1030FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1050", "Phase": "5. الميدات وصبة الأرضية Slab on Grade", "Days": 20, "Pred": "ACT-1040FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1060", "Phase": "6. أعمدة وسقف الطابق الأرضي Flat Slab", "Days": 35, "Pred": "ACT-1050FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1070", "Phase": "7. أعمدة وسقف الطابق الأول وأعمال المباني العظم", "Days": 45, "Pred": "ACT-1060FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1080", "Phase": "8. التمديدات الكهروميكانيكية MEP الأولية", "Days": 45, "Pred": "ACT-1060SS+15", "Crit": "NON-CRITICAL"},
        {"ID": "ACT-1090", "Phase": "9. العزل المائي والحراري للأسطح (الكومبو)", "Days": 20, "Pred": "ACT-1070FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1100", "Phase": "10. اللياسة الإسمنتية والبلاستر والتشطيبات", "Days": 60, "Pred": "ACT-1080FS", "Crit": "NON-CRITICAL"},
        {"ID": "ACT-1110", "Phase": "11. الواجهات والألومنيوم والزجاج والأسوار", "Days": 45, "Pred": "ACT-1090FS", "Crit": "CRITICAL"},
        {"ID": "ACT-1120", "Phase": "12. الفحص وإطلاق التيار وشهادة الإنجاز البلدية", "Days": 28, "Pred": "ACT-1110FS", "Crit": "CRITICAL"}
    ]

    c_s = pd.to_datetime(p6_start_d)
    rows_sched = []
    for item in p6_tasks:
        c_e = c_s + pd.Timedelta(days=item["Days"])
        rows_sched.append({
            "Activity ID": item["ID"],
            "المرحلة التنفيذية": item["Phase"],
            "البداية": c_s.strftime('%Y-%m-%d'),
            "النهاية": c_e.strftime('%Y-%m-%d'),
            "المدة (يوم)": item["Days"],
            "العلاقات السابقة": item["Pred"],
            "المسار الحرج": item["Crit"]
        })
        if item["Crit"] == "CRITICAL":
            c_s = c_e - pd.Timedelta(days=int(item["Days"] * 0.22))

    df_p6_table = pd.DataFrame(rows_sched)
    st.dataframe(df_p6_table, use_container_width=True)

    p6_csv_buf = io.StringIO()
    df_p6_table.to_csv(p6_csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل جدول بريمافيرا المعتمد بصيغة Excel / CSV", p6_csv_buf.getvalue().encode('utf-8-sig'), "Primavera_P6_Schedule.csv", "text/csv")

# ==============================================================================
# TAB 6: نافذة الاستشارات الهندسية التفاعلية المستمرة (AI Copilot)
# ==============================================================================
with main_tabs[5]:
    st.subheader("🤖 المستشار الهندسي الذكي التفاعلي (UAE Engineering Copilot)")
    st.caption("مساعد استشاري مدعوم بنموذج Gemini لمراجعة كودات البناء، حل مشاكل التسليح والتربة، والتحقق الفني.")

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    main_q = st.chat_input("اطرح استفسارك الهندسي هنا...")
    if main_q:
        st.session_state.chat_history.append({"role": "user", "content": main_q})
        with st.chat_message("user"):
            st.markdown(main_q)

        with st.chat_message("assistant"):
            if api_key:
                client = genai.Client(api_key=api_key)
                ctx = f"Senior UAE Civil/Structural Engineer in {emirate}. Plot dims: {plot_w}x{plot_l}m, BUA={total_bua}m2, Finish={target_finish}. Answer critically, technically, and reference UAE codes."
                try:
                    ans_text = client.models.generate_content(model="gemini-2.5-flash", contents=[ctx, main_q]).text
                except Exception as err:
                    ans_text = f"خطأ بالاتصال: {err}"
            else:
                ans_text = "يرجى إدخال المفتاح لتفعيل المستشار الذكي."
            st.markdown(ans_text)
            st.session_state.chat_history.append({"role": "assistant", "content": ans_text})
