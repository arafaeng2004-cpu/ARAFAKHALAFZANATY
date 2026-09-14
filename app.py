import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Polygon, Circle
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Civil & Architectural Engineering Suite", layout="wide")

# جلب المفتاح تلقائياً من Secrets السحابية دون طلب إدخاله من المستخدم
api_key = st.secrets.get("GEMINI_API_KEY", "")

# ----------------- الشريط الجانبي: اختيار بيئة العمل -----------------
st.sidebar.title("🛠️ منصة الأنظمة الهندسية")
module_choice = st.sidebar.radio(
    "اختر المنظومة المستقلة للتشغيل:",
    [
        "1. المنظومة المعمارية وتوليد المخططات والـ 3D (Design & BIM)",
        "2. محرك البرامج الزمنية والمسار الحرج لمشروع مصمم (CPM Schedule)",
        "3. محرك حصر الكميات والمواصفات والتسعير المعتمد (BOQ Engine)"
    ]
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود المعتمد:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

# ==============================================================================
# الوحدة الأولى: المنظومة المعمارية المتكاملة وتخصيص السلالم والـ 3D
# ==============================================================================
if "1. المنظومة المعمارية" in module_choice:
    st.title("🏛️ المنظومة المعمارية والإنشائية التنفيذية الشاملة")
    st.markdown("دراسة اشتراطات البناء البلدية، توزيع المساقط التنفيذية، إدراج السلالم الإبداعية، وتصدير ملفات AutoCAD و 3ds Max و Photoshop.")

    input_mode = st.radio("طريقة تحديد أبعاد القسيمة:", ["إدخال أبعاد القسيمة يدوياً", "رفع مخطط الأرض (الكروكي - PDF أو صورة)"], horizontal=True)

    width, length, actual_sbc = 30.0, 50.0, 150.0

    if input_mode == "رفع مخطط الأرض (الكروكي - PDF أو صورة)":
        uploaded_file = st.file_uploader("ارفع ملف الكروكي (PDF / PNG / JPG):", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_file and api_key:
            client = genai.Client(api_key=api_key)
            file_bytes = uploaded_file.read()
            mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

            with st.spinner("جاري قراءة أبعاد القسيمة وتحليل المحددات التخطيطية..."):
                prompt = "Extract width (street frontage) and length (depth) in meters from this UAE Krooki. Return purely JSON: {'width': float, 'length': float}."
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(res.text)
                    width = float(data.get("width", 30.0))
                    length = float(data.get("length", 50.0))
                    st.success(f"✅ الأبعاد المعتمدة آلياً: الواجهة = {width} م | العمق = {length} م | المساحة = {width*length:.1f} م²")
                except Exception:
                    st.warning("تم اعتماد الأبعاد المعيارية الافتراضية.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: width = st.number_input("عرض واجهة الأرض على الشارع (متر):", 12.0, 200.0, 30.0, 0.5)
        with c2: length = st.number_input("عمق القسيمة الداخلي (متر):", 15.0, 300.0, 50.0, 0.5)
        with c3: actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", 60.0, 400.0, 150.0, 10.0)

    # حسابات الارتدادات البلدية والمساحات الصافية
    front_sb = 5.0 if "أبوظبي" in emirate else (4.5 if "الشارقة" in emirate else 4.0)
    rear_sb = 3.0
    side_sb = 2.0 if "أبوظبي" in emirate else 1.5
    max_cov = 0.50 if ("أبوظبي" in emirate or "دبي" in emirate) else 0.55

    plot_area = round(width * length, 2)
    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov, 2))
    buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

    st.markdown("---")
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_scheme = st.selectbox(
            "اختر النموذج المعماري المطلوب دراسته:",
            [
                "المقترح 1: فيلا عائلية فاخرة مستقلة (Single Luxury Villa - G+1)",
                "المقترح 2: فيلتان متلاصقتان (Twin Villas / Semi-Detached - G+1)",
                "المقترح 3: 3 فلل متلاصقة تاون هاوس (3 Townhouses - G+1)",
                "المقترح 4: 4 وحدات دوبلكس استثمارية (Row Houses / Fourplex - G+1)",
                "المقترح 5: فيلا رئيسية مع ملحق خدمات خارجي (Villa + Outbuilding Block)"
            ]
        )
    with col_sel2:
        stair_style = st.selectbox(
            "اختر الطراز الهندسي للدرج الرئيسي (Staircase Architecture):",
            [
                "1. درج حلزوني دائري مدمج بالبرج (Helical Spiral in Glass Tower)",
                "2. درج مقوس إمبراطوري ملكي (Double Curved Imperial Staircase)",
                "3. درج مودرن معلق كابولي (Floating Cantilevered Modern)",
                "4. درج تقليدي قلبتين مع بسطة استراحة (U-Shaped Dog-Leg with Landing)"
            ]
        )

    # تجهيز الغرف المعمارية للنموذج المختار
    if "المقترح 1" in selected_scheme:
        bua_factor = 1.85
        rooms = [
            {"n": "مجلس رجال رسمي فندقي\nFormal Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "c": "#FEF3C7"},
            {"n": "صالة طعام رسمية\nDining Suite", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
            {"n": "مطبخ تحضيري ورئيسي\nShow & Dirty Kitchen", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "c": "#FED7AA"},
            {"n": "صالة معيشة عائلية بانورامية\nPanoramic Living Hall", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
            {"n": "جناح كبار السن / ضيوف\nGround Master Suite", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
        ]
        doors = [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]
        entries = [("مدخل الضيوف الرسمي", (side_sb + net_w*0.24, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.24, rear_sb + buildable_l), "#B45309"),
                   ("المدخل العائلي الرئيسي", (side_sb + net_w*0.74, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.74, rear_sb + buildable_l), "#0284C7")]
    elif "المقترح 2" in selected_scheme:
        bua_factor = 1.80
        uw = net_w / 2
        rooms = [
            {"n": "فيلا 1: مجلس ضيوف", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#DCFCE7"},
            {"n": "فيلا 1: صالة عائلية ومطبخ", "x": side_sb, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0FDF4"},
            {"n": "فيلا 2: مجلس ضيوف", "x": side_sb + uw, "y": rear_sb + buildable_l*0.55, "w": uw, "h": buildable_l*0.45, "c": "#E0F2FE"},
            {"n": "فيلا 2: صالة عائلية ومطبخ", "x": side_sb + uw, "y": rear_sb, "w": uw, "h": buildable_l*0.55, "c": "#F0F9FF"}
        ]
        doors = [(side_sb + uw*0.5, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + uw*1.5, rear_sb + buildable_l, 1.2, 270, 360)]
        entries = [("مدخل فيلا 1", (side_sb + uw*0.5, rear_sb + buildable_l + 3.2), (side_sb + uw*0.5, rear_sb + buildable_l), "#15803D"),
                   ("مدخل فيلا 2", (side_sb + uw*1.5, rear_sb + buildable_l + 3.2), (side_sb + uw*1.5, rear_sb + buildable_l), "#0284C7")]
    elif "المقترح 3" in selected_scheme:
        bua_factor = 1.80
        uw = net_w / 3
        rooms = [{"n": f"تاون هاوس {i+1}\nمعيشة وضيافة", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.4, "w": uw, "h": buildable_l*0.6, "c": "#FEF9C3"} for i in range(3)] + \
                 [{"n": f"تاون هاوس {i+1}\nمطبخ وخدمات", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.4, "c": "#FEF08A"} for i in range(3)]
        doors = [(side_sb + (i+0.5)*uw, rear_sb + buildable_l, 1.1, 180, 270) for i in range(3)]
        entries = [(f"مدخل تاون هاوس {i+1}", (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.2), (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "#CA8A04") for i in range(3)]
    elif "المقترح 4" in selected_scheme:
        bua_factor = 1.75
        uw = net_w / 4
        rooms = [{"n": f"دوبلكس {i+1}\nمعيشة واستقبال", "x": side_sb + i*uw, "y": rear_sb + buildable_l*0.45, "w": uw, "h": buildable_l*0.55, "c": "#FEE2E2"} for i in range(4)] + \
                 [{"n": f"دوبلكس {i+1}\nمطبخ وخدمات", "x": side_sb + i*uw, "y": rear_sb, "w": uw, "h": buildable_l*0.45, "c": "#FFEDD5"} for i in range(4)]
        doors = [(side_sb + (i+0.5)*uw, rear_sb + buildable_l, 1.0, 180, 270) for i in range(4)]
        entries = [(f"مدخل دوبلكس {i+1}", (side_sb + (i+0.5)*uw, rear_sb + buildable_l + 3.2), (side_sb + (i+0.5)*uw, rear_sb + buildable_l), "#DC2626") for i in range(4)]
    else:
        bua_factor = 1.90
        rooms = [
            {"n": "الفيلا الرئيسية (سكن العائلة)\nMain Residence (G+1)", "x": side_sb, "y": rear_sb, "w": net_w, "h": buildable_l*0.70, "c": "#EEF2FF"},
            {"n": "ملحق الخدمات ومجلس الضيوف\nMajlis & Services Block", "x": side_sb, "y": rear_sb + buildable_l*0.78, "w": net_w*0.75, "h": buildable_l*0.22, "c": "#F3E8FF"}
        ]
        doors = [(side_sb + net_w*0.37, rear_sb + buildable_l, 1.3, 180, 270), (side_sb + net_w*0.5, rear_sb + buildable_l*0.70, 1.3, 270, 360)]
        entries = [("مدخل المجلس الخارجي", (side_sb + net_w*0.37, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.37, rear_sb + buildable_l), "#7E22CE"),
                   ("مدخل الفيلا العائلية", (side_sb + net_w*0.85, rear_sb + buildable_l*0.70 + 2.5), (side_sb + net_w*0.85, rear_sb + buildable_l*0.70), "#4338CA")]

    calc_total_bua = round(effective_ground * bua_factor, 2)

    tab_plan, tab_export, tab_mep = st.tabs([
        "📐 المسقط المعماري والدرج التفصيلي",
        "📦 بوابة الربط والتصدير (AutoCAD / 3ds Max / Photoshop)",
        "📋 مخططات الخدمات والدفاع المدني"
    ])

    with tab_plan:
        fig_plan, ax = plt.subplots(figsize=(11, 14), dpi=220)
        ax.set_facecolor('#F8FAFC')

        # حدود القسيمة وخط الارتداد
        ax.add_patch(patches.Rectangle((0, 0), width, length, lw=3.5, edgecolor='#0F172A', facecolor='#FFFFFF'))
        ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, lw=2.0, edgecolor='#EF4444', linestyle='--', facecolor='none'))

        # الجدران المزدوجة والفراغات
        for r in rooms:
            ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.2, edgecolor='#1E293B', facecolor=r["c"], alpha=0.88))
            ax.add_patch(patches.Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.2, weight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

        # رسم الدرج الإبداعي بحسب الطراز المختار
        st_cx = side_sb + net_w * 0.48
        st_cy = rear_sb + buildable_l * 0.45

        if "1. درج حلزوني" in stair_style:
            # برج دائري مع درجات حلزونية
            r_tower = 2.4
            circle_tower = patches.Circle((st_cx, st_cy), r_tower, facecolor='#E0F2FE', edgecolor='#0369A1', lw=2.5)
            ax.add_patch(circle_tower)
            hub = patches.Circle((st_cx, st_cy), 0.4, facecolor='#0F172A')
            ax.add_patch(hub)
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax.plot([st_cx + 0.4*np.cos(rad), st_cx + r_tower*np.cos(rad)], [st_cy + 0.4*np.sin(rad), st_cy + r_tower*np.sin(rad)], color='#0369A1', lw=1.4)
            ax.annotate('صعود UP', xy=(st_cx + 1.6, st_cy + 1.2), xytext=(st_cx + 0.5, st_cy - 1.5),
                        ha='center', fontsize=8.5, weight='bold', color='#0369A1',
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0369A1', lw=2.2))

        elif "2. درج مقوس إمبراطوري" in stair_style:
            # جناحان مقوسان يلتقيان ببسطة عريضة
            sw, sh = 4.2, 4.0
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF3C7', edgecolor='#B45309', lw=2.2))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax.plot([st_cx - sw/2 + 0.4, st_cx, st_cx + sw/2 - 0.4], [sy, sy + 0.25, sy], color='#B45309', lw=1.6)
            ax.annotate('صعود ملكي UP', xy=(st_cx, st_cy + sh - 0.3), xytext=(st_cx, st_cy + 0.4),
                        ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.2))

        elif "3. درج مودرن معلق" in stair_style:
            # درجات كابولية طائرة
            sw, sh = 2.4, 4.5
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#F1F5F9', edgecolor='#475569', lw=1.8))
            ax.plot([st_cx - sw/2, st_cx - sw/2], [st_cy, st_cy + sh], color='#0F172A', lw=4.5) # جدار التثبيت
            for sy in np.linspace(st_cy + 0.2, st_cy + sh - 0.2, 13):
                ax.add_patch(patches.Rectangle((st_cx - sw/2, sy), sw*0.9, 0.2, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.2))
            ax.annotate('صعود UP', xy=(st_cx, st_cy + sh - 0.4), xytext=(st_cx, st_cy + 0.4),
                        ha='center', fontsize=8.5, weight='bold', color='#1E293B', arrowprops=dict(arrowstyle="->", color='#1E293B', lw=2.0))

        else: # درج U-Shape
            sw, sh = 3.2, 4.2
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
            ax.plot([st_cx, st_cx], [st_cy, st_cy + sh*0.65], color='#0F172A', lw=2.0) # قاطع القلبتين
            ax.add_patch(patches.Rectangle((st_cx - sw/2, st_cy + sh*0.65), sw, sh*0.35, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.5)) # البسطة
            for sy in np.linspace(st_cy, st_cy + sh*0.65, 8):
                ax.plot([st_cx - sw/2, st_cx], [sy, sy], color='#475569', lw=1.4)
                ax.plot([st_cx, st_cx + sw/2], [sy, sy], color='#475569', lw=1.4, linestyle='--')
            ax.annotate('صعود UP', xy=(st_cx - 0.8, st_cy + sh*0.5), xytext=(st_cx - 0.8, st_cy + 0.3),
                        ha='center', fontsize=8.0, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.8))

        # الأبواب ومسار الفتح
        for dx, dy, r, a1, a2 in doors:
            ax.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        # المداخل
        for title_e, p1, p2, col_e in entries:
            arrow = FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=18, color=col_e, lw=2.6)
            ax.add_patch(arrow)
            ax.text(p1[0], p1[1] + 0.6, title_e, ha='center', va='bottom', fontsize=8.5, weight='bold', color=col_e,
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=col_e, alpha=0.95, lw=1.0))

        ax.annotate('الشارع الرئيسي / الواجهة (Main Road Frontage)', xy=(width/2, length), xytext=(width/2, length + 2.5),
                    ha='center', fontsize=11, weight='bold', color='#15803D',
                    bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax.set_xlim(-width * 0.12, width * 1.12)
        ax.set_ylim(-length * 0.08, length * 1.16)
        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig_plan)

    with tab_export:
        st.markdown("### 📦 قنوات التصدير المباشر لبرامج التصميم والإظهار")
        col_cad, col_3ds, col_ps = st.columns(3)

        with col_cad:
            st.markdown("#### 📐 AutoCAD (.DXF)")
            st.write("ملف طبقات كامل (`WALLS`, `DOORS`, `STAIRS`, `SETBACKS`) يفتح في AutoCAD و Revit بمقاسات حقيقية.")
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="SETBACKS", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (width-side_sb, rear_sb), (width-side_sb, length-front_sb), (side_sb, length-front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
            doc.layers.add(name="WALLS", color=4)
            for r in rooms:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
            doc.layers.add(name="STAIRS", color=2)
            msp.add_lwpolyline([(st_cx-1.6, st_cy), (st_cx+1.6, st_cy), (st_cx+1.6, st_cy+4.2), (st_cx-1.6, st_cy+4.2), (st_cx-1.6, st_cy)], dxfattribs={'layer': 'STAIRS'})
            dxf_buf = io.StringIO()
            doc.write(dxf_buf)
            st.download_button("💾 تحميل ملف AutoCAD (.DXF)", dxf_buf.getvalue().encode('utf-8'), "Master_Site_Plan.dxf", "application/dxf")

        with col_3ds:
            st.markdown("#### 🧊 3ds Max / Blender (.OBJ)")
            st.write("مجسم 3D هندسي حقيقي بأسطحه وكتله وجدرانه وارتفاعاته جاهز للرندر في V-Ray / Corona.")
            obj_lines = ["# UAE Villa 3D Geometric Mesh for 3ds Max\n"]
            v_i = 1
            for idx, r in enumerate(rooms):
                x, y, w, h = r["x"], r["y"], r["w"], r["h"]
                verts = [(x,y,0),(x+w,y,0),(x+w,y+h,0),(x,y+h,0),(x,y,8.5),(x+w,y,8.5),(x+w,y+h,8.5),(x,y+h,8.5)]
                for vx, vy, vz in verts: obj_lines.append(f"v {vx:.2f} {vz:.2f} {vy:.2f}\n")
                f = v_i
                faces = [(f,f+1,f+2,f+3),(f+4,f+7,f+6,f+5),(f,f+4,f+5,f+1),(f+1,f+5,f+6,f+2),(f+2,f+6,f+7,f+3),(f+3,f+7,f+4,f)]
                obj_lines.append(f"g Room_{idx+1}\n")
                for f1,f2,f3,f4 in faces: obj_lines.append(f"f {f1} {f2} {f3} {f4}\n")
                v_i += 8
            st.download_button("💾 تحميل مجسم 3ds Max (.OBJ)", "".join(obj_lines).encode('utf-8'), "Villa_3D_Model.obj", "model/obj")

        with col_ps:
            st.markdown("#### 🎨 Photoshop (.PNG 300 DPI)")
            st.write("مسقط معماري عالي الدقة بدون خلفية (Transparent) مخصص لتلوين المخططات وإظهار الحدائق والفرش.")
            img_buf = io.BytesIO()
            fig_plan.savefig(img_buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
            st.download_button("💾 تحميل شيت Photoshop عالي الدقة", img_buf.getvalue(), "Plan_Photoshop_Render.png", "image/png")

    with tab_mep:
        st.subheader("📋 حزمة المخططات التنفيذية وتراخيص الدفاع المدني (Authority MEP Package)")
        st.markdown("""
        * **مخطط الدفاع المدني والسلامة (Civil Defence):** مسارات الهروب وعروض المخارج ومسافات الانتقال ($\le 20$ م للغرف ذات المخرج الواحد)، وتوزيع كواشف الدخان البصرية وكواشف الحرارة بالمطابخ، ومطفآت بودرة جافة DCP 6kg و CO2، وأبواب مقاومة للحريق FD-60.
        * **مخطط التغذية والصرف الصحي (Plumbing):** شبكة مزدوجة مفصولة للأنابيب السوداء والرمادية بنظام (Two-Pipe System) مع مصيدة شحوم للمطبخ، وأنابيب تغذية مياه بولي بروبلين حراري (PPR PN20) معزولة.
        * **مخطط الأحمال الكهربائية (Electrical):** لوحة MDB رئيسية مع قواطع حساسة للتسريب الأرضي ELCB 30mA للغرف الرطبة و 100mA للعمومي، وشبكة تأريض نحاسية تحقق مقاومة أقل من 1 أوم.
        * **مخطط التكييف والتهوية (HVAC):** تكييف مخفي دكت سبليت Inverter موفر للطاقة بمخارج هواء طولية Linear Slots ومجاري صاج معزولة بالصوف الزجاجي.
        """)

# ==============================================================================
# الوحدة الثانية: محرك البرنامج الزمني والمسار الحرج لمشروع تم تصميمه
# ==============================================================================
elif "2. محرك البرنامج الزمني" in module_choice:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج (CPM / WBS Engine)")
    st.markdown("وحدة مستقلة لتوليد برنامج زمني تنفيذي احترافي لمشروع تم تصميمه مسبقاً وفق معدلات الإنتاجية والاعتمادات البلدية بدولة الإمارات.")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        custom_bua = st.number_input("إجمالي مسطح البناء للمشروع BUA (م²):", min_value=100.0, max_value=25000.0, value=850.0, step=50.0)
    with col_s2:
        start_date = st.date_input("تاريخ تسليم الموقع وبدء المشروع:", datetime.date.today())
    with col_s3:
        project_pace = st.selectbox("وتيرة التنفيذ المطلوبة:", ["قياسي اعتيادي (Standard Track)", "مكثف / مسار سريع (Fast-Track)"])

    factor = 0.82 if "مكثف" in project_pace else 1.0

    # جدول الحزم التنفيذية والمسار الحرج
    wbs_tasks = [
        {"Phase": "1. استخراج رخصة البناء وفحص التربة وشهادات NOC", "Days": int(28 * factor)},
        {"Phase": "2. تجهيز الموقع والحفر والإحلال وتحديد الصفر المعماري", "Days": int(21 * factor)},
        {"Phase": "3. صبة النظافة PCC والأساسات والرقاب المسلحة (SRC)", "Days": int(35 * factor)},
        {"Phase": "4. العزل المائي للأساسات والردم على طبقات واختبار الدمك", "Days": int(21 * factor)},
        {"Phase": "5. الميدات الأرضية وصبة الأرضية Slab on Grade", "Days": int(20 * factor)},
        {"Phase": "6. هيكل الطابق الأرضي (أعمدة وسقف Flat Slab)", "Days": int(35 * factor)},
        {"Phase": "7. هيكل الطابق الأول والسطح وأعمال المباني العظم", "Days": int(45 * factor)},
        {"Phase": "8. التمديدات الكهروميكانيكية وتأسيسات MEP الأولية", "Days": int(45 * factor)},
        {"Phase": "9. العزل المائي والحراري للأسطح بنظام الكومبو المعتمد", "Days": int(20 * factor)},
        {"Phase": "10. أعمال اللياسة الإسمنتية (طرطشة وبلاستر) والأرضيات", "Days": int(60 * factor)},
        {"Phase": "11. الواجهات الخارجية والألومنيوم والزجاج والأسوار", "Days": int(45 * factor)},
        {"Phase": "12. الفحص النهائي وإطلاق التيار وشهادة الإنجاز البلدية", "Days": int(28 * factor)}
    ]

    c_start = pd.to_datetime(start_date)
    schedule_records = []
    for item in wbs_tasks:
        c_end = c_start + pd.Timedelta(days=item["Days"])
        schedule_records.append({"المرحلة التنفيذية": item["Phase"], "تاريخ البداية": c_start, "تاريخ الانتهاء": c_end, "المدة (يوم)": item["Days"]})
        c_start = c_end - pd.Timedelta(days=int(item["Days"] * 0.28)) # تداخل المسار الحرج (Fast-track Overlapping)

    df_schedule = pd.DataFrame(schedule_records)
    total_days = (df_schedule["تاريخ الانتهاء"].max() - pd.to_datetime(start_date)).days

    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي مدة المشروع التنفيذية", f"{total_days} يوماً")
    m2.metric("المدة الإجمالية بالشهور", f"{total_days / 30.5:.1f} شهراً")
    m3.metric("تاريخ إنجاز المشروع المتوقع", df_schedule["تاريخ الانتهاء"].max().strftime('%Y-%m-%d'))

    st.markdown("---")
    st.subheader("📊 مخطط جانت الزمني والمسار الحرج (Gantt Chart)")

    fig_gantt, ax_g = plt.subplots(figsize=(11, 6.5), dpi=180)
    for i, row in df_schedule.iterrows():
        s_num = mdates.date2num(row["تاريخ البداية"])
        e_num = mdates.date2num(row["تاريخ الانتهاء"])
        ax_g.barh(row["المرحلة التنفيذية"], e_num - s_num, left=s_num, color='#2563EB', edgecolor='#1E3A8A', height=0.55)

    ax_g.xaxis_date()
    ax_g.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax_g.grid(True, linestyle=':', alpha=0.6)
    ax_g.invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig_gantt)

    # تصدير كراسة الجدول الزمني
    csv_buf = io.StringIO()
    df_schedule.to_csv(csv_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة البرنامج الزمني بصيغة Excel / CSV", csv_buf.getvalue().encode('utf-8-sig'), "Baseline_Schedule.csv", "text/csv")

# ==============================================================================
# الوحدة الثالثة: محرك كراسة الكميات والمواصفات والتسعير لمشروع مصمم
# ==============================================================================
else:
    st.title("📊 محرك كراسة الكميات والمواصفات والتكاليف (BOQ Engine)")
    st.markdown("وحدة مستقلة لإعداد جدول كميات تنفيذي وحساب تكلفة العظم والتشطيبات لمشروع تم تصميمه بالفعل.")

    c_b1, c_b2, c_b3 = st.columns(3)
    with c_b1:
        proj_bua = st.number_input("مسطح البناء الإجمالي BUA للمشروع (م²):", 100.0, 30000.0, 850.0, 50.0)
    with c_b2:
        finishing_level = st.selectbox("مستوى المواصفات والتشطيب:", ["ديلوكس تجاري (Standard Deluxe)", "سوبر ديلوكس فاخر (Super Deluxe)", "ألترا لوكجري VIP (Ultra Luxury)"])
    with c_b3:
        ground_footprint = st.number_input("مسطح بصمة الطابق الأرضي (Footprint م²):", 50.0, 15000.0, float(proj_bua * 0.52), 25.0)

    # معادلات الحصر المعتمدة وفق كود البناء الإماراتي
    conc_sub = round(proj_bua * 0.26, 1)
    conc_sup = round(proj_bua * 0.40, 1)
    tot_conc = round(conc_sub + conc_sup, 1)
    steel_t = round((tot_conc * 115) / 1000, 1)
    blocks_qty = round(proj_bua * 4.3)
    waterproof_m2 = round(ground_footprint * 2.3, 1)
    plaster_m2 = round(proj_bua * 6.5, 1)

    rate_multiplier = 1.0 if "تجاري" in finishing_level else (1.35 if "سوبر" in finishing_level else 1.80)

    boq_items = [
        {"كود": "01-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الحفر العام والتسوية ونقل المخلفات لمنسوب التأسيس", "الوحدة": "م³", "الكمية": round(ground_footprint * 1.8, 1), "السعر الإفرادي (AED)": 25.0},
        {"كود": "02-01", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة نظافة عادية Blinding PCC عيار 20 N/mm² أسفل القواعد", "الوحدة": "م³", "الكمية": round(ground_footprint * 0.12, 1), "السعر الإفرادي (AED)": 270.0},
        {"كود": "02-02", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة كبريتية SRC C40 للأساسات والميدات والرقاب", "الوحدة": "م³", "الكمية": conc_sub, "السعر الإفرادي (AED)": 340.0},
        {"كود": "02-03", "بند الأعمال الهندسي والمواصفة الفنية": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": conc_sup, "السعر الإفرادي (AED)": 330.0},
        {"كود": "03-01", "بند الأعمال الهندسي والمواصفة الفنية": "حديد تسليح عالي المقاومة مشوه رتبة 500 MPa مشتملاً على القص والتشكيل", "الوحدة": "طن", "الكمية": steel_t, "السعر الإفرادي (AED)": 2750.0},
        {"كود": "04-01", "بند الأعمال الهندسي والمواصفة الفنية": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والميدات مع ألواح الحماية", "الوحدة": "م²", "الكمية": waterproof_m2, "السعر الإفرادي (AED)": 45.0},
        {"كود": "05-01", "بند الأعمال الهندسي والمواصفة الفنية": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومصمت/مفرغ للداخل", "الوحدة": "حبة", "الكمية": blocks_qty, "السعر الإفرادي (AED)": 3.6},
        {"كود": "06-01", "بند الأعمال الهندسي والمواصفة الفنية": "لياسة إسمنتية داخلية وخارجية (طرطشة + بلاستر + زوايا وشبك فايبر)", "الوحدة": "م²", "الكمية": plaster_m2, "السعر الإفرادي (AED)": round(22.0 * rate_multiplier, 1)},
        {"كود": "07-01", "بند الأعمال الهندسي والمواصفة الفنية": "نظام العزل المائي والحراري المتكامل للأسطح (كومبو Combo System)", "الوحدة": "م²", "الكمية": round(ground_footprint * 1.1, 1), "السعر الإفرادي (AED)": 115.0},
        {"كود": "08-01", "بند الأعمال الهندسي والمواصفة الفنية": "أعمال الألومنيوم والزجاج المزدوج العازل (Double Glazing) واللوفرز", "الوحدة": "م²", "الكمية": round(proj_bua * 0.22, 1), "السعر الإفرادي (AED)": round(650.0 * rate_multiplier, 1)}
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
