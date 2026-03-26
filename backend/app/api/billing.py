"""
Stripe billing integration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

log = logging.getLogger("anemialens.billing")

router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PRO_SUBSCRIPTION_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "price_test_123")

# Demo mode if key is missing or looks like a placeholder
_DEMO_MODE = (
    not stripe.api_key
    or len(stripe.api_key) < 30
    or stripe.api_key.endswith("this")
    or "placeholder" in stripe.api_key.lower()
)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


@router.post(
    "/create-checkout-session",
    response_model=CheckoutSessionResponse,
    summary="Create Stripe Checkout Session",
)
async def create_checkout_session(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CheckoutSessionResponse:
    origin = request.headers.get("origin", "http://localhost:5173")

    if _DEMO_MODE:
        log.warning("No Stripe API key configured. Checkout unavailable in demo mode.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured. Please set a valid STRIPE_SECRET_KEY.",
        )

    try:
        # The base origin for success/cancel URLs

        # Determine if we should create a new customer or use an existing one
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                email=user.email,
                metadata={"user_uid": user.uid},
            )
            customer_id = customer.id
            # NOTE: We can't trivially update the User synchronously here because 
            # stripe is sync/blocking, but we can rely on the webhook to sync it, 
            # or just write it below if we wrap in async block.
            # We'll just rely on the webhook to formalize the relation.

        checkout_session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": PRO_SUBSCRIPTION_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{origin}/?payment_success=true",
            cancel_url=f"{origin}/?payment_cancelled=true",
        )
        return CheckoutSessionResponse(checkout_url=checkout_session.url)
    except Exception as e:
        log.error("Stripe error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/webhook",
    summary="Stripe Webhook handler",
    include_in_schema=False,
)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Handle Stripe webhooks for subscription fulfillment.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")

        if customer_id:
            # We need the user associated with this customer email
            customer = stripe.Customer.retrieve(customer_id)
            user_uid = customer.metadata.get("user_uid")

            if user_uid:
                result = await db.execute(select(User).where(User.uid == user_uid))
                u = result.scalar_one_or_none()
                if u:
                    u.stripe_customer_id = customer_id
                    u.subscription_tier = "pro"
                    await db.commit()
                    log.info("User %s upgraded to pro", u.email)

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        
        if customer_id:
            result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
            u = result.scalar_one_or_none()
            if u:
                u.subscription_tier = "free"
                await db.commit()
                log.info("User %s downgraded to free", u.email)

    return {"status": "success"}
