"""
API wrapper for the Asana Chat Assistant.

This module provides a safe wrapper around the Asana API functions
with rate limiting and caching.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import asana
import pandas as pd

logger = logging.getLogger("asana_chat_assistant")

class AsanaAPIWrapper:
    """
    Safe wrapper around Asana API functions with rate limiting and caching.
    """
    
    def __init__(self, api_instances: Dict[str, Any]):
        """
        Initialize the API wrapper with Asana API instances.
        
        Args:
            api_instances: Dictionary of Asana API instances
        """
        self.api_instances = api_instances
        
        # Cache settings
        self.cache = {}
        self.cache_expiry = {}
        self.default_ttl = 300  # 5 minutes
        
        # Rate limiting settings
        self.last_call_time = 0
        self.min_call_interval = 1  # 1 second between calls
        
        logger.info("AsanaAPIWrapper initialized successfully")
    
    def _apply_rate_limit(self):
        """Apply rate limiting to API calls."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and is not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if cache_key in self.cache and cache_key in self.cache_expiry and datetime.now() < self.cache_expiry[cache_key]:
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        logger.debug(f"Cache miss for {cache_key}")
        return None
    
    def _store_in_cache(self, cache_key: str, value: Any, ttl: Optional[int] = None):
        """
        Store a value in the cache with expiry.
        
        Args:
            cache_key: Cache key
            value: Value to store
            ttl: Time to live in seconds (default: self.default_ttl)
        """
        ttl = ttl or self.default_ttl
        self.cache[cache_key] = value
        self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=ttl)
        logger.debug(f"Stored {cache_key} in cache with TTL {ttl} seconds")
    
    def get_project(self, project_gid: str, ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        Get project details with caching.
        
        Args:
            project_gid: Project GID
            ttl: Cache TTL in seconds (optional)
            
        Returns:
            Project details
        """
        cache_key = f"project_{project_gid}"
        cached_value = self._get_from_cache(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            # Make API call
            opts = {
                'opt_fields': 'name,due_on,owner.name,members,html_notes,completed,created_at,modified_at,public,workspace.name,custom_fields'
            }
            project = self.api_instances["_projects_api"].get_project(project_gid, opts=opts)
            
            # Cache result
            self._store_in_cache(cache_key, project, ttl)
            return project
            
        except Exception as e:
            logger.error(f"Error getting project {project_gid}: {e}")
            raise
    
    def get_tasks_for_project(self, project_gid: str, ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get tasks for a project with caching.
        
        Args:
            project_gid: Project GID
            ttl: Cache TTL in seconds (optional)
            
        Returns:
            List of tasks
        """
        cache_key = f"tasks_for_project_{project_gid}"
        cached_value = self._get_from_cache(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            # Make API call
            opts = {
                'opt_fields': 'name,completed,due_on,created_at,completed_at,assignee.name,memberships.section.name,custom_fields,tags,num_subtasks',
            }
            tasks = list(self.api_instances["_tasks_api"].get_tasks_for_project(project_gid, opts=opts))
            
            # Cache result
            self._store_in_cache(cache_key, tasks, ttl)
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks for project {project_gid}: {e}")
            raise
    
    def get_portfolio_projects(self, portfolio_gid: str, ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get projects in a portfolio with caching.
        
        Args:
            portfolio_gid: Portfolio GID
            ttl: Cache TTL in seconds (optional)
            
        Returns:
            List of projects
        """
        cache_key = f"portfolio_projects_{portfolio_gid}"
        cached_value = self._get_from_cache(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            # Make API call
            opts = {
                'opt_fields': 'name,gid',
            }
            projects = list(self.api_instances["_portfolios_api"].get_items_for_portfolio(portfolio_gid, opts=opts))
            
            # Cache result
            self._store_in_cache(cache_key, projects, ttl)
            return projects
            
        except Exception as e:
            logger.error(f"Error getting projects for portfolio {portfolio_gid}: {e}")
            raise
    
    def get_sections_for_project(self, project_gid: str, ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get sections in a project with caching.
        
        Args:
            project_gid: Project GID
            ttl: Cache TTL in seconds (optional)
            
        Returns:
            List of sections
        """
        cache_key = f"sections_for_project_{project_gid}"
        cached_value = self._get_from_cache(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            # Make API call
            opts = {
                'opt_fields': 'name',
            }
            sections = list(self.api_instances["_sections_api"].get_sections_for_project(project_gid, opts=opts))
            
            # Cache result
            self._store_in_cache(cache_key, sections, ttl)
            return sections
            
        except Exception as e:
            logger.error(f"Error getting sections for project {project_gid}: {e}")
            raise
    
    def refresh_project_data(self, project_gid: str) -> Dict[str, Any]:
        """
        Refresh project data by clearing cache and fetching fresh data.
        
        Args:
            project_gid: Project GID
            
        Returns:
            Fresh project data
        """
        # Clear cache entries
        project_key = f"project_{project_gid}"
        tasks_key = f"tasks_for_project_{project_gid}"
        sections_key = f"sections_for_project_{project_gid}"
        
        for key in [project_key, tasks_key, sections_key]:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]
        
        # Fetch fresh data
        project = self.get_project(project_gid, ttl=60)  # Short TTL
        tasks = self.get_tasks_for_project(project_gid, ttl=60)  # Short TTL
        
        return {
            "project": project,
            "tasks": tasks
        }
    
    def _safe_get(self, data, *keys):
        """
        Safely get nested values from a dictionary.
        
        Args:
            data: Dictionary to extract from
            *keys: Keys to traverse
            
        Returns:
            Value or None if not found
        """
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        return data
    
    def _extract_task_basic_data(self, task, project_name, project_gid):
        """
        Extract basic task data into a dictionary.
        
        Args:
            task: Task data from Asana API
            project_name: Name of the project
            project_gid: GID of the project
            
        Returns:
            Dictionary with basic task data
        """
        return {
            'project': project_name,
            'project_gid': project_gid,
            'name': self._safe_get(task, 'name'),
            'status': 'Completed' if self._safe_get(task, 'completed') else 'In Progress',
            'due_date': self._safe_get(task, 'due_on'),
            'created_at': self._safe_get(task, 'created_at'),
            'completed_at': self._safe_get(task, 'completed_at'),
            'assignee': self._safe_get(task, 'assignee', 'name') or 'Unassigned',
            'section': self._safe_get(task, 'memberships', 0, 'section', 'name') or 'No section',
            'tags': [tag['name'] for tag in self._safe_get(task, 'tags') or []],
            'num_subtasks': self._safe_get(task, 'num_subtasks') or 0,
        }
    
    def _process_custom_fields(self, task, task_data):
        """
        Process custom fields from a task and add them to task_data.
        
        Args:
            task: Task data from Asana API
            task_data: Dictionary to add custom fields to
            
        Returns:
            Updated task_data dictionary
        """
        custom_fields = self._safe_get(task, 'custom_fields') or []
        for field in custom_fields:
            if field_name := self._safe_get(field, 'name'):
                task_data[f"custom_{field_name}"] = self._safe_get(field, 'display_value')
        return task_data
    
    def process_tasks_to_dataframe(self, tasks: List[Dict[str, Any]], project_name: str, project_gid: str) -> pd.DataFrame:
        """
        Process tasks from Asana API into a pandas DataFrame.
        
        Args:
            tasks: List of tasks from Asana API
            project_name: Name of the project
            project_gid: GID of the project
            
        Returns:
            DataFrame with processed tasks
        """
        processed_tasks = []
        
        for task in tasks:
            # Extract basic task data
            task_data = self._extract_task_basic_data(task, project_name, project_gid)
            
            # Process custom fields
            task_data = self._process_custom_fields(task, task_data)
            
            processed_tasks.append(task_data)
        
        return pd.DataFrame(processed_tasks) 