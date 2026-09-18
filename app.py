import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import datetime
import hashlib
from PIL import Image

# ------------------------------------------------------------------------------
# 1. تهيئة المنظومة وضبط بيئة العرض
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="EmaratBuild Studio - Digital Twin Core",
    layout="wide",
    initial_sidebar_state="expanded"
)

# جلب المفتاح السحابي المشفر
secret_gemini_key = st.secrets.get("GEMINI_API_KEY", "")

# ------------------------------------------------------------------------------
# 2. بناء النواة البرمجية للتوأم الرقمي (The Digital Twin State Machine)
# ------------------------------------------------------------------------------
def compute_state_hash(state_dict):
    """توليد بصمة تشفيرية لحالة المشروع لمنع تسليم وثائق قديمة"""
    serializable = {
        "plot_w": state_dict.get("plot_w"),
        "plot_l": state_dict.get("plot_l"),
        "sbc": state_dict.get("sbc"),
        "emirate": state_dict.get("emirate"),
        "rev_id": state_dict.get("rev_id")
    }
    raw = json.dumps(serializable, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:12].upper()

def init_project_twin():
    """تهيئة هيكل البيانات المركزي للمشروع (Single Source of Truth)"""
    default_twin = {
        "project_id": "UAE-PRJ-2026-001",
        "project_name": "مشروع فيلا سكنية فاخرة (G + 1 + Roof)",
        "active_workflow": "المسار 2: تصميم مشروع جديد من الصفر (Greenfield)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "authority": "بلدية دبي (Dubai Municipality)",
        "rev_id": "Rev.00",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        
        # أبعاد الأرض والمحددات التنظيمية
        "plot_w": 25.0,
        "plot_l": 32.0,
        "bua_target": 650.0,
        "setbacks": {"front": 4.0, "rear": 3.0, "side": 1.5},
        "max_coverage": 0.50,
        "roof_coverage": 0.35,

        # البيانات الجيوتقنية والافتراضات
        "sbc": 150.0,
        "sbc_status": "افتراض آمن غير مؤكد (UNVERIFIED_ASSUMPTION)",
        
        # سجل الافتراضات الهندسي
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

        # سجل مصادر المستندات
        "source_registry": [],

        # سجل مراجعات المشروع وتتبع الفروقات
        "revisions_log": [
            {
                "rev": "Rev.00",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": "إنشاء النسخة الأساسية للمشروع (Baseline)",
                "author": "System Engine"
            }
        ],

        # بيانات الهيكل الفولاذي
        "steel_params": {
            "span": 24.0,
            "length": 36.0,
            "eave_h": 7.5,
            "spacing": 6.0
        },

        # سجل تدقيق الموقع الميداني للمشاريع القائمة
        "recovery_data": {
            "total_contract_rc": 420.0,
            "executed_rc": 180.0,
            "structural_defects": [],
            "steel_progress_pct": 30
        },

        "drive_folder_url": ""
    }
    default_twin["state_hash"] = compute_state_hash(default_twin)
    return default_twin

if "project_twin" not in st.session_state:
    st.session_state.project_twin = init_project_twin()

pt = st.session_state.project_twin

# ------------------------------------------------------------------------------
# 3. الشريط الجانبي: محول المسارات وضبط كودات الإمارات
# ------------------------------------------------------------------------------
st.sidebar.markdown("### 🏢 **EmaratBuild Enterprise OS**")
st.sidebar.caption("نظام التوأم الرقمي وهندسة المشاريع المعتمد بالدولة")

# محول مسارات العمل الرئيسي
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

# تحديث الارتدادات البلدية آلياً بحسب الإمارة
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
# 4. كبسولة حالة التوأم الرقمي العلوية (Project Digital Twin Status Bar)
# ------------------------------------------------------------------------------
# تحديث البصمة الرقمية لحالة المشروع
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
                حالة جهد التربة: <strong>{pt['sbc']} kN/m²</strong> ({pt['sbc_status']})
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 5. تفريع مسارات العمل الأساسية للمنظومة
# ------------------------------------------------------------------------------
if "المسار 2" in pt["active_workflow"]:
    st.markdown("### 📐 مسار التصميم المتكامل للمشاريع الجديدة (Greenfield Architecture)")
    st.caption("النواة المركزية متصلة وجاهزة لتوليد المساقط التنفيذية، المخططات الإنشائية، كراسات الكميات، والعروض.")
    
    # بطاقة فحص سجل الافتراضات الحالية
    with st.expander("📑 سجل الافتراضات الهندسية النشطة (Assumptions Ledger)", expanded=False):
        df_assumptions = pd.DataFrame(pt["assumptions_ledger"])
        st.dataframe(df_assumptions, use_container_width=True)
        st.info("💡 أي تعديل لجهد التربة لاحقاً سيطلق تلقائياً حدث إعادة الحساب ويولد مراجعة Rev.01.")

    st.success("✅ النواة البرمجية للمسار الثاني جاهزة لاستقبال محرك الرسم التنفيذي بالخطوات القادمة.")

else:
    st.markdown("### 🚩 مسار تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery & Audit)")
    st.caption("النواة المركزية مهيأة لاستقبال المخططات المعتمدة، كراسة العقد، والمعرض غير المحدود لصور الموقع.")
    
    with st.expander("📋 حالة وثائق تدقيق الموقع المعتمدة", expanded=False):
        st.write(f"- إجمالي خرسانات العقد المعتمدة: **{pt['recovery_data']['total_contract_rc']} م³**")
        st.write(f"- الخرسانة المنجزة المطابقة: **{pt['recovery_data']['executed_rc']} م³**")
        st.write(f"- الأعمال المتبقية: **{pt['recovery_data']['total_contract_rc'] - pt['recovery_data']['executed_rc']} م³**")

    st.success("✅ النواة البرمجية للمسار الأول جاهزة لاستقبال منظومة فحص الصور ورصد العيوب.")
