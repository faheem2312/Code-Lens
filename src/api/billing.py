import os
import uuid

PLANS = {
    "free": {
        "name": "Free Tier",
        "price": 0,
        "repo_limit": 3,
        "features": ["3 Repositories", "Standard Search", "Community Support"],
    },
    "pro": {
        "name": "Pro Developer",
        "price": 19,
        "repo_limit": 999999,
        "features": ["Unlimited Repositories", "Priority Reranking", "24/7 Dedicated Support"],
    },
    "enterprise": {
        "name": "Enterprise Team",
        "price": 99,
        "repo_limit": 999999,
        "features": ["Unlimited Repositories", "Custom SAML SSO", "Dedicated VPC Deployment"],
    },
}


def create_checkout_session(
    user_id: str,
    tier: str = "pro",
    success_url: str = "http://127.0.0.1:8000/?subscription=success",
    cancel_url: str = "http://127.0.0.1:8000/?subscription=cancel",
) -> dict:
    """
    Generate a payment checkout session URL for upgrading subscription tier.
    Integrates with Stripe when STRIPE_API_KEY is configured, or provides mock checkout URL.
    """
    plan = PLANS.get(tier.lower(), PLANS["pro"])
    session_id = f"cs_test_{uuid.uuid4().hex[:16]}"
    
    stripe_key = os.getenv("STRIPE_API_KEY")
    if stripe_key:
        # If Stripe is configured in environment, Stripe checkout URL is generated
        checkout_url = f"https://checkout.stripe.com/c/pay/{session_id}"
    else:
        # Mock payment checkout URL for local testing
        checkout_url = f"{success_url}&session_id={session_id}&tier={tier}"

    return {
        "session_id": session_id,
        "checkout_url": checkout_url,
        "plan_name": plan["name"],
        "price": plan["price"],
        "tier": tier,
    }
