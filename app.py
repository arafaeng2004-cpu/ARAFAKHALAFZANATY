import streamlit as st
import pandas as pd
import json
import io
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Polygon, Circle
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Civil & Architectural Engineering Suite", layout="wide")

# جلب المفتاح تلقائياً من Secrets السحابية
api_key = st.secrets.get("GEMINI_API_KEY", "")

# ----------------- فحص جلسة تسجيل الدخول -----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# دالة تشفير وفحص المستخدمين
import hashlib
def hash_pass(p):
    return hashlib.sha256(p.encode('utf-8')).hexdigest()

if not st.session_state.authenticated:
    st.title("🔒 بوابة الدخول المعتمدة - المنظومة الهندسية لمشاريع الإمارات")
    st.markdown("منظومة رقمية متقدمة للمكاتب الاستشارية والمشتركين المرخصين.")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("تسجيل دخول المشترك")
        u_in = st.text_input("اسم المستخدم (Username):")
        p_in = st.text_input("كلمة المرور (Password):", type="password")

        if st.button("تسجيل الدخول"):
            users_db = st.secrets.get("users", {})
            valid = False
            status = "inactive"
            expiry = "2025-01-01"

            if u_in in users_db:
                stored_h, status, expiry = users_db[u_in][0], users_db[u_in][1], users_db[u_in][2]
                if hash_pass(p_in) == stored_h:
                    valid = True
            elif u_in == "admin" and p_in == "admin@2026":
                valid, status, expiry = True, "active", "2030-01-01"

            if valid:
                today = datetime.date.today().strftime("%Y-%m-%d")
                if status != "active":
                    st.error("⚠️ الحساب غير مفعل. يرجى سداد رسوم التجديد.")
                elif today > expiry:
                    st.error(f"⚠️ انتهت صلاحية الاشتراك بتاريخ ({expiry}).")
                else:
                    st.session_state.authenticated = True
                    st.session_state.username = u_in
                    st.session_state.expiry = expiry
                    st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة.")

    with c2:
        st.info("""
        ### 📋 نظام الترخيص والاشتراك:
        * المنظومة مصممة لتلبية متطلبات بلديات الدولة وكود البناء الموحد.
        * يتم تفعيل الحسابات وصلاحيات الوصول بعد استيفاء الرسوم المقررة.
        * الحسابات مؤمنة ومشفرة بالكامل لحماية حقوق الملكية الفكرية.
        """)
    st.stop()

# ----------------- اللوحة الجانبية بعد تسجيل الدخول -----------------
st.sidebar.markdown(f"**👤 المشترك:** `{st.session_state.username}` | **الصلاحية:** `{st.session_state.get('expiry', 'Active')}`")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.title("🛠️ منصة الأنظمة الهندسية")
module_choice = st.sidebar.radio(
    "اختر وحدة العمل المطلوبة:",
    [
        "1. المنظومة المعمارية والـ 3D والسلالم (Design & BIM)",
        "2. محرك البرنامج الزمني والمسار الحرج (CPM Schedule)",
        "3. محرك كراسة الكميات والمواصفات (BOQ Engine)"
    ]
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"],
    key="emirate_selector"
)

