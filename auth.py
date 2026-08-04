"""
Auth blueprint — register, login, logout, OTP verify,
forgot/reset password, Google OAuth.
"""

import os
import random
import string
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth

from models import db, User, Profile
from email_sender import send_otp_email, send_reset_email

auth    = Blueprint("auth", __name__)
oauth   = OAuth()

# ── Google OAuth setup ────────────────────────────────────────────
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ── Helpers ───────────────────────────────────────────────────────
def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))

def _create_profile(user_id: int):
    db.session.add(Profile(user_id=user_id))
    db.session.commit()


# ══════════════════════════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════════════════════════
@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        # Create unverified user
        otp     = _generate_otp()
        expires = datetime.utcnow() + timedelta(minutes=10)

        user = User(
            name=name, email=email,
            otp_code=otp, otp_expires=expires,
            email_verified=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        _create_profile(user.id)

        # Send OTP
        sent = send_otp_email(email, name, otp)
        if not sent:
            flash("Could not send verification email. Check your Resend API key.", "danger")
            db.session.rollback()
            return render_template("register.html")

        db.session.commit()

        # Store pending email in session for verify page
        session["pending_verify_email"] = email
        flash(f"A 6-digit code was sent to {email}. Enter it below.", "info")
        return redirect(url_for("auth.verify_otp"))

    return render_template("register.html")


# ══════════════════════════════════════════════════════════════════
# OTP VERIFY
# ══════════════════════════════════════════════════════════════════
@auth.route("/verify", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_verify_email")
    if not email:
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        entered = request.form.get("otp", "").strip()
        user    = User.query.filter_by(email=email).first()

        if not user:
            flash("Session expired. Please register again.", "danger")
            return redirect(url_for("auth.register"))

        if user.email_verified:
            login_user(user)
            return redirect(url_for("index"))

        if datetime.utcnow() > user.otp_expires:
            flash("Code expired. Click Resend to get a new one.", "danger")
            return render_template("verify.html", email=email)

        if entered != user.otp_code:
            flash("Incorrect code. Please try again.", "danger")
            return render_template("verify.html", email=email)

        # ✅ Verified
        user.email_verified = True
        user.otp_code       = None
        user.otp_expires    = None
        db.session.commit()

        session.pop("pending_verify_email", None)
        login_user(user)
        return redirect(url_for("index"))

    return render_template("verify.html", email=email)


@auth.route("/verify/resend", methods=["POST"])
def resend_otp():
    email = session.get("pending_verify_email")
    if not email:
        return redirect(url_for("auth.register"))

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for("auth.register"))

    otp             = _generate_otp()
    user.otp_code   = otp
    user.otp_expires = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    send_otp_email(email, user.name, otp)
    flash("A new code has been sent to your email.", "info")
    return redirect(url_for("auth.verify_otp"))


# ══════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════
@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        if not user or not user.password_hash or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        if not user.email_verified:
            # Re-send OTP and redirect to verify
            otp             = _generate_otp()
            user.otp_code   = otp
            user.otp_expires = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            send_otp_email(email, user.name, otp)
            session["pending_verify_email"] = email
            flash("Please verify your email first. A new code has been sent.", "warning")
            return redirect(url_for("auth.verify_otp"))

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("login.html")


# ══════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))


# ══════════════════════════════════════════════════════════════════
# FORGOT PASSWORD
# ══════════════════════════════════════════════════════════════════
@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = User.query.filter_by(email=email).first()

        # Always show success (prevent email enumeration)
        if user and user.password_hash:
            token            = secrets.token_urlsafe(32)
            user.reset_token   = token
            user.reset_expires = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()

            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_reset_email(email, user.name, reset_url)

        flash("If that email exists, a reset link has been sent.", "info")
        return render_template("forgot_password.html", submitted=True)

    return render_template("forgot_password.html", submitted=False)


# ══════════════════════════════════════════════════════════════════
# RESET PASSWORD
# ══════════════════════════════════════════════════════════════════
@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_expires or datetime.utcnow() > user.reset_expires:
        flash("This reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("reset_password.html", token=token)
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        user.set_password(password)
        user.reset_token   = None
        user.reset_expires = None
        db.session.commit()

        flash("Password reset successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


# ══════════════════════════════════════════════════════════════════
# GOOGLE OAUTH
# ══════════════════════════════════════════════════════════════════
@auth.route("/login/google")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True,_scheme="https")
    return google.authorize_redirect(redirect_uri)


@auth.route("/login/google/callback")
def google_callback():
    try:
        token    = google.authorize_access_token()
        userinfo = token.get("userinfo")
        if not userinfo:
            import httpx
            userinfo = google.userinfo(token=token)
    except Exception as e:
        flash("Google login failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    google_id = userinfo.get("sub")
    email     = userinfo.get("email", "").lower()
    name      = userinfo.get("name", email.split("@")[0])
    avatar    = userinfo.get("picture", "")

    # Find or create user
    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        # Check if email already registered (merge accounts)
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id  = google_id
            user.avatar_url = avatar
            user.email_verified = True
        else:
            user = User(
                name=name, email=email,
                google_id=google_id, avatar_url=avatar,
                email_verified=True,
            )
            db.session.add(user)
            db.session.flush()
            _create_profile(user.id)

    user.avatar_url = avatar
    db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════════════
# PROFILE API
# ══════════════════════════════════════════════════════════════════
@auth.route("/api/profile/save", methods=["POST"])
@login_required
def save_profile():
    data    = request.get_json(silent=True) or {}
    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)

    profile.age       = data.get("age")       or profile.age
    profile.gender    = data.get("gender")    or profile.gender
    profile.weight_kg = data.get("weight_kg") or profile.weight_kg
    profile.height_cm = data.get("height_cm") or profile.height_cm
    profile.goal      = data.get("goal")      or profile.goal
    profile.diet      = data.get("diet")      or profile.diet
    db.session.commit()
    return jsonify({"status": "saved"})


@auth.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    p = current_user.profile
    return jsonify({
        "name":      current_user.name,
        "email":     current_user.email,
        "plan":      current_user.plan,
        "age":       p.age       if p else None,
        "gender":    p.gender    if p else None,
        "weight_kg": p.weight_kg if p else None,
        "height_cm": p.height_cm if p else None,
        "goal":      p.goal      if p else None,
        "diet":      p.diet      if p else None,
        "usage":     current_user.usage_summary(),
    })
