"""
NutriBot — Email sender via Resend API.
Handles: OTP verification, password reset.
"""

import os
import resend
import logging

logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY", "")

MAIL_FROM      = os.getenv("MAIL_FROM", "onboarding@resend.dev")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "NutriBot")
FROM_ADDRESS   = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"


# ──────────────────────────────────────────────────────────────────
# OTP Verification Email
# ──────────────────────────────────────────────────────────────────
def send_otp_email(to_email: str, name: str, otp: str) -> bool:
    html = f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:480px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);padding:32px 40px;text-align:center;">
        <div style="font-size:2.5rem;margin-bottom:8px;">🥗</div>
        <h1 style="color:#ffffff;font-size:1.4rem;margin:0;font-weight:700;">NutriBot</h1>
        <p style="color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:.85rem;">AI Nutrition Agent</p>
      </div>
      <div style="padding:36px 40px;">
        <h2 style="color:#0f172a;font-size:1.2rem;margin:0 0 8px;">Verify your email</h2>
        <p style="color:#64748b;font-size:.9rem;margin:0 0 28px;">Hi {name}, use the code below to verify your NutriBot account.</p>
        <div style="background:#f1f5f9;border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
          <div style="letter-spacing:10px;font-size:2.2rem;font-weight:800;color:#2563eb;">{otp}</div>
          <p style="color:#94a3b8;font-size:.75rem;margin:8px 0 0;">Expires in 10 minutes</p>
        </div>
        <p style="color:#94a3b8;font-size:.78rem;margin:0;">If you didn't create a NutriBot account, you can safely ignore this email.</p>
      </div>
      <div style="background:#f8fafc;padding:16px 40px;border-top:1px solid #e2e8f0;text-align:center;">
        <p style="color:#cbd5e1;font-size:.72rem;margin:0;">© 2024 NutriBot · AI Nutrition Agent</p>
      </div>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_ADDRESS,
            "to":      [to_email],
            "subject": f"{otp} is your NutriBot verification code",
            "html":    html,
        })
        logger.info("OTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send OTP email to %s: %s", to_email, e)
        return False


# ──────────────────────────────────────────────────────────────────
# Password Reset Email
# ──────────────────────────────────────────────────────────────────
def send_reset_email(to_email: str, name: str, reset_url: str) -> bool:
    html = f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:480px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);padding:32px 40px;text-align:center;">
        <div style="font-size:2.5rem;margin-bottom:8px;">🥗</div>
        <h1 style="color:#ffffff;font-size:1.4rem;margin:0;font-weight:700;">NutriBot</h1>
        <p style="color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:.85rem;">AI Nutrition Agent</p>
      </div>
      <div style="padding:36px 40px;">
        <h2 style="color:#0f172a;font-size:1.2rem;margin:0 0 8px;">Reset your password</h2>
        <p style="color:#64748b;font-size:.9rem;margin:0 0 28px;">Hi {name}, click the button below to reset your password. This link expires in 30 minutes.</p>
        <div style="text-align:center;margin-bottom:28px;">
          <a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:600;font-size:.95rem;">Reset Password</a>
        </div>
        <p style="color:#64748b;font-size:.82rem;margin:0 0 8px;">Or copy this link:</p>
        <p style="color:#2563eb;font-size:.78rem;word-break:break-all;margin:0;">{reset_url}</p>
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
        <p style="color:#94a3b8;font-size:.78rem;margin:0;">If you didn't request a password reset, you can safely ignore this email.</p>
      </div>
      <div style="background:#f8fafc;padding:16px 40px;border-top:1px solid #e2e8f0;text-align:center;">
        <p style="color:#cbd5e1;font-size:.72rem;margin:0;">© 2024 NutriBot · AI Nutrition Agent</p>
      </div>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_ADDRESS,
            "to":      [to_email],
            "subject": "Reset your NutriBot password",
            "html":    html,
        })
        logger.info("Reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send reset email to %s: %s", to_email, e)
        return False
