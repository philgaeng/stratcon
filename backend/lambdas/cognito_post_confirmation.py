"""
Cognito PostConfirmation Lambda Trigger
Automatically adds newly confirmed users to the default group (viewer).
"""
import os
import boto3

cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ["USER_POOL_ID"]
DEFAULT_GROUP = os.getenv("DEFAULT_GROUP", "viewer")


def handler(event, context):
    """
    PostConfirmation Lambda handler.
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        event: Unmodified event
    """
    # Only process sign-up confirmations
    if event.get("triggerSource") != "PostConfirmation_ConfirmSignUp":
        return event
    
    username = event.get("userName")
    if not username:
        return event
    
    try:
        # Add user to default group
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=DEFAULT_GROUP,
        )
    except Exception as e:
        # Log error but don't fail the confirmation
        print(f"Error adding user {username} to group {DEFAULT_GROUP}: {str(e)}")
    
    return event

