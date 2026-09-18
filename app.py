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
from google import genai
from google.genai import types

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
        "active_workflow": "🚩 المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "authority": "بلدية دبي (Dubai Municipality)",
        "rev_id": "Rev.00",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        
        # أبعاد الأرض والمحددات التنظيمية للمسار 2
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

        # بيانات المسار 1: تدقيق الموقع واستئناف الأعمال
        "recovery_data": {
            "total_contract_rc": 420.0,
            "executed_rc": 180.0,
            "rebar_cond": "صدأ سطحي يتطلب سفع رملي وتطبيق برايمر",
            "waterproof_cond": "متضرر نتيجة الردم يتطلب إعادة عزل وتثبيت ألواح حماية",
            "steel_span": 24.0,
            "steel_frames": 8,
            "steel_spacing": 6.0,
            "steel_eave": 7.5,
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
# 3. الشريط الجانبي وضبط محددات الكود
# ------------------------------------------------------------------------------
st.sidebar.markdown("### 🏢 **EmaratBuild Enterprise OS**")
st.sidebar.caption("نظام التوأم الرقمي وهندسة المشاريع المعتمد بالدولة")

selected_workflow = st.sidebar.radio(
    "مسار العمل المعتمد:",
    [
        "🚩 المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)",
        "🏛️ المسار 2: تصميم مشروع جديد من الصفر (Greenfield)"
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

# ضبط الارتدادات البلدية
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
                حالة جهد التربة: <strong>{pt['sbc']} kN/m²</strong> ({pt['sbc_status']})
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery Engine)
# ==============================================================================
if "المسار 1" in pt["active_workflow"]:
    st.title("🚩 منظومة تقييم واستئناف المشاريع قيد التنفيذ (Site Recovery & Audit)")
    st.caption(f"المرجع الرقابي: بلدية {pt['emirate']} | فحص العيوب الميدانية، حصر الأعمال المتبقية، وإعداد حزمة استئناف التراخيص.")

    t_rec1, t_rec2, t_rec3, t_rec4 = st.tabs([
        "📸 1. مركز استقبال الوثائق وصور الموقع (مفتوح)",
        "🏗️ 2. تدقيق الخرسانات المسلحة (RC Audit)",
        "🔩 3. تدقيق الهياكل الفولاذية (Steel Audit)",
        "📄 4. كراسة الأعمال المتبقية وحزمة الاستئناف (Recovery Package)"
    ])

    # ----------------- تبويب 1: الرفع غير المحدود وفحص الصور -----------------
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
        st.markdown("#### 📷 سجل الفحص الميداني التفاعلي للصور الموقعية (Photo Defect Logger)")
        st.caption("يتيح رفع عدد غير محدود من صور الموقع لمعاينة وتوصيف كل عنصر ورصد نسبة الإنجاز والعيوب وتكلفة المعالجة:")
        
        up_site_photos = st.file_uploader(
            "اسحب وأفلت صور الموقع هنا (JPG, PNG, WEBP):",
            type=["jpg", "png", "jpeg", "webp"],
            accept_multiple_files=True,
            key="rec_site_photos_gallery"
        )

        current_findings = []
        if up_site_photos:
            st.info(f"تم تحميل {len(up_site_photos)} صورة للموقع. قم بتوصيف العناصر بالبطاقات التالية:")
            p_cols = st.columns(3)
            
            for idx, p_file in enumerate(up_site_photos):
                t_col = p_cols[idx % 3]
                with t_col:
                    p_img = Image.open(p_file)
                    st.image(p_img, caption=f"صورة #{idx+1}: {p_file.name}", use_container_width=True)
                    with st.expander(f"⚙️ فحص وتوصيف الصورة #{idx+1}", expanded=True):
                        el_name = st.selectbox(
                            "العنصر الهندسي الظاهر:",
                            ["قواعد وميدات مسلحة", "أعمدة خرسانية", "سقف خرساني وكمرات", "هيكل فولاذي (أعمدة UC / رافتر UB)", "مدادات سقف Z-Purlins", "مباني طابوقية", "عزل مائي/حراري"],
                            key=f"rec_el_type_{idx}"
                        )
                        el_prog = st.select_slider(
                            "نسبة الإنجاز الميداني:",
                            ["0%", "25%", "50%", "75%", "100%"],
                            value="50%",
                            key=f"rec_el_prog_{idx}"
                        )
                        el_defect = st.selectbox(
                            "الملاحظات والعيوب الفنية:",
                            ["سليم ومطابق للمواصفات", "صدأ أشاير يتطلب سفع رملي وتطبيق برايمر", "تعشيش خرساني يتطلب تكسير وحقن إيبوكسي", "توقف أعمال وتأثر شديد بالرطوبة", "عدم اكتمال دهان الحريق (مقاومة ساعتين)", "أخطاء مناسيب"],
                            key=f"rec_el_def_{idx}"
                        )
                        el_cost = st.number_input(
                            "تكلفة المعالجة التقديرية (AED):",
                            0.0, 500000.0, 4500.0, 500.0,
                            key=f"rec_el_cost_{idx}"
                        )
                        current_findings.append({
                            "رقم": idx + 1,
                            "اسم الملف": p_file.name,
                            "العنصر": el_name,
                            "نسبة الإنجاز": el_prog,
                            "الملاحظات الفنية": el_defect,
                            "تكلفة المعالجة (AED)": el_cost
                        })

            pt["recovery_data"]["inspection_findings"] = current_findings

            st.markdown("---")
            st.subheader("📊 جدول حصر العيوب والأعمال المستخلصة من المعاينة الميدانية")
            df_findings = pd.DataFrame(current_findings)
            st.dataframe(df_findings, use_container_width=True)

            tot_rect_cost = df_findings["تكلفة المعالجة (AED)"].sum()
            st.metric("إجمالي ميزانية المعالجة واستكمال الأعمال المرصودة ميدانياً", f"{tot_rect_cost:,.0f} درهم إماراتي")

            buf_csv = io.StringIO()
            df_findings.to_csv(buf_csv, index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 تحميل كشف تدقيق الصور الميدانية (CSV / Excel)",
                data=buf_csv.getvalue().encode('utf-8-sig'),
                file_name="Site_Defects_Inspection_Log.csv",
                mime="text/csv",
                key="btn_dl_defects_log"
            )

    # ----------------- تبويب 2: تدقيق الخرسانات المسلحة -----------------
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

        # تفصيل العناصر المتبقية
        st.markdown("##### 📋 كشف توزيع الخرسانات المتبقية:")
        rc_breakdown = [
            {"العنصر الإنشائي": "قواعد مسلحة وميدات ربط (SRC C40)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.35, 1), "المنفذ بالموقع (م³)": round(min(exec_c_rc, tot_c_rc * 0.35), 1), "الحالة": "مكتملة جزئياً / تحت الفحص"},
            {"العنصر الإنشائي": "أعمدة الطابق الأرضي (OPC C35)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.15, 1), "المنفذ بالموقع (م³)": round(max(0.0, min(exec_c_rc - tot_c_rc * 0.35, tot_c_rc * 0.15)), 1), "الحالة": "أشاير تحتاج صيانة وسفع"},
            {"العنصر الإنشائي": "أسقف وكمرات وأدراج (OPC C35)", "الكمية المعتمدة (م³)": round(tot_c_rc * 0.50, 1), "المنفذ بالموقع (م³)": 0.0, "الحالة": "أعمال متبقية بالكامل"}
        ]
        df_rc_breakdown = pd.DataFrame(rc_breakdown)
        df_rc_breakdown["المتبقي للإنجاز (م³)"] = df_rc_breakdown["الكمية المعتمدة (م³)"] - df_rc_breakdown["المنفذ بالموقع (م³)"].clip(upper=df_rc_breakdown["الكمية المعتمدة (م³)"])
        st.dataframe(df_rc_breakdown, use_container_width=True)

    # ----------------- تبويب 3: تدقيق الهياكل الفولاذية -----------------
    with t_rec3:
        st.subheader("3. حصر أطوال وكتل الهياكل الفولاذية المتبقية (Steel Audit)")
        c_st1, c_st2, c_st3 = st.columns(3)
        with c_st1:
            pt["recovery_data"]["steel_span"] = st.number_input("بحر الهيكل الإنشائي Span (م):", 10.0, 60.0, float(pt["recovery_data"]["steel_span"]), key="rec_st_span_inp")
        with c_st2:
            pt["recovery_data"]["steel_frames"] = st.number_input("عدد الإطارات الإنشائية (Frames Count):", 2, 50, int(pt["recovery_data"]["steel_frames"]), key="rec_st_frames_inp")
        with c_st3:
            pt["recovery_data"]["steel_progress_pct"] = st.slider("نسبة تركيب وتثبيت الهيكل بالموقع (%):", 0, 100, int(pt["recovery_data"]["steel_progress_pct"]), key="rec_st_prog_inp")

        st_span = pt["recovery_data"]["steel_span"]
        st_frames = pt["recovery_data"]["steel_frames"]
        st_eave = pt["recovery_data"]["steel_eave"]
        st_prog = pt["recovery_data"]["steel_progress_pct"]
        pitch_rad = np.radians(10.0)
        ridge_h = st_eave + (st_span / 2) * np.tan(pitch_rad)

        # رسم قطاع الإطار
        fig_st, ax_st = plt.subplots(figsize=(10, 4.5), dpi=200)
        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=5.0, label='Main Columns (UC)')
        ax_st.plot([st_span, st_span], [0, st_eave], color='#1E3A8A', lw=5.0)
        ax_st.plot([0, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=4.0, label='Main Rafters (UB)')
        ax_st.plot([st_span, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=4.0)
        
        # علامات الارتفاعات والأبعاد
        ax_st.annotate('', xy=(0, -0.8), xytext=(st_span, -0.8), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_st.text(st_span/2, -0.6, f"Clear Span = {st_span:.1f} m", ha='center', fontsize=8, weight='bold')
        ax_st.set_xlim(-3, st_span + 3); ax_st.set_ylim(-1.5, ridge_h + 2); ax_st.axis('off')
        st.pyplot(fig_st)

        # حسابات الحصر الفولاذي
        col_len_tot = st_frames * 2 * st_eave
        raf_len_tot = st_frames * 2 * ((st_span / 2) / np.cos(pitch_rad))
        purlin_len_tot = 12 * (st_frames * 6.0)
        
        gross_steel_ton = ((col_len_tot * 73.0) + (raf_len_tot * 51.0) + (purlin_len_tot * 5.2)) / 1000.0
        rem_steel_ton = gross_steel_ton * (1.0 - (st_prog / 100.0))
        fireproof_area = (col_len_tot + raf_len_tot) * 1.15

        st.markdown("---")
        ms1, ms2, ms3 = st.columns(3)
        ms1.metric("إجمالي وزن الهيكل الفولاذي", f"{gross_steel_ton:,.2f} طن")
        ms2.metric("المنجز بالموقع", f"{gross_steel_ton - rem_steel_ton:,.2f} طن ({st_prog}%)")
        ms3.metric("المتبقي للتصنيع والتركيب", f"{rem_steel_ton:,.2f} طن", delta=f"-{100 - st_prog}% غير منجز", delta_color="inverse")
        st.info(f"مساحة دهان الحماية من الحريق الإنتوميسنت (ساعتين) المتبقية: **{fireproof_area * (1.0 - st_prog/100.0):,.1f} م²**")

    # ----------------- تبويب 4: حزمة الاستئناف المعتمدة -----------------
    with t_rec4:
        st.subheader("4. كراسة الكميات المتبقية والتقرير الاستشاري الموجه للبلدية")
        
        # جدول كراسة الكميات المتبقية المسعر
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

        # الجدول الزمني التعويضي لبريمافيرا
        st.markdown("##### ⏱️ البرنامج الزمني الاستدراكي المعتمد (Recovery CPM Schedule):")
        rec_tasks = [
            {"ID": "REC-101", "المرحلة": "الفحص الإنشائي واختبارات الكور تيست Core Test والاعتماد البلدي", "المدة (يوم)": 21, "المسار": "CRITICAL"},
            {"ID": "REC-102", "المرحلة": "معالجة عيوب الموقع والسفع الرملي وإعادة عزل الأساسات", "المدة (يوم)": 28, "المسار": "CRITICAL"},
            {"ID": "REC-103", "المرحلة": "صب الأسقف الخرسانية المتبقية والأعمدة العلوية", "المدة (يوم)": 45, "المسار": "CRITICAL"},
            {"ID": "REC-104", "المرحلة": "تركيب الهيكل الفولاذي المتبقي والمدادات ودهان الحريق", "المدة (يوم)": 35, "المسار": "NON-CRITICAL"},
            {"ID": "REC-105", "المرحلة": "التشطيبات وإطلاق التيار وشهادة الإنجاز البلدية", "المدة (يوم)": 60, "المسار": "CRITICAL"}
        ]
        st.dataframe(pd.DataFrame(rec_tasks), use_container_width=True)

        # التقرير الاستشاري الرسمي
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

# ==============================================================================
# المسار 2: تصميم مشروع جديد من الصفر (Greenfield - Placeholder for Step 4)
# ==============================================================================
else:
    st.title("🏛️ مسار التصميم المتكامل للمشاريع الجديدة (Greenfield Architecture)")
    st.caption("النواة المركزية متصلة وجاهزة لتفعيل محرك الرسم المعماري التنفيذي بالجدران المزدوجة والأبعاد الثلاثية في الخطوة القادمة.")
    st.info("💡 سيتم بناء هذا المسار بالكامل فور التأكد من اكتمال واختبار المسار الأول.")
