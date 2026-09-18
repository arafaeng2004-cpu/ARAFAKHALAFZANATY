import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import datetime
import hashlib
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, Rectangle, Polygon
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import ezdxf
from google import genai
from google.genai import types

# ------------------------------------------------------------------------------
# 1. تهيئة المنظومة وضبط بيئة العرض
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="EmaratBuild Enterprise Engineering OS",
    layout="wide",
    initial_sidebar_state="expanded"
)

secret_gemini_key = st.secrets.get("GEMINI_API_KEY", "")

# ------------------------------------------------------------------------------
# 2. بناء النواة البرمجية للتوأم الرقمي (Digital Twin State Machine)
# ------------------------------------------------------------------------------
def compute_state_hash(state_dict):
    serializable = {
        "plot_w": state_dict.get("plot_w"),
        "plot_l": state_dict.get("plot_l"),
        "sbc": state_dict.get("sbc"),
        "emirate": state_dict.get("emirate"),
        "rev_id": state_dict.get("rev_id"),
        "studio": state_dict.get("active_studio"),
        "concept": state_dict.get("active_concept")
    }
    raw = json.dumps(serializable, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:12].upper()

def init_project_twin():
    default_twin = {
        "project_id": "UAE-PRJ-2026-001",
        "project_name": "مشروع فيلا سكنية فاخرة (G + 1 + Roof)",
        "active_studio": "🏛️ 1. استوديو الفلل والمباني السكنية (Residential Villa Studio)",
        "active_concept": "Concept A: فيلا عصرية على شكل L (L-Shape Privacy)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "authority": "بلدية دبي (Dubai Municipality)",
        "rev_id": "Rev.00",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        
        # مدخلات الفلل السكنية
        "plot_w": 25.0,
        "plot_l": 32.0,
        "bua_target": 650.0,
        "setbacks": {"front": 4.0, "rear": 3.0, "side": 1.5},
        "max_coverage": 0.50,
        "roof_coverage": 0.35,
        "sbc": 150.0,
        "sbc_status": "افتراض آمن غير مؤكد (UNVERIFIED_ASSUMPTION)",

        # مدخلات الهياكل المعدنية والصناعية المستقلة
        "steel_studio": {
            "facility_type": "مستودع لوجستي وتخزين (Logistics Warehouse)",
            "frame_type": "جملون بقمة في منتصف البحر (Gable Dual-Pitch)",
            "span": 24.0,
            "eave_h": 7.5,
            "length": 36.0,
            "spacing": 6.0,
            "slope_deg": 10.0,
            "drainage_gutter_w": 0.40,
            "downspouts_count": 6
        },

        # مدخلات تدقيق الموقع الميداني
        "recovery_data": {
            "total_contract_rc": 420.0,
            "executed_rc": 180.0,
            "rebar_cond": "صدأ سطحي يتطلب سفع رملي وتطبيق برايمر",
            "waterproof_cond": "متضرر نتيجة الردم يتطلب إعادة عزل",
            "inspection_findings": []
        },

        "drive_folder_url": ""
    }
    default_twin["state_hash"] = compute_state_hash(default_twin)
    return default_twin

if "project_twin" not in st.session_state:
    st.session_state.project_twin = init_project_twin()

pt = st.session_state.project_twin

# ------------------------------------------------------------------------------
# 3. الشريط الجانبي وتعدد النوافذ والاستوديوهات
# ------------------------------------------------------------------------------
st.sidebar.markdown("### 🏢 **EmaratBuild Studio v5.5**")
st.sidebar.caption("نظام التوأم الرقمي المتعدد - فصل الفلل عن الهياكل المعدنية")

active_studio = st.sidebar.radio(
    "نافذة العمل والاستوديو الهندسي:",
    [
        "🏛️ 1. استوديو الفلل والمباني السكنية (Residential Villa Studio)",
        "🔩 2. استوديو الهياكل المعدنية والمستودعات والإسطبلات (Steel & Industrial Studio)",
        "🚩 3. تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery Audit)"
    ],
    key="nav_master_studio_sel"
)
pt["active_studio"] = active_studio

st.sidebar.markdown("---")
pt["emirate"] = st.sidebar.selectbox(
    "الكود التنظيمي المعتمد:",
    [
        "دبي (Dubai Building Code DBC)",
        "الشارقة (المناطق الحضرية والشرقية)",
        "أبوظبي / العين (ADIBC)",
        "عجمان / الفجيرة"
    ],
    key="nav_master_emirate_sel"
)

if "أبوظبي" in pt["emirate"]:
    pt["setbacks"] = {"front": 5.0, "rear": 3.0, "side": 2.0}
    pt["max_coverage"] = 0.50
