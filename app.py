import streamlit as st
import pandas as pd
import json
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch
import ezdxf
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Engineering & Architectural Engine", layout="wide")

st.title("🏗️ المنظومة الهندسية والمعمارية المتكاملة - دولة الإمارات")
st.markdown("توليد المخططات المعمارية المتقنة، المداخل والمخارج، ملفات الأوتوكاد التنفيذية، وحزم التراخيص والكميات.")

# ----------------- الإعدادات الجانبية -----------------
st.sidebar.header("⚙️ إعدادات المشروع")
api_key = st.sidebar.text_input("أدخل Gemini API Key (اختياري للكروكي):", type="password")

emirate = st.sidebar.selectbox(
    "الإمارة / الجهة التنظيمية:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

input_mode = st.radio("طريقة إدخال بيانات الأرض:", ["إدخال أبعاد القسيمة يدوياً", "رفع صورة أو كروكي الأرض (Site Plan)"])

width, length, actual_sbc = 0.0, 0.0, 150.0

if input_mode == "إدخال أبعاد القسيمة يدوياً":
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (متر):", min_value=10.0, max_value=200.0, value=30.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة (متر):", min_value=10.0, max_value=300.0, value=50.0, step=0.5)
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
                width = float(data.get("width", 30.0))
                length = float(data.get("length", 50.0))

