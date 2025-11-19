#!/usr/bin/env python3
"""
Email service for sending reports via AWS SES.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .utils import ReportLogger


def send_report_email(
    *,
    email: str,
    client_name: str,
    tenant_name: str,
    last_month: Optional[str] = None,
    attachments: Optional[List[Path]] = None,
    logger: Optional[ReportLogger] = None,
) -> bool:
    """
    Send report email with attachments via AWS SES.
    
    Args:
        email: Recipient email address
        attachments: Optional list of report file paths to attach
        client_name: Client name for email subject
        tenant_name: Tenant name for email subject
        last_month: Reporting period identifier
        logger: Optional logger instance
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if logger is None:
        logger = ReportLogger()
    attachments = attachments or []
    logger.debug(f"sending report email to {email} for client {client_name} and tenant {tenant_name} with last month {last_month}")
    
    if not BOTO3_AVAILABLE:
        logger.error("❌ boto3 is not installed. Install it with: pip install boto3")
        return False

    try:
        # Initialize SES client
        ses_client = boto3.client('ses', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        # Get sender email from environment or use default
        sender_email = os.getenv('SES_SENDER_EMAIL', 'philippe@stratcon.ph')
        
        # Validate sender email is verified in SES
        try:
            ses_client.get_identity_verification_attributes(Identities=[sender_email])
        except ClientError:
            logger.warning(f"⚠️ Sender email {sender_email} may not be verified in SES")
        
        # Build email subject
        subject_period = last_month or "Latest"
        subject = f"Electricity Report - {client_name} - {tenant_name} - {subject_period}"
        
        # Build email body (HTML)
        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: #333; }}
                h1 {{ font-family: 'Montserrat', Arial, sans-serif; font-size: 24px; color: #2E7D32; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Electricity Consumption Report</h1>
                <p>Dear User,</p>
                <p>Your electricity consumption report has been generated successfully.</p>
                <p><strong>Client:</strong> {client_name}</p>
                <p><strong>Tenant:</strong> {tenant_name}</p>
                <p><strong>Period:</strong> {subject_period}</p>
                <p>The report is attached to this email.</p>
                <p>Best regards,<br>Stratcon</p>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Electricity Consumption Report
        
        Dear User,
        
        Your electricity consumption report has been generated successfully.
        
        Client: {client_name}
        Tenant: {tenant_name}
        Period: {subject_period}
        
        The report is attached to this email.
        
        Best regards,
        Stratcon
        
        ---
        This is an automated email. Please do not reply.
        """
        
        # Prepare attachments
        encoded_attachments: List[dict[str, str]] = []
        for report_path in attachments:
            if not report_path.exists():
                logger.warning(f"⚠️ Report file not found: {report_path}")
                continue

            with open(report_path, "rb") as f:
                file_data = f.read()

            ext = report_path.suffix.lower()
            if ext == ".html":
                content_type = "text/html"
            elif ext == ".pdf":
                content_type = "application/pdf"
            else:
                content_type = "application/octet-stream"

            encoded_attachments.append(
                {
                    "name": report_path.name,
                    "data": file_data,
                    "content_type": content_type,
                }
            )

        if not encoded_attachments:
            logger.error("❌ No valid report files to attach")
            return False
        
        # Send email using SES send_raw_email
        # Note: For production, consider using AWS SES template or sending service
        message_parts = [
            f"From: {sender_email}",
            f"To: {email}",
            f"Subject: {subject}",
            "MIME-Version: 1.0",
            "Content-Type: multipart/mixed; boundary=mixed_boundary",
            "",
            "--mixed_boundary",
            "Content-Type: multipart/alternative; boundary=alt_boundary",
            "",
            "--alt_boundary",
            "Content-Type: text/plain; charset=utf-8",
            "Content-Transfer-Encoding: quoted-printable",
            "",
            body_text,
            "",
            "--alt_boundary",
            "Content-Type: text/html; charset=utf-8",
            "Content-Transfer-Encoding: quoted-printable",
            "",
            body_html,
            "",
            "--alt_boundary--",
        ]
        
        # Add attachments
        for att in encoded_attachments:
            import base64
            encoded_data = base64.b64encode(att['data']).decode('utf-8')
            message_parts.extend([
                "",
                "--mixed_boundary",
                f"Content-Type: {att['content_type']}; name=\"{att['name']}\"",
                "Content-Transfer-Encoding: base64",
                f"Content-Disposition: attachment; filename=\"{att['name']}\"",
                "",
                encoded_data,
            ])
        
        message_parts.append("")
        message_parts.append("--mixed_boundary--")
        
        raw_message = "\n".join(message_parts)
        
        # Send email
        response = ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[email],
            RawMessage={'Data': raw_message.encode('utf-8')}
        )
        
        logger.info(f"✅ Email sent successfully to {email}")
        logger.info(f"   Message ID: {response['MessageId']}")
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"❌ AWS SES error ({error_code}): {error_msg}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