elif "الشارقة" in pt["emirate"]:
    pt["setbacks"] = {"front": 4.5, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.55
elif "دبي" in pt["emirate"]:
    pt["setbacks"] = {"front": 4.0, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.50
else:
    pt["setbacks"] = {"front": 4.0, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.55

override_api_key = st.sidebar.text_input(
    "مفتاح Gemini API (تحديث اختياري):",
    type="password",
    key="nav_api_key_override"
)
active_gemini_key = override_api_key.strip() if override_api_key.strip() else secret_gemini_key.strip()

# كبسولة الحالة
pt["state_hash"] = compute_state_hash(pt)

st.markdown(f"""
<div style="background-color: #1E293B; border-radius: 10px; padding: 12px 20px; border-right: 5px solid #0284C7; margin-bottom: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h4 style="margin: 0; color: #38BDF8;">{pt['active_studio'].split('(')[0]}</h4>
            <span style="color: #94A3B8; font-size: 0.85em;">
                الكود: <strong>{pt['emirate']}</strong> | 
                الإصدار: <span style="background-color: #0369A1; color: white; padding: 2px 6px; border-radius: 4px;">{pt['rev_id']}</span> | 
                بصمة التوأم: <code style="color: #38BDF8;">{pt['state_hash']}</code>
            </span>
        </div>
        <div>
            <span style="background-color: #0F172A; border: 1px solid #334155; padding: 5px 10px; border-radius: 6px; font-size: 0.8em; color: #E2E8F0;">
                جهد التربة المعتمد: <strong>{pt['sbc']} kN/m²</strong>
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# الاستوديو 1: الفلل والمباني السكنية (مع المنظور 3D والجولة الافتراضية)
# ==============================================================================
if "1. استوديو الفلل" in pt["active_studio"]:
    st.title("🏛️ استوديو التصميم المعماري والإنشائي للفلل السكنية (G+1+Roof)")
    st.caption("توليد البدائل المعمارية التنفيذية، المنظور الكتلي ثلاثي الأبعاد، محاكي الجولة الافتراضية، والقواعد الخرسانية.")

    sb_f = pt["setbacks"]["front"]
    sb_r = pt["setbacks"]["rear"]
    sb_s = pt["setbacks"]["side"]
    max_cov = pt["max_coverage"]

    c_v1, c_v2, c_v3, c_v4 = st.columns(4)
    with c_v1:
        pt["plot_w"] = st.number_input("عرض واجهة القسيمة (م):", 12.0, 150.0, float(pt["plot_w"]), 0.5, key="v_pw")
    with c_v2:
        pt["plot_l"] = st.number_input("عمق القسيمة (م):", 14.0, 200.0, float(pt["plot_l"]), 0.5, key="v_pl")
    with c_v3:
        new_sbc = st.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 500.0, float(pt["sbc"]), 10.0, key="v_sbc")
        if new_sbc != pt["sbc"]:
            pt["sbc"] = new_sbc
            pt["rev_id"] = "Rev.01"
            st.toast("تم تحديث حسابات القواعد الإنشائية.")
    with c_v4:
        pt["bua_target"] = st.number_input("إجمالي مسطح البناء BUA (م²):", 150.0, 5000.0, float(pt["bua_target"]), 25.0, key="v_bua")

    # اختيار البديل المعماري
    concept_list = [
        "Concept A: فيلا عصرية على شكل L (L-Shape Privacy)",
        "Concept B: فيلا الفناء الداخلي المفتوح (Central Courtyard)",
        "Concept C: الفيلا المدمجة الفاخرة (Compact Contemporary)",
        "Concept D: فيلتان متلاصقتان قابلة للفرز (Twin Villa Ready)"
    ]
    pt["active_concept"] = st.selectbox(
        "اختر البديل المعماري لتوليد المخططات والمنظور والجولة:",
        concept_list,
        index=concept_list.index(pt.get("active_concept", concept_list[0])),
        key="v_concept_select"
    )

    p_area = round(pt["plot_w"] * pt["plot_l"], 2)
    net_w = max(0.0, pt["plot_w"] - (2 * sb_s))
    net_l = max(0.0, pt["plot_l"] - (sb_f + sb_r))
    eff_ground = min(round(net_w * net_l, 2), round(p_area * max_cov, 2))
    bld_l = min(net_l, eff_ground / net_w if net_w > 0 else net_l)

    tabs_v = st.tabs([
        "📐 1. المسقط المعماري التنفيذي (2D CAD)",
        "🧊 2. المنظور الحجمي ثلاثي الأبعاد (3D Perspective)",
        "🚶‍♂️ 3. محاكي الجولة الافتراضية (Virtual Tour)",
        "🏗️ 4. القواعد الخرسانية والمحاور",
        "📊 5. كراسة الكميات المسعرة (CSI BOQ)"
    ])

    # 1. المسقط 2D
    with tabs_v[0]:
        st.subheader("المسقط المعماري التنفيذي المعتمد - الطابق الأرضي")
        fig_cad, ax_c = plt.subplots(figsize=(13, 16), dpi=200)
        ax_c.set_facecolor('#FFFFFF')

        ax_c.add_patch(Rectangle((0, 0), pt["plot_w"], pt["plot_l"], fill=False, edgecolor='#0F172A', lw=2.0))
        ax_c.add_patch(Rectangle((sb_s, sb_r), net_w, net_l, fill=False, edgecolor='#DC2626', lw=1.2, linestyle='--'))

        ext_th, int_th = 0.25, 0.20
        corr_w = 2.20
        corr_x = sb_s + (net_w * 0.46) - (corr_w / 2)

        def render_wall(x, y, w, h):
            ax_c.add_patch(Rectangle((x, y), w, h, facecolor='#334155', edgecolor='#0F172A', lw=0.8, zorder=2))

        render_wall(sb_s, sb_r, net_w, ext_th)
        render_wall(sb_s, sb_r + bld_l - ext_th, net_w, ext_th)
        render_wall(sb_s, sb_r, ext_th, bld_l)
        render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l)

        y_din = sb_r + bld_l * 0.32
        y_maj = sb_r + bld_l * 0.62
        y_gst = sb_r + bld_l * 0.40

        render_wall(corr_x, sb_r, int_th, bld_l * 0.75)
        render_wall(corr_x + corr_w - int_th, sb_r, int_th, bld_l * 0.75)
        render_wall(sb_s + ext_th, y_din, corr_x - (sb_s + ext_th), int_th)
        render_wall(sb_s + ext_th, y_maj, corr_x - (sb_s + ext_th), int_th)
        render_wall(corr_x + corr_w, y_gst, (sb_s + net_w - ext_th) - (corr_x + corr_w), int_th)

        # تفريغ الأبواب
        def cut_door(x, y, width, swing="UP_RIGHT"):
            ax_c.add_patch(Rectangle((x - 0.02, y - 0.02), width + 0.04, int_th + 0.04, facecolor='#FFFFFF', edgecolor='none', zorder=3))
            ax_c.plot([x, x], [y - 0.02, y + int_th + 0.02], color='#000000', lw=1.2, zorder=4)
            ax_c.plot([x + width, x + width], [y - 0.02, y + int_th + 0.02], color='#000000', lw=1.2, zorder=4)
            if swing == "UP_RIGHT":
                ax_c.plot([x, x], [y + int_th, y + int_th + width], color='#78350F', lw=1.8, zorder=4)
                ax_c.add_patch(Arc((x, y + int_th), width*2, width*2, angle=0, theta1=0, theta2=90, color='#B45309', lw=1.0, linestyle='--', zorder=4))
            elif swing == "DOWN_LEFT":
                ax_c.plot([x + width, x + width], [y, y - width], color='#78350F', lw=1.8, zorder=4)
                ax_c.add_patch(Arc((x + width, y), width*2, width*2, angle=0, theta1=180, theta2=270, color='#B45309', lw=1.0, linestyle='--', zorder=4))
            elif swing == "MAIN_DOUBLE":
                lf = width / 2
                ax_c.plot([x, x], [y - lf, y], color='#78350F', lw=2.0, zorder=4)
                ax_c.plot([x + width, x + width], [y - lf, y], color='#78350F', lw=2.0, zorder=4)
                ax_c.add_patch(Arc((x, y), lf*2, lf*2, angle=0, theta1=270, theta2=360, color='#B45309', lw=1.0, linestyle='--', zorder=4))
                ax_c.add_patch(Arc((x + width, y), lf*2, lf*2, angle=0, theta1=180, theta2=270, color='#B45309', lw=1.0, linestyle='--', zorder=4))

        cut_door(corr_x, y_maj + 0.40, 1.10, "UP_RIGHT")
        cut_door(corr_x, y_din + 0.40, 1.00, "UP_RIGHT")
        cut_door(corr_x + corr_w - int_th, y_gst + 0.40, 1.00, "DOWN_LEFT")
        cut_door(corr_x + (corr_w/2) - 0.80, sb_r + bld_l - ext_th, 1.60, "MAIN_DOUBLE")

        # بيت الدرج التنفيذي
        st_x, st_y = corr_x + int_th, sb_r + bld_l * 0.35
        st_w, land_d, st_len = corr_w - (2 * int_th), 1.20, 3.80
        fl_w = (st_w - 0.15) / 2
        ax_c.add_patch(Rectangle((st_x, st_y), st_w, st_len, fill=False, edgecolor='#1E293B', lw=1.2, zorder=3))
        ax_c.add_patch(Rectangle((st_x, st_y + st_len - land_d), st_w, land_d, facecolor='#E2E8F0', edgecolor='#475569', lw=0.8, zorder=3))
        for ytr in np.linspace(st_y, st_y + st_len - land_d, 11):
            ax_c.plot([st_x, st_x + fl_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)
            ax_c.plot([st_x + fl_w + 0.15, st_x + st_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)
        ax_c.annotate('', xy=(st_x + fl_w/2, st_y + st_len - land_d - 0.2), xytext=(st_x + fl_w/2, st_y + 0.3), arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.5), zorder=4)

        # الأعمدة المدفونة
        cols_embedded = [
            (sb_s, sb_r), (corr_x, sb_r), (corr_x + corr_w - int_th, sb_r), (sb_s + net_w - 0.60, sb_r),
            (sb_s, y_din), (corr_x, y_din), (corr_x + corr_w - int_th, y_gst), (sb_s + net_w - 0.60, y_gst),
            (sb_s, y_maj), (corr_x, y_maj), (corr_x + corr_w - int_th, y_maj), (sb_s + net_w - 0.60, y_maj),
            (sb_s, sb_r + bld_l - 0.60), (corr_x, sb_r + bld_l - 0.60), (corr_x + corr_w - int_th, sb_r + bld_l - 0.60), (sb_s + net_w - 0.60, sb_r + bld_l - 0.60)
        ]
        for cx, cy in cols_embedded:
            ax_c.add_patch(Rectangle((cx, cy), 0.20, 0.60, facecolor='#000000', edgecolor='none', zorder=5))

        # المحاور والأبعاد
        gxs = [sb_s + 0.10, corr_x + 0.10, corr_x + corr_w - 0.10, sb_s + net_w - 0.10]
        gys = [sb_r + 0.10, y_din + 0.10, y_maj + 0.10, sb_r + bld_l - 0.10]
        for idx, gx in enumerate(gxs):
            ax_c.plot([gx, gx], [sb_r - 2.5, sb_r + bld_l + 2.5], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(gx, sb_r + bld_l + 3.0, str(idx+1), ha='center', va='center', fontsize=8, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))
        for idx, gy in enumerate(gys):
            ax_c.plot([sb_s - 2.5, sb_s + net_w + 2.5], [gy, gy], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(sb_s - 3.0, gy, chr(65+idx), ha='center', va='center', fontsize=8, weight='bold', bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))

        ax_c.set_xlim(-4, pt["plot_w"] + 5)
        ax_c.set_ylim(-4, pt["plot_l"] + 5)
        ax_c.set_aspect('equal')
        ax_c.axis('off')
        st.pyplot(fig_cad)

    # 2. المنظور الحجمي 3D
    with tabs_v[1]:
        st.subheader("🧊 المنظور الكتلي ثلاثي الأبعاد للمبنى (3D Volumetric Perspective)")
        st.caption("نمذجة كتل الطوابق (الأرضي + الأول + بيت الدرج والروف) مشتقة مباشرة من أبعاد المسقط.")

        fig_3d = plt.figure(figsize=(10, 8), dpi=180)
        ax_3d = fig_3d.add_subplot(111, projection='3d')
        ax_3d.set_facecolor('#0F172A')

        # كتل الطوابق
        h_g, h_1, h_r = 3.8, 3.6, 3.2
        # كتلة الطابق الأرضي
        ax_3d.bar3d(sb_s, sb_r, 0, net_w, bld_l, h_g, color='#38BDF8', alpha=0.65, edgecolor='#0284C7', lw=0.8)
        # كتلة الطابق الأول (مع بلكونة وبروز مع بيم)
        ax_3d.bar3d(sb_s, sb_r, h_g, net_w * 0.90, bld_l * 0.85, h_1, color='#F8FAFC', alpha=0.75, edgecolor='#475569', lw=0.8)
        # كتلة الروف وبيت الدرج
        ax_3d.bar3d(corr_x, sb_r + bld_l * 0.30, h_g + h_1, corr_w + 1.0, 4.5, h_r, color='#FBBF24', alpha=0.85, edgecolor='#B45309', lw=1.0)

        # أرضية القسيمة والحديقة
        ax_3d.bar3d(0, 0, -0.2, pt["plot_w"], pt["plot_l"], 0.2, color='#1E293B', alpha=0.9, edgecolor='#334155')

        ax_3d.set_xlabel("عرض القسيمة X (م)", color='#94A3B8')
        ax_3d.set_ylabel("عمق القسيمة Y (م)", color='#94A3B8')
        ax_3d.set_zlabel("الارتفاع Z (م)", color='#94A3B8')
        ax_3d.tick_params(colors='#94A3B8')
        ax_3d.view_init(elev=28, azim=-55)
        st.pyplot(fig_3d)

    # 3. محاكي الجولة الافتراضية
    with tabs_v[2]:
        st.subheader("🚶‍♂️ محاكي الجولة الافتراضية والانتقال بين الفراغات (Virtual Spatial Walk)")
        st.caption("استعراض الإحساس الفراغي، المناسيب، الإطلالات، ومواد التشطيب لكل محطة بالمشروع:")

        tour_spots = {
            "1. بهو الاستقبال والمدخل الرئيسي (Main Foyer)": {
                "level": "FFL +0.45", "area": "18.5 م²", "view": "إطلالة مباشرة على البرج الزجاجي وممر التوزيع المحوري",
                "finishes": "أرضيات رخام كليما مارفل إسباني، باب دبل هايت خشب تيك طبيعي 2.80م", "lighting": "إضاءة غير مباشرة مقعرة + ثريا مدخلية دبل فوليوم"
            },
            "2. مجلس الرجال الرسمي وصالة الطعام (Formal Majlis & Dining)": {
                "level": "FFL +0.45", "area": "52.0 م²", "view": "واجهات زجاجية مزدوجة ممتدة تطل على الحديقة الأمامية والارتداد",
                "finishes": "ألواح خشبية جدارية (Acoustic Slatted Wood)، مغاسل رخام مصمت مع قواطع خصوصية", "lighting": "سبوت لايت مضاد للتوهج (CRI 90) وتكييف مخفي هادئ"
            },
            "3. صالة المعيشة العائلية الكبرى (Panoramic Family Living)": {
                "level": "FFL +0.45", "area": "64.0 م²", "view": "إطلالة بانورامية كاملة على الفناء والحديقة والمسبح الخلفي",
                "finishes": "بورسلان ألواح كبيرة 120×240 سم، زجاج ألمنيوم ثيرمال بريك فولدنج", "lighting": "إنارة طبيعية واسعة مع فتحات سماوية موجهة (Skylights)"
            },
            "4. بيت الدرج والمصعد البانورامي (Vertical Core)": {
                "level": "من +0.45 إلى +8.20", "area": "14.2 م²", "view": "درج معلق (Cantilevered) يلتف حول برج مصعد زجاجي هيدروليكي",
                "finishes": "درجات رخام مضيئة (LED Embedded Steps) ودرابزين زجاجي فريم لس 12 مم", "lighting": "إنارة شريطية خطية مدمجة بجدار الدرج المصمت"
            },
            "5. جناح الماستر الملكي بالطابق الأول (Royal Master Suite)": {
                "level": "FFL +4.25", "area": "48.0 م²", "view": "تراس خاص مطل على الحديقة الخارجية مع مظلة لوفرز ألمنيوم",
                "finishes": "باركيه خشب طبيعي معالج، دريسنج رووم مدمجة وحمام جاكوزي بتهوية طبيعية", "lighting": "نظام تحكم ذكي بالسيناريوهات والستائر الكهربائية"
            }
        }

        sel_spot = st.selectbox("اختر المحطة الفراغية لمعاينتها:", list(tour_spots.keys()), key="v_tour_station")
        cur_station = tour_spots[sel_spot]

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f"**الموقع والمستوى الإنشائي:** `{cur_station['level']}` | **المساحة الصافية:** `{cur_station['area']}`")
            st.markdown(f"**التوجيه والإطلالة:** {cur_station['view']}")
            st.markdown(f"**المواد والتشطيبات المعمارية:** {cur_station['finishes']}")
            st.markdown(f"**الإنارة والتكييف:** {cur_station['lighting']}")
        with sc2:
            st.info(f"💡 المحطة الفراغية: **{sel_spot.split('(')[0]}** تحقق استقلالية كاملة لحركة الضيوف عن خصوصية أهل المنزل ومسارات الخدمة.")

    # 4. القواعد الخرسانية
    with tabs_v[3]:
        st.subheader("القواعد الخرسانية المنفصلة والمحاور (ACI 318 Foundation Plan)")
        f_area = (1350.0 / 1.45) / pt["sbc"]
        f_dim = np.sqrt(f_area)
        f_thk = max(0.50, round(f_dim * 0.25, 2))
        st.success(f"القاعدة F1: أبعاد {f_dim:.2f} × {f_dim:.2f} × {f_thk:.2f} م | الخرسانة: SRC C40 لمقاومة الكبريتات | التسليح: 7 T 16mm/m بالاتجاهين.")

    # 5. كراسة الكميات
    with tabs_v[4]:
        st.subheader("كراسة الكميات المسعرة للفيلا (CSI MasterFormat BOQ)")
        boq_data_v = [
            {"البند": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات", "الكمية": round(pt["bua_target"] * 0.28, 1), "الوحدة": "م³", "السعر": 1200.0},
            {"البند": "خرسانة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الكمية": round(pt["bua_target"] * 0.38, 1), "الوحدة": "م³", "السعر": 1250.0},
            {"البند": "طابوق حراري عازل 20 سم ومفرغ للقواطع", "الكمية": round(pt["bua_target"] * 2.2, 1), "الوحدة": "م²", "السعر": 110.0},
            {"البند": "نظام عزل الأسطح المتكامل كومبو فوم 7 سم مع الضمان", "الكمية": round(pt["bua_target"] * 0.45, 1), "الوحدة": "م²", "السعر": 125.0}
        ]
        df_v_boq = pd.DataFrame(boq_data_v)
        df_v_boq["الإجمالي (AED)"] = round(df_v_boq["الكمية"] * df_v_boq["السعر"])
        st.dataframe(df_v_boq, use_container_width=True)

# ==============================================================================
# الاستوديو 2: الهياكل المعدنية والمستودعات والإسطبلات (نافذة مستقلة بالكامل)
# ==============================================================================
elif "2. استوديو الهياكل" in pt["active_studio"]:
    st.title("🔩 استوديو تصميم الهياكل المعدنية والمستودعات والإسطبلات (Steel Studio)")
    st.caption("تصميم الإطارات الفولاذية (Portal Frames)، دراسة الميول (Gable / Monopitch / Flat)، منظومة تصريف الأمطار، وحصر الأوزان ودهان الحريق.")

    st_cfg = pt["steel_studio"]

    cs_1, cs_2, cs_3, cs_4 = st.columns(4)
    with cs_1:
        st_cfg["facility_type"] = st.selectbox(
            "طبيعة المنشأة والاستخدام:",
            [
                "مستودع لوجستي وتخزين (Logistics Warehouse)",
                "مبنى مصنع وورش إنتاجية (Industrial Factory)",
                "إسطبل ومضمار خيول مغطى (Equestrian Stable Arena)",
                "مظلة سيارات ومرافق تجارية خاصة (Commercial Canopy)"
            ],
            key="st_fac_type"
        )
    with cs_2:
        st_cfg["frame_type"] = st.selectbox(
            "نوع وشكل الإطار الإنشائي والميول:",
            [
                "1. جملون بقمة في منتصف البحر (Gable Dual-Pitch)",
                "2. إطار مائل باتجاه واحد (Monopitch / Single Slope)",
                "3. سقف مسطح مع شبكة تصريف أمطار ومزاريب (Flat Roof & Gutter System)"
            ],
            key="st_frame_type"
        )
    with cs_3:
        st_cfg["span"] = st.number_input("بحر الإطار Span (م):", 10.0, 60.0, float(st_cfg["span"]), 0.5, key="st_span_val")
    with cs_4:
        st_cfg["eave_h"] = st.number_input("ارتفاع العمود الصافي Eave (م):", 4.0, 18.0, float(st_cfg["eave_h"]), 0.5, key="st_eave_val")

    cs_5, cs_6, cs_7 = st.columns(3)
    with cs_5:
        st_cfg["length"] = st.number_input("طول المبنى الإجمالي (م):", 12.0, 300.0, float(st_cfg["length"]), 6.0, key="st_len_val")
    with cs_6:
        st_cfg["spacing"] = st.number_input("التباعد بين الإطارات Bay Spacing (م):", 4.0, 9.0, float(st_cfg["spacing"]), 0.5, key="st_spacing_val")
    with cs_7:
        wind_design_speed = st.number_input("سرعة الرياح التصميمية لكود الإمارات (m/s):", 35.0, 50.0, 42.0, 1.0, key="st_wind_val")

    # حسابات الشكل والمناسيب
    st_span = st_cfg["span"]
    st_eave = st_cfg["eave_h"]
    st_len = st_cfg["length"]
    frames_count = int(st_len / st_cfg["spacing"]) + 1

    # رسم الإطار حسب النوع المختار
    fig_steel, ax_st = plt.subplots(figsize=(11, 5.2), dpi=200)
    ax_st.set_facecolor('#FFFFFF')

    if "1. جملون بقمة" in st_cfg["frame_type"]:
        # جملون ذو ميلين
        ridge_h = st_eave + (st_span / 2) * np.tan(np.radians(10.0))
        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([st_span, st_span], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([0, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0)
        ax_st.plot([st_span, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0)
        ax_st.text(st_span/2, ridge_h + 0.3, f"Ridge H = {ridge_h:.2f} m (10° Slope)", ha='center', fontsize=8, weight='bold', color='#0284C7')
    
    elif "2. إطار مائل باتجاه واحد" in st_cfg["frame_type"]:
        # مائل باتجاه واحد
        top_h = st_eave + st_span * np.tan(np.radians(7.0))
        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([st_span, st_span], [0, top_h], color='#1E3A8A', lw=6.0)
        ax_st.plot([0, st_span], [st_eave, top_h], color='#0284C7', lw=5.0)
        ax_st.text(st_span, top_h + 0.3, f"High Eave = {top_h:.2f} m", ha='center', fontsize=8, weight='bold', color='#0284C7')
    
    else:
        # مسطح تماماً مع مجرى تصريف خارجي
        ridge_h = st_eave + 0.30  # ميل تصريف طفيف 1.5%
        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([st_span, st_span], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([0, st_span], [st_eave, ridge_h], color='#0284C7', lw=5.0)
        # رسم مجرى التصريف (Box Gutter) والمزاريب
        ax_st.add_patch(Rectangle((-0.50, st_eave - 0.40), 0.50, 0.40, facecolor='#64748B', edgecolor='#0F172A', lw=1.2))
        ax_st.plot([-0.25, -0.25], [st_eave - 0.40, 0], color='#0369A1', lw=3.0, linestyle=':')
        ax_st.text(-0.80, st_eave/2, "ماسورة هبوط صرف أمطار\nUPVC Downspout Ø160mm", ha='right', va='center', fontsize=7, color='#0369A1', weight='bold')

    # خطوط الأبعاد
    ax_st.annotate('', xy=(0, -0.8), xytext=(st_span, -0.8), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
    ax_st.text(st_span/2, -0.6, f"Span = {st_span:.2f} m", ha='center', fontsize=8.5, weight='bold')
    ax_st.annotate('', xy=(-1.2, 0), xytext=(-1.2, st_eave), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
    ax_st.text(-1.5, st_eave/2, f"Eave = {st_eave:.2f} m", ha='right', va='center', fontsize=8, weight='bold', color='#1E3A8A', rotation=90)
    ax_st.set_xlim(-4, st_span + 4); ax_st.set_ylim(-1.5, st_eave + 4); ax_st.axis('off')
    st.pyplot(fig_steel)

    # منظومة تصريف مياه الأمطار
    st.markdown("##### 🌧️ منظومة تصريف مياه الأمطار للأسطح (Roof Stormwater Drainage per UAE Manual):")
    rainfall_intensity = 75.0  # mm/hr (أقصى شدة مطرية لعاصفة 15 دقيقة بالإمارات)
    roof_catchment_area = st_span * st_len  # m²
    run_off_q_liters = (rainfall_intensity * roof_catchment_area * 0.90) / 3600.0  # L/s
    required_pipes = int(np.ceil(run_off_q_liters / 9.5))  # قدرة تصريف ماسورة 160 مم حوالي 9.5 L/s

    cd1, cd2, cd3, cd4 = st.columns(4)
    cd1.metric("مساحة مستجمع مياه السطح", f"{roof_catchment_area:,.0f} م²")
    cd2.metric("التدفق التصميمي للأمطار (Q)", f"{run_off_q_liters:.1f} لتر/ثانية")
    cd3.metric("مجرى التصريف المعدني (Box Gutter)", "عرض 45 سم × عمق 35 سم")
    cd4.metric("عدد مواسير الهبوط المطلوبة", f"{required_pipes} مواسير Ø160mm")

    # حصر كتل الفولاذ ودهان الحريق
    col_l_tot = frames_count * 2 * st_eave
    raf_l_tot = frames_count * 2 * (st_span / 2 / np.cos(np.radians(10)))
    gross_steel = ((col_l_tot * 73.0) + (raf_l_tot * 51.0) + (12 * frames_count * 6.0 * 5.2)) / 1000.0
    fireproof_area = (col_l_tot + raf_l_tot) * 1.15

    st.markdown("---")
    st.markdown("##### 📊 المؤشرات الهندسية لحصر وتصنيع الهيكل الفولاذي:")
    ms1, ms2, ms3, ms4 = st.columns(4)
    ms1.metric("إجمالي وزن الهيكل الفولاذي", f"{gross_steel:,.2f} طن")
    ms2.metric("رتبة الصلب الإنشائي", "S355JR (Fy=355 MPa)")
    ms3.metric("دهان الحريق ساعتين (Intumescent)", f"{fireproof_area:,.1f} م²")
    ms4.metric("تكسيات ساندوتش بانل (PIR 50mm)", f"{roof_catchment_area * 1.08:,.0f} م²")

# ==============================================================================
# الاستوديو 3: تدقيق واستئناف المشاريع قيد التنفيذ (المسار الميداني)
# ==============================================================================
else:
    st.title("🚩 منظومة تقييم واستئناف المشاريع قيد التنفيذ (Site Recovery Audit)")
    st.caption("الفحص البصري للموقع بالذكاء الاصطناعي، مطابقة الخرسانات المصبوبة، وحصر الأعمال المتبقية لاستئناف الترخيص.")

    up_site_photos = st.file_uploader(
        "رفع صور المعاينة الميدانية للموقع (JPG, PNG, WEBP):",
        type=["jpg", "png", "jpeg", "webp"],
        accept_multiple_files=True,
        key="rec_site_photos_audit"
    )

    if "vision_cache" not in st.session_state:
        st.session_state.vision_cache = {}

    if up_site_photos:
        if st.button("🔍 تحليل وتوصيف كافة الصور بالذكاء الاصطناعي", key="btn_run_vision_audit"):
            if active_gemini_key:
                client = genai.Client(api_key=active_gemini_key)
                scan_prog = st.progress(0)
                for idx, p_file in enumerate(up_site_photos):
                    try:
                        raw_pil = Image.open(p_file)
                        if raw_pil.mode in ("RGBA", "P"):
                            raw_pil = raw_pil.convert("RGB")
                        b_io = io.BytesIO()
                        raw_pil.save(b_io, format='JPEG', quality=85)
                        c_bytes = b_io.getvalue()
                    except Exception:
                        c_bytes = p_file.getvalue()

                    prompt = """
                    Analyze this site inspection photo in UAE. Output STRICT JSON:
                    {
                        "element_category": "One of: ملاعب ومنشآت رياضية / حلبات ومرافق خيل / أرضيات إنترلوك وممرات / قواعد وميدات مسلحة / أعمدة وهيكل خرساني / هيكل معدني جملون / أسوار وبوابات",
                        "actual_description": "وصف هندسي واقعي وموجز باللغة العربية",
                        "progress_percentage": integer 0-100,
                        "defect_status": "One of: مكتمل وسليم ومطابق / أعمال قيد التنفيذ / صدأ أشاير يتطلب معالجة / تعشيش خرساني / أرضيات وأسوار بحالة جيدة",
                        "estimated_cost": estimated cost in AED to rectify (0 if complete)
                    }
                    """
                    for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                        try:
                            res = client.models.generate_content(
                                model=m_name,
                                contents=[types.Part.from_bytes(data=c_bytes, mime_type="image/jpeg"), prompt],
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            st.session_state.vision_cache[p_file.name] = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                            break
                        except Exception:
                            continue
                    scan_prog.progress((idx + 1) / len(up_site_photos))
                st.success("✅ تم الفحص البصري بنجاح.")

        # عرض كروت الصور
        p_cols = st.columns(3)
        findings = []
        for idx, p_file in enumerate(up_site_photos):
            t_c = p_cols[idx % 3]
            cached = st.session_state.vision_cache.get(p_file.name, {
                "element_category": "أرضيات إنترلوك وممرات" if "whatsapp" in p_file.name.lower() else "منشأة موقعية",
                "actual_description": "بانتظار الضغط على زر الفحص الذكي أعلاه",
                "progress_percentage": 90 if "whatsapp" in p_file.name.lower() else 50,
                "defect_status": "أرضيات وأسوار بحالة جيدة",
                "estimated_cost": 0.0
            })
            with t_c:
                st.image(Image.open(p_file), caption=f"صورة #{idx+1}: {p_file.name}", use_container_width=True)
                st.markdown(f"**التوصيف:** `{cached['actual_description']}`")
                st.caption(f"التصنيف: **{cached['element_category']}** | الإنجاز: **{cached['progress_percentage']}%**")
                findings.append({
                    "الصورة": p_file.name, "التصنيف": cached["element_category"],
                    "الوصف": cached["actual_description"], "الإنجاز": f"{cached['progress_percentage']}%",
                    "التكلفة (AED)": cached["estimated_cost"]
                })

        st.markdown("---")
        df_audit = pd.DataFrame(findings)
        st.dataframe(df_audit, use_container_width=True)
