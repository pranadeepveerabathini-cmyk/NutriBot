"""
╔══════════════════════════════════════════════════════════════════╗
║        NutritionAgent — Multi-provider AI Core                   ║
║        Primary: Google Gemini                                    ║
║        Fallback: Groq (Llama)                                    ║
║        Last resort: Demo mode                                    ║
╚══════════════════════════════════════════════════════════════════╝

Edit AGENT_INSTRUCTIONS to customise NutriBot's behaviour.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
#  AGENT INSTRUCTIONS — Customise behaviour here
# ══════════════════════════════════════════════════════════════════
AGENT_INSTRUCTIONS = """
You are NutriBot, an expert AI nutritionist and wellness coach.

## PERSONA & TONE
- Warm, encouraging, and professional — like a trusted nutritionist friend.
- Use simple language; avoid heavy jargon unless the user asks for clinical detail.
- Be motivational: celebrate small wins, never shame food choices.
- Use bullet points and structured sections for clarity.

## SPECIALISATIONS
- Indian cuisine expertise: dal, roti, rice, sabzi, curries, millets, fermented foods (idli, dosa).
- Ayurvedic principles: seasonal eating, doshas, warming/cooling foods.
- Medical nutrition therapy: diabetes, hypertension, PCOS, thyroid, cholesterol management.
- Weight management: scientifically-backed calorie deficit / surplus strategies.
- Sports & fitness nutrition: pre/post workout meals, protein timing.
- Child & elderly nutrition: age-appropriate dietary guidance.
- Plant-based & vegan diets: complete protein combinations in Indian context.

## INDIAN FOOD PREFERENCES
- Prioritise ingredients available in Indian households: atta, dal lentils, paneer, curd, ghee,
  coconut, mustard oil, turmeric, cumin, coriander, curry leaves, amla, moringa.
- Suggest seasonal Indian fruits and vegetables.
- Provide both North Indian and South Indian meal options.
- Include traditional superfoods: sattu, ragi, jowar, bajra, rajgira.

## RESPONSE FORMAT
- Always structure responses with clear headings.
- Provide calorie estimates where relevant.
- Use ✅ for recommendations and ⚠️ for cautions.
- For meal plans: list Breakfast, Lunch, Dinner, Snacks with calories.
- Keep responses concise but complete (aim for 200–400 words unless a full plan is requested).

## SAFETY RULES (MUST FOLLOW)
- Always add: "⚠️ Consult a registered dietitian or doctor before making significant dietary changes."
- Never diagnose medical conditions — only provide general nutritional guidance.
- For users mentioning pregnancy, serious illness, or eating disorders — recommend professional help first.
- Do not recommend extreme calorie restriction below 1200 kcal/day for women, 1500 kcal/day for men.
- Do not promote any specific supplement brands.

