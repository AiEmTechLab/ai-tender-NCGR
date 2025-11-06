# modules/analyzer.py
import os, json, hashlib, re
import streamlit as st
from groq import Groq
import fitz
import pytesseract
from PIL import Image

# ============================================================
# ☁️ إعداد Groq (سحابي فقط)
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8", "ignore")).hexdigest()

# ============================================================
# 🧠 دوال مساعدة
# ============================================================
def _safe_json_loads(s: str):
    """يحاول استخراج JSON حتى لو أضاف النموذج نصوصاً زائدة."""
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"(\[.*\])", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
    return None


def clean_text(text):
    """تنظيف النص من الرموز الغريبة والفراغات."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\-\(\)\/%]', '', text)
    return text.strip()


def extract_text_with_ocr(pdf_bytes, show_progress=True):
    """
    🧠 استخراج نص دقيق من PDF:
    - يستخدم النص الأصلي إن وُجد
    - يفعّل OCR عند الحاجة
    - يعرض شريط تقدم في Streamlit
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    total = len(doc)
    ocr_count = 0

    progress_bar = st.progress(0)
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        used_ocr = False

        if len(text) < 40:  # إذا الصفحة فقيرة نصيًا → استخدم OCR
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang="ara+eng")
            used_ocr = True
            ocr_count += 1

        text = clean_text(text)
        pages.append({"page_num": i + 1, "text": text, "ocr_used": used_ocr})

        # تحديث شريط التقدم
        progress_bar.progress((i + 1) / total)

    if show_progress:
        percent_ocr = (ocr_count / total) * 100
        if ocr_count > 0:
            st.warning(f"🟨 تم استخدام OCR في {ocr_count} صفحة ({percent_ocr:.1f}%).")
        else:
            st.success("🟩 تم استخراج جميع الصفحات نصيًا بدون الحاجة إلى OCR.")

    return {"type": "pdf", "pages": pages}


# ============================================================
# 🧠 استدعاء Groq (مع دعم اختيار النموذج)
# ============================================================
def _llm_json_only(prompt: str, model=None) -> str:
    """استدعاء Groq وإرجاع الاستجابة كنص فقط (يتوقع JSON)."""
    if not client:
        raise RuntimeError("⚠️ GROQ_API_KEY غير مضبوط.")

    selected_model = model or "llama-3.3-70b-versatile"
    resp = client.chat.completions.create(
        model=selected_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_tokens=4000
    )
    return resp.choices[0].message.content.strip()


# ============================================================
# 📄 تحليل الأقسام بدقة مع رقم الصفحة الحقيقي
# ============================================================
def analyze_sections_with_pages(doc_payload: dict):
    st.info("🤖 جارٍ تحليل المستند بدقة مع الحفاظ على النصوص الكاملة...")

    if doc_payload.get("type") == "pdf":
        parts = [f"[[PAGE:{p['page_num']}]]\n{p['text']}" for p in doc_payload["pages"]]
        full_text = "\n\n".join(parts)
        chunks = [full_text[i:i+18000] for i in range(0, len(full_text), 18000)]
        all_sections = []

        for idx, chunk in enumerate(chunks):
            st.caption(f"📄 تحليل الجزء {idx+1}/{len(chunks)}...")
            prompt = f"""
اقرأ النص أدناه من عرض فني يحتوي على علامات صفحات بالشكل [[PAGE:n]].
قسّمه إلى أقسام رئيسية مثل:
المقدمة، الأهداف، المنهجية، خطة التنفيذ، الفريق، النتائج، الخاتمة.

لكل قسم أعد JSON بهذا الشكل فقط:
[
  {{
    "section": "اسم القسم بالعربية",
    "start_page": رقم الصفحة,
    "summary": "ملخص قصير وواضح",
    "content": "النص الكامل للقسم"
  }}
]

⚠️ لا تضف أي نص خارج JSON.
النص:
{chunk}
"""
            try:
                reply = _llm_json_only(prompt)
                data = _safe_json_loads(reply)
                if data:
                    all_sections.extend(data)
            except Exception as e:
                st.error(f"❌ خطأ أثناء تحليل الجزء {idx+1}: {e}")

        merged = {}
        for sec in all_sections:
            name = sec.get("section", "").strip()
            if not name:
                continue
            if name in merged:
                merged[name]["content"] += "\n" + sec.get("content", "")
                merged[name]["summary"] = merged[name]["summary"] or sec.get("summary", "")
                merged[name]["start_page"] = min(merged[name]["start_page"], sec.get("start_page", 1))
            else:
                merged[name] = sec

        out = sorted(merged.values(), key=lambda x: x["start_page"])
        return out

    elif doc_payload.get("type") == "docx":
        text = doc_payload["text"]
        prompt = f"""
قسّم النص التالي إلى أقسام واضحة مثل المقدمة، الأهداف، المنهجية، خطة التنفيذ، الفريق، النتائج، الخاتمة.
لكل قسم:
- "section": الاسم بالعربية
- "summary": ملخص بسيط دون تحريف
- "start_page": دائماً 1
- "content": النص الكامل كما هو.

أعد النتيجة بصيغة JSON فقط.
النص:
{text[:20000]}
"""
        reply = _llm_json_only(prompt)
        data = _safe_json_loads(reply)
        return data or []


