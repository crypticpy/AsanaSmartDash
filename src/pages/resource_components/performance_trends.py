"""
Performance Trends Component for Resource Allocation Page.

This module provides visualizations for team member performance trends over time,
including task completion velocity, acceleration/deceleration analysis, and performance benchmarks.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

def create_performance_trends(df: pd.DataFrame) -> None:
    """
    Create performance trend visualizations for team members.
    
    Args:
        df: DataFrame with task data
    """
    st.markdown("### Performance Trends")
    
    # Check if we have data
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    
    # Get team member filter from session state
    filters = st.session_state.get("resource_filters", {})
    selected_team_member = filters.get("team_member", "All Team Members")
    
    # Create performance trend visualization
    create_performance_trend_visualization(df, selected_team_member)
    
    # Create performance acceleration analysis
    create_performance_acceleration_analysis(df, selected_team_member)

def create_performance_trend_visualization(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create performance trend visualization for team members.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    
    # Filter for completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        st.info("No completed tasks available for trend analysis.")
        return
    
    # Filter for selected team member if specified
    if selected_team_member != "All Team Members":
        completed_tasks = completed_tasks[completed_tasks["assignee"] == selected_team_member]
        
        if completed_tasks.empty:
            st.info(f"No completed tasks available for {selected_team_member}.")
            return
    
    # Group by completion date and count tasks
    completed_tasks["completion_date"] = completed_tasks["completed_at"].dt.date
    
    # Get the date range
    min_date = completed_tasks["completion_date"].min()
    max_date = completed_tasks["completion_date"].max()
    
    # Create date range
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    # Create a DataFrame with all dates
    date_df = pd.DataFrame({"completion_date": date_range})
    date_df["completion_date"] = date_df["completion_date"].dt.date
    
    # Group by completion date and count tasks
    if selected_team_member != "All Team Members":
        # For a single team member
        task_counts = completed_tasks.groupby("completion_date").size().reset_index(name="count")
        
        # Merge with date range to fill in missing dates
        task_counts = pd.merge(date_df, task_counts, on="completion_date", how="left").fillna(0)
        
        # Calculate rolling average (7-day window)
        task_counts["rolling_avg"] = task_counts["count"].rolling(window=7, min_periods=1).mean()
        
        # Create visualization
        fig = go.Figure()
        
        # Add bar chart for daily counts
        fig.add_trace(
            go.Bar(
                x=task_counts["completion_date"],
                y=task_counts["count"],
                name="Daily Completed Tasks",
                marker_color="lightblue"
            )
        )
        
        # Add line chart for rolling average
        fig.add_trace(
            go.Scatter(
                x=task_counts["completion_date"],
                y=task_counts["rolling_avg"],
                name="7-Day Rolling Average",
                line=dict(color="darkblue", width=2)
            )
        )
        
        # Update layout
        fig.update_layout(
            title=f"Task Completion Trend for {selected_team_member}",
            xaxis_title="Date",
            yaxis_title="Number of Tasks Completed",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        # For all team members, show top 5
        top_members = completed_tasks["assignee"].value_counts().head(5).index.tolist()
        
        # Filter for top members
        top_member_tasks = completed_tasks[completed_tasks["assignee"].isin(top_members)]
        
        # Group by completion date and assignee
        task_counts = top_member_tasks.groupby(["completion_date", "assignee"]).size().reset_index(name="count")
        
        # Create a multi-line chart
        fig = px.line(
            task_counts,
            x="completion_date",
            y="count",
            color="assignee",
            title="Task Completion Trends by Team Member",
            labels={
                "completion_date": "Date",
                "count": "Number of Tasks Completed",
                "assignee": "Team Member"
            },
            height=400
        )
        
        # Update layout
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Tasks Completed",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)

def create_performance_acceleration_analysis(df: pd.DataFrame, selected_team_member: str) -> None:
    """
    Create performance acceleration analysis for team members.
    
    Args:
        df: DataFrame with task data
        selected_team_member: Selected team member from filters
    """
    # Ensure datetime columns are properly formatted
    if "completed_at" in df.columns:
        df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True)
    
    # Filter for completed tasks
    completed_tasks = df[df["status"] == "Completed"].copy()
    
    if completed_tasks.empty:
        st.info("No completed tasks available for acceleration analysis.")
        return
    
    # Calculate performance metrics for all team members
    performance_metrics = calculate_performance_metrics(completed_tasks)
    
    if not performance_metrics:
        st.info("Insufficient data for performance acceleration analysis.")
        return
    
    # Convert to DataFrame
    metrics_df = pd.DataFrame(performance_metrics)
    
    # Create visualization
    if selected_team_member != "All Team Members":
        # Filter for selected team member
        member_metrics = metrics_df[metrics_df["assignee"] == selected_team_member]
        
        if member_metrics.empty:
            st.info(f"No performance metrics available for {selected_team_member}.")
            return
        
        # Create a gauge chart for acceleration
        acceleration = member_metrics["acceleration"].iloc[0]
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=acceleration,
            title={"text": f"Performance Trend for {selected_team_member}"},
            delta={"reference": 0, "increasing": {"color": "green"}, "decreasing": {"color": "red"}},
            gauge={
                "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "darkblue"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [-100, -33], "color": "red"},
                    {"range": [-33, 33], "color": "yellow"},
                    {"range": [33, 100], "color": "green"}
                ]
            }
        ))
        
        # Update layout
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation
        trend_text = "accelerating" if acceleration > 0 else "decelerating" if acceleration < 0 else "maintaining steady performance"
        
        st.markdown(f"""
        **Performance Trend Analysis:**
        
        {selected_team_member} is **{trend_text}** in task completion rate.
        
        - **Recent Velocity**: {member_metrics["recent_velocity"].iloc[0]:.1f} tasks per week
        - **Historical Velocity**: {member_metrics["historical_velocity"].iloc[0]:.1f} tasks per week
        - **Change**: {acceleration:.1f}%
        """)
    else:
        # Show acceleration for all team members
        # Sort by acceleration
        metrics_df = metrics_df.sort_values("acceleration", ascending=False)
        
        # Create a bar chart
        fig = px.bar(
            metrics_df,
            x="assignee",
            y="acceleration",
            title="Performance Acceleration by Team Member",
            labels={
                "assignee": "Team Member",
                "acceleration": "Performance Acceleration (%)"
            },
            height=400,
            color="acceleration",
            color_continuous_scale="RdYlGn",
            range_color=[-100, 100]
        )
        
        # Add reference line at 0
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        # Update layout
        fig.update_layout(
            xaxis_title="Team Member",
            yaxis_title="Performance Acceleration (%)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add explanation
        with st.expander("Understanding Performance Acceleration"):
            st.markdown("""
            **Performance Acceleration:**
            
            This metric compares recent task completion velocity with historical velocity to determine if a team member is:
            
            - **Accelerating** (positive values): Completing tasks faster than their historical average
            - **Maintaining** (near zero): Consistent with their historical performance
            - **Decelerating** (negative values): Completing tasks slower than their historical average
            
            Each team member is measured against their own historical performance, not against other team members.
            This provides a fair assessment regardless of individual capacity differences.
            """)

def calculate_performance_metrics(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculate performance metrics for team members, including velocity and acceleration.
    
    Args:
        df: DataFrame with completed task data
        
    Returns:
        List of performance metrics by team member
    """
    performance_metrics = []
    
    # Get unique team members
    team_members = df["assignee"].unique()
    
    for member in team_members:
        # Filter for this team member
        member_df = df[df["assignee"] == member].copy()
        
        if len(member_df) < 5:  # Skip if too few tasks
            continue
        
        # Sort by completion date
        member_df = member_df.sort_values("completed_at")
        
        # Calculate recent and historical velocity
        recent_velocity, historical_velocity = calculate_velocity(member_df)
        
        # Calculate acceleration (percentage change)
        if historical_velocity > 0:
            acceleration = ((recent_velocity - historical_velocity) / historical_velocity) * 100
        else:
            acceleration = 0 if recent_velocity == 0 else 100
        
        # Cap acceleration at +/- 100%
        acceleration = max(min(acceleration, 100), -100)
        
        performance_metrics.append({
            "assignee": member,
            "recent_velocity": recent_velocity,
            "historical_velocity": historical_velocity,
            "acceleration": acceleration
        })
    
    return performance_metrics

