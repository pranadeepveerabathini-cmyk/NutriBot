"""
NutriBot SaaS — Billing & Payments via Stripe.
Handles Checkout sessions, Customer Portal, and Webhook processing.
"""

import os
import logging
import stripe
from flask import url_for, jsonify
from models import db, User

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PRICE_MAP = {
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
    "family": os.getenv("STRIPE_PRICE_FAMILY", "price_family_placeholder"),
}

PLAN_NAME_MAP = {
    "pro": "Pro Plan",
    "family": "Family Plan",
}


def create_checkout_session(user: User, plan_type: str, success_url: str, cancel_url: str) -> dict:
    """
    Creates a Stripe Checkout Session for upgrading plan.
    """
    if plan_type not in PRICE_MAP:
        return {"error": "Invalid plan type."}

    if not stripe.api_key or stripe.api_key.startswith("sk_test_placeholder") or stripe.api_key == "":
        # Demo / Simulated payment upgrade when Stripe keys are default
        user.plan = plan_type
        user.subscription_status = "active"
        db.session.commit()
        return {"demo": True, "message": f"Upgraded to {plan_type.capitalize()} plan (Demo Mode)."}

    try:
        # Create or fetch Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": user.id}
            )
            user.stripe_customer_id = customer.id
            db.session.commit()

        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": PRICE_MAP[plan_type],
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user.id,
                "plan_type": plan_type,
            }
        )
        return {"url": checkout_session.url}
    except Exception as e:
        logger.error("Stripe Checkout error: %s", e)
        return {"error": str(e)}


def create_customer_portal_session(user: User, return_url: str) -> dict:
    """
    Creates a Stripe Customer Portal session for subscription management.
    """
    if not user.stripe_customer_id:
        return {"error": "No subscription found."}

    if not stripe.api_key or stripe.api_key.startswith("sk_test_placeholder") or stripe.api_key == "":
        return {"demo": True, "message": "Portal unavailable in Demo mode."}

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )
        return {"url": portal_session.url}
    except Exception as e:
        logger.error("Stripe Portal error: %s", e)
        return {"error": str(e)}


def handle_stripe_webhook(payload: bytes, sig_header: str) -> tuple:
    """
    Handles incoming Stripe Webhook events to automatically activate / cancel subscriptions.
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured.")
        return jsonify({"status": "ignored"}), 200

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error("Invalid webhook payload: %s", e)
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid webhook signature: %s", e)
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_type = metadata.get("plan_type")

        if user_id and plan_type:
            user = User.query.get(int(user_id))
            if user:
                user.plan = plan_type
                user.subscription_status = "active"
                user.stripe_subscription_id = data_object.get("subscription")
                db.session.commit()
                logger.info("User %s upgraded to %s via Stripe", user.email, plan_type)

    elif event_type in ["customer.subscription.deleted", "customer.subscription.updated"]:
        sub_id = data_object.get("id")
        status = data_object.get("status")
        user = User.query.filter_by(stripe_subscription_id=sub_id).first()
        if user:
            user.subscription_status = status
            if status == "canceled":
                user.plan = "free"
            db.session.commit()

    return jsonify({"status": "success"}), 200
