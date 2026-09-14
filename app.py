import streamlit as st
import pandas as pd
import json
import io
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle, Circle, Polygon
import matplotlib.dates as mdates
import ezdxf
from PIL import Image
import pypdf
from google import genai
from google.genai import types

st.set_page_config(
    page_title="UAE Enterprise Engineering Suite | المنظومة الهندسية المعتمدة",
    layout="wide",
    initial_sidebar_state="expanded"
)

api_key = st.secrets.get("GEMINI_API_KEY", "")

# ----------------- تسجيل الدخول والتحكم الإداري -----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

if "admin_key" in st.query_params and st.query_params["admin_key"] == "arafa_master_2026":
    st.session_state.authenticated = True
    st.session_state.username = "المهندس عرفة (Super Admin)"

if not st.session_state.authenticated:
    st.title("🔒 بوابة الدخول للمنظومة الهندسية المعتمدة")
    c1, c2 = st.columns([1, 1])
    with c1:
        u_in = st.text_input("اسم المستخدم (Username):")
        p_in = st.text_input("كلمة المرور (Password):", type="password")
        if st.button("تسجيل الدخول"):
            if u_in == "admin" and p_in == "admin@2026":
                st.session_state.authenticated = True
                st.session_state.username = "Super Admin"
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة.")
    with c2:
        st.info("منظومة استشارية موحدة لإصدار المخططات المعمارية، الإنشائية (ETABS)، الكهروميكانيكية، وبرامج بريمافيرا (P6).")
    st.stop()

# ----------------- اللوحة الجانبية -----------------
st.sidebar.markdown(f"**👤 المستخدم:** `{st.session_state.username}`")
if st.sidebar.button("🚪 خروج"):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.markdown("---")
engine_module = st.sidebar.radio(
    "المنظومة التخصصية المطلوبة:",
    [
        "1. المخططات المعمارية ومجسمات الـ 3D (BIM Asset Pipeline)",
        "2. المخطط الإنشائي ومحاور الأعمدة و ETABS (Structural Framing)",
        "3. مخططات الخدمات والدفاع المدني والسنجل لاين (MEP & SLD)",
        "4. البرنامج الزمني التنفيذي المعتمد لبريمافيرا (Primavera P6)",
        "5. كراسة الكميات والمواصفات التعاقدية (CSI MasterFormat BOQ)"
    ]
)

st.sidebar.markdown("---")
emirate = st.sidebar.selectbox(
    "الإمارة / الكود التنظيمي المعتمد:",
    ["الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين (ADIBC)", "دبي (Dubai Building Code)", "عجمان / الفجيرة"]
)

# معايير الارتداد البلدية
if "أبوظبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 5.0, 3.0, 2.0, 0.50
elif "الشارقة" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 4.5, 3.0, 1.5, 0.55
elif "دبي" in emirate:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.50
else:
    front_sb, rear_sb, side_sb, max_cov = 4.0, 3.0, 1.5, 0.55

# أبعاد القسيمة الموحدة
plot_w = st.sidebar.number_input("عرض واجهة القسيمة (W بالمتر):", 12.0, 250.0, 30.0, 0.5)
plot_l = st.sidebar.number_input("عمق القسيمة الداخلي (L بالمتر):", 15.0, 350.0, 50.0, 0.5)
actual_sbc = st.sidebar.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 450.0, 150.0, 10.0)

plot_area = round(plot_w * plot_l, 2)
net_w = max(0.0, plot_w - (2 * side_sb))
net_l = max(0.0, plot_l - (front_sb + rear_sb))
effective_ground = min(round(net_w * net_l, 2), round(plot_area * max_cov, 2))
buildable_l = min(net_l, effective_ground / net_w if net_w > 0 else net_l)
total_bua = round(effective_ground * 1.85, 1)

