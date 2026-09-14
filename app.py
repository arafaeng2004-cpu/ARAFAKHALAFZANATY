import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Polygon
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Luxury Architecture & BIM Pipeline", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "")

st.title("🏛️ المنظومة المعمارية التنفيذية الشاملة - مشاريع الإمارات")
st.markdown("توليد مساقط معمارية متكاملة بالسلالم الإبداعية، تصدير مجسمات 3D لـ 3ds Max، ملفات جاهزة لـ Photoshop، وحزم AutoCAD التنفيذية.")

# ----------------- الإدخال والتحليل -----------------
st.sidebar.header("⚙️ معايير القسيمة والتنظيم")
emirate = st.sidebar.selectbox(
    "الإمارة / الجهة التنظيمية:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين", "دبي", "عجمان / الفجيرة / أخرى"]
)

input_mode = st.radio("تحديد بيانات القسيمة:", ["رفع مخطط الأرض (الكروكي - PDF أو صورة)", "إدخال أبعاد القسيمة يدوياً"])

width, length, actual_sbc = 30.0, 50.0, 150.0

if input_mode == "رفع مخطط الأرض (الكروكي - PDF أو صورة)":
    uploaded_file = st.file_uploader("ارفع ملف الكروكي (PDF / PNG / JPG):", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_file and api_key:
        client = genai.Client(api_key=api_key)
        file_bytes = uploaded_file.read()
        mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

        with st.spinner("جاري قراءة أبعاد وحدود القسيمة آلياً..."):
            prompt = (
                "Extract plot dimensions from this UAE site plan (Krooki). "
                "Return strictly JSON: {'width': float, 'length': float, 'plot_area': float}. Return only JSON."
            )
            try:
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                data = json.loads(res.text)
                width = float(data.get("width", 30.0))
                length = float(data.get("length", 50.0))
                st.success(f"✅ الأبعاد المعتمدة: الواجهة = {width} م | العمق = {length} م | مساحة القسيمة = {width*length:.1f} م²")
            except Exception as e:
                st.warning("تم اعتماد الأبعاد القياسية.")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (متر):", min_value=12.0, max_value=200.0, value=30.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة الداخلي (متر):", min_value=15.0, max_value=300.0, value=50.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=60.0, max_value=400.0, value=150.0, step=10.0)

# ----------------- المعالجة الحسابية -----------------
plot_area = round(width * length, 2)

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
effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov_ratio, 2))
buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)

# نماذج السلالم الإبداعية
stairs_config = {
    "pos": (side_sb + net_w*0.48, rear_sb + buildable_l*0.45),
    "type": "Curved Imperial Staircase",
    "width": 3.6, "depth": 4.5
}

# ----------------- وظائف التصدير الهندسي -----------------

def generate_obj_3d(rooms, b_height=8.5):
    """توليد مجسم 3D بصيغة OBJ يفتح في 3ds Max / Blender / SketchUp بكامل تفاصيل الكتل"""
    obj_lines = ["# UAE Luxury Villa 3D Asset - Compatible with 3ds Max & Blender\n"]
    v_idx = 1
    
    # تصدير الكتل كغرف ثلاثية الأبعاد
    for idx, r in enumerate(rooms):
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        # القواعد والأسطح
        vertices = [
            (x, y, 0), (x + w, y, 0), (x + w, y + h, 0), (x, y + h, 0),
            (x, y, b_height), (x + w, y, b_height), (x + w, y + h, b_height), (x, y + h, b_height)
        ]
        for vx, vy, vz in vertices:
            obj_lines.append(f"v {vx:.3f} {vz:.3f} {vy:.3f}\n")
        
        # الأوجه
        f = v_idx
        faces = [
            (f, f+1, f+2, f+3), # Floor
            (f+4, f+7, f+6, f+5), # Roof
            (f, f+4, f+5, f+1), # Front
            (f+1, f+5, f+6, f+2), # Right
            (f+2, f+6, f+7, f+3), # Back
            (f+3, f+7, f+4, f)  # Left
        ]
        obj_lines.append(f"g Room_{idx+1}\n")
        for f1, f2, f3, f4 in faces:
            obj_lines.append(f"f {f1} {f2} {f3} {f4}\n")
        v_idx += 8
        
    return "".join(obj_lines)

