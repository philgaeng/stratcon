#!/usr/bin/env python3
"""
Test script to send a test email via the email service.
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables from env.local
from load_env import load_env_local
load_env_local()

def test_email_sending():
    """Test sending an email"""
    print("="*60)
    print("Testing Email Service")
    print("="*60)
    
    try:
        from services.email_service import send_report_email
        from services.utils import ReportLogger
        
        logger = ReportLogger()
        
        # Create a dummy test report file
        test_report_path = Path("/tmp/test_report.html")
        test_report_path.write_text("""
        <html>
        <body>
            <h1>Test Report</h1>
            <p>This is a test email from Stratcon API.</p>
            <p>If you receive this, the email service is working!</p>
        </body>
        </html>
        """)
        
        recipient_email = "philgaeng@gmail.com"
        print(f"\n📧 Sending test email to: {recipient_email}")
        print(f"   Test report file: {test_report_path}")
        
        result = send_report_email(
            email=recipient_email,
            client_name="Test Client",
            tenant_name="Test Tenant",
            last_month="2025-01",
            attachments=[test_report_path],
            logger=logger,
        )
        
        if result:
            print(f"\n✅ Email sent successfully!")
            print(f"   Check inbox at: {recipient_email}")
            print(f"   (Note: May take a few moments to arrive)")
        else:
            print(f"\n❌ Email sending failed")
            print(f"   Check logs above for error details")
            print(f"\n   Common issues:")
            print(f"   - AWS credentials not configured")
            print(f"   - Sender email not verified in SES")
            print(f"   - Recipient email not verified (if in SES sandbox)")
            print(f"   - AWS_REGION not set")
        
        # Cleanup
        if test_report_path.exists():
            test_report_path.unlink()
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_email_sending()
    sys.exit(0 if success else 1)

