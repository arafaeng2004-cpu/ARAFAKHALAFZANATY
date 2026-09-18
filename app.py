import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, Rectangle, Polygon
from PIL import Image
import io
import datetime
import ezdxf

# ----------------- ضبط إعدادات المنظومة -----------------
st.set_page_config(
    page_title="EmaratBuild Enterprise Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تأمين وقراءة المفتاح السحابي
secret_api_key = st.secrets.get("GEMINI_API_KEY", "")

# تهيئة الحقيقة المركزية للمشروع (Digital Twin State)
if "project_twin" not in st.session_state:
    st.session_state.project_twin = {
        "workflow": "المشاريع الجديدة (Greenfield)",
        "emirate": "دبي (Dubai Building Code DBC)",
        "plot_w": 25.0,
        "plot_l": 32.0,
        "sbc": 150.0,
        "sbc_status": "افتراض آمن غير مؤكد (Unverified)",
        "bua": 650.0,
        "steel_span": 24.0,
        "steel_len": 36.0,
        "rev_id": "Rev.00",
        "defect_log": [],
        "revisions": []
    }

pt = st.session_state.project_twin

# ----------------- الشريط الجانبي والتحكم العام -----------------
st.sidebar.markdown("### 🏢 **EmaratBuild OS v4.0**")
st.sidebar.caption("المنظومة الهندسية الاستشارية المعتمدة لكودات الإمارات")

workflow_mode = st.sidebar.radio(
    "مسار العمل الرئيسي:",
    [
        "🏛️ المسار 1: المشاريع الجديدة (Greenfield Design)",
        "🚩 المسار 2: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)"
    ],
    key="sb_workflow_sel"
)

pt["emirate"] = st.sidebar.selectbox(
    "الكود التنظيمي المعتمد:",
    ["دبي (Dubai Building Code DBC)", "الشارقة (المناطق الحضرية والشرقية)", "أبوظبي / العين (ADIBC)", "عجمان / الفجيرة"],
    key="sb_emirate_sel"
)

# محددات البناء البلدية
if "أبوظبي" in pt["emirate"]:
    sb_f, sb_r, sb_s, max_cov, roof_cov = 5.0, 3.0, 2.0, 0.50, 0.35
elif "الشارقة" in pt["emirate"]:
    sb_f, sb_r, sb_s, max_cov, roof_cov = 4.5, 3.0, 1.5, 0.55, 0.40
elif "دبي" in pt["emirate"]:
    sb_f, sb_r, sb_s, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.50, 0.35
else:
    sb_f, sb_r, sb_s, max_cov, roof_cov = 4.0, 3.0, 1.5, 0.55, 0.40

override_key = st.sidebar.text_input("تحديث مفتاح Gemini API (اختياري):", type="password", key="sb_key_override")
active_api = override_key.strip() if override_key.strip() else secret_api_key.strip()

# ==============================================================================
# المسار 1: المشاريع الجديدة (Greenfield Digital Twin)
# ==============================================================================
if "المشاريع الجديدة" in workflow_mode:
    st.title("🏛️ منظومة التصميم والنمذجة للمشاريع الجديدة (Greenfield Engine)")
    st.caption(f"المرجع: {pt['emirate']} | حالة جهد التربة: {pt['sbc_status']}")

    # لوحة المدخلات الأساسية
    ci1, ci2, ci3, ci4 = st.columns(4)
    with ci1:
        pt["plot_w"] = st.number_input("واجهة القسيمة (م):", 12.0, 250.0, float(pt["plot_w"]), 0.5, key="gf_pw_inp")
    with ci2:
        pt["plot_l"] = st.number_input("عمق القسيمة (م):", 14.0, 350.0, float(pt["plot_l"]), 0.5, key="gf_pl_inp")
    with ci3:
        new_sbc = st.number_input("جهد التربة الصافي SBC (kN/m²):", 60.0, 500.0, float(pt["sbc"]), 10.0, key="gf_sbc_inp")
        if new_sbc != pt["sbc"]:
            pt["sbc"] = new_sbc
            pt["sbc_status"] = "محدث بناءً على تقرير معتمد (Verified)"
            pt["rev_id"] = "Rev.01"
            st.toast("تم تحديث الحسابات وتوليد مراجعة جديدة للمشروع.")
    with ci4:
        pt["bua"] = st.number_input("مسطح البناء الإجمالي BUA (م²):", 100.0, 15000.0, float(pt["bua"]), 25.0, key="gf_bua_inp")

    # الحسابات الهندسية الأساسية
    p_area = round(pt["plot_w"] * pt["plot_l"], 2)
    net_w = max(0.0, pt["plot_w"] - (2 * sb_s))
    net_l = max(0.0, pt["plot_l"] - (sb_f + sb_r))
    eff_ground = min(round(net_w * net_l, 2), round(p_area * max_cov, 2))
    bld_l = min(net_l, eff_ground / net_w if net_w > 0 else net_l)

    tabs_gf = st.tabs([
        "📐 1. المسقط المعماري التنفيذي (CAD)",
        "🏗️ 2. المخطط الإنشائي والمحاور",
        "🔩 3. قطاع وحصر الهيكل المعدني",
        "📊 4. كراسة الكميات المسعرة (CSI)",
        "⏱️ 5. برنامج بريمافيرا (P6)",
        "💼 6. العرض التنفيذي لـ NotebookLM"
    ])

    # 1. المسقط المعماري التنفيذي
    with tabs_gf[0]:
        st.subheader("المسقط المعماري التنفيذي - الطابق الأرضي (Double-Line CAD Plan)")
        fig_cad, ax_c = plt.subplots(figsize=(14, 18), dpi=220)
        ax_c.set_facecolor('#FFFFFF')

        # الحدود والارتدادات
        ax_c.add_patch(Rectangle((0, 0), pt["plot_w"], pt["plot_l"], fill=False, edgecolor='#0F172A', lw=2.0))
        ax_c.add_patch(Rectangle((sb_s, sb_r), net_w, net_l, fill=False, edgecolor='#DC2626', lw=1.2, linestyle='--'))

        ext_th, int_th = 0.25, 0.20
        corr_w = 2.20
        corr_x = sb_s + (net_w * 0.46) - (corr_w / 2)

        def render_wall(x, y, w, h):
            ax_c.add_patch(Rectangle((x, y), w, h, facecolor='#334155', edgecolor='#0F172A', lw=0.8, zorder=2))

        # جدران المحيط الخارجي المزدوجة
        render_wall(sb_s, sb_r, net_w, ext_th)
        render_wall(sb_s, sb_r + bld_l - ext_th, net_w, ext_th)
        render_wall(sb_s, sb_r, ext_th, bld_l)
        render_wall(sb_s + net_w - ext_th, sb_r, ext_th, bld_l)

        # مناسيب القواطع الداخلية
        y_din = sb_r + bld_l * 0.32
        y_maj = sb_r + bld_l * 0.62
        y_gst = sb_r + bld_l * 0.40

        # جدران الممر والعصب الحركي
        render_wall(corr_x, sb_r, int_th, bld_l * 0.75)
        render_wall(corr_x + corr_w - int_th, sb_r, int_th, bld_l * 0.75)

        # قواطع الضيافة والعائلة
        render_wall(sb_s + ext_th, y_din, corr_x - (sb_s + ext_th), int_th)
        render_wall(sb_s + ext_th, y_maj, corr_x - (sb_s + ext_th), int_th)
        render_wall(corr_x + corr_w, y_gst, (sb_s + net_w - ext_th) - (corr_x + corr_w), int_th)

        # تفريغ فتحات الأبواب المعمارية
        def cut_door(x, y, width, swing="UP_RIGHT"):
            ax_c.add_patch(Rectangle((x - 0.02, y - 0.02), width + 0.04, int_th + 0.04, facecolor='#FFFFFF', edgecolor='none', zorder=3))
            ax_c.plot([x, x], [y - 0.02, y + int_th + 0.02], color='#000000', lw=1.2, zorder=4)
            ax_c.plot([x + width, x + width], [y - 0.02, y + int_th + 0.02], color='#000000', lw=1.2, zorder=4)
            if swing == "UP_RIGHT":
                ax_c.plot([x, x], [y + int_th, y + int_th + width], color='#78350F', lw=1.8, zorder=4)
                ax_c.add_patch(Arc((x, y + int_th), width*2, width*2, angle=0, theta1=0, theta2=90, color='#B45309', lw=1.0, linestyle='--', zorder=4))
            elif swing == "DOWN_LEFT":
                ax_c.plot([x + width, x + width], [y, y - width], color='#78350F', lw=1.8, zorder=4)
                ax_c.add_patch(Arc((x + width, y), width*2, width*2, angle=0, theta1=180, theta2=270, color='#B45309', lw=1.0, linestyle='--', zorder=4))
            elif swing == "MAIN_DOUBLE":
                lf = width / 2
                ax_c.plot([x, x], [y - lf, y], color='#78350F', lw=2.0, zorder=4)
                ax_c.plot([x + width, x + width], [y - lf, y], color='#78350F', lw=2.0, zorder=4)
                ax_c.add_patch(Arc((x, y), lf*2, lf*2, angle=0, theta1=270, theta2=360, color='#B45309', lw=1.0, linestyle='--', zorder=4))
                ax_c.add_patch(Arc((x + width, y), lf*2, lf*2, angle=0, theta1=180, theta2=270, color='#B45309', lw=1.0, linestyle='--', zorder=4))

        cut_door(corr_x, y_maj + 0.40, 1.10, "UP_RIGHT")
        cut_door(corr_x, y_din + 0.40, 1.00, "UP_RIGHT")
        cut_door(corr_x + corr_w - int_th, y_gst + 0.40, 1.00, "DOWN_LEFT")
        cut_door(corr_x + (corr_w/2) - 0.80, sb_r + bld_l - ext_th, 1.60, "MAIN_DOUBLE")

        # بيت الدرج المحسوب (22 درجة، بسطة 1.20م، سهم صعود)
        st_x, st_y = corr_x + int_th, sb_r + bld_l * 0.35
        st_w, land_d, st_len = corr_w - (2 * int_th), 1.20, 3.80
        fl_w = (st_w - 0.15) / 2

        ax_c.add_patch(Rectangle((st_x, st_y), st_w, st_len, fill=False, edgecolor='#1E293B', lw=1.2, zorder=3))
        ax_c.add_patch(Rectangle((st_x, st_y + st_len - land_d), st_w, land_d, facecolor='#E2E8F0', edgecolor='#475569', lw=0.8, zorder=3))
        ax_c.text(st_x + st_w/2, st_y + st_len - land_d/2, "بسطة استراحة\nLanding 1.20m", ha='center', va='center', fontsize=6.5, weight='bold', zorder=4)

        for ytr in np.linspace(st_y, st_y + st_len - land_d, 11):
            ax_c.plot([st_x, st_x + fl_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)
            ax_c.plot([st_x + fl_w + 0.15, st_x + st_w], [ytr, ytr], color='#334155', lw=0.9, zorder=3)

        ax_c.annotate('', xy=(st_x + fl_w/2, st_y + st_len - land_d - 0.2), xytext=(st_x + fl_w/2, st_y + 0.3),
                      arrowprops=dict(arrowstyle="->", color='#1E3A8A', lw=1.5), zorder=4)
        ax_c.text(st_x + fl_w/2, st_y + 0.15, "صعود UP", ha='center', fontsize=6.5, weight='bold', color='#1E3A8A')

        # الأعمدة المدفونة بالجدران (20x60 سم)
        cols_embedded = [
            (sb_s, sb_r), (corr_x, sb_r), (corr_x + corr_w - int_th, sb_r), (sb_s + net_w - 0.60, sb_r),
            (sb_s, y_din), (corr_x, y_din), (corr_x + corr_w - int_th, y_gst), (sb_s + net_w - 0.60, y_gst),
            (sb_s, y_maj), (corr_x, y_maj), (corr_x + corr_w - int_th, y_maj), (sb_s + net_w - 0.60, y_maj),
            (sb_s, sb_r + bld_l - 0.60), (corr_x, sb_r + bld_l - 0.60), (corr_x + corr_w - int_th, sb_r + bld_l - 0.60), (sb_s + net_w - 0.60, sb_r + bld_l - 0.60)
        ]
        for cx, cy in cols_embedded:
            ax_c.add_patch(Rectangle((cx, cy), 0.20, 0.60, facecolor='#000000', edgecolor='none', zorder=5))

        # شبكة المحاور وخطوط الأبعاد الثلاثية المعيارية
        gxs = [sb_s + 0.10, corr_x + 0.10, corr_x + corr_w - 0.10, sb_s + net_w - 0.10]
        gys = [sb_r + 0.10, y_din + 0.10, y_maj + 0.10, sb_r + bld_l - 0.10]
        xlbls, ylbls = ["1", "2", "3", "4"], ["A", "B", "C", "D"]

        for idx, gx in enumerate(gxs):
            ax_c.plot([gx, gx], [sb_r - 2.8, sb_r + bld_l + 2.8], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(gx, sb_r + bld_l + 3.4, xlbls[idx], ha='center', va='center', fontsize=8, weight='bold',
                      bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626', lw=1.0))

        for idx, gy in enumerate(gys):
            ax_c.plot([sb_s - 2.8, sb_s + net_w + 2.8], [gy, gy], color='#DC2626', linestyle='-.', lw=0.8, zorder=1)
            ax_c.text(sb_s - 3.4, gy, ylbls[idx], ha='center', va='center', fontsize=8, weight='bold',
                      bbox=dict(boxstyle='circle', facecolor='#FEE2E2', edgecolor='#DC2626', lw=1.0))

        # أبعاد المحاور الإنشائية (Tier 2) والبعد الكلي (Tier 3)
        dy2 = sb_r + bld_l + 1.6
        dy3 = sb_r + bld_l + 2.4
        for i in range(len(gxs) - 1):
            ax_c.annotate('', xy=(gxs[i], dy2), xytext=(gxs[i+1], dy2), arrowprops=dict(arrowstyle='<->', color='#0F172A', lw=1.0))
            ax_c.text((gxs[i] + gxs[i+1])/2, dy2 + 0.20, f"{gxs[i+1] - gxs[i]:.2f} m", ha='center', fontsize=7, weight='bold')

        ax_c.annotate('', xy=(gxs[0], dy3), xytext=(gxs[-1], dy3), arrowprops=dict(arrowstyle='<->', color='#1E3A8A', lw=1.2))
        ax_c.text((gxs[0] + gxs[-1])/2, dy3 + 0.25, f"Total = {gxs[-1] - gxs[0]:.2f} m", ha='center', fontsize=8, weight='bold', color='#1E3A8A')

        # المسميات والمناسيب
        room_tags = [
            ("مجلس رجال رسمي\nFormal Majlis\nFFL +0.45", sb_s + (corr_x - sb_s)/2, y_maj + (sb_r + bld_l - y_maj)/2),
            ("صالة طعام رسمية\nDining Hall\nFFL +0.45", sb_s + (corr_x - sb_s)/2, y_din + (y_maj - y_din)/2),
            ("مطبخ رئيسي وتحضيري\nKitchen Suite\nFFL +0.45", sb_s + (corr_x - sb_s)/2, sb_r + (y_din - sb_r)/2),
            ("صالة معيشة عائلية بانورامية\nFamily Living Hall\nFFL +0.45", (corr_x + corr_w) + (sb_s + net_w - (corr_x + corr_w))/2, y_gst + (sb_r + bld_l - y_gst)/2),
            ("جناح نوم كبار السن / ضيوف\nGuest Bedroom Suite\nFFL +0.45", (corr_x + corr_w) + (sb_s + net_w - (corr_x + corr_w))/2, sb_r + (y_gst - sb_r)/2),
            ("بهو وممر التوزيع الرئيسي\nMain Circulation Spine (W=2.20m)", corr_x + corr_w/2, sb_r + bld_l * 0.18)
        ]
        for t, lx, ly in room_tags:
            ax_c.text(lx, ly, t, ha='center', va='center', fontsize=7.5, weight='bold', color='#0F172A',
                      bbox=dict(boxstyle='round,pad=0.25', facecolor='#F8FAFC', edgecolor='#CBD5E1', lw=0.6), zorder=6)

        ax_c.set_xlim(-4, pt["plot_w"] + 5)
        ax_c.set_ylim(-4, pt["plot_l"] + 5)
        ax_c.set_aspect('equal')
        ax_c.axis('off')
        st.pyplot(fig_cad)

    # 2. المخطط الإنشائي
    with tabs_gf[1]:
        st.subheader("مخطط القواعد والميدات والمحاور الإنشائية (Foundation & Framing)")
        f_area = (1350.0 / 1.45) / pt["sbc"]
        f_dim = np.sqrt(f_area)
        f_thk = max(0.50, round(f_dim * 0.25, 2))

        fig_s, ax_s = plt.subplots(figsize=(10, 12), dpi=180)
        ax_s.set_facecolor('#FFFFFF')
        for gx in gxs:
            ax_s.plot([gx, gx], [sb_r - 2, sb_r + bld_l + 2], color='#DC2626', linestyle='-.', lw=1.0)
            ax_s.plot([gx, gx], [sb_r, sb_r + bld_l], color='#475569', lw=3.0)
        for gy in gys:
            ax_s.plot([sb_s - 2, sb_s + net_w + 2], [gy, gy], color='#DC2626', linestyle='-.', lw=1.0)
            ax_s.plot([sb_s, sb_s + net_w], [gy, gy], color='#475569', lw=3.0)

        for gx in gxs:
            for gy in gys:
                ax_s.add_patch(Rectangle((gx - f_dim/2, gy - f_dim/2), f_dim, f_dim, facecolor='#E2E8F0', edgecolor='#1E293B', lw=1.2))
                ax_s.add_patch(Rectangle((gx - 0.10, gy - 0.30), 0.20, 0.60, facecolor='#0F172A'))

        ax_s.set_xlim(sb_s - 4, sb_s + net_w + 4)
        ax_s.set_ylim(sb_r - 4, sb_r + bld_l + 4)
        ax_s.set_aspect('equal')
        ax_s.axis('off')
        st.pyplot(fig_s)
        st.success(f"القاعدة F1: أبعاد {f_dim:.2f} × {f_dim:.2f} × {f_thk:.2f} م | التسليح: 7 T 16mm/m باتجاهين بخرسانة كبريتية SRC C40 طبقاً لإجهاد التربة {pt['sbc']} kN/m².")

    # 3. الهيكل المعدني
    with tabs_gf[2]:
        st.subheader("قطاع الإطار الفولاذي وحصر الأطوال والأوزان (Steel Portal Frame)")
        st_span = st.number_input("بحر الهيكل الإنشائي Span (م):", 10.0, 60.0, float(pt["steel_span"]), key="gf_span_inp")
        st_len = st.number_input("طول المستودع الإجمالي (م):", 12.0, 200.0, float(pt["steel_len"]), key="gf_len_inp")
        eave_h, pitch_deg = 7.5, 10.0
        ridge_h = eave_h + (st_span / 2) * np.tan(np.radians(pitch_deg))

        fig_st, ax_st = plt.subplots(figsize=(10, 4.5), dpi=180)
        ax_st.plot([0, 0], [0, eave_h], color='#1E3A8A', lw=5.0)
        ax_st.plot([st_span, st_span], [0, eave_h], color='#1E3A8A', lw=5.0)
        ax_st.plot([0, st_span/2], [eave_h, ridge_h], color='#0284C7', lw=4.0)
        ax_st.plot([st_span, st_span/2], [eave_h, ridge_h], color='#0284C7', lw=4.0)
        ax_st.set_xlim(-3, st_span + 3); ax_st.set_ylim(-1, ridge_h + 2); ax_st.axis('off')
        st.pyplot(fig_st)

        frames_n = int(st_len / 6.0) + 1
        col_w = (frames_n * 2 * eave_h * 73.0) / 1000.0
        raf_w = (frames_n * 2 * (st_span/2/np.cos(np.radians(pitch_deg))) * 51.0) / 1000.0
        tot_steel = col_w + raf_w
        st.info(f"إجمالي وزن الهيكل: **{tot_steel:.2f} طن** | مساحة دهان الحريق (مقاومة ساعتين): **{tot_steel * 24.5:.1f} م²**")

    # 4. كراسة الكميات المسعرة
    with tabs_gf[3]:
        st.subheader("كراسة الكميات التعاقدية (CSI MasterFormat Live BOQ)")
        tier_sel = st.selectbox("المواصفة ومستوى التشطيب:", ["1. تجاري معتمد (قروض الإسكان)", "2. ديلوكس عصري حديث", "3. سوبر ديلوكس فندقي", "4. ألترا لوكجري VIP"], key="gf_tier_inp")
        mult = 1.0 if "تجاري" in tier_sel else (1.35 if "ديلوكس" in tier_sel else (1.75 if "سوبر" in tier_sel else 2.40))

        boq_data = [
            {"الكود": "01.00", "البند": "الأعمال التحضيرية وتجهيز الموقع واختبارات فحص التربة", "الوحدة": "مقطوع", "الكمية": 1, "السعر (AED)": 48500.0},
            {"الكود": "02.00", "البند": "الحفر لزوم التأسيس وردم الدفان على طبقات", "الوحدة": "م³", "الكمية": round(pt["bua"] * 1.6, 1), "السعر (AED)": 12.0},
            {"الكود": "03.10", "البند": "خرسانة مسلحة كبريتية SRC C40 للقواعد والميدات", "الوحدة": "م³", "الكمية": round(pt["bua"] * 0.28, 1), "السعر (AED)": 1200.0},
            {"الكود": "03.20", "البند": "خرسانة مسلحة بورتلاندية OPC للأعمدة والأسقف والسلالم", "الوحدة": "م³", "الكمية": round(pt["bua"] * 0.38, 1), "السعر (AED)": 1250.0},
            {"الكود": "04.00", "البند": "طابوق إسمنتي عازل 20 سم ومفرغ للقواطع الداخلية", "الوحدة": "م²", "الكمية": round(pt["bua"] * 2.2, 1), "السعر (AED)": 110.0},
            {"الكود": "05.00", "البند": "نظام عزل الأسطح حرارياً ومائياً (كومبو فوم 7 سم مع الضمان)", "الوحدة": "م²", "الكمية": round(pt["bua"] * 0.45, 1), "السعر (AED)": 125.0},
            {"الكود": "06.00", "البند": "التشطيبات، الرخام، والدرج، والدهانات الداخلية", "الوحدة": "م²", "الكمية": round(pt["bua"] * 1.2, 1), "السعر (AED)": round(140.0 * mult, 1)},
            {"الكود": "07.00", "البند": "الواجهات الزجاجية المزدوجة والألمنيوم واللوفرز", "الوحدة": "م²", "الكمية": round(pt["bua"] * 0.22, 1), "السعر (AED)": round(750.0 * mult, 1)},
            {"الكود": "08.00", "البند": "الأعمال الكهروميكانيكية والتكييف المخفي Inverter والصحي", "الوحدة": "م²", "الكمية": round(pt["bua"], 1), "السعر (AED)": round(320.0 * mult, 1)}
        ]
        df_boq = pd.DataFrame(boq_data)
        df_boq["الإجمالي (AED)"] = round(df_boq["الكمية"] * df_boq["السعر (AED)"])
        tot_cost = df_boq["الإجمالي (AED)"].sum()

        m_b1, m_b2, m_b3 = st.columns(3)
        m_b1.metric("إجمالي تكلفة المشروع التقديرية", f"{tot_cost:,.0f} درهم")
        m_b2.metric("سعر المتر المربع (BUA)", f"{tot_cost / pt['bua']:,.1f} AED / m²")
        m_b3.metric("سعر القدم المربع", f"{(tot_cost / pt['bua'])/10.764:,.1f} AED / sq.ft")
        st.dataframe(df_boq, use_container_width=True)

    # 5. بريمافيرا P6
    with tabs_gf[4]:
        st.subheader("الجدول الزمني التنفيذي والمسار الحرج (Primavera P6 Engine)")
        s_date = st.date_input("تاريخ استلام الموقع وبدء المشروع:", datetime.date.today(), key="gf_p6_sdate_inp")
        p6_tasks = [
            {"ID": "ACT-1010", "WBS": "1.PRE-CON", "Name": "التراخيص البلدية وفحص التربة وشهادات NOC", "Dur": 28, "Crit": "CRITICAL"},
            {"ID": "ACT-1020", "WBS": "2.SUB-STR", "Name": "أعمال الحفر والإحلال وسند الجوانب والقواعد المسلحة SRC", "Dur": 42, "Crit": "CRITICAL"},
            {"ID": "ACT-1030", "WBS": "3.SUP-STR", "Name": "أعمدة وأسقف الهيكل الخرساني الكامل (G+1+Roof)", "Dur": 70, "Crit": "CRITICAL"},
            {"ID": "ACT-1040", "WBS": "4.ENCLOSE", "Name": "المباني الطابوقية ونظام عزل الأسطح كومبو والواجهات", "Dur": 45, "Crit": "CRITICAL"},
            {"ID": "ACT-1050", "WBS": "5.FINISH", "Name": "أعمال التشطيبات الداخلية والكهروميكانيك وإطلاق التيار", "Dur": 60, "Crit": "CRITICAL"}
        ]
        c_date = pd.to_datetime(s_date)
        rows_p6 = []
        for tk in p6_tasks:
            e_date = c_date + pd.Timedelta(days=tk["Dur"])
            rows_p6.append({"Activity ID": tk["ID"], "WBS": tk["WBS"], "المرحلة": tk["Name"], "البداية": c_date.strftime('%Y-%m-%d'), "النهاية": e_date.strftime('%Y-%m-%d'), "المدة (يوم)": tk["Dur"], "المسار الحرج": tk["Crit"]})
            c_date = e_date - pd.Timedelta(days=7)
        st.dataframe(pd.DataFrame(rows_p6), use_container_width=True)

    # 6. العرض التنفيذي لـ NotebookLM
    with tabs_gf[5]:
        st.subheader("العرض الاستشاري التفاعلي وسيناريو NotebookLM Audio")
        brief_script = f"""
تقرير مشروع فيلا سكنية فاخرة (G + 1 + Roof) - كود {pt['emirate']}
بيانات القسيمة: الواجهة {pt['plot_w']:.1f}م × العمق {pt['plot_l']:.1f}م | المساحة الإجمالية: {p_area:.0f} م².
المحددات المعمارية: عصب حركي وسطي 2.20م، جدران مزدوجة عازلة، ودرج تنفيذي 22 درجة بقلبتين وبسطة 1.20م.
السلامة الإنشائية: جهد التربة {pt['sbc']} kN/m² ({pt['sbc_status']}) | قواعد منفصلة F1 مسلحة بخرسانة C40 SRC.
الميزانية والمدة: التكلفة التقديرية {tot_cost:,.0f} درهم بمدة تنفيذ 12 شهراً وفق المسار الحرج المعتمد.
مرجع المشروع: {pt['rev_id']}
        """
        st.text_area("نص الإحاطة الهندسية:", brief_script.strip(), height=180, key="gf_brief_text")
        st.download_button("📥 تحميل نص السرد لـ NotebookLM (TXT)", brief_script.strip().encode('utf-8'), "NotebookLM_Briefing.txt", "text/plain", key="btn_dl_brief")

# ==============================================================================
# المسار 2: تدقيق واستئناف المشاريع قيد التنفيذ (Site Recovery)
# ==============================================================================
else:
    st.title("🚩 منظومة تقييم واستئناف المشاريع قيد التنفيذ (Site Recovery & Audit)")
    st.caption(f"تدقيق المشاريع المتوقفة والمتعثرة | كود: {pt['emirate']} | حصر الأعمال المتبقية والبرنامج الزمني التعويضي.")

    tabs_rec = st.tabs([
        "📸 1. رفع المستندات والصور الميدانية (مفتوح)",
        "🏗️ 2. تدقيق الخرسانات المسلحة",
        "🔩 3. تدقيق الهياكل المعدنية",
        "📄 4. التقرير الاستشاري لاستئناف الترخيص"
    ])

    # 1. الرفع غير المحدود
    with tabs_rec[0]:
        st.subheader("مركز استقبال الوثائق وصور الموقع (Unlimited Ingestion)")
        c_u1, c_u2 = st.columns(2)
        with c_u1:
            rec_docs = st.file_uploader("رفع المخطط المعتمد والـ BOQ التعاقدي (PDF, Excel, DXF):", type=["pdf", "xlsx", "xls", "csv", "dxf"], accept_multiple_files=True, key="rec_docs_inp")
            if rec_docs:
                st.success(f"تم تحميل {len(rec_docs)} ملفات تعاقدية.")
        with c_u2:
            pt["drive_link"] = st.text_input("رابط مجلد Google Drive للصور والوثائق الميدانية:", value=pt["drive_link"], placeholder="https://drive.google.com/drive/folders/...", key="rec_drive_inp")

        st.markdown("---")
        st.markdown("#### 📷 معرض الفحص الميداني للصور الموقعية (Unlimited Photo Defect Logger)")
        rec_imgs = st.file_uploader("اسحب وأفلت جميع صور الموقع الميدانية (عدد غير محدود):", type=["jpg", "png", "jpeg", "webp"], accept_multiple_files=True, key="rec_imgs_inp")

        if rec_imgs:
            st.info(f"تم استقبال {len(rec_imgs)} صورة للموقع. قم بتوصيف العناصر بالأسفل:")
            img_grid = st.columns(3)
            inspection_results = []
            
            for idx, img_f in enumerate(rec_imgs):
                col_tgt = img_grid[idx % 3]
                with col_tgt:
                    im_view = Image.open(img_f)
                    st.image(im_view, caption=f"صورة #{idx+1}: {img_f.name}", use_container_width=True)
                    with st.expander(f"تدقيق الصورة #{idx+1}", expanded=False):
                        el_t = st.selectbox("العنصر المرصود:", ["قواعد وميدات مسلحة", "أعمدة خرسانية", "سقف خرساني", "هيكل فولاذي (أعمدة/جملون)", "مدادات Z-Purlins", "طابوق وعوازل"], key=f"r_elem_{idx}")
                        el_s = st.select_slider("نسبة الإنجاز الفعلي:", ["0%", "25%", "50%", "75%", "100%"], value="50%", key=f"r_stat_{idx}")
                        el_d = st.selectbox("العيوب الفنية المرصودة:", ["سليم ومطابق", "صدأ أشاير يتطلب سفع رملي وتطبيق برايمر", "تعشيش خرساني يتطلب حقن إيبوكسي", "توقف أعمال وتأثر بالرطوبة", "عدم اكتمال دهان الحريق"], key=f"r_def_{idx}")
                        el_c = st.number_input("تكلفة المعالجة والإكمال التقديرية (AED):", 0.0, 500000.0, 4500.0, 500.0, key=f"r_cst_{idx}")
                        
                        inspection_results.append({
                            "رقم": idx+1, "الملف": img_f.name, "العنصر": el_t,
                            "الإنجاز": el_s, "العيوب": el_d, "تكلفة المعالجة (AED)": el_c
                        })

            st.markdown("---")
            df_rec_insp = pd.DataFrame(inspection_results)
            st.dataframe(df_rec_insp, use_container_width=True)
            tot_rect = df_rec_insp["تكلفة المعالجة (AED)"].sum()
            st.metric("إجمالي تكلفة المعالجة واستكمال الأعمال المرصودة بالصور", f"{tot_rect:,.0f} درهم إماراتي")

    # 2. تدقيق الخرسانات
    with tabs_rec[1]:
        st.subheader("حصر كميات الخرسانات المسلحة المتبقية (RC Audit)")
        c_rc1, c_rc2 = st.columns(2)
        with c_rc1:
            tot_rc = st.number_input("إجمالي خرسانة المشروع بالمخطط المعتمد (م³):", 50.0, 15000.0, 420.0, key="rec_rc_tot_inp")
            exec_rc = st.number_input("الخرسانة المصبوبة المطابقة بالموقع (م³):", 0.0, float(tot_rc), 180.0, key="rec_rc_exec_inp")
        with c_rc2:
            rebar_st = st.selectbox("حالة حديد الأشاير والتعرض الجوي:", ["سليم - محمي بطلاء إسمنتي", "صدأ سطحي يتطلب سفع رملي وتطبيق برايمر", "تآكل متقدم يتطلب فحص كربنة واختبارات Core Test"], key="rec_rebar_st_inp")
            wp_st = st.selectbox("حالة العزل المائي للقواعد والرقاب:", ["سليم ومحمي بألواح حماية", "متضرر نتيجة الردم يتطلب إعادة عزل", "غير منفذ نهائياً"], key="rec_wp_st_inp")

        rem_rc = tot_rc - exec_rc
        st.metric("الخرسانة المسلحة المتبقية للإنجاز", f"{rem_rc:.1f} م³", delta=f"{((rem_rc/tot_rc)*100):.1f}% غير منجز", delta_color="inverse")

    # 3. تدقيق الهياكل المعدنية
    with tabs_rec[2]:
        st.subheader("حصر أطوال وكتل الهيكل الفولاذي المتبقية (Steel Audit)")
        c_st1, c_st2, c_st3 = st.columns(3)
        with c_st1:
            span_r = st.number_input("بحر الهيكل Span (م):", 10.0, 60.0, 24.0, key="rec_span_inp")
        with c_st2:
            frames_r = st.number_input("عدد الإطارات الإنشائية (Frames):", 2, 50, 8, key="rec_frames_inp")
        with c_st3:
            prog_r = st.slider("نسبة تركيب وتثبيت الهيكل بالموقع (%):", 0, 100, 30, key="rec_prog_inp")

        col_tot = frames_r * 2 * 7.5
        raf_tot = frames_r * 2 * (span_r / 2 / np.cos(np.radians(10)))
        gross_t = ((col_tot * 73.0) + (raf_tot * 51.0) + (frames_r * 6.0 * 12 * 5.2)) / 1000.0
        rem_t = gross_t * (1.0 - (prog_r / 100.0))

        st.info(f"إجمالي وزن الهيكل: **{gross_t:.2f} طن** | المتبقي للتصنيع والتركيب: **{rem_t:.2f} طن** | مساحة دهان الحريق المطلوبة: **{col_tot * 1.15:.1f} م²**")

    # 4. التقرير الاستشاري لاستئناف الأعمال
    with tabs_rec[3]:
        st.subheader("إصدار التقرير الاستشاري المعتمد لاستئناف الترخيص")
        recovery_report = f"""
تقرير استشاري فني لمعاينة وتدقيق استئناف أعمال المشروع الميداني
المرجع التنظيمي: بلدية {pt['emirate']}
تاريخ المعاينة: {datetime.date.today().strftime('%d/%m/%Y')}

1. نتائج التدقيق الخرساني:
- إجمالي حجم الخرسانة المعتمدة: {tot_rc:.1f} م³
- المنفذ فعلياً بالموقع: {exec_rc:.1f} م³ (نسبة الإنجاز: {(exec_rc/tot_rc)*100:.1f}%)
- الأعمال الخرسانية المتبقية: {rem_rc:.1f} م³
- حالة حديد التسليح والأشاير: {rebar_st}

2. نتائج تدقيق الهياكل الفولاذية (Steel Structures):
- وزن الهيكل الإجمالي: {gross_t:.2f} طن | المتبقي: {rem_t:.2f} طن
- مساحة دهان الحماية الإنتوميسنت المطلوبة: {col_tot * 1.15:.1f} م² (مقاومة ساعتين)

3. التوصيات الفنية والخطوات التنفيذية:
- استخراج شهادة سلامة إنشائية واختبارات Core Test للأعمدة المصبوبة القائمة.
- اعتماد كراسة الكميات المتبقية وتعيين مقاول استكمال معتمد لدى البلدية.
        """
        st.text_area("مسودة التقرير الفني المعتمد:", recovery_report.strip(), height=260, key="rec_rep_txt")
        st.download_button("📥 تحميل التقرير الاستشاري الرسمي (TXT)", recovery_report.strip().encode('utf-8'), "Site_Recovery_Report.txt", "text/plain", key="btn_dl_rec_rep")