def calculate_velocity(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Calculate recent and historical velocity for a team member.
    
    Args:
        df: DataFrame with completed task data for a single team member
        
    Returns:
        Tuple of (recent_velocity, historical_velocity)
    """
    # Get the date range
    min_date = df["completed_at"].min()
    max_date = df["completed_at"].max()
    
    # Calculate the midpoint
    midpoint = min_date + (max_date - min_date) / 2
    
    # Split into recent and historical
    recent_df = df[df["completed_at"] >= midpoint]
    historical_df = df[df["completed_at"] < midpoint]
    
    # Calculate velocity (tasks per week)
    recent_velocity = calculate_weekly_velocity(recent_df)
    historical_velocity = calculate_weekly_velocity(historical_df)
    
    return recent_velocity, historical_velocity

def calculate_weekly_velocity(df: pd.DataFrame) -> float:
    """
    Calculate weekly velocity for a set of tasks.
    
    Args:
        df: DataFrame with completed task data
        
    Returns:
        Weekly velocity (tasks per week)
    """
    if df.empty:
        return 0
    
    # Get the date range
    min_date = df["completed_at"].min()
    max_date = df["completed_at"].max()
    
    # Calculate the number of weeks
    days = (max_date - min_date).total_seconds() / (24 * 60 * 60)
    weeks = max(days / 7, 1)  # Ensure at least 1 week to avoid division by zero
    
    # Calculate velocity
    velocity = len(df) / weeks
    
    return velocity 