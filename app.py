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
    page_title="UAE Municipal & Engineering Enterprise Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- PROMPT 01: ARCHITECTURE & AUTHENTICATION -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# استرداد المفتاح السحابي المشفر
api_key = st.secrets.get("GEMINI_API_KEY", "")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": "", "role": "", "expiry": ""}
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

# التحقق الأمني من الرابط السري المباشر للإدارة (Admin Bypass)
if "admin_key" in st.query_params and st.query_params["admin_key"] == "arafa_master_2026":
    st.session_state.auth = {"logged_in": True, "user": "Super Admin (Engineer Arafa)", "role": "admin", "expiry": "2030-01-01"}

if not st.session_state.auth["logged_in"]:
    st.title("🔒 المنظومة الهندسية والمعمارية لمشاريع الإمارات | بوابة الدخول")
    st.markdown("نظام معتمد لإدارة المخططات، الحسابات الإنشائية، الكهروميكانيكية، وكراسات الكميات.")

    col_auth1, col_auth2 = st.columns([1, 1])
    with col_auth1:
        st.subheader("تسجيل الدخول للمشتركين والشركاء")
        u_name = st.text_input("اسم المستخدم (Username):")
        u_pass = st.text_input("كلمة المرور (Password):", type="password")

        if st.button("دخول المنظومة"):
            users_db = st.secrets.get("users", {})
            auth_ok = False
            user_role = "consultant"
            u_exp = "2025-01-01"

            if u_name in users_db:
                stored_h, u_status, u_exp = users_db[u_name][0], users_db[u_name][1], users_db[u_name][2]
                if hash_password(u_pass) == stored_h and u_status == "active":
                    auth_ok = True
            elif u_name == "admin" and u_pass == "admin@2026":
                auth_ok, user_role, u_exp = True, "admin", "2030-01-01"

            if auth_ok:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                if today_str <= u_exp:
                    st.session_state.auth = {"logged_in": True, "user": u_name, "role": user_role, "expiry": u_exp}
                    st.success("تم التحقق بنجاح! جاري تحميل المنظومة...")
                    st.rerun()
                else:
                    st.error(f"انتهت صلاحية الحساب بتاريخ ({u_exp}). يرجى تجديد الاشتراك.")
            else:
                st.error("بيانات الدخول غير صحيحة أو الحساب غير مفعل.")

    with col_auth2:
        st.info("""
        ### 📋 محاور البوابة الهندسية المعتمدة:
        * **Prompt 01–03:** معمارية آمنة، إدارة وثائق ومخططات، وقراءة ذكية لملفات الكروكي (PDF/Images).
        * **Prompt 04–06:** مطابقة اشتراطات بلديات الدولة، مستشار ذكي RAG، وحصر كميات CSI MasterFormat.
        * **Prompt 07–10:** محرك حسابات إنشائية وميكانيكية، أصول CAD/BIM، وتقارير رسمية جاهزة للترخيص.
        """)
    st.stop()

# ----------------- SIDEBAR: MODULE SELECTOR -----------------
st.sidebar.markdown(f"**👤 المستخدم:** `{st.session_state.auth['user']}`")
st.sidebar.markdown(f"**📅 الترخيص حتى:** `{st.session_state.auth['expiry']}`")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.auth = {"logged_in": False, "user": "", "role": "", "expiry": ""}
    st.rerun()

st.sidebar.markdown("---")
active_module = st.sidebar.radio(
    "المنظومات والوحدات المتاحة:",
    [
        "1. المنظومة المعمارية والـ 3D والسلالم (Architectural Engine)",
        "2. محرك الحسابات الإنشائية والجيوتقنية (Structural & Geotech)",
        "3. محرك الأحمال الميكانيكية والكهربائية (MEP Sizing)",
        "4. محرك الجدولة الزمنية والمسار الحرج لمشروع مصمم (CPM / WBS)",
        "5. محرك حصر الكميات والمواصفات والتسعير (BOQ Engine)",
        "6. المستشار الهندسي الذكي لحل المشكلات (AI Engineering Copilot)"
    ]
)

# ----------------- PROMPT 04: UAE MUNICIPAL CODE MATRIX -----------------
st.sidebar.markdown("---")
emirate_selection = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين (ADIBC)", "دبي (Dubai Building Code)", "عجمان / الفجيرة"]
)

if "أبوظبي" in emirate_selection:
    front_sb, rear_sb, side_sb, max_cov = 5.0, 3.0, 2.0, 0.50
    code_title = "كود أبوظبي الدولي للبناء (ADIBC) | ارتداد أمامي 5.0م - جانبي 2.0م - تغطية 50%"
elif "الشارقة" in emirate_selection:
    front_sb, rear_sb, side_sb, max_cov = 4.5, 3.0, 1.5, 0.55
    code_title = "دليل اشتراطات بلدية الشارقة | ارتداد أمامي 4.5م - جانبي 1.5م - تغطية 55%"
