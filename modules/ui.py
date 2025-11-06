import base64
import os
import streamlit as st

ACCENT = "#5A33A4"
ACCENT_SOFT = "#8B5CF6"

# ==========================================================
# 🌐 إعداد اللغة
# ==========================================================
def setup_language():
    """اللغة العربية فقط، مع دعم وسيطين لتوافق بقية الكود"""
    st.session_state.lang = "AR"

    def _(en=None, ar=None):
        if ar is not None:
            return ar
        return en if en is not None else ""

    return _


# ==========================================================
# 🎨 تطبيق التصميم العام
# ==========================================================
def apply_theme():
    """تطبيق الخط العربي DiodrumArabic + تنسيق RTL + تحسين الأزرار والخطوط"""
    st.markdown(f"""
    <style>

    /* 🚀 الزر الأساسي (ابدأ) */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #5A33A4 0%, #8B5CF6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        padding: 10px 17px !important;         /* ← جعلها مستطيلة */
        width: auto !important;
        height: auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        margin: 40px auto !important;         /* ← بالمنتصف */
        cursor: pointer !important;
        box-shadow: 0 4px 12px rgba(90, 51, 164, 0.25);
        transition: all 0.25s ease-in-out !important;
    }}

    button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #8B5CF6, #5A33A4) !important;
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(90, 51, 164, 0.35);
    }}

    /* ===== الخطوط ===== */
    @font-face {{
        font-family: 'DiodrumArabic';
        src: url('https://raw.githubusercontent.com/google/fonts/main/ofl/diodrumarabic/DiodrumArabic-Regular.ttf') format('truetype');
        font-weight: normal;
    }}
    @font-face {{
        font-family: 'DiodrumArabic';
        src: url('https://raw.githubusercontent.com/google/fonts/main/ofl/diodrumarabic/DiodrumArabic-Semibold.ttf') format('truetype');
        font-weight: 600;
    }}

    /* ===== النصوص العامة ===== */
    html, body, [class*="css"] {{
      font-family: 'DiodrumArabic', system-ui !important;
      direction: rtl;
      text-align: right;
      font-size: 20px !important;
      line-height: 1.8em !important;
      color: #222 !important;
    }}

    /* ===== العناوين ===== */
    h1, h2, h3, h4 {{
      color: {ACCENT} !important;
      letter-spacing: .2px;
      font-weight: 700;
      font-family: 'DiodrumArabic';
    }}
    h1 {{ font-size: 44px !important; }}
    h2 {{ font-size: 32px !important; }}
    h3 {{ font-size: 26px !important; }}
    h4 {{ font-size: 22px !important; }}

    </style>
    """, unsafe_allow_html=True)


# ==========================================================
# 🧩 رأس الصفحة + الشعاران
# ==========================================================
def render_header(_):
    """العنوان + شعاران في الجهة اليمنى السفلى"""
    logo_right_1 = os.path.join("assets", "NCGR33.png")
    logo_right_2 = os.path.join("assets", "DGA _Logo_Landscape-01.png")
    title_text = "مُقيّم العروض الذكي"

    imgs = []
    for logo_path in [logo_right_1, logo_right_2]:
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            imgs.append(
                f"<img src='data:image/png;base64,{logo_b64}' style='height:70px; margin-right:14px; opacity:0.95;'>"
            )

    logos_html = f"""
        <div style="
            position:fixed;
            bottom:18px;
            right:25px;
            z-index:9999;
            display:flex;
            align-items:center;
            gap:20px;">
            {''.join(imgs)}
        </div>
    """

    st.markdown(
        f"<h1 style='text-align:center; color:{ACCENT}; font-weight:800; margin-top:60px;'>{title_text}</h1>",
        unsafe_allow_html=True
    )
    st.markdown(logos_html, unsafe_allow_html=True)


# ==========================================================
# 🏠 الصفحة الترحيبية
# ==========================================================
def landing_hero(_):
    """الصفحة الترحيبية الرئيسية"""
    ACCENT = "#5A33A4"

    st.markdown(f"""
    <div style="text-align:center; padding: 70px 0 40px 0; font-family:'DiodrumArabic';">
        <h2 style="margin:0; color:{ACCENT}; font-weight:700; font-size:38px;">
            👋 مرحبًا بك في مُقيِّم العروض الذكي
        </h2>
        <p style="opacity:.85; margin-top:15px; font-size:20px;">
            💡 هذه الأداة تمكّنك من تحليل العروض الفنية بسهولة وسرعة باستخدام الذكاء الاصطناعي.
        </p>
        <div style="margin-top:45px;">
            <p style="color:#444; font-size:18px; line-height:1.9;">
                ابدأ برفع ملفات العروض الفنية بصيغة&nbsp;
                <b>PDF</b> &nbsp;أو&nbsp; <b>DOCX</b>،<br>
                ثم قم بتحديد معايير التقييم ليقوم النظام بالتحليل الآلي وإظهار النتائج.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
