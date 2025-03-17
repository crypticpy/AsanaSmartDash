"""
Data context manager for the Asana Chat Assistant.

This module provides a centralized data context manager that maintains
up-to-date information about projects and tasks for the chat assistant.
"""
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("asana_chat_assistant")

class DataContextManager:
    """
    Manages data context for the chat assistant, providing up-to-date
    information and summary statistics about projects and tasks.
    """
    
    def __init__(
        self, 
        project_df: pd.DataFrame, 
        task_df: pd.DataFrame, 
        project_details: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the data context manager with project and task data.
        
        Args:
            project_df: DataFrame containing project data with completion estimates
            task_df: DataFrame containing task data
            project_details: List of detailed project information (optional)
        """
        self.project_df = project_df
        self.task_df = task_df
        self.project_details = project_details or []
        
        # Cache for computed statistics
        self._cache = {}
        self._cache_expiry = {}
        self._default_ttl = 300  # 5 minutes
        
        # Initialize cache with basic statistics
        self._update_basic_stats()
        
        logger.info("DataContextManager initialized successfully")
    
    def _update_basic_stats(self):
        """Update basic statistics in the cache."""
        # Project statistics
        self._cache["project_count"] = len(self.project_df)
        self._cache["active_project_count"] = len(self.project_df[
            ~self.project_df['project'].isin(['Completed', 'Archived', 'Canceled'])
        ])
        
        # Task statistics
        self._cache["task_count"] = len(self.task_df)
        self._cache["completed_task_count"] = len(self.task_df[
            self.task_df['status'] == 'Completed'
        ])
        self._cache["in_progress_task_count"] = len(self.task_df[
            self.task_df['status'] == 'In Progress'
        ])
        
        # Assignee statistics
        self._cache["assignee_count"] = self.task_df['assignee'].nunique()
        
        # Set expiry for all basic stats
        now = datetime.now()
        for key in self._cache:
            self._cache_expiry[key] = now + timedelta(seconds=self._default_ttl)
    
    def get_stat(self, key: str, default=None):
        """
        Get a statistic from the cache, updating if expired.
        
        Args:
            key: The statistic key
            default: Default value if key not found
            
        Returns:
            The statistic value or default
        """
        now = datetime.now()
        
        # Check if key exists and is not expired
        if key in self._cache and key in self._cache_expiry and now < self._cache_expiry[key]:
            return self._cache[key]
        
        # If expired or not in cache, update basic stats
        self._update_basic_stats()
        return self._cache.get(key, default)
    
    def get_context_summary(self) -> str:
        """
        Get a summary of the current data context.
        
        Returns:
            String with context summary
        """
        summary = []
        
        # Project summary
        project_count = self.get_stat("project_count")
        active_project_count = self.get_stat("active_project_count")
        summary.append(f"There are {project_count} total projects, with {active_project_count} active projects.")
        
        # Task summary
        task_count = self.get_stat("task_count")
        completed_task_count = self.get_stat("completed_task_count")
        in_progress_task_count = self.get_stat("in_progress_task_count")
        completion_pct = (completed_task_count / task_count * 100) if task_count > 0 else 0
        
        summary.append(f"There are {task_count} total tasks: {completed_task_count} completed ({completion_pct:.1f}%) and {in_progress_task_count} in progress.")
        
        # Assignee summary
        assignee_count = self.get_stat("assignee_count")
        summary.append(f"Tasks are assigned to {assignee_count} team members.")
        
        return " ".join(summary)
    
    def get_query_specific_context(self, query: str) -> str:
        """
        Get context specific to a query.
        
        Args:
            query: The user query
            
        Returns:
            String with query-specific context
        """
        query_lower = query.lower()
        context_parts = []
        
        # Add project-specific context
        if any(keyword in query_lower for keyword in ["project", "projects", "portfolio"]):
            context_parts.append(self._get_project_context(query_lower))
        
        # Add task-specific context
        if any(keyword in query_lower for keyword in ["task", "tasks", "todo", "to-do", "to do"]):
            context_parts.append(self._get_task_context(query_lower))
        
        # Add assignee-specific context
        if any(keyword in query_lower for keyword in ["assignee", "assigned", "team member", "who"]):
            context_parts.append(self._get_assignee_context(query_lower))
        
        # Return specific context if available, otherwise return general summary
        return " ".join(context_parts) if context_parts else self.get_context_summary()
    
    def _get_project_context(self, query_lower: str) -> str:
        """Get project-specific context based on the query."""
        context = f"There are {self.get_stat('project_count')} total projects and {self.get_stat('active_project_count')} active projects."
        
        # Check for specific project mentions
        for _, row in self.project_df.iterrows():
            project_name = row['project'].lower()
            if project_name in query_lower:
                context += self._format_project_details(row)
                break
        
        return context
    
    def _format_project_details(self, project_row) -> str:
        """Format project details into a string."""
        details = f" Project '{project_row['project']}' "
        
        if 'estimated_completion_date' in project_row and pd.notna(project_row['estimated_completion_date']):
            details += f"has an estimated completion date of {project_row['estimated_completion_date'].strftime('%Y-%m-%d')}."
        
        if 'days_difference' in project_row and pd.notna(project_row['days_difference']):
            days = project_row['days_difference']
            if days > 0:
                details += f" It is {days} days behind schedule."
            elif days < 0:
                details += f" It is {abs(days)} days ahead of schedule."
            else:
                details += " It is on schedule."
        
        return details
    
    def _get_task_context(self, query_lower: str) -> str:
        """
        Get task-specific context based on the query.
        
        Args:
            query_lower: Lowercase user query
            
        Returns:
            Task-specific context string
        """
        task_count = self.get_stat("task_count")
        completed_count = self.get_stat("completed_task_count")
        in_progress_count = self.get_stat("in_progress_task_count")
        
        completion_pct = (completed_count / task_count * 100) if task_count > 0 else 0
        
        context = f"There are {task_count} total tasks: {completed_count} completed ({completion_pct:.1f}%) and {in_progress_count} in progress."
        
        # Add overdue tasks context if relevant
        if any(term in query_lower for term in ["overdue", "late", "behind", "delayed"]):
            context += self._get_overdue_tasks_context()
        
        # Add specific task context if mentioned
        context += self._get_specific_task_context(query_lower)
        
        return context
    
    def _get_overdue_tasks_context(self) -> str:
        """Get context about overdue tasks."""
        overdue_tasks = self.task_df[
            (self.task_df['status'] != 'Completed') & 
            (pd.notna(self.task_df['due_date'])) & 
            (pd.to_datetime(self.task_df['due_date']) < pd.Timestamp.now())
        ]
        
        if overdue_tasks.empty:
            return ""
            
        context = f" There are {len(overdue_tasks)} overdue tasks."
        if len(overdue_tasks) <= 3:
            task_names = ", ".join([f"'{task}'" for task in overdue_tasks['name'].head(3)])
            context += f" Overdue tasks include: {task_names}."
        
        return context
    
    def _get_specific_task_context(self, query_lower: str) -> str:
        """Get context for a specific task mentioned in the query."""
        for _, task in self.task_df.iterrows():
            task_name = str(task.get('name', '')).lower()
            if task_name and task_name in query_lower:
                context = f" Task '{task['name']}' is {task['status']}."
                if task['status'] != 'Completed' and pd.notna(task.get('due_date')):
                    context += f" It is due on {task['due_date']}."
                if pd.notna(task.get('assignee')):
                    context += f" It is assigned to {task['assignee']}."
                return context
        
        return ""
    
    def _get_assignee_context(self, query_lower: str) -> str:
        """
        Get assignee-specific context based on the query.
        
        Args:
            query_lower: Lowercase user query
            
        Returns:
            Assignee-specific context string
        """
        assignee_count = self.get_stat("assignee_count")
        context = f"Tasks are assigned to {assignee_count} team members."
        
        # Add top assignees information
        context += self._get_top_assignees_context()
        
        # Add specific assignee information if mentioned
        context += self._get_specific_assignee_context(query_lower)
        
        return context
    
    def _get_top_assignees_context(self) -> str:
        """Get context about top assignees by task count."""
        if self.task_df.empty:
            return ""
            
        assignee_counts = self.task_df['assignee'].value_counts().head(3)
        if assignee_counts.empty:
            return ""
            
        top_assignees = ", ".join([f"{name} ({count} tasks)" for name, count in assignee_counts.items()])
        return f" Top assignees are: {top_assignees}."
    
    def _get_specific_assignee_context(self, query_lower: str) -> str:
        """Get context for a specific assignee mentioned in the query."""
        if self.task_df.empty:
            return ""
            
        for assignee in self.task_df['assignee'].unique():
            if not assignee or str(assignee).lower() not in query_lower:
                continue
                
            assignee_tasks = self.task_df[self.task_df['assignee'] == assignee]
            total = len(assignee_tasks)
            completed = len(assignee_tasks[assignee_tasks['status'] == 'Completed'])
            in_progress = total - completed
            
            context = f" {assignee} has {total} tasks: {completed} completed and {in_progress} in progress."
            
            # Add upcoming tasks information
            context += self._get_upcoming_tasks_context(assignee_tasks)
            
            return context
            
        return ""
    
    def _get_upcoming_tasks_context(self, assignee_tasks: pd.DataFrame) -> str:
        """Get context about upcoming tasks for an assignee."""
        upcoming_tasks = assignee_tasks[
            (assignee_tasks['status'] != 'Completed') & 
            (pd.notna(assignee_tasks['due_date']))
        ].sort_values('due_date').head(2)
        
        if upcoming_tasks.empty:
            return ""
            
        task_details = []
        for _, task in upcoming_tasks.iterrows():
            due_date = pd.to_datetime(task['due_date']).strftime('%Y-%m-%d')
            task_details.append(f"'{task['name']}' (due {due_date})")
        
        task_list = ", ".join(task_details)
        return f" Upcoming tasks: {task_list}." 