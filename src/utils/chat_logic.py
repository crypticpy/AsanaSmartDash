"""
Chat logic for the Asana Portfolio Dashboard.
This module contains the core logic for the AI chat assistant that answers
questions about Asana projects and tasks.

This file is maintained for backward compatibility. New code should import
directly from the src.utils.chat package.
"""

# Import from new modular structure to maintain backward compatibility
from src.utils.chat import AsanaChatAssistant
from src.utils.chat.formatting import format_project_progress, format_recent_activity

# Export symbols for backward compatibility
__all__ = [
    "AsanaChatAssistant",
    "format_project_progress",
    "format_recent_activity"
]