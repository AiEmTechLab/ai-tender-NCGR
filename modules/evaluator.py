# modules/evaluator.py
import streamlit as st
import pandas as pd
import json, re, os
from groq import Groq
from dotenv import load_dotenv
from langdetect import detect
from deep_translator import GoogleTranslator
from modules.extractors import extract_text_with_pages

# تحميل مفتاح Groq من .env
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ===========================================================
# 🔤 ترجمة المعايير عند الحاجة
# ===========================================================
def translate_if_needed(criteria_list, text):
    """إذا كان النص إنجليزيًا تُترجم المعايير تلقائيًا"""
    try:
        sample = text[:1000]
        lang = detect(sample)
        if lang == "en":
            st.info("🔤 تم اكتشاف أن العرض باللغة الإنجليزية، يجري ترجمة المعايير...")
            translated = [
                GoogleTranslator(source="ar", target="en").translate(c)
                for c in criteria_list
            ]
            return translated, "en"
    except Exception:
        pass
    return criteria_list, "ar"


# ===========================================================
# 🧠 التقييم الذكي للعروض
# ===========================================================
@st.cache_data(show_spinner=False)
def evaluate_offers(offers, criteria_list):
    results, details = [], {}

    for f in offers:
        with st.spinner(f"🔍 تحليل العرض: {f.name}"):
            # استخراج النصوص
            data = extract_text_with_pages(f)
            if isinstance(data, dict):
                if data.get("type") == "pdf":
                    text = "\n".join(p["text"] for p in data.get("pages", []))
                elif data.get("type") == "docx":
                    text = data.get("text", "")
                else:
                    text = ""
            else:
                text = str(data)

            if not text.strip():
                st.warning(f"⚠️ لا يوجد نص يمكن تحليله في الملف: {f.name}")
                continue

            # ترجمة المعايير إذا لزم
            criteria_list, lang_detected = translate_if_needed(criteria_list, text)
            text_criteria = "\n".join([f"- {c}" for c in criteria_list])

            # ===== التوجيه للنموذج =====
            prompt = f"""
أنت خبير تقييم عروض تقنية. اقرأ النص التالي ثم قيّم العرض بناءً على المعايير المحددة.

لكل معيار:
- ضع درجة من 1 إلى 4 (1=ضعيف، 4=ممتاز)
- اكتب السؤال الذي طرحته لتقييمه (ai_question)
- اكتب السبب المنطقي (reason)

أعد النتيجة بصيغة JSON فقط بهذا الشكل:
{{
  "scores": [
    {{"criterion":"...","score":3,"ai_question":"...","reason":"..."}}
  ],
  "overall_comment": "ملاحظات عامة عن العرض"
}}

المعايير:
{text_criteria}

النص:
{text[:18000]}
"""

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=3500,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.choices[0].message.content.strip()

                # محاولة استخراج JSON
                json_match = re.search(r"\{.*\}", result_text, re.S)
                if not json_match:
                    st.warning(f"⚠️ لم يُرجع النموذج JSON صالح للملف: {f.name}")
                    continue

                data_json = json.loads(json_match.group(0))
                scores = data_json.get("scores", [])
                comment = data_json.get("overall_comment", "— لا توجد ملاحظات عامة —")

                df = pd.DataFrame(scores)
                for col in ["criterion", "score", "reason", "ai_question"]:
                    if col not in df.columns:
                        df[col] = ""

                # تنظيف الرموز الغريبة (مثل الصينية)
                for c in ["reason", "ai_question"]:
                    df[c] = df[c].astype(str).apply(lambda x: re.sub(r"[^\u0600-\u06FFa-zA-Z0-9\s.,()%-]", "", x))

                # حساب المتوسط
                df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
                overall = df["score"].mean() / 4

                results.append({
                    "file": f.name,
                    "overall": overall,
                    "comment": comment
                })
                details[f.name] = df

            except Exception as e:
                st.error(f"❌ خطأ أثناء تحليل {f.name}: {e}")
                # حتى لو فشل عرض واحد، نحفظ صف افتراضي
                results.append({
                    "file": f.name,
                    "overall": 0.0,
                    "comment": f"خطأ أثناء التحليل: {e}"
                })
                details[f.name] = pd.DataFrame()

    # تحويل النتائج إلى DataFrame
    if results:
        ranked = pd.DataFrame(results)
        if "overall" not in ranked.columns:
            ranked["overall"] = 0.0
        ranked = ranked.sort_values("overall", ascending=False).reset_index(drop=True)
        return ranked, details
    else:
        st.warning("⚠️ لم يتم تحليل أي عروض.")
        return pd.DataFrame(columns=["file", "overall", "comment"]), {}
