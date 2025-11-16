"""
Cognito PreSignUp Lambda Trigger
Rejects sign-ups from email domains not in the allowlist.
"""
import os

ALLOWLIST = {
    d.strip().lower()
    for d in os.getenv("ALLOWLIST_DOMAINS", "").split(",")
    if d.strip()
}


def handler(event, context):
    """
    PreSignUp Lambda handler.
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        event: Modified event (or raises Exception if domain not allowed)
    """
    email = (event.get("request", {}).get("userAttributes", {}).get("email") or "").lower()
    domain = email.split("@")[-1] if "@" in email else ""
    
    if not domain:
        raise Exception("Invalid email address")
    
    if domain not in ALLOWLIST:
        raise Exception(f"Sign-up not allowed for email domain: {domain}")
    
    # Keep default confirmation behavior (email verification required)
    event["response"]["autoConfirmUser"] = False
    event["response"]["autoVerifyEmail"] = False
    
    return event

