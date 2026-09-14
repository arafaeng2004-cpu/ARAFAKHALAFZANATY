import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Ellipse
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Luxury Architecture & Engineering Suite", layout="wide")

st.title("🏛️ المنظومة المعمارية والهندسية الشاملة - مشاريع الإمارات")
st.markdown("تحليل الكروكي (PDF أو صور)، وتوليد المقترحات المعمارية الـ 5 كاملة بمساقطها ومناظيرها الإبداعية.")

# ----------------- الإعدادات الجانبية -----------------
st.sidebar.header("⚙️ معايير الأرض والتنظيم")
emirate = st.sidebar.selectbox(
    "الإمارة / الجهة التنظيمية:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

api_key = st.sidebar.text_input("Gemini API Key (لقراءة الكروكي):", type="password")

input_mode = st.radio("طريقة تحديد بيانات القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع مخطط الأرض (الكروكي - PDF أو صورة)"])

width, length, actual_sbc = 30.0, 50.0, 150.0

if input_mode == "إدخال أبعاد القسيمة يدوياً":
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (W بالمتر):", min_value=12.0, max_value=200.0, value=30.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة الداخلي (L بالمتر):", min_value=15.0, max_value=300.0, value=50.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=60.0, max_value=400.0, value=150.0, step=10.0)
else:
    # دعم PDF بجانب PNG و JPG
    uploaded_file = st.file_uploader("ارفع ملف الكروكي (PDF / PNG / JPG):", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_file:
        if not api_key:
            st.warning("⚠️ يرجى إدخال مفتاح Gemini API Key في الشريط الجانبي لتفعيل القراءة الآلية للملف.")
        else:
            if st.button("🔍 قراءة واستخراج أبعاد الأرض من الملف المرفوع"):
                client = genai.Client(api_key=api_key)
                file_bytes = uploaded_file.read()
                mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

                with st.spinner("جاري قراءة أبعاد وحدود الأرض هندسياً عبر الذكاء الاصطناعي..."):
                    prompt = (
                        "You are an expert UAE municipal civil engineer. Analyze this site plan (Krooki). "
                        "Extract the plot dimensions strictly in JSON format: "
                        "{'width': <frontage_width_number>, 'length': <depth_length_number>, 'plot_area': <area_number>}. "
                        "Ensure 'width' and 'length' are pure floating point numbers in meters. Return only JSON."
                    )
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                                prompt
                            ],
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        data = json.loads(res.text)
                        st.success("✅ تم قراءة بيانات المخطط بنجاح!")
                        width = float(data.get("width", 30.0))
                        length = float(data.get("length", 50.0))
                        st.info(f"الأبعاد المستخرجة: الواجهة على الشارع = **{width} م** | عمق الأرض = **{length} م** | مساحة الأرض = **{width*length:.1f} م²**")
                    except Exception as err:
                        st.error(f"خطأ أثناء معالجة الملف: {err}. سيتم استخدام الأبعاد القياسية 30×50م.")