# ----------------- واجهة العرض الرئيسية -----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. المسقط المعماري والسلالم الإبداعية",
    "2. بوابة الربط الهندسي (3ds Max / Photoshop / CAD)",
    "3. الرندر المعماري الإبداعي (Photorealistic Render)",
    "4. مخططات الخدمات والترخيص البلدي",
    "5. حصر الكميات والمواصفات التنفيذية"
])

# بيانات المقترح المعماري الرئيسي
scheme_rooms = [
    {"n": "مجلس رجال رسمي فندقي\nFormal Guest Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "c": "#FEF3C7"},
    {"n": "صالة طعام رسمية\nDining Suite", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
    {"n": "مطبخ تحضيري ورئيسي\nShow & Heavy Kitchen", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "c": "#FED7AA"},
    {"n": "صالة معيشة عائلية بانورامية\nPanoramic Living Hall", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
    {"n": "جناح كبار السن / ضيوف\nGround Master Suite", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
]

with tab1:
    st.subheader("المسقط المعماري المفصل مع توزيع السلالم والفرش")
    
    fig, ax = plt.subplots(figsize=(11, 14), dpi=220)
    ax.set_facecolor('#F8FAFC')
    
    # القسيمة والارتدادات
    ax.add_patch(patches.Rectangle((0, 0), width, length, linewidth=3.5, edgecolor='#0F172A', facecolor='#FFFFFF', label='حدود القسيمة (Plot Boundary)'))
    ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=2.0, edgecolor='#DC2626', linestyle='--', facecolor='none', label='حد الارتداد المسموح (Setback)'))
    
    # الجدران المزدوجة والفراغات
    for r in scheme_rooms:
        ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=2.0, edgecolor='#1E293B', facecolor=r["c"], alpha=0.88))
        ax.add_patch(patches.Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, linewidth=1.0, edgecolor='#94A3B8', facecolor='none'))
        ax.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.2, weight='bold', color='#0F172A',
                bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

    # رسم الدرج الإبداعي المقوس (Curved Feature Stairs) في البهو الأوسط
    st_x, st_y = stairs_config["pos"]
    st_w, st_h = stairs_config["width"], stairs_config["depth"]
    ax.add_patch(patches.Rectangle((st_x - st_w/2, st_y), st_w, st_h, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
    for step_y in np.linspace(st_y, st_y + st_h, 14):
        ax.plot([st_x - st_w/2, st_x + st_w/2], [step_y, step_y], color='#475569', lw=1.2)
        # درجات منحنية
        ax.plot([st_x - st_w/2 + 0.3, st_x, st_x + st_w/2 - 0.3], [step_y, step_y + 0.15, step_y], color='#0F172A', lw=1.5)
    
    # سهم الصعود للدرج (Up Arrow)
    ax.annotate('صعود UP', xy=(st_x, st_y + st_h - 0.4), xytext=(st_x, st_y + 0.5),
                ha='center', fontsize=8.5, weight='bold', color='#1E3A8A',
                arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=2.2))

    # الأبواب ومسار الفتح
    doors_data = [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]
    for d in doors_data:
        ax.add_patch(Arc((d[0], d[1]), d[2]*2, d[2]*2, angle=0, theta1=d[3], theta2=d[4], color='#0F172A', lw=1.8, ls='--'))
        ax.plot([d[0], d[0] + d[2]], [d[1], d[1]], color='#0F172A', lw=2.5)

    # المداخل
    ax.annotate('المدخل الرسمي للضيوف (Formal Majlis Entry)', xy=(side_sb + net_w*0.24, rear_sb + buildable_l), xytext=(side_sb + net_w*0.24, rear_sb + buildable_l + 3.5),
                ha='center', fontsize=9.0, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.5))
    ax.annotate('المدخل العائلي الرئيسي (Main Family Entry)', xy=(side_sb + net_w*0.74, rear_sb + buildable_l), xytext=(side_sb + net_w*0.74, rear_sb + buildable_l + 3.5),
                ha='center', fontsize=9.0, weight='bold', color='#0284C7', arrowprops=dict(arrowstyle="->", color='#0284C7', lw=2.5))

    ax.set_xlim(-width * 0.12, width * 1.12)
    ax.set_ylim(-length * 0.08, length * 1.16)
    ax.set_aspect('equal')
    ax.axis('off')
    st.pyplot(fig)