elif "دبي" in emirate_selection:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.50
    code_title = "كود دبي للبناء (DBC) | ارتداد أمامي 4.0م - جانبي 1.5م - تغطية 50%"
else:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.55
    code_title = "الاشتراطات البلدية الموحدة | ارتداد أمامي 4.0م - جانبي 1.5م - تغطية 55%"

# ==============================================================================
# MODULE 1: ARCHITECTURAL ENGINE & 3D PIPELINE (Prompts 02, 03, 04, 08)
# ==============================================================================
if "1. المنظومة المعمارية" in active_module:
    st.title("🏛️ المنظومة المعمارية التنفيذية وأصول الـ 3D والسلالم")
    st.info(f"📌 **المحددات البلدية المعتمدة تلقائياً:** {code_title}")

    # PROMPT 03: PDF/Vision Document Intelligence
    in_mode = st.radio("طريقة تحديد القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع كروكي القسيمة (PDF / صورة)"], horizontal=True)

    plot_w = st.session_state.get("pw", 30.0)
    plot_l = st.session_state.get("pl", 50.0)

    if in_mode == "رفع كروكي القسيمة (PDF / صورة)":
        up_krooki = st.file_uploader("ارفع كروكي الأرض الصادر من البلدية/دائرة التخطيط (PDF/PNG/JPG):", type=["pdf", "png", "jpg", "jpeg"])
        if up_krooki and api_key:
            client = genai.Client(api_key=api_key)
            f_bytes = up_krooki.read()
            m_type = "application/pdf" if up_krooki.name.lower().endswith(".pdf") else up_krooki.type
            with st.spinner("جاري استخراج أبعاد القسيمة آلياً عبر الذكاء الاصطناعي..."):
                try:
                    p = "Extract plot width (frontage on road) and length (depth) in meters from this UAE Krooki. Return JSON: {'width': float, 'length': float}."
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[types.Part.from_bytes(data=f_bytes, mime_type=m_type), p],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    dim_data = json.loads(res.text)
                    plot_w = float(dim_data.get("width", 30.0))
                    plot_l = float(dim_data.get("length", 50.0))
                    st.session_state.pw = plot_w
                    st.session_state.pl = plot_l
                    st.success(f"تم التعرف على القسيمة: الواجهة = {plot_w} م | العمق = {plot_l} م")
                except Exception:
                    st.warning("تم اعتماد الأبعاد المعيارية الافتراضية للقسيمة.")
    else:
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            plot_w = st.number_input("عرض واجهة الأرض على الشارع (متر):", 12.0, 250.0, float(plot_w), 0.5)
            st.session_state.pw = plot_w
        with c_w2:
            plot_l = st.number_input("عمق القسيمة الداخلي (متر):", 15.0, 350.0, float(plot_l), 0.5)
            st.session_state.pl = plot_l

    # الحسابات الهندسية الصافية
    plot_area = round(plot_w * plot_l, 2)
    net_w = max(0.0, plot_w - (2 * side_sb))
    net_l = max(0.0, plot_l - (front_sb + rear_sb))
    max_ground = round(plot_area * max_cov, 2)
    effective_ground = min(round(net_w * net_l, 2), max_ground)
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("إجمالي مساحة القسيمة", f"{plot_area:.1f} م²")
    c_m2.metric("الكتلة المبنية المصرحة", f"{net_w:.1f} × {buildable_l:.1f} م")
    c_m3.metric(f"أقصى مسطح أرضي ({int(max_cov*100)}%)", f"{effective_ground:.1f} م²")
    c_m4.metric("الارتداد الأمامي المعتمد", f"{front_sb:.1f} م")

    st.markdown("---")
    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        scheme_id = st.selectbox(
            "اختر النموذج المعماري المطلوب دراسته:",
            [
                "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات دوبلكس استثمارية (Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية + ملحق خدمات خارجي (Villa + Outbuilding)"
            ]
        )
    with c_opt2:
        stair_id = st.selectbox(
            "اختر الطراز الهندسي للدرج الرئيسي (Staircase Typology):",
            [
                "1. درج حلزوني دائري مدمج ببرج زجاجي (Helical Spiral in Glass Tower)",
                "2. درج مقوس إمبراطوري ملكي (Double Curved Imperial Staircase)",
                "3. درج مودرن معلق كابولي (Floating Cantilevered)",
                "4. درج تقليدي قلبتين مع بسطة استراحة (U-Shaped Dog-Leg)"
            ]
        )

    # بناء الفراغات المعمارية ديناميكياً
    active_rooms = []
    active_doors = []
    active_entries = []

    if "المقترح 1" in scheme_id:
        bua_factor = 1.85
        active_rooms = [
            {"n": "مجلس رجال رسمي فندقي\nFormal Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Suite", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ تحضيري ورئيسي\nKitchen Suite", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "c": "#FED7AA"},
            {"n": "صالة معيشة عائلية بانورامية\nPanoramic Living Hall", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح كبار السن / ضيوف\nGround Master Suite", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]
        active_doors = [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]
        active_entries = [("مدخل الضيوف الرسمي", (side_sb + net_w*0.24, rear_sb + buildable_l + 3.0), (side_sb + net_w*0.24, rear_sb + buildable_l), "#B45309"),
                          ("المدخل العائلي الرئيسي", (side_sb + net_w*0.74, rear_sb + buildable_l + 3.0), (side_sb + net_w*0.74, rear_sb + buildable_l), "#0284C7")]
    elif "المقترح 2" in scheme_id:
        bua_factor = 1.80
        uw = net_w / 2
        active_rooms = [
            {"n": "فيلا 1: مجلس ضيوف", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#DCFCE7"},
            {"n": "فيلا 1: صالة عائلية ومطبخ", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0FDF4"},
            {"n": "فيلا 2: مجلس ضيوف", "x": side_sb + uw, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#E0F2FE"},
            {"n": "فيلا 2: صالة عائلية ومطبخ", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0F9FF"}
        ]
        active_doors = [(side_sb + uw*0.5, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + uw*1.5, rear_sb + buildable_l, 1.2, 270, 360)]
        active_entries = [("مدخل فيلا 1", (side_sb + uw*0.5, rear_sb + buildable_l + 3.0), (side_sb + uw*0.5, rear_sb + buildable_l), "#15803D"),
                          ("مدخل فيلا 2", (side_sb + uw*1.5, rear_sb + buildable_l + 3.0), (side_sb + uw*1.5, rear_sb + buildable_l), "#0284C7")]
    elif "المقترح 3" in scheme_id:
        bua_factor = 1.80
        uw = net_w / 3
        active_rooms = [{"n": f"تاون هاوس {i+1}\nمعيشة وضيافة", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.4, "w": uw, "h": buildable_l*0.6, "c": "#FEF9C3"} for i in range(3)] + \
                       [{"n": f"تاون هاوس {i+1}\nمطبخ وحديقة", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.4, "c": "#FEF08A"} for i in range(3)]
        active_doors = [(side_sb + (i+0.5)*uw, rear_sb + buildable_l, 1.1, 180, 270) for i in range(3)]
        active_entries = [(f"مدخل TH {i+1}", (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.0), (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "#CA8A04") for i in range(3)]
    elif "المقترح 4" in scheme_id:
        bua_factor = 1.75
        uw = net_w / 4
        active_rooms = [{"n": f"دوبلكس {i+1}\nاستقبال ومعيشة", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.45, "w": uw, "h": buildable_l*0.55, "c": "#FEE2E2"} for i in range(4)] + \
                       [{"n": f"دوبلكس {i+1}\nمطبخ وخدمات", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.45, "c": "#FFEDD5"} for i in range(4)]
        active_doors = [(side_sb + (i+0.5)*uw, rear_sb + buildable_l, 1.0, 180, 270) for i in range(4)]
        active_entries = [(f"مدخل دوبلكس {i+1}", (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.0), (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "#DC2626") for i in range(4)]
    else:
        bua_factor = 1.90
        active_rooms = [
            {"n": "الفيلا الرئيسية (سكن العائلة)\nMain Residence (G+1)", "x": side_sb, "y": rear_sb, "w": net_w, "h": buildable_l*0.70, "c": "#EEF2FF"},
            {"n": "ملحق الخدمات ومجلس الضيوف\nMajlis & Services Block", "x": side_sb, "y": rear_sb + buildable_l*0.78, "w": net_w*0.75, "h": buildable_l*0.22, "c": "#F3E8FF"}
        ]
        active_doors = [(side_sb + net_w*0.37, rear_sb + buildable_l, 1.3, 180, 270), (side_sb + net_w*0.5, rear_sb + buildable_l*0.70, 1.3, 270, 360)]
        active_entries = [("مدخل المجلس الخارجي", (side_sb + net_w*0.37, rear_sb + buildable_l + 3.0), (side_sb + net_w*0.37, rear_sb + buildable_l), "#7E22CE"),
                          ("مدخل الفيلا العائلية", (side_sb + net_w*0.85, rear_sb + buildable_l*0.70 + 2.2), (side_sb + net_w*0.85, rear_sb + buildable_l*0.70), "#4338CA")]

    calc_total_bua = round(effective_ground * bua_factor, 2)

    tab_render, tab_cad = st.tabs(["📐 المسقط المعماري والسلالم المحددة", "📦 تصدير الأصول الهندسية (AutoCAD / 3ds Max / PS)"])

    with tab_render:
        fig_plan, ax = plt.subplots(figsize=(11, 14), dpi=200)
        ax.set_facecolor('#F8FAFC')
        ax.add_patch(patches.Rectangle((0, 0), plot_w, plot_l, lw=3.5, edgecolor='#0F172A', facecolor='#FFFFFF'))
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, lw=2.0, edgecolor='#EF4444', linestyle='--', facecolor='none'))

        # رسم الغرف المزدوجة الجدران
        for r in active_rooms:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.2, edgecolor='#1E293B', facecolor=r["c"], alpha=0.9))
            ax.add_patch(patches.Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.0, weight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

        # تمثيل الدرج الإبداعي المختار
        st_cx = side_sb + net_w * 0.48
        st_cy = rear_sb + buildable_l * 0.45

        if "1. درج حلزوني" in stair_id:
            r_tower = 2.4
            ax.add_patch(Circle((st_cx, st_cy), r_tower, facecolor='#E0F2FE', edgecolor='#0369A1', lw=2.5))
            ax.add_patch(Circle((st_cx, st_cy), 0.4, facecolor='#0F172A'))
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax.plot([st_cx + 0.4*np.cos(rad), st_cx + r_tower*np.cos(rad)], [st_cy + 0.4*np.sin(rad), st_cy + r_tower*np.sin(rad)], color='#0369A1', lw=1.4)
            ax.annotate('صعود حلزوني UP', xy=(st_cx + 1.6, st_cy + 1.2), xytext=(st_cx + 0.4, st_cy - 1.5),
                        ha='center', fontsize=8.5, weight='bold', color='#0369A1', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0369A1', lw=2.2))
        elif "2. درج مقوس إمبراطوري" in stair_id:
            sw, sh = 4.2, 4.0
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF3C7', edgecolor='#B45309', lw=2.2))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax.plot([st_cx - sw/2 + 0.4, st_cx, st_cx + sw/2 - 0.4], [sy, sy + 0.25, sy], color='#B45309', lw=1.6)
            ax.annotate('صعود ملكي UP', xy=(st_cx, st_cy + sh - 0.3), xytext=(st_cx, st_cy + 0.4),
                        ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.2))
        elif "3. درج مودرن معلق" in stair_id:
            sw, sh = 2.4, 4.5
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#F1F5F9', edgecolor='#475569', lw=1.8))
            ax.plot([st_cx - sw/2, st_cx - sw/2], [st_cy, st_cy + sh], color='#0F172A', lw=4.5)
            for sy in np.linspace(st_cy + 0.2, st_cy + sh - 0.2, 13):
                ax.add_patch(patches.Rectangle((st_cx - sw/2, sy), sw*0.9, 0.2, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.2))
            ax.annotate('صعود UP', xy=(st_cx, st_cy + sh - 0.4), xytext=(st_cx, st_cy + 0.4),
                        ha='center', fontsize=8.5, weight='bold', color='#1E293B', arrowprops=dict(arrowstyle="->", color='#1E293B', lw=2.0))
        else:
            sw, sh = 3.2, 4.2
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
            ax.plot([st_cx, st_cx], [st_cy, st_cy + sh*0.65], color='#0F172A', lw=2.0)
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy + sh*0.65), sw, sh*0.35, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.5))
            for sy in np.linspace(st_cy, st_cy + sh*0.65, 8):
                ax.plot([st_cx - sw/2, st_cx], [sy, sy], color='#475569', lw=1.4)
                ax.plot([st_cx, st_cx + sw/2], [sy, sy], color='#475569', lw=1.4, linestyle='--')
            ax.annotate('صعود UP', xy=(st_cx - 0.8, st_cy + sh*0.5), xytext=(st_cx - 0.8, st_cy + 0.3),
                        ha='center', fontsize=8.0, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.8))

        # الأبواب والمداخل
        for dx, dy, r, a1, a2 in active_doors:
            ax.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        for title_e, p1, p2, col_e in active_entries:
            arrow = FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=18, color=col_e, lw=2.6)
            ax.add_patch(arrow)
            ax.text(p1[0], p1[1] + 0.6, title_e, ha='center', va='bottom', fontsize=8.5, weight='bold', color=col_e,
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=col_e, alpha=0.95, lw=1.0))

        ax.annotate(f'الشارع الرئيسي / الواجهة المعتمدة - كود {emirate_selection}', xy=(plot_w/2, plot_l), xytext=(plot_w/2, plot_l + 2.5),
                    ha='center', fontsize=10.5, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-plot_w * 0.12, plot_w * 1.12)
        ax.set_ylim(-plot_l * 0.08, plot_l * 1.16)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f"{scheme_id.split(':')[0]} | المسقط المعماري التنفيذي المحدث - {emirate_selection}\nمسطح الأرضي: {effective_ground:.1f} م² | إجمالي البناء (BUA): {calc_total_bua:.1f} م²", fontsize=11.5, weight='bold', pad=15)
        st.pyplot(fig_plan)

    with tab_cad:
        col_c, col_m, col_p = st.columns(3)
        with col_c:
            st.markdown("#### 📐 AutoCAD (.DXF)")
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="SETBACKS", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (plot_w-side_sb, rear_sb), (plot_w-side_sb, plot_l-front_sb), (side_sb, plot_l-front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
            doc.layers.add(name="WALLS", color=4)
            for r in active_rooms:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
            dxf_buf = io.StringIO()
            doc.write(dxf_buf)
            st.download_button("💾 تحميل ملف AutoCAD (.DXF)", dxf_buf.getvalue().encode('utf-8'), "MasterPlan.dxf", "application/dxf")

        with col_m:
            st.markdown("#### 🧊 3ds Max / Blender (.OBJ)")
            obj_lines = ["# 3D Geometric Mesh for 3ds Max\n"]
            v_i = 1
            for idx, r in enumerate(active_rooms):
                x, y, w, h = r["x"], r["y"], r["w"], r["h"]
                verts = [(x,y,0),(x+w,y,0),(x+w,y+h,0),(x,y+h,0),(x,y,8.5),(x+w,y,8.5),(x+w,y+h,8.5),(x,y+h,8.5)]
                for vx, vy, vz in verts: obj_lines.append(f"v {vx:.2f} {vz:.2f} {vy:.2f}\n")
                f = v_i
                faces = [(f,f+1,f+2,f+3),(f+4,f+7,f+6,f+5),(f,f+4,f+5,f+1),(f+1,f+5,f+6,f+2),(f+2,f+6,f+7,f+3),(f+3,f+7,f+4,f)]
                obj_lines.append(f"g Room_{idx+1}\n")
                for f1,f2,f3,f4 in faces: obj_lines.append(f"f {f1} {f2} {f3} {f4}\n")
                v_i += 8
            st.download_button("💾 تحميل مجسم 3D (.OBJ)", "".join(obj_lines).encode('utf-8'), "Villa_3D.obj", "model/obj")

        with col_p:
            st.markdown("#### 🎨 Photoshop (.PNG 300 DPI)")
            img_buf = io.BytesIO()
            fig_plan.savefig(img_buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
            st.download_button("💾 تحميل شيت شفاف لـ Photoshop", img_buf.getvalue(), "Plan_Photoshop.png", "image/png")

# ==============================================================================
# MODULE 2: STRUCTURAL & GEOTECHNICAL CALCULATIONS (Prompt 07)
# ==============================================================================
elif "2. محرك الحسابات الإنشائية" in active_module:
    st.title("🏗️ محرك الحسابات الإنشائية والجيوتقنية (ACI 318 / BS 8110)")
    st.markdown("تحليل مسطحات التأسيس، إجهادات التربة المسموحة، وسماكات البلاطات اللاكمرية (Flat Slab) وفق الكود.")

    c_st1, c_st2, c_st3 = st.columns(3)
    with c_st1:
        sbc_val = st.number_input("جهد التربة الصافي المسموح Net SBC (kN/m²):", 60.0, 450.0, 150.0, 10.0)
    with c_st2:
        col_load = st.number_input("الحمل الأقصى لأثقل عمود داخلي Ultimate Load Pu (kN):", 200.0, 5000.0, 1250.0, 50.0)
    with c_st3:
        span_length = st.number_input("أطول بحر بين عمودين Clear Span Ln (متر):", 3.0, 12.0, 6.5, 0.25)

    # حسابات التأسيس
    service_load = col_load / 1.45
    footing_area = service_load / sbc_val
    footing_dim = np.sqrt(footing_area)
    slab_thickness = max(20.0, (span_length * 100) / 30.0) # ACI min thickness for flat slab without drop panels

    st.markdown("---")
    res1, res2, res3 = st.columns(3)
    res1.metric("مساحة القاعدة المنفصلة المطلوبة", f"{footing_area:.2f} م²")
    res2.metric("أبعاد القاعدة المربعة المقترحة", f"{footing_dim:.2f} × {footing_dim:.2f} م")
    res3.metric("السماكة الإنشائية للبلاطة اللاكمرية", f"{slab_thickness:.0f} سم")

    if sbc_val < 130:
        st.warning("⚠️ جهد التربة منخفض (< 130 kN/m²): يوصى هندسياً باعتماد لبشة مسلحة كاملة (Raft Foundation) لتفادي الهبوط المتفاوت (Differential Settlement).")
    else:
        st.success("✅ جهد التربة آمن للقواعد المنفصلة المسلحة المتصلة بميدات ربط جاسئة (Tie Beams) طبقاً لكود البناء.")

    st.markdown("""
    #### 📋 مواصفات المواد الإنشائية المعتمدة لمشاريع الدولة:
    * **خرسانة تحت الأرض (Substructure):** عيار C40 مقاوم للكبريتات (SRC) مع نسبة ماء إلى إسمنت لا تتجاوز 0.40.
    * **خرسانة الهيكل العلوي (Superstructure):** خرسانة بورتلاندية عادية OPC عيار C35/C40.
    * **حديد التسليح:** مشوه عالي المقاومة High Yield Deformed Bars إجهاد خضوع 500 N/mm².
    """)

# ==============================================================================
# MODULE 3: MEP CALCULATIONS ENGINE (Prompt 07)
# ==============================================================================
elif "3. محرك الأحمال الميكانيكية" in active_module:
    st.title("⚡ محرك الحسابات الكهروميكانيكية (MEP Load Sizing)")
    st.markdown("تقدير الأحمال الكهربائية وحجم التبريد المعتمد وفق معايير هيئات الكهرباء والبيئة (SEWA, DEWA, TAQA).")

    c_e1, c_e2 = st.columns(2)
    with c_e1:
        calc_bua = st.number_input("إجمالي مسطح البناء للمشروع BUA (م²):", 100.0, 15000.0, 850.0, 25.0)
    with c_e2:
        ac_system = st.selectbox("نظام التكييف المعتمد:", ["تكييف مخفي دكت سبليت Inverter", "نظام التبريد المتغير VRF / VRV", "شيلر مبرد بالماء/الهواء (Chiller)"])

    # الحسابات المعتمدة بمناخ الإمارات
    cooling_tr = round(calc_bua / 14.5, 1) # معدل 14.5 م2 لكل طن تبريد
    connected_kw = round(calc_bua * 0.12, 1) # 120 واط لكل م2
    demand_kva = round((connected_kw * 0.80) / 0.85, 1) # Demand Factor = 0.80, Power Factor = 0.85

    m_e1, m_e2, m_e3 = st.columns(3)
    m_e1.metric("إجمالي حمل التكييف التقديري", f"{cooling_tr} TR (طن تبريد)")
    m_e2.metric("الحمل الكهربائي المتصل (Connected)", f"{connected_kw} kW")
    m_e3.metric("الحمل التصميمي الأقصى (Demand Load)", f"{demand_kva} kVA")

    st.markdown("---")
    st.markdown(f"""
    #### 📋 الاشتراطات الفنية لتغذية الموقع ({emirate_selection}):
    * **لوحة التوزيع الرئيسية (MDB):** سعة قاطع رئيسي موصى بها: **{int(demand_kva * 1.5)}A TP&N**.
    * **القواطع الحساسة ELCB:** 30mA لدوائر المطابخ والحمامات والمضخات، و 100mA لدوائر الإنارة والتكييف.
    * **شبكة مياه الشرب:** أنابيب بولي بروبلين حراري (PPR Class PN20) معزولة حرارياً من الخزان إلى المضخات المعززة.
    * **خزان المياه:** خزان علوي وأرضي من ألياف الزجاج (GRP) مزود بوحدة تبريد صيفية مدمجة (Water Chiller).
    """)

# ==============================================================================
# MODULE 4: CPM SCHEDULE & GANTT ENGINE (Prompt 02)
# ==============================================================================
elif "4. محرك الجدولة الزمنية" in active_module:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج لمشروع مصمم (CPM Schedule)")
    st.markdown("إعداد جدول زمني تنفيذي متكامل لمشروع مصمم بالفعل وحساب المسار الحرج (Fast-Track).")

    cs1, cs2, cs3 = st.columns(3)
    with cs1: b_area = st.number_input("مسطح البناء الإجمالي للمشروع (م²):", 100.0, 30000.0, 850.0, 50.0)
    with cs2: s_date = st.date_input("تاريخ استلام الموقع وبدء الأعمال:", datetime.date.today())
    with cs3: p_speed = st.selectbox("وتيرة التنفيذ:", ["قياسي اعتيادي (Standard Track)", "مكثف / مسار سريع (Fast-Track)"])

    sp_fac = 0.82 if "مكثف" in p_speed else 1.0

    tasks = [
        {"Phase": "1. التراخيص وفحص التربة وشهادات NOC", "Days": int(28 * sp_fac)},
        {"Phase": "2. تجهيز الموقع والحفر والإحلال وتحديد الصفر المعماري", "Days": int(21 * sp_fac)},
        {"Phase": "3. صبة النظافة PCC والأساسات والرقاب المسلحة (SRC)", "Days": int(35 * sp_fac)},
        {"Phase": "4. العزل المائي للأساسات والردم واختبار الدمك", "Days": int(21 * sp_fac)},
        {"Phase": "5. الميدات الأرضية وصبة الأرضية Slab on Grade", "Days": int(20 * sp_fac)},
        {"Phase": "6. هيكل الطابق الأرضي (أعمدة وسقف Flat Slab)", "Days": int(35 * sp_fac)},
        {"Phase": "7. هيكل الطابق الأول والسطح وأعمال المباني العظم", "Days": int(45 * sp_fac)},
        {"Phase": "8. التمديدات الكهروميكانيكية وتأسيسات MEP الأولية", "Days": int(45 * sp_fac)},
        {"Phase": "9. العزل المائي والحراري للأسطح بنظام الكومبو المعتمد", "Days": int(20 * sp_fac)},
        {"Phase": "10. أعمال اللياسة الإسمنتية (طرطشة وبلاستر) والأرضيات", "Days": int(60 * sp_fac)},
        {"Phase": "11. الواجهات الخارجية والألومنيوم والزجاج والأسوار", "Days": int(45 * sp_fac)},
        {"Phase": "12. الفحص النهائي وإطلاق التيار وشهادة الإنجاز البلدية", "Days": int(28 * sp_fac)}
    ]

    curr_start = pd.to_datetime(s_date)
    records = []
    for item in tasks:
        curr_end = curr_start + pd.Timedelta(days=item["Days"])
        records.append({"المرحلة التنفيذية": item["Phase"], "البداية": curr_start, "النهاية": curr_end, "المدة (يوم)": item["Days"]})
        curr_start = curr_end - pd.Timedelta(days=int(item["Days"] * 0.28))

    df_sched = pd.DataFrame(records)
    tot_days = (df_sched["النهاية"].max() - pd.to_datetime(s_date)).days

    res_d1, res_d2, res_d3 = st.columns(3)
    res_d1.metric("إجمالي مدة المشروع", f"{tot_days} يوماً")
    res_d2.metric("المدة بالشهور", f"{tot_days / 30.5:.1f} شهراً")
    res_d3.metric("تاريخ الإنجاز المتوقع", df_sched["النهاية"].max().strftime('%Y-%m-%d'))

    fig_g, ax_g = plt.subplots(figsize=(11, 6.5), dpi=180)
    for i, row in df_sched.iterrows():
        s_num = mdates.date2num(row["البداية"])
        e_num = mdates.date2num(row["النهاية"])
        ax_g.barh(row["المرحلة التنفيذية"], e_num - s_num, left=s_num, color='#2563EB', edgecolor='#1E3A8A', height=0.55)

    ax_g.xaxis_date()
    ax_g.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax_g.grid(True, linestyle=':', alpha=0.6)
    ax_g.invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig_g)

    csv_s_buf = io.StringIO()
    df_sched.to_csv(csv_s_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة البرنامج الزمني بصيغة Excel / CSV", csv_s_buf.getvalue().encode('utf-8-sig'), "Project_Schedule.csv", "text/csv")

# ==============================================================================
# MODULE 5: DETAILED BOQ & COST ESTIMATOR (Prompt 06)
# ==============================================================================
elif "5. محرك حصر الكميات" in active_module:
    st.title("📊 محرك حصر الكميات والمواصفات القياسية (CSI MasterFormat)")
    st.markdown("إعداد جدول كميات تنفيذي وحساب تكلفة العظم والتشطيبات لمشروع مصمم مسبقاً.")

    cb1, cb2, cb3 = st.columns(3)
    with cb1: qto_bua = st.number_input("مسطح البناء الإجمالي BUA للمشروع (م²):", 100.0, 30000.0, 850.0, 50.0)
    with cb2: fin_level = st.selectbox("مستوى المواصفات:", ["ديلوكس تجاري (Standard Deluxe)", "سوبر ديلوكس فاخر (Super Deluxe)", "ألترا لوكجري VIP (Ultra Luxury)"])
    with cb3: fp_area = st.number_input("مسطح البصمة الأرضية Footprint (م²):", 50.0, 15000.0, float(qto_bua * 0.52), 25.0)

    # حساب الكميات الإنشائية
    conc_sub = round(qto_bua * 0.26, 1)
    conc_sup = round(qto_bua * 0.40, 1)
    tot_conc = round(conc_sub + conc_sup, 1)
    steel_t = round((tot_conc * 115) / 1000, 1)
    blocks_qty = round(qto_bua * 4.3)
    waterproof_m2 = round(fp_area * 2.3, 1)
    plaster_m2 = round(qto_bua * 6.5, 1)

    r_mult = 1.0 if "تجاري" in fin_level else (1.35 if "سوبر" in fin_level else 1.80)

    boq_items = [
        {"كود": "01-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الحفر العام والتسوية ونقل المخلفات لمنسوب التأسيس", "الوحدة": "م³", "الكمية": round(fp_area * 1.8, 1), "السعر (AED)": 25.0},
        {"كود": "02-01", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة نظافة عادية Blinding PCC عيار 20 N/mm² أسفل القواعد", "الوحدة": "م³", "الكمية": round(fp_area * 0.12, 1), "السعر (AED)": 270.0},
        {"كود": "02-02", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة كبريتية SRC C40 للأساسات والميدات والرقاب", "الوحدة": "م³", "الكمية": conc_sub, "السعر (AED)": 340.0},
        {"كود": "02-03", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": conc_sup, "السعر (AED)": 330.0},
        {"كود": "03-01", "بند الأعمال الهندسي والمواصفة الفنية": "حديد تسليح عالي المقاومة مشوه رتبة 500 MPa مشتملاً على القص والتشكيل", "الوحدة": "طن", "الكمية": steel_t, "السعر (AED)": 2750.0},
        {"كود": "04-01", "بند الأعمال الهندسي والمواصفة الفنية": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والميدات مع ألواح الحماية", "الوحدة": "م²", "الكمية": waterproof_m2, "السعر (AED)": 45.0},
        {"كود": "05-01", "بند الأعمال الهندسي والمواصفة الفنية": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومصمت/مفرغ للداخل", "الوحدة": "حبة", "الكمية": blocks_qty, "السعر (AED)": 3.6},
        {"كود": "06-01", "بند الأعمال الهندسي والمواصفة الفنية": "لياسة إسمنتية داخلية وخارجية (طرطشة + بلاستر + زوايا وشبك فايبر)", "الوحدة": "م²", "الكمية": plaster_m2, "السعر (AED)": round(22.0 * r_mult, 1)},
        {"كود": "07-01", "بند الأعمال الهندسي والمواصفة الفنية": "نظام العزل المائي والحراري المتكامل للأسطح (كومبو Combo System)", "الوحدة": "م²", "الكمية": round(fp_area * 1.1, 1), "السعر (AED)": 115.0},
        {"كود": "08-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الألومنيوم والزجاج المزدوج العازل (Double Glazing) واللوفرز", "الوحدة": "م²", "الكمية": round(qto_bua * 0.22, 1), "السعر (AED)": round(650.0 * r_mult, 1)}
    ]

    df_b = pd.DataFrame(boq_items)
    df_b["الإجمالي التقديري (AED)"] = round(df_b["الكمية"] * df_b["السعر (AED)"])
    tot_cost = df_b["الإجمالي التقديري (AED)"].sum()

    bq1, bq2, bq3 = st.columns(3)
    bq1.metric("إجمالي التكلفة التقديرية للأعمال", f"{tot_cost:,.0f} درهم إماراتي")
    bq2.metric("متوسط سعر المتر المربع للبناء", f"{tot_cost / qto_bua:,.1f} AED/م²")
    bq3.metric("مستوى المواصفات المطبق", fin_level.split('(')[0])

    st.dataframe(df_b, use_container_width=True)

    csv_b_buf = io.StringIO()
    df_b.to_csv(csv_b_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات (BOQ) بصيغة Excel / CSV", csv_b_buf.getvalue().encode('utf-8-sig'), "Project_BOQ.csv", "text/csv")

# ==============================================================================
# MODULE 6: AI ENGINEERING COPILOT (Prompt 05)
# ==============================================================================
else:
    st.title("🤖 المستشار الهندسي الذكي (UAE AI Engineering Copilot)")
    st.markdown("مساعد ذكي متخصص في كودات البناء الإماراتية، تشخيص المخططات، وحل المشكلات الإنشائية والمعمارية للمشتركين.")

    for msg in st.session_state.chat_log:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    q = st.chat_input("اطرح استفسارك الهندسي، اشتراطات البلدية، أو مشكلة المشروع هنا...")
    if q:
        st.session_state.chat_log.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)

        with st.chat_message("assistant"):
            if api_key:
                client = genai.Client(api_key=api_key)
                sp = (
                    f"You are a senior UAE consulting structural and civil engineer in {emirate_selection}. "
                    "You are rigorous, technical, analytical, objective, and deeply versed in municipal codes "
                    "(Dubai Building Code DBC, Sharjah Municipal Regulations, Abu Dhabi IBC, and UAE Fire & Life Safety Code). "
                    "Provide clear, actionable engineering answers, avoiding filler or generic fluff."
                )
                try:
                    resp = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[sp, q]
                    )
                    ans = resp.text
                except Exception as ex:
                    ans = f"تعذر الاتصال بالمستشار الذكي: {ex}"
            else:
                ans = "المستشار الذكي يتطلب حفظ مفتاح GEMINI_API_KEY في إعدادات Secrets السحابية."

            st.markdown(ans)
            st.session_state.chat_log.append({"role": "assistant", "content": ans})
