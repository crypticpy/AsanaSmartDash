"""
Visualization handler for the Asana Chat Assistant.

This module handles the detection and generation of visualizations
based on user queries and chat responses.
"""
import logging
import re
from typing import Dict, Any, List, Optional, Union

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.utils.visualizations import (
    create_interactive_timeline, create_velocity_chart, create_burndown_chart,
    create_resource_allocation_chart, create_task_status_distribution, create_project_progress_bars
)

logger = logging.getLogger("asana_chat_assistant")

# Define constants for task statuses
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETED = "Completed"

def extract_visualization_info(query: str, response: str) -> Dict[str, Any]:
    """
    Determine if visualization is needed and extract visualization type and parameters.

    Args:
        query: User's query text
        response: Generated response text

    Returns:
        Dictionary with visualization info (needed, type, params)
    """
    # Keywords that indicate visualization might be helpful
    viz_keywords = {
        "timeline": ["timeline", "schedule", "when", "due date", "deadline", "gantt"],
        "resource_allocation": ["resource", "assignee", "who", "workload", "allocation",
                               "team member"],
        "task_status": ["status", "distribution", "completion rate", "completed", "in progress"],
        "velocity": ["velocity", "speed", "productivity", "trend", "over time", "completed per"],
        "burndown": ["burndown", "remaining work", "completion trend", "track progress"],
        "project_progress": ["progress", "completion", "percent complete", "status update"]
    }

    # Default response if no visualization needed
    result = {
        "needed": False,
        "type": None,
        "params": {}
    }

    # Look for explicit visualization suggestions in the response
    viz_type = None

    # Look for explicit visualization suggestions in the response
    viz_patterns = [
        r'visualization of type "([a-z_]+)"',
        r'suggest a ([a-z_]+) visualization',
        r'recommend a ([a-z_]+) chart',
        r'a ([a-z_]+) chart would help',
        r'I can show you a ([a-z_]+)'
    ]

    # Use next with a generator expression instead of a for loop
    matches = next((match for pattern in viz_patterns
                   if (match := re.search(pattern, response.lower()))), None)

    if matches and (viz_type := matches[1]) in viz_keywords:
        result["needed"] = True
        result["type"] = viz_type
        return result

    # Otherwise check query and response for keywords
    query_and_response = f"{query} {response}".lower()

    for vtype, keywords in viz_keywords.items():
        if any(keyword in query_and_response for keyword in keywords):
            result["needed"] = True
            result["type"] = vtype
            break

    return result

def generate_visualization(
    viz_type: str,
    params: Dict[str, Any],
    project_df: pd.DataFrame,
    task_df: pd.DataFrame,
    project_details: List[Dict[str, Any]]
) -> Optional[Union[go.Figure, Dict[str, Any]]]:
    """
    Generate a visualization based on the type and parameters.

    Args:
        viz_type: Type of visualization to generate
        params: Parameters for the visualization
        project_df: DataFrame with project data
        task_df: DataFrame with task data
        project_details: List of project details

    Returns:
        Plotly figure object or None if visualization can't be generated
    """
    result = None

    # Define visualization type handlers
    viz_handlers = {
        "timeline": lambda: create_interactive_timeline(project_df),
        "resource_allocation": lambda: create_resource_allocation_chart(task_df),
        "task_status": lambda: create_task_status_distribution(task_df),
        "project_progress": lambda: create_project_progress_bars(project_details),
        "assignee_workload": lambda: create_assignee_workload_chart(task_df),
        "project_comparison": lambda: create_project_comparison_chart(project_details),
    }

    try:
        # Handle velocity chart (needs special handling for project filtering)
        if viz_type == "velocity":
            if "project" in params and params["project"] in task_df["project"].unique():
                filtered_df = task_df[task_df["project"] == params["project"]]
                result = create_velocity_chart(filtered_df)
            else:
                result = create_velocity_chart(task_df)
        
        # Handle burndown chart (needs special handling for project filtering)
        elif viz_type == "burndown":
            if "project" in params and params["project"] in task_df["project"].unique():
                filtered_df = task_df[task_df["project"] == params["project"]]
                result = create_burndown_chart(filtered_df)
            else:
                result = create_burndown_chart(task_df)
        
        # Handle other visualization types using the handlers dictionary
        elif viz_type in viz_handlers:
            result = viz_handlers[viz_type]()
        
        # Default to task status distribution if type not recognized
        else:
            logger.warning("Unknown visualization type: %s, defaulting to task_status", viz_type)
            result = create_task_status_distribution(task_df)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Error generating visualization: %s", e)
        result = None

    return result

def create_assignee_workload_chart(task_df: pd.DataFrame) -> go.Figure:
    """
    Create a custom chart showing workload by assignee with task status breakdown.

    Args:
        task_df: DataFrame with task data

    Returns:
        Plotly figure object
    """
    # Group tasks by assignee and status
    task_counts = task_df.groupby(["assignee", "status"]).size().reset_index(name="count")

    # Pivot the data for plotting
    pivot_df = task_counts.pivot(
        index="assignee", columns="status", values="count"
    ).fillna(0).reset_index()

    # Ensure both 'Completed' and 'In Progress' columns exist
    if STATUS_COMPLETED not in pivot_df.columns:
        pivot_df[STATUS_COMPLETED] = 0
    if STATUS_IN_PROGRESS not in pivot_df.columns:
        pivot_df[STATUS_IN_PROGRESS] = 0

    # Create stacked bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=pivot_df["assignee"],
        y=pivot_df[STATUS_IN_PROGRESS],
        name=STATUS_IN_PROGRESS,
        marker_color="#FFC107"
    ))

    fig.add_trace(go.Bar(
        x=pivot_df["assignee"],
        y=pivot_df[STATUS_COMPLETED],
        name=STATUS_COMPLETED,
        marker_color="#4CAF50"
    ))

    # Update layout
    fig.update_layout(
        title="Assignee Workload by Task Status",
        xaxis_title="Assignee",
        yaxis_title="Number of Tasks",
        barmode="stack",
        height=500,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1
        }
    )

    return fig

def create_project_comparison_chart(project_details: List[Dict[str, Any]]) -> go.Figure:
    """
    Create a custom chart comparing projects by completion percentage and task count.

    Args:
        project_details: List of project details

    Returns:
        Plotly figure object
    """
    # Prepare data from project_details
    project_data = []

    for project in project_details:
        total_tasks = project.get("total_tasks", 0)
        completed_tasks = project.get("completed_tasks", 0)
        completion_pct = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

        project_data.append({
            "project": project["name"],
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_percentage": completion_pct,
            "overdue_tasks": project.get("overdue_tasks", 0)
        })

    # Convert to DataFrame
    df = pd.DataFrame(project_data)

    # Create bubble chart
    fig = px.scatter(
        df,
        x="completion_percentage",
        y="total_tasks",
        size="overdue_tasks",
        color="completion_percentage",
        color_continuous_scale=px.colors.sequential.Viridis,
        range_color=[0, 100],
        hover_name="project",
        size_max=50,
        text="project"
    )

    # Update layout
    fig.update_layout(
        title="Project Comparison: Completion vs. Size",
        xaxis_title="Completion Percentage",
        yaxis_title="Total Task Count",
        height=600,
        xaxis={
            "ticksuffix": "%",
            "range": [0, 105]
        }
    )

    # Update traces
    fig.update_traces(
        textposition="top center",
        marker={
            "line": {"width": 1, "color": "DarkSlateGrey"}
        }
    )

    return fig