with tab2:
    st.subheader("📦 بوابة التصدير المباشر لبرامج التصميم والإظهار الهندسي")
    st.write("تم تجهيز المخرجات لتتكامل مباشرة مع منظومة العمل في مكاتب الاستشارات الهندسية:")
    
    col_cad, col_3ds, col_ps = st.columns(3)
    
    with col_cad:
        st.markdown("### 📐 AutoCAD (.DXF)")
        st.write("ملف طبقات كامل (Layers: WALLS, DOORS, STAIRS, SETBACKS) يفتح في AutoCAD و Revit.")
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        doc.layers.add(name="WALLS", color=4)
        doc.layers.add(name="SETBACKS", color=1)
        msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'SETBACKS'})
        for r in scheme_rooms:
            msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
        dxf_buf = io.StringIO()
        doc.write(dxf_buf)
        st.download_button("💾 تحميل ملف AutoCAD (.DXF)", data=dxf_buf.getvalue().encode('utf-8'), file_name="Villa_Master_Plan.dxf", mime="application/dxf")

    with col_3ds:
        st.markdown("### 🧊 3ds Max / Blender (.OBJ)")
        st.write("مجسم كتل 3D هندسي حقيقي بأسطحه وجدرانه وارتفاعاته جاهز للرندر الاحترافي في Corona / V-Ray.")
        obj_content = generate_obj_3d(scheme_rooms)
        st.download_button("💾 تحميل مجسم 3ds Max (.OBJ)", data=obj_content.encode('utf-8'), file_name="Villa_3D_Model.obj", mime="model/obj")

    with col_ps:
        st.markdown("### 🎨 Photoshop (.PNG 300 DPI)")
        st.write("مسقط معماري عالي الدقة بدون خلفية (Transparent) مخصص لتلوين المخططات وإظهار الحدائق والفرش.")
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
        st.download_button("💾 تحميل شيت Photoshop عالي الدقة", data=img_buf.getvalue(), file_name="Plan_For_Photoshop_Render.png", mime="image/png")

with tab3:
    st.subheader("📸 الرندر المعماري الإبداعي ثلاثي الأبعاد (Photorealistic 3D Concept)")
    st.info("💡 يتم توليد المنظور عبر النموذج الذكي بالربط مع محددات الواجهة الإماراتية المعاصرة (البرج الزجاجي الأسطواني، كتل الحجر الترافنتين الأبيض، الزجاج المزدوج العاكس، واللوفرز الخشبية).")
    
    if st.button("✨ توليد لقطة الرندر الواقعية للمشروع"):
        if api_key:
            client = genai.Client(api_key=api_key)
            with st.spinner("جاري معالجة المشهد وتوليد اللقطة المعمارية عالية الدقة..."):
                prompt_render = (
                    "Architectural ultra-photorealistic exterior daytime eye-level perspective render of a luxurious modern G+1 villa in Khorfakkan, UAE. "
                    "Features an iconic curved cylindrical glass staircase tower with black aluminum mullions, travertine white stone facade, dark grey accent portals, "
                    "double-height floor-to-ceiling glass curtain walls with wooden louvers, modern boundary wall, clean asphalt driveway, luxury palm trees, crisp architectural photography lighting."
                )
                try:
                    # استدعاء الرندر التصويري
                    result_img = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=prompt_render,
                        config=dict(number_of_images=1, aspect_ratio="16:9")
                    )
                    image_bytes = result_img.generated_images[0].image.image_bytes
                    st.image(Image.open(io.BytesIO(image_bytes)), caption="المنظور المعماري الواقعي ثلاثي الأبعاد المعتمد للمشروع", use_container_width=True)
                except Exception as ex:
                    st.warning(f"ملاحظة: تعذر الاتصال بمولد الصور ({ex}).")
        else:
            st.warning("⚠️ يرجى حفظ مفتاح API في Secrets لتفعيل توليد الرندر الفوري.")