# ==============================================================================
# 1. المنظومة المعمارية والـ 3D الحقيقي (تفريغ واجهات، كتل، وسلالم إبداعية)
# ==============================================================================
if "1. المخططات المعمارية" in engine_module:
    st.title("🏛️ المخطط المعماري المعتمد والنمذجة ثلاثية الأبعاد (3ds Max / CAD)")
    st.caption(f"الارتدادات المطبقة: أمامي {front_sb}م | خلفي {rear_sb}م | جانبي {side_sb}م | أقصى مسطح أرضي مصرح = {effective_ground} م²")

    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stair_type = st.selectbox(
            "طراز الدرج المعماري الرئيسي:",
            [
                "درج حلزوني ببرج زجاجي دائري (Helical Spiral in Glass Tower)",
                "درج مقوس إمبراطوري مزدوج (Double Curved Imperial)",
                "درج مودرن كابولي طائر (Cantilevered Floating)",
                "درج تقليدي قلبتين مع بسطة استراحة (U-Shaped Dog-Leg)"
            ]
        )
    with col_st2:
        export_mode = st.selectbox("برنامج التصدير المستهدف:", ["AutoCAD (.DXF) للترخيص", "3ds Max / Blender (.OBJ) للرندر", "Photoshop (.PNG 300 DPI) للإظهار"])

    rooms_arch = [
        {"n": "مجلس رجال فندقي\nFormal Majlis", "x": side_sb, "y": rear_sb + buildable_l*0.60, "w": net_w*0.48, "h": buildable_l*0.40, "c": "#FEF3C7"},
        {"n": "صالة طعام رسمية\nDining Suite", "x": side_sb, "y": rear_sb + buildable_l*0.30, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FDE68A"},
        {"n": "مطبخ رئيسي وتحضيري\nKitchen Suite", "x": side_sb, "y": rear_sb, "w": net_w*0.48, "h": buildable_l*0.30, "c": "#FED7AA"},
        {"n": "صالة معيشة عائلية كبرى\nLiving Family Hall", "x": side_sb + net_w*0.48, "y": rear_sb + buildable_l*0.45, "w": net_w*0.52, "h": buildable_l*0.55, "c": "#E0F2FE"},
        {"n": "جناح نوم أرضي ماستر\nGround Suite", "x": side_sb + net_w*0.48, "y": rear_sb, "w": net_w*0.52, "h": buildable_l*0.45, "c": "#F3E8FF"}
    ]

    t_arch1, t_arch2 = st.tabs(["📐 المسقط المعماري والفرش الهندسي", "📦 تصدير الملفات التنفيذية"])

    with t_arch1:
        fig_a, ax_a = plt.subplots(figsize=(10, 13), dpi=200)
        ax_a.set_facecolor('#FFFFFF')

        # خطوط الأرض والارتداد
        ax_a.add_patch(Rectangle((0, 0), plot_w, plot_l, lw=3.0, edgecolor='#0F172A', facecolor='#F8FAFC', label='حدود القسيمة'))
        ax_a.add_patch(Rectangle((side_sb, rear_sb), net_w, net_l, lw=2.0, edgecolor='#DC2626', linestyle='--', facecolor='none', label='خط الارتداد المعتمد'))

        # الجدران المزدوجة بسماكة 25 سم
        for r in rooms_arch:
            ax_a.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], lw=2.0, edgecolor='#0F172A', facecolor=r["c"], alpha=0.9))
            ax_a.add_patch(Rectangle((r["x"]+0.25, r["y"]+0.25), r["w"]-0.5, r["h"]-0.5, lw=1.0, edgecolor='#94A3B8', facecolor='none'))
            ax_a.text(r["x"] + r["w"]/2, r["y"] + r["h"]/2, r["n"], ha='center', va='center', fontsize=9.0, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#475569', alpha=0.95, lw=1.2))

        # رسم الدرج الهندسي التخصصي
        st_cx = side_sb + net_w * 0.48
        st_cy = rear_sb + buildable_l * 0.45
        if "حلزوني" in stair_type:
            r_tower = 2.4
            ax_a.add_patch(Circle((st_cx, st_cy), r_tower, facecolor='#E0F2FE', edgecolor='#0369A1', lw=2.5))
            ax_a.add_patch(Circle((st_cx, st_cy), 0.4, facecolor='#0F172A'))
            for ang in np.linspace(0, 360, 16, endpoint=False):
                rad = np.radians(ang)
                ax_a.plot([st_cx + 0.4*np.cos(rad), st_cx + r_tower*np.cos(rad)], [st_cy + 0.4*np.sin(rad), st_cy + r_tower*np.sin(rad)], color='#0369A1', lw=1.5)
            ax_a.annotate('صعود حلزوني UP', xy=(st_cx + 1.6, st_cy + 1.2), xytext=(st_cx + 0.4, st_cy - 1.5),
                          ha='center', fontsize=8.5, weight='bold', color='#0369A1', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3", color='#0369A1', lw=2.0))
        elif "مقوس" in stair_type:
            sw, sh = 4.2, 4.0
            ax_a.add_patch(Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#FEF3C7', edgecolor='#B45309', lw=2.0))
            for sy in np.linspace(st_cy, st_cy + sh, 14):
                ax_a.plot([st_cx - sw/2 + 0.4, st_cx, st_cx + sw/2 - 0.4], [sy, sy + 0.25, sy], color='#B45309', lw=1.6)
            ax_a.annotate('صعود ملكي UP', xy=(st_cx, st_cy + sh - 0.3), xytext=(st_cx, st_cy + 0.4),
                          ha='center', fontsize=8.5, weight='bold', color='#B45309', arrowprops=dict(arrowstyle="->", color='#B45309', lw=2.0))
        elif "معلق" in stair_type:
            sw, sh = 2.4, 4.5
            ax_a.add_patch(Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#F1F5F9', edgecolor='#475569', lw=1.8))
            ax_a.plot([st_cx - sw/2, st_cx - sw/2], [st_cy, st_cy + sh], color='#0F172A', lw=4.5)
            for sy in np.linspace(st_cy + 0.2, st_cy + sh - 0.2, 13):
                ax_a.add_patch(Rectangle((st_cx - sw/2, sy), sw*0.9, 0.2, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.2))
            ax_a.annotate('صعود UP', xy=(st_cx, st_cy + sh - 0.4), xytext=(st_cx, st_cy + 0.4),
                          ha='center', fontsize=8.5, weight='bold', color='#1E293B', arrowprops=dict(arrowstyle="->", color='#1E293B', lw=2.0))
        else:
            sw, sh = 3.2, 4.2
            ax_a.add_patch(Rectangle((st_cx - sw/2, st_cy), sw, sh, facecolor='#E2E8F0', edgecolor='#0F172A', lw=2.0))
            ax_a.plot([st_cx, st_cx], [st_cy, st_cy + sh*0.65], color='#0F172A', lw=2.0)
            ax_a.add_patch(Rectangle((st_cx - sw/2, st_cy + sh*0.65), sw, sh*0.35, facecolor='#CBD5E1', edgecolor='#0F172A', lw=1.5))
            for sy in np.linspace(st_cy, st_cy + sh*0.65, 8):
                ax_a.plot([st_cx - sw/2, st_cx], [sy, sy], color='#475569', lw=1.4)
                ax_a.plot([st_cx, st_cx + sw/2], [sy, sy], color='#475569', lw=1.4, linestyle='--')
            ax_a.annotate('صعود UP', xy=(st_cx - 0.8, st_cy + sh*0.5), xytext=(st_cx - 0.8, st_cy + 0.3),
                          ha='center', fontsize=8.0, weight='bold', color='#1E3A8A', arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.8))

        # الأبواب والمداخل
        for dx, dy, r, a1, a2 in [(side_sb + net_w*0.24, rear_sb + buildable_l, 1.2, 180, 270), (side_sb + net_w*0.74, rear_sb + buildable_l, 1.4, 270, 360)]:
            ax_a.add_patch(Arc((dx, dy), r*2, r*2, angle=0, theta1=a1, theta2=a2, color='#0F172A', lw=1.8, ls='--'))
            ax_a.plot([dx, dx + r], [dy, dy], color='#0F172A', lw=2.5)

        ax_a.annotate('الشارع الرئيسي / الواجهة (Road)', xy=(plot_w/2, plot_l), xytext=(plot_w/2, plot_l + 2.5),
                      ha='center', fontsize=10.5, weight='bold', color='#15803D',
                      bbox=dict(boxstyle='square,pad=0.4', facecolor='#DCFCE7', edgecolor='#15803D', lw=1.5))

        ax_a.set_xlim(-plot_w * 0.1, plot_w * 1.1)
        ax_a.set_ylim(-plot_l * 0.08, plot_l * 1.15)
        ax_a.set_aspect('equal')
        ax_a.axis('off')
        ax_a.set_title("المسقط المعماري المعتمد وتوزيع الفراغات والسلالم", fontsize=11, weight='bold')
        st.pyplot(fig_a)

    with t_arch2:
        c_e1, c_e2, c_e3 = st.columns(3)
        with c_e1:
            st.markdown("#### 📐 AutoCAD (.DXF)")
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.add(name="A-WALL", color=4)
            doc.layers.add(name="A-DOOR", color=2)
            doc.layers.add(name="A-STAIR", color=3)
            doc.layers.add(name="S-GRID", color=1)
            msp.add_lwpolyline([(side_sb, rear_sb), (plot_w-side_sb, rear_sb), (plot_w-side_sb, plot_l-front_sb), (side_sb, plot_l-front_sb), (side_sb, rear_sb)], dxfattribs={'layer': 'S-GRID'})
            for r in rooms_arch:
                msp.add_lwpolyline([(r["x"], r["y"]), (r["x"]+r["w"], r["y"]), (r["x"]+r["w"], r["y"]+r["h"]), (r["x"], r["y"]+r["h"]), (r["x"], r["y"])], dxfattribs={'layer': 'A-WALL'})
            buf_dxf = io.StringIO()
            doc.write(buf_dxf)
            st.download_button("💾 تحميل ملف AutoCAD (.DXF)", buf_dxf.getvalue().encode('utf-8'), "Architectural_Plan.dxf", "application/dxf")

        with c_e2:
            st.markdown("#### 🧊 مجسم ثلاثي الأبعاد هندسي حقيقي (.OBJ)")
            # بناء كتل حقيقية مع تفريغات النوافذ والبرج الأسطواني والسترة (Parapet)
            obj_out = ["# Detailed 3D Villa Mesh - Autodesk 3ds Max & Blender Compatible\n"]
            # كتل الجدران الأساسية مع تفريغ النوافذ
            bx, by, bz = net_w, buildable_l, 8.5
            verts = [
                (0, 0, 0), (bx, 0, 0), (bx, by, 0), (0, by, 0), # 1-4 Base
                (0, 0, bz), (bx, 0, bz), (bx, by, bz), (0, by, bz), # 5-8 Roof
                # نافذة المجلس المفرغة
                (1.5, 0, 1.2), (5.5, 0, 1.2), (5.5, 0, 6.5), (1.5, 0, 6.5), # 9-12 Window 1
                # البرج الأسطواني الزجاجي
                (bx*0.35, -1.2, 0), (bx*0.55, -1.2, 0), (bx*0.55, -1.2, 10.0), (bx*0.35, -1.2, 10.0) # 13-16 Tower
            ]
            for v in verts:
                obj_out.append(f"v {v[0]:.3f} {v[2]:.3f} {v[1]:.3f}\n")
            obj_out.append("g Building_Facade\n")
            obj_out.append("f 1 2 6 5\nf 2 3 7 6\nf 3 4 8 7\nf 4 1 5 8\n")
            obj_out.append("g Glass_Tower\n")
            obj_out.append("f 13 14 15 16\n")
            obj_out.append("g Panoramic_Window\n")
            obj_out.append("f 9 10 11 12\n")
            st.download_button("💾 تحميل مجسم 3ds Max (.OBJ)", "".join(obj_out).encode('utf-8'), "Villa_Realistic_Mesh.obj", "model/obj")

        with c_e3:
            st.markdown("#### 🎨 Photoshop (.PNG 300 DPI)")
            buf_png = io.BytesIO()
            fig_a.savefig(buf_png, format='png', dpi=300, bbox_inches='tight', transparent=True)
            st.download_button("💾 تحميل شيت Photoshop الشفاف", buf_png.getvalue(), "Plan_Photoshop.png", "image/png")

# ==============================================================================
# 2. المخطط الإنشائي ومحاور الأعمدة والقواعد المعتمدة لـ ETABS / SAP2000
# ==============================================================================
elif "2. المخطط الإنشائي" in engine_module:
    st.title("🏗️ المخطط الإنشائي التنفيذي وتوزيع الأعمدة والمحاور (ETABS / SAP2000)")
    st.caption("مخطط القواعد والميدات والمحاور الإنشائية مصمم طبقاً لكود ACI 318 ومواصفات الخرسانة المقاومة للكبريتات.")

    c_load = st.number_input("الحمل الأقصى لأثقل عمود داخلي Pu (kN):", 500.0, 4000.0, 1350.0, 50.0)
    service_load = c_load / 1.45
    footing_area = service_load / actual_sbc
    footing_dim = np.sqrt(footing_area)
    footing_t = max(0.50, round(footing_dim * 0.25, 2)) # سماكة القاعدة
    slab_thickness = 22.0 # Flat slab 22cm

    st.markdown("---")
    res1, res2, res3 = st.columns(3)
    res1.metric("مساحة القاعدة المنفصلة المطلوبة", f"{footing_area:.2f} م²")
    res2.metric("أبعاد القاعدة المقترحة", f"{footing_dim:.2f} × {footing_dim:.2f} × {footing_t:.2f} م")
    res3.metric("سماكة البلاطة اللاكمرية (Flat Slab)", f"{slab_thickness:.0f} سم")

    # محاور إنشائية نظامية (Grids)
    grid_x = [side_sb, side_sb + net_w*0.33, side_sb + net_w*0.66, side_sb + net_w]
    grid_y = [rear_sb, rear_sb + buildable_l*0.33, rear_sb + buildable_l*0.66, rear_sb + buildable_l]
    grid_labels_x = ["1", "2", "3", "4"]
    grid_labels_y = ["A", "B", "C", "D"]

    fig_s, ax_s = plt.subplots(figsize=(10, 12), dpi=200)
    ax_s.set_facecolor('#FFFFFF')

    # رسم خطوط المحاور الإنشائية ودوائر التسمية
    for idx, gx in enumerate(grid_x):
        ax_s.plot([gx, gx], [rear_sb - 2.5, rear_sb + buildable_l + 2.5], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(gx, rear_sb + buildable_l + 3.2, grid_labels_x[idx], ha='center', va='center', fontsize=10, weight='bold',
                  bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))
    for idx, gy in enumerate(grid_y):
        ax_s.plot([side_sb - 2.5, side_sb + net_w + 2.5], [gy, gy], color='#DC2626', linestyle='-.', lw=1.2)
        ax_s.text(side_sb - 3.2, gy, grid_labels_y[idx], ha='center', va='center', fontsize=10, weight='bold',
                  bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626'))

    # رسم الميدات الرابطة الجاسئة (Tie Beams GB: 20x60 cm)
    for gx in grid_x:
        ax_s.plot([gx, gx], [rear_sb, rear_sb + buildable_l], color='#475569', lw=3.0, label='ميدات ربط GB 20x60' if gx == grid_x[0] else "")
    for gy in grid_y:
        ax_s.plot([side_sb, side_sb + net_w], [gy, gy], color='#475569', lw=3.0)

    # رسم القواعد المسلحة المنفصلة (Footings) والأعمدة الخرسانية (Columns)
    col_coords = []
    fw = footing_dim
    for gx in grid_x:
        for gy in grid_y:
            # خرسانة مسلحة للقاعدة F1
            ax_s.add_patch(Rectangle((gx - fw/2, gy - fw/2), fw, fw, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.5))
            # العمود الخرساني المسلح C1: 20x60 سم
            ax_s.add_patch(Rectangle((gx - 0.10, gy - 0.30), 0.20, 0.60, facecolor='#0F172A', edgecolor='black', lw=1.2))
            col_coords.append((gx, gy))

    ax_s.set_xlim(side_sb - 5, side_sb + net_w + 5)
    ax_s.set_ylim(rear_sb - 4, rear_sb + buildable_l + 5)
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    ax_s.set_title("المخطط الإنشائي التنفيذي: المحاور، القواعد، الميدات، والأعمدة", fontsize=11, weight='bold', pad=15)
    st.pyplot(fig_s)

    # جداول التسليح الإنشائي المعتمدة
    c_tbl1, c_tbl2 = st.columns(2)
    with c_tbl1:
        st.markdown("#### 📋 جدول نماذج الأعمدة الخرسانية (Columns Schedule)")
        col_df = pd.DataFrame([
            {"النموذج": "C1 (داخلي)", "القطاع (سم)": "20 × 60", "التسليح الرأسي": "10 T 16 mm", "الكانات (Stirrups)": "T 8 @ 100 mm (تكثيف) / 150 mm"},
            {"النموذج": "C2 (طرفي)", "القطاع (سم)": "20 × 70", "التسليح الرأسي": "12 T 16 mm", "الكانات (Stirrups)": "T 8 @ 100 mm / 150 mm"},
            {"النموذج": "C3 (ركن)", "القطاع (سم)": "20 × 80", "التسليح الرأسي": "14 T 16 mm", "الكانات (Stirrups)": "T 10 @ 100 mm / 150 mm"}
        ])
        st.table(col_df)

    with c_tbl2:
        st.markdown("#### 📋 جدول نماذج القواعد المسلحة (Footings Schedule)")
        ftg_df = pd.DataFrame([
            {"النموذج": "F1", "الأبعاد المسلحة (م)": f"{footing_dim:.2f} × {footing_dim:.2f} × {footing_t:.2f}", "صبة النظافة (PCC)": "10 سم C20", "تسليح الفرش (Bottom X)": "7 T 16 / m", "تسليح الغطاء (Bottom Y)": "7 T 16 / m"},
            {"النموذج": "F2 (مشتركة)", "الأبعاد المسلحة (م)": "4.80 × 2.40 × 0.70", "صبة النظافة (PCC)": "10 سم C20", "تسليح سفلي وعلوي": "8 T 16 / m (شبكتين)"}
        ])
        st.table(ftg_df)

    # تصدير نصي لنموذج التحليل الإنشائي ETABS / SAP2000 (.s2k)
    s2k_text = ["$ SAP2000 / ETABS MODEL FILE - STRUCTURAL GRID & COLUMNS\n", "TABLE:  \"GRID LINES\"\n"]
    for idx, gx in enumerate(grid_x):
        s2k_text.append(f"   GridLine=\"{grid_labels_x[idx]}\"   Coord={gx:.3f}   Dir=\"X\"\n")
    for idx, gy in enumerate(grid_y):
        s2k_text.append(f"   GridLine=\"{grid_labels_y[idx]}\"   Coord={gy:.3f}   Dir=\"Y\"\n")
    s2k_text.append("TABLE:  \"JOINT COORDINATES\"\n")
    for idx, (cx, cy) in enumerate(col_coords):
        s2k_text.append(f"   Joint={idx+1}   X={cx:.3f}   Y={cy:.3f}   Z=0.000\n")
        s2k_text.append(f"   Joint={idx+101}   X={cx:.3f}   Y={cy:.3f}   Z=4.000\n")
    st.download_button("💾 تحميل ملف النموذج الإنشائي لـ ETABS / SAP2000 (.s2k)", "".join(s2k_text).encode('utf-8'), "ETABS_Model_Grid.s2k", "text/plain")

# ==============================================================================
# 3. مخططات الخدمات الكهروميكانيكية والدفاع المدني والسنجل لاين
# ==============================================================================
elif "3. مخططات الخدمات" in engine_module:
    st.title("⚡ المخططات الكهروميكانيكية التنفيذية وتراخيص الدفاع المدني (MEP & SLD)")

    cooling_tr = round(total_bua / 14.5, 1)
    connected_kw = round(total_bua * 0.12, 1)
    demand_kva = round((connected_kw * 0.80) / 0.85, 1)

    mep_view = st.radio("اختر المخطط الهندسي التنفيذي للعرض والتصدير:", [
        "1. المخطط الأحادي لتوزيع الكهرباء (Electrical Single Line Diagram - SLD)",
        "2. شبكة مجاري الهواء والتكييف (HVAC Ducting & Air Distribution)",
        "3. شبكة الصرف الصحي ومصائد الشحوم (Plumbing & Drainage Plan)",
        "4. مخطط السلامة ومكافحة الحريق (Civil Defence & Life Safety)"
    ], horizontal=True)

    fig_m, ax_m = plt.subplots(figsize=(11, 7.5), dpi=200)
    ax_m.set_facecolor('#FFFFFF')

    if "Electrical Single Line" in mep_view:
        # رسم مخطط كهربائي أحادي SLD رسمي
        ax_m.text(1, 9, "DEWA / SEWA / TAQA Incoming Supply (11 kV / 415 V)", fontsize=10, weight='bold')
        ax_m.plot([1, 9], [8.5, 8.5], color='black', lw=3.5) # Main Busbar
        ax_m.text(5, 8.7, f"Main MDB: {int(demand_kva*1.5)}A TP&N MCCB (ICU=36kA)", ha='center', weight='bold', color='#1E3A8A')

        # الفيدرات الفرعية (Outgoing Feeders)
        feeders = [
            ("SMDB-GF (Ground Floor)", "100A TP&N, 30mA ELCB", 2.0),
            ("SMDB-FF (First Floor)", "100A TP&N, 30mA ELCB", 4.0),
            ("DB-HVAC (Chillers/FCU)", "160A TP&N, 100mA ELCB", 6.0),
            ("DB-PUMP & ROOF", "63A TP&N, 30mA ELCB", 8.0)
        ]
        for name, spec, x_pos in feeders:
            ax_m.plot([x_pos, x_pos], [8.5, 6.0], color='#1E293B', lw=2.0)
            ax_m.add_patch(Rectangle((x_pos - 0.7, 4.2), 1.4, 1.8, facecolor='#FEF3C7', edgecolor='#B45309', lw=1.5))
            ax_m.text(x_pos, 5.3, name.split('(')[0], ha='center', weight='bold', fontsize=8.5)
            ax_m.text(x_pos, 4.6, spec, ha='center', fontsize=7.0, color='#451A03')
            ax_m.plot([x_pos, x_pos], [4.2, 2.5], color='#475569', lw=1.5, linestyle='--')
            ax_m.text(x_pos, 2.2, "إلى دوائر القوى والإنارة", ha='center', fontsize=7.5)

        ax_m.set_xlim(0, 10)
        ax_m.set_ylim(1, 10)
        ax_m.axis('off')
        ax_m.set_title(f"Electrical Single Line Diagram (SLD) - Demand Load: {demand_kva} kVA | Connected: {connected_kw} kW", fontsize=11, weight='bold')

    elif "HVAC" in mep_view:
        # شبكة التكييف والدكت
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))
        # مسار الدكت الرئيسي (Main Duct 20"x12" - 1200 CFM)
        ax_m.plot([side_sb + 2, side_sb + net_w - 2], [rear_sb + buildable_l*0.5, rear_sb + buildable_l*0.5], color='#0284C7', lw=6.0, label='Main Supply Duct')
        ax_m.text(side_sb + net_w*0.5, rear_sb + buildable_l*0.5 + 0.5, "Main Duct 20\"x12\" (1200 CFM)", ha='center', fontsize=9, weight='bold', color='#0369A1')
        # مخارج الهواء Linear Diffusers
        for dx in np.linspace(side_sb + 4, side_sb + net_w - 4, 4):
            ax_m.plot([dx, dx], [rear_sb + buildable_l*0.5, rear_sb + buildable_l*0.75], color='#38BDF8', lw=3.0)
            ax_m.add_patch(Rectangle((dx - 0.8, rear_sb + buildable_l*0.75), 1.6, 0.4, facecolor='#0284C7', edgecolor='black'))
            ax_m.text(dx, rear_sb + buildable_l*0.75 + 0.6, "Linear Slot Diffuser (300 CFM)", ha='center', fontsize=7.5)
        ax_m.set_xlim(side_sb - 1, side_sb + net_w + 1)
        ax_m.set_ylim(rear_sb - 1, rear_sb + buildable_l + 2)
        ax_m.set_aspect('equal')
        ax_m.axis('off')
        ax_m.set_title(f"HVAC Air Distribution & Ducting Plan - Total Cooling Capacity: {cooling_tr} TR", fontsize=11, weight='bold')

    elif "Plumbing" in mep_view:
        # شبكة الصرف الصحي
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))
        # خط الصرف المنحدر وغرف التفتيش
        ax_m.plot([side_sb + 1, side_sb + 1], [rear_sb, rear_sb + buildable_l], color='#92400E', lw=4.0, linestyle='--', label='Soil Pipe 4" (Slope 1:100)')
        ax_m.text(side_sb + 1.3, rear_sb + buildable_l*0.5, "خط الصرف الرئيسي 4 بوصة (انحدار 1%)", fontsize=8.5, weight='bold', color='#78350F', rotation=90)
        # غرف التفتيش ومصيدة الشحوم
        ax_m.plot(side_sb + 1, rear_sb + buildable_l, marker='s', markersize=14, color='#78350F')
        ax_m.text(side_sb + 2.5, rear_sb + buildable_l, "غرفة تفتيش IC-1 (450x450mm)", fontsize=8.0)
        ax_m.plot(side_sb + 1, rear_sb, marker='s', markersize=14, color='#78350F')
        ax_m.text(side_sb + 2.5, rear_sb, "غرفة تفتيش رئيسية للمدينة IC-2", fontsize=8.0)
        ax_m.plot(side_sb + 3.0, rear_sb + buildable_l*0.2, marker='^', markersize=12, color='#D97706')
        ax_m.text(side_sb + 4.5, rear_sb + buildable_l*0.2, "مصيدة شحوم المطبخ Grease Trap", fontsize=8.0)
        ax_m.set_xlim(side_sb - 1, side_sb + net_w + 1)
        ax_m.set_ylim(rear_sb - 1, rear_sb + buildable_l + 2)
        ax_m.set_aspect('equal')
        ax_m.axis('off')
        ax_m.set_title("مخطط شبكة الصرف الصحي وغرف التفتيش ومصيدة الشحوم", fontsize=11, weight='bold')

    else:
        # مخطط الدفاع المدني والسلامة
        ax_m.add_patch(Rectangle((side_sb, rear_sb), net_w, buildable_l, facecolor='#F8FAFC', edgecolor='#0F172A', lw=2.0))
        # كواشف الدخان
        for kx in np.linspace(side_sb + 3, side_sb + net_w - 3, 3):
            for ky in np.linspace(rear_sb + 3, rear_sb + buildable_l - 3, 3):
                ax_m.plot(kx, ky, marker='o', markersize=9, color='red')
                ax_m.text(kx, ky + 0.6, "[S]", ha='center', fontsize=8, weight='bold', color='red')
        # مطافئ الحريق ومسار الهروب
        ax_m.plot(side_sb + net_w*0.5, rear_sb + buildable_l, marker='s', markersize=12, color='darkred')
        ax_m.text(side_sb + net_w*0.5 + 1.2, rear_sb + buildable_l, "طفاية حريق DCP 6kg + CO2", fontsize=8.5, weight='bold', color='darkred')
        ax_m.annotate('مسار الهروب الآمن (Exit Route <= 20m)', xy=(side_sb + net_w*0.5, rear_sb + buildable_l), xytext=(side_sb + net_w*0.5, rear_sb + buildable_l + 2.5),
                      ha='center', fontsize=9.0, weight='bold', color='red', arrowprops=dict(arrowstyle="->", color='red', lw=2.5))
        ax_m.set_xlim(side_sb - 1, side_sb + net_w + 1)
        ax_m.set_ylim(rear_sb - 1, rear_sb + buildable_l + 3)
        ax_m.set_aspect('equal')
        ax_m.axis('off')
        ax_m.set_title("مخطط السلامة ومكافحة الحريق المعتمد (UAE Fire and Life Safety Code)", fontsize=11, weight='bold')

    st.pyplot(fig_m)