# ----------------- تشغيل المنظومة -----------------
if st.button("🚀 تشغيل المنظومة وتوليد المخططات المعمارية الإبداعية"):
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
        "2. المخطط المعماري الإبداعي والمداخل", 
        "3. مخططات الخدمات والدفاع المدني (MEP)", 
        "4. النظام الإنشائي والمواصفات", 
        "5. كراسة الكميات (BOQ)", 
        "6. البرنامج الزمني ومراحل التنفيذ"
    ])

    with tab1:
        st.subheader(f"المحددات التخطيطية واشتراطات البناء - {emirate}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("مساحة القسيمة الإجمالية", f"{plot_area:.1f} م²")
        c2.metric("أبعاد الكتلة الصافية المسموحة", f"{net_w:.1f} × {net_l:.1f} م")
        c3.metric(f"الحد الأقصى للأرضي ({int(max_cov_ratio*100)}%)", f"{effective_ground:.1f} م²")
        c4.metric("عمق الارتداد الأمامي", f"{front_sb:.1f} م")
        st.write(f"**الارتدادات المقررة:** أمامي {front_sb}م | خلفي {rear_sb}م | جانبي {side_sb}م من الجانبين")

    with tab2:
        st.subheader("المساقط المعمارية والمداخل المنظمة")
        
        selected_scheme = st.selectbox(
            "اختر النموذج المعماري المطلوب عرضه:",
            [
                "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات متلاصقة استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات خارجي منفصل (Villa + Outbuilding Block)"
            ]
        )

        buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
        
        # تجهيز الغرف، الأبواب، والمداخل للمقترح 1 ومقترحات المنظومة
        rooms = []
        doors = []
        access_points = []
        num_units = 1
        bua_factor = 1.85

        if "المقترح 1" in selected_scheme:
            # تقسيم هندسي واضح مع ممر توزيع وموزع استقبال
            rooms = [
                {"name": "مجلس رجال رسمي\nMajlis", "dim": "6.0 x 8.5 m", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "fc": "#FEF3C7", "ec": "#D97706"},
                {"name": "صالة طعام رسمية\nDining Room", "dim": "4.5 x 6.0 m", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "fc": "#FDE68A", "ec": "#D97706"},
                {"name": "مطبخ رئيسي وتحضيري\nKitchen & Pantry", "dim": "4.5 x 5.0 m", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "fc": "#FED7AA", "ec": "#EA580C"},
                {"name": "صالة معيشة بانورامية كبرى\nLiving Family Area", "dim": "7.0 x 8.5 m", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "fc": "#BAE6FD", "ec": "#0284C7"},
                {"name": "جناح كبار السن / ضيوف\nMaster Suite (G)", "dim": "4.5 x 5.0 m", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "fc": "#E9D5FF", "ec": "#9333EA"}
            ]
            doors = [
                {"x": side_sb + net_w*0.24, "y": rear_sb + buildable_l, "r": 1.2, "theta1": 180, "theta2": 270}, # باب مجلس
                {"x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.50, "r": 1.0, "theta1": 90, "theta2": 180}, # باب داخلي
                {"x": side_sb + net_w*0.74, "y": rear_sb + buildable_l, "r": 1.4, "theta1": 270, "theta2": 360}, # باب معيشة
                {"x": side_sb, "y": rear_sb + buildable_l*0.15, "r": 1.0, "theta1": 0, "theta2": 90}, # باب خدمة مطبخ
                {"x": side_sb + net_w*0.74, "y": rear_sb, "r": 1.2, "theta1": 90, "theta2": 180} # باب خلفي للحديقة
            ]
            access_points = [
                {"txt": "المدخل الرسمي للضيوف\nGuest Entrance", "pos": (side_sb + net_w*0.24, rear_sb + buildable_l + 3.5), "target": (side_sb + net_w*0.24, rear_sb + buildable_l), "c": "#B45309"},
                {"txt": "المدخل العائلي الرئيسي\nFamily Entrance", "pos": (side_sb + net_w*0.74, rear_sb + buildable_l + 3.5), "target": (side_sb + net_w*0.74, rear_sb + buildable_l), "c": "#0369A1"},
                {"txt": "مدخل الخدمة والمطبخ\nService Entry", "pos": (side_sb - 2.5, rear_sb + buildable_l*0.15), "target": (side_sb, rear_sb + buildable_l*0.15), "c": "#C2410C"},
                {"txt": "مخرج الحديقة والمسبح\nGarden / Terrace", "pos": (side_sb + net_w*0.74, rear_sb - 2.5), "target": (side_sb + net_w*0.74, rear_sb), "c": "#15803D"}
            ]
        elif "المقترح 2" in selected_scheme:
            num_units = 2
            bua_factor = 1.80
            uw = net_w / 2
            rooms = [
                {"name": "فيلا 1: مجلس واستقبال\nVilla 1: Majlis", "dim": f"{uw:.1f} x {buildable_l*0.5:.1f} m", "x": side_sb, "y": rear_sb + buildable_l*0.5, "w": uw, "h": buildable_l*0.5, "fc": "#DCFCE7", "ec": "#16A34A"},
                {"name": "فيلا 1: معيشة ومطبخ\nVilla 1: Living & Kitchen", "dim": f"{uw:.1f} x {buildable_l*0.5:.1f} m", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.5, "fc": "#F0FDF4", "ec": "#16A34A"},
                {"name": "فيلا 2: مجلس واستقبال\nVilla 2: Majlis", "dim": f"{uw:.1f} x {buildable_l*0.5:.1f} m", "x": side_sb + uw, "y": rear_sb + buildable_l*0.5, "w": uw, "h": buildable_l*0.5, "fc": "#E0F2FE", "ec": "#0284C7"},
                {"name": "فيلا 2: معيشة ومطبخ\nVilla 2: Living & Kitchen", "dim": f"{uw:.1f} x {buildable_l*0.5:.1f} m", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.5, "fc": "#F0F9FF", "ec": "#0284C7"}
            ]
            access_points = [
                {"txt": "مدخل فيلا 1 (Entrance 1)", "pos": (side_sb + uw*0.5, rear_sb + buildable_l + 3.5), "target": (side_sb + uw*0.5, rear_sb + buildable_l), "c": "#15803D"},
                {"txt": "مدخل فيلا 2 (Entrance 2)", "pos": (side_sb + uw*1.5, rear_sb + buildable_l + 3.5), "target": (side_sb + uw*1.5, rear_sb + buildable_l), "c": "#0369A1"}
            ]
        elif "المقترح 3" in selected_scheme:
            num_units = 3
            bua_factor = 1.80
            uw = net_w / 3
            rooms = [
                {"name": f"تاون هاوس {i+1}\nTownhouse {i+1}", "dim": f"{uw:.1f} x {buildable_l:.1f} m", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l, "fc": "#FEF9C3", "ec": "#CA8A04"} for i in range(3)
            ]
            access_points = [
                {"txt": f"مدخل TH {i+1}", "pos": (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.5), "target": (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "c": "#CA8A04"} for i in range(3)
            ]
        elif "المقترح 4" in selected_scheme:
            num_units = 4
            bua_factor = 1.75
            uw = net_w / 4
            rooms = [
                {"name": f"وحدة {i+1}\nUnit {i+1}", "dim": f"{uw:.1f} x {buildable_l:.1f} m", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l, "fc": "#FEE2E2", "ec": "#DC2626"} for i in range(4)
            ]
            access_points = [
                {"txt": f"مدخل {i+1}", "pos": (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.5), "target": (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "c": "#DC2626"} for i in range(4)
            ]
        else:
            num_units = 1
            bua_factor = 1.90
            main_l = buildable_l * 0.70
            serv_l = buildable_l * 0.22
            gap = buildable_l * 0.08
            rooms = [
                {"name": "الفيلا الرئيسية (سكن العائلة)\nMain Family Residence", "dim": f"{net_w:.1f} x {main_l:.1f} m", "x": side_sb, "y": rear_sb, "w": net_w, "h": main_l, "fc": "#EEF2FF", "ec": "#4338CA"},
                {"name": "ملحق الخدمات والمجلس الخارجي\nOutbuilding & Services", "dim": f"{net_w*0.75:.1f} x {serv_l:.1f} m", "x": side_sb, "y": rear_sb + main_l + gap, "w": net_w*0.75, "h": serv_l, "fc": "#F3E8FF", "ec": "#7E22CE"}
            ]
            access_points = [
                {"txt": "مدخل مجلس الضيوف الخارجي", "pos": (side_sb + net_w*0.35, rear_sb + buildable_l + 3.5), "target": (side_sb + net_w*0.35, rear_sb + buildable_l), "c": "#7E22CE"},
                {"txt": "المدخل العائلي الخاص", "pos": (side_sb + net_w*0.85, rear_sb + main_l + 2.0), "target": (side_sb + net_w*0.85, rear_sb + main_l), "c": "#4338CA"}
            ]

        calc_total_bua = round(effective_ground * bua_factor, 2)

        # ----------------- لوحة الرسم الهندسي المتطورة -----------------
        fig, ax = plt.subplots(figsize=(11, 13), dpi=200)

        # خلفية أنيقة وحدود القسيمة
        plot_rect = patches.Rectangle((0, 0), width, length, linewidth=3.0, edgecolor='#0F172A', facecolor='#F8FAFC', label='حدود القسيمة (Plot Boundary)')
        ax.add_patch(plot_rect)

        # خط الارتداد المسموح
        setback_rect = patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none', label='خط الارتداد المسموح (Setback Line)')
        ax.add_patch(setback_rect)

        # رسم الفراغات المعمارية مع علامات الحدود
        for r in rooms:
            # البلاطة المعمارية
            room_patch = patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=2.2, edgecolor=r["ec"], facecolor=r["fc"], alpha=0.9)
            ax.add_patch(room_patch)

            # صندوق البيانات الداخلي المنسق
            text_box_props = dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor=r["ec"], alpha=0.9, lw=1.2)
            content = f"{r['name']}\n[{r['dim']}]"
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, content, ha='center', va='center', fontsize=9.5, weight='bold', color='#1E293B', bbox=text_box_props)

        # رسم الأبواب ومسار الفتح المعماري (Door Swings)
        for d in doors:
            ax.add_patch(Arc((d["x"], d["y"]), d["r"]*2, d["r"]*2, angle=0, theta1=d["theta1"], theta2=d["theta2"], color='#0F172A', lw=1.5, ls='--'))
            ax.plot([d["x"], d["x"] + d["r"]], [d["y"], d["y"]], color='#0F172A', lw=2.0)

        # توضيح المداخل والمخارج بأسهم بارزة
        for ap in access_points:
            arrow = FancyArrowPatch(ap["pos"], ap["target"], arrowstyle='-|>', mutation_scale=18, color=ap["c"], lw=2.5)
            ax.add_patch(arrow)
            ax.text(ap["pos"][0], ap["pos"][1] + 0.6, ap["txt"], ha='center', va='bottom', fontsize=8.5, weight='bold', color=ap["c"],
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=ap["c"], alpha=0.95, lw=1.0))

        # خط وتحديد الشارع الرئيسي
        ax.annotate('الشارع الرئيسي / الواجهة المعتمدة (Main Access Road)', xy=(width/2, length), xytext=(width/2, length + 2.5),
                    ha='center', fontsize=11, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-width * 0.12, width * 1.12)
        ax.set_ylim(-length * 0.08, length * 1.16)
        ax.set_aspect('equal')
        ax.set_xlabel("عرض الواجهة على الشارع (متر)", fontsize=10, weight='bold')
        ax.set_ylabel("عمق القسيمة الداخلي (متر)", fontsize=10, weight='bold')
        ax.set_title(f"المسقط المعماري المنظم - {selected_scheme.split(':')[0]}\nمسطح الأرضي: {effective_ground:.1f} م² | البناء الكلي: {calc_total_bua:.1f} م²", fontsize=12, weight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
        ax.grid(True, linestyle=':', alpha=0.5)

        st.pyplot(fig)

        # أزرار التصدير (DXF و PNG)
        c_dxf, c_img = st.columns(2)
        with c_dxf:
            try:
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                
                doc.layers.add(name="PLOT_BOUNDARY", color=7)
                msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_BOUNDARY'})

                doc.layers.add(name="SETBACKS", color=1)
                msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})

                doc.layers.add(name="WALLS_AND_ROOMS", color=4)
                doc.layers.add(name="TEXT_ANNOTATIONS", color=2)
                for r in rooms:
                    msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS_AND_ROOMS'})
                    msp.add_text(r["name"].replace('\n', ' '), dxfattribs={'layer': 'TEXT_ANNOTATIONS', 'height': 0.6}).set_placement((r["x"]+0.5, r["y"]+r["h"]/2))

                doc.layers.add(name="ENTRANCES", color=3)
                for ap in access_points:
                    msp.add_text(ap["txt"].replace('\n', ' '), dxfattribs={'layer': 'ENTRANCES', 'height': 0.5}).set_placement((ap["pos"][0], ap["pos"][1]))

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
                file_name=f"Architectural_Plan_{width}x{length}.png",
                mime="image/png"
            )

    # ----------------- TAB 3: مخططات الدفاع المدني و MEP -----------------
    with tab3:
        st.subheader("📋 المخططات التنفيذية للخدمات والدفاع المدني (MEP & Life Safety Set)")
        
        mep_view = st.radio("اختر المخطط الخدمي المطلوب توليده:", [
            "1. مخطط الدفاع المدني والسلامة (Civil Defence & Life Safety)",
            "2. مخطط التغذية والصرف الصحي (Plumbing & Drainage)",
            "3. المخطط الكهربائي وتوزيع الإنارة والأحمال (Electrical Layout)",
            "4. مخطط التكييف ومجاري الهواء (HVAC Ducting)"
        ])

        fig_mep, ax_m = plt.subplots(figsize=(10, 8))
        ax_m.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, buildable_l, linewidth=2, edgecolor='black', facecolor='#F1F5F9'))
        
        for r in rooms:
            ax_m.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=1, edgecolor='#94A3B8', facecolor='none', linestyle=':'))
            ax_m.text(r["x"] + r["w"]/2, r["y"] + r["h"]*0.88, r["name"].split('\n')[0], ha='center', fontsize=7.5, color='#475569', weight='bold')

        if "الدفاع المدني" in mep_view:
            st.markdown("#### مخطط السلامة والدفاع المدني (UAE Fire and Life Safety Code)")
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]/2, r["y"] + r["h"]/2, marker='o', markersize=8, color='red', label='كاشف دخان ضوئي' if r == rooms[0] else "")
            ax_m.plot(side_sb + net_w*0.24, rear_sb + buildable_l, marker='s', markersize=10, color='darkred', label='طفاية حريق DCP 6kg')
            ax_m.annotate('مسار الهروب المعتمد (Exit)', xy=(side_sb + net_w*0.24, rear_sb + buildable_l), xytext=(side_sb + net_w*0.24, rear_sb + buildable_l + 3.0),
                          ha='center', fontsize=9, weight='bold', color='red',
                          arrowprops=dict(arrowstyle="->", color='red', lw=2))
            st.write("- **كواشف الدخان:** كواشف بصرية معنونة موزعة وفق مسافات التغطية النظامية.")
            st.write("- **مقاومة الحريق:** أبواب FD-60 للمطابخ وغرف الخدمات.")

        elif "الصرف" in mep_view:
            st.markdown("#### مخطط الصرف الصحي ومصائد الشحوم وتغذية المياه")
            ax_m.plot([side_sb + 1, side_sb + 1], [rear_sb, rear_sb + buildable_l], color='brown', linewidth=2.5, linestyle='--', label='خط الصرف الرئيسي (Soil 4")')
            ax_m.plot(side_sb + 1, rear_sb, marker='D', markersize=10, color='brown', label='غرفة تفتيش (Inspection Chamber)')
            ax_m.plot(side_sb + 1.5, rear_sb + buildable_l*0.15, marker='^', markersize=10, color='orange', label='مصيدة شحوم (Grease Trap)')
            st.write("- **فصل الصرف:** خطين منفصلين للمياه السوداء والمياه الرمادية.")
            st.write("- **التغذية:** أنابيب بولي بروبلين حراري (PPR PN20) معزولة.")

        elif "الكهربائي" in mep_view:
            est_kw = round(calc_total_bua * 0.12, 1)
            st.markdown(f"#### المخطط الكهربائي - الحمل التصميمي التقديري: **{est_kw} kW**")
            ax_m.plot(side_sb + 0.5, rear_sb + buildable_l*0.5, marker='s', markersize=12, color='blue', label='لوحة التوزيع الرئيسية (MDB)')
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]*0.35, r["y"] + r["h"]*0.5, marker='*', markersize=9, color='gold')
                ax_m.plot(r["x"] + r["w"]*0.65, r["y"] + r["h"]*0.5, marker='*', markersize=9, color='gold', label='نقاط إنارة LED' if r == rooms[0] else "")
            st.write("- **التأريض:** شبكة متكاملة تحقق مقاومة أقل من 1 أوم.")
            st.write("- **القواطع:** ELCB بحساسية 30mA للغرف الرطبة و 100mA للعمومي.")

        else:
            est_tr = round(calc_total_bua / 14.5, 1)
            st.markdown(f"#### مخطط التكييف ومجاري الهواء - الحمل التقديري: **{est_tr} TR**")
            for r in rooms:
                ax_m.add_patch(patches.Rectangle((r["x"] + r["w"]*0.2, r["y"] + r["h"]*0.4), r["w"]*0.6, r["h"]*0.2, facecolor='#38BDF8', edgecolor='blue', alpha=0.6, label='مجاري الهواء والدكت' if r == rooms[0] else ""))
                ax_m.plot(r["x"] + r["w"]*0.5, r["y"] + r["h"]*0.5, marker='o', markersize=6, color='darkblue', label='مخرج هواء (Diffuser)' if r == rooms[0] else "")
            st.write("- **النظام المقترح:** وحدات Inverter دكت سبليت موفرة للطاقة مع مخارج طولية.")

        ax_m.set_xlim(side_sb - 3, side_sb + net_w + 3)
        ax_m.set_ylim(rear_sb - 3, rear_sb + buildable_l + 5)
        ax_m.set_aspect('equal')
        ax_m.legend(loc='upper right', fontsize=8.5)
        ax_m.grid(True, linestyle=':', alpha=0.4)
        st.pyplot(fig_mep)

    # ----------------- TAB 4: النظام الإنشائي -----------------
    with tab4:
        st.subheader("النظام الإنشائي ومواصفات التأسيس")
        found_rec = "أساس حصيري مسلح (Raft Foundation)" if actual_sbc < 140 or num_units >= 3 else "قواعد منفصلة مسلحة (Isolated Footings) متصلة بميدات ربط جاسئة"
        st.info(f"**نظام الأساسات الموصى به:** {found_rec} (جهد التربة: {actual_sbc} kN/m²)")
        c_st1, c_st2 = st.columns(2)
        with c_st1:
            st.markdown("**مواصفات الخرسانة والمواد (Substructure):**")
            st.write("- خرسانة مقاومة للكبريتات SRC رتبة C40 مع نسبة W/C لا تتجاوز 0.40.")
            st.write("- لفائف بيتومينية مسلحة 4 مم طبقتين مع ألواح حماية.")
            st.write("- حديد تسليح عالي المقاومة Grade 500.")
        with c_st2:
            st.markdown("**مواصفات الهيكل العلوي (Superstructure):**")
            st.write("- خرسانة بورتلاندية اعتيادية OPC رتبة C35 إلى C40.")
            st.write("- بلاطات لاكمرية Flat Slab بسماكة 22-24 سم لتحقيق مرونة التوزيع المعماري.")

    # ----------------- TAB 5: كراسة الكميات -----------------
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
            {"البند": "1. أعمال الحفر العام والتسوية", "الوحدة": "م³", "الكمية": excavation_qty, "سعر الوحدة (AED)": 25, "الإجمالي (AED)": round(excavation_qty * 25)},
            {"البند": "2. خرسانة عادية للنظافة (Blinding PCC C20)", "الوحدة": "م³", "الكمية": round(effective_ground * 0.12, 1), "سعر الوحدة (AED)": 270, "الإجمالي (AED)": round(effective_ground * 0.12 * 270)},
            {"البند": "3. خرسانة مسلحة كبريتية للأساسات والميدات (SRC C40)", "الوحدة": "م³", "الكمية": vol_concrete_sub, "سعر الوحدة (AED)": 340, "الإجمالي (AED)": round(vol_concrete_sub * 340)},
            {"البند": "4. خرسانة مسلحة للأعمدة والأسقف (OPC C35/C40)", "الوحدة": "م³", "الكمية": vol_concrete_super, "سعر الوحدة (AED)": 330, "الإجمالي (AED)": round(vol_concrete_super * 330)},
            {"البند": "5. حديد تسليح عالي المقاومة (Grade 500)", "الوحدة": "طن", "الكمية": steel_tonnage, "سعر الوحدة (AED)": 2750, "الإجمالي (AED)": round(steel_tonnage * 2750)},
            {"البند": "6. عزل مائي بيتوميني للأساسات والميدات", "الوحدة": "م²", "الكمية": round(effective_ground * 2.2, 1), "سعر الوحدة (AED)": 45, "الإجمالي (AED)": round(effective_ground * 2.2 * 45)},
            {"البند": "7. أعمال الطابوق الأسمنتي المعزول والداخلي", "الوحدة": "حبة", "الكمية": blocks_qty, "سعر الوحدة (AED)": 3.5, "الإجمالي (AED)": round(blocks_qty * 3.5)},
            {"البند": "8. أعمال اللياسة الإسمنتية الداخلية والخارجية", "الوحدة": "م²", "الكمية": plaster_qty, "سعر الوحدة (AED)": 22, "الإجمالي (AED)": round(plaster_qty * 22)}
        ]
        df_boq = pd.DataFrame(boq_data)
        st.table(df_boq)
        st.metric("التكلفة التقديرية المبدئية للعظم والهيكل الإنشائي", f"{df_boq['الإجمالي (AED)'].sum():,.0f} درهم إماراتي")

    # ----------------- TAB 6: البرنامج الزمني -----------------
    with tab6:
        st.subheader("البرنامج الزمني ومسار التنفيذ والاعتمادات")
        base_weeks = 52 if num_units <= 2 else 64
        st.info(f"**المدة الزمنية المقدرة للمشروع:** من {base_weeks - 4} إلى {base_weeks + 4} أسبوعاً.")
        schedule_items = [
            {"المرحلة": "1. التراخيص وفحص التربة وشهادات NOC", "المدة": "4 - 6 أسابيع", "الوزن": "5%", "الجهة المسؤولة": "البلدية / هيئة الكهرباء والمياه"},
            {"المرحلة": "2. أعمال الحفر، صبة النظافة، وعزل القواعد", "المدة": "3 - 4 أسابيع", "الوزن": "10%", "الجهة المسؤولة": "مهندس الإشراف الاستشاري"},
            {"المرحلة": "3. القواعد والميدات والردم المعتمد (Substructure)", "المدة": "4 - 5 أسابيع", "الوزن": "15%", "الجهة المسؤولة": "الاستشاري + مختبر التربة"},
            {"المرحلة": "4. الهيكل الخرساني العظم والمباني (Superstructure)", "المدة": "12 - 16 أسبوعاً", "الوزن": "30%", "الجهة المسؤولة": "مهندس الاستشاري والبلدية"},
            {"المرحلة": "5. التمديدات الكهروميكانيكية (MEP) والعوازل", "المدة": "8 - 10 أسابيع", "الوزن": "15%", "الجهة المسؤولة": "هيئة الكهرباء والمياه والدفاع المدني"},
            {"المرحلة": "6. التشطيبات المعمارية والأرضيات والواجهات", "المدة": "12 - 14 أسبوعاً", "الوزن": "20%", "الجهة المسؤولة": "المالك والاستشاري"},
            {"المرحلة": "7. الفحص النهائي، إطلاق التيار، وشهادة الإنجاز", "المدة": "3 - 4 أسابيع", "الوزن": "5%", "الجهة المسؤولة": "البلدية وإدارة الدفاع المدني"}
        ]
        st.table(pd.DataFrame(schedule_items))