# ----------------- زر تشغيل المنظومة بالكامل -----------------
if st.button("🚀 تشغيل المنظومة وتوليد كافة المقترحات الهندسية والمناظير"):
    plot_area = round(width * length, 2)

    # معايير الارتداد البلدية
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

    # بيانات المقترحات الخمسة بالكامل
    schemes_dict = {
        "المقترح 1: فيلا عائلية فاخرة منفردة (Single Luxury Villa - G+1)": {
            "units": 1, "factor": 1.85, "theme": "طراز إماراتي معاصر مع فناء داخلي ومسبح وبرج أسطواني زجاجي",
            "rooms": [
                {"name": "مجلس رجال رسمي\nMajlis", "dim": "6.0 x 8.5 m", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "fc": "#FEF3C7", "ec": "#D97706"},
                {"name": "صالة طعام رسمية\nDining Room", "dim": "4.5 x 6.0 m", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "fc": "#FDE68A", "ec": "#D97706"},
                {"name": "مطبخ تحضيري ورئيسي\nShow & Dirty Kitchen", "dim": "4.5 x 5.0 m", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "fc": "#FED7AA", "ec": "#EA580C"},
                {"name": "صالة معيشة بانورامية كبرى\nLiving Family Area", "dim": "7.0 x 8.5 m", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "fc": "#BAE6FD", "ec": "#0284C7"},
                {"name": "جناح كبار السن / ضيوف\nMaster Suite (G)", "dim": "4.5 x 5.0 m", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "fc": "#E9D5FF", "ec": "#9333EA"}
            ],
            "doors": [
                {"x": side_sb + net_w*0.24, "y": rear_sb + buildable_l, "r": 1.2, "theta1": 180, "theta2": 270},
                {"x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.50, "r": 1.0, "theta1": 90, "theta2": 180},
                {"x": side_sb + net_w*0.74, "y": rear_sb + buildable_l, "r": 1.4, "theta1": 270, "theta2": 360},
                {"x": side_sb, "y": rear_sb + buildable_l*0.15, "r": 1.0, "theta1": 0, "theta2": 90},
                {"x": side_sb + net_w*0.74, "y": rear_sb, "r": 1.2, "theta1": 90, "theta2": 180}
            ],
            "entries": [
                {"txt": "المدخل الرسمي للضيوف\nGuest Entrance", "pos": (side_sb + net_w*0.24, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.24, rear_sb + buildable_l), "c": "#B45309"},
                {"txt": "المدخل العائلي الرئيسي\nFamily Entrance", "pos": (side_sb + net_w*0.74, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.74, rear_sb + buildable_l), "c": "#0369A1"},
                {"txt": "مدخل الخدمة والمطبخ\nService Entry", "pos": (side_sb - 2.8, rear_sb + buildable_l*0.15), "target": (side_sb, rear_sb + buildable_l*0.15), "c": "#C2410C"},
                {"txt": "مخرج الحديقة والمسبح\nGarden / Terrace", "pos": (side_sb + net_w*0.74, rear_sb - 2.8), "target": (side_sb + net_w*0.74, rear_sb), "c": "#15803D"}
            ]
        },
        "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)": {
            "units": 2, "factor": 1.80, "theme": "فيلتان مستقلتان بجدار فاصل مزدوج 20+20سم ومدخلين منفصلين تماماً",
            "rooms": [
                {"name": "فيلا 1: مجلس ضيوف\nVilla 1: Majlis", "dim": f"{(net_w/2)*0.9:.1f} x {buildable_l*0.4:.1f} m", "x": side_sb, "y": rear_sb + buildable_l*0.6, "w": net_w/2, "h": buildable_l*0.4, "fc": "#DCFCE7", "ec": "#16A34A"},
                {"name": "فيلا 1: معيشة ومطبخ\nVilla 1: Living & Kitchen", "dim": f"{(net_w/2)*0.9:.1f} x {buildable_l*0.6:.1f} m", "x": side_sb, "y": rear_sb, "w": net_w/2, "h": buildable_l*0.6, "fc": "#F0FDF4", "ec": "#16A34A"},
                {"name": "فيلا 2: مجلس ضيوف\nVilla 2: Majlis", "dim": f"{(net_w/2)*0.9:.1f} x {buildable_l*0.4:.1f} m", "x": side_sb + net_w/2, "y": rear_sb + buildable_l*0.6, "w": net_w/2, "h": buildable_l*0.4, "fc": "#E0F2FE", "ec": "#0284C7"},
                {"name": "فيلا 2: معيشة ومطبخ\nVilla 2: Living & Kitchen", "dim": f"{(net_w/2)*0.9:.1f} x {buildable_l*0.6:.1f} m", "x": side_sb + net_w/2, "y": rear_sb, "w": net_w/2, "h": buildable_l*0.6, "fc": "#F0F9FF", "ec": "#0284C7"}
            ],
            "doors": [
                {"x": side_sb + (net_w/4), "y": rear_sb + buildable_l, "r": 1.2, "theta1": 180, "theta2": 270},
                {"x": side_sb + (3*net_w/4), "y": rear_sb + buildable_l, "r": 1.2, "theta1": 270, "theta2": 360}
            ],
            "entries": [
                {"txt": "مدخل فيلا 1 المستقل\nVilla 1 Entry", "pos": (side_sb + net_w*0.25, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.25, rear_sb + buildable_l), "c": "#15803D"},
                {"txt": "مدخل فيلا 2 المستقل\nVilla 2 Entry", "pos": (side_sb + net_w*0.75, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.75, rear_sb + buildable_l), "c": "#0369A1"}
            ]
        },
        "المقترح 3: 3 فلل تاون هاوس (3 Townhouses - G+1)": {
            "units": 3, "factor": 1.80, "theme": "3 فلل تاون هاوس متلاصقة مع حدائق خاصة ومواقف مدمجة",
            "rooms": [
                {"name": f"تاون هاوس {i+1}\nمعيشة وضيافة مفتوحة", "dim": f"{(net_w/3):.1f} x {buildable_l*0.6:.1f} m", "x": side_sb + i*(net_w/3), "y": rear_sb + buildable_l*0.4, "w": net_w/3, "h": buildable_l*0.6, "fc": "#FEF9C3", "ec": "#CA8A04"} for i in range(3)
            ] + [
                {"name": f"تاون هاوس {i+1}\nمطبخ وحديقة خاصة", "dim": f"{(net_w/3):.1f} x {buildable_l*0.4:.1f} m", "x": side_sb + i*(net_w/3), "y": rear_sb, "w": net_w/3, "h": buildable_l*0.4, "fc": "#FEF08A", "ec": "#CA8A04"} for i in range(3)
            ],
            "doors": [{"x": side_sb + (i+0.5)*(net_w/3), "y": rear_sb + buildable_l, "r": 1.1, "theta1": 180, "theta2": 270} for i in range(3)],
            "entries": [{"txt": f"مدخل تاون هاوس {i+1}\nTH {i+1} Entry", "pos": (side_sb + (i+0.5)*(net_w/3), rear_sb + buildable_l + 3.2), "target": (side_sb + (i+0.5)*(net_w/3), rear_sb + buildable_l), "c": "#CA8A04"} for i in range(3)]
        },
        "المقترح 4: 4 وحدات متلاصقة استثمارية (Row Houses / Fourplex - G+1)": {
            "units": 4, "factor": 1.75, "theme": "4 وحدات دوبلكس استثمارية لتحقيق أعلى عائد إيجاري مع مداخل مستقلة",
            "rooms": [
                {"name": f"وحدة دوبلكس {i+1}\nمعيشة ومطبخ (G)", "dim": f"{(net_w/4):.1f} x {buildable_l:.1f} m", "x": side_sb + i*(net_w/4), "y": rear_sb, "w": net_w/4, "h": buildable_l, "fc": "#FEE2E2", "ec": "#DC2626"} for i in range(4)
            ],
            "doors": [{"x": side_sb + (i+0.5)*(net_w/4), "y": rear_sb + buildable_l, "r": 1.0, "theta1": 180, "theta2": 270} for i in range(4)],
            "entries": [{"txt": f"مدخل دوبلكس {i+1}\nUnit {i+1}", "pos": (side_sb + (i+0.5)*(net_w/4), rear_sb + buildable_l + 3.2), "target": (side_sb + (i+0.5)*(net_w/4), rear_sb + buildable_l), "c": "#DC2626"} for i in range(4)]
        },
        "المقترح 5: فيلا رئيسية مع ملحق خدمات منفصل (Villa + Outbuilding Block)": {
            "units": 1, "factor": 1.90, "theme": "فيلا سكن عائلية هادئة مفصولة بالكامل عن ملحق الطبخ الثقيل والمجلس الخارجي",
            "rooms": [
                {"name": "الفيلا العائلية الرئيسية\nMain Residence (G+1)", "dim": f"{net_w:.1f} x {buildable_l*0.7:.1f} m", "x": side_sb, "y": rear_sb, "w": net_w, "h": buildable_l*0.70, "fc": "#EEF2FF", "ec": "#4338CA"},
                {"name": "ملحق الخدمات ومجلس الضيوف\nMajlis & Services Block", "dim": f"{net_w*0.75:.1f} x {buildable_l*0.22:.1f} m", "x": side_sb, "y": rear_sb + buildable_l*0.78, "w": net_w*0.75, "h": buildable_l*0.22, "fc": "#F3E8FF", "ec": "#7E22CE"}
            ],
            "doors": [
                {"x": side_sb + net_w*0.37, "y": rear_sb + buildable_l, "r": 1.3, "theta1": 180, "theta2": 270},
                {"x": side_sb + net_w*0.5, "y": rear_sb + buildable_l*0.70, "r": 1.3, "theta1": 270, "theta2": 360}
            ],
            "entries": [
                {"txt": "مدخل مجلس الضيوف الخارجي\nOutbuilding Guest Majlis", "pos": (side_sb + net_w*0.37, rear_sb + buildable_l + 3.2), "target": (side_sb + net_w*0.37, rear_sb + buildable_l), "c": "#7E22CE"},
                {"txt": "المدخل العائلي الخاص\nMain Villa Family Entry", "pos": (side_sb + net_w*0.85, rear_sb + buildable_l*0.70 + 2.5), "target": (side_sb + net_w*0.85, rear_sb + buildable_l*0.70), "c": "#4338CA"}
            ]
        }
    }

    # دوال توليد الرسم
    def draw_floor_plan(s_data, s_title):
        fig, ax = plt.subplots(figsize=(10, 13), dpi=180)
        ax.add_patch(patches.Rectangle((0, 0), width, length, linewidth=3.0, edgecolor='#0F172A', facecolor='#F8FAFC', label='حدود القسيمة (Plot Boundary)'))
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=1.8, edgecolor='#DC2626', linestyle='--', facecolor='none', label='خط الارتداد المسموح (Setbacks)'))

        for r in s_data["rooms"]:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=2.0, edgecolor=r["ec"], facecolor=r["fc"], alpha=0.92))
            box_props = dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor=r["ec"], alpha=0.95, lw=1.2)
            content = f"{r['name']}\n[{r['dim']}]"
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, content, ha='center', va='center', fontsize=9.0, weight='bold', color='#1E293B', bbox=box_props)

        for d in s_data["doors"]:
            ax.add_patch(Arc((d["x"], d["y"]), d["r"]*2, d["r"]*2, angle=0, theta1=d["theta1"], theta2=d["theta2"], color='#0F172A', lw=1.6, ls='--'))
            ax.plot([d["x"], d["x"] + d["r"]], [d["y"], d["y"]], color='#0F172A', lw=2.2)

        for ap in s_data["entries"]:
            arrow = FancyArrowPatch(ap["pos"], ap["target"], arrowstyle='-|>', mutation_scale=18, color=ap["c"], lw=2.4)
            ax.add_patch(arrow)
            ax.text(ap["pos"][0], ap["pos"][1] + 0.6, ap["txt"], ha='center', va='bottom', fontsize=8.5, weight='bold', color=ap["c"],
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=ap["c"], alpha=0.95, lw=1.0))

        ax.annotate('الشارع الرئيسي / الواجهة (Main Road)', xy=(width/2, length), xytext=(width/2, length + 2.6),
                    ha='center', fontsize=11, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-width * 0.12, width * 1.12)
        ax.set_ylim(-length * 0.08, length * 1.16)
        ax.set_aspect('equal')
        ax.set_xlabel("عرض الواجهة على الشارع (متر)", fontsize=10, weight='bold')
        ax.set_ylabel("عمق القسيمة الداخلي (متر)", fontsize=10, weight='bold')
        ax.set_title(f"المسقط المعماري الإبداعي - {s_title}\nمسطح الأرضي: {effective_ground:.1f} م² | البناء الكلي: {effective_ground*s_data['factor']:.1f} م²", fontsize=11, weight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=8.5)
        ax.grid(True, linestyle=':', alpha=0.45)
        return fig

    def draw_3d_facade(s_title):
        fig_elev, ax_e = plt.subplots(figsize=(11, 6.5), dpi=180)
        ax_e.set_facecolor("#E0F2FE")
        ax_e.fill_between([-3, net_w + 5], -1.5, 0, color='#64748B')
        ax_e.fill_between([-3, net_w + 5], -0.2, 0, color='#CBD5E1')

        h_total = 8.5
        b_w = net_w

        # الواجهة والكتل الحجرية
        ax_e.add_patch(Rectangle((0, 0), b_w, h_total, facecolor='#F8FAFC', edgecolor='#94A3B8', lw=2.0))
        for y_g in np.arange(0.5, h_total, 0.6):
            ax_e.plot([0, b_w], [y_g, y_g], color='#E2E8F0', lw=0.9)

        # البرج الأسطواني الزجاجي
        tower_x = b_w * 0.32
        tower_w = b_w * 0.18
        tower_h = h_total + 1.2
        ax_e.add_patch(Rectangle((tower_x, 0), tower_w, tower_h, facecolor='#E2E8F0', edgecolor='#475569', lw=2.2))
        ax_e.add_patch(Rectangle((tower_x + 0.3, 1.0), tower_w - 0.6, tower_h - 1.8, facecolor='#38BDF8', edgecolor='#0F172A', lw=2.0, alpha=0.85))
        for ty in np.arange(1.0, tower_h - 0.8, 1.2):
            ax_e.plot([tower_x + 0.3, tower_x + tower_w - 0.3], [ty, ty], color='#0F172A', lw=1.5)

        # بوابة المدخل
        ent_x = tower_x + tower_w + 0.8
        ent_w = b_w * 0.16
        ax_e.add_patch(Rectangle((ent_x - 0.2, 0), ent_w + 0.4, 4.2, facecolor='#334155', edgecolor='#0F172A', lw=1.8))
        ax_e.add_patch(Rectangle((ent_x, 0.2), ent_w, 3.2, facecolor='#78350F', edgecolor='#451A03', lw=1.5))
        ax_e.plot([ent_x + ent_w/2, ent_x + ent_w/2], [0.2, 3.4], color='#B45309', lw=2.0)

        # النوافذ واللوفرز
        w1_x = b_w * 0.05
        w1_w = b_w * 0.22
        ax_e.add_patch(Rectangle((w1_x, 1.0), w1_w, 6.0, facecolor='#38BDF8', edgecolor='#1E293B', lw=2.8, alpha=0.8))
        for wx in np.linspace(w1_x, w1_x + w1_w, 4):
            ax_e.plot([wx, wx], [1.0, 7.0], color='#1E293B', lw=1.5)

        # نباتات تجميلية باستخدام Ellipse لتفادي الخطأ
        for tx in [-1.2, b_w + 1.2]:
            ax_e.add_patch(Rectangle((tx, 0), 0.3, 1.2, facecolor='#78350F'))
            ax_e.add_patch(Ellipse((tx + 0.15, 2.0), width=1.8, height=2.5, facecolor='#15803D', edgecolor='#166534', lw=1.5))

        ax_e.add_patch(Rectangle((-0.4, h_total), b_w + 0.8, 0.6, facecolor='#1E293B', edgecolor='#0F172A', lw=2.0))
        ax_e.set_xlim(-3, b_w + 4)
        ax_e.set_ylim(-1.5, h_total + 2.5)
        ax_e.set_aspect('equal')
        ax_e.axis('off')
        ax_e.set_title(f"المنظور والواجهة المعمارية المودرن - {s_title}", fontsize=11, weight='bold', pad=12)
        return fig_elev

    # ----------------- عرض المقترحات الخمسة في التبويبات -----------------
    tab_m1, tab_m2, tab_m3, tab_m4, tab_m5, tab_mep_all, tab_boq_all = st.tabs([
        "المقترح 1 (فيلا عائلية)",
        "المقترح 2 (فيلتان Twin)",
        "المقترح 3 (3 تاون هاوس)",
        "المقترح 4 (4 دوبلكس)",
        "المقترح 5 (فيلا + ملحق)",
        "مخططات الدفاع المدني و MEP",
        "حصر الكميات والبرنامج الزمني"
    ])

    all_tabs = [tab_m1, tab_m2, tab_m3, tab_m4, tab_m5]
    schemes_keys = list(schemes_dict.keys())

    for idx, tab_i in enumerate(all_tabs):
        k = schemes_keys[idx]
        s_data = schemes_dict[k]
        with tab_i:
            st.subheader(k)
            st.info(f"**الفلسفة التصميمية:** {s_data['theme']}")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("#### 📐 المسقط المعماري والتقسيم الداخلي")
                fig_p = draw_floor_plan(s_data, k.split(':')[0])
                st.pyplot(fig_p)

                # تصدير DXF
                try:
                    doc = ezdxf.new('R2010')
                    msp = doc.modelspace()
                    doc.layers.add(name="PLOT_BOUNDARY", color=7)
                    msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_BOUNDARY'})
                    doc.layers.add(name="SETBACKS", color=1)
                    msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
                    doc.layers.add(name="ROOMS", color=4)
                    for r in s_data["rooms"]:
                        msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'ROOMS'})
                    buf = io.StringIO()
                    doc.write(buf)
                    st.download_button(f"💾 تحميل ملف AutoCAD (.DXF) - {k.split(':')[0]}", data=buf.getvalue().encode('utf-8'), file_name=f"Scheme_{idx+1}.dxf", mime="application/dxf")
                except Exception as ex:
                    st.error(f"خطأ DXF: {ex}")

            with col_m2:
                st.markdown("#### 🏛️ المنظور والواجهة المعمارية 3D")
                fig_e = draw_3d_facade(k.split(':')[0])
                st.pyplot(fig_e)

    with tab_mep_all:
        st.subheader("📋 حزمة المخططات التنفيذية وتراخيص الدفاع المدني (Authority MEP Package)")
        st.markdown("""
        * **مخطط الدفاع المدني (Civil Defence):** كواشف دخان ضوئية بجميع الغرف والممرات + كواشف حرارة بالمطابخ + مطفآت بودرة جافة DCP 6kg وطفاية CO2 + أبواب مقاومة للحريق FD-60.
        * **مخطط الصرف والتغذية (Plumbing):** شبكة مزدوجة مفصولة للأنابيب السوداء والرمادية + مصيدة شحوم للمطبخ + أنابيب تغذية PPR PN20 معزولة حرارياً.
        * **مخطط الأحمال الكهربائية (Electrical):** لوحة MDB رئيسية + قواطع حساسة للتسريب الأرضي ELCB 30mA للغرف الرطبة و 100mA للعمومي + شبكة تأريض أقل من 1 أوم.
        * **مخطط التكييف (HVAC):** تكييف مخفي دكت سبليت Inverter موفر للطاقة بمخارج هواء طولية Linear Slots ومجاري صاج معزولة بالصوف الزجاجي.
        """)

    with tab_boq_all:
        st.subheader("📊 كراسة حصر الكميات والمواد التقديرية (BOQ) والجدول الزمني")
        bua_avg = round(effective_ground * 1.82, 1)
        sub_c = round(bua_avg * 0.25, 1)
        sup_c = round(bua_avg * 0.40, 1)
        tot_c = round(sub_c + sup_c, 1)
        stl = round((tot_c * 115) / 1000, 1)

        boq_data = pd.DataFrame([
            {"البند": "1. أعمال الحفر العام والتسوية", "الوحدة": "م³", "الكمية": round(effective_ground * 1.8, 1), "السعر (AED)": 25, "الإجمالي (AED)": round(effective_ground * 1.8 * 25)},
            {"البند": "2. خرسانة مسلحة كبريتية للقواعد والميدات (SRC)", "الوحدة": "م³", "الكمية": sub_c, "السعر (AED)": 340, "الإجمالي (AED)": round(sub_c * 340)},
            {"البند": "3. خرسانة مسلحة للأعمدة والأسقف (OPC)", "الوحدة": "م³", "الكمية": sup_c, "السعر (AED)": 330, "الإجمالي (AED)": round(sup_c * 330)},
            {"البند": "4. حديد تسليح عالي المقاومة Grade 500", "الوحدة": "طن", "الكمية": stl, "السعر (AED)": 2750, "الإجمالي (AED)": round(stl * 2750)},
            {"البند": "5. عوازل الأساسات والأسطح", "الوحدة": "م²", "الكمية": round(effective_ground * 2.2, 1), "السعر (AED)": 45, "الإجمالي (AED)": round(effective_ground * 2.2 * 45)},
            {"البند": "6. أعمال الطابوق الداخلي والخارجي", "الوحدة": "حبة", "الكمية": round(bua_avg * 4.2), "السعر (AED)": 3.5, "الإجمالي (AED)": round(bua_avg * 4.2 * 3.5)}
        ])
        st.table(boq_data)
        st.metric("التكلفة التقديرية الإجمالية للعظم", f"{boq_data['الإجمالي (AED)'].sum():,.0f} درهم إماراتي")
        st.info("⏱️ **المدة الزمنية المتوقعة للمشروع:** 14 إلى 16 شهراً حتى شهادة الإنجاز البلدية.")
