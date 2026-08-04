"""
╔══════════════════════════════════════════════════════════════════╗
║          AI-Powered Nutrition Agent — Flask Backend              ║
║          NutriBot SaaS — Multi-user with auth & persistence      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv

from models import db, User, Profile, ChatHistory, MealPlan, BMIRecord
from agent import NutritionAgent
from auth import auth as auth_blueprint, oauth

# ─────────────────────────────────────────────────────────────────
# Boot
# ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
ADMIN_EMAIL    = "pranadeepveerabathini@gmail.com"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")

# ── Database ──────────────────────────────────────────────────────
database_url = os.getenv("DATABASE_URL", "sqlite:///nutribot.db")
# Railway PostgreSQL uses postgres:// — SQLAlchemy needs postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ── Flask-Login ───────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to use NutriBot."
login_manager.login_message_category = "info"
app.config["SECRET_KEY"] = app.secret_key

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── CORS + Blueprints ─────────────────────────────────────────────
CORS(app)
oauth.init_app(app)
app.register_blueprint(auth_blueprint)

# ── Create tables ─────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    logger.info("Database tables ready.")

# ── Agent ─────────────────────────────────────────────────────────
nutrition_agent = NutritionAgent()


# ─────────────────────────────────────────────────────────────────
# Routes — Pages
# ─────────────────────────────────────────────────────────────────
@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("landing.html")


@app.route("/app")
@login_required
def index():
    return render_template("index.html", user=current_user)


@app.route("/account")
@login_required
def account():
    profile     = current_user.profile
    meal_plans  = current_user.meal_plans[:10]
    bmi_records = current_user.bmi_records[:10]
    usage       = current_user.usage_summary()
    return render_template(
        "account.html",
        user=current_user,
        profile=profile,
        meal_plans=meal_plans,
        bmi_records=bmi_records,
        usage=usage,
    )


# ─────────────────────────────────────────────────────────────────
# Routes — Chat API
# ─────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    context      = data.get("context", {})

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Usage limit check
    if not current_user.can_chat():
        usage = current_user.usage_summary()
        return jsonify({
            "error": "limit_reached",
            "message": f"You've used all {usage['chats_limit']} chats this month on the {usage['plan']} plan. Upgrade for more!",
        }), 429

    # Load last 10 turns from DB for this user
    history_rows = (
        ChatHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(20)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(history_rows)]

    try:
        response = nutrition_agent.chat(user_message, history, context)

        # Persist both turns
        db.session.add(ChatHistory(user_id=current_user.id, role="user",      content=user_message))
        db.session.add(ChatHistory(user_id=current_user.id, role="assistant", content=response))
        db.session.commit()

        current_user.increment_chat()

        return jsonify({"response": response, "timestamp": datetime.now().isoformat()})
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        return jsonify({"error": "Agent error. Please try again.", "details": str(exc)}), 500


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def clear_chat():
    ChatHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"status": "cleared"})


@app.route("/api/chat/history", methods=["GET"])
@login_required
def chat_history():
    rows = (
        ChatHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(ChatHistory.timestamp.asc())
        .limit(100)
        .all()
    )
    return jsonify([{
        "role":      r.role,
        "content":   r.content,
        "timestamp": r.timestamp.isoformat(),
    } for r in rows])


# ─────────────────────────────────────────────────────────────────
# Routes — Nutrition Analysis
# ─────────────────────────────────────────────────────────────────
@app.route("/api/nutrition/analyze", methods=["POST"])
@login_required
def analyze_nutrition():
    data     = request.get_json(silent=True) or {}
    meal     = data.get("meal", "")
    servings = data.get("servings", 1)

    if not meal:
        return jsonify({"error": "Meal description required"}), 400

    prompt = (
        f"Analyze the nutritional content of: {meal} ({servings} serving(s)). "
        f"Provide calories, protein, carbohydrates, fat, fiber, vitamins, and minerals in a structured format."
    )
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
@login_required
def generate_meal_plan():
    data = request.get_json(silent=True) or {}

    if not current_user.can_generate_plan():
        usage = current_user.usage_summary()
        return jsonify({
            "error": "limit_reached",
            "message": f"You've used all {usage['plans_limit']} meal plans this month on the {usage['plan']} plan. Upgrade for more!",
        }), 429

    calories     = data.get("calories", 2000)
    dietary_pref = data.get("dietary_preference", "balanced")
    duration     = data.get("duration", 7)
    health_goal  = data.get("health_goal", "maintain weight")
    allergies    = data.get("allergies", [])
    cuisine      = data.get("cuisine", "Indian")
    allergy_text = f", avoiding: {', '.join(allergies)}" if allergies else ""

    prompt = (
        f"Create a detailed {duration}-day meal plan for a {dietary_pref} diet "
        f"targeting {calories} kcal/day. Health goal: {health_goal}. "
        f"Preferred cuisine: {cuisine}{allergy_text}. "
        f"Include breakfast, lunch, dinner, and snacks for each day with approximate calories."
    )
    try:
        plan = nutrition_agent.generate_plan(prompt)

        # Save to DB
        db.session.add(MealPlan(
            user_id=current_user.id,
            plan_text=plan,
            parameters=data,
        ))
        db.session.commit()
        current_user.increment_plan()

        return jsonify({"meal_plan": plan, "parameters": data})
    except Exception as exc:
        logger.error("Meal plan error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────
# Routes — BMI Calculator
# ─────────────────────────────────────────────────────────────────
@app.route("/api/bmi/calculate", methods=["POST"])
@login_required
def calculate_bmi():
    data = request.get_json(silent=True) or {}
    try:
        weight   = float(data["weight_kg"])
        height_m = float(data["height_cm"]) / 100
        age      = int(data.get("age", 30))
        gender   = data.get("gender", "unspecified")
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400

    bmi      = round(weight / (height_m ** 2), 1)
    category = _bmi_category(bmi)

    prompt = (
        f"A {age}-year-old {gender} has a BMI of {bmi} ({category}). "
        f"Weight: {weight} kg, Height: {height_m*100:.0f} cm. "
        f"Provide personalised nutrition advice, ideal weight range, and dietary recommendations."
    )
    try:
        advice = nutrition_agent.analyze(prompt)

        # Save record
        db.session.add(BMIRecord(
            user_id=current_user.id,
            bmi=bmi,
            weight_kg=weight,
            height_cm=height_m * 100,
            category=category,
            advice=advice,
        ))
        db.session.commit()

        return jsonify({
            "bmi":               bmi,
            "category":          category,
            "advice":            advice,
            "ideal_weight_range": _ideal_weight(height_m),
        })
    except Exception as exc:
        logger.error("BMI error: %s", exc)
        return jsonify({"error": str(exc)}), 500


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5: return "Underweight"
    if bmi < 25.0: return "Normal weight"
    if bmi < 30.0: return "Overweight"
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
@login_required
def family_plan():
    data    = request.get_json(silent=True) or {}
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
# Routes — Health Info
# ─────────────────────────────────────────────────────────────────
@app.route("/api/health/tips", methods=["GET"])
@login_required
def health_tips():
    prompt = "Give me 5 quick, actionable daily nutrition tips focused on Indian dietary habits and seasonal foods."
    try:
        tips = nutrition_agent.analyze(prompt)
        return jsonify({"tips": tips})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health/status", methods=["GET"])
def health_status():
    return jsonify({
        "status":    "online",
        "agent":     "NutriBot AI Nutrition Agent",
        "model":     nutrition_agent.model_id,
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/usage", methods=["GET"])
@login_required
def usage():
    return jsonify(current_user.usage_summary())
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.email != ADMIN_EMAIL:
        return "Not Found", 404

    users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin.html",
        users=users,
        admin=current_user
    )

# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("APP_PORT", 5000))
    host  = os.getenv("APP_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    logger.info("NutriBot SaaS starting on http://%s:%s", host, port)
    app.run(host=host, port=port, debug=debug)
