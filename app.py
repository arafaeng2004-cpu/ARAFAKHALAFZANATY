import streamlit as st
import json
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="UAE Structural & Zoning Engine", layout="wide")

st.title("🏗️ المنظومة الهندسية الإنشائية لمشاريع الإمارات")
st.markdown("تحليل المخططات، حساب الارتدادات البلدية، وتوليد الفروض الإنشائية وحصر الكميات آلياً.")

# إدخال المفتاح في الشريط الجانبي
api_key = st.sidebar.text_input("أدخل Gemini API Key الخاص بك:", type="password")

city = st.sidebar.selectbox("اختر الإمارة / الجهة التنظيمية:", ["الشارقة", "أبوظبي / العين", "دبي", "إمارات أخرى"])
input_mode = st.radio("طريقة الإدخال:", ["إدخال أبعاد الأرض يدوياً", "رفع صورة أو كروكي الأرض"])

width, length, actual_sbc = 0.0, 0.0, 150.0

if input_mode == "إدخال أبعاد الأرض يدوياً":
    col1, col2, col3 = st.columns(3)
    with col1:
        width = st.number_input("عرض الأرض على الشارع (متر):", min_value=5.0, value=25.0)
    with col2:
        length = st.number_input("عمق الأرض (متر):", min_value=5.0, value=30.0)
    with col3:
        actual_sbc = st.number_input("جهد التربة SBC المسموح به (kN/m²):", min_value=50.0, value=150.0)

else:
    uploaded_file = st.file_uploader("ارفع صورة الكروكي / المخطط (JPG أو PNG):", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        if not api_key:
            st.warning("يرجى إدخال API Key في القائمة الجانبية لتفعيل القراءة الذكية.")
        else:
            if st.button("استخراج بيانات المخطط عبر الذكاء الاصطناعي"):
                client = genai.Client(api_key=api_key)
                image = Image.open(uploaded_file)
                st.image(image, caption="المخطط المرفوع", width=350)
                
                with st.spinner("جاري استخراج البيانات والمساحات..."):
                    prompt = "Extract plot data from this UAE krooki strictly in JSON with numeric keys: 'width', 'length', 'area'."
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    data = json.loads(response.text)
                    st.success("تم استخراج البيانات بنجاح!")
                    st.json(data)
                    width = float(data.get("width", 25.0))
                    length = float(data.get("length", 30.0))

# تشغيل التحليل وتوليد المخرجات
if st.button("🚀 توليد التقرير الهندسي والإنشائي الكامل"):
    area = width * length
    front_sb = 4.5 if "الشارقة" in city else 5.0
    rear_sb = 3.0
    side_sb = 1.5 if "الشارقة" in city else 2.0

    net_w = max(0.0, width - (2 * side_sb))
    net_l = max(0.0, length - (front_sb + rear_sb))
    buildable_envelope = round(net_w * net_l, 2)
    max_ground = round(area * 0.55, 2)
    footprint = min(buildable_envelope, max_ground)
    total_bua = round(footprint * 1.85, 2)

    est_concrete = round(total_bua * 0.65, 2)
    est_steel = round((est_concrete * 110) / 1000, 2)
    found_type = "قواعد منفصلة مع ميدات ربط قوية (Isolated Footings)" if actual_sbc >= 150 else "لبشة مسلحة كاملة (Raft Foundation)"

    st.subheader("📊 نتائج الفحص التنظيمي والمحددات")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("المساحة الكلية للأرض", f"{area:.1f} م²")
    c2.metric("أبعاد كتلة البناء الصافية", f"{net_w:.1f} × {net_l:.1f} م")
    c3.metric("مسطح الأرضي المسموح", f"{footprint:.1f} م²")
    c4.metric("إجمالي مسطح البناء المقدر (G+1)", f"{total_bua:.1f} م²")

    st.subheader("🏗️ الفروضات والحلول الإنشائية المبدئية")
    st.info(f"**نوع الأساسات المقترح:** {found_type} (بناءً على جهد تربة {actual_sbc} kN/m²)")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**مواصفات المواد الإنشائية:**")
        st.write("- الأساسات والميدات: خرسانة مقاومة للأملاح SRC (رتبة C40)")
        st.write("- الأعمدة والأسقف: خرسانة بورتلاندية عادية OPC (رتبة C35)")
        st.write("- حديد التسليح: إجهاد خضوع 500 MPa عالي المقاومة")
    with col_b:
        st.write("**حصر الكميات التقديري للمشروع (Preliminary BOQ):**")
        st.metric("حجم الخرسانة المسلحة التقديري", f"{est_concrete} م³")
        st.metric("وزن حديد التسليح التقديري", f"{est_steel} طن")
