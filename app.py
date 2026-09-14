import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Civil & Architectural Engineering Platform", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "")

# ----------------- اختيار الوحدة التشغيلية -----------------
st.sidebar.title("🛠️ منصة المهام الهندسية")
module_choice = st.sidebar.radio(
    "اختر وحدة العمل المطلوبة:",
    [
        "1. المنظومة المعمارية المتكاملة والتصدير (Full Design & 3D)",
        "2. محرك البرنامج الزمني والمسار الحرج (Schedule & Gantt)",
        "3. محرك حصر الكميات والتسعير لمشروع قائم (BOQ Engine)"
    ]
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

# ==============================================================================
# الوحدة الأولى: المنظومة المعمارية والتصدير الـ 3D
# ==============================================================================
if "1. المنظومة المعمارية" in module_choice:
    st.title("🏛️ المنظومة المعمارية والتصدير الهندسي متعدد البرامج")
    st.markdown("تحليل المخططات، توزيع المساقط مع السلالم المقوسة الإبداعية، وتصدير الأصول لـ 3ds Max و Photoshop و AutoCAD.")

    input_mode = st.radio("تحديد بيانات القسيمة:", ["رفع مخطط الأرض (الكروكي - PDF أو صورة)", "إدخال أبعاد القسيمة يدوياً"], horizontal=True)

    width, length, actual_sbc = 30.0, 50.0, 150.0

    if input_mode == "رفع مخطط الأرض (الكروكي - PDF أو صورة)":
        uploaded_file = st.file_uploader("ارفع ملف الكروكي (PDF / PNG / JPG):", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_file and api_key:
            client = genai.Client(api_key=api_key)
            file_bytes = uploaded_file.read()
            mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

            with st.spinner("جاري قراءة أبعاد القسيمة آلياً..."):
                prompt = "Extract width (frontage) and length (depth) in meters from this UAE site plan. Return JSON: {'width': float, 'length': float}."
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(res.text)
                    width = float(data.get("width", 30.0))
                    length = float(data.get("length", 50.0))
                    st.success(f"✅ تم التعرف على الأبعاد: الواجهة = {width} م | العمق = {length} م | المساحة = {width*length:.1f} م²")
                except Exception:
                    st.warning("تم اعتماد الأبعاد الافتراضية 30 × 50 م.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: width = st.number_input("عرض واجهة الأرض على الشارع (م):", 12.0, 200.0, 30.0, 0.5)
        with c2: length = st.number_input("عمق القسيمة الداخلي (م):", 15.0, 300.0, 50.0, 0.5)
        with c3: actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", 60.0, 400.0, 150.0, 10.0)

    # حسابات الكتلة
    front_sb = 5.0 if "أبوظبي" in emirate else (4.5 if "الشارقة" in emirate else 4.0)
    rear_sb = 3.0
    side_sb = 2.0 if "أبوظبي" in emirate else 1.5
    max_cov = 0.50 if ("أبوظبي" in emirate or "دبي" in emirate) else 0.55

    plot_area = round(width * length, 2)
    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov, 2))
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

    scheme_rooms = [
        {"n": "مجلس رجال رسمي\nFormal Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "c": "#FEF3C7"},
        {"n": "صالة طعام رسمية\nDining Suite", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
        {"n": "مطبخ تحضيري ورئيسي\nKitchen Suite", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "c": "#FED7AA"},
        {"n": "صالة معيشة عائلية\nPanoramic Living", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
        {"n": "جناح كبار السن\nGround Master Suite", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
    ]

    t1, t2 = st.tabs(["📐 المسقط المعماري والسلالم", "📦 تصدير البرامج الهندسية (3ds Max / CAD / PS)"])

    with t1:
        fig, ax = plt.subplots(figsize=(10, 13), dpi=200)
        ax.set_facecolor('#F8FAFC')
        ax.add_patch(patches.Rectangle((0, 0), width, length, lw=3.0, edgecolor='#0F172A', facecolor='#FFFFFF'))
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, lw=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none'))

        for r in scheme_rooms:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#1E293B', facecolor=r["c"], alpha=0.9))
            ax.add_patch(patches.Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.0, weight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

        # رسم الدرج الملكي المقوس
        st_x, st_y = side_sb + net_w*0.48, rear_sb + buildable_l*0.45
        st_w, st_h = 3.6, 4.5
        ax.add_patch(patches.Rectangle((st_x - st_w/2, st_y), st_w, st_h, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
        for sy in np.linspace(st_y, st_y + st_h, 14):
            ax.plot([st_x - st_w/2, st_x + st_w/2], [sy, sy], color='#475569', lw=1.2)
            ax.plot([st_x - st_w/2 + 0.3, st_x, st_x + st_w/2 - 0.3], [sy, sy + 0.15, sy], color='#0F172A', lw=1.5)
        ax.annotate('صعود UP', xy=(st_x, st_y + st_h - 0.4), xytext=(st_x, st_y + 0.5),
                    ha='center', fontsize=8.5, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=2.0))

        # الأبواب والمداخل
        for dx, dy, r, a1, a2 in [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]:
            ax.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        ax.annotate('المدخل الرسمي للضيوف (Majlis)', xy=(side_sb + net_w*0.24, rear_sb + buildable_l), xytext=(side_sb + net_w*0.24, rear_sb + buildable_l + 3.0),
                    ha='center', fontsize=9.0, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.2))
        ax.annotate('المدخل العائلي (Family)', xy=(side_sb + net_w*0.74, rear_sb + buildable_l), xytext=(side_sb + net_w*0.74, rear_sb + buildable_l + 3.0),
                    ha='center', fontsize=9.0, weight='bold', color='#0284C7', arrowprops=dict(arrowstyle="->", color='#0284C7', lw=2.2))

        ax.set_xlim(-width * 0.1, width * 1.1)
        ax.set_ylim(-length * 0.08, length * 1.15)
        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

    with t2:
        st.markdown("### 📦 قنوات التصدير المباشر لبرامج التصميم")
        col_c, col_m, col_p = st.columns(3)

        with col_c:
            st.markdown("#### 📐 AutoCAD (.DXF)")
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="SETBACKS", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (width-side_sb, rear_sb), (width-side_sb, length-front_sb), (side_sb, length-front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
            doc.layers.add(name="WALLS", color=4)
            for r in scheme_rooms:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
            dxf_buf = io.StringIO()
            doc.write(dxf_buf)
            st.download_button("💾 تحميل ملف AutoCAD (.DXF)", dxf_buf.getvalue().encode('utf-8'), "FloorPlan.dxf", "application/dxf")

        with col_m:
            st.markdown("#### 🧊 3ds Max / Blender (.OBJ)")
            obj_lines = ["# Villa 3D Asset for 3ds Max\n"]
            v_i = 1
            for idx, r in enumerate(scheme_rooms):
                x, y, w, h = r["x"], r["y"], r["w"], r["h"]
                verts = [(x,y,0),(x+w,y,0),(x+w,y+h,0),(x,y+h,0),(x,y,8.5),(x+w,y,8.5),(x+w,y+h,8.5),(x,y+h,8.5)]
                for vx, vy, vz in verts: obj_lines.append(f"v {vx:.2f} {vz:.2f} {vy:.2f}\n")
                f = v_i
                faces = [(f,f+1,f+2,f+3),(f+4,f+7,f+6,f+5),(f,f+4,f+5,f+1),(f+1,f+5,f+6,f+2),(f+2,f+6,f+7,f+3),(f+3,f+7,f+4,f)]
                obj_lines.append(f"g Room_{idx+1}\n")
                for f1,f2,f3,f4 in faces: obj_lines.append(f"f {f1} {f2} {f3} {f4}\n")
                v_i += 8
            st.download_button("💾 تحميل مجسم 3D (.OBJ)", "".join(obj_lines).encode('utf-8'), "Villa_Model.obj", "model/obj")

        with col_p:
            st.markdown("#### 🎨 Photoshop (.PNG 300 DPI)")
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
            st.download_button("💾 تحميل شيت شفاف لـ Photoshop", img_buf.getvalue(), "Plan_Transparent.png", "image/png")

# ==============================================================================
# الوحدة الثانية: محرك البرنامج الزمني المستقل (Gantt & CPM Engine)
# ==============================================================================
elif "2. محرك البرنامج الزمني" in module_choice:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج (Project Baseline & CPM)")
    st.markdown("توليد برنامج زمني تنفيذي احترافي لمشروع مصمم بالفعل وفق معدلات الإنتاجية المعتمدة في دولة الإمارات.")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        custom_bua = st.number_input("إجمالي مساحة مسطح البناء للمشروع BUA (م²):", min_value=100.0, max_value=20000.0, value=750.0, step=50.0)
    with col_s2:
        start_date = st.date_input("تاريخ تسليم الموقع وبدء الأعمال:", datetime.date.today())
    with col_s3:
        project_pace = st.selectbox("معدل وتيرة التنفيذ:", ["قياسي اعتيادي (Standard)", "مكثف / مسار سريع (Fast-Track)"])

    factor = 0.85 if "مكثف" in project_pace else 1.0

    # جدول الحزم والمسار الحرج
    wbs_data = [
        {"Task": "1. التراخيص وفحص التربة وشهادات عدم الممانعة (NOC)", "Days": int(30 * factor)},
        {"Task": "2. تجهيز الموقع والحفر والإحلال وسند الجوانب", "Days": int(20 * factor)},
        {"Task": "3. صبة النظافة (PCC) والقواعد والرقاب المسلحة", "Days": int(35 * factor)},
        {"Task": "4. عزل الأساسات والردم وطبقات الدفان والميدات", "Days": int(25 * factor)},
        {"Task": "5. الهيكل الخرساني العظم (الأعمدة والأسقف والمباني)", "Days": int(90 * factor * (custom_bua / 600.0)**0.5)},
        {"Task": "6. التمديدات الكهروميكانيكية وتأسيسات MEP", "Days": int(60 * factor)},
        {"Task": "7. العوازل المائية والحرارية للأسطح والكومبو", "Days": int(20 * factor)},
        {"Task": "8. أعمال البلاستر والأرضيات والتشطيبات الداخلية", "Days": int(75 * factor)},
        {"Task": "9. الألومنيوم والزجاج والواجهات الخارجية والأسوار", "Days": int(45 * factor)},
        {"Task": "10. الفحص والتشغيل التجريبي، استلام البلدية، والدفاع المدني", "Days": int(30 * factor)}
    ]

    current_start = pd.to_datetime(start_date)
    chart_rows = []
    for item in wbs_data:
        end_d = current_start + pd.Timedelta(days=item["Days"])
        chart_rows.append({"المرحلة التنفيذية": item["Task"], "البداية": current_start, "النهاية": end_d, "المدة (يوم)": item["Days"]})
        current_start = end_d - pd.Timedelta(days=int(item["Days"] * 0.25)) # تداخل المسار الحرج (Fast-tracking overlap)

    df_schedule = pd.DataFrame(chart_rows)
    total_project_days = (df_schedule["النهاية"].max() - pd.to_datetime(start_date)).days

    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي مدة المشروع", f"{total_project_days} يوماً")
    m2.metric("المدة بالشهور", f"{total_project_days / 30.5:.1f} شهراً")
    m3.metric("تاريخ الإنجاز والتسليم المتوقع", df_schedule["النهاية"].max().strftime('%Y-%m-%d'))

    st.markdown("---")
    st.subheader("📊 مخطط جانت التنفيذي لمراحل المشروع (Gantt Chart)")

    fig_gantt, ax_g = plt.subplots(figsize=(11, 6), dpi=180)
    for i, row in df_schedule.iterrows():
        start_num = mdates.date2num(row["البداية"])
        end_num = mdates.date2num(row["النهاية"])
        ax_g.barh(row["المرحلة التنفيذية"], end_num - start_num, left=start_num, color='#2563EB', edgecolor='#1E3A8A', height=0.55)

    ax_g.xaxis_date()
    ax_g.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax_g.grid(True, linestyle=':', alpha=0.6)
    ax_g.invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig_gantt)

    # تصدير الجدول
    csv_buf = io.StringIO()
    df_schedule.to_csv(csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة البرنامج الزمني بصيغة Excel / CSV", csv_buf.getvalue().encode('utf-8-sig'), "Project_Schedule.csv", "text/csv")

# ==============================================================================
# الوحدة الثالثة: محرك حصر الكميات والمواصفات المستقل (BOQ Engine)
# ==============================================================================
else:
    st.title("📊 محرك كراسة الكميات والمواصفات والتكاليف (Detailed BOQ Engine)")
    st.markdown("إعداد جدول كميات تنفيذي وحساب تكلفة العظم والتشطيبات لمشروع تم تصميمه بالفعل.")

    c_b1, c_b2, c_b3 = st.columns(3)
    with c_b1:
        proj_bua = st.number_input("مسطح البناء الإجمالي للمشروع (BUA م²):", 100.0, 30000.0, 850.0, 50.0)
    with c_b2:
        finishing_level = st.selectbox("مستوى المواصفات والتشطيب:", ["ديلوكس تجاري (Standard Deluxe)", "سوبر ديلوكس فاخر (Super Deluxe)", "ألترا لوكجري مودرن (Ultra Luxury VIP)"])
    with c_b3:
        ground_footprint = st.number_input("مسطح بصمة الطابق الأرضي Footprint (م²):", 50.0, 15000.0, float(proj_bua * 0.52), 25.0)

    # معادلات الحصر التقديرية المعتمدة
    conc_sub = round(proj_bua * 0.26, 1)
    conc_sup = round(proj_bua * 0.40, 1)
    tot_conc = round(conc_sub + conc_sup, 1)
    steel_t = round((tot_conc * 115) / 1000, 1)
    blocks_qty = round(proj_bua * 4.3)
    waterproof_m2 = round(ground_footprint * 2.3, 1)
    plaster_m2 = round(proj_bua * 6.5, 1)

    # أسعار البنود حسب مستوى التشطيب
    rate_multiplier = 1.0 if "تجاري" in finishing_level else (1.35 if "سوبر" in finishing_level else 1.80)

    boq_items = [
        {"كود البند": "01-01", "بند الأعمال الهندسي والمواصفة": "أعمال الحفر العام والتسوية ونقل المخلفات لمنسوب التأسيس", "الوحدة": "م³", "الكمية": round(ground_footprint * 1.8, 1), "السعر الإفرادي (AED)": 25.0},
        {"كود البند": "02-01", "بند الأعمال الهندسي والمواصفة": "خرسانة نظافة عادية Blinding PCC عيار 20 N/mm² تحت القواعد", "الوحدة": "م³", "الكمية": round(ground_footprint * 0.12, 1), "السعر الإفرادي (AED)": 270.0},
        {"كود البند": "02-02", "بند الأعمال الهندسي والمواصفة": "خرسانة مسلحة كبريتية SRC C40 للأساسات والميدات والرقاب", "الوحدة": "م³", "الكمية": conc_sub, "السعر الإفرادي (AED)": 340.0},
        {"كود البند": "02-03", "بند الأعمال الهندسي والمواصفة": "خرسانة مسلحة بورتلاندية OPC C35-C40 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": conc_sup, "السعر الإفرادي (AED)": 330.0},
        {"كود البند": "03-01", "بند الأعمال الهندسي والمواصفة": "حديد تسليح عالي المقاومة مشوه رتبة 500 MPa مشتملاً على الأسلاك والقص", "الوحدة": "طن", "الكمية": steel_t, "السعر الإفرادي (AED)": 2750.0},
        {"كود البند": "04-01", "بند الأعمال الهندسي والمواصفة": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والميدات مع ألواح الحماية", "الوحدة": "م²", "الكمية": waterproof_m2, "السعر الإفرادي (AED)": 45.0},
        {"كود البند": "05-01", "بند الأعمال الهندسي والمواصفة": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومصمت/مفرغ للداخل", "الوحدة": "حبة", "الكمية": blocks_qty, "السعر الإفرادي (AED)": 3.6},
        {"كود البند": "06-01", "بند الأعمال الهندسي والمواصفة": "لياسة إسمنتية داخلية وخارجية (طرطشة + بلاستر + زوايا وشبك فايبر)", "الوحدة": "م²", "الكمية": plaster_m2, "السعر الإفرادي (AED)": round(22.0 * rate_multiplier, 1)},
        {"كود البند": "07-01", "بند الأعمال الهندسي والمواصفة": "نظام العزل المائي والحراري المتكامل للأسطح (كومبو Combo System)", "الوحدة": "م²", "الكمية": round(ground_footprint * 1.1, 1), "السعر الإفرادي (AED)": 115.0},
        {"كود البند": "08-01", "بند الأعمال الهندسي والمواصفة": "أعمال الألومنيوم والزجاج المزدوج العازل (Double Glazing) واللوفرز", "الوحدة": "م²", "الكمية": round(proj_bua * 0.22, 1), "السعر الإفرادي (AED)": round(650.0 * rate_multiplier, 1)}
    ]

    df_boq = pd.DataFrame(boq_items)
    df_boq["الإجمالي التقديري (AED)"] = round(df_boq["الكمية"] * df_boq["السعر الإفرادي (AED)"])

    total_cost = df_boq["الإجمالي التقديري (AED)"].sum()

    b1, b2, b3 = st.columns(3)
    b1.metric("إجمالي التكلفة التقديرية للأعمال", f"{total_cost:,.0f} درهم إماراتي")
    b2.metric("متوسط سعر المتر المربع للبناء", f"{total_cost / proj_bua:,.1f} AED/م²")
    b3.metric("مستوى المواصفات المطبق", finishing_level.split('(')[0])

    st.markdown("---")
    st.subheader("📋 جدول حصر الكميات والمواصفات الفنية التفصيلي (Bill of Quantities)")
    st.dataframe(df_boq, use_container_width=True)

    csv_boq = io.StringIO()
    df_boq.to_csv(csv_boq, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات (BOQ) المعتمدة بصيغة Excel / CSV", csv_boq.getvalue().encode('utf-8-sig'), "Project_BOQ.csv", "text/csv")
