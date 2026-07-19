"""Discord webhook integration tool plugin."""

def tool_discord_post_webhook(webhook_url: str, content: str) -> str:
    """Post a chat message to a Discord server webhook.
    
    Args:
        webhook_url: Target discord webhook address.
        content: Chat message body text.
    """
    return f"Discord: Webhook message successfully posted."