# ============================================================
# 💡 اقتراح معايير إضافية بالذكاء الصناعي
# ============================================================
def suggest_criteria_from_offers(offers_texts, base_criteria, lang="ar"):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("❌ لم يتم ضبط مفتاح GROQ_API_KEY في ملف .env")
        return []

    client = Groq(api_key=api_key)
    joined = "\n\n---\n\n".join(offers_texts)[:12000]
    seed = ", ".join(base_criteria[:15])

    system = (
        "أنت خبير تقييم مناقصات. اقترح معايير تقييم إضافية مختصرة وواضحة "
        "تتناسب مع محتوى العروض المقدمة. أعد النتيجة بصيغة JSON فقط "
        "على شكل قائمة نصوص عربية مثل: "
        '["جودة العرض", "منهجية التنفيذ", "إدارة المخاطر", ...]'
    )

    user = (
        f"المعايير الحالية:\n{seed}\n\n"
        f"مقتطفات من العروض:\n{joined}\n\n"
        "اقترح حتى 10 معايير جديدة بالعربية، بدون تكرار أو شرح."
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.25,
            max_tokens=600,
        )
        txt = resp.choices[0].message.content.strip()

        # 🧩 إصلاح ناتج النص لو رجع كـ string بدلاً من list
        if txt.startswith("[") and txt.endswith("]"):
            try:
                fixed = json.loads(txt)
                if isinstance(fixed, list):
                    return [s.strip() for s in fixed if s.strip()]
            except:
                pass
        if txt.startswith('"[') or txt.startswith("'["):
            txt = txt.strip('"').strip("'")
            try:
                fixed = json.loads(txt)
                if isinstance(fixed, list):
                    return [s.strip() for s in fixed if s.strip()]
            except:
                pass

        # fallback manual parsing
        lines = [l.strip("•- ").strip() for l in txt.splitlines() if l.strip()]
        return [l for l in lines if l]
    except Exception as e:
        st.error(f"⚠️ خطأ أثناء اقتراح المعايير: {e}")
        return []


# ============================================================
# 🧠 تحسين وتلخيص الفقرات (عرض منسق داخل Streamlit)
# ============================================================
def summarize_paragraphs_llm(section_text, model="llama-3.3-70b-versatile"):
    if not section_text.strip():
        return {"clean_text": "", "summaries": []}

    prompt = f"""
قسم النص التالي إلى فقرات قصيرة ومفهومة، ولكل فقرة اكتب ملخصًا بالعربية الفصحى يشرح فكرتها الأساسية بإيجاز.
أعد النتيجة بصيغة JSON فقط كالتالي:
[
  {{"paragraph": "النص الأصلي للفقره", "summary_ar": "ملخص بالعربية"}}
]
النص:
{section_text[:15000]}
"""

    summaries = []
    try:
        raw = _llm_json_only(prompt, model=model)
        data = _safe_json_loads(raw)
        if isinstance(data, list):
            summaries = data
        else:
            st.warning("⚠️ لم يتمكن الذكاء الصناعي من إرجاع تنسيق JSON صحيح.")
            summaries = [{"paragraph": section_text, "summary_ar": raw.strip()}]
    except Exception as e:
        st.error(f"⚠️ خطأ أثناء تلخيص الفقرات: {e}")
        summaries = [{"paragraph": section_text, "summary_ar": "لم يتم توليد ملخص بسبب خطأ تقني."}]

    clean_text_out = re.sub(r"\s+", " ", section_text).strip()

    # 🎨 عرض منسق
    st.markdown("### ✨ الملخص الذكي ")
    for idx, item in enumerate(summaries, start=1):
        st.markdown(
            f"""
            <div style='background:#f8f6ff;border-right:5px solid #5A33A4;
                        padding:14px;border-radius:12px;margin-top:10px;'>
                <b>🔹 الفقرة {idx}:</b><br>
                <span style='color:#333;'>{item['paragraph']}</span>
                <hr style='border:none;border-top:1px dashed #ccc;margin:6px 0;'>
                <b>💡 الملخص:</b> <span style='color:#5A33A4;'>{item['summary_ar']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    return {"clean_text": clean_text_out, "summaries": summaries}
