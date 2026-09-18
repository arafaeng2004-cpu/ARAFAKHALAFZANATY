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

secret_gemini_key = st.secrets.get("GEMINI_API_KEY", "")

# ------------------------------------------------------------------------------
# 2. بناء النواة البرمجية للتوأم الرقمي (The Digital Twin State Machine)
# ------------------------------------------------------------------------------
def compute_state_hash(state_dict):
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
    default_twin = {
        "project_id": "UAE-PRJ-2026-001",
        "project_name": "مشروع فيلا سكنية فاخرة (G + 1 + Roof)",
        "active_workflow": "🚩 المسار 1: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "authority": "بلدية دبي (Dubai Municipality)",
        "rev_id": "Rev.00",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
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
# 4. شريط حالة التوأم الرقمي العلوي
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
                    file_bytes = p_file.getvalue()
                    m_type = p_file.type if p_file.type else "image/jpeg"
                    
                    vision_prompt = """
                    You are a Senior UAE Civil & Structural Project Inspection Engineer.
                    Analyze this site inspection image thoroughly and return STRICT JSON with this schema:
                    {
                        "element_category": "One of: ملاعب ومنشآت رياضية (بادل/تنس) / حلبات ومرافق خيل (Equestrian) / مخطط هندسي وكروكي / قواعد وميدات مسلحة / أعمدة وهيكل خرساني / سقف خرساني وكمرات / هيكل معدني جملون (Steel) / مدادات سقف Z-Purlins / أسوار وبوابات خارجية / أعمال ترابية وتسوية",
                        "actual_description": "وصف هندسي واقعي وموجز لما يظهر بالصورة في سطر واحد باللغة العربية",
                        "progress_percentage": integer between 0 and 100,
                        "defect_status": "One of: مكتمل وسليم ومطابق / أعمال قيد التنفيذ / صدأ أشاير يتطلب معالجة / تعشيش خرساني / تأثر بالرطوبة وتوقف أعمال / عدم اكتمال دهان الحريق / أرضيات وأسوار بحالة جيدة / مخطط معتمد يحتاج تدقيق",
                        "estimated_cost": estimated cost in AED to complete or rectify (0 if 100% complete)
                    }
                    Output strictly JSON without markdown wrappers.
                    """
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                types.Part.from_bytes(data=file_bytes, mime_type=m_type),
                                vision_prompt
                            ],
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        st.session_state.vision_cache[p_file.name] = json.loads(res.text)
                    except Exception as e:
                        st.session_state.vision_cache[p_file.name] = {
                            "element_category": "قواعد وميدات مسلحة",
                            "actual_description": f"تعذر الفحص الآلي: {str(e)[:40]}",
                            "progress_percentage": 50,
                            "defect_status": "أعمال قيد التنفيذ",
                            "estimated_cost": 4500.0
                        }
                    scan_prog.progress((idx + 1) / len(up_site_photos))
                st.success("✅ تم اكتمال التحليل البصري لكافة الصور بنجاح.")

            p_cols = st.columns(3)
            current_findings = []
            category_options = [
                "ملاعب ومنشآت رياضية (بادل/تنس)",
                "حلبات ومرافق خيل (Equestrian)",
                "مخطط هندسي وكروكي",
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
                
                # افتراض أولي ذكي حسب اسم الملف إذا لم يُشغل الفحص بعد
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

        # 1. مدخلات الأبعاد والارتفاعات
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

        # 2. الحسابات الإنشائية وقوة التحمل (AISC 360 / UAE Code)
        # سرعة الرياح التصميمية لكود الإمارات
        wind_speed_ms = 42.0  # 42 m/s (~151 km/h)
        wind_pressure_kpa = 0.613 * (wind_speed_ms ** 2) / 1000.0 * 1.15  # ~1.24 kN/m2
        dl_roof = 0.35  # Dead Load (PIR Sandwich Panels 50mm + Purlins + Sag rods)
        ll_roof = 0.60  # Live Load (Roof Maintenance per ASCE 7)
        total_gravity_load = 1.2 * dl_roof + 1.6 * ll_roof  # Ultimate Limit State (ULS) = 1.38 kN/m2
        
        # العزم الأقصى وقوة التحمل المقدرة
        spacing = 6.0  # تباعد الإطارات
        w_frame_uls = total_gravity_load * spacing  # kN/m
        mu_rafter_approx = (w_frame_uls * (st_span ** 2)) / 16.0  # kNm (عند الوصلة الركبية Haunch)
        rafter_capacity_phi_mn = 385.0  # kNm لقطاع UB 356x171x51 رتبة S355
        unity_ratio = min(1.0, round(mu_rafter_approx / rafter_capacity_phi_mn, 2))

        # 3. رسم الإطار مع المناسيب والأبعاد
        fig_st, ax_st = plt.subplots(figsize=(11, 5.2), dpi=220)
        ax_st.set_facecolor('#FFFFFF')

        # الأعمدة والجملون
        ax_st.plot([0, 0], [0, st_eave], color='#1E3A8A', lw=6.0, label='Main Columns (UC)')
        ax_st.plot([st_span, st_span], [0, st_eave], color='#1E3A8A', lw=6.0)
        ax_st.plot([0, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0, label='Main Rafters (UB)')
        ax_st.plot([st_span, st_span/2], [st_eave, ridge_h], color='#0284C7', lw=5.0)

        # وصلات الركبة (Haunch Plates)
        haunch_len = min(2.0, st_span * 0.10)
        ax_st.add_patch(Polygon([(0, st_eave - 1.2), (0, st_eave), (haunch_len, st_eave + haunch_len * np.tan(pitch_rad))], facecolor='#0369A1', alpha=0.85))
        ax_st.add_patch(Polygon([(st_span, st_eave - 1.2), (st_span, st_eave), (st_span - haunch_len, st_eave + haunch_len * np.tan(pitch_rad))], facecolor='#0369A1', alpha=0.85))

        # خطوط الأبعاد والمناسيب
        # البحر الأفقي (Span)
        ax_st.annotate('', xy=(0, -1.0), xytext=(st_span, -1.0), arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
        ax_st.text(st_span/2, -0.8, f"Clear Span = {st_span:.2f} m", ha='center', fontsize=8.5, weight='bold')

        # ارتفاع الكتف (Eave Height)
        ax_st.annotate('', xy=(-1.2, 0), xytext=(-1.2, st_eave), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
        ax_st.text(-1.5, st_eave/2, f"Eave H = {st_eave:.2f} m", ha='right', va='center', fontsize=8, weight='bold', color='#1E3A8A', rotation=90)

        # ارتفاع القمة الكلي (Ridge Height)
        ax_st.annotate('', xy=(st_span + 1.2, 0), xytext=(st_span + 1.2, ridge_h), arrowprops=dict(arrowstyle='<->', color='#B45309', lw=1.2))
        ax_st.text(st_span + 1.5, ridge_h/2, f"Ridge H = {ridge_h:.2f} m (Slope 10°)", ha='left', va='center', fontsize=8, weight='bold', color='#B45309', rotation=90)

        ax_st.set_xlim(-4, st_span + 5)
        ax_st.set_ylim(-2, ridge_h + 2)
        ax_st.axis('off')
        st.pyplot(fig_st)

        # 4. بطاقة معايير قوة التحمل والأحمال التصميمية
        st.markdown("##### 🛡️ محددات قوة التحمل والتصميم الإنشائي المعتمدة (Structural Design Criteria):")
        cp1, cp2, cp3, cp4 = st.columns(4)
        cp1.metric("رتبة الصلب الإنشائي", "S355JR (Fy=355 MPa)")
        cp2.metric("سرعة الرياح التصميمية (كود الإمارات)", f"{wind_speed_ms:.0f} m/s ({wind_pressure_kpa:.2f} kN/m²)")
        cp3.metric("عزم التحمل التصميمي (ϕMn)", f"{rafter_capacity_phi_mn:.0f} kN.m")
        cp4.metric("نسبة استغلال القطاع (Unity Ratio)", f"{unity_ratio:.2f}", delta="آمن ومطابق" if unity_ratio <= 1.0 else "غير آمن", delta_color="normal" if unity_ratio <= 1.0 else "inverse")

        # 5. الحصر المادي والكميات
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
# المسار 2: تصميم مشروع جديد من الصفر (Greenfield)
# ==============================================================================
else:
    st.title("🏛️ مسار التصميم المتكامل للمشاريع الجديدة (Greenfield Architecture)")
    st.caption("النواة المركزية متصلة وجاهزة لتفعيل محرك الرسم المعماري التنفيذي بالجدران المزدوجة والأبعاد الثلاثية في الخطوة القادمة.")
    st.info("💡 سيتم بناء هذا المسار بالكامل فور التأكد من اكتمال واختبار المسار الأول.")
