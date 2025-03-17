"""
Project Allocation Component for Resource Allocation Page.

This module provides visualizations and metrics for project resource allocation,
including team allocation, task distribution, and resource utilization by project.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime, timedelta

def create_project_allocation_metrics(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create project allocation metrics and visualizations.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    st.markdown("### Project Resource Allocation")
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Create project resource allocation visualization
    create_project_resource_allocation(df)
    
    # Create project health indicators
    create_project_health_indicators(df, project_details)

def create_project_resource_allocation(df: pd.DataFrame) -> None:
    """
    Create resource allocation visualization by project.
    
    Args:
        df: DataFrame with task data
    """
    # Get project filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_project = filters.get("project", "All Projects")
    
    # If a specific project is selected, show team allocation for that project
    if selected_project != "All Projects":
        # Filter for the selected project
        project_df = df[df["project"] == selected_project]
        
        # Get team member counts
        team_member_counts = project_df.groupby("assignee").size().reset_index(name="count")
        team_member_counts.columns = ["Team Member", "Task Count"]
        
        # Sort by task count
        team_member_counts = team_member_counts.sort_values("Task Count", ascending=False)
        
        # Create visualization
        if not team_member_counts.empty:
            fig = px.bar(
                team_member_counts,
                x="Team Member",
                y="Task Count",
                title=f"Team Allocation for {selected_project}",
                height=400,
                color="Task Count",
                color_continuous_scale="Viridis"
            )
            
            # Update layout
            fig.update_layout(
                xaxis_title="Team Member",
                yaxis_title="Number of Tasks"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No team allocation data available for {selected_project}.")
    else:
        # Show resource allocation across all projects
        # Group by project and assignee
        project_allocation = df.groupby(["project", "assignee"]).size().reset_index(name="count")
        
        # Create visualization
        if not project_allocation.empty:
            fig = px.sunburst(
                project_allocation,
                path=["project", "assignee"],
                values="count",
                title="Resource Allocation by Project",
                height=500
            )
            
            # Update layout
            fig.update_layout(
                margin=dict(t=30, b=30, l=30, r=30)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No resource allocation data available.")

def create_project_health_indicators(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> None:
    """
    Create project health indicators based on resource allocation and task completion.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
    """
    # Calculate project health metrics
    project_health = calculate_project_health(df, project_details)
    
    # Create visualization
    if project_health:
        # Convert to DataFrame
        health_df = pd.DataFrame(project_health)
        
        # Create visualization
        fig = px.scatter(
            health_df,
            x="resource_allocation",
            y="completion_rate",
            size="total_tasks",
            color="health_score",
            hover_name="project",
            title="Project Health by Resource Allocation",
            labels={
                "resource_allocation": "Resource Allocation Score",
                "completion_rate": "Task Completion Rate (%)",
                "health_score": "Health Score"
            },
            height=500,
            color_continuous_scale="RdYlGn",
            range_color=[0, 100]
        )
        
        # Add reference lines
        fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Update layout
        fig.update_layout(
            xaxis_title="Resource Allocation Score (higher = better allocated)",
            yaxis_title="Task Completion Rate (%)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation
        with st.expander("Understanding Project Health Indicators"):
            st.markdown("""
            **Project Health Indicators:**
            
            - **Resource Allocation Score**: Measures how well resources are allocated to the project. 
              Higher scores indicate better allocation (balanced workload among team members).
            
            - **Task Completion Rate**: Percentage of tasks completed in the project.
            
            - **Health Score**: Overall health score based on resource allocation and task completion.
              - 0-33: Needs attention (red)
              - 34-66: Moderate (yellow)
              - 67-100: Good (green)
            
            - **Bubble Size**: Represents the total number of tasks in the project.
            
            **Potential Issues:**
            
            - **Low Allocation, Low Completion**: Project may be under-resourced.
            - **High Allocation, Low Completion**: Resources may be overallocated or ineffective.
            - **Low Allocation, High Completion**: Project may be efficiently resourced but at risk.
            """)
    else:
        st.info("No project health data available.")

def calculate_project_health(df: pd.DataFrame, project_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate project health metrics based on resource allocation and task completion.
    
    Args:
        df: DataFrame with task data
        project_details: List of detailed project information
        
    Returns:
        List of project health metrics
    """
    project_health = []
    
    for project in project_details:
        project_name = project.get("name")
        
        # Filter for this project
        project_df = df[df["project"] == project_name]
        
        if not project_df.empty:
            # Calculate metrics
            total_tasks = len(project_df)
            completed_tasks = project_df[project_df["status"] == "Completed"].shape[0]
            completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            
            # Calculate resource allocation score
            team_members = project_df["assignee"].nunique()
            tasks_per_member = total_tasks / team_members if team_members > 0 else 0
            
            # Calculate standard deviation of tasks per member (lower is better)
            tasks_per_member_std = project_df.groupby("assignee").size().std()
            tasks_per_member_std = tasks_per_member_std if not pd.isna(tasks_per_member_std) else 0
            
            # Calculate resource allocation score (0-100)
            # Lower standard deviation means more balanced allocation
            max_std = 10  # Maximum expected standard deviation
            resource_allocation = max(0, 100 - (tasks_per_member_std / max_std * 100))
            
            # Calculate health score (0-100)
            health_score = (completion_rate + resource_allocation) / 2
            
            project_health.append({
                "project": project_name,
                "total_tasks": total_tasks,
                "completion_rate": completion_rate,
                "resource_allocation": resource_allocation,
                "health_score": health_score,
                "team_members": team_members,
                "tasks_per_member": tasks_per_member
            })
    
    return project_health 