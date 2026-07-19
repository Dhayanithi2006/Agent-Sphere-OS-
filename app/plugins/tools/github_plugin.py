"""GitHub integration tool plugin."""

def tool_github_create_issue(repo: str, title: str, body: str) -> str:
    """Create a GitHub issue in the specified repository.
    
    Args:
        repo: Repository identifier, e.g. 'owner/repo'.
        title: Issue title.
        body: Issue body markdown.
    """
    return f"GitHub: Issue '{title}' successfully created in repository '{repo}'."


def tool_github_list_pulls(repo: str, state: str = "open") -> str:
    """List open or closed pull requests.
    
    Args:
        repo: Repository identifier, e.g. 'owner/repo'.
        state: State of pull requests ('open', 'closed').
    """
    return f"GitHub: Retrieved {state} pull requests for '{repo}': [PR-42] Fix layout alignment."