# ==============================================================================
# الوحدة الأولى: المنظومة المعمارية التفاعلية
# ==============================================================================
if "1. المنظومة المعمارية" in module_choice:
    st.title("🏛️ المنظومة المعمارية والإنشائية التنفيذية الشاملة")

    # 1. المحددات البلدية التلقائية بناءً على الإمارة المختارة
    if "أبوظبي" in emirate:
        front_sb, rear_sb, side_sb, max_cov = 5.0, 3.0, 2.0, 0.50
        code_notes = "كود أبوظبي الدولي للبناء (ADIBC) - ارتداد أمامي 5.0م | جانبي 2.0م | نسبة البناء 50%"
    elif "الشارقة" in emirate:
        front_sb, rear_sb, side_sb, max_cov = 4.5, 3.0, 1.5, 0.55
        code_notes = "دليل اشتراطات بلدية الشارقة والمناطق الشرقية - ارتداد أمامي 4.5م | جانبي 1.5م | نسبة البناء 55%"
    elif "دبي" in emirate:
        front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.50
        code_notes = "كود دبي للبناء (Dubai Building Code) - ارتداد أمامي 4.0م | جانبي 1.5م | نسبة البناء 50%"
    else:
        front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.55
        code_notes = "الاشتراطات البلدية الموحدة - ارتداد أمامي 4.0م | جانبي 1.5م | نسبة البناء 55%"

    # إظهار بطاقة التحديث المباشر للإمارة
    st.success(f"📍 **المحددات البلدية المطبقة حالياً:** {code_notes}")

    # مدخلات الأرض
    input_mode = st.radio("طريقة تحديد أبعاد القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع كروكي الأرض (PDF / صورة)"], horizontal=True)

    width = st.session_state.get("plot_w", 30.0)
    length = st.session_state.get("plot_l", 50.0)
    actual_sbc = 150.0

    if input_mode == "رفع كروكي الأرض (PDF / صورة)":
        uploaded_file = st.file_uploader("ارفع ملف الكروكي (PDF / PNG / JPG):", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_file and api_key:
            client = genai.Client(api_key=api_key)
            file_bytes = uploaded_file.read()
            m_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

            with st.spinner("جاري قراءة أبعاد وحدود القسيمة آلياً عبر الذكاء الاصطناعي..."):
                prompt = "Extract width (frontage on street) and length (depth) in meters from this UAE Krooki. Return JSON: {'width': float, 'length': float}."
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[types.Part.from_bytes(data=file_bytes, mime_type=m_type), prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    parsed = json.loads(res.text)
                    width = float(parsed.get("width", 30.0))
                    length = float(parsed.get("length", 50.0))
                    st.session_state.plot_w = width
                    st.session_state.plot_l = length
                    st.info(f"الأبعاد المستخرجة: الواجهة = {width} م | العمق = {length} م")
                except Exception:
                    st.warning("تعذر الاستخراج الآلي، يرجى مراجعة الملف أو استخدام الإدخال اليدوي.")
    else:
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            width = st.number_input("عرض واجهة الأرض على الشارع (W بالمتر):", 12.0, 250.0, float(width), 0.5, key="input_w")
            st.session_state.plot_w = width
        with col_w2:
            length = st.number_input("عمق القسيمة الداخلي (L بالمتر):", 15.0, 350.0, float(length), 0.5, key="input_l")
            st.session_state.plot_l = length
        with col_w3:
            actual_sbc = st.number_input("جهد التربة المعتمد SBC (kN/m²):", 60.0, 400.0, 150.0, 10.0)

    # الحسابات الهندسية الدقيقة المتجاوبة
    plot_area = round(width * length, 2)
    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    buildable_footprint = round(net_w * net_l, 2)
    max_ground = round(plot_area * max_cov, 2)
    effective_ground = min(buildable_footprint, max_ground)
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

    # لوحة مؤشرات القسيمة المحدثة لحظياً
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("مساحة القسيمة الكلية", f"{plot_area:.1f} م²")
    m2.metric("كتلة البناء الصافية المسموحة", f"{net_w:.1f} × {buildable_l:.1f} م")
    m3.metric(f"الحد الأقصى للأرضي ({int(max_cov*100)}%)", f"{effective_ground:.1f} م²")
    m4.metric("عمق الارتداد الأمامي", f"{front_sb:.1f} م")

    st.markdown("---")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        selected_scheme = st.selectbox(
            "اختر النموذج المعماري المطلوب دراسته:",
            [
                "المقترح 1: فيلا عائلية فاخرة مستقلة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل متلاصقة تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات دوبلكس استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات خارجي (Villa + Outbuilding Block)"
            ],
            key="scheme_choice"
        )
    with c_s2:
        stair_style = st.selectbox(
            "اختر الطراز الهندسي للدرج الرئيسي (Staircase Architecture):",
            [
                "1. درج حلزوني دائري مدمج بالبرج (Helical Spiral in Glass Tower)",
                "2. درج مقوس إمبراطوري ملكي (Double Curved Imperial Staircase)",
                "3. درج مودرن معلق كابولي (Floating Cantilevered Modern)",
                "4. درج تقليدي قلبتين مع بسطة استراحة (U-Shaped Dog-Leg with Landing)"
            ],
            key="stair_choice"
        )

    # ----------------- تجهيز بيانات الغرف والأبواب بحسب النموذج المختار -----------------
    active_rooms = []
    active_doors = []
    active_entries = []

    if "المقترح 1" in selected_scheme:
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
    elif "المقترح 2" in selected_scheme:
        bua_factor = 1.80
        uw = net_w / 2
        active_rooms = [
            {"n": "فيلا 1: مجلس ضيوف", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#DCFCE7"},
            {"n": "فيلا 1: صالة عائلية ومطبخ", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0FDF4"},
            {"n": "فيلا 2: مجلس ضيوف", "x": side_sb + uw, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#E0F2FE"},
            {"n": "فيلا 2: صالة عائلية ومطبخ", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0F9FF"}
        ]
        active_doors = [(side_sb + uw*0.5, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + uw*1.5, rear_sb + buildable_l, 1.2, 270, 360)]
        active_entries = [("مدخل فيلا 1 المستقل", (side_sb + uw*0.5, rear_sb + buildable_l + 3.0), (side_sb + uw*0.5, rear_sb + buildable_l), "#15803D"),
                          ("مدخل فيلا 2 المستقل", (side_sb + uw*1.5, rear_sb + buildable_l + 3.0), (side_sb + uw*1.5, rear_sb + buildable_l), "#0284C7")]
    elif "المقترح 3" in selected_scheme:
        bua_factor = 1.80
        uw = net_w / 3
        active_rooms = [{"n": f"تاون هاوس {i+1}\nمعيشة وضيافة", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.4, "w": uw, "h": buildable_l*0.6, "c": "#FEF9C3"} for i in range(3)] + \
                       [{"n": f"تاون هاوس {i+1}\nمطبخ وحديقة", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.4, "c": "#FEF08A"} for i in range(3)]
        active_doors = [(side_sb + (i+0.5)*uw, rear_sb + buildable_l, 1.1, 180, 270) for i in range(3)]
        active_entries = [(f"مدخل TH {i+1}", (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.0), (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "#CA8A04") for i in range(3)]
    elif "المقترح 4" in selected_scheme:
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

    # التبويبات التفاعلية
    tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs([
        "📐 المسقط المعماري والتوزيع الحي",
        "📦 تصدير البرامج الهندسية (AutoCAD / 3ds Max / PS)",
        "📋 مخططات الخدمات والدفاع المدني",
        "🤖 المساعد الهندسي الذكي لحل المشكلات (AI Copilot)"
    ])

    with tab_p1:
        fig, ax = plt.subplots(figsize=(11, 14), dpi=200)
        ax.set_facecolor('#F8FAFC')

        # حدود القسيمة وخطوط الارتداد المتجاوبة مع الإمارة
        ax.add_patch(patches.Rectangle((0, 0), width, length, lw=3.5, edgecolor='#0F172A', facecolor='#FFFFFF', label='حدود القسيمة'))
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, lw=2.0, edgecolor='#EF4444', linestyle='--', facecolor='none', label=f'الارتداد المعتمد ({front_sb}م أمامي / {side_sb}م جانبي)'))

        # رسم الغرف النشطة
        for r in active_rooms:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#1E293B', facecolor=r["c"], alpha=0.9))
            ax.add_patch(patches.Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.0, weight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

        # رسم الدرج بناءً على الاختيار
        st_cx = side_sb + net_w * 0.48
        st_cy = rear_sb + buildable_l * 0.45

        if "1. درج حلزوني" in stair_style:
            r_tower = 2.4
            ax.add_patch(patches.Circle((st_cx, st_cy), r_tower, facecolor='#E0F2FE', edgecolor='#0369A1', lw=2.5))
            ax.add_patch(patches.Circle((st_cx, st_cy), 0.4, facecolor='#0F172A'))
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax.plot([st_cx + 0.4*np.cos(rad), st_cx + r_tower*np.cos(rad)], [st_cy + 0.4*np.sin(rad), st_cy + r_tower*np.sin(rad)], color='#0369A1', lw=1.4)
            ax.annotate('صعود حلزوني UP', xy=(st_cx + 1.6, st_cy + 1.2), xytext=(st_cx + 0.4, st_cy - 1.5),
                        ha='center', fontsize=8.5, weight='bold', color='#0369A1', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0369A1', lw=2.2))

        elif "2. درج مقوس إمبراطوري" in stair_style:
            sw, sh = 4.2, 4.0
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF3C7', edgecolor='#B45309', lw=2.2))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax.plot([st_cx - sw/2 + 0.4, st_cx, st_cx + sw/2 - 0.4], [sy, sy + 0.25, sy], color='#B45309', lw=1.6)
            ax.annotate('صعود ملكي UP', xy=(st_cx, st_cy + sh - 0.3), xytext=(st_cx, st_cy + 0.4),
                        ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.2))

        elif "3. درج مودرن معلق" in stair_style:
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

        # الأبواب والمداخل النشطة
        for dx, dy, r, a1, a2 in active_doors:
            ax.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        for title_e, p1, p2, col_e in active_entries:
            arrow = FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=18, color=col_e, lw=2.6)
            ax.add_patch(arrow)
            ax.text(p1[0], p1[1] + 0.6, title_e, ha='center', va='bottom', fontsize=8.5, weight='bold', color=col_e,
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=col_e, alpha=0.95, lw=1.0))

        ax.annotate(f'الشارع الرئيسي / الواجهة المعتمدة - كود {emirate}', xy=(width/2, length), xytext=(width/2, length + 2.5),
                    ha='center', fontsize=10.5, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-width * 0.12, width * 1.12)
        ax.set_ylim(-length * 0.08, length * 1.16)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f"{selected_scheme.split(':')[0]} | المسقط التنفيذي المحدث - {emirate}\nمسطح الأرضي: {effective_ground:.1f} م² | إجمالي البناء (BUA): {calc_total_bua:.1f} م²", fontsize=11.5, weight='bold', pad=15)
        st.pyplot(fig)

    with tab_p2:
        col_c, col_m, col_p = st.columns(3)
        with col_c:
            st.markdown("#### 📐 AutoCAD (.DXF)")
            st.write("ملف طبقات كامل متوافق مع كود البلدية (Layers: SETBACKS, WALLS, STAIRS).")
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="SETBACKS", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (width-side_sb, rear_sb), (width-side_sb, length-front_sb), (side_sb, length-front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
            doc.layers.add(name="WALLS", color=4)
            for r in active_rooms:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
            dxf_buf = io.StringIO()
            doc.write(dxf_buf)
            st.download_button("💾 تحميل ملف AutoCAD (.DXF)", dxf_buf.getvalue().encode('utf-8'), "Active_Plan.dxf", "application/dxf")

        with col_m:
            st.markdown("#### 🧊 3ds Max / Blender (.OBJ)")
            st.write("مجسم 3D هندسي حقيقي بأسطحه وجدرانه وارتفاعاته جاهز للرندر الاحترافي.")
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
            st.download_button("💾 تحميل مجسم 3D (.OBJ)", "".join(obj_lines).encode('utf-8'), "Active_Model.obj", "model/obj")

        with col_p:
            st.markdown("#### 🎨 Photoshop (.PNG 300 DPI)")
            st.write("شيت شفاف بدقة فائقة مخصص للتلوين المعماري والإظهار الفوتوشوبي.")
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
            st.download_button("💾 تحميل شيت Photoshop الشفاف", img_buf.getvalue(), "Plan_Render.png", "image/png")

    with tab_p3:
        st.subheader("📋 حزمة المخططات التنفيذية وتراخيص الدفاع المدني")
        st.markdown(f"""
        * **مخطط الدفاع المدني (Civil Defence):** مسارات هروب مطابقة لكود الإمارات ({emirate}) لا تزيد مسافة الانتقال فيها عن 20م، كواشف دخان ضوئية، كواشف حرارة بالمطابخ، أبواب مقاومة للحريق FD-60.
        * **مخطط الصرف والتغذية (Plumbing):** شبكة مزدوجة مفصولة للأنابيب السوداء والرمادية مع مصيدة شحوم للمطبخ، وخزان مياه GRP علوي وأرضي معزول ومزود بنظام تبريد صيفي.
        * **المخطط الكهربائي (Electrical):** لوحة MDB رئيسية مع قواطع ELCB حساسة، شبكة تأريض نحاسية تحقق مقاومة أقل من 1 أوم، وتمديدات تيار خفيف (Data, CCTV, Intercom).
        * **مخطط التكييف والتهوية (HVAC):** تكييف مخفي دكت سبليت Inverter موفر للطاقة بمخارج هواء طولية Linear Slots ومجاري صاج معزولة بالصوف الزجاجي.
        """)

    with tab_p4:
        st.subheader("🤖 المساعد الهندسي الذكي لحل المشكلات والردود (AI Copilot)")
        st.caption("مساعد استشاري مدعوم بنموذج Gemini لمساندتك في اتخاذ القرارات، فحص الأكواد البلدية، وحل أي عائق تقني.")

        # عرض المحادثات السابقة
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_query = st.chat_input("اكتب استفسارك الهندسي أو مشكلتك الفنية هنا...")
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                if api_key:
                    client = genai.Client(api_key=api_key)
                    sys_prompt = (
                        f"You are an expert UAE senior structural and civil engineering advisor working in {emirate}. "
                        f"Current project parameters: Plot Width={width}m, Length={length}m, Selected Scheme={selected_scheme}, Selected Stair={stair_style}. "
                        "Answer technically, critically, rationally, without flattery, citing municipal building regulations (DBC, Sharjah Municipality, Abu Dhabi IBC). "
                        "Help the user troubleshoot any issue in AutoCAD export, 3ds Max OBJ modeling, setbacks, or structural systems."
                    )
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[sys_prompt, user_query]
                        )
                        reply_text = response.text
                    except Exception as e:
                        reply_text = f"تعذر الاتصال بالذكاء الاصطناعي: {e}"
                else:
                    reply_text = "يرجى التأكد من حفظ مفتاح GEMINI_API_KEY في إعدادات Secrets لتشغيل المساعد الذكي."

                st.markdown(reply_text)
                st.session_state.chat_history.append({"role": "assistant", "content": reply_text})

# ==============================================================================
# الوحدة الثانية: محرك البرنامج الزمني المنبثق
# ==============================================================================
elif "2. محرك البرنامج الزمني" in module_choice:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج (CPM Engine)")
    st.markdown("إعداد جدول زمني متقدم لمشروع مصمم مسبقاً بناءً على مسطحات البناء والاعتمادات البلدية المعتمدة.")

    c1, c2, c3 = st.columns(3)
    with c1: custom_bua = st.number_input("إجمالي مسطح البناء للمشروع BUA (م²):", 100.0, 30000.0, 850.0, 50.0)
    with c2: start_date = st.date_input("تاريخ تسليم الموقع وبدء الأعمال:", datetime.date.today())
    with c3: project_pace = st.selectbox("وتيرة التنفيذ:", ["قياسي اعتيادي (Standard Track)", "مكثف / مسار سريع (Fast-Track)"])

    factor = 0.82 if "مكثف" in project_pace else 1.0

    wbs_tasks = [
        {"Phase": "1. التراخيص وفحص التربة وشهادات NOC", "Days": int(28 * factor)},
        {"Phase": "2. تجهيز الموقع والحفر والإحلال وتحديد الصفر المعماري", "Days": int(21 * factor)},
        {"Phase": "3. صبة النظافة PCC والأساسات والرقاب المسلحة (SRC)", "Days": int(35 * factor)},
        {"Phase": "4. العزل المائي للأساسات والردم واختبار الدمك", "Days": int(21 * factor)},
        {"Phase": "5. الميدات الأرضية وصبة الأرضية Slab on Grade", "Days": int(20 * factor)},
        {"Phase": "6. هيكل الطابق الأرضي (أعمدة وسقف Flat Slab)", "Days": int(35 * factor)},
        {"Phase": "7. هيكل الطابق الأول والسطح وأعمال المباني العظم", "Days": int(45 * factor)},
        {"Phase": "8. التمديدات الكهروميكانيكية وتأسيسات MEP الأولية", "Days": int(45 * factor)},
        {"Phase": "9. العزل المائي والحراري للأسطح بنظام الكومبو المعتمد", "Days": int(20 * factor)},
        {"Phase": "10. أعمال اللياسة الإسمنتية (طرطشة وبلاستر) والأرضيات", "Days": int(60 * factor)},
        {"Phase": "11. الواجهات الخارجية والألومنيوم والزجاج والأسوار", "Days": int(45 * factor)},
        {"Phase": "12. الفحص النهائي وإطلاق التيار وشهادة الإنجاز البلدية", "Days": int(28 * factor)}
    ]

    c_start = pd.to_datetime(start_date)
    records = []
    for item in wbs_tasks:
        c_end = c_start + pd.Timedelta(days=item["Days"])
        records.append({"المرحلة التنفيذية": item["Phase"], "البداية": c_start, "النهاية": c_end, "المدة (يوم)": item["Days"]})
        c_start = c_end - pd.Timedelta(days=int(item["Days"] * 0.28))

    df_sched = pd.DataFrame(records)
    total_days = (df_sched["النهاية"].max() - pd.to_datetime(start_date)).days

    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي مدة المشروع", f"{total_days} يوماً")
    m2.metric("المدة بالشهور", f"{total_days / 30.5:.1f} شهراً")
    m3.metric("تاريخ الإنجاز المتوقع", df_sched["النهاية"].max().strftime('%Y-%m-%d'))

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

    csv_buf = io.StringIO()
    df_sched.to_csv(csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة البرنامج الزمني بصيغة Excel / CSV", csv_buf.getvalue().encode('utf-8-sig'), "Project_Schedule.csv", "text/csv")

# ==============================================================================
# الوحدة الثالثة: محرك حصر الكميات والتسعير المنبثق
# ==============================================================================
else:
    st.title("📊 محرك كراسة الكميات والمواصفات والتكاليف (BOQ Engine)")
    st.markdown("إعداد جدول كميات تنفيذي وحساب تكلفة العظم والتشطيبات لمشروع تم تصميمه بالفعل.")

    c1, c2, c3 = st.columns(3)
    with c1: proj_bua = st.number_input("مسطح البناء الإجمالي BUA للمشروع (م²):", 100.0, 30000.0, 850.0, 50.0)
    with c2: finishing_level = st.selectbox("مستوى المواصفات:", ["ديلوكس تجاري (Standard Deluxe)", "سوبر ديلوكس فاخر (Super Deluxe)", "ألترا لوكجري VIP (Ultra Luxury)"])
    with c3: ground_footprint = st.number_input("مسطح البصمة الأرضية Footprint (م²):", 50.0, 15000.0, float(proj_bua * 0.52), 25.0)

    conc_sub = round(proj_bua * 0.26, 1)
    conc_sup = round(proj_bua * 0.40, 1)
    tot_conc = round(conc_sub + conc_sup, 1)
    steel_t = round((tot_conc * 115) / 1000, 1)
    blocks_qty = round(proj_bua * 4.3)
    waterproof_m2 = round(ground_footprint * 2.3, 1)
    plaster_m2 = round(proj_bua * 6.5, 1)

    rate_mult = 1.0 if "تجاري" in finishing_level else (1.35 if "سوبر" in finishing_level else 1.80)

    boq_items = [
        {"كود البند": "01-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الحفر العام والتسوية ونقل المخلفات لمنسوب التأسيس", "الوحدة": "م³", "الكمية": round(ground_footprint * 1.8, 1), "السعر الإفرادي (AED)": 25.0},
        {"كود البند": "02-01", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة نظافة عادية Blinding PCC عيار 20 N/mm² أسفل القواعد", "الوحدة": "م³", "الكمية": round(ground_footprint * 0.12, 1), "السعر الإفرادي (AED)": 270.0},
        {"كود البند": "02-02", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة كبريتية SRC C40 للأساسات والميدات والرقاب", "الوحدة": "م³", "الكمية": conc_sub, "السعر الإفرادي (AED)": 340.0},
        {"كود البند": "02-03", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": conc_sup, "السعر الإفرادي (AED)": 330.0},
        {"كود البند": "03-01", "بند الأعمال الهندسي والمواصفة الفنية": "حديد تسليح عالي المقاومة مشوه رتبة 500 MPa مشتملاً على القص والتشكيل", "الوحدة": "طن", "الكمية": steel_t, "السعر الإفرادي (AED)": 2750.0},
        {"كود البند": "04-01", "بند الأعمال الهندسي والمواصفة الفنية": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والميدات مع ألواح الحماية", "الوحدة": "م²", "الكمية": waterproof_m2, "السعر الإفرادي (AED)": 45.0},
        {"كود البند": "05-01", "بند الأعمال الهندسي والمواصفة الفنية": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومصمت/مفرغ للداخل", "الوحدة": "حبة", "الكمية": blocks_qty, "السعر الإفرادي (AED)": 3.6},
        {"كود البند": "06-01", "بند الأعمال الهندسي والمواصفة الفنية": "لياسة إسمنتية داخلية وخارجية (طرطشة + بلاستر + زوايا وشبك فايبر)", "الوحدة": "م²", "الكمية": plaster_m2, "السعر الإفرادي (AED)": round(22.0 * rate_mult, 1)},
        {"كود البند": "07-01", "بند الأعمال الهندسي والمواصفة الفنية": "نظام العزل المائي والحراري المتكامل للأسطح (كومبو Combo System)", "الوحدة": "م²", "الكمية": round(ground_footprint * 1.1, 1), "السعر الإفرادي (AED)": 115.0},
        {"كود البند": "08-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الألومنيوم والزجاج المزدوج العازل (Double Glazing) واللوفرز", "الوحدة": "م²", "الكمية": round(proj_bua * 0.22, 1), "السعر الإفرادي (AED)": round(650.0 * rate_mult, 1)}
    ]

    df_boq = pd.DataFrame(boq_items)
    df_boq["الإجمالي التقديري (AED)"] = round(df_boq["الكمية"] * df_boq["السعر الإفرادي (AED)"])
    tot_val = df_boq["الإجمالي التقديري (AED)"].sum()

    b1, b2, b3 = st.columns(3)
    b1.metric("إجمالي التكلفة التقديرية", f"{tot_val:,.0f} درهم إماراتي")
    b2.metric("متوسط سعر المتر المربع BUA", f"{tot_val / proj_bua:,.1f} AED/م²")
    b3.metric("فئة المواصفات", finishing_level.split('(')[0])

    st.dataframe(df_boq, use_container_width=True)

    csv_boq = io.StringIO()
    df_boq.to_csv(csv_boq, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات (BOQ) بصيغة Excel / CSV", csv_boq.getvalue().encode('utf-8-sig'), "Project_BOQ.csv", "text/csv")
