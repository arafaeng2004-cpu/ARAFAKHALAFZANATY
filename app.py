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
st.markdown("محرك عام: دراسة الارتدادات، رسم التقسيمات الداخلية بالأبعاد، مخططات الدفاع المدني والخدمات (MEP)، وتصدير ملفات AutoCAD.")

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
    if uploaded_file and api_key:
        if st.button("🔍 قراءة بيانات الكروكي آلياً"):
            client = genai.Client(api_key=api_key)
            image = Image.open(uploaded_file)
            st.image(image, caption="الكروكي المرفوع", width=350)
            with st.spinner("جاري استخراج الأبعاد..."):
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

# ----------------- تشغيل المنظومة -----------------
if st.button("🚀 تشغيل المنظومة وتوليد المخططات والملف الفني الكامل"):
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
        "2. المخطط المعماري والتقسيم الداخلي", 
        "3. مخططات الخدمات والدفاع المدني (MEP)", 
        "4. النظام الإنشائي والمواصفات", 
        "5. كراسة الكميات (BOQ)", 
        "6. البرنامج الزمني ومراحل التنفيذ"
    ])

    with tab1:
        st.subheader(f"المحددات التخطيطية واشتراطات البناء - {emirate}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي مساحة القسيمة", f"{plot_area:.1f} م²")
        c2.metric("أبعاد الكتلة الصافية المسموحة", f"{net_w:.1f} × {net_l:.1f} م")
        c3.metric(f"الحد الأقصى للأرضي ({int(max_cov_ratio*100)}%)", f"{effective_ground:.1f} م²")
        c4.metric("عمق الارتداد الأمامي", f"{front_sb:.1f} م")
        st.write(f"**الارتدادات المقررة:** أمامي {front_sb}م | خلفي {rear_sb}م | جانبي {side_sb}م من الجانبين")

    with tab2:
        st.subheader("المخططات المعمارية والتقسيمات الفراغية الداخلية")
        
        selected_scheme = st.selectbox(
            "اختر النموذج لتوليد مسقطه المعماري الداخلي ومخططه الهندسي:",
            [
                "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات متلاصقة استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات خارجي منفصل (Villa + Outbuilding Block)"
            ]
        )

        buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
        
        # تجهيز الغرف الداخلية حسب المقترح
        rooms = []
        if "المقترح 1" in selected_scheme:
            num_units = 1
            bua_factor = 1.85
            rooms = [
                {"name": "مجلس رجال رسمي\n(6.0x8.5m)", "x": side_sb, "y": rear_sb + buildable_l*0.6, "w": net_w*0.45, "h": buildable_l*0.4, "color": "#FEF08A"},
                {"name": "صالة طعام رسمية\n(4.5x6.0m)", "x": side_sb, "y": rear_sb + buildable_l*0.3, "w": net_w*0.45, "h": buildable_l*0.3, "color": "#FDE68A"},
                {"name": "مطبخ تحضيري + رئيسي\n(Show & Dirty Kitchen)", "x": side_sb, "y": rear_sb, "w": net_w*0.45, "h": buildable_l*0.3, "color": "#FED7AA"},
                {"name": "صالة معيشة بانورامية كبرى\n(7.0x8.5m)", "x": side_sb + net_w*0.45, "y": rear_sb + buildable_l*0.45, "w": net_w*0.55, "h": buildable_l*0.55, "color": "#BAE6FD"},
                {"name": "جناح كبار السن / الضيوف\n(4.5x5.0m)", "x": side_sb + net_w*0.45, "y": rear_sb, "w": net_w*0.55, "h": buildable_l*0.45, "color": "#E9D5FF"}
            ]
        elif "المقترح 2" in selected_scheme:
            num_units = 2
            bua_factor = 1.80
            uw = net_w / 2
            rooms = [
                {"name": "فيلا 1: مجلس واستقبال", "x": side_sb, "y": rear_sb + buildable_l*0.5, "w": uw, "h": buildable_l*0.5, "color": "#BBF7D0"},
                {"name": "فيلا 1: معيشة ومطبخ وضيافة", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.5, "color": "#DCFCE7"},
                {"name": "فيلا 2: مجلس واستقبال", "x": side_sb + uw, "y": rear_sb + buildable_l*0.5, "w": uw, "h": buildable_l*0.5, "color": "#BAE6FD"},
                {"name": "فيلا 2: معيشة ومطبخ وضيافة", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.5, "color": "#E0F2FE"}
            ]
        elif "المقترح 3" in selected_scheme:
            num_units = 3
            bua_factor = 1.80
            uw = net_w / 3
            rooms = [
                {"name": f"تاون هاوس {i+1}\nمعيشة واستقبال\nومطبخ", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l, "color": "#FEF9C3"} for i in range(3)
            ]
        elif "المقترح 4" in selected_scheme:
            num_units = 4
            bua_factor = 1.75
            uw = net_w / 4
            rooms = [
                {"name": f"وحدة {i+1}\nدوبلكس\n(G+1)", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l, "color": "#FEE2E2"} for i in range(4)
            ]
        else:
            num_units = 1
            bua_factor = 1.90
            main_l = buildable_l * 0.70
            serv_l = buildable_l * 0.22
            gap = buildable_l * 0.08
            rooms = [
                {"name": "الفيلا الرئيسية:\nمعيشة عائلية وأجنحة النوم", "x": side_sb, "y": rear_sb, "w": net_w, "h": main_l, "color": "#E0E7FF"},
                {"name": "ملحق الخدمات:\nمطبخ ولائم + مجلس خارجي وسكن عمالة", "x": side_sb, "y": rear_sb + main_l + gap, "w": net_w*0.75, "h": serv_l, "color": "#DDD6FE"}
            ]

        calc_total_bua = round(effective_ground * bua_factor, 2)

        # رسم المسقط المعماري الداخلي
        fig, ax = plt.subplots(figsize=(10, 8))
        # سور الأرض
        ax.add_patch(patches.Rectangle((0, 0), width, length, linewidth=2.5, edgecolor='black', facecolor='#F8FAFC', label='حدود الأرض (Plot Boundary)'))
        # خط الارتداد
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=1.5, edgecolor='red', linestyle='--', facecolor='none', label='خط الارتداد المسموح'))

        # رسم الفراغات الداخلية
        for r in rooms:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=1.8, edgecolor='#1E293B', facecolor=r["color"], alpha=0.85))
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["name"], ha='center', va='center', fontsize=8.5, weight='bold', color='#0F172A')

        ax.set_xlim(-width * 0.1, width * 1.1)
        ax.set_ylim(-length * 0.08, length * 1.15)
        ax.set_aspect('equal')
        ax.set_xlabel("العرض على الشارع (متر)")
        ax.set_ylabel("عمق الأرض (متر)")
        ax.set_title(f"المسقط المعماري والتقسيم الداخلي - {selected_scheme.split(':')[0]}", fontsize=11, weight='bold')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, linestyle=':', alpha=0.5)

        ax.annotate('الشارع الرئيسي / الواجهة (Street)', xy=(width/2, length), xytext=(width/2, length + 2),
                    ha='center', fontsize=10, weight='bold', color='darkgreen',
                    arrowprops=dict(arrowstyle="->", color='darkgreen', lw=1.5))
        st.pyplot(fig)

        # أزرار التصدير
        c_dxf, c_img = st.columns(2)
        with c_dxf:
            try:
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                doc.layers.add(name="PLOT_LIMITS", color=7)
                msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_LIMITS'})
                doc.layers.add(name="SETBACKS", color=1)
                msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
                doc.layers.add(name="INTERNAL_WALLS", color=4)
                for r in rooms:
                    msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'INTERNAL_WALLS'})
                    msp.add_text(r["name"].replace('\n', ' '), dxfattribs={'layer': 'INTERNAL_WALLS', 'height': 0.6}).set_placement((r["x"]+0.5, r["y"]+r["h"]/2))

                dxf_stream = io.StringIO()
                doc.write(dxf_stream)
                st.download_button(
                    label=f"💾 تحميل المخطط المعماري الداخلي بصيغة AutoCAD (.DXF)",
                    data=dxf_stream.getvalue().encode('utf-8'),
                    file_name=f"Architectural_Layout_{width}x{length}.dxf",
                    mime="application/dxf"
                )
            except Exception as e:
                st.error(f"خطأ DXF: {e}")

        with c_img:
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight')
            img_buf.seek(0)
            st.download_button(
                label="📄 تحميل المسقط المعماري كصورة هندسية عالية الدقة",
                data=img_buf,
                file_name=f"Floor_Plan_{width}x{length}.png",
                mime="image/png"
            )

    with tab3:
        st.subheader("📋 المخططات التنفيذية للخدمات والدفاع المدني (MEP & Life Safety Set)")
        
        mep_view = st.radio("اختر المخطط الخدمي المطلوب عرضه وتوليده:", [
            "1. مخطط الدفاع المدني والسلامة (Civil Defence & Life Safety)",
            "2. مخطط التغذية والصرف الصحي (Plumbing & Drainage)",
            "3. المخطط الكهربائي وتوزيع الإنارة والأحمال (Electrical Layout)",
            "4. مخطط التكييف ومجاري الهواء (HVAC Ducting)"
        ])

        fig_mep, ax_m = plt.subplots(figsize=(10, 8))
        ax_m.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, buildable_l, linewidth=2, edgecolor='black', facecolor='#F1F5F9'))
        
        # رسم الحوائط الفاصلة كخلفية خفيفة
        for r in rooms:
            ax_m.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=1, edgecolor='#94A3B8', facecolor='none', linestyle=':'))
            ax_m.text(r["x"] + r["w"]/2, r["y"] + r["h"]*0.85, r["name"].split('\n')[0], ha='center', fontsize=7, color='#64748B')

        if "الدفاع المدني" in mep_view:
            st.markdown("#### مخطط السلامة والدفاع المدني (UAE Fire and Life Safety Code)")
            # كواشف الدخان ومطافئ الحريق ومسارات الهروب
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]/2, r["y"] + r["h"]/2, marker='o', markersize=8, color='red', label='كاشف دخان' if r == rooms[0] else "")
            ax_m.plot(side_sb + net_w*0.5, rear_sb + buildable_l, marker='s', markersize=10, color='darkred', label='طفاية حريق DCP 6kg')
            ax_m.annotate('مسار الهروب الرئيسي (Exit)', xy=(side_sb + net_w*0.5, rear_sb + buildable_l), xytext=(side_sb + net_w*0.5, rear_sb + buildable_l + 3),
                          ha='center', fontsize=9, weight='bold', color='red',
                          arrowprops=dict(arrowstyle="->", color='red', lw=2))
            st.write("- **كواشف الدخان:** كواشف بصرية معنونة بكل غرفة وممر.")
            st.write("- **الأبواب المقاومة للحريق:** أبواب FD-60 تفصل المطبخ والخدمات عن مسار الهروب.")

        elif "الصرف" in mep_view:
            st.markdown("#### مخطط شبكة الصرف الصحي ومياه الشرب")
            # غرف تفتيش وخطوط الصرف
            ax_m.plot([side_sb + 1, side_sb + 1], [rear_sb, rear_sb + buildable_l], color='brown', linewidth=2.5, linestyle='--', label='خط الصرف الصحي الرئيسي (Soil 4")')
            ax_m.plot(side_sb + 1, rear_sb, marker='D', markersize=10, color='brown', label='غرفة تفتيش (Inspection Chamber)')
            ax_m.plot(side_sb + 2, rear_sb + 2, marker='^', markersize=10, color='orange', label='مصيدة شحوم (Grease Trap)')
            st.write("- **نظام الصرف:** شبكتان منفصلتان لمياه المراحيض (Black) ومياه المغاسل (Grey).")
            st.write("- **شبكة التغذية:** مواسير بولي بروبلين حراري (PPR PN20) معزولة بالكامل.")

        elif "الكهربائي" in mep_view:
            est_kw = round(calc_total_bua * 0.12, 1)
            st.markdown(f"#### المخطط الكهربائي - إجمالي الحمل التصميمي: **{est_kw} kW**")
            # لوحة التوزيع ونقاط الإنارة
            ax_m.plot(side_sb + 0.5, rear_sb + buildable_l*0.5, marker='s', markersize=12, color='blue', label='لوحة التوزيع الرئيسية (MDB)')
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]*0.3, r["y"] + r["h"]*0.5, marker='*', markersize=8, color='gold')
                ax_m.plot(r["x"] + r["w"]*0.7, r["y"] + r["h"]*0.5, marker='*', markersize=8, color='gold', label='نقاط إنارة LED' if r == rooms[0] else "")
            st.write("- **تأريض المنشأة:** شبكة نحاسية تحقق مقاومة أقل من 1 أوم.")
            st.write("- **حماية القواطع:** قواطع ELCB حساسة 30mA للغرف الرطبة و 100mA للدوائر العامة.")

        else: # التكييف
            est_tr = round(calc_total_bua / 14.5, 1)
            st.markdown(f"#### مخطط التكييف ومجاري الهواء - الحمل الحراري: **{est_tr} TR**")
            # مسارات الدكت ووحدات FCU
            for r in rooms:
                ax_m.add_patch(patches.Rectangle((r["x"] + r["w"]*0.2, r["y"] + r["h"]*0.4), r["w"]*0.6, r["h"]*0.2, facecolor='#38BDF8', edgecolor='blue', alpha=0.6, label='مجاري الهواء والدكت (Duct)' if r == rooms[0] else ""))
                ax_m.plot(r["x"] + r["w"]*0.5, r["y"] + r["h"]*0.5, marker='o', markersize=6, color='darkblue', label='مخرج هواء (Diffuser)' if r == rooms[0] else "")
            st.write("- **النظام المقترح:** وحدات دكت سبليت Inverter موفرة للطاقة مع مخارج هواء طولية Linear Slots.")

        ax_m.set_xlim(side_sb - 2, side_sb + net_w + 2)
        ax_m.set_ylim(rear_sb - 2, rear_sb + buildable_l + 4)
        ax_m.set_aspect('equal')
        ax_m.legend(loc='upper right', fontsize=8)
        ax_m.grid(True, linestyle=':', alpha=0.4)
        st.pyplot(fig_mep)

    with tab4:
        st.subheader("النظام الإنشائي ومواصفات التأسيس")
        found_rec = "أساس حصيري مسلح (Raft Foundation)" if actual_sbc < 140 or num_units >= 3 else "قواعد منفصلة مسلحة (Isolated Footings) متصلة بميدات ربط جاسئة"
        st.info(f"**نظام الأساسات الموصى به:** {found_rec} (جهد التربة: {actual_sbc} kN/m²)")
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            st.markdown("**مواصفات الخرسانة والمواد (Substructure):**")
            st.write("- الأساسات والميدات الملامسة للتربة: خرسانة مقاومة للكبريتات SRC رتبة C40 مع نسبة W/C لا تتجاوز 0.40.")
            st.write("- عزل مائي: لفائف بيتومينية مسلحة 4 مم طبقتين مع ألواح حماية قبل الردم.")
            st.write("- حديد التسليح: إجهاد خضوع 500 MPa مشوه عالي المقاومة.")
        with col_st2:
            st.markdown("**مواصفات الهيكل العلوي (Superstructure):**")
            st.write("- الأعمدة والأسقف: خرسانة بورتلاندية اعتيادية OPC رتبة C35 إلى C40.")
            st.write("- نظام البلاطات: بلاطات لاكمرية Flat Slab بسماكة 22-24 سم لتفادي سقوط الجسور داخل الغرف والصالات.")

    with tab5:
        st.subheader(f"كراسة حصر الكميات والمواد التقديرية (BOQ) - مسطح البناء {calc_total_bua:.1f} م²")
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
        st.metric("التكلفة التقديرية المبدئية للعظم والهيكل الإنشائي", f"{total_est_cost:,.0f} درهم إماراتي")

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
