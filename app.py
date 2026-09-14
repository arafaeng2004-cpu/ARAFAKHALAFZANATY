import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Ellipse, Polygon
import ezdxf
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Luxury Architecture & Engineering Suite", layout="wide")

st.title("🏛️ المنظومة المعمارية والهندسية المتكاملة - مشاريع الإمارات")
st.markdown("توليد المساقط المعمارية المتقنة، المناظير والواجهات الإبداعية، حزم تراخيص الدفاع المدني، والكميات التنفيذية.")

# ----------------- إعدادات القسيمة -----------------
st.sidebar.header("⚙️ معايير الأرض والبلدية")
emirate = st.sidebar.selectbox(
    "الإمارة / الجهة التنظيمية:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

api_key = st.sidebar.text_input("Gemini API Key (لقراءة الكروكي):", type="password")

input_mode = st.radio("تحديد بيانات القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع صورة مخطط الأرض (الكروكي)"])

width, length, actual_sbc = 0.0, 0.0, 150.0

if input_mode == "إدخال أبعاد القسيمة يدوياً":
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (W بالمتر):", min_value=12.0, max_value=200.0, value=30.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة الداخلي (L بالمتر):", min_value=15.0, max_value=300.0, value=50.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=60.0, max_value=400.0, value=150.0, step=10.0)
else:
    uploaded_file = st.file_uploader("ارفع صورة الكروكي (PNG / JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        if not api_key:
            st.warning("يرجى إدخال API Key في القائمة الجانبية لقراءة الصورة.")
        else:
            if st.button("🔍 قراءة أبعاد الأرض من الكروكي"):
                client = genai.Client(api_key=api_key)
                image = Image.open(uploaded_file)
                st.image(image, caption="الكروكي المرفوع", width=320)
                with st.spinner("جاري استخراج الأبعاد البلدية..."):
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

# ----------------- المعالجة المعمارية -----------------
if st.button("🚀 توليد المقترحات والمناظير الإبداعية بالكامل"):
    plot_area = round(width * length, 2)

    # الارتدادات البلدية القياسية
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
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

    tab_arch, tab_3d, tab_mep, tab_str, tab_boq = st.tabs([
        "1. المسقط المعماري الإبداعي المنسق",
        "2. المنظور والواجهة المعمارية 3D",
        "3. مخططات الخدمات والدفاع المدني",
        "4. النظام الإنشائي ومحددات الكود",
        "5. كراسة الكميات والبرنامج الزمني"
    ])

    with tab_arch:
        selected_scheme = st.selectbox(
            "اختر النموذج المعماري المطلوب عرضه:",
            [
                "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات متلاصقة استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات منفصل (Villa + Outbuilding Block)"
            ]
        )

        rooms, doors, access_points = [], [], []

        if "المقترح 1" in selected_scheme:
            num_units = 1
            bua_factor = 1.85
            rooms = [
                {"name": "مجلس رجال رسمي\nMajlis", "dim": "6.0 x 8.5 m", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "fc": "#FEF3C7", "ec": "#D97706"},
                {"name": "صالة طعام رسمية\nDining Room", "dim": "4.5 x 6.0 m", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "fc": "#FDE68A", "ec": "#D97706"},
                {"name": "مطبخ رئيسي وتحضيري\nKitchen & Pantry", "dim": "4.5 x 5.0 m", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "fc": "#FED7AA", "ec": "#EA580C"},
                {"name": "صالة معيشة بانورامية كبرى\nLiving Family Area", "dim": "7.0 x 8.5 m", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "fc": "#BAE6FD", "ec": "#0284C7"},
                {"name": "جناح كبار السن / ضيوف\nMaster Suite (G)", "dim": "4.5 x 5.0 m", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "fc": "#E9D5FF", "ec": "#9333EA"}
            ]
            doors = [
                {"x": side_sb + net_w*0.24, "y": rear_sb + buildable_l, "r": 1.2, "theta1": 180, "theta2": 270},
                {"x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.50, "r": 1.0, "theta1": 90, "theta2": 180},
                {"x": side_sb + net_w*0.74, "y": rear_sb + buildable_l, "r": 1.4, "theta1": 270, "theta2": 360},
                {"x": side_sb, "y": rear_sb + buildable_l*0.15, "r": 1.0, "theta1": 0, "theta2": 90},
                {"x": side_sb + net_w*0.74, "y": rear_sb, "r": 1.2, "theta1": 90, "theta2": 180}
            ]
            access_points = [
                {"txt": "المدخل الرسمي للضيوف\nGuest Entrance", "pos": (side_sb + net_w*0.24, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.24, rear_sb + buildable_l), "c": "#B45309"},
                {"txt": "المدخل العائلي الرئيسي\nFamily Entrance", "pos": (side_sb + net_w*0.74, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.74, rear_sb + buildable_l), "c": "#0369A1"},
                {"txt": "مدخل الخدمة والمطبخ\nService Entry", "pos": (side_sb - 2.8, rear_sb + buildable_l*0.15), "target": (side_sb, rear_sb + buildable_l*0.15), "c": "#C2410C"},
                {"txt": "مخرج الحديقة والمسبح\nGarden / Terrace", "pos": (side_sb + net_w*0.74, rear_sb - 2.8), "target": (side_sb + net_w*0.74, rear_sb), "c": "#15803D"}
            ]
        elif "المقترح 2" in selected_scheme:
            num_units = 2
            bua_factor = 1.80
            uw = net_w / 2
            rooms = [
                {"name": "فيلا 1: مجلس ضيوف\nVilla 1: Majlis", "dim": f"{uw*0.9:.1f} x {buildable_l*0.4:.1f} m", "x": side_sb, "y": rear_sb + buildable_l*0.6, "w": uw, "h": buildable_l*0.4, "fc": "#DCFCE7", "ec": "#16A34A"},
                {"name": "فيلا 1: صالة عائلية ومطبخ\nVilla 1: Living & Kitchen", "dim": f"{uw*0.9:.1f} x {buildable_l*0.6:.1f} m", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.6, "fc": "#F0FDF4", "ec": "#16A34A"},
                {"name": "فيلا 2: مجلس ضيوف\nVilla 2: Majlis", "dim": f"{uw*0.9:.1f} x {buildable_l*0.4:.1f} m", "x": side_sb + uw, "y": rear_sb + buildable_l*0.6, "w": uw, "h": buildable_l*0.4, "fc": "#E0F2FE", "ec": "#0284C7"},
                {"name": "فيلا 2: صالة عائلية ومطبخ\nVilla 2: Living & Kitchen", "dim": f"{uw*0.9:.1f} x {buildable_l*0.6:.1f} m", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.6, "fc": "#F0F9FF", "ec": "#0284C7"}
            ]
            doors = [
                {"x": side_sb + uw*0.45, "y": rear_sb + buildable_l, "r": 1.2, "theta1": 180, "theta2": 270},
                {"x": side_sb + uw*1.45, "y": rear_sb + buildable_l, "r": 1.2, "theta1": 270, "theta2": 360}
            ]
            access_points = [
                {"txt": "مدخل فيلا 1 المستقل\nVilla 1 Entry", "pos": (side_sb + uw*0.45, rear_sb + buildable_l + 3.2), "target": (side_sb + uw*0.45, rear_sb + buildable_l), "c": "#15803D"},
                {"txt": "مدخل فيلا 2 المستقل\nVilla 2 Entry", "pos": (side_sb + uw*1.45, rear_sb + buildable_l + 3.2), "target": (side_sb + uw*1.45, rear_sb + buildable_l), "c": "#0369A1"}
            ]
        elif "المقترح 3" in selected_scheme:
            num_units = 3
            bua_factor = 1.80
            uw = net_w / 3
            rooms = [
                {"name": f"تاون هاوس {i+1}\nمجلس ومعيشة مفتوحة", "dim": f"{uw:.1f} x {buildable_l*0.6:.1f} m", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.4, "w": uw, "h": buildable_l*0.6, "fc": "#FEF9C3", "ec": "#CA8A04"} for i in range(3)
            ] + [
                {"name": f"تاون هاوس {i+1}\nمطبخ وحديقة خاصة", "dim": f"{uw:.1f} x {buildable_l*0.4:.1f} m", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.4, "fc": "#FEF08A", "ec": "#CA8A04"} for i in range(3)
            ]
            doors = [{"x": side_sb + (i+0.5)*uw, "y": rear_sb + buildable_l, "r": 1.1, "theta1": 180, "theta2": 270} for i in range(3)]
            access_points = [{"txt": f"مدخل تاون هاوس {i+1}\nTH {i+1} Entry", "pos": (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.2), "target": (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "c": "#CA8A04"} for i in range(3)]
        elif "المقترح 4" in selected_scheme:
            num_units = 4
            bua_factor = 1.75
            uw = net_w / 4
            rooms = [
                {"name": f"وحدة دوبلكس {i+1}\nمعيشة ومطبخ (G)", "dim": f"{uw:.1f} x {buildable_l:.1f} m", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l, "fc": "#FEE2E2", "ec": "#DC2626"} for i in range(4)
            ]
            doors = [{"x": side_sb + (i+0.5)*uw, "y": rear_sb + buildable_l, "r": 1.0, "theta1": 180, "theta2": 270} for i in range(4)]
            access_points = [{"txt": f"مدخل دوبلكس {i+1}\nUnit {i+1}", "pos": (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.2), "target": (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "c": "#DC2626"} for i in range(4)]
        else:
            num_units = 1
            bua_factor = 1.90
            main_l = buildable_l * 0.70
            serv_l = buildable_l * 0.22
            gap = buildable_l * 0.08
            rooms = [
                {"name": "الفيلا العائلية الرئيسية\nMain Residence (G+1)", "dim": f"{net_w:.1f} x {main_l:.1f} m", "x": side_sb, "y": rear_sb, "w": net_w, "h": main_l, "fc": "#EEF2FF", "ec": "#4338CA"},
                {"name": "ملحق الخدمات ومجلس الضيوف\nMajlis & Services Block", "dim": f"{net_w*0.75:.1f} x {serv_l:.1f} m", "x": side_sb, "y": rear_sb + main_l + gap, "w": net_w*0.75, "h": serv_l, "fc": "#F3E8FF", "ec": "#7E22CE"}
            ]
            doors = [
                {"x": side_sb + net_w*0.37, "y": rear_sb + buildable_l, "r": 1.3, "theta1": 180, "theta2": 270},
                {"x": side_sb + net_w*0.5, "y": rear_sb + main_l, "r": 1.3, "theta1": 270, "theta2": 360}
            ]
            access_points = [
                {"txt": "مدخل مجلس الضيوف الخارجي\nOutbuilding Guest Majlis", "pos": (side_sb + net_w*0.37, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.37, rear_sb + buildable_l), "c": "#7E22CE"},
                {"txt": "المدخل العائلي الخاص\nMain Villa Family Entry", "pos": (side_sb + net_w*0.85, rear_sb + main_l + 2.5), "target": (side_sb + net_w*0.85, rear_sb + main_l), "c": "#4338CA"}
            ]

        calc_total_bua = round(effective_ground * bua_factor, 2)

        # ----------------- لوحة المسقط المعماري -----------------
        fig, ax = plt.subplots(figsize=(10, 13), dpi=220)

        # حدود القسيمة وخط الارتداد
        plot_rect = patches.Rectangle((0, 0), width, length, linewidth=3.0, edgecolor='#0F172A', facecolor='#F8FAFC', label='حدود القسيمة (Plot Boundary)')
        ax.add_patch(plot_rect)

        setback_rect = patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none', label='خط الارتداد المسموح (Setback Line)')
        ax.add_patch(setback_rect)

        # رسم الفراغات المعمارية
        for r in rooms:
            room_patch = patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=2.2, edgecolor=r["ec"], facecolor=r["fc"], alpha=0.92)
            ax.add_patch(room_patch)

            box_props = dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor=r["ec"], alpha=0.95, lw=1.2)
            content = f"{r['name']}\n[{r['dim']}]"
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, content, ha='center', va='center', fontsize=9.2, weight='bold', color='#1E293B', bbox=box_props)

        # رسم مسار فتح الأبواب
        for d in doors:
            ax.add_patch(Arc((d["x"], d["y"]), d["r"]*2, d["r"]*2, angle=0, theta1=d["theta1"], theta2=d["theta2"], color='#0F172A', lw=1.6, ls='--'))
            ax.plot([d["x"], d["x"] + d["r"]], [d["y"], d["y"]], color='#0F172A', lw=2.2)

        # رسم المداخل والمخارج
        for ap in access_points:
            arrow = FancyArrowPatch(ap["pos"], ap["target"], arrowstyle='-|>', mutation_scale=18, color=ap["c"], lw=2.4)
            ax.add_patch(arrow)
            ax.text(ap["pos"][0], ap["pos"][1] + 0.6, ap["txt"], ha='center', va='bottom', fontsize=8.5, weight='bold', color=ap["c"],
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=ap["c"], alpha=0.95, lw=1.0))

        # مسمى الشارع الرئيسي
        ax.annotate('الشارع الرئيسي / الواجهة المعتمدة (Main Access Road)', xy=(width/2, length), xytext=(width/2, length + 2.6),
                    ha='center', fontsize=11, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-width * 0.12, width * 1.12)
        ax.set_ylim(-length * 0.08, length * 1.16)
        ax.set_aspect('equal')
        ax.set_xlabel("عرض الواجهة على الشارع (متر)", fontsize=10, weight='bold')
        ax.set_ylabel("عمق القسيمة الداخلي (متر)", fontsize=10, weight='bold')
        ax.set_title(f"المسقط المعماري المنظم - {selected_scheme.split(':')[0]}\nمسطح الأرضي: {effective_ground:.1f} م² | البناء الكلي: {calc_total_bua:.1f} م²", fontsize=11.5, weight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
        ax.grid(True, linestyle=':', alpha=0.45)
        st.pyplot(fig)

        # زر تحميل AutoCAD DXF
        try:
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="PLOT_BOUNDARY", color=7)
            msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_BOUNDARY'})
            doc.layers.add(name="SETBACKS", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
            doc.layers.add(name="ROOMS_WALLS", color=4)
            for r in rooms:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'ROOMS_WALLS'})
            dxf_stream = io.StringIO()
            doc.write(dxf_stream)
            st.download_button(
                label="💾 تحميل المخطط المعماري بصيغة AutoCAD (.DXF)",
                data=dxf_stream.getvalue().encode('utf-8'),
                file_name=f"Floor_Plan_{width}x{length}.dxf",
                mime="application/dxf"
            )
        except Exception as e:
            st.error(f"خطأ DXF: {e}")

    # ----------------- TAB 2: المنظور والواجهة المعمارية 3D -----------------
    with tab_3d:
        st.subheader(f"المنظور الإبداعي والواجهة المعمارية المودرن (3D Elevation Perspective) - {selected_scheme.split(':')[0]}")
        st.info("🎨 **المفهوم التصميمي للواجهة:** طراز إماراتي معاصر (Modern Contemporary Style) يعتمد على البرج الأسطواني الزجاجي مع كتل حجرية بيضاء ورمادية، وحوائط زجاجية كورتن وول (Curtain Wall) مع مظلات ألمنيوم وشاشات خشبية (Louvers).")

        fig_elev, ax_e = plt.subplots(figsize=(11, 7), dpi=220)
        ax_e.set_facecolor("#E0F2FE")

        # أرضية الرصيف والشارع
        ax_e.fill_between([-2, net_w + 4], -1.5, 0, color='#64748B')
        ax_e.fill_between([-2, net_w + 4], -0.2, 0, color='#CBD5E1')

        h_total = 8.5
        b_w = net_w

        # الكتلة الرئيسية من الحجر الأبيض
        ax_e.add_patch(Rectangle((0, 0), b_w, h_total, facecolor='#F8FAFC', edgecolor='#94A3B8', lw=2.0))

        # خطوط الحجر الصناعي الأفقي
        for y_g in np.arange(0.5, h_total, 0.6):
            ax_e.plot([0, b_w], [y_g, y_g], color='#E2E8F0', lw=0.9)

        # برج الدرج الأسطواني الزجاجي
        tower_x = b_w * 0.32
        tower_w = b_w * 0.18
        tower_h = h_total + 1.2
        ax_e.add_patch(Rectangle((tower_x, 0), tower_w, tower_h, facecolor='#E2E8F0', edgecolor='#475569', lw=2.2))
        ax_e.add_patch(Rectangle((tower_x + 0.3, 1.0), tower_w - 0.6, tower_h - 1.8, facecolor='#38BDF8', edgecolor='#0F172A', lw=2.0, alpha=0.85))
        for ty in np.arange(1.0, tower_h - 0.8, 1.2):
            ax_e.plot([tower_x + 0.3, tower_x + tower_w - 0.3], [ty, ty], color='#0F172A', lw=1.5)

        # بوابة المدخل الرئيسي
        ent_x = tower_x + tower_w + 0.8
        ent_w = b_w * 0.16
        ax_e.add_patch(Rectangle((ent_x - 0.2, 0), ent_w + 0.4, 4.2, facecolor='#334155', edgecolor='#0F172A', lw=1.8))
        ax_e.add_patch(Rectangle((ent_x, 0.2), ent_w, 3.2, facecolor='#78350F', edgecolor='#451A03', lw=1.5))
        ax_e.plot([ent_x + ent_w/2, ent_x + ent_w/2], [0.2, 3.4], color='#B45309', lw=2.0)

        # نوافذ المجلس والصالات البانورامية
        w1_x = b_w * 0.05
        w1_w = b_w * 0.22
        ax_e.add_patch(Rectangle((w1_x, 1.0), w1_w, 6.0, facecolor='#38BDF8', edgecolor='#1E293B', lw=2.8, alpha=0.8))
        for wx in np.linspace(w1_x, w1_x + w1_w, 4):
            ax_e.plot([wx, wx], [1.0, 7.0], color='#1E293B', lw=1.5)

        # واجهة الطابق الأول المعلقة واللوفرز الخشبية
        w2_x = ent_x + ent_w + 0.8
        w2_w = b_w - w2_x - 0.8
        if w2_w > 1.5:
            ax_e.add_patch(Rectangle((w2_x, 1.0), w2_w, 6.2, facecolor='#38BDF8', edgecolor='#1E293B', lw=2.5, alpha=0.85))
            for ly in np.arange(1.0, 7.2, 0.5):
                ax_e.plot([w2_x, w2_x + w2_w], [ly, ly], color='#78350F', lw=1.2, alpha=0.7)

        # سترة السطح البانورامية (Parapet)
        ax_e.add_patch(Rectangle((-0.4, h_total), b_w + 0.8, 0.6, facecolor='#1E293B', edgecolor='#0F172A', lw=2.0))

        # معالجة النباتات التجميلية باستخدام Ellipse لتجنب خطأ Arc
        for tx in [-1.0, b_w + 1.2]:
            ax_e.add_patch(Rectangle((tx, 0), 0.3, 1.2, facecolor='#78350F'))
            ax_e.add_patch(Ellipse((tx + 0.15, 2.0), width=1.8, height=2.5, facecolor='#15803D', edgecolor='#166534', lw=1.5))

        ax_e.set_xlim(-3, b_w + 5)
        ax_e.set_ylim(-1.5, h_total + 2.5)
        ax_e.set_aspect('equal')
        ax_e.axis('off')
        st.pyplot(fig_elev)

    # ----------------- TAB 3: مخططات الخدمات والدفاع المدني -----------------
    with tab_mep:
        st.subheader("📋 حزمة المخططات الكهروميكانيكية وتراخيص الدفاع المدني (MEP Set)")
        mep_choice = st.radio("اختر المخطط التنفيذي المطلوب استعراضه:", [
            "1. مخطط الدفاع المدني والسلامة (Civil Defence)",
            "2. مخطط التغذية والصرف الصحي (Plumbing & Drainage)",
            "3. مخطط الأحمال وتوزيع القوى والإنارة (Electrical Set)",
            "4. مخطط التكييف ومجاري الهواء (HVAC Ducting)"
        ])

        fig_m, ax_m = plt.subplots(figsize=(10, 8), dpi=200)
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, linewidth=2, edgecolor='black', facecolor='#F8FAFC'))

        for r in rooms:
            ax_m.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=1.2, edgecolor='#94A3B8', facecolor='none', linestyle=':'))
            ax_m.text(r["x"] + r["w"]/2, r["y"] + r["h"]*0.85, r["name"].split('\n')[0], ha='center', fontsize=7.5, color='#475569', weight='bold')

        if "الدفاع المدني" in mep_choice:
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]/2, r["y"] + r["h"]/2, marker='o', markersize=8, color='red', label='كاشف دخان ضوئي' if r == rooms[0] else "")
            ax_m.plot(side_sb + net_w*0.24, rear_sb + buildable_l, marker='s', markersize=11, color='darkred', label='طفاية حريق DCP 6kg')
            ax_m.annotate('مسار الهروب المعتمد (Exit)', xy=(side_sb + net_w*0.24, rear_sb + buildable_l), xytext=(side_sb + net_w*0.24, rear_sb + buildable_l + 3.0),
                          ha='center', fontsize=9, weight='bold', color='red', arrowprops=dict(arrowstyle="->", color='red', lw=2))
        elif "الصرف" in mep_choice:
            ax_m.plot([side_sb + 1.2, side_sb + 1.2], [rear_sb, rear_sb + buildable_l], color='brown', linewidth=2.5, linestyle='--', label='خط الصرف الرئيسي 4 بوصة')
            ax_m.plot(side_sb + 1.2, rear_sb, marker='D', markersize=10, color='brown', label='غرفة تفتيش (Inspection Chamber)')
            ax_m.plot(side_sb + 1.5, rear_sb + buildable_l*0.2, marker='^', markersize=10, color='orange', label='مصيدة شحوم (Grease Trap)')
        elif "الكهربائي" in mep_choice:
            ax_m.plot(side_sb + 0.5, rear_sb + buildable_l*0.5, marker='s', markersize=12, color='blue', label='لوحة التوزيع الرئيسية (MDB)')
            for r in rooms:
                ax_m.plot(r["x"] + r["w"]*0.35, r["y"] + r["h"]*0.5, marker='*', markersize=9, color='gold')
                ax_m.plot(r["x"] + r["w"]*0.65, r["y"] + r["h"]*0.5, marker='*', markersize=9, color='gold', label='إنارة LED' if r == rooms[0] else "")
        else:
            for r in rooms:
                ax_m.add_patch(Rectangle((r["x"] + r["w"]*0.2, r["y"] + r["h"]*0.4), r["w"]*0.6, r["h"]*0.2, facecolor='#38BDF8', edgecolor='blue', alpha=0.6, label='مجاري دكت التكييف' if r == rooms[0] else ""))
                ax_m.plot(r["x"] + r["w"]*0.5, r["y"] + r["h"]*0.5, marker='o', markersize=6, color='darkblue', label='مخرج هواء (Diffuser)' if r == rooms[0] else "")

        ax_m.set_xlim(side_sb - 2, side_sb + net_w + 2)
        ax_m.set_ylim(rear_sb - 2, rear_sb + buildable_l + 4)
        ax_m.set_aspect('equal')
        ax_m.legend(loc='upper right', fontsize=8)
        ax_m.grid(True, linestyle=':', alpha=0.4)
        st.pyplot(fig_m)

    # ----------------- TAB 4: النظام الإنشائي -----------------
    with tab_str:
        st.subheader("النظام الإنشائي ومواصفات التأسيس")
        found_rec = "أساس حصيري مسلح (Raft Foundation)" if actual_sbc < 140 or num_units >= 3 else "قواعد منفصلة مسلحة متصلة بميدات ربط جاسئة (Isolated Footings + Tie Beams)"
        st.info(f"**نظام الأساسات الموصى به:** {found_rec} (بناءً على جهد تربة {actual_sbc} kN/m²)")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            st.markdown("**مواصفات الخرسانة والمواد (Substructure):**")
            st.write("- خرسانة الأساسات والميدات: خرسانة مقاومة للكبريتات SRC عيار C40.")
            st.write("- عزل مائي مزدوج: لفائف بيتومينية مسلحة بالبوليستر 4 مم مع ألواح حماية.")
            st.write("- حديد التسليح: إجهاد خضوع 500 MPa عالي المقاومة.")
        with c_s2:
            st.markdown("**مواصفات الهيكل العلوي (Superstructure):**")
            st.write("- خرسانة بورتلاندية عادية OPC رتبة C35 إلى C40 للأعمدة والأسقف.")
            st.write("- أسقف لاكمرية (Flat Slab 22-24 سم) لمرونة التعديل الداخلي ومجاري التكييف المخفي.")

    # ----------------- TAB 5: كراسة الكميات والبرنامج الزمني -----------------
    with tab_boq:
        st.subheader(f"كراسة حصر الكميات والمواد التقديرية (BOQ) - مسطح البناء {calc_total_bua:.1f} م²")
        vol_concrete_sub = round(calc_total_bua * 0.25, 1)
        vol_concrete_super = round(calc_total_bua * 0.40, 1)
        total_concrete_vol = round(vol_concrete_sub + vol_concrete_super, 1)
        steel_tonnage = round((total_concrete_vol * 115) / 1000, 1)

        boq_df = pd.DataFrame([
            {"البند": "1. حفر وتسوية الموقع العام", "الوحدة": "م³", "الكمية": round(effective_ground * 1.8, 1), "السعر التقديري (AED)": 25, "الإجمالي (AED)": round(effective_ground * 1.8 * 25)},
            {"البند": "2. خرسانة مسلحة كبريتية للقواعد والميدات (SRC)", "الوحدة": "م³", "الكمية": vol_concrete_sub, "السعر التقديري (AED)": 340, "الإجمالي (AED)": round(vol_concrete_sub * 340)},
            {"البند": "3. خرسانة مسلحة للأعمدة والأسقف (OPC)", "الوحدة": "م³", "الكمية": vol_concrete_super, "السعر التقديري (AED)": 330, "الإجمالي (AED)": round(vol_concrete_super * 330)},
            {"البند": "4. حديد تسليح عالي المقاومة Grade 500", "الوحدة": "طن", "الكمية": steel_tonnage, "السعر التقديري (AED)": 2750, "الإجمالي (AED)": round(steel_tonnage * 2750)},
            {"البند": "5. عوازل الأساسات والأسطح", "الوحدة": "م²", "الكمية": round(effective_ground * 2.2, 1), "السعر التقديري (AED)": 45, "الإجمالي (AED)": round(effective_ground * 2.2 * 45)},
            {"البند": "6. أعمال الطابوق الداخلي والخارجي المعزول", "الوحدة": "حبة", "الكمية": round(calc_total_bua * 4.2), "السعر التقديري (AED)": 3.5, "الإجمالي (AED)": round(calc_total_bua * 4.2 * 3.5)}
        ])
        st.table(boq_df)
        st.metric("التكلفة التقديرية المبدئية للعظم والهيكل الإنشائي", f"{boq_df['الإجمالي (AED)'].sum():,.0f} درهم إماراتي")

        st.markdown("---")
        st.subheader("البرنامج الزمني للتنفيذ والاعتمادات البلدية")
        st.info("المدة الكلية المتوقعة للمشروع: **14 إلى 16 شهراً** من تسليم الموقع حتى شهادة الإنجاز.")
