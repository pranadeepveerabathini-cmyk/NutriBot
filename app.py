"""
╔══════════════════════════════════════════════════════════════════╗
║          AI-Powered Nutrition Agent — Flask Backend              ║
║          Powered by IBM Watsonx.ai (Granite Models)              ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv

from agent import NutritionAgent

# ─────────────────────────────────────────────────────────────────
# Boot
# ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
CORS(app)

# Initialise the agent once at startup
nutrition_agent = NutritionAgent()


# ─────────────────────────────────────────────────────────────────
# Routes — Pages
# ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Main application page."""
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────
# Routes — Chat API
# ─────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    POST  { "message": str, "context": {...} }
    Returns { "response": str, "timestamp": str }
    """
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    context = data.get("context", {})

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Persist conversation history in server-side session
    if "conversation_history" not in session:
        session["conversation_history"] = []

    history = session["conversation_history"]

    try:
        response = nutrition_agent.chat(user_message, history, context)
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": response})
        # Keep last 20 turns to avoid bloat
        session["conversation_history"] = history[-40:]
        return jsonify({"response": response, "timestamp": datetime.now().isoformat()})
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        return jsonify({"error": "Agent error. Please try again.", "details": str(exc)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear the current conversation history."""
    session.pop("conversation_history", None)
    return jsonify({"status": "cleared"})


# ─────────────────────────────────────────────────────────────────
# Routes — Nutrition Analysis
# ─────────────────────────────────────────────────────────────────
@app.route("/api/nutrition/analyze", methods=["POST"])
def analyze_nutrition():
    """
    POST  { "meal": str, "servings": int }
    Returns detailed calorie + macro breakdown.
    """
    data = request.get_json(silent=True) or {}
    meal = data.get("meal", "")
    servings = data.get("servings", 1)

    if not meal:
        return jsonify({"error": "Meal description required"}), 400

    prompt = f"Analyze the nutritional content of: {meal} ({servings} serving(s)). Provide calories, protein, carbohydrates, fat, fiber, vitamins, and minerals in a structured format."
    try:
        result = nutrition_agent.analyze(prompt)
        return jsonify({"analysis": result, "meal": meal, "servings": servings})
    except Exception as exc:
        logger.error("Nutrition analysis error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────
# Routes — Meal Plan Generation
# ─────────────────────────────────────────────────────────────────
@app.route("/api/mealplan/generate", methods=["POST"])
def generate_meal_plan():
    """
    POST  {
        "calories": int, "dietary_preference": str,
        "duration": int, "health_goal": str,
        "allergies": [str], "cuisine": str
    }
    Returns a full weekly meal plan.
    """
    data = request.get_json(silent=True) or {}
    calories = data.get("calories", 2000)
    dietary_pref = data.get("dietary_preference", "balanced")
    duration = data.get("duration", 7)
    health_goal = data.get("health_goal", "maintain weight")
    allergies = data.get("allergies", [])
    cuisine = data.get("cuisine", "Indian")

    allergy_text = f", avoiding: {', '.join(allergies)}" if allergies else ""

    prompt = (
        f"Create a detailed {duration}-day meal plan for a {dietary_pref} diet "
        f"targeting {calories} kcal/day. Health goal: {health_goal}. "
        f"Preferred cuisine: {cuisine}{allergy_text}. "
        f"Include breakfast, lunch, dinner, and snacks for each day with approximate calories."
    )
    try:
        plan = nutrition_agent.generate_plan(prompt)
        return jsonify({"meal_plan": plan, "parameters": data})
    except Exception as exc:
        logger.error("Meal plan error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────
# Routes — BMI Calculator
# ─────────────────────────────────────────────────────────────────
@app.route("/api/bmi/calculate", methods=["POST"])
def calculate_bmi():
    """
    POST  { "weight_kg": float, "height_cm": float, "age": int, "gender": str }
    Returns BMI, category, and personalised advice.
    """
    data = request.get_json(silent=True) or {}
    try:
        weight = float(data["weight_kg"])
        height_m = float(data["height_cm"]) / 100
        age = int(data.get("age", 30))
        gender = data.get("gender", "unspecified")
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400

    bmi = round(weight / (height_m ** 2), 1)
    category = _bmi_category(bmi)

    prompt = (
        f"A {age}-year-old {gender} has a BMI of {bmi} ({category}). "
        f"Weight: {weight} kg, Height: {height_m*100:.0f} cm. "
        f"Provide personalised nutrition advice, ideal weight range, and dietary recommendations."
    )
    try:
        advice = nutrition_agent.analyze(prompt)
        return jsonify({
            "bmi": bmi,
            "category": category,
            "advice": advice,
            "ideal_weight_range": _ideal_weight(height_m),
        })
    except Exception as exc:
        logger.error("BMI error: %s", exc)
        return jsonify({"error": str(exc)}), 500


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal weight"
    if bmi < 30.0:
        return "Overweight"
    return "Obese"


def _ideal_weight(height_m: float) -> dict:
    return {
        "min_kg": round(18.5 * height_m ** 2, 1),
        "max_kg": round(24.9 * height_m ** 2, 1),
    }


# ─────────────────────────────────────────────────────────────────
# Routes — Family Profile
# ─────────────────────────────────────────────────────────────────
@app.route("/api/family/plan", methods=["POST"])
def family_plan():
    """
    POST  { "members": [{ "name", "age", "gender", "health_conditions", "dietary_preference" }] }
    Returns a unified family diet plan.
    """
    data = request.get_json(silent=True) or {}
    members = data.get("members", [])

    if not members:
        return jsonify({"error": "At least one family member required"}), 400

    member_summary = "; ".join(
        f"{m.get('name','Member')} (age {m.get('age','?')}, {m.get('gender','?')}, "
        f"conditions: {m.get('health_conditions','none')}, diet: {m.get('dietary_preference','balanced')})"
        for m in members
    )

    prompt = (
        f"Create a comprehensive family nutrition plan for: {member_summary}. "
        f"Consider each member's needs, suggest common meals the whole family can enjoy, "
        f"and highlight individual modifications where needed. Include Indian-inspired recipes."
    )
    try:
        plan = nutrition_agent.generate_plan(prompt)
        return jsonify({"family_plan": plan, "members": members})
    except Exception as exc:
        logger.error("Family plan error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────
# Routes — Health Info (static quick lookups)
# ─────────────────────────────────────────────────────────────────
@app.route("/api/health/tips", methods=["GET"])
def health_tips():
    """Return daily nutrition tips using the agent."""
    prompt = "Give me 5 quick, actionable daily nutrition tips focused on Indian dietary habits and seasonal foods."
    try:
        tips = nutrition_agent.analyze(prompt)
        return jsonify({"tips": tips})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health/status", methods=["GET"])
def health_status():
    return jsonify({
        "status": "online",
        "agent": "IBM Watsonx Nutrition Agent",
        "model": nutrition_agent.model_id,
        "timestamp": datetime.now().isoformat(),
    })


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 5000))
    host = os.getenv("APP_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    logger.info("Nutrition Agent starting on http://%s:%s", host, port)
    app.run(host=host, port=port, debug=debug)