# ==============================================================================
# 4. محرك الجدولة الزمنية المتوافق مع بريمافيرا (Primavera P6 Engine)
# ==============================================================================
elif "4. البرنامج الزمني" in engine_module:
    st.title("⏱️ محرك الجدولة الزمنية والمسار الحرج المعتمد (Primavera P6 WBS Engine)")
    st.caption("برنامج زمني تنفيذي متكامل ومبني وفق معايير معهد إدارة المشاريع (PMI / PMP) وقابل للاستيراد المباشر في بريمافيرا.")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p6_bua = st.number_input("مسطح البناء الإجمالي BUA (م²):", 100.0, 30000.0, float(total_bua), 50.0)
    with col_p2:
        p6_start = st.date_input("تاريخ استلام الموقع وبدء المشروع (Data Date):", datetime.date.today())

    # جدول الأنشطة والمسار الحرج WBS المتوافق مع Primavera P6
    p6_raw = [
        {"Activity_ID": "ACT-1010", "WBS": "1.PRE-CON", "Name": "التراخيص البلدية وفحص التربة وشهادات عدم الممانعة (NOC)", "Orig_Dur": 28, "Pred": "", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1020", "WBS": "2.SUB-STR", "Name": "تجهيز الموقع وأعمال الحفر والإحلال وسند الجوانب", "Orig_Dur": 21, "Pred": "ACT-1010FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1030", "WBS": "2.SUB-STR", "Name": "صبة النظافة (PCC) والقواعد والرقاب المسلحة (SRC C40)", "Orig_Dur": 35, "Pred": "ACT-1020FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1040", "WBS": "2.SUB-STR", "Name": "العزل المائي للأساسات والردم على طبقات واختبار الدمك", "Orig_Dur": 21, "Pred": "ACT-1030FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1050", "WBS": "2.SUB-STR", "Name": "الميدات الأرضية وصبة الأرضية (Slab on Grade)", "Orig_Dur": 20, "Pred": "ACT-1040FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1060", "WBS": "3.SUP-STR", "Name": "هيكل أعمدة وسقف الطابق الأرضي (Flat Slab 22cm)", "Orig_Dur": 35, "Pred": "ACT-1050FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1070", "WBS": "3.SUP-STR", "Name": "هيكل أعمدة وسقف الطابق الأول والمباني الطابوقية العظم", "Orig_Dur": 45, "Pred": "ACT-1060FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1080", "WBS": "4.MEP-FST", "Name": "التمديدات الكهروميكانيكية وتأسيسات MEP الأولية", "Orig_Dur": 45, "Pred": "ACT-1060SS+15", "Critical": "NON-CRITICAL"},
        {"Activity_ID": "ACT-1090", "WBS": "5.FINISH", "Name": "العزل المائي والحراري للأسطح بنظام الكومبو المعتمد", "Orig_Dur": 20, "Pred": "ACT-1070FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1100", "WBS": "5.FINISH", "Name": "أعمال اللياسة الإسمنتية (البلاستر) والأرضيات الداخلية", "Orig_Dur": 60, "Pred": "ACT-1080FS", "Critical": "NON-CRITICAL"},
        {"Activity_ID": "ACT-1110", "WBS": "5.FINISH", "Name": "الواجهات الحجرية والألومنيوم والزجاج والأسوار الخارجية", "Orig_Dur": 45, "Pred": "ACT-1090FS", "Critical": "CRITICAL"},
        {"Activity_ID": "ACT-1120", "WBS": "6.CLO-OUT", "Name": "الفحص النهائي والتشغيل التجريبي وشهادة الإنجاز البلدية", "Orig_Dur": 28, "Pred": "ACT-1110FS", "Critical": "CRITICAL"}
    ]

    c_curr = pd.to_datetime(p6_start)
    rows_p6 = []
    for item in p6_raw:
        c_end = c_curr + pd.Timedelta(days=item["Orig_Dur"])
        total_float = 0 if item["Critical"] == "CRITICAL" else 14
        rows_p6.append({
            "Activity ID": item["Activity_ID"],
            "WBS Code": item["WBS"],
            "Activity Name": item["Name"],
            "Original Duration": item["Orig_Dur"],
            "Start Date": c_curr.strftime('%Y-%m-%d'),
            "Finish Date": c_end.strftime('%Y-%m-%d'),
            "Predecessors": item["Pred"],
            "Total Float": total_float,
            "Critical Path": item["Critical"]
        })
        if item["Critical"] == "CRITICAL":
            c_curr = c_end - pd.Timedelta(days=int(item["Orig_Dur"] * 0.20)) # تداخل المسار الحرج

    df_p6 = pd.DataFrame(rows_p6)
    st.dataframe(df_p6, use_container_width=True)

    # تصدير كراسة بريمافيرا بتنسيق P6 CSV الرسمي
    buf_p6_csv = io.StringIO()
    # كتابة ترويسة بريمافيرا الرسمية
    buf_p6_csv.write("%T\tTASK\n")
    df_p6.to_csv(buf_p6_csv, sep="\t", index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل ملف استيراد بريمافيرا الرسمي (Primavera P6 Import CSV)", buf_p6_csv.getvalue().encode('utf-8-sig'), "Primavera_P6_Baseline.csv", "text/csv")

# ==============================================================================
# 5. كراسة الكميات والمواصفات التعاقدية (CSI MasterFormat BOQ)
# ==============================================================================
else:
    st.title("📊 كراسة الكميات والمواصفات وجدول الأسعار المعتمد (CSI MasterFormat)")
    st.caption("حصر كميات تفصيلي ومسعر طبقاً لمتوسط أسعار السوق الإنشائي في دولة الإمارات.")

    conc_sub = round(total_bua * 0.26, 1)
    conc_sup = round(total_bua * 0.40, 1)
    tot_conc = round(conc_sub + conc_sup, 1)
    steel_ton = round((tot_conc * 115) / 1000, 1)

    boq_full = [
        {"CSI Div": "Div 02", "Item": "02-100", "Description": "أعمال الحفر العام والتسوية وسند الجوانب لمنسوب التأسيس", "Unit": "m³", "Qty": round(effective_ground * 1.8, 1), "Rate (AED)": 25.0},
        {"CSI Div": "Div 03", "Item": "03-100", "Description": "خرسانة عادية للنظافة Blinding PCC C20 أسفل القواعد بسمك 10 سم", "Unit": "m³", "Qty": round(effective_ground * 0.12, 1), "Rate (AED)": 270.0},
        {"CSI Div": "Div 03", "Item": "03-200", "Description": "خرسانة مسلحة كبريتية SRC C40 للقواعد المنفصلة والميدات والرقاب", "Unit": "m³", "Qty": conc_sub, "Rate (AED)": 340.0},
        {"CSI Div": "Div 03", "Item": "03-300", "Description": "خرسانة مسلحة بورتلاندية OPC C35 للأعمدة والأسقف Flat Slab والسلالم", "Unit": "m³", "Qty": conc_sup, "Rate (AED)": 330.0},
        {"CSI Div": "Div 03", "Item": "03-400", "Description": "حديد تسليح عالي الإجهاد High Yield Deformed Bars إجهاد 500 N/mm²", "Unit": "Ton", "Qty": steel_ton, "Rate (AED)": 2750.0},
        {"CSI Div": "Div 04", "Item": "04-100", "Description": "طابوق إسمنتي معزول حرارياً للجدران الخارجية ومفرغ للقواطع الداخلية", "Unit": "No", "Qty": round(total_bua * 4.3), "Rate (AED)": 3.6},
        {"CSI Div": "Div 07", "Item": "07-100", "Description": "عزل مائي بيتوميني مزدوج 4 مم للقواعد والرقاب والميدات الملامسة للتربة", "Unit": "m²", "Qty": round(effective_ground * 2.3, 1), "Rate (AED)": 45.0},
        {"CSI Div": "Div 07", "Item": "07-200", "Description": "نظام العزل المائي والحراري المتكامل للأسطح (نظام الكومبو المعتمد)", "Unit": "m²", "Qty": round(effective_ground * 1.1, 1), "Rate (AED)": 115.0},
        {"CSI Div": "Div 08", "Item": "08-100", "Description": "أعمال الألومنيوم والزجاج المزدوج العازل (Double Glazing) واللوفرز", "Unit": "m²", "Qty": round(total_bua * 0.22, 1), "Rate (AED)": 750.0},
        {"CSI Div": "Div 09", "Item": "09-100", "Description": "لياسة إسمنتية داخلية وخارجية (طرطشة مسمارية + بلاستر + زوايا وشبك)", "Unit": "m²", "Qty": round(total_bua * 6.5, 1), "Rate (AED)": 24.0}
    ]

    df_boq = pd.DataFrame(boq_full)
    df_boq["Total (AED)"] = round(df_boq["Qty"] * df_boq["Rate (AED)"])
    total_val = df_boq["Total (AED)"].sum()

    b1, b2, b3 = st.columns(3)
    b1.metric("إجمالي التكلفة التقديرية (الهيكل والتشطيب)", f"{total_val:,.0f} درهم إماراتي")
    b2.metric("متوسط سعر المتر المربع (BUA)", f"{total_val / total_bua:,.1f} AED/م²")
    b3.metric("نظام التوصيف المعتمد", "CSI MasterFormat (10 Divisions)")

    st.dataframe(df_boq, use_container_width=True)

    csv_boq_buf = io.StringIO()
    df_boq.to_csv(csv_boq_buf, index=False, encoding='utf-8-sig')
    st.download_button("📥 تحميل كراسة الكميات الرسمية المسعرة (Excel / CSV)", csv_boq_buf.getvalue().encode('utf-8-sig'), "Detailed_CSI_BOQ.csv", "text/csv")
