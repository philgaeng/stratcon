#!/usr/bin/env python3
"""
Verify email addresses in AWS SES from database users and contacts.

This script:
1. Reads all unique email addresses from users and contacts tables
2. Initiates verification for each email in AWS SES
3. Users will receive verification emails and must click the link to complete verification
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("❌ boto3 is not installed. Install it with: pip install boto3")
    sys.exit(1)

from services.data.db_manager.db_schema import get_db_connection
from load_env import load_env_local


def get_all_emails_from_database():
    """Get all unique email addresses from users and contacts tables."""
    conn = get_db_connection()
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()
    
    # Get emails from users table
    cursor.execute("SELECT DISTINCT email FROM users WHERE email IS NOT NULL AND email != ''")
    user_emails = [row['email'] for row in cursor.fetchall()]
    
    # Get emails from contacts table
    cursor.execute("SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL AND email != ''")
    contact_emails = [row['email'] for row in cursor.fetchall()]
    
    # Combine and deduplicate
    all_emails = list(set(user_emails + contact_emails))
    
    conn.close()
    
    return all_emails


def check_verification_status(ses_client, email: str, region: str):
    """Check if an email is already verified in SES."""
    try:
        response = ses_client.get_identity_verification_attributes(
            Identities=[email]
        )
        attributes = response.get('VerificationAttributes', {})
        if email in attributes:
            status = attributes[email].get('VerificationStatus')
            return status
        return None
    except ClientError as e:
        print(f"   ⚠️  Error checking status for {email}: {e}")
        return None


def verify_email_in_ses(ses_client, email: str, region: str):
    """Initiate verification for an email address in AWS SES."""
    try:
        # Check if already verified
        status = check_verification_status(ses_client, email, region)
        if status == 'Success':
            return 'already_verified'
        
        # Initiate verification
        ses_client.verify_email_identity(EmailAddress=email)
        return 'verification_sent'
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AlreadyExists':
            return 'already_pending'
        return f'error: {e}'


def main():
    """Main function to verify all emails."""
    print("=" * 60)
    print("AWS SES Email Verification Script")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_env_local()
    
    # Get AWS configuration
    aws_region = os.getenv('AWS_REGION', 'ap-southeast-1')
    sender_email = os.getenv('SES_SENDER_EMAIL', 'philippe@stratcon.ph')
    
    if not BOTO3_AVAILABLE:
        print("❌ boto3 is not available")
        return
    
    # Initialize SES client
    try:
        ses_client = boto3.client('ses', region_name=aws_region)
        print(f"✅ Connected to AWS SES in region: {aws_region}")
    except Exception as e:
        print(f"❌ Failed to initialize SES client: {e}")
        return
    
    # Get all emails from database
    print("\n📧 Fetching emails from database...")
    emails = get_all_emails_from_database()
    print(f"   Found {len(emails)} unique email addresses")
    
    if not emails:
        print("   No emails found in database")
        return
    
    # Verify each email
    print("\n🔐 Verifying emails in AWS SES...")
    print(f"   Region: {aws_region}")
    print()
    
    results = {
        'already_verified': [],
        'verification_sent': [],
        'already_pending': [],
        'errors': []
    }
    
    for email in sorted(emails):
        print(f"   Processing: {email}...", end=" ")
        result = verify_email_in_ses(ses_client, email, region=aws_region)
        
        if result == 'already_verified':
            print("✅ Already verified")
            results['already_verified'].append(email)
        elif result == 'verification_sent':
            print("📧 Verification email sent")
            results['verification_sent'].append(email)
        elif result == 'already_pending':
            print("⏳ Verification already pending")
            results['already_pending'].append(email)
        else:
            print(f"❌ {result}")
            results['errors'].append((email, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Already verified: {len(results['already_verified'])}")
    print(f"📧 Verification sent: {len(results['verification_sent'])}")
    print(f"⏳ Already pending: {len(results['already_pending'])}")
    print(f"❌ Errors: {len(results['errors'])}")
    
    if results['verification_sent']:
        print("\n📬 Verification emails sent to:")
        for email in results['verification_sent']:
            print(f"   - {email}")
        print("\n💡 Users must check their email and click the verification link.")
    
    if results['errors']:
        print("\n❌ Errors encountered:")
        for email, error in results['errors']:
            print(f"   - {email}: {error}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