## CAPABILITIES
- Personalised daily nutrition plans.
- Calorie and macro-nutrient analysis.
- BMI interpretation and ideal weight guidance.
- Family meal planning accommodating multiple dietary needs.
- Healthy Indian recipe suggestions with nutritional breakdowns.
- Grocery shopping list generation.
- Hydration and micronutrient advice.
- Intermittent fasting guidance.
- Festive / religious fasting meal ideas (Navratri, Ramadan, Ekadashi).
"""
# ══════════════════════════════════════════════════════════════════


class NutritionAgent:
    """
    Multi-provider AI agent.
    Primary  → Google Gemini (gemini-1.5-flash)
    Fallback → Groq (llama-3.1-70b-versatile)
    Demo     → Static responses when both are unavailable
    """

    model_id = "gemini-1.5-flash"  # displayed in /api/health/status

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key   = os.getenv("GROQ_API_KEY")

        self._gemini_client = None
        self._groq_client   = None

        if not self.gemini_key and not self.groq_key:
            logger.warning("No AI API keys found — running in demo mode.")
        else:
            if self.gemini_key:
                logger.info("NutritionAgent: Gemini primary ready.")
            if self.groq_key:
                logger.info("NutritionAgent: Groq fallback ready.")

    # ──────────────────────────────────────────────────────────────
    # Lazy clients
    # ──────────────────────────────────────────────────────────────
    def _get_gemini(self):
        if self._gemini_client is not None:
            return self._gemini_client
        if not self.gemini_key:
            return None
        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.gemini_key)
            logger.info("Gemini client initialised.")
            return self._gemini_client
        except Exception as e:
            logger.error("Gemini init failed: %s", e)
            return None

    def _get_groq(self):
        if self._groq_client is not None:
            return self._groq_client
        if not self.groq_key:
            return None
        try:
            from groq import Groq
            self._groq_client = Groq(api_key=self.groq_key)
            logger.info("Groq client initialised.")
            return self._groq_client
        except Exception as e:
            logger.error("Groq init failed: %s", e)
            return None

    # ──────────────────────────────────────────────────────────────
    # Core generation — Gemini → Groq → Demo
    # ──────────────────────────────────────────────────────────────
    def _generate(self, prompt: str) -> str:
        # 1️⃣ Try Gemini
        gemini = self._get_gemini()
        if gemini:
            try:
                response = gemini.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=AGENT_INSTRUCTIONS + "\n\n" + prompt,
                )
                return response.text.strip()
            except Exception as e:
                logger.warning("Gemini failed, trying Groq: %s", e)

        # 2️⃣ Try Groq
        groq = self._get_groq()
        if groq:
            try:
                completion = groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": AGENT_INSTRUCTIONS},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=1024,
                    temperature=0.7,
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("Groq failed, using demo: %s", e)

        # 3️⃣ Demo fallback
        return self._demo_response(prompt)

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────
    def chat(self, user_message: str, history: list, context: dict = None) -> str:
        context_text  = self._format_context(context or {})
        history_text  = self._format_history(history[-10:])

        prompt = (
            f"{'### User Context\n' + context_text + chr(10) if context_text else ''}"
            f"{'### Conversation History\n' + history_text + chr(10) if history_text else ''}"
            f"### User: {user_message}\n"
            f"### NutriBot:"
        )
        return self._generate(prompt)

    def analyze(self, prompt: str) -> str:
        return self._generate(f"### Task: {prompt}\n### NutriBot:")

    def analyze_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """
        Multimodal Food Scanner — Analyzes food photos using Gemini 1.5 Flash.
        """
        gemini = self._get_gemini()
        if gemini:
            try:
                from google.genai import types
                part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                prompt = (
                    "You are NutriBot Food Scanner. Analyze this food image in detail:\n"
                    "1. Identified food items & estimated portion sizes\n"
                    "2. Total estimated Calories (kcal)\n"
                    "3. Macro breakdown (Protein g, Carbs g, Fat g, Fiber g)\n"
                    "4. Health rating & actionable advice/modifications\n"
                    "Provide output with clean bold markdown sections and bullet points."
                )
                response = gemini.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[AGENT_INSTRUCTIONS + "\n\n" + prompt, part],
                )
                return response.text.strip()
            except Exception as e:
                logger.warning("Gemini Vision failed: %s", e)

        # Demo response fallback
        return (
            "### 📸 NutriBot Food Scanner (Analysis)\n\n"
            "**Identified Items:**\n"
            "- Paneer Butter Masala (1 bowl, ~200g)\n"
            "- Garlic Naan (2 pieces)\n"
            "- Cucumber & Onion Salad\n\n"
            "**Nutritional Breakdown:**\n"
            "- ⚡ **Calories:** ~720 kcal\n"
            "- 🥩 **Protein:** 24g\n"
            "- 🌾 **Carbohydrates:** 68g\n"
            "- 🥑 **Fat:** 38g\n"
            "- 🥗 **Fiber:** 6g\n\n"
            "**NutriBot Insights:**\n"
            "- ✅ Great source of protein from paneer.\n"
            "- ⚠️ High saturated fat from butter & cream. Consider opting for tandoori roti instead of garlic butter naan for a lower calorie deficit.\n\n"
            "⚠️ Add `GEMINI_API_KEY` to `.env` for real-time AI image scanning."
        )

    def generate_plan(self, prompt: str) -> str:
        return self._generate(
            f"### Generate a detailed plan for: {prompt}\n"
            f"### NutriBot (provide a well-structured plan with headings):"
        )

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _format_history(history: list) -> str:
        lines = []
        for turn in history:
            role = "User" if turn["role"] == "user" else "NutriBot"
            lines.append(f"{role}: {turn['content']}")
        return "\n".join(lines)

    @staticmethod
    def _format_context(context: dict) -> str:
        if not context:
            return ""
        return "\n".join(f"  {k}: {v}" for k, v in context.items() if v)

    @staticmethod
    def _demo_response(prompt: str) -> str:
        lp = prompt.lower()
        if "meal plan" in lp or "generate a detailed plan" in lp:
            return (
                "**7-Day Indian Meal Plan (Demo Mode)**\n\n"
                "**Day 1**\n"
                "- 🌅 Breakfast: Oats upma with vegetables (320 kcal)\n"
                "- ☀️ Lunch: Dal tadka + 2 rotis + cucumber raita (480 kcal)\n"
                "- 🌙 Dinner: Palak paneer + brown rice + salad (520 kcal)\n"
                "- 🍎 Snacks: Handful of almonds + 1 banana (210 kcal)\n\n"
                "**Total: ~1530 kcal** ✅\n\n"
                "⚠️ Demo mode — add GEMINI_API_KEY or GROQ_API_KEY to .env for real AI plans."
            )
        if "bmi" in lp:
            return (
                "**BMI Analysis (Demo)**\n\n"
                "- ✅ Include protein at every meal (dal, paneer, eggs, legumes)\n"
                "- ✅ Aim for 5 servings of vegetables and 2 fruits daily\n"
                "- ✅ Stay hydrated: 8–10 glasses of water\n\n"
                "⚠️ Consult a registered dietitian before making significant dietary changes."
            )
        return (
            "**NutriBot (Demo Mode)**\n\n"
            "I'm NutriBot, your AI nutrition assistant. 🥗\n\n"
            "I can help you with:\n"
            "- ✅ Personalised meal plans\n"
            "- ✅ Calorie and nutrition analysis\n"
            "- ✅ BMI calculation and weight management\n"
            "- ✅ Family diet planning\n\n"
            "⚠️ Add GEMINI_API_KEY or GROQ_API_KEY to .env for full AI responses."
        )
