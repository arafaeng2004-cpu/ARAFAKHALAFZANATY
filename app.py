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
st.markdown("محرك عام: دراسة الارتدادات، التقسيمات الداخلية للمقترحات الـ 5، مخططات الدفاع المدني والخدمات الكهروميكانيكية (MEP)، والكميات التنفيذية.")

# ----------------- الشريط الجانبي -----------------
st.sidebar.header("⚙️ إعدادات المشروع والتنظيم")
api_key = st.sidebar.text_input("أدخل Gemini API Key (لقراءة الكروكي):", type="password")

emirate = st.sidebar.selectbox(
    "الإمارة / الجهة التنظيمية:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

input_mode = st.radio("طريقة إدخال بيانات القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع صورة أو كروكي الأرض (Site Plan)"])

width, length, actual_sbc = 0.0, 0.0, 150.0

if input_mode == "إدخال أبعاد القسيمة يدوياً":
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (متر):", min_value=10.0, max_value=200.0, value=25.0, step=0.5)
    with c2:
        length = st.number_input("عمق الأرض الداخلي (متر):", min_value=10.0, max_value=300.0, value=35.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=60.0, max_value=400.0, value=150.0, step=10.0)
else:
    uploaded_file = st.file_uploader("ارفع صورة الكروكي (PNG / JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        if not api_key:
            st.warning("يرجى إدخال API Key لتفعيل الاستخراج الذكي للأبعاد.")
        else:
            if st.button("🔍 قراءة بيانات الكروكي آلياً"):
                client = genai.Client(api_key=api_key)
                image = Image.open(uploaded_file)
                st.image(image, caption="الكروكي المرفوع", width=350)
                with st.spinner("جاري استخراج الأبعاد والحدود..."):
                    prompt = "Extract plot parameters strictly in JSON format with numeric keys: 'width', 'length', 'plot_area'. Return only JSON."
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(res.text)
                    st.success("تم استخراج البيانات بنجاح!")
                    width = float(data.get("width", 25.0))
                    length = float(data.get("length", 35.0))
                    st.write(f"الأبعاد المقروءة: الواجهة = **{width} م** | العمق = **{length} م**")

# ----------------- تشغيل المنظومة -----------------
if st.button("🚀 تشغيل المنظومة وتوليد الملف الفني الكامل"):
    plot_area = round(width * length, 2)

    # 1. المحددات البلدية
    if "أبوظبي" in emirate:
        front_sb, rear_sb, side_sb = 5.0, 3.0, 2.0
        max_cov_ratio = 0.50
    elif "الشارقة" in emirate:
        front_sb, rear_sb, side_sb = 4.5, 3.0, 1.5
        max_cov_ratio = 0.55
    elif "دبي" in emirate:
        front_sb, rear_sb, side_sb = 4.0, 3.0, 1.5
        max_cov_ratio = 0.50
    else:
        front_sb, rear_sb, side_sb = 4.0, 3.0, 1.5
        max_cov_ratio = 0.55

    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    buildable_footprint = round(net_w * net_l, 2)
    max_ground = round(plot_area * max_cov_ratio, 2)
    effective_ground = min(buildable_footprint, max_ground)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "1. المحددات البلدية", 
        "2. المقترحات والتقسيمات الداخلية", 
        "3. ملف الدفاع المدني ومخططات MEP", 
        "4. النظام الإنشائي والمواصفات", 
        "5. كراسة الكميات (BOQ)", 
        "6. البرنامج الزمني ومراحل التنفيذ"
    ])

    # ----------------- TAB 1: المحددات البلدية -----------------
    with tab1:
        st.subheader(f"المحددات التخطيطية واشتراطات البناء - {emirate}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي مساحة القسيمة", f"{plot_area:.1f} م²")
        c2.metric("أبعاد الكتلة الصافية المسموحة", f"{net_w:.1f} × {net_l:.1f} م")
        c3.metric(f"الحد الأقصى للأرضي ({int(max_cov_ratio*100)}%)", f"{effective_ground:.1f} م²")
        c4.metric("عمق الارتداد الأمامي", f"{front_sb:.1f} م")
        st.write(f"**الارتدادات المقررة:** أمامي {front_sb}م | خلفي {rear_sb}م | جانبي {side_sb}م من الجانبين")

    # ----------------- TAB 2: المقترحات المعمارية والتقسيم الداخلي -----------------
    with tab2:
        st.subheader("المقترحات المعمارية والتقسيمات الفراغية الداخلية التفصيلية")
        
        selected_scheme = st.selectbox(
            "اختر النموذج المعماري المطلوب استعراض مخططاته:",
            [
                "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات متلاصقة استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات خارجي منفصل (Villa + Outbuilding Block)"
            ]
        )

        if "المقترح 1" in selected_scheme:
            num_units = 1
            bua_factor = 1.85
            b_color = '#93C5FD'
            st.markdown("""
            #### 🏠 تفاصيل التقسيم الداخلي (فيلا عائلية فاخرة مستقلة):
            * **الطابق الأرضي:**
              * موزع استقبال رسمي ومدخل معزول ($3.0 \\times 4.0$ م) ومجلس رجال رسمي ($6.0 \\times 8.5$ م) بارتفاع $3.8$ م مع مغاسل وحمام ضيوف.
              * صالة طعام رسمية منفصلة ($4.5 \\times 6.0$ م) متصلة بباب خدمة للمطبخ.
              * صالة معيشة عائلية مفتوحة بحوائط زجاجية بانورامية ($7.0 \\times 8.5$ م) تطل على الفناء والمسبح الداخلي.
              * مجلس نساء/عائلي مستقل ($5.0 \\times 5.5$ م) بدورة مياه خاصة.
              * مطبخ Show Kitchen مفتوح ($4.0 \\times 5.0$ م) + مطبخ تحضيري ثقيل Dirty Kitchen ($3.5 \\times 4.5$ م) ومخزن تبريد.
              * جناح نوم أرضي لكبار السن/الضيوف ماستر ($4.5 \\times 5.0$ م) مجهز بالكامل.
              * غرفة خادمة بحمام خاص وغرفة غسيل وكوي مستقلة.
            * **الطابق الأول:**
              * جناح ماستر رئيسي فاخر (غرفة نوم $6.0 \\times 6.5$ م + دريسنج $3.5 \\times 4.5$ م + حمام بجاكوزي وشرفة بانورامية).
              * عدد 4 أجنحة نوم للأبناء، كل غرفة ماستر بدورة مياه مستقلة وخزائن حائطية.
              * صالة جلوس عائلية علوية ($5.0 \\times 6.0$ م) مزودة ببوفيه خدمة (Pantry).
            """)
        elif "المقترح 2" in selected_scheme:
            num_units = 2
            bua_factor = 1.80
            b_color = '#86EFAC'
            st.markdown("""
            #### 🏠 تفاصيل التقسيم الداخلي (فيلتان متلاصقتان Twin Villas):
            * **الطابق الأرضي (لكل وحدة):**
              * مدخل أمامي معزول لعدم تقابل المداخل، مجلس استقبال ($4.5 \\times 6.0$ م) مع حمام ومغاسل.
              * صالة معيشة وطعام عائلية ($5.0 \\times 7.5$ م) تطل على حديقة خلفية خاصة معزولة بجدار ساتر.
              * مطبخ متكامل مجهز ($3.5 \\times 4.5$ م) متصل بمخزن صغير، وغرفة نوم ضيوف أرضية ماستر.
              * غرفة عاملة منزلية بحمام مستقل.
            * **الطابق الأول (لكل وحدة):**
              * جناح نوم رئيسي ماستر ($4.5 \\times 5.5$ م) مع دريسنج وحمام واسع.
              * غرفتا نوم للأطفال ماستر بحمامات خاصة ($4.0 \\times 4.5$ م).
              * صالة توزيع علوية مع بوفيه تحضيري.
            """)
        elif "المقترح 3" in selected_scheme:
            num_units = 3
            bua_factor = 1.80
            b_color = '#FDE047'
            st.markdown("""
            #### 🏠 تفاصيل التقسيم الداخلي (3 فلل تاون هاوس):
            * **الطابق الأرضي (لكل وحدة):** موقف سيارة مغطى مدمج، صالة معيشة واستقبال عصرية مفتوحة ($5.0 \\times 9.0$ م) تطل على حديقة خلفية خاصة، مطبخ شبه مفتوح ($3.0 \\times 4.0$ م)، ومرحاض ضيوف وغرفة غسيل مدمجة.
            * **الطابق الأول (لكل وحدة):** جناح ماستر رئيسي ($4.2 \\times 5.0$ م) مع شرفة وحمام خاص، غرفتا نوم إضافيتان للأطفال بحمام مشترك، وركن مكتب ودراسة مفتوح.
            """)
        elif "المقترح 4" in selected_scheme:
            num_units = 4
            bua_factor = 1.75
            b_color = '#FCA5A5'
            st.markdown("""
            #### 🏠 تفاصيل التقسيم الداخلي (4 وحدات متلاصقة استثمارية Fourplex):
            * **الطابق الأرضي (لكل وحدة دوبلكس):** مدخل خاص، صالة معيشة ملمومة ($4.2 \\times 6.5$ م)، مطبخ نظامي ($2.6 \\times 3.5$ م)، حمام ضيوف وركن للغسيل مع سلم داخلي.
            * **الطابق الأول (لكل وحدة دوبلكس):** غرفة نوم ماستر رئيسية بحمام داخلي ($3.8 \\times 4.5$ م)، وغرفة نوم ثانية بحمام خارجي مجاور.
            """)
        else:
            num_units = 1
            bua_factor = 1.90
            b_color = '#C4B5FD'
            st.markdown("""
            #### 🏠 تفاصيل التقسيم الداخلي (فيلا رئيسية + ملحق خدمات خارجي منفصل):
            * **كتلة الفيلا الرئيسية (Main Villa G+1):**
              * الأرضي: مخصص للهدوء والاجتماع العائلي الخالص؛ صالة معيشة كبرى مزدوجة الارتفاع ($8.0 \\times 9.0$ م)، مطبخ إفطار Show Pantry، وجناح نوم لكبار السن.
              * الأول: 4 أجنحة نوم ماستر كاملة مع صالة جلوس عائلية وتراس واسع.
            * **كتلة الملحق الخدمي الخارجي (Outbuilding Ground Floor):**
              * مجلس رسمي خارجي للمناسبات والولائم ($7.0 \\times 10.0$ م) بحمامات ومغاسل فندقية.
              * مطبخ ولائم ثقيل ($4.5 \\times 6.5$ م) مع غرفة تبريد ومستودع تموين.
              * سكن العمالة المنزلية (غرفتان + حمامان + غرفة غسيل مركزية) وغرفة سائق تفتح للخارج.
            """)

        calc_total_bua = round(effective_ground * bua_factor, 2)
        calc_bua_per_unit = round(calc_total_bua / num_units, 2)

        st.markdown("---")
        st.subheader("📐 المخطط الكروكي التفاعلي للموقع العام (Dynamic Site Layout)")

        fig, ax = plt.subplots(figsize=(8, 6))
        plot_rect = patches.Rectangle((0, 0), width, length, linewidth=2.5, edgecolor='black', facecolor='#F8FAFC', label='حدود القسيمة')
        ax.add_patch(plot_rect)

        setback_rect = patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=1.5, edgecolor='red', linestyle='--', facecolor='none', label='خط الارتداد المسموح')
        ax.add_patch(setback_rect)

        buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

        if num_units == 1 and "المقترح 5" in selected_scheme:
            main_l = buildable_l * 0.70
            serv_l = buildable_l * 0.22
            gap = buildable_l * 0.08
            ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, main_l, linewidth=2, edgecolor='#312E81', facecolor=b_color, alpha=0.7, label='الفيلا الرئيسية'))
            ax.add_patch(patches.Rectangle((side_sb, rear_sb + main_l + gap), net_w * 0.65, serv_l, linewidth=1.5, edgecolor='#312E81', facecolor='#DDD6FE', alpha=0.8, label='ملحق الخدمات والمجلس'))
            ax.text(side_sb + (net_w/2), rear_sb + (main_l/2), "Main Villa", ha='center', va='center', weight='bold')
            ax.text(side_sb + (net_w * 0.65 / 2), rear_sb + main_l + gap + (serv_l/2), "Services Block", ha='center', va='center', fontsize=9)
        else:
            unit_w = net_w / num_units
            for i in range(num_units):
                u_x = side_sb + (i * unit_w)
                lbl = f'الوحدات السكنية ({num_units})' if i == 0 else None
                ax.add_patch(patches.Rectangle((u_x, rear_sb), unit_w, buildable_l, linewidth=1.8, edgecolor='#065F46', facecolor=b_color, alpha=0.65, label=lbl))
                if i > 0:
                    ax.plot([u_x, u_x], [rear_sb, rear_sb + buildable_l], color='black', linestyle='-', linewidth=2.5)
                ax.text(u_x + (unit_w / 2), rear_sb + (buildable_l / 2), f"Unit {i+1}\n({unit_w:.1f}m)", ha='center', va='center', fontsize=9, weight='bold')

        ax.set_xlim(-width * 0.15, width * 1.15)
        ax.set_ylim(-length * 0.10, length * 1.15)
        ax.set_aspect('equal')
        ax.set_xlabel("عرض الواجهة على الشارع (متر)")
        ax.set_ylabel("عمق القسيمة (متر)")
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig)

        c_dxf, c_img = st.columns(2)
        with c_dxf:
            try:
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                doc.layers.add(name="PLOT_BOUNDARY", color=7)
                msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_BOUNDARY'})
                doc.layers.add(name="SETBACKS", color=1)
                msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
                doc.layers.add(name="BUILDING_UNITS", color=3)
                if num_units == 1 and "المقترح 5" in selected_scheme:
                    msp.add_lwpolyline([(side_sb, rear_sb), (side_sb + net_w, rear_sb), (side_sb + net_w, rear_sb + main_l), (side_sb, rear_sb + main_l), (side_sb, rear_sb)], dxfattribs={'layer': 'BUILDING_UNITS'})
                else:
                    unit_w = net_w / num_units
                    for i in range(num_units):
                        u_x = side_sb + (i * unit_w)
                        msp.add_lwpolyline([(u_x, rear_sb), (u_x + unit_w, rear_sb), (u_x + unit_w, rear_sb + buildable_l), (u_x, rear_sb + buildable_l), (u_x, rear_sb)], dxfattribs={'layer': 'BUILDING_UNITS'})

                dxf_stream = io.StringIO()
                doc.write(dxf_stream)
                st.download_button(
                    label=f"💾 تحميل ملف AutoCAD (.DXF) للنموذج المختار",
                    data=dxf_stream.getvalue().encode('utf-8'),
                    file_name=f"Plot_{width}x{length}_Scheme.dxf",
                    mime="application/dxf"
                )
            except Exception as e:
                st.error(f"خطأ DXF: {e}")

        with c_img:
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight')
            img_buf.seek(0)
            st.download_button(
                label="📄 تحميل الكروكي كصورة هندسية بدقة عالية",
                data=img_buf,
                file_name=f"Plot_{width}x{length}_SitePlan.png",
                mime="image/png"
            )

    # ----------------- TAB 3: مخططات الدفاع المدني و MEP -----------------
    with tab3:
        st.subheader("📋 حزمة المخططات المتكاملة للاعتماد والترخيص (Authority Submission Set)")
        
        mep_tabs = st.tabs([
            "1. مخططات الدفاع المدني والسلامة (Civil Defence)", 
            "2. مخططات الصرف الصحي وتغذية المياه (Plumbing)", 
            "3. المخطط الكهربائي وحساب الأحمال (Electrical)", 
            "4. مخطط التكييف والتهوية الميكانيكية (HVAC)"
        ])
        
        with mep_tabs[0]:
            st.markdown("#### اشتراطات السلامة والوقاية من الحريق (UAE Fire & Life Safety Code)")
            st.write("- **نظام الإنذار المبكر:** كواشف دخان ضوئية (Optical Smoke Detectors) موزعة في جميع غرف النوم والممرات والصالات + كاشف حرارة (Heat Detector) في المطابخ.")
            st.write("- **أبواب الحماية ومسارات الهروب:** أبواب مقاومة للحريق والحرارة لمدة 60 دقيقة (Fire Rated FD-60) تفصل المطابخ وغرف الخدمات ومواقف السيارات عن مسار الهروب الداخلي.")
            st.write("- **أجهزة الإطفاء اليدوية:** طفاية بودرة كيميائية جافة (DCP 6kg) بجوار المخارج والمواقف + طفاية غاز ثاني أكسيد الكربون (CO2 2kg) داخل المطابخ وغرف التوزيع الكهربائي.")
            st.write("- **إنارة الطوارئ:** كشافات طوارئ وإشارات خروج مضيئة (Self-Contained Exit Lights) ببطارية داخلية تدوم 3 ساعات.")

        with mep_tabs[1]:
            st.markdown("#### شبكات الصرف الصحي والتغذية المائية المعتمدة")
            st.write("- **نظام الصرف الصحي المزدوج (Two-Pipe System):** فصل مياه الصرف السوداء (Soil Pipes 4\") عن مياه الصرف الرمادية (Waste Pipes 3\") مع أنابيب تنفيس رأسية (Vent Stacks) فوق السطح.")
            st.write("- **غرف التفتيش ومصائد الشحوم:** إنشاء غرف تفتيش (Inspection Chambers) بأغطية دكتايل مانعة للروائح، مع تركيب مصيدة شحوم (Grease Trap) إلزامية لمياه غسيل المطابخ قبل الربط.")
            st.write("- **شبكة تغذية مياه الشرب:** أنابيب بولي بروبلين حراري (PPR PN20) معزولة بالكامل ضد الإشعاع الشمسي، وخزان مياه أرضي وعلوي من الـ GRP مزود بمبرد مياه صيفي (Chiller System).")

        with mep_tabs[2]:
            est_load_kw = round(calc_total_bua * 0.12, 1)
            est_load_kva = round(est_load_kw / 0.85, 1)
            st.markdown("#### الأحمال الكهربائية وشبكات التيار الخفيف (Wiring Regulations)")
            col_el1, col_el2 = st.columns(2)
            col_el1.metric("إجمالي الحمل الكهربائي التقديري (Connected Load)", f"{est_load_kw} kW")
            col_el2.metric("الحمل التصميمي المقدر (Estimated Demand Load)", f"{est_load_kva} kVA")
            st.write("- **مواصفات اللوحات:** لوحة توزيع رئيسية (MDB) مع قواطع حساسة للتسريب الأرضي (ELCB 30mA للغرف الرطبة و 100mA للإنارة والدوائر العامة).")
            st.write("- **التأريض ومانعات الصواعق:** شبكة تأريض نحاسية مصفوفة تحقق مقاومة أرضي أقل من 1 أوم وفق اشتراطات الهيئة المعتمدة.")
            st.write("- **التيار الخفيف (Low Current):** نقاط إنترنت (Cat6 Data Sockets)، كاميرات مراقبة (CCTV) للأسوار والمداخل، ونظام إنتركم مرئي ذكي (IP Intercom).")

        with mep_tabs[3]:
            est_cooling_tr = round(calc_total_bua / 14.5, 1)
            st.markdown("#### الحسابات الحرارية ومخططات التكييف (HVAC Engineering)")
            st.metric("الحمل الحراري التقديري للتكييف", f"{est_cooling_tr} طن تبريد (TR)")
            st.write("- **النظام المعتمد:** وحدات تكييف مجزأة مخفية (Ducted Split Units) موفرة للطاقة بنظام Inverter أو نظام التبريد المتغير (VRF).")
            st.write("- **مجاري الهواء (Ductwork):** ألواح صاج مجلفن معزولة داخلياً وخارجياً بالصوف الزجاجي (Fiberglass) بكثافة 24 كجم/م³ مع مخارج هواء خطية (Linear Slot Diffusers).")
            st.write("- **تصريف مياه التكييف:** شبكة أنابيب UPVC معزولة مخصصة للصرف تصب في أقرب جاليتراب أو نقطة صرف مياه رمادية لتفادي التسرب والتكثف.")

    # ----------------- TAB 4: النظام الإنشائي والمواصفات -----------------
    with tab4:
        st.subheader("النظام الإنشائي ومواصفات التأسيس")
        if actual_sbc < 140 or num_units >= 3:
            found_rec = "أساس حصيري مسلح (Raft Foundation) أو قواعد مشتركة (Combined Strip Footings)"
            found_reason = "نظراً لتقارب الأحمال ووجود فواصل إنشائية متعددة أو انخفاض جهد التربة المسموح."
        else:
            found_rec = "قواعد منفصلة مسلحة (Isolated Footings) متصلة بشبكة ميدات ربط جاسئة (Tie Beams)"
            found_reason = f"لأن جهد التربة ({actual_sbc} kN/m²) كافٍ وآمن لتحمل الأحمال المركزة لأعمدة الفلل السكنية."

        st.info(f"**نظام الأساسات الموصى به:** {found_rec}\n\n*التعليل الهندسي:* {found_reason}")

        c_st1, c_st2 = st.columns(2)
        with c_st1:
            st.markdown("**مواصفات المواد الإنشائية (Substructure):**")
            st.write("- **خرسانة الأساسات والميدات:** خرسانة مقاومة للكبريتات SRC رتبة C40 مع نسبة W/C لا تتجاوز 0.40.")
            st.write("- **نظام العزل:** غشاء بيتوميني مزدوج 4 مم مع ألواح حماية Protection Board قبل الردم.")
            st.write("- **حديد التسليح:** مشوه عالي المقاومة High-Yield Deformed Bars رتبة 500 MPa.")
        with c_st2:
            st.markdown("**مواصفات الهيكل العلوي (Superstructure):**")
            st.write("- **خرسانة الأعمدة والأسقف:** بورتلاندية عادية OPC رتبة C35 إلى C40.")
            st.write("- **نظام الأسقف:** بلاطات لاكمرية Flat Slabs بسماكة 22 إلى 24 سم لتحقيق مرونة التوزيع المعماري الداخلي وتفادي سقوط الجسور.")
            if num_units > 1:
                st.write(f"- **الفواصل الإنشائية:** فاصل هبوط وتمدد كامل بسماكة 25 مم مع جدارين مزدوجين (20 سم + 20 سم) لعزل الصوت بين الوحدات.")

    # ----------------- TAB 5: حصر الكميات والتكاليف (BOQ) -----------------
    with tab5:
        st.subheader(f"كراسة حصر الكميات والمواد التقديرية (BOQ) - إجمالي مسطح البناء {calc_total_bua:.1f} م²")
        vol_concrete_sub = round(calc_total_bua * 0.25, 1)
        vol_concrete_super = round(calc_total_bua * 0.40, 1)
        total_concrete_vol = round(vol_concrete_sub + vol_concrete_super, 1)
        steel_tonnage = round((total_concrete_vol * 115) / 1000, 1)
        blocks_qty = round(calc_total_bua * (4.5 if num_units > 1 else 4.2))
        plaster_qty = round(calc_total_bua * 6.5, 1)
        excavation_qty = round(effective_ground * 1.8, 1)

        boq_data = [
            {"البند": "1. أعمال الحفر العام والتسوية", "الوحدة": "م³", "الكمية": excavation_qty, "سعر الوحدة التقديري (AED)": 25, "الإجمالي (AED)": round(excavation_qty * 25)},
            {"البند": "2. خرسانة عادية للنظافة (Blinding PCC C20)", "الوحدة": "م³", "الكمية": round(effective_ground * 0.12, 1), "سعر الوحدة التقديري (AED)": 270, "الإجمالي (AED)": round(effective_ground * 0.12 * 270)},
            {"البند": "3. خرسانة مسلحة كبريتية للأساسات والميدات (SRC C40)", "الوحدة": "م³", "الكمية": vol_concrete_sub, "سعر الوحدة التقديري (AED)": 340, "الإجمالي (AED)": round(vol_concrete_sub * 340)},
            {"البند": "4. خرسانة مسلحة للأعمدة والأسقف (OPC C35/C40)", "الوحدة": "م³", "الكمية": vol_concrete_super, "سعر الوحدة التقديري (AED)": 330, "الإجمالي (AED)": round(vol_concrete_super * 330)},
            {"البند": "5. حديد تسليح عالي المقاومة (Grade 500)", "الوحدة": "طن", "الكمية": steel_tonnage, "سعر الوحدة التقديري (AED)": 2750, "الإجمالي (AED)": round(steel_tonnage * 2750)},
            {"البند": "6. عزل مائي بيتوميني للأساسات والميدات", "الوحدة": "م²", "الكمية": round(effective_ground * 2.2, 1), "سعر الوحدة التقديري (AED)": 45, "الإجمالي (AED)": round(effective_ground * 2.2 * 45)},
            {"البند": "7. أعمال الطابوق الأسمنتي المعزول والداخلي", "الوحدة": "حبة", "الكمية": blocks_qty, "سعر الوحدة التقديري (AED)": 3.5, "الإجمالي (AED)": round(blocks_qty * 3.5)},
            {"البند": "8. أعمال اللياسة الإسمنتية الداخلية والخارجية", "الوحدة": "م²", "الكمية": plaster_qty, "سعر الوحدة التقديري (AED)": 22, "الإجمالي (AED)": round(plaster_qty * 22)}
        ]

        df_boq = pd.DataFrame(boq_data)
        st.table(df_boq)
        total_est_cost = df_boq["الإجمالي (AED)"].sum()
        st.metric("التكلفة التقديرية المبدئية لبنود الهيكل الإنشائي والعظم", f"{total_est_cost:,.0f} درهم إماراتي")

    # ----------------- TAB 6: البرنامج الزمني -----------------
    with tab6:
        st.subheader("البرنامج الزمني ومراحل التنفيذ والاستلامات")
        base_weeks = 52 if num_units <= 2 else 64
        st.info(f"**المدة الزمنية المقدرة للمشروع:** من {base_weeks - 4} إلى {base_weeks + 4} أسبوعاً.")

        schedule_items = [
            {"المرحلة": "1. التراخيص وفحص التربة وشهادات NOC", "المدة المقدرة": "4 - 6 أسابيع", "الوزن النسبي": "5%", "الجهة المسؤولة للاعتماد": "البلدية / هيئة الكهرباء والمياه"},
            {"المرحلة": "2. أعمال الحفر، صبة النظافة، وعزل القواعد", "المدة المقدرة": "3 - 4 أسابيع", "الوزن النسبي": "10%", "الجهة المسؤولة للاعتماد": "مهندس الإشراف الاستشاري"},
            {"المرحلة": "3. القواعد والميدات والردم المعتمد (Substructure)", "المدة المقدرة": "4 - 5 أسابيع", "الوزن النسبي": "15%", "الجهة المسؤولة للاعتماد": "الاستشاري + مختبر التربة المعتمد"},
            {"المرحلة": "4. الهيكل الخرساني العظم والمباني (Superstructure)", "المدة المقدرة": "12 - 16 أسبوعاً", "الوزن النسبي": "30%", "الجهة المسؤولة للاعتماد": "مهندس الاستشاري والبلدية"},
            {"المرحلة": "5. التمديدات الكهروميكانيكية (MEP) والعوازل المائية والحرارية", "المدة المقدرة": "8 - 10 أسابيع", "الوزن النسبي": "15%", "الجهة المسؤولة للاعتماد": "هيئة الكهرباء والمياه والدفاع المدني"},
            {"المرحلة": "6. التشطيبات المعمارية والأرضيات والواجهات", "المدة المقدرة": "12 - 14 أسبوعاً", "الوزن النسبي": "20%", "الجهة المسؤولة للاعتماد": "المالك والاستشاري"},
            {"المرحلة": "7. الفحص النهائي، إطلاق التيار، وشهادة الإنجاز", "المدة المقدرة": "3 - 4 أسابيع", "الوزن النسبي": "5%", "الجهة المسؤولة للاعتماد": "البلدية وإدارة الدفاع المدني"}
        ]
        st.table(pd.DataFrame(schedule_items))
