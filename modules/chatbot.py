# modules/chatbot.py
import os
import re
from groq import Groq

# =========================================================
# 🔑 إعداد مفتاح Groq
# =========================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("⚠️ لم يتم العثور على مفتاح GROQ_API_KEY في البيئة.")

client = Groq(api_key=GROQ_API_KEY)

# =========================================================
# 🧹 أدوات مساعدة للنظافة والتهيئة
# =========================================================
def clean_text_for_ai(text: str) -> str:
    """ينظّف النص من الرموز والأسطر المكررة والعلامات غير الضرورية"""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[_•▪️●■□]+", "", text)
    text = re.sub(r"([A-Za-z]{2,})", lambda m: m.group(1).strip() + " ", text)
    text = text.replace("\n", " ").strip()
    return text


def limit_text(text: str, limit: int = 15000) -> str:
    """يقتطع النص الطويل لتفادي حدود النموذج"""
    return text[:limit]


# =========================================================
# 💬 الكلاس الأساسي للشاتبوت
# =========================================================
class TenderChat:
    def __init__(self, offers_context: dict):
        """
        offers_context = {
            "offer_name.pdf": "نص العرض الكامل...",
            ...
        }
        """
        self.context = offers_context

    def _build_prompt(self, question: str) -> str:
        """ينشئ البرومبت الذكي"""
        context_text = ""
        for fname, text in self.context.items():
            context_text += f"\n\n### 📘 العرض: {fname}\n\n"
            context_text += clean_text_for_ai(limit_text(text))

        prompt = f"""
أنت مساعد ذكي مختص في تحليل العروض الفنية المكتوبة بالعربية.
استخدم النص أدناه للإجابة عن الأسئلة.
أجب بالعربية فقط، وبأسلوب مهني وواضح.

- إذا وُجدت أرقام صفحات داخل النص (مثل [صفحة 4]) فاذكرها في إجابتك.
- إذا كان النص بالإنجليزية، ترجمه للعربية أولاً.
- لا تضف معلومات غير موجودة.
- اجعل الإجابة موجزة ومركزة ومفهومة.

السؤال:
{question}

المحتوى المتاح:
{context_text}
"""
        return prompt

    def answer(self, question: str) -> str:
        """يرسل السؤال إلى نموذج Groq ويعيد الرد"""
        try:
            prompt = self._build_prompt(question)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ✅ أحدث نموذج مدعوم
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي يجيب بالعربية فقط."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.25,
                max_tokens=1500
            )

            answer = resp.choices[0].message.content.strip()

            # ✨ تنسيق الإجابة النهائية
            answer = re.sub(r"\n{2,}", "\n\n", answer)
            answer = answer.replace("###", "🔹").replace("**", "")
            answer = re.sub(r"(\[صفحة\s*\d+\])", r"📄 \1", answer)

            if not answer:
                answer = "لم أجد معلومات كافية للإجابة عن هذا السؤال داخل العرض."
            return answer

        except Exception as e:
            return f"⚠️ حدث خطأ أثناء تحليل السؤال: {e}"