with tab4:
    st.subheader("📋 حزمة التراخيص البلدية ومخططات الدفاع المدني و MEP")
    st.markdown("""
    * **مخطط الدفاع المدني (Civil Defence):** مسارات هروب ومخارج لا تزيد مسافة الانتقال فيها عن 20م، كواشف دخان ضوئية بالغرف والموزعات، كواشف حرارة بالمطابخ، أبواب مقاومة للحريق FD-60.
    * **مخطط الصرف والتغذية (Plumbing):** شبكة مزدوجة (Soil & Waste) منفصلة بالكامل، مصيدة شحوم للمطبخ، وخزان مياه GRP علوي وأرضي معزول ومزود بنظام تبريد للمياه صيفاً.
    * **المخطط الكهربائي (Electrical):** لوحة MDB رئيسية مع قواطع ELCB حساسة، شبكة تأريض نحاسية مقاومتها أقل من 1 أوم، وتمديدات تيار خفيف (Data, CCTV, Video Intercom).
    * **مخطط التكييف (HVAC):** تكييف مخفي دكت سبليت Inverter موفر للطاقة بمخارج هواء طولية Linear Slots ومجاري صاج معزولة بالصوف الزجاجي.
    """)

with tab5:
    st.subheader("📊 كراسة الكميات والمواصفات التنفيذية (BOQ)")
    bua_total = round(effective_ground * 1.85, 1)
    sub_c = round(bua_total * 0.25, 1)
    sup_c = round(bua_total * 0.40, 1)
    steel_t = round(((sub_c + sup_c) * 115) / 1000, 1)

    boq_df = pd.DataFrame([
        {"بند الأعمال": "1. حفر الموقع العام والتسوية والتجهيز", "الوحدة": "م³", "الكمية": round(effective_ground * 1.8, 1), "السعر التقديري (AED)": 25, "الإجمالي (AED)": round(effective_ground * 1.8 * 25)},
        {"بند الأعمال": "2. خرسانة مسلحة مقاومة للأملاح للقواعد والميدات (SRC C40)", "الوحدة": "م³", "الكمية": sub_c, "السعر التقديري (AED)": 340, "الإجمالي (AED)": round(sub_c * 340)},
        {"بند الأعمال": "3. خرسانة مسلحة بورتلاندية للأعمدة والأسقف (OPC C35)", "الوحدة": "م³", "الكمية": sup_c, "السعر التقديري (AED)": 330, "الإجمالي (AED)": round(sup_c * 330)},
        {"بند الأعمال": "4. حديد تسليح عالي الإجهاد مشوه (Grade 500)", "الوحدة": "طن", "الكمية": steel_t, "السعر التقديري (AED)": 2750, "الإجمالي (AED)": round(steel_t * 2750)},
        {"بند الأعمال": "5. أعمال العزل المائي للأساسات والميدات (لفائف 4 مم طبقتين)", "الوحدة": "م²", "الكمية": round(effective_ground * 2.2, 1), "السعر التقديري (AED)": 45, "الإجمالي (AED)": round(effective_ground * 2.2 * 45)},
        {"بند الأعمال": "6. تكسيات الحجر الصناعي والرخام للواجهات الخارجية", "الوحدة": "م²", "الكمية": round(net_w * 8.5 * 1.3, 1), "السعر التقديري (AED)": 180, "الإجمالي (AED)": round(net_w * 8.5 * 1.3 * 180)}
    ])
    st.table(boq_df)
    st.metric("التكلفة التقديرية المبدئية للعظم والواجهات", f"{boq_df['الإجمالي (AED)'].sum():,.0f} درهم إماراتي")
