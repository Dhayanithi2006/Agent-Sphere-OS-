"""Jira ticket integration tool plugin."""

def tool_jira_create_ticket(project: str, summary: str, description: str) -> str:
    """Create a new issue ticket in Jira.
    
    Args:
        project: Project key, e.g. 'PROJ'.
        summary: Short summary of the ticket.
        description: Full ticket details.
    """
    return f"Jira: Ticket '{project}-101' created: '{summary}'."
