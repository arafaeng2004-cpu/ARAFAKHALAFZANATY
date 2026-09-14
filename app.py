import streamlit as st
import pandas as pd
import json
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Polygon, PathPatch
from matplotlib.path import Path
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Luxury Architecture & Engineering Suite", layout="wide")

# جلب المفتاح تلقائياً من Secrets أو من المتغيرات
api_key = st.secrets.get("GEMINI_API_KEY", "")

st.title("🏛️ المنظومة المعمارية والهندسية التنفيذية - مشاريع الإمارات")
st.markdown("توليد المساقط المعمارية التنفيذية (2D Full Fit-out)، المناظير ثلاثية الأبعاد (Isometric 3D)، كراسة الكميات، وملفات AutoCAD.")

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
    if uploaded_file:
        client = genai.Client(api_key=api_key) if api_key else None
        file_bytes = uploaded_file.read()
        mime_type = "application/pdf" if uploaded_file.name.lower().endswith(".pdf") else uploaded_file.type

        if client:
            with st.spinner("جاري قراءة أبعاد وحدود القسيمة آلياً عبر الذكاء الاصطناعي..."):
                prompt = (
                    "Extract plot dimensions from this UAE site plan (Krooki). "
                    "Return strictly a JSON object: {'width': float, 'length': float, 'plot_area': float}. "
                    "Width is frontage on street, length is depth. Do not include markdown wraps."
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
                    st.success(f"✅ تم استخراج الأبعاد آلياً بنجاح: الواجهة = {width} م | العمق = {length} م | المساحة = {width*length:.1f} م²")
                except Exception as e:
                    st.warning(f"تعذر الاستخراج الآلي ({e})، سيتم اعتماد الأبعاد المعيارية.")
        else:
            st.info("ℹ️ للقراءة الآلية بدون إدخال المفتاح يدوياً، تأكد من إضافة GEMINI_API_KEY في إعدادات Secrets.")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.number_input("عرض واجهة الأرض على الشارع (متر):", min_value=12.0, max_value=200.0, value=30.0, step=0.5)
    with c2:
        length = st.number_input("عمق القسيمة الداخلي (متر):", min_value=15.0, max_value=300.0, value=50.0, step=0.5)
    with c3:
        actual_sbc = st.number_input("جهد التربة SBC المعتمد (kN/m²):", min_value=60.0, max_value=400.0, value=150.0, step=10.0)

# ----------------- المعالجة المعمارية والهندسية -----------------
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

# قاعدة بيانات المقترحات الخمسة بالتقسيم والفرش المعماري
schemes = {
    "المقترح 1: فيلا فاخرة مستقلة (Single Luxury Villa)": {
        "units": 1, "factor": 1.85,
        "rooms": [
            {"n": "مجلس رجال رسمي\nFormal Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.62, "w": net_w*0.48, "h": buildable_l*0.38, "c": "#FEF3C7", "type": "majlis"},
            {"n": "صالة طعام رئيسية\nDining Hall", "x": side_sb, "y": rear_sb + buildable_l*0.32, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A", "type": "dining"},
            {"n": "مطبخ Show + Dirty\nKitchen Suite", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.32, "c": "#FED7AA", "type": "kitchen"},
            {"n": "صالة معيشة عائلية\nFamily Living", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE", "type": "living"},
            {"n": "جناح كبار السن\nMaster Suite (G)", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF", "type": "bed"}
        ],
        "doors": [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360), (side_sb + net_w*0.48, rear_sb + buildable_l*0.5, 1.0, 90, 180)],
        "entries": [("مدخل الضيوف الرسمي (Guest Entry)", (side_sb + net_w*0.24, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.24, rear_sb + buildable_l), "#B45309"),
                    ("مدخل العائلة (Family Entry)", (side_sb + net_w*0.74, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.74, rear_sb + buildable_l), "#0284C7")]
    },
    "المقترح 2: فيلتان متلاصقتان (Twin Villas)": {
        "units": 2, "factor": 1.80,
        "rooms": [
            {"n": "فيلا 1: مجلس ضيوف", "x": side_sb, "y": rear_sb + buildable_l*0.55, "w": net_w/2, "h": buildable_l*0.45, "c": "#DCFCE7", "type": "majlis"},
            {"n": "فيلا 1: صالة عائلية ومطبخ", "x": side_sb, "y": rear_sb, "w": net_w/2, "h": buildable_l*0.55, "c": "#F0FDF4", "type": "living"},
            {"n": "فيلا 2: مجلس ضيوف", "x": side_sb + net_w/2, "y": rear_sb + buildable_l*0.55, "w": net_w/2, "h": buildable_l*0.45, "c": "#E0F2FE", "type": "majlis"},
            {"n": "فيلا 2: صالة عائلية ومطبخ", "x": side_sb + net_w/2, "y": rear_sb, "w": net_w/2, "h": buildable_l*0.55, "c": "#F0F9FF", "type": "living"}
        ],
        "doors": [(side_sb + net_w*0.25, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.75, rear_sb + buildable_l, 1.2, 270, 360)],
        "entries": [("مدخل فيلا 1", (side_sb + net_w*0.25, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.25, rear_sb + buildable_l), "#15803D"),
                    ("مدخل فيلا 2", (side_sb + net_w*0.75, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.75, rear_sb + buildable_l), "#0284C7")]
    },
    "المقترح 3: 3 فلل تاون هاوس (3 Townhouses)": {
        "units": 3, "factor": 1.80,
        "rooms": [{"n": f"تاون هاوس {i+1}\nمعيشة وضيافة", "x": side_sb + i*(net_w/3), "y": rear_sb + buildable_l*0.4, "w": net_w/3, "h": buildable_l*0.6, "c": "#FEF9C3", "type": "living"} for i in range(3)] +
                 [{"n": f"تاون هاوس {i+1}\nمطبخ وحديقة", "x": side_sb + i*(net_w/3), "y": rear_sb, "w": net_w/3, "h": buildable_l*0.4, "c": "#FEF08A", "type": "kitchen"} for i in range(3)],
        "doors": [(side_sb + (i+0.5)*(net_w/3), rear_sb + buildable_l, 1.1, 180, 270) for i in range(3)],
        "entries": [(f"مدخل TH {i+1}", (side_sb + (i+0.5)*(net_w/3), rear_sb + buildable_l + 3.2), (side_sb + (i+0.5)*(net_w/3), rear_sb + buildable_l), "#CA8A04") for i in range(3)]
    },
    "المقترح 4: 4 وحدات دوبلكس (Row Houses)": {
        "units": 4, "factor": 1.75,
        "rooms": [{"n": f"دوبلكس {i+1}\nمعيشة واستقبال", "x": side_sb + i*(net_w/4), "y": rear_sb + buildable_l*0.45, "w": net_w/4, "h": buildable_l*0.55, "c": "#FEE2E2", "type": "living"} for i in range(4)] +
                 [{"n": f"دوبلكس {i+1}\nمطبخ وخدمات", "x": side_sb + i*(net_w/4), "y": rear_sb, "w": net_w/4, "h": buildable_l*0.45, "c": "#FFEDD5", "type": "kitchen"} for i in range(4)],
        "doors": [(side_sb + (i+0.5)*(net_w/4), rear_sb + buildable_l, 1.0, 180, 270) for i in range(4)],
        "entries": [(f"مدخل {i+1}", (side_sb + (i+0.5)*(net_w/4), rear_sb + buildable_l + 3.2), (side_sb + (i+0.5)*(net_w/4), rear_sb + buildable_l), "#DC2626") for i in range(4)]
    },
    "المقترح 5: فيلا + ملحق خدمات (Villa + Outbuilding)": {
        "units": 1, "factor": 1.90,
        "rooms": [
            {"n": "الفيلا الرئيسية (سكن العائلة)\nMain Villa Residence", "x": side_sb, "y": rear_sb, "w": net_w, "h": buildable_l*0.70, "c": "#EEF2FF", "type": "living"},
            {"n": "ملحق الخدمات ومجلس الضيوف\nMajlis & Outbuilding", "x": side_sb, "y": rear_sb + buildable_l*0.78, "w": net_w*0.75, "h": buildable_l*0.22, "c": "#F3E8FF", "type": "majlis"}
        ],
        "doors": [(side_sb + net_w*0.37, rear_sb + buildable_l, 1.3, 180, 270), (side_sb + net_w*0.5, rear_sb + buildable_l*0.70, 1.3, 270, 360)],
        "entries": [("مدخل مجلس الضيوف الخارجي", (side_sb + net_w*0.37, rear_sb + buildable_l + 3.2), (side_sb + net_w*0.37, rear_sb + buildable_l), "#7E22CE"),
                    ("مدخل الفيلا العائلية", (side_sb + net_w*0.85, rear_sb + buildable_l*0.70 + 2.5), (side_sb + net_w*0.85, rear_sb + buildable_l*0.70), "#4338CA")]
    }
}

# ----------------- دوال الرسم المتقدمة -----------------

def render_detailed_floorplan(s_data, title):
    fig, ax = plt.subplots(figsize=(11, 14), dpi=200)
    ax.set_facecolor('#F8FAFC')
    
    # حدود القسيمة والارتدادات
    ax.add_patch(patches.Rectangle((0, 0), width, length, linewidth=3.5, edgecolor='#0F172A', facecolor='#FFFFFF', label='حدود القسيمة (Plot Boundary)'))
    ax.add_patch(patches.Rectangle((side_sb, rear_sb), net_w, net_l, linewidth=2.0, edgecolor='#EF4444', linestyle='--', facecolor='none', label='حد الارتداد المسموح (Setback)'))

    # رسم الغرف مع الجدران المزدوجة والفرش
    wall_t = 0.25  # سماكة الجدار 25 سم
    for r in s_data["rooms"]:
        # الجدار الخارجي للغرفة
        ax.add_patch(patches.Rectangle((r["x"], r["y"]), r["w"], r["h"], linewidth=1.5, edgecolor='#334155', facecolor=r["c"], alpha=0.85))
        # الجدار الداخلي لإبراز السماكة الحقيقية
        ax.add_patch(patches.Rectangle((r["x"]+wall_t, r["y"]+wall_t), r["w"]-2*wall_t, r["h"]-2*wall_t, linewidth=1.0, edgecolor='#94A3B8', facecolor='none', linestyle='-'))

        # تمثيل رمزي واقعي للفرش المعماري
        cx, cy = r["x"] + r["w"]/2, r["y"] + r["h"]/2
        if r["type"] == "majlis":
            # جلسة عربية متصلة U-Shape
            ax.add_patch(patches.Rectangle((r["x"]+1.0, r["y"]+1.0), r["w"]-2.0, 0.7, facecolor='#B45309', alpha=0.4))
            ax.add_patch(patches.Rectangle((r["x"]+1.0, r["y"]+r["h"]-1.7), r["w"]-2.0, 0.7, facecolor='#B45309', alpha=0.4))
            ax.plot([cx-1.5, cx+1.5], [cy, cy], color='#78350F', lw=3.0, label='طاولة ضيافة')
        elif r["type"] == "dining":
            # طاولة طعام وكراسي
            ax.add_patch(patches.Rectangle((cx-1.5, cy-0.8), 3.0, 1.6, facecolor='#D97706', alpha=0.5, edgecolor='#78350F'))
        elif r["type"] == "bed":
            # سرير ماستر مع طاولات جانبية
            ax.add_patch(patches.Rectangle((cx-1.0, r["y"]+0.8), 2.0, 2.2, facecolor='#6D28D9', alpha=0.35, edgecolor='#4C1D95'))
            ax.plot([cx-0.8, cx+0.8], [r["y"]+2.6, r["y"]+2.6], color='#4C1D95', lw=2.5) # وسائد

        # الأعمدة الإنشائية الخرسانية عند الأركان
        for col_x in [r["x"], r["x"] + r["w"] - 0.5]:
            for col_y in [r["y"], r["y"] + r["h"] - 0.25]:
                ax.add_patch(patches.Rectangle((col_x, col_y), 0.5, 0.25, facecolor='#0F172A', edgecolor='black'))

        # صناديق المسميات المنسقة
        ax.text(cx, cy, r["n"], ha='center', va='center', fontsize=9.2, weight='bold', color='#0F172A',
                bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

    # الأبواب ومسارات الفتح
    for d in s_data["doors"]:
        ax.add_patch(Arc((d[0], d[1]), d[2]*2, d[2]*2, angle=0, theta1=d[3], theta2=d[4], color='#0F172A', lw=1.8, ls='--'))
        ax.plot([d[0], d[0] + d[2]], [d[1], d[1]], color='#0F172A', lw=2.5)

    # المداخل بأسهم واضحة
    for ep in s_data["entries"]:
        arrow = FancyArrowPatch(ep[1], ep[2], arrowstyle='-|>', mutation_scale=18, color=ep[3], lw=2.6)
        ax.add_patch(arrow)
        ax.text(ep[1][0], ep[1][1] + 0.6, ep[0], ha='center', va='bottom', fontsize=8.5, weight='bold', color=ep[3],
                bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor=ep[3], alpha=0.95, lw=1.0))

    ax.annotate('الشارع الرئيسي / الواجهة (Main Road Frontage)', xy=(width/2, length), xytext=(width/2, length + 2.5),
                ha='center', fontsize=11, weight='bold', color='#15803D',
                bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

    ax.set_xlim(-width * 0.12, width * 1.12)
    ax.set_ylim(-length * 0.08, length * 1.16)
    ax.set_aspect('equal')
    ax.set_xlabel("عرض الواجهة على الشارع (متر)", fontsize=10, weight='bold')
    ax.set_ylabel("عمق القسيمة الداخلي (متر)", fontsize=10, weight='bold')
    ax.set_title(f"المسقط المعماري التنفيذي الموزع - {title}\nمسطح الأرضي: {effective_ground:.1f} م² | إجمالي البناء (BUA): {effective_ground*s_data['factor']:.1f} م²", fontsize=11.5, weight='bold', pad=15)
    ax.legend(loc='upper right', fontsize=8.5)
    ax.grid(True, linestyle=':', alpha=0.4)
    return fig

def render_3d_isometric_view(title):
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=200)
    ax.set_facecolor('#F0F9FF')
    
    # إسقاط متساوي القياس أكسونومتري 3D حقيقي
    cos30, sin30 = np.cos(np.radians(30)), np.sin(np.radians(30))
    def iso(x, y, z):
        return (x - y) * cos30, (x + y) * sin30 + z

    # الأرضية الخضراء والأرصفة
    p_ground = [iso(-2, -2, 0), iso(22, -2, 0), iso(22, 22, 0), iso(-2, 22, 0)]
    ax.add_patch(Polygon(p_ground, facecolor='#E2E8F0', edgecolor='#94A3B8', lw=1.5))

    # كتلة المبنى الرئيسية (Base Block G+1)
    bx, by, bz = 16, 14, 8.5
    # الوجه الأمامي الجنوبي
    p_front = [iso(0, 0, 0), iso(bx, 0, 0), iso(bx, 0, bz), iso(0, 0, bz)]
    ax.add_patch(Polygon(p_front, facecolor='#F8FAFC', edgecolor='#334155', lw=2.0))
    # الوجه الجانبي الشرقي
    p_side = [iso(bx, 0, 0), iso(bx, by, 0), iso(bx, by, bz), iso(bx, 0, bz)]
    ax.add_patch(Polygon(p_side, facecolor='#CBD5E1', edgecolor='#334155', lw=2.0))
    # السطح العلوي
    p_top = [iso(0, 0, bz), iso(bx, 0, bz), iso(bx, by, bz), iso(0, by, bz)]
    ax.add_patch(Polygon(p_top, facecolor='#E2E8F0', edgecolor='#334155', lw=2.0))

    # البرج الزجاجي الدائري الأيقوني البارز للأمام
    tx, ty, tz, tw = 6, 0, 10.0, 4.0
    p_tower_f = [iso(tx, -1.0, 0), iso(tx+tw, -1.0, 0), iso(tx+tw, -1.0, tz), iso(tx, -1.0, tz)]
    ax.add_patch(Polygon(p_tower_f, facecolor='#38BDF8', edgecolor='#0F172A', lw=2.2, alpha=0.85))
    # تقطيعات كورتن وول زجاج البرج
    for h in np.arange(1.5, tz, 1.4):
        p1 = iso(tx, -1.0, h)
        p2 = iso(tx+tw, -1.0, h)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#0F172A', lw=1.6)

    # المدخل الخشبي الفاخر المزدوج
    p_door = [iso(tx+tw+0.6, 0, 0), iso(tx+tw+2.6, 0, 0), iso(tx+tw+2.6, 0, 3.5), iso(tx+tw+0.6, 0, 3.5)]
    ax.add_patch(Polygon(p_door, facecolor='#78350F', edgecolor='#451A03', lw=1.8))

    # نوافذ المجلس البانورامية
    p_win = [iso(1.0, 0, 1.2), iso(5.0, 0, 1.2), iso(5.0, 0, 6.5), iso(1.0, 0, 6.5)]
    ax.add_patch(Polygon(p_win, facecolor='#7DD3FC', edgecolor='#1E293B', lw=2.0, alpha=0.8))

    # الظلال الساقطة ثلاثية الأبعاد (Sun Shadows)
    p_shadow = [iso(0, 0, 0), iso(bx+4, -3, 0), iso(bx+by+4, by, 0), iso(bx, 0, 0)]
    ax.add_patch(Polygon(p_shadow, facecolor='#0F172A', alpha=0.18))

    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"المنظور المعماري الحجمي ثلاثي الأبعاد (3D Isometric Perspective) - {title}", fontsize=11.5, weight='bold', pad=12)
    return fig

# ----------------- عرض المقترحات في الواجهة -----------------
tabs = st.tabs([
    "المقترح 1 (فيلا فاخرة)",
    "المقترح 2 (فيلتان Twin)",
    "المقترح 3 (3 تاون هاوس)",
    "المقترح 4 (4 دوبلكس)",
    "المقترح 5 (فيلا + ملحق)",
    "مخططات الدفاع المدني و MEP",
    "حصر الكميات والبرنامج الزمني"
])

sch_keys = list(schemes.keys())

for idx in range(5):
    k = sch_keys[idx]
    s_data = schemes[k]
    with tabs[idx]:
        st.subheader(k)
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.markdown("#### 📐 المسقط المعماري والتقسيم الداخلي")
            st.pyplot(render_detailed_floorplan(s_data, k.split(':')[0]))
            
            # تصدير DXF تنفيذي
            try:
                doc = ezdxf.new('R2010')
                msp = doc.modelspace()
                doc.layers.add(name="PLOT_BOUNDARY", color=7)
                msp.add_lwpolyline([(0, 0), (width, 0), (width, length), (0, length), (0, 0)], dxfattribs={'layer': 'PLOT_BOUNDARY'})
                doc.layers.add(name="SETBACKS", color=1)
                msp.add_lwpolyline([(side_sb, rear_sb), (width - side_sb, rear_sb), (width - side_sb, length - front_sb), (side_sb, length - front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'SETBACKS'})
                doc.layers.add(name="WALLS", color=4)
                for r in s_data["rooms"]:
                    msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'WALLS'})
                buf = io.StringIO()
                doc.write(buf)
                st.download_button(f"💾 تحميل ملف AutoCAD (.DXF) - {k.split(':')[0]}", data=buf.getvalue().encode('utf-8'), file_name=f"Scheme_{idx+1}.dxf", mime="application/dxf")
            except Exception as e:
                st.error(f"خطأ DXF: {e}")

        with c_right:
            st.markdown("#### 🏛️ المنظور ثلاثي الأبعاد (3D Perspective)")
            st.pyplot(render_3d_isometric_view(k.split(':')[0]))

with tabs[5]:
    st.subheader("📋 حزمة المخططات التنفيذية وتراخيص الدفاع المدني (Authority MEP Package)")
    st.markdown("""
    * **مخطط الدفاع المدني (Civil Defence):** كواشف دخان ضوئية معنونة + كواشف حرارة بالمطابخ + مطفآت بودرة جافة DCP 6kg وطفاية CO2 + أبواب مقاومة للحريق FD-60.
    * **مخطط الصرف والتغذية (Plumbing):** شبكة مزدوجة مفصولة للأنابيب السوداء والرمادية + مصيدة شحوم للمطبخ + أنابيب تغذية PPR PN20 معزولة حرارياً.
    * **مخطط الأحمال الكهربائية (Electrical):** لوحة MDB رئيسية + قواطع حساسة للتسريب الأرضي ELCB 30mA للغرف الرطبة و 100mA للعمومي + شبكة تأريض أقل من 1 أوم.
    * **مخطط التكييف (HVAC):** تكييف مخفي دكت سبليت Inverter موفر للطاقة بمخارج هواء طولية Linear Slots ومجاري صاج معزولة بالصوف الزجاجي.
    """)

with tabs[6]:
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
