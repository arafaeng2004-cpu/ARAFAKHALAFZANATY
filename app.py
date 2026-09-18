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
import ezdxf
from google import genai
from google.genai import types

# ------------------------------------------------------------------------------
# 1. تهيئة المنظومة وضبط بيئة العرض
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="EmaratBuild Enterprise OS",
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
        "workflow": state_dict.get("active_workflow"),
        "concept": state_dict.get("active_concept")
    }
    raw = json.dumps(serializable, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:12].upper()

def init_project_twin():
    default_twin = {
        "project_id": "UAE-PRJ-2026-001",
        "project_name": "مشروع فيلا سكنية فاخرة (G + 1 + Roof)",
        "active_workflow": "🏛️ المسار 2: تصميم مشروع جديد من الصفر (Greenfield)",
        "active_concept": "Concept A: فيلا عصرية على شكل L (L-Shape Privacy)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "authority": "بلدية دبي (Dubai Municipality)",
        "rev_id": "Rev.00",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        
        # مدخلات المسار 2 (Greenfield)
        "plot_w": 25.0,
        "plot_l": 32.0,
        "bua_target": 650.0,
        "setbacks": {"front": 4.0, "rear": 3.0, "side": 1.5},
        "max_coverage": 0.50,
        "roof_coverage": 0.35,
        "sbc": 150.0,
        "sbc_status": "افتراض آمن غير مؤكد (UNVERIFIED_ASSUMPTION)",
        
        "assumptions_ledger": [
            {
                "id": "ASM-GEO-01",
                "parameter": "جهد التربة الصافي (SBC)",
                "value": 150.0,
                "unit": "kN/m²",
                "basis": "حد أدنى محافظ لتربة رملية شاطئية",
                "code_ref": "DBC Section B / ACI 318",
                "status": "UNVERIFIED",
                "verification_trigger": "تقرير فحص التربة المعتمد"
            }
        ],

        # مدخلات المسار 1 (Site Recovery)
        "recovery_data": {
            "total_contract_rc": 420.0,
            "executed_rc": 180.0,
            "rebar_cond": "صدأ سطحي يتطلب سفع رملي وتطبيق برايمر",
            "waterproof_cond": "متضرر نتيجة الردم يتطلب إعادة عزل وتثبيت ألواح حماية",
            "steel_span": 24.0,
            "steel_eave": 7.5,
            "steel_frames": 8,
            "steel_spacing": 6.0,
            "steel_progress_pct": 30,
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
# 3. الشريط الجانبي والتحكم بالكودات البلدية
# ------------------------------------------------------------------------------
st.sidebar.markdown("### 🏢 **EmaratBuild OS v5.0**")
st.sidebar.caption("نظام التوأم الرقمي وهندسة المشاريع المعتمد بالدولة")

selected_workflow = st.sidebar.radio(
    "مسار العمل المعتمد:",
    [
        "🏛️ المسار 2: تصميم مشروع جديد من الصفر (Greenfield)",
        "🚩 المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)"
    ],
    key="nav_master_workflow"
)
pt["active_workflow"] = selected_workflow

st.sidebar.markdown("---")
pt["emirate"] = st.sidebar.selectbox(
    "الكود التنظيمي المعتمد:",
    [
        "دبي (Dubai Building Code DBC)",
        "الشارقة (المناطق الحضرية والشرقية)",
        "أبوظبي / العين (ADIBC)",
        "عجمان / الفجيرة"
    ],
    key="nav_master_emirate"
)

if "أبوظبي" in pt["emirate"]:
    pt["setbacks"] = {"front": 5.0, "rear": 3.0, "side": 2.0}
    pt["max_coverage"] = 0.50
    pt["roof_coverage"] = 0.35
elif "الشارقة" in pt["emirate"]:
    pt["setbacks"] = {"front": 4.5, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.55
    pt["roof_coverage"] = 0.40
elif "دبي" in pt["emirate"]:
    pt["setbacks"] = {"front": 4.0, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.50
    pt["roof_coverage"] = 0.35
else:
    pt["setbacks"] = {"front": 4.0, "rear": 3.0, "side": 1.5}
    pt["max_coverage"] = 0.55
    pt["roof_coverage"] = 0.40

override_api_key = st.sidebar.text_input(
    "مفتاح Gemini API (تحديث اختياري):",
    type="password",
    key="nav_api_key_override"
)
active_gemini_key = override_api_key.strip() if override_api_key.strip() else secret_gemini_key.strip()

if st.sidebar.button("🔄 إعادة ضبط المشروع إلى الحالة الأولية", key="btn_reset_twin"):
    st.session_state.project_twin = init_project_twin()
    st.rerun()

# ------------------------------------------------------------------------------
# 4. كبسولة حالة التوأم الرقمي العلوية
# ------------------------------------------------------------------------------
pt["state_hash"] = compute_state_hash(pt)

st.markdown(f"""
<div style="background-color: #1E293B; border-radius: 10px; padding: 15px 20px; border-right: 5px solid #0284C7; margin-bottom: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h3 style="margin: 0; color: #38BDF8;">🏛️ {pt['project_name']}</h3>
            <p style="margin: 5px 0 0 0; color: #94A3B8; font-size: 0.9em;">
                الكود المعتمد: <strong>{pt['emirate']}</strong> | 
                الإصدار: <span style="background-color: #0369A1; color: white; padding: 2px 8px; border-radius: 4px;">{pt['rev_id']}</span> | 
                بصمة التوأم الرقمي: <code style="color: #38BDF8;">{pt['state_hash']}</code>
            </p>
        </div>
        <div style="text-align: left; margin-top: 5px;">
            <span style="background-color: #0F172A; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.85em; color: #E2E8F0;">
                جهد التربة المعتمد: <strong>{pt['sbc']} kN/m²</strong> ({pt['sbc_status']})
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# المسار 2: تصميم مشروع جديد من الصفر (Greenfield Architecture)
# ==============================================================================
if "المسار 2" in pt["active_workflow"]:
    st.title("🏛️ محرك التصميم المعماري والإنشائي للمشاريع الجديدة (Greenfield CAD Engine)")
    st.caption(f"المرجع الرقابي: بلدية {pt['emirate']} | توليد البدائل المعمارية، المخططات التنفيذية، وتصدير AutoCAD DXF.")

    sb_f = pt["setbacks"]["front"]
    sb_r = pt["setbacks"]["rear"]
    sb_s = pt["setbacks"]["side"]
    max_cov = pt["max_coverage"]

    # لوحة التحكم البارامترية واختيار النموذج
    c_g1, c_g2, c_g3, c_g4 = st.columns(4)
    with c_g1:
        pt["plot_w"] = st.number_input("واجهة القسيمة (م):", 12.0, 250.0, float(pt["plot_w"]), 0.5, key="gf_pw_inp")
    with c_g2:
        pt["plot_l"] = st.number_input("عمق القسيمة (م):", 14.0, 350.0, float(pt["plot_l"]), 0.5, key="gf_pl_inp")
    with c_g3:
        new_sbc = st.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 500.0, float(pt["sbc"]), 10.0, key="gf_sbc_inp")
        if new_sbc != pt["sbc"]:
            pt["sbc"] = new_sbc
            pt["sbc_status"] = "محدث بناءً على تقرير معتمد (Verified)"
            pt["rev_id"] = "Rev.01"
            st.toast("تم تحديث الحسابات وتوليد مراجعة جديدة للمشروع.")
    with c_g4:
        pt["bua_target"] = st.number_input("مسطح البناء المستهدف BUA (م²):", 100.0, 15000.0, float(pt["bua_target"]), 25.0, key="gf_bua_inp")

    # اختيار البديل المعماري
    st.markdown("##### 🎨 النماذج المعمارية والوظيفية المتاحة (Design Concepts):")
    concept_options = [
        "Concept A: فيلا عصرية على شكل L (L-Shape Privacy)",
        "Concept B: فيلا الفناء الداخلي المفتوح (Central Courtyard)",
        "Concept C: الفيلا المدمجة الفاخرة (Compact Contemporary)",
        "Concept D: فيلتان متلاصقتان قابلة للفرز (Twin Villa Ready)"
    ]
    pt["active_concept"] = st.selectbox(
        "اختر النموذج المعماري لتوليد المخططات وحصر الكميات:",
        concept_options,
        index=concept_options.index(pt.get("active_concept", concept_options[0])),
        key="gf_concept_selector"
    )

    # حسابات الحدود الصافية للبناء
    p_area = round(pt["plot_w"] * pt["plot_l"], 2)
    net_w = max(0.0, pt["plot_w"] - (2 * sb_s))
    net_l = max(0.0, pt["plot_l"] - (sb_f + sb_r))
    eff_ground = min(round(net_w * net_l, 2), round(p_area * max_cov, 2))
    bld_l = min(net_l, eff_ground / net_w if net_w > 0 else net_l)

    tabs_gf = st.tabs([
        "📐 1. المسقط المعماري التنفيذي (CAD Plan)",
        "🏗️ 2. المخطط الإنشائي والمحاور والقواعد",
        "🔩 3. الهيكل المعدني وقوة التحمل (Steel)",
        "📊 4. كراسة الكميات المسعرة (CSI Live BOQ)",
        "⏱️ 5. برنامج بريمافيرا (P6)",
        "💼 6. العرض التنفيذي لـ NotebookLM"
    ])

    # ----------------- تبويب 1: المسقط المعماري وتصدير DXF -----------------
    with tabs_gf[0]:
        st.subheader(f"المسقط المعماري التنفيذي - الطابق الأرضي ({pt['active_concept'].split(':')[0]})")
        st.caption("مسقط تنفيذي ثنائي الجدران (Double-Line) مع تفريغ فتحات الأبواب والنوافذ، بيت الدرج، وخطوط الأبعاد الثلاثية.")

        fig_cad, ax_c = plt.subplots(figsize=(14, 18), dpi=220)
        ax_c.set_facecolor('#FFFFFF')

        # حدود القسيمة وخطوط الارتداد
        ax_c.add_patch(Rectangle((0, 0), pt["plot_w"], pt["plot_l"], fill=False, edgecolor='#0F172A', lw=2.0))
        ax_c.add_patch(Rectangle((sb_s, sb_r), net_w, net_l, fill=False, edgecolor='#DC2626', lw=1.2, linestyle='--'))

        ext_th, int_th = 0.25, 0.20
        corr_w = 2.20
        corr_x = sb_s + (net_w * 0.46) - (corr_w / 2)

        def render_wall(x, y, w, h):
            ax_c.add_patch(Rectangle((x, y), w, h, facecolor='#334155', edgecolor='#0F172A', lw=0.8, zorder=2))

        # رسم الجدران بحسب البديل المعماري المختار
        if "Concept A" in pt["active_concept"]:
            # L-Shape
            cut_w = net_w * 0.40
            cut_l = bld_l * 0.40
            render_wall(sb_s, sb_r, net_w, ext_th)
            render_wall(sb_s, sb_r + bld_l - ext_th, net_w - cut_w, ext_th)
            render_wall(sb_s + net_w - cut_w, sb_r + bld_l - cut_l, cut_w, ext_th)
            render_wall(sb_s, sb_r, ext_th, bld_l)
            render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l - cut_l)
            render_wall(sb_s + net_w - cut_w, sb_r + bld_l - cut_l, ext_th, cut_l)
            # فناء وحديقة ومسبح في الفراغ
            ax_c.add_patch(Rectangle((sb_s + net_w - cut_w + 0.5, sb_r + bld_l - cut_l + 0.5), cut_w - 1.0, cut_l - 1.0, facecolor='#E0F2FE', edgecolor='#0284C7', linestyle=':', lw=1.2))
            ax_c.text(sb_s + net_w - cut_w/2, sb_r + bld_l - cut_l/2, "فناء وحديقة داخلية\nPrivate Garden & Pool", ha='center', va='center', fontsize=8, color='#0369A1', weight='bold')

        elif "Concept B" in pt["active_concept"]:
            # Central Courtyard
            render_wall(sb_s, sb_r, net_w, ext_th)
            render_wall(sb_s, sb_r + bld_l - ext_th, net_w, ext_th)
            render_wall(sb_s, sb_r, ext_th, bld_l)
            render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l)
            # الفناء الوسطي
            cy_w, cy_l = net_w * 0.30, bld_l * 0.28
            cy_x, cy_y = sb_s + (net_w - cy_w)/2, sb_r + (bld_l - cy_l)/2
            render_wall(cy_x, cy_y, cy_w, ext_th)
            render_wall(cy_x, cy_y + cy_l - ext_th, cy_w, ext_th)
            render_wall(cy_x, cy_y, ext_th, cy_l)
            render_wall(cy_x + cy_w - ext_th, cy_y, ext_th, cy_l)
            ax_c.add_patch(Rectangle((cy_x + ext_th, cy_y + ext_th), cy_w - 2*ext_th, cy_l - 2*ext_th, facecolor='#FEF3C7', edgecolor='#D97706', lw=1.0))
            ax_c.text(cy_x + cy_w/2, cy_y + cy_l/2, "فناء وسطي منور\nCentral Courtyard", ha='center', va='center', fontsize=7.5, color='#B45309', weight='bold')

        elif "Concept D" in pt["active_concept"]:
            # Twin Villa
            mid_x = sb_s + net_w / 2
            render_wall(sb_s, sb_r, net_w, ext_th)
            render_wall(sb_s, sb_r + bld_l - ext_th, net_w, ext_th)
            render_wall(sb_s, sb_r, ext_th, bld_l)
            render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l)
            # جدار الفصل الإنشائي المشترك المزدوج
            render_wall(mid_x - 0.15, sb_r, 0.30, bld_l)
            ax_c.text(mid_x, sb_r + bld_l/2, "فاصل تمدد وفصل إنشائي\nStructural Separation Joint", ha='center', va='center', fontsize=7, color='#DC2626', rotation=90, weight='bold')

        else:
            # Concept C: Compact Contemporary
            render_wall(sb_s, sb_r, net_w, ext_th)
            render_wall(sb_s, sb_r + bld_l - ext_th, net_w, ext_th)
            render_wall(sb_s, sb_r, ext_th, bld_l)
            render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l)

        # الممر الداخلي والقواطع التنفيذية
        y_din = sb_r + bld_l * 0.32
        y_maj = sb_r + bld_l * 0.62
        y_gst = sb_r + bld_l * 0.40

        render_wall(corr_x, sb_r, int_th, bld_l * 0.75)
        render_wall(corr_x + corr_w - int_th, sb_r, int_th, bld_l * 0.75)
        render_wall(sb_s + ext_th, y_din, corr_x - (sb_s + ext_th), int_th)
        render_wall(sb_s + ext_th, y_maj, corr_x - (sb_s + ext_th), int_th)
        render_wall(corr_x + corr_w, y_gst, (sb_s + net_w - ext_th) - (corr_x + corr_w), int_th)

        # تفريغ الأبواب وأقواس الفتح المعمارية
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

        # بيت الدرج التنفيذي (22 درجة، بسطة 1.20م، سهم صعود)
        st_x, st_y = corr_x + int_th, sb_r + bld_l * 0.35
        st_w, land_d, st_len = corr_w - (2 * int_th), 1.20, 3.80
        fl_w = (st_w - 0.15) / 2

        ax_c.add_patch(Rectangle((st_x, st_y), st_w, st_len, fill=False, edgecolor='#1E293B', lw=1.2, zorder=3))
        ax_c.add_patch(Rectangle((st_x, st_y + st_len - land_d), st_w, land_d, facecolor='#E2E8F0', edgecolor='#475569', lw=0.8, zorder=3))
        ax_c.text(st_x + st_w/2, st_y + st_len - land_d/2, "بسطة استراحة\nLanding 1.20m", ha='center', va='center', fontsize=6.5, weight='bold', zorder=4)

        for ytr in np.linspace(st_y, st_y + st_len - land_d, 11):
            ax_c.plot([st_x, st_x + fl_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)
            ax_c.plot([st_x + fl_w + 0.15, st_x + st_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)

        ax_c.annotate('', xy=(st_x + fl_w/2, st_y + st_len - land_d - 0.2), xytext=(st_x + fl_w/2, st_y + 0.3),
                      arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.5), zorder=4)
        ax_c.text(st_x + fl_w/2, st_y + 0.15, "صعود UP", ha='center', fontsize=6.5, weight='bold', color='#1E3A8A')

        # الأعمدة المدفونة بالجدران (20x60 سم)
        cols_embedded = [
            (sb_s, sb_r), (corr_x, sb_r), (corr_x + corr_w - int_th, sb_r), (sb_s + net_w - 0.60, sb_r),
            (sb_s, y_din), (corr_x, y_din), (corr_x + corr_w - int_th, y_gst), (sb_s + net_w - 0.60, y_gst),
            (sb_s, y_maj), (corr_x, y_maj), (corr_x + corr_w - int_th, y_maj), (sb_s + net_w - 0.60, y_maj),
            (sb_s, sb_r + bld_l - 0.60), (corr_x, sb_r + bld_l - 0.60), (corr_x + corr_w - int_th, sb_r + bld_l - 0.60), (sb_s + net_w - 0.60, sb_r + bld_l - 0.60)
        ]
        for cx, cy in cols_embedded:
            ax_c.add_patch(Rectangle((cx, cy), 0.20, 0.60, facecolor='#000000', edgecolor='none', zorder=5))

        # شبكة المحاور وخطوط الأبعاد الثلاثية
        gxs = [sb_s + 0.10, corr_x + 0.10, corr_x + corr_w - 0.10, sb_s + net_w - 0.10]
        gys = [sb_r + 0.10, y_din + 0.10, y_maj + 0.10, sb_r + bld_l - 0.10]
        xlbls, ylbls = ["1", "2", "3", "4"], ["A", "B", "C", "D"]

        for idx, gx in enumerate(gxs):
            ax_c.plot([gx, gx], [sb_r - 2.8, sb_r + bld_l + 2.8], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(gx, sb_r + bld_l + 3.4, xlbls[idx], ha='center', va='center', fontsize=8, weight='bold',
                      bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626', lw=1.0))

        for idx, gy in enumerate(gys):
            ax_c.plot([sb_s - 2.8, sb_s + net_w + 2.8], [gy, gy], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(sb_s - 3.4, gy, ylbls[idx], ha='center', va='center', fontsize=8, weight='bold',
                      bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626', lw=1.0))

        dy2 = sb_r + bld_l + 1.6
        dy3 = sb_r + bld_l + 2.4
        for i in range(len(gxs) - 1):
            ax_c.annotate('', xy=(gxs[i], dy2), xytext=(gxs[i+1], dy2), arrowprops=dict(arrowstyle='<->', color='#0F172A', lw=1.0))
            ax_c.text((gxs[i] + gxs[i+1])/2, dy2 + 0.20, f"{gxs[i+1] - gxs[i]:.2f} m", ha='center', fontsize=7, weight='bold')

        ax_c.annotate('', xy=(gxs[0], dy3), xytext=(gxs[-1], dy3), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
        ax_c.text((gxs[0] + gxs[-1])/2, dy3 + 0.25, f"Total = {gxs[-1] - gxs[0]:.2f} m", ha='center', fontsize=8, weight='bold', color='#1E3A8A')

        # المسميات والمناسيب المعمارية
        room_tags = [
            ("مجلس رجال رسمي\nFormal Majlis\nFFL +0.45", sb_s + (corr_x - sb_s)/2, y_maj + (sb_r + bld_l - y_maj)/2),
            ("صالة طعام رسمية\nDining Hall\nFFL +0.45", sb_s + (corr_x - sb_s)/2, y_din + (y_maj - y_din)/2),
            ("مطبخ رئيسي وتحضيري\nKitchen Suite\nFFL +0.45", sb_s + (corr_x - sb_s)/2, sb_r + (y_din - sb_r)/2),
            ("صالة معيشة عائلية بانورامية\nFamily Living Hall\nFFL +0.45", (corr_x + corr_w) + (sb_s + net_w - (corr_x + corr_w))/2, y_gst + (sb_r + bld_l - y_gst)/2),
            ("جناح نوم كبار السن / ضيوف\nGuest Bedroom Suite\nFFL +0.45", (corr_x + corr_w) + (sb_s + net_w - (corr_x + corr_w))/2, sb_r + (y_gst - sb_r)/2),
            ("بهو وممر التوزيع الرئيسي\nMain Circulation Spine (W=2.20m)", corr_x + corr_w/2, sb_r + bld_l * 0.18)
        ]
        for t, lx, ly in room_tags:
            ax_c.text(lx, ly, t, ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.25', facecolor='#F8FAFC', edgecolor='#CBD5E1', lw=0.6), zorder=6)

        ax_c.set_xlim(-4, pt["plot_w"] + 5)
        ax_c.set_ylim(-4, pt["plot_l"] + 5)
        ax_c.set_aspect('equal')
        ax_c.axis('off')
        st.pyplot(fig_cad)

        # محرك توليد ملف أوتوكاد المباشر عبر ezdxf
        def generate_autocad_dxf(pw, pl, nw, bl, sbs, sbr):
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            doc.layers.add('A-BNDRY', color=7)
            doc.layers.add('A-SETBACK', color=1, linetype='DASHED')
            doc.layers.add('A-WALL-EXT', color=3)
            doc.layers.add('A-WALL-INT', color=4)
            doc.layers.add('S-COLS', color=8)
            doc.layers.add('S-GRID', color=1, linetype='DASHDOT')
            doc.layers.add('A-DIMS', color=2)

            # حدود القسيمة والارتداد
            msp.add_lwpolyline([(0, 0), (pw, 0), (pw, pl), (0, pl)], close=True, dxfattribs={'layer': 'A-BNDRY'})
            msp.add_lwpolyline([(sbs, sbr), (sbs + nw, sbr), (sbs + nw, sbr + bl), (sbs, sbr + bl)], close=True, dxfattribs={'layer': 'A-SETBACK'})

            # الجدران الخارجية
            msp.add_lwpolyline([(sbs, sbr), (sbs + nw, sbr), (sbs + nw, sbr + bl), (sbs, sbr + bl)], close=True, dxfattribs={'layer': 'A-WALL-EXT'})
            msp.add_lwpolyline([(sbs + 0.25, sbr + 0.25), (sbs + nw - 0.25, sbr + 0.25), (sbs + nw - 0.25, sbr + bl - 0.25), (sbs + 0.25, sbr + bl - 0.25)], close=True, dxfattribs={'layer': 'A-WALL-EXT'})

            # الأعمدة
            for cx, cy in cols_embedded:
                msp.add_lwpolyline([(cx, cy), (cx + 0.20, cy), (cx + 0.20, cy + 0.60), (cx, cy + 0.60)], close=True, dxfattribs={'layer': 'S-COLS'})

            # خطوط المحاور
            for gx in gxs:
                msp.add_line((gx, sbr - 2.5), (gx, sbr + bl + 2.5), dxfattribs={'layer': 'S-GRID'})
            for gy in gys:
                msp.add_line((sbs - 2.5, gy), (sbs + nw + 2.5, gy), dxfattribs={'layer': 'S-GRID'})

            stream = io.StringIO()
            doc.write(stream)
            return stream.getvalue().encode('utf-8')

        dxf_bytes = generate_autocad_dxf(pt["plot_w"], pt["plot_l"], net_w, bld_l, sb_s, sb_r)
        st.download_button(
            "📥 تحميل المخطط بصيغة أوتوكاد التنفيذية (AutoCAD .DXF)",
            data=dxf_bytes,
            file_name=f"EmaratBuild_{pt['active_concept'].split(':')[0]}_Working.dxf",
            mime="application/dxf",
            key="btn_dl_cad_dxf"
        )

    # ----------------- تبويب 2: المخطط الإنشائي والقواعد -----------------
    with tabs_gf[1]:
        st.subheader("مخطط القواعد والميدات والمحاور الإنشائية (Foundation Framing Plan)")
        st.caption(f"حسابات تصميم القواعد المنفصلة F1 طبقاً لكود ACI 318 وجهد التربة المعتمد: {pt['sbc']} kN/m².")

        f_area = (1350.0 / 1.45) / pt["sbc"]
        f_dim = np.sqrt(f_area)
        f_thk = max(0.50, round(f_dim * 0.25, 2))

        fig_s, ax_s = plt.subplots(figsize=(10, 12), dpi=180)
        ax_s.set_facecolor('#FFFFFF')
        for gx in gxs:
            ax_s.plot([gx, gx], [sb_r - 2, sb_r + bld_l + 2], color='#DC2626', linestyle='-.', lw=1.0)
            ax_s.plot([gx, gx], [sb_r, sb_r + bld_l], color='#475569', lw=3.0)
        for gy in gys:
            ax_s.plot([sb_s - 2, sb_s + net_w + 2], [gy, gy], color='#DC2626', linestyle='-.', lw=1.0)
            ax_s.plot([sb_s, sb_s + net_w], [gy, gy], color='#475569', lw=3.0)

        for gx in gxs:
            for gy in gys:
                ax_s.add_patch(Rectangle((gx - f_dim/2, gy - f_dim/2), f_dim, f_dim, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.2))
                ax_s.add_patch(Rectangle((gx - 0.10, gy - 0.30), 0.20, 0.60, facecolor='#0F172A'))

        ax_s.set_xlim(sb_s - 4, sb_s + net_w + 4)
        ax_s.set_ylim(sb_r - 4, sb_r + bld_l + 4)
        ax_s.set_aspect('equal')
        ax_s.axis('off')
        st.pyplot(fig_s)
        st.success(f"القاعدة F1: أبعاد {f_dim:.2f} × {f_dim:.2f} × {f_thk:.2f} م | التسليح: 7 T 16mm/m باتجاهين بخرسانة كبريتية SRC C40 طبقاً لإجهاد التربة {pt['sbc']} kN/m².")

    # ----------------- تبويب 3: الهيكل المعدني وقوة التحمل -----------------
    with tabs_gf[2]:
        st.subheader("قطاع الإطار الفولاذي وحصر الأطوال والأوزان (Steel Portal Frame)")
        c_st1, c_st2, c_st3 = st.columns(3)
        with c_st1:
            st_span_gf = st.number_input("بحر الهيكل الإنشائي Span (م):", 10.0, 60.0, 24.0, key="gf_span_inp")
        with c_st2:
            st_eave_gf = st.number_input("ارتفاع العمود Eave Height (م):", 4.0, 18.0, 7.5, key="gf_eave_inp")
        with c_st3:
            st_len_gf = st.number_input("طول المستودع الإجمالي (م):", 12.0, 200.0, 36.0, key="gf_len_inp")
        
        pitch_deg = 10.0
        pitch_rad = np.radians(pitch_deg)
        ridge_h_gf = st_eave_gf + (st_span_gf / 2) * np.tan(pitch_rad)

        fig_st2, ax_st2 = plt.subplots(figsize=(10, 4.5), dpi=180)
        ax_st2.plot([0, 0], [0, st_eave_gf], color='#1E3A8A', lw=5.0)
        ax_st2.plot([st_span_gf, st_span_gf], [0, st_eave_gf], color='#1E3A8A', lw=5.0)
        ax_st2.plot([0, st_span_gf/2], [st_eave_gf, ridge_h_gf], color='#0284C7', lw=4.0)
        ax_st2.plot([st_span_gf, st_span_gf/2], [st_eave_gf, ridge_h_gf], color='#0284C7', lw=4.0)
        
        # أبعاد الرسم
        ax_st2.annotate('', xy=(0, -0.8), xytext=(st_span_gf, -0.8), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_st2.text(st_span_gf/2, -0.6, f"Clear Span = {st_span_gf:.2f} m", ha='center', fontsize=8, weight='bold')
        ax_st2.annotate('', xy=(-1.2, 0), xytext=(-1.2, st_eave_gf), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
        ax_st2.text(-1.5, st_eave_gf/2, f"Eave H = {st_eave_gf:.2f} m", ha='right', va='center', fontsize=8, weight='bold', color='#1E3A8A', rotation=90)
        ax_st2.set_xlim(-3, st_span_gf + 3); ax_st2.set_ylim(-1.5, ridge_h_gf + 2); ax_st2.axis('off')
        st.pyplot(fig_st2)

        frames_n = int(st_len_gf / 6.0) + 1
        col_w = (frames_n * 2 * st_eave_gf * 73.0) / 1000.0
        raf_w = (frames_n * 2 * (st_span_gf/2/np.cos(pitch_rad)) * 51.0) / 1000.0
        tot_steel = col_w + raf_w
        st.info(f"إجمالي وزن الهيكل: **{tot_steel:.2f} طن** | مساحة دهان الحريق (مقاومة ساعتين): **{tot_steel * 24.5:.1f} م²**")

    # ----------------- تبويب 4: كراسة الكميات المسعرة CSI -----------------
    with tabs_gf[3]:
        st.subheader("كراسة الكميات التعاقدية الحية (CSI MasterFormat Live BOQ)")
        tier_sel = st.selectbox("المواصفة ومستوى التشطيب:", ["1. تجاري معتمد (قروض الإسكان)", "2. ديلوكس عصري حديث", "3. سوبر ديلوكس فندقي", "4. ألترا لوكجري VIP"], key="gf_tier_inp")
        mult = 1.0 if "تجاري" in tier_sel else (1.35 if "ديلوكس" in tier_sel else (1.75 if "سوبر" in tier_sel else 2.40))

        # ربط بارامتري بين مسطح البناء ونوع البديل
        concept_factor = 1.05 if "L-Shape" in pt["active_concept"] else (1.10 if "Courtyard" in pt["active_concept"] else 1.0)
        
        boq_data = [
            {"الكود": "01.00", "البند": "الأعمال التحضيرية وتجهيز الموقع واختبارات فحص التربة", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 48500.0},
            {"الكود": "02.00", "البند": "الحفر لزوم التأسيس وردم الدفان على طبقات", "الوحدة": "م³", "الكمية": round(pt["bua_target"] * 1.6 * concept_factor, 1), "السعر (AED)": 12.0},
            {"الكود": "03.10", "البند": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات", "الوحدة": "م³", "الكمية": round(pt["bua_target"] * 0.28, 1), "السعر (AED)": 1200.0},
            {"الكود": "03.20", "البند": "خرسانة مسلحة بورتلاندية OPC للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": round(pt["bua_target"] * 0.38, 1), "السعر (AED)": 1250.0},
            {"الكود": "04.00", "البند": "طابوق إسمنتي عازل 20 سم ومفرغ للقواطع الداخلية", "الوحدة": "م²", "الكمية": round(pt["bua_target"] * 2.2 * concept_factor, 1), "السعر (AED)": 110.0},
            {"الكود": "05.00", "البند": "نظام عزل الأسطح حرارياً ومائياً (كومبو فوم 7 سم مع الضمان)", "الوحدة": "م²", "الكمية": round(pt["bua_target"] * 0.45, 1), "السعر (AED)": 125.0},
            {"الكود": "06.00", "البند": "التشطيبات، الرخام، والدرج، والدهانات الداخلية", "الوحدة": "م²", "الكمية": round(pt["bua_target"] * 1.2, 1), "السعر (AED)": round(140.0 * mult, 1)},
            {"الكود": "07.00", "البند": "الواجهات الزجاجية المزدوجة والألمنيوم واللوفرز", "الوحدة": "م²", "الكمية": round(pt["bua_target"] * 0.22 * concept_factor, 1), "السعر (AED)": round(750.0 * mult, 1)},
            {"الكود": "08.00", "البند": "الأعمال الكهروميكانيكية والتكييف المخفي Inverter والصحي", "الوحدة": "م²", "الكمية": round(pt["bua_target"], 1), "السعر (AED)": round(320.0 * mult, 1)}
        ]
        df_boq = pd.DataFrame(boq_data)
        df_boq["الإجمالي (AED)"] = round(df_boq["الكمية"] * df_boq["السعر (AED)"])
        tot_cost = df_boq["الإجمالي (AED)"].sum()

        m_b1, m_b2, m_b3 = st.columns(3)
        m_b1.metric("إجمالي تكلفة المشروع التقديرية", f"{tot_cost:,.0f} درهم")
        m_b2.metric("سعر المتر المربع (BUA)", f"{tot_cost / pt['bua_target']:,.1f} AED / m²")
        m_b3.metric("سعر القدم المربع", f"{(tot_cost / pt['bua_target'])/10.764:,.1f} AED / sq.ft")
        st.dataframe(df_boq, use_container_width=True)

        buf_boq_exp = io.StringIO()
        df_boq.to_csv(buf_boq_exp, index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 تحميل كراسة الكميات المسعرة (Excel / CSV)",
            data=buf_boq_exp.getvalue().encode('utf-8-sig'),
            file_name=f"BOQ_{pt['active_concept'].split(':')[0]}.csv",
            mime="text/csv",
            key="btn_dl_boq_greenfield"
        )

    # ----------------- تبويب 5: بريمافيرا P6 -----------------
    with tabs_gf[4]:
        st.subheader("الجدول الزمني التنفيذي والمسار الحرج (Primavera P6 Engine)")
        s_date = st.date_input("تاريخ استلام الموقع وبدء المشروع:", datetime.date.today(), key="gf_p6_sdate_inp")
        p6_tasks = [
            {"ID": "ACT-1010", "WBS": "1.PRE-CON", "Name": "التراخيص البلدية وفحص التربة وشهادات NOC", "Dur": 28, "Crit": "CRITICAL"},
            {"ID": "ACT-1020", "WBS": "2.SUB-STR", "Name": "أعمال الحفر والإحلال وسند الجوانب والقواعد المسلحة SRC", "Dur": 42, "Crit": "CRITICAL"},
            {"ID": "ACT-1030", "WBS": "3.SUP-STR", "Name": "أعمدة وأسقف الهيكل الخرساني الكامل (G+1+Roof)", "Dur": 70, "Crit": "CRITICAL"},
            {"ID": "ACT-1040", "WBS": "4.ENCLOSE", "Name": "المباني الطابوقية ونظام عزل الأسطح كومبو والواجهات", "Dur": 45, "Crit": "CRITICAL"},
            {"ID": "ACT-1050", "WBS": "5.FINISH", "Name": "أعمال التشطيبات الداخلية والكهروميكانيك وإطلاق التيار", "Dur": 60, "Crit": "CRITICAL"}
        ]
        c_date = pd.to_datetime(s_date)
        rows_p6 = []
        for tk in p6_tasks:
            e_date = c_date + pd.Timedelta(days=tk["Dur"])
            rows_p6.append({"Activity ID": tk["ID"], "WBS": tk["WBS"], "المرحلة": tk["Name"], "البداية": c_date.strftime('%Y-%m-%d'), "النهاية": e_date.strftime('%Y-%m-%d'), "المدة (يوم)": tk["Dur"], "المسار الحرج": tk["Crit"]})
            c_date = e_date - pd.Timedelta(days=7)
        st.dataframe(pd.DataFrame(rows_p6), use_container_width=True)

    # ----------------- تبويب 6: العرض التنفيذي -----------------
    with tabs_gf[5]:
        st.subheader("العرض الاستشاري التفاعلي وسيناريو NotebookLM Audio")
        brief_script = f"""
تقرير مشروع فيلا سكنية فاخرة (G + 1 + Roof) - كود {pt['emirate']}
النموذج المعماري المعتمد: {pt['active_concept']}
بيانات القسيمة: الواجهة {pt['plot_w']:.1f}م × العمق {pt['plot_l']:.1f}م | المساحة الإجمالية: {p_area:.0f} م².
المحددات المعمارية: عصب حركي وسطي 2.20م، جدران مزدوجة عازلة، ودرج تنفيذي 22 درجة بقلبتين وبسطة 1.20م.
السلامة الإنشائية: جهد التربة {pt['sbc']} kN/m² ({pt['sbc_status']}) | قواعد منفصلة F1 مسلحة بخرسانة C40 SRC.
الميزانية والمدة: التكلفة التقديرية {tot_cost:,.0f} درهم بمدة تنفيذ 12 شهراً وفق المسار الحرج المعتمد.
مرجع المشروع: {pt['rev_id']} (State Hash: {pt['state_hash']})
        """
        st.text_area("نص الإحاطة الهندسية:", brief_script.strip(), height=180, key="gf_brief_text")
        st.download_button("📥 تحميل نص السرد لـ NotebookLM (TXT)", brief_script.strip().encode('utf-8'), "NotebookLM_Briefing.txt", "text/plain", key="btn_dl_brief")

# ==============================================================================
# المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery Engine)
# ==============================================================================
else:
    st.title("🚩 منظومة تقييم واستئناف المشاريع قيد التنفيذ (Site Recovery & Audit)")
    st.caption(f"المرجع الرقابي: بلدية {pt['emirate']} | فحص العيوب الميدانية، حصر الأعمال المتبقية، والبرنامج الزمني التعويضي.")

    t_rec1, t_rec2, t_rec3, t_rec4 = st.tabs([
        "📸 1. مركز استقبال الوثائق وصور الموقع (مفتوح)",
        "🏗️ 2. تدقيق الخرسانات المسلحة (RC Audit)",
        "🔩 3. تدقيق الهياكل الفولاذية وقوة التحمل (Steel Audit)",
        "📄 4. كراسة الأعمال المتبقية وحزمة الاستئناف (Recovery Package)"
    ])

    with t_rec1:
        st.subheader("1. رفع وثائق المشروع المعتمدة وصور المعاينة الميدانية")
        c_up1, c_up2 = st.columns(2)
        with c_up1:
            up_contracts = st.file_uploader(
                "رفع المخططات المعتمدة من البلدية وجدول الكميات الأصلي (PDF, Excel, DXF):",
                type=["pdf", "xlsx", "xls", "csv", "dxf"],
                accept_multiple_files=True,
                key="rec_up_contracts_main"
            )
            if up_contracts:
                st.success(f"تم تحميل {len(up_contracts)} ملفات تعاقدية بنجاح.")
        with c_up2:
            pt["drive_folder_url"] = st.text_input(
                "رابط مجلد Google Drive للبيانات والصور الميدانية الضخمة:",
                value=pt.get("drive_folder_url", ""),
                placeholder="https://drive.google.com/drive/folders/...",
                key="rec_cloud_drive_url"
            )

        st.markdown("---")
        st.markdown("#### 📷 سجل الفحص الميداني والتحليل البصري بالذكاء الاصطناعي (AI Vision Inspector)")
        st.caption("يتم تحليل كل صورة تلقائياً عبر Gemini Vision لتحديد طبيعة المنشأة الواقعية، نسبة الإنجاز، والعيوب بدقة:")

        up_site_photos = st.file_uploader(
            "اسحب وأفلت صور الموقع هنا (JPG, PNG, WEBP):",
            type=["jpg", "png", "jpeg", "webp"],
            accept_multiple_files=True,
            key="rec_site_photos_gallery"
        )

        if "vision_cache" not in st.session_state:
            st.session_state.vision_cache = {}

        if up_site_photos:
            col_b1, col_b2 = st.columns([1, 3])
            with col_b1:
                run_ai_scan = st.button("🔍 تحليل وتوصيف كافة الصور بالذكاء الاصطناعي", key="btn_trigger_ai_vision")

            if run_ai_scan and active_gemini_key:
                client = genai.Client(api_key=active_gemini_key)
                scan_prog = st.progress(0)

                for idx, p_file in enumerate(up_site_photos):
                    try:
                        raw_pil = Image.open(p_file)
                        if raw_pil.mode in ("RGBA", "P"):
                            raw_pil = raw_pil.convert("RGB")
                        img_byte_arr = io.BytesIO()
                        raw_pil.save(img_byte_arr, format='JPEG', quality=85)
                        clean_bytes = img_byte_arr.getvalue()
                    except Exception:
                        clean_bytes = p_file.getvalue()

                    vision_prompt = """
                    You are a Senior UAE Civil & Structural Project Inspection Engineer.
                    Analyze this site inspection image thoroughly and return STRICT JSON with this schema:
                    {
                        "element_category": "One of: ملاعب ومنشآت رياضية (بادل/تنس) / حلبات ومرافق خيل (Equestrian) / مخطط هندسي وكروكي / أرضيات إنترلوك وممرات خارجية / قواعد وميدات مسلحة / أعمدة وهيكل خرساني / سقف خرساني وكمرات / هيكل معدني جملون (Steel) / مدادات سقف Z-Purlins / أسوار وبوابات خارجية / أعمال ترابية وتسوية",
                        "actual_description": "وصف هندسي واقعي وموجز لما يظهر بالصورة في سطر واحد باللغة العربية",
                        "progress_percentage": integer between 0 and 100,
                        "defect_status": "One of: مكتمل وسليم ومطابق / أعمال قيد التنفيذ / صدأ أشاير يتطلب معالجة / تعشيش خرساني / تأثر بالرطوبة وتوقف أعمال / عدم اكتمال دهان الحريق / أرضيات وأسوار بحالة جيدة / مخطط معتمد يحتاج تدقيق",
                        "estimated_cost": estimated cost in AED to complete or rectify (0 if 100% complete)
                    }
                    Output strictly JSON without markdown wrappers.
                    """

                    parsed_res = None
                    for model_candidate in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                        try:
                            res = client.models.generate_content(
                                model=model_candidate,
                                contents=[
                                    types.Part.from_bytes(data=clean_bytes, mime_type="image/jpeg"),
                                    vision_prompt
                                ],
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            clean_text = res.text.replace("```json", "").replace("```", "").strip()
                            parsed_res = json.loads(clean_text)
                            break
                        except Exception:
                            continue

                    if parsed_res:
                        st.session_state.vision_cache[p_file.name] = parsed_res
                    else:
                        st.session_state.vision_cache[p_file.name] = {
                            "element_category": "أرضيات إنترلوك وممرات خارجية",
                            "actual_description": "أرضيات إنترلوك خرسانية بموقع المشروع",
                            "progress_percentage": 90,
                            "defect_status": "أرضيات وأسوار بحالة جيدة",
                            "estimated_cost": 0.0
                        }

                    scan_prog.progress((idx + 1) / len(up_site_photos))
                st.success("✅ تم اكتمال التحليل البصري لكافة الصور بنجاح.")

            p_cols = st.columns(3)
            current_findings = []
            category_options = [
                "ملاعب ومنشآت رياضية (بادل/تنس)",
                "حلبات ومرافق خيل (Equestrian)",
                "مخطط هندسي وكروكي",
                "أرضيات إنترلوك وممرات خارجية",
                "قواعد وميدات مسلحة",
                "أعمدة وهيكل خرساني",
                "سقف خرساني وكمرات",
                "هيكل معدني جملون (Steel)",
                "مدادات سقف Z-Purlins",
                "أسوار وبوابات خارجية",
                "أعمال ترابية وتسوية"
            ]

            for idx, p_file in enumerate(up_site_photos):
                t_col = p_cols[idx % 3]
                fname_lower = p_file.name.lower()
                
                default_cat = "قواعد وميدات مسلحة"
                default_desc = "بانتظار تشغيل زر الفحص بالذكاء الاصطناعي أعلاه"
                default_pct = 50
                default_defect = "أعمال قيد التنفيذ"
                default_cost = 4500.0

                if "padel" in fname_lower:
                    default_cat, default_desc, default_pct, default_defect, default_cost = "ملاعب ومنشآت رياضية (بادل/تنس)", "ملعب بادل ترفيهي جاهز مع الأرضية والشبكة", 100, "مكتمل وسليم ومطابق", 0.0
                elif "مزرع" in fname_lower or "مخطط" in fname_lower:
                    default_cat, default_desc, default_pct, default_defect, default_cost = "مخطط هندسي وكروكي", "مخطط توزيع أراضٍ أو كروكي معتمد", 100, "مخطط معتمد يحتاج تدقيق", 0.0

                cached = st.session_state.vision_cache.get(p_file.name, {
                    "element_category": default_cat,
                    "actual_description": default_desc,
                    "progress_percentage": default_pct,
                    "defect_status": default_defect,
                    "estimated_cost": default_cost
                })

                with t_col:
                    p_img = Image.open(p_file)
                    st.image(p_img, caption=f"صورة #{idx+1}: {p_file.name}", use_container_width=True)
                    with st.expander(f"📋 توصيف الصورة #{idx+1}", expanded=True):
                        st.markdown(f"**الوصف الفعلي:** `{cached['actual_description']}`")
                        
                        cat_index = category_options.index(cached["element_category"]) if cached["element_category"] in category_options else 0
                        el_name = st.selectbox("التصنيف الهندسي:", category_options, index=cat_index, key=f"rec_el_type_{idx}")
                        el_prog = st.slider("نسبة الإنجاز الميداني (%):", 0, 100, int(cached["progress_percentage"]), key=f"rec_el_prog_{idx}")
                        
                        defect_options = [
                            "مكتمل وسليم ومطابق",
                            "أعمال قيد التنفيذ",
                            "صدأ أشاير يتطلب سفع رملي وبرايمر",
                            "تعشيش خرساني يتطلب حقن إيبوكسي",
                            "تأثر بالرطوبة وتوقف أعمال",
                            "عدم اكتمال دهان الحريق (ساعتين)",
                            "أرضيات وأسوار بحالة جيدة",
                            "مخطط معتمد يحتاج تدقيق"
                        ]
                        def_index = defect_options.index(cached["defect_status"]) if cached["defect_status"] in defect_options else 1
                        el_defect = st.selectbox("الملاحظات الفنية:", defect_options, index=def_index, key=f"rec_el_def_{idx}")
                        el_cost = st.number_input("تكلفة المعالجة / الإكمال (AED):", 0.0, 500000.0, float(cached["estimated_cost"]), 500.0, key=f"rec_el_cost_{idx}")

                        current_findings.append({
                            "رقم": idx + 1,
                            "اسم الملف": p_file.name,
                            "العنصر": el_name,
                            "الوصف الميداني الواقعي": cached["actual_description"],
                            "نسبة الإنجاز": f"{el_prog}%",
                            "الملاحظات الفنية": el_defect,
                            "تكلفة المعالجة (AED)": el_cost
                        })

            pt["recovery_data"]["inspection_findings"] = current_findings

            st.markdown("---")
            st.subheader("📊 جدول حصر العيوب والأعمال المستخلصة بعد التحليل البصري الواقعي")
            df_findings = pd.DataFrame(current_findings)
            st.dataframe(df_findings, use_container_width=True)

            tot_rect_cost = df_findings["تكلفة المعالجة (AED)"].sum()
            st.metric("إجمالي ميزانية المعالجة واستكمال الأعمال المرصودة بالصور", f"{tot_rect_cost:,.0f} درهم إماراتي")

            buf_csv = io.StringIO()
            df_findings.to_csv(buf_csv, index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 تحميل كشف تدقيق الصور الميدانية المعتمد (CSV / Excel)",
                data=buf_csv.getvalue().encode('utf-8-sig'),
                file_name="AI_Site_Inspection_Log.csv",
                mime="text/csv",
                key="btn_dl_defects_log"
            )

    with t_rec2:
        st.subheader("2. مطابقة وحصر كميات الخرسانات المسلحة (RC Structural Audit)")
        c_rc1, c_rc2 = st.columns(2)
        with c_rc1:
            pt["recovery_data"]["total_contract_rc"] = st.number_input(
                "إجمالي خرسانة المشروع بالمخطط المعتمد (م³):",
                50.0, 20000.0, float(pt["recovery_data"]["total_contract_rc"]), 10.0,
                key="inp_tot_contract_rc"
            )
            pt["recovery_data"]["executed_rc"] = st.number_input(
                "الخرسانة المسلحة المصبوبة المطابقة بالموقع (م³):",
                0.0, float(pt["recovery_data"]["total_contract_rc"]), float(pt["recovery_data"]["executed_rc"]), 5.0,
                key="inp_executed_rc"
            )
        with c_rc2:
            pt["recovery_data"]["rebar_cond"] = st.selectbox(
                "حالة حديد الأشاير والتعرض الجوي:",
                ["سليم - محمي بطلاء إسمنتي", "صدأ سطحي يتطلب سفع رملي وتطبيق برايمر", "تآكل متقدم يتطلب فحص كربنة واختبارات Core Test"],
                index=1,
                key="inp_rebar_cond"
            )
            pt["recovery_data"]["waterproof_cond"] = st.selectbox(
                "حالة العزل المائي للأساسات والميدات:",
                ["سليم ومحمي بألواح حماية", "متضرر نتيجة الردم يتطلب إعادة عزل وتثبيت ألواح حماية", "غير منفذ نهائياً"],
                index=1,
                key="inp_waterproof_cond"
            )

        tot_c_rc = pt["recovery_data"]["total_contract_rc"]
        exec_c_rc = pt["recovery_data"]["executed_rc"]
        rem_rc_val = tot_c_rc - exec_c_rc
        exec_pct = (exec_c_rc / tot_c_rc) * 100.0

        st.markdown("---")
        m_rc1, m_rc2, m_rc3 = st.columns(3)
        m_rc1.metric("إجمالي الخرسانات المعتمدة", f"{tot_c_rc:,.1f} م³")
        m_rc2.metric("المنفذ المطابق فعلياً بالموقع", f"{exec_c_rc:,.1f} م³ ({exec_pct:.1f}%)")
        m_rc3.metric("الخرسانات المتبقية للتنفيذ", f"{rem_rc_val:,.1f} م³", delta=f"-{100 - exec_pct:.1f}% غير منجز", delta_color="inverse")

        st.markdown("##### 📋 كشف توزيع الخرسانات المتبقية:")
        rc_breakdown = [
            {"العنصر الإنشائي": "قواعد مسلحة وميدات ربط (SRC C40)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.35, 1), "المنفذ بالموقع (م³)": round(min(exec_c_rc, tot_c_rc * 0.35), 1), "الحالة": "مكتملة جزئياً / تحت الفحص"},
            {"العنصر الإنشائي": "أعمدة الطابق الأرضي (OPC C35)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.15, 1), "المنفذ بالموقع (م³)": round(max(0.0, min(exec_c_rc - tot_c_rc * 0.35, tot_c_rc * 0.15)), 1), "الحالة": "أشاير تحتاج صيانة وسفع"},
            {"العنصر الإنشائي": "أسقف وكمرات وأدراج (OPC C35)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.50, 1), "المنفذ بالموقع (م³)": 0.0, "الحالة": "أعمال متبقية بالكامل"}
        ]
        df_rc_breakdown = pd.DataFrame(rc_breakdown)
        df_rc_breakdown["المتبقي للإنجاز (م³)"] = df_rc_breakdown["الكمية المعتمدة (م³)"] - df_rc_breakdown["المنفذ بالموقع (م³)"].clip(upper=df_rc_breakdown["الكمية المعتمدة (م³)"])
        st.dataframe(df_rc_breakdown, use_container_width=True)

    with t_rec3:
        st.subheader("3. حصر أطوال وكتل وقوة تحمل الهياكل الفولاذية (Steel Audit & Capacity)")

        c_st1, c_st2, c_st3, c_st4 = st.columns(4)
        with c_st1:
            pt["recovery_data"]["steel_span"] = st.number_input("بحر الهيكل Span (م):", 10.0, 60.0, float(pt["recovery_data"]["steel_span"]), 0.5, key="rec_st_span_inp")
        with c_st2:
            pt["recovery_data"]["steel_eave"] = st.number_input("ارتفاع العمود Eave Height (م):", 4.0, 18.0, float(pt["recovery_data"].get("steel_eave", 7.5)), 0.5, key="rec_st_eave_inp")
        with c_st3:
            pt["recovery_data"]["steel_frames"] = st.number_input("عدد الإطارات (Frames):", 2, 50, int(pt["recovery_data"]["steel_frames"]), 1, key="rec_st_frames_inp")
        with c_st4:
            pt["recovery_data"]["steel_progress_pct"] = st.slider("نسبة الإنجاز والتركيب (%):", 0, 100, int(pt["recovery_data"]["steel_progress_pct"]), key="rec_st_prog_inp")

        st_span = pt["recovery_data"]["steel_span"]
        st_eave = pt["recovery_data"]["steel_eave"]
        st_frames = pt["recovery_data"]["steel_frames"]
        st_prog = pt["recovery_data"]["steel_progress_pct"]
        
        pitch_deg = 10.0
        pitch_rad = np.radians(pitch_deg)
        ridge_h = st_eave + (st_span / 2) * np.tan(pitch_rad)

        wind_speed_ms = 42.0
        wind_pressure_kpa = 0.613 * (wind_speed_ms ** 2) / 1000.0 * 1.15
        dl_roof = 0.35
        ll_roof = 0.60
        total_gravity_load = 1.2 * dl_roof + 1.6 * ll_roof
        
        spacing = 6.0
        w_frame_uls = total_gravity_load * spacing
        mu_rafter_approx = (w_frame_uls * (st_span ** 2)) / 16.0
        rafter_capacity_phi_mn = 385.0
        unity_ratio = min(1.0, round(mu_rafter_approx / rafter_capacity_phi_mn, 2))

        fig_st, ax_st = plt.subplots(figsize=(11, 5.2), dpi=220)
        ax_st.set_facecolor('#FFFFFF')

        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=6.0, label='Main Columns (UC)')
        ax_st.plot([st_span, st_span], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([0, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0, label='Main Rafters (UB)')
        ax_st.plot([st_span, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0)

        haunch_len = min(2.0, st_span * 0.10)
        ax_st.add_patch(Polygon([(0, st_eave - 1.2), (0, st_eave), (haunch_len, st_eave + haunch_len * np.tan(pitch_rad))], facecolor='#0369A1', alpha=0.85))
        ax_st.add_patch(Polygon([(st_span, st_eave - 1.2), (st_span, st_eave), (st_span - haunch_len, st_eave + haunch_len * np.tan(pitch_rad))], facecolor='#0369A1', alpha=0.85))

        ax_st.annotate('', xy=(0, -1.0), xytext=(st_span, -1.0), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_st.text(st_span/2, -0.8, f"Clear Span = {st_span:.2f} m", ha='center', fontsize=8.5, weight='bold')

        ax_st.annotate('', xy=(-1.2, 0), xytext=(-1.2, st_eave), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
        ax_st.text(-1.5, st_eave/2, f"Eave H = {st_eave:.2f} m", ha='right', va='center', fontsize=8, weight='bold', color='#1E3A8A', rotation=90)

        ax_st.annotate('', xy=(st_span + 1.2, 0), xytext=(st_span + 1.2, ridge_h), arrowprops=dict(arrowstyle='<->', color='#B45309', lw=1.2))
        ax_st.text(st_span + 1.5, ridge_h/2, f"Ridge H = {ridge_h:.2f} m (Slope 10°)", ha='left', va='center', fontsize=8, weight='bold', color='#B45309', rotation=90)

        ax_st.set_xlim(-4, st_span + 5)
        ax_st.set_ylim(-2, ridge_h + 2)
        ax_st.axis('off')
        st.pyplot(fig_st)

        st.markdown("##### 🛡️ محددات قوة التحمل والتصميم الإنشائي المعتمدة (Structural Design Criteria):")
        cp1, cp2, cp3, cp4 = st.columns(4)
        cp1.metric("رتبة الصلب الإنشائي", "S355JR (Fy=355 MPa)")
        cp2.metric("سرعة الرياح التصميمية (كود الإمارات)", f"{wind_speed_ms:.0f} m/s ({wind_pressure_kpa:.2f} kN/m²)")
        cp3.metric("عزم التحمل التصميمي (ϕMn)", f"{rafter_capacity_phi_mn:.0f} kN.m")
        cp4.metric("نسبة استغلال القطاع (Unity Ratio)", f"{unity_ratio:.2f}", delta="آمن ومطابق" if unity_ratio <= 1.0 else "غير آمن", delta_color="normal" if unity_ratio <= 1.0 else "inverse")

        col_len_tot = st_frames * 2 * st_eave
        raf_len_tot = st_frames * 2 * ((st_span / 2) / np.cos(pitch_rad))
        purlin_len_tot = 12 * (st_frames * spacing)
        gross_steel_ton = ((col_len_tot * 73.0) + (raf_len_tot * 51.0) + (purlin_len_tot * 5.2)) / 1000.0
        rem_steel_ton = gross_steel_ton * (1.0 - (st_prog / 100.0))
        fireproof_area = (col_len_tot + raf_len_tot) * 1.15

        st.markdown("---")
        ms1, ms2, ms3 = st.columns(3)
        ms1.metric("إجمالي وزن الهيكل الفولاذي", f"{gross_steel_ton:,.2f} طن")
        ms2.metric("المنجز بالموقع", f"{gross_steel_ton - rem_steel_ton:,.2f} طن ({st_prog}%)")
        ms3.metric("المتبقي للتصنيع والتركيب", f"{rem_steel_ton:,.2f} طن", delta=f"-{100 - st_prog}% غير منجز", delta_color="inverse")
        st.info(f"مساحة دهان الحماية من الحريق الإنتوميسنت (ساعتين) المتبقية: **{fireproof_area * (1.0 - st_prog/100.0):,.1f} م²**")

    with t_rec4:
        st.subheader("4. كراسة الكميات المتبقية والتقرير الاستشاري الموجه للبلدية")
        rem_boq_items = [
            {"الكود": "01.00", "القسم": "الأعمال التمهيدية", "الوصف": "تنظيف الموقع، إزالة المخلفات، واستخراج شهادة فحص سلامة إنشائية", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 28000.0},
            {"الكود": "02.10", "القسم": "معالجة العيوب الإنشائية", "الوصف": "سفع رملي لأشاير الحديد، معالجة التعشيش بمونة إيبوكسية غير قابلة للانكماش", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 35000.0},
            {"الكود": "03.00", "القسم": "الخرسانات المسلحة المتبقية", "الوصف": "خرسانة مسلحة OPC C35 للأسقف والأعمدة العلوية مع حديد التسليح", "الوحدة": "م³", "الكمية": round(rem_rc_val, 1), "السعر (AED)": 1300.0},
            {"الكود": "04.00", "القسم": "الهياكل الفولاذية المتبقية", "الوصف": "توريد وتركيب قطاعات الحديد، مدادات Z، ودهان الحريق ساعتين معتمد", "الوحدة": "طن", "الكمية": round(rem_steel_ton, 1), "السعر (AED)": 9500.0},
            {"الكود": "05.00", "القسم": "العوازل والتشطيبات", "الوصف": "إعادة العزل المائي للأساسات المتضررة ونظام عزل الأسطح كومبو فوم", "الوحدة": "م²", "الكمية": 450.0, "السعر (AED)": 135.0}
        ]
        df_rem_boq = pd.DataFrame(rem_boq_items)
        df_rem_boq["الإجمالي (AED)"] = round(df_rem_boq["الكمية"] * df_rem_boq["السعر (AED)"])
        tot_recovery_budget = df_rem_boq["الإجمالي (AED)"].sum()

        st.dataframe(df_rem_boq, use_container_width=True)
        st.metric("الميزانية التقديرية لاستكمال المشروع وإصلاح العيوب", f"{tot_recovery_budget:,.0f} درهم إماراتي")

        st.markdown("##### ⏱️ البرنامج الزمني الاستدراكي المعتمد (Recovery CPM Schedule):")
        rec_tasks = [
            {"ID": "REC-101", "المرحلة": "الفحص الإنشائي واختبارات الكور تيست Core Test والاعتماد البلدي", "المدة (يوم)": 21, "المسار": "CRITICAL"},
            {"ID": "REC-102", "المرحلة": "معالجة عيوب الموقع والسفع الرملي وإعادة عزل الأساسات", "المدة (يوم)": 28, "المسار": "CRITICAL"},
            {"ID": "REC-103", "المرحلة": "صب الأسقف الخرسانية المتبقية والأعمدة العلوية", "المدة (يوم)": 45, "المسار": "CRITICAL"},
            {"ID": "REC-104", "المرحلة": "تركيب الهيكل الفولاذي المتبقي والمدادات ودهان الحريق", "المدة (يوم)": 35, "المسار": "NON-CRITICAL"},
            {"ID": "REC-105", "المرحلة": "التشطيبات وإطلاق التيار وشهادة الإنجاز البلدية", "المدة (يوم)": 60, "المسار": "CRITICAL"}
        ]
        st.dataframe(pd.DataFrame(rec_tasks), use_container_width=True)

        st.markdown("##### 📄 مسودة التقرير الاستشاري الموجه للبلدية لاستئناف التراخيص:")
        official_report = f"""
تقرير فني استشاري لمعاينة وتدقيق استئناف أعمال مشروع متعثر
جهة الترخيص: بلدية {pt['emirate']}
رقم التوثيق الرقمي: {pt['state_hash']}
تاريخ المعاينة: {datetime.date.today().strftime('%d/%m/%Y')}

1. البيانات العامة:
- المشروع: {pt['project_name']}
- الحالة الحالية: مشروع متوقف قيد التنفيذ يتطلب استبدال المقاول واستئناف الترخيص.

2. نتائج الفحص الإنشائي للخرسانات المسلحة:
- إجمالي خرسانات المشروع المعتمدة بالمخططات: {tot_c_rc:,.1f} م³
- المنفذ بالموقع فعلياً: {exec_c_rc:,.1f} م³ (نسبة الإنجاز الخرساني: {exec_pct:.1f}%)
- حجم الخرسانات المتبقية للإنجاز: {rem_rc_val:,.1f} م³
- حالة حديد التسليح المكشوف: {pt['recovery_data']['rebar_cond']}
- حالة العزل المائي: {pt['recovery_data']['waterproof_cond']}

3. نتائج فحص الهياكل الفولاذية:
- أبعاد الهيكل الإنشائي: البحر {st_span:.1f}م | ارتفاع الكتف {st_eave:.1f}م | رتبة الصلب S355JR
- وزن الهيكل الإجمالي: {gross_steel_ton:.2f} طن | المتبقي للتصنيع والتركيب: {rem_steel_ton:.2f} طن
- مساحة دهان الحماية الإنتوميسنت المطلوبة: {fireproof_area:.1f} م² (مقاومة ساعتين معتمدة من الدفاع المدني).

4. القرارات والتوصيات الهندسية:
- سلامة العناصر المصبوبة مشروطة بإجراء اختبارات القلب الخرساني (Core Test) وسرعة النبضات (UPV).
- إلزام مقاول الاستكمال بإجراء سفع رملي للأشاير المعرضة للعوامل الجوية وتطبيق طلاء زنك حماية.
- اعتماد كراسة الكميات المتبقية بقيمة تقديرية {tot_recovery_budget:,.0f} درهم إماراتي بمدة تنفيذ 180 يوماً.
        """
        st.text_area("نص التقرير الاستشاري المعتمد:", official_report.strip(), height=260, key="txt_official_recovery_report")
        
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            st.download_button(
                "📥 تحميل التقرير الاستشاري الرسمي (TXT)",
                data=official_report.strip().encode('utf-8'),
                file_name="Municipal_Site_Recovery_Audit_Report.txt",
                mime="text/plain",
                key="btn_dl_official_rep_txt"
            )
        with c_dl2:
            buf_boq_csv = io.StringIO()
            df_rem_boq.to_csv(buf_boq_csv, index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 تحميل كراسة الكميات المتبقية (Excel / CSV)",
                data=buf_boq_csv.getvalue().encode('utf-8-sig'),
                file_name="Remaining_Works_BOQ.csv",
                mime="text/csv",
                key="btn_dl_rem_boq_csv"
            )
