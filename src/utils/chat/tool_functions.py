"""
Tool functions for the Asana Chat Assistant.

This module provides a set of tool functions that the chat assistant can call
to get specific data about projects and tasks.
"""
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger("asana_chat_assistant")

class AsanaToolFunctions:
    """
    Tool functions for retrieving specific data about Asana projects and tasks.
    """
    
    def __init__(
        self, 
        project_df: pd.DataFrame, 
        task_df: pd.DataFrame, 
        project_details: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the tool functions with project and task data.
        
        Args:
            project_df: DataFrame containing project data with completion estimates
            task_df: DataFrame containing task data
            project_details: List of detailed project information (optional)
        """
        self.project_df = project_df
        self.task_df = task_df
        self.project_details = project_details or []
        logger.info("AsanaToolFunctions initialized successfully")
    
    def get_project_count(self) -> Dict[str, Any]:
        """
        Get the total number of projects and active projects.
        
        Returns:
            Dictionary with project count information
        """
        total_count = len(self.project_df)
        active_count = len(self.project_df[
            ~self.project_df['project'].isin(['Completed', 'Archived', 'Canceled'])
        ])
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "result": f"There are {total_count} total projects, with {active_count} active projects."
        }
    
    def get_project_by_name(self, project_name: str) -> Dict[str, Any]:
        """
        Get details about a specific project by name.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary with project details or error message
        """
        # First check project_df
        project = self.project_df[self.project_df['project'] == project_name]

        if len(project) == 0:
            return {
                "error": f"Project '{project_name}' not found.",
                "result": f"Project '{project_name}' not found."
            }

        project_row = project.iloc[0]
        result = {
            "name": project_row['project'],
            "result": f"Project: {project_row['project']}\n"
        }

        # Add basic project details
        self._add_project_dates(result, project_row)
        self._add_schedule_status(result, project_row)

        if project_detail := next(
            (p for p in self.project_details if p.get('name') == project_name),
            None,
        ):
            self._add_project_metadata(result, project_detail)

        return result
    
    def _add_project_dates(self, result: Dict[str, Any], project_row: pd.Series) -> None:
        """Add date information to project result."""
        # Add estimated completion date if available
        if 'estimated_completion_date' in project_row and pd.notna(project_row['estimated_completion_date']):
            est_date = project_row['estimated_completion_date'].strftime('%Y-%m-%d')
            result["estimated_completion_date"] = est_date
            result["result"] += f"Estimated completion date: {est_date}\n"
        
        # Add project due date if available
        if 'project_due_date' in project_row and pd.notna(project_row['project_due_date']):
            due_date = project_row['project_due_date'].strftime('%Y-%m-%d')
            result["due_date"] = due_date
            result["result"] += f"Due date: {due_date}\n"
    
    def _add_schedule_status(self, result: Dict[str, Any], project_row: pd.Series) -> None:
        """Add schedule status information to project result."""
        if 'days_difference' not in project_row or pd.isna(project_row['days_difference']):
            return
            
        days_diff = project_row['days_difference']
        result["days_difference"] = days_diff
        
        if days_diff > 0:
            result["result"] += f"Project is {days_diff} days behind schedule.\n"
        elif days_diff < 0:
            result["result"] += f"Project is {abs(days_diff)} days ahead of schedule.\n"
        else:
            result["result"] += "Project is on schedule.\n"
    
    def _add_project_metadata(self, result: Dict[str, Any], project_detail: Dict[str, Any]) -> None:
        """Add metadata from project_details to result."""
        # Add owner if available
        if 'owner' in project_detail:
            result["owner"] = project_detail['owner']
            result["result"] += f"Owner: {project_detail['owner']}\n"
        
        # Add progress information
        self._add_progress_info(result, project_detail)
        
        # Add overdue tasks if available
        if 'overdue_tasks' in project_detail:
            result["overdue_tasks"] = project_detail['overdue_tasks']
            result["result"] += f"Overdue tasks: {project_detail['overdue_tasks']}\n"
    
    def _add_progress_info(self, result: Dict[str, Any], project_detail: Dict[str, Any]) -> None:
        """Add progress information to project result."""
        if 'total_tasks' not in project_detail or 'completed_tasks' not in project_detail:
            return
            
        total = project_detail['total_tasks']
        completed = project_detail['completed_tasks']
        result["total_tasks"] = total
        result["completed_tasks"] = completed
        
        if total <= 0:
            return
            
        percentage = (completed / total) * 100
        result["completion_percentage"] = percentage
        result["result"] += f"Progress: {percentage:.1f}% ({completed}/{total} tasks completed)\n"
    
    def get_tasks_by_assignee(self, assignee: str) -> Dict[str, Any]:
        """
        Get tasks assigned to a specific person.
        
        Args:
            assignee: Name of the assignee
            
        Returns:
            Dictionary with task information
        """
        # Filter tasks by assignee
        tasks = self.task_df[self.task_df['assignee'] == assignee]
        
        if len(tasks) == 0:
            return {
                "error": f"No tasks found for assignee '{assignee}'.",
                "result": f"No tasks found for assignee '{assignee}'."
            }
        
        # Count tasks by status
        completed_count = len(tasks[tasks['status'] == 'Completed'])
        in_progress_count = len(tasks[tasks['status'] == 'In Progress'])
        
        # Get projects the assignee is working on
        projects = tasks['project'].unique()
        
        result = {
            "assignee": assignee,
            "total_tasks": len(tasks),
            "completed_tasks": completed_count,
            "in_progress_tasks": in_progress_count,
            "projects": list(projects),
            "result": f"Assignee: {assignee}\n"
                     f"Total tasks: {len(tasks)}\n"
                     f"Completed tasks: {completed_count}\n"
                     f"In progress tasks: {in_progress_count}\n"
                     f"Working on projects: {', '.join(projects)}\n"
        }
        
        # Add recent tasks (up to 5)
        recent_tasks = tasks.sort_values('created_at', ascending=False).head(5)
        if not recent_tasks.empty:
            task_list = []
            for _, task in recent_tasks.iterrows():
                task_info = f"{task['name']} ({task['project']}) - {task['status']}"
                task_list.append(task_info)
            
            result["recent_tasks"] = task_list
            result["result"] += "\nRecent tasks:\n- " + "\n- ".join(task_list)
        
        return result
    
    def get_overdue_tasks(self) -> Dict[str, Any]:
        """
        Get all overdue tasks.
        
        Returns:
            Dictionary with overdue task information
        """
        # Get current date
        today = pd.Timestamp.now().normalize()
        
        # Filter tasks that are not completed and have a due date in the past
        overdue_tasks = self.task_df[
            (self.task_df['status'] != 'Completed') & 
            (self.task_df['due_date'] < today) &
            (pd.notna(self.task_df['due_date']))
        ]
        
        if len(overdue_tasks) == 0:
            return {
                "count": 0,
                "result": "No overdue tasks found."
            }
        
        # Group by project
        project_counts = overdue_tasks.groupby('project').size().to_dict()
        
        # Group by assignee
        assignee_counts = overdue_tasks.groupby('assignee').size().to_dict()
        
        result = {
            "count": len(overdue_tasks),
            "by_project": project_counts,
            "by_assignee": assignee_counts,
            "result": f"Found {len(overdue_tasks)} overdue tasks.\n\n"
        }
        
        # Add project breakdown
        result["result"] += "Breakdown by project:\n"
        for project, count in project_counts.items():
            result["result"] += f"- {project}: {count} tasks\n"
        
        # Add assignee breakdown
        result["result"] += "\nBreakdown by assignee:\n"
        for assignee, count in assignee_counts.items():
            result["result"] += f"- {assignee}: {count} tasks\n"
        
        return result
    
    def get_task_status_distribution(self) -> Dict[str, Any]:
        """
        Get the distribution of tasks by status.
        
        Returns:
            Dictionary with task status distribution
        """
        # Count tasks by status
        status_counts = self.task_df['status'].value_counts().to_dict()
        
        # Calculate percentages
        total_tasks = len(self.task_df)
        status_percentages = {}
        
        for status, count in status_counts.items():
            percentage = (count / total_tasks) * 100 if total_tasks > 0 else 0
            status_percentages[status] = round(percentage, 1)
        
        result = {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "status_percentages": status_percentages,
            "result": f"Task Status Distribution (Total: {total_tasks} tasks):\n"
        }
        
        # Add status breakdown
        for status, count in status_counts.items():
            percentage = status_percentages[status]
            result["result"] += f"- {status}: {count} tasks ({percentage}%)\n"
        
        return result
    
    def get_project_progress(self) -> Dict[str, Any]:
        """
        Get progress information for all projects.
        
        Returns:
            Dictionary with project progress information
        """
        if not self.project_details:
            return {
                "error": "No detailed project information available.",
                "result": "No detailed project information available."
            }
        
        result = {
            "projects": [],
            "result": "Project Progress:\n"
        }
        
        for project in self.project_details:
            project_name = project.get('name', 'Unknown')
            total_tasks = project.get('total_tasks', 0)
            completed_tasks = project.get('completed_tasks', 0)
            
            if total_tasks > 0:
                percentage = (completed_tasks / total_tasks) * 100
                
                # Determine status
                if percentage >= 90:
                    status = "Almost Complete"
                elif percentage >= 75:
                    status = "On Track"
                elif percentage >= 50:
                    status = "In Progress"
                elif percentage >= 25:
                    status = "Started"
                else:
                    status = "Just Beginning"
                
                project_info = {
                    "name": project_name,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "percentage": round(percentage, 1),
                    "status": status
                }
                
                result["projects"].append(project_info)
                result["result"] += f"- {project_name}: {percentage:.1f}% complete ({completed_tasks}/{total_tasks} tasks) - {status}\n"
            else:
                project_info = {
                    "name": project_name,
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "percentage": 0,
                    "status": "No Tasks"
                }
                
                result["projects"].append(project_info)
                result["result"] += f"- {project_name}: No tasks available\n"
        
        return result 