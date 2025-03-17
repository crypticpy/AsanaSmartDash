"""
Text formatting utilities for the Asana Chat Assistant.

This module provides functions for formatting various data structures
into readable text for chat responses.
"""
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta

def format_project_progress(project_details: List[Dict[str, Any]]) -> str:
    """
    Format project progress information for text response.
    
    Args:
        project_details: List of project details
        
    Returns:
        Formatted text with project progress information
    """
    if not project_details:
        return "No project data available."
    
    result = "Project Progress Summary:\n\n"
    
    for project in project_details:
        name = project.get("name", "Unknown project")
        total = project.get("total_tasks", 0)
        completed = project.get("completed_tasks", 0)
        
        if total > 0:
            percentage = (completed / total) * 100
            status = "✅ On track" if percentage >= 75 else "⚠️ At risk" if percentage >= 50 else "❌ Behind"
            
            result += f"{name}: {percentage:.1f}% complete ({completed}/{total} tasks) - {status}\n"
        else:
            result += f"{name}: No tasks available\n"
    
    return result

def format_recent_activity(task_df: pd.DataFrame, days: int = 7) -> str:
    """
    Format recent activity information for text response.
    
    Args:
        task_df: DataFrame with task data
        days: Number of days to consider as recent
        
    Returns:
        Formatted text with recent activity information
    """
    if task_df.empty:
        return "No task data available."
    
    # Ensure datetime columns are properly converted
    task_df = task_df.copy()
    if 'created_at' in task_df.columns and task_df['created_at'].dtype != 'datetime64[ns, UTC]':
        task_df['created_at'] = pd.to_datetime(task_df['created_at'], utc=True)
    if 'completed_at' in task_df.columns and task_df['completed_at'].dtype != 'datetime64[ns, UTC]':
        task_df['completed_at'] = pd.to_datetime(task_df['completed_at'], utc=True)
    
    # Get recent date cutoff
    recent_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days)
    
    # Filter for recent tasks
    recent_completed = task_df[(task_df['completed_at'] >= recent_date) & (task_df['status'] == 'Completed')]
    recent_created = task_df[task_df['created_at'] >= recent_date]
    
    # Generate summary
    result = f"Recent Activity (Last {days} Days):\n\n"
    result += f"- Tasks completed: {len(recent_completed)}\n"
    result += f"- Tasks created: {len(recent_created)}\n\n"
    
    # Add recently completed tasks
    if not recent_completed.empty:
        result += "Recently completed tasks:\n"
        for _, task in recent_completed.sort_values('completed_at', ascending=False).head(5).iterrows():
            completion_date = task['completed_at'].strftime('%Y-%m-%d')
            result += f"- '{task['name']}' from '{task['project']}' (completed on {completion_date})\n"
    
    return result

def _format_single_task(task):
    """Format a single task into a string representation."""
    # Format task information
    task_info = f"- {task['name']} ({task['project']})"
    
    # Add status
    if 'status' in task:
        task_info += f" - {task['status']}"
    
    # Add assignee if available
    if 'assignee' in task and pd.notna(task['assignee']):
        task_info += f" - Assigned to: {task['assignee']}"
    
    # Add due date if available
    if 'due_date' in task and pd.notna(task['due_date']):
        due_date = task['due_date'].strftime('%Y-%m-%d')
        task_info += f" - Due: {due_date}"
    
    return task_info + "\n"

def format_task_list(tasks: pd.DataFrame, max_tasks: int = 10) -> str:
    """
    Format a list of tasks for text response.
    
    Args:
        tasks: DataFrame with filtered task data
        max_tasks: Maximum number of tasks to include in output
        
    Returns:
        Formatted text with task list
    """
    if tasks.empty:
        return "No matching tasks found."
    
    result = f"Found {len(tasks)} tasks:\n\n"
    
    # Get tasks to display (up to max_tasks)
    display_tasks = tasks.head(max_tasks)
    
    # Format each task
    for _, task in display_tasks.iterrows():
        result += _format_single_task(task)
    
    # Add note if more tasks were found than displayed
    if len(tasks) > max_tasks:
        result += f"\n... and {len(tasks) - max_tasks} more tasks not shown"
    
    return result

def _format_date_field(field_name, value, prefix=""):
    """Format a date field with appropriate handling of different types."""
    if not value:
        return ""
        
    if isinstance(value, str):
        return f"{prefix}{field_name}: {value}\n"
    else:
        formatted_date = value.strftime('%Y-%m-%d')
        return f"{prefix}{field_name}: {formatted_date}\n"

def _format_progress_info(project):
    """Format progress information for a project."""
    total = project.get('total_tasks', 0)
    completed = project.get('completed_tasks', 0)
    
    if total <= 0:
        return ""
        
    percentage = (completed / total) * 100
    return f"Progress: {percentage:.1f}% ({completed}/{total} tasks completed)\n"

def _format_schedule_status(project):
    """Format schedule status information for a project."""
    if 'days_difference' not in project or pd.isna(project['days_difference']):
        return ""
        
    days_diff = project['days_difference']
    if days_diff > 0:
        return f"Project is {days_diff} days behind schedule.\n"
    elif days_diff < 0:
        return f"Project is {abs(days_diff)} days ahead of schedule.\n"
    else:
        return "Project is on schedule.\n"

def format_project_details(project: Dict[str, Any]) -> str:
    """
    Format detailed information about a project.
    
    Args:
        project: Dictionary with project details
        
    Returns:
        Formatted text with project details
    """
    if not project:
        return "Project details not available."
    
    result = f"Project: {project.get('name', 'Unknown')}\n\n"
    
    # Add owner if available
    if 'owner' in project and project['owner']:
        result += f"Owner: {project['owner']}\n"
    
    # Add progress information
    result += _format_progress_info(project)
    
    # Add date fields
    result += _format_date_field("Due date", project.get('due_date'))
    result += _format_date_field("Estimated completion", project.get('estimated_completion_date'))
    
    # Add schedule status
    result += _format_schedule_status(project)
    
    # Add team members count if available
    if 'members_count' in project:
        result += f"Team members: {project['members_count']}\n"
    
    # Add overdue tasks if available
    if 'overdue_tasks' in project:
        result += f"Overdue tasks: {project['overdue_tasks']}\n"
    
    return result 