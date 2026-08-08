"""
Database models for NutriBot SaaS.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)   # nullable for Google users
    plan          = db.Column(db.String(20), default="free")   # free | pro | family
    is_admin      = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Email verification ────────────────────────────────────────
    email_verified  = db.Column(db.Boolean, default=False)
    otp_code        = db.Column(db.String(6))
    otp_expires     = db.Column(db.DateTime)

    # ── Google OAuth ──────────────────────────────────────────────
    google_id       = db.Column(db.String(200), unique=True, nullable=True)
    avatar_url      = db.Column(db.String(500), nullable=True)

    # ── Password reset ────────────────────────────────────────────
    reset_token     = db.Column(db.String(200), nullable=True)
    reset_expires   = db.Column(db.DateTime, nullable=True)

    # ── Stripe Subscription ──────────────────────────────────────
    stripe_customer_id     = db.Column(db.String(120), nullable=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True)
    subscription_status    = db.Column(db.String(30), default="inactive")
    subscription_end_date  = db.Column(db.DateTime, nullable=True)

    # usage counters (reset monthly — simple approach)
    chats_this_month     = db.Column(db.Integer, default=0)
    plans_this_month     = db.Column(db.Integer, default=0)
    usage_reset_month    = db.Column(db.Integer, default=0)   # stores month number

    # relationships
    profile      = db.relationship("Profile",     backref="user", uselist=False, cascade="all, delete-orphan")
    chat_history = db.relationship("ChatHistory", backref="user", cascade="all, delete-orphan", order_by="ChatHistory.timestamp")
    meal_plans   = db.relationship("MealPlan",    backref="user", cascade="all, delete-orphan", order_by="MealPlan.created_at.desc()")
    bmi_records  = db.relationship("BMIRecord",   backref="user", cascade="all, delete-orphan", order_by="BMIRecord.created_at.desc()")
    daily_logs   = db.relationship("DailyLog",    backref="user", cascade="all, delete-orphan", order_by="DailyLog.created_at.desc()")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ── Plan limits ──────────────────────────────────────────────
    LIMITS = {
        "free":   {"chats": 20,  "plans": 3},
        "pro":    {"chats": 500, "plans": 50},
        "family": {"chats": 999, "plans": 100},
    }

    def _reset_if_new_month(self):
        current_month = datetime.utcnow().month
        if self.usage_reset_month != current_month:
            self.chats_this_month  = 0
            self.plans_this_month  = 0
            self.usage_reset_month = current_month
            db.session.commit()

    def can_chat(self):
        self._reset_if_new_month()
        return self.chats_this_month < self.LIMITS[self.plan]["chats"]

    def can_generate_plan(self):
        self._reset_if_new_month()
        return self.plans_this_month < self.LIMITS[self.plan]["plans"]

    def increment_chat(self):
        self._reset_if_new_month()
        self.chats_this_month += 1
        db.session.commit()

    def increment_plan(self):
        self._reset_if_new_month()
        self.plans_this_month += 1
        db.session.commit()

    def usage_summary(self):
        self._reset_if_new_month()
        limits = self.LIMITS[self.plan]
        return {
            "chats_used":  self.chats_this_month,
            "chats_limit": limits["chats"],
            "plans_used":  self.plans_this_month,
            "plans_limit": limits["plans"],
            "plan":        self.plan,
        }

    def __repr__(self):
        return f"<User {self.email}>"


class Profile(db.Model):
    __tablename__ = "profiles"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    age        = db.Column(db.Integer)
    gender     = db.Column(db.String(20))
    weight_kg  = db.Column(db.Float)
    height_cm  = db.Column(db.Float)
    goal       = db.Column(db.String(60))
    diet       = db.Column(db.String(60))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistory(db.Model):
    __tablename__ = "chat_history"

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role      = db.Column(db.String(20), nullable=False)   # "user" | "assistant"
    content   = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class MealPlan(db.Model):
    __tablename__ = "meal_plans"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_text  = db.Column(db.Text, nullable=False)
    parameters = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BMIRecord(db.Model):
    __tablename__ = "bmi_records"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    bmi        = db.Column(db.Float)
    weight_kg  = db.Column(db.Float)
    height_cm  = db.Column(db.Float)
    category   = db.Column(db.String(30))
    advice     = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class UserMemory(db.Model):
    __tablename__ = "user_memories"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    category = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship("User", backref="memories")


class DailyLog(db.Model):
    __tablename__ = "daily_logs"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date       = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    meal_type  = db.Column(db.String(30), nullable=False) # breakfast, lunch, dinner, snack
    meal_name  = db.Column(db.String(200), nullable=False)
    calories   = db.Column(db.Integer, default=0)
    protein_g  = db.Column(db.Float, default=0.0)
    carbs_g    = db.Column(db.Float, default=0.0)
    fat_g      = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)