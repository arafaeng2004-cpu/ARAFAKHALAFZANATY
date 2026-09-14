import streamlit as st
import pandas as pd
import json
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import ezdxf
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Engineering & Construction Suite", layout="wide")

st.title("🏗️ المنظومة الهندسية المتكاملة لمشاريع البناء - دولة الإمارات")
st.markdown("من دراسة المحددات البلدية وتوليد المخططات، إلى البرامج الزمنية وحصر المواد وإدارة التنفيذ خطوة بخطوة.")

# إعدادات الشريط الجانبي
api_key = st.sidebar.text_input("أدخل Gemini API Key:", type="password")
city = st.sidebar.selectbox("الإمارة / الجهة التنظيمية:", ["الشارقة", "أبوظبي / العين", "دبي", "عجمان / أخرى"])
project_type = st.sidebar.selectbox("نوع المشروع:", ["فيلا سكنية خاصة (G+1)", "فيلا طابق أرضي فقط (G)", "فيلا مع ملحق وخدمات (G+1+R)"])

input_mode = st.radio("طريقة تحديد الأرض:", ["إدخال أبعاد القسيمة يدوياً", "رفع مخطط الأرض (الكروكي / Site Plan)"])

width, length, actual_sbc = 0.0, 0.0, 150.0

if input_mode == "إدخال أبعاد القسيمة يدوياً":
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض الواجهة على الشارع (متر):", min_value=5.0, value=25.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة (متر):", min_value=5.0, value=35.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=50.0, value=150.0, step=10.0)
else:
    uploaded_file = st.file_uploader("ارفع صورة الكروكي (PNG / JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_file and api_key:
        if st.button("استخراج بيانات القسيمة آلياً عبر الذكاء الاصطناعي"):
            client = genai.Client(api_key=api_key)
            image = Image.open(uploaded_file)
            st.image(image, caption="مخطط الأرض المرفوع", width=350)
            with st.spinner("جاري استخراج البيانات والمساحات..."):
                prompt = "Extract plot parameters strictly in JSON format with keys: 'width', 'length', 'plot_area', 'plot_no', 'sector'."
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                data = json.loads(res.text)
                st.success("تم استخراج البيانات بنجاح!")
                st.json(data)
                width = float(data.get("width", 25.0))
                length = float(data.get("length", 35.0))

# تشغيل التحليل الشامل
if st.button("🚀 تشغيل المنظومة وتوليد المخرجات الكاملة"):
    plot_area = width * length

    # 1. المحددات البلدية
    front_sb = 5.0 if "أبوظبي" in city else (4.5 if "الشارقة" in city else 4.0)
    rear_sb = 3.0
    side_sb = 2.0 if "أبوظبي" in city else 1.5

    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    buildable_footprint = round(net_w * net_l, 2)
    max_ground = round(plot_area * 0.55, 2)
    effective_ground = min(buildable_footprint, max_ground)
    
    multiplier = 1.0 if "طابق أرضي" in project_type else 1.85
    total_bua = round(effective_ground * multiplier, 2)

    # 2. الحسابات الإنشائية وحصر الكميات
    est_concrete_sub = round(total_bua * 0.25, 1)
    est_concrete_super = round(total_bua * 0.40, 1)
    total_concrete = round(est_concrete_sub + est_concrete_super, 1)
    total_steel = round((total_concrete * 115) / 1000, 1)
    blockwork_qty = round(total_bua * 4.2)
    excavation_vol = round(effective_ground * 1.8, 1)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1. المحددات البلدية", 
        "2. المقترحات المعمارية والكروكي", 
        "3. النظام الإنشائي والمواصفات", 
        "4. حصر المواد والتكاليف (BOQ)", 
        "5. البرنامج الزمني ومراحل التنفيذ"
    ])

    with tab1:
        st.subheader("المحددات التخطيطية واشتراطات البناء")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي مساحة القسيمة", f"{plot_area:.1f} م²")
        c2.metric("كتلة البناء المسموحة", f"{net_w:.1f} × {net_l:.1f} م")
        c3.metric("مسطح الطابق الأرضي", f"{effective_ground:.1f} م²")
        c4.metric("إجمالي مسطح البناء (BUA)", f"{total_bua:.1f} م²")
        st.write(f"**الارتدادات المقررة:** أمامي {front_sb}م | خلفي {rear_sb}م | جانبي {side_sb}م")

    with tab2:
        st.subheader("المقترحات المعمارية واستغلال الفراغات")
        arch_data = {
            "المقترح": ["النمط المركزي (L-Shape / Courtyard)", "النمط المفتوح المودرن (Open Living)", "النمط التقليدي المنفصل (Privacy Focus)"],
            "المزايا": ["أقصى خصوصية للحديقة والمسبح، إطلالة مباشرة لجميع الصالات", "تقليل الممرات، كفاءة عالية في توزيع التكييف والإنارة", "فصل تام بين مجالس الضيوف وجناح العائلة والخدمات"],
            "مناسب لـ": ["العائلات الكبيرة والأراضي العريضة", "التصاميم الحديثة وتقليل تكلفة البناء", "الاشتراطات الاجتماعية مع ملحق خارجي للخدمات"]
        }
        st.table(pd.DataFrame(arch_data))

        st.markdown("---")
        st.subheader("📐 المخطط الكروكي العام للموقع (Site Layout)")

        fig, ax = plt.subplots(figsize=(8, 6))
        plot_rect = patches.Rectangle((0, 0), width, length, linewidth=2.5, edgecolor='black', facecolor='#f4f4f4', label='حدود الأرض (Plot Boundary)')
        ax.add_patch(plot_rect)

        setback_rect = patches.Rectangle(
            (side_sb, rear_sb), 
            net_w, net_l, 
            linewidth=1.5, edgecolor='red', linestyle='--', facecolor='none', label='حد الارتداد المسموح (Setback Limit)'
        )
        ax.add_patch(setback_rect)

        buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
        building_rect = patches.Rectangle(
            (side_sb, rear_sb), 
            net_w, buildable_l, 
            linewidth=2, edgecolor='#1E3A8A', facecolor='#93C5FD', alpha=0.6, label='كتلة المبنى المقترحة (Building Footprint)'
        )
        ax.add_patch(building_rect)

        ax.set_xlim(-5, width + 5)
        ax.set_ylim(-5, length + 8)
        ax.set_aspect('equal')
        ax.set_xlabel("العرض (متر)", fontsize=10)
        ax.set_ylabel("العمق (متر)", fontsize=10)
        ax.set_title(f"مخطط الموقع العام المبدئي - مساحة البناء: {effective_ground:.1f} م²", fontsize=12)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, linestyle=':', alpha=0.6)

        ax.annotate('الشارع الرئيسي / الواجهة', xy=(width/2, length + 1), xytext=(width/2, length + 4),
                    ha='center', fontsize=10, weight='bold', color='darkgreen',
                    arrowprops=dict(arrowstyle="->", color='darkgreen', lw=1.5))

        st.pyplot(fig)

        # أزرار التصدير
        c_dxf, c_pdf = st.columns(2)
        with c_dxf:
            try:
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                doc.layers.add(name="PLOT_LIMITS", color=7)
                msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_LIMITS'})
                doc.layers.add(name="SETBACKS", color=1)
                msp.add_lwpolyline([
                    (side_sb, rear_sb), 
                    (width - side_sb, rear_sb), 
                    (width - side_sb, length - front_sb), 
                    (side_sb, length - front_sb), 
                    (side_sb, rear_sb)
                ], dxfattribs={'layer': 'SETBACKS'})
                doc.layers.add(name="BUILDING_FOOTPRINT", color=4)
                msp.add_lwpolyline([
                    (side_sb, rear_sb), 
                    (side_sb + net_w, rear_sb), 
                    (side_sb + net_w, rear_sb + buildable_l), 
                    (side_sb, rear_sb + buildable_l), 
                    (side_sb, rear_sb)
                ], dxfattribs={'layer': 'BUILDING_FOOTPRINT'})

                dxf_stream = io.StringIO()
                doc.write(dxf_stream)
                st.download_button(
                    label="💾 تحميل المخطط بصيغة AutoCAD (.DXF)",
                    data=dxf_stream.getvalue().encode('utf-8'),
                    file_name=f"Plot_{width}x{length}_SitePlan.dxf",
                    mime="application/dxf"
                )
            except Exception as e:
                st.error(f"خطأ في توليد ملف DXF: {e}")

        with c_pdf:
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight')
            img_buf.seek(0)
            st.download_button(
                label="📄 تحميل الكروكي كصورة هندسية عالية الدقة",
                data=img_buf,
                file_name=f"Plot_{width}x{length}_SitePlan.png",
                mime="image/png"
            )

    with tab3:
        st.subheader("التوصيات الهندسية والإنشائية المبدئية")
        found_decision = "قواعد منفصلة + ميدات ربط متصلة (Isolated Footings + Tie Beams)" if actual_sbc >= 150 else "أساس حصيري مسلح (Raft Foundation)"
        st.info(f"**نظام التأسيس المقترح بناءً على جهد تربة ({actual_sbc} kN/m²):** {found_decision}")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**مواصفات الخرسانة المعتمدة:**")
            st.write("- **الهيكل السفلي الملامس للتربة:** خرسانة كبريتية مقومة للأملاح (SRC - C40) مع عزل مائي بيتونيمي مزدوج.")
            st.write("- **الهيكل العلوي:** خرسانة بورتلاندية اعتيادية (OPC - C35/C40).")
        with col_s2:
            st.markdown("**النظام الإنشائي للأسقف:**")
            st.write("- **نظام البلاطات اللاكمرية (Flat Slab 22-24 سم):** لضمان مرونة التقسيم الداخلي وتفادي سقوط الجسور داخل المجالس.")

    with tab4:
        st.subheader("جدول حصر الكميات والمواد المبدئي (Preliminary BOQ)")
        boq_data = {
            "بند الأعمال": ["أعمال الحفر والردم والتسوية", "خرسانة الأساسات والرقاب والميدات (SRC)", "خرسانة الأعمدة والأسقف (OPC)", "حديد التسليح عالي المقاومة (Grade 500)", "أعمال الطابوق المصمت والمفرغ"],
            "الوحدة": ["متر مكعب (م³)", "متر مكعب (م³)", "متر مكعب (م³)", "طن", "طابوقة"],
            "الكمية التقديرية": [excavation_vol, est_concrete_sub, est_concrete_super, total_steel, blockwork_qty]
        }
        st.table(pd.DataFrame(boq_data))

    with tab5:
        st.subheader("البرنامج الزمني ومسار التنفيذ خطوة بخطوة (WBS & Execution Flow)")
        schedule_data = {
            "المرحلة التنفيذية": [
                "1. التراخيص والاعتمادات البلدية وفحص التربة",
                "2. تجهيز الموقع والحفر وصبة النظافة",
                "3. الأساسات الخرسانية، الرقاب، وعزل القواعد",
                "4. الردم على طبقات والميدات الأرضية (Tie Beams)",
                "5. أعمدة وأسقف الهيكل الإنشائي (العظم)",
                "6. أعمال المباني والتشطيبات والكهرباء والصحي (MEP)",
                "7. الفحص النهائي وتوصيل الخدمات وإنجاز المبنى"
            ],
            "المدة المتوقعة": ["3 - 5 أسابيع", "2 أسابيع", "3 - 4 أسابيع", "2 - 3 أسابيع", "8 - 10 أسابيع", "12 - 16 أسبوع", "3 - 4 أسابيع"],
            "متطلبات الاستلام والاعتماد": [
                "اعتماد المخططات، فحص تربة لـ 2-3 جسات، شهادة عدم ممانعة (NOC)",
                "مطابقة منسوب الحفر ومطابقة منسوب الصفر المعماري",
                "فحص حديد التسليح واختبار كسر المكعبات (7 و 28 يوم) واستلام العزل",
                "اختبار دمك التربة (Compaction Test) بدرجة نجاح لا تقل عن 95%",
                "فحص شاقولية الأعمدة، وتدعيم الشدات الخشبية، واختبار هبوط الخرسانة",
                "اعتماد عينات التشطيبات ومخططات التمديدات المعتمدة من هيئة الكهرباء والمياه",
                "شهادة استيفاء الدفاع المدني وشهادة إنجاز البلدية"
            ]
        }
        st.table(pd.DataFrame(schedule_data))
