"""Gmail email integration tool plugin."""

def tool_gmail_send_email(to: str, subject: str, body: str) -> str:
    """Send an email using Gmail services.
    
    Args:
        to: Recipient email address.
        subject: Email subject header.
        body: Message body.
    """
    return f"Gmail: Email successfully dispatched to '{to}' under subject '{subject}'."
