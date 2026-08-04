"""
╔══════════════════════════════════════════════════════════════════╗
║        NutritionAgent — IBM Watsonx.ai (Granite) Core           ║
╚══════════════════════════════════════════════════════════════════╝

Edit the  AGENT_INSTRUCTIONS  block below to customise:
  • Tone and personality
  • Diet specialisation (vegan, keto, Indian, diabetic…)
  • Safety & medical disclaimers
  • Preferred foods / cuisines
  • Response length / format
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
You are NutriBot, an expert AI nutritionist and wellness coach powered by IBM Watsonx.ai.

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
    """Wraps IBM Watsonx.ai (Granite) for nutrition-focused conversations."""

    # Default model — granite-13b-chat-v2 is optimised for dialogue
    model_id: str = "ibm/granite-13b-chat-v2"

    # Generation parameters — tune as needed
    GENERATE_PARAMS = {
        "decoding_method": "greedy",
        "max_new_tokens": 1024,
        "min_new_tokens": 50,
        "stop_sequences": ["<|endoftext|>"],
        "repetition_penalty": 1.1,
        "temperature": 0.7,
    }

    def __init__(self):
        self.api_key = os.getenv("IBM_API_KEY")
        self.project_id = os.getenv("IBM_PROJECT_ID")
        self.watsonx_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

        if not self.api_key or not self.project_id:
            raise EnvironmentError(
                "IBM_API_KEY and IBM_PROJECT_ID must be set in the .env file."
            )

        self._model = None
        logger.info("NutritionAgent initialised (model: %s)", self.model_id)

    # ──────────────────────────────────────────────────────────────
    # Lazy model initialisation
    # ──────────────────────────────────────────────────────────────
    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

            credentials = Credentials(
                url=self.watsonx_url,
                api_key=self.api_key,
            )

            self._model = ModelInference(
                model_id=self.model_id,
                credentials=credentials,
                project_id=self.project_id,
                params=self.GENERATE_PARAMS,
            )
            logger.info("Watsonx ModelInference ready.")
        except ImportError:
            logger.warning("ibm-watsonx-ai not installed — using mock responses.")
            self._model = "mock"
        except Exception as exc:
            logger.error("Failed to init Watsonx model: %s", exc)
            self._model = "mock"

        return self._model

    # ──────────────────────────────────────────────────────────────
    # Core generation
    # ──────────────────────────────────────────────────────────────
    def _generate(self, prompt: str) -> str:
        model = self._get_model()

        if model == "mock":
            return self._mock_response(prompt)

        try:
            response = model.generate_text(prompt=prompt)
            return response.strip()
        except Exception as exc:
            logger.error("Generation error: %s", exc)
            return self._mock_response(prompt)

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────
    def chat(self, user_message: str, history: list, context: dict = None) -> str:
        """Multi-turn conversation handler."""
        history_text = self._format_history(history[-10:])  # last 5 turns
        context_text = self._format_context(context or {})

        full_prompt = (
            f"{AGENT_INSTRUCTIONS}\n\n"
            f"{'### User Context\\n' + context_text + chr(10) if context_text else ''}"
            f"{'### Conversation History\\n' + history_text + chr(10) if history_text else ''}"
            f"### User: {user_message}\n"
            f"### NutriBot:"
        )

        return self._generate(full_prompt)

    def analyze(self, prompt: str) -> str:
        """Single-turn nutritional analysis."""
        full_prompt = (
            f"{AGENT_INSTRUCTIONS}\n\n"
            f"### Task: {prompt}\n"
            f"### NutriBot:"
        )
        return self._generate(full_prompt)

    def generate_plan(self, prompt: str) -> str:
        """Generate a structured meal / nutrition plan."""
        full_prompt = (
            f"{AGENT_INSTRUCTIONS}\n\n"
            f"### Generate a detailed plan for: {prompt}\n"
            f"### NutriBot (provide a well-structured plan with headings):"
        )
        return self._generate(full_prompt)

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
        parts = []
        for key, val in context.items():
            parts.append(f"  {key}: {val}")
        return "\n".join(parts)

    @staticmethod
    def _mock_response(prompt: str) -> str:
        """Fallback when Watsonx is unavailable (dev/demo mode)."""
        lp = prompt.lower()
        if "meal plan" in lp or "generate a detailed plan" in lp:
            return (
                "**7-Day Indian Meal Plan (Demo — connect IBM Watsonx for real plans)**\n\n"
                "**Day 1**\n"
                "- 🌅 Breakfast: Oats upma with vegetables (320 kcal)\n"
                "- ☀️ Lunch: Dal tadka + 2 rotis + cucumber raita (480 kcal)\n"
                "- 🌙 Dinner: Palak paneer + brown rice + salad (520 kcal)\n"
                "- 🍎 Snacks: Handful of almonds + 1 banana (210 kcal)\n\n"
                "**Total: ~1530 kcal** ✅\n\n"
                "⚠️ This is a demo response. Connect your IBM Watsonx API key for personalised plans."
            )
        if "bmi" in lp:
            return (
                "**BMI Analysis (Demo)**\n\n"
                "Based on your metrics, here are key recommendations:\n"
                "- ✅ Include protein at every meal (dal, paneer, eggs, legumes)\n"
                "- ✅ Aim for 5 servings of vegetables and 2 fruits daily\n"
                "- ✅ Stay hydrated: 8–10 glasses of water\n"
                "- ✅ Limit processed foods, refined sugar, and fried snacks\n\n"
                "⚠️ Consult a registered dietitian before making significant dietary changes."
            )
        return (
            "**NutriBot (Demo Mode)**\n\n"
            "Hello! I'm NutriBot, your AI nutrition assistant powered by IBM Watsonx.ai. 🥗\n\n"
            "I can help you with:\n"
            "- ✅ Personalised meal plans (Indian & international)\n"
            "- ✅ Calorie and nutrition analysis\n"
            "- ✅ BMI calculation and weight management tips\n"
            "- ✅ Family diet planning\n"
            "- ✅ Healthy recipe suggestions\n\n"
            "Ask me anything about nutrition!\n\n"
            "⚠️ Currently in demo mode. Connect IBM Watsonx API key for full AI responses."
        )
