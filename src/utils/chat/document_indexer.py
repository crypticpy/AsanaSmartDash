"""
Document indexer for the Asana Chat Assistant.

This module handles the creation of documents and indices from Asana data
for use with LlamaIndex.
"""
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
import openai

from llama_index.core import VectorStoreIndex, Document
from llama_index.embeddings.openai import OpenAIEmbedding

logger = logging.getLogger("asana_chat_assistant")

def _create_project_text(row, project_detail):
    """Create text representation of a project."""
    text = f"Project: {row['project']}\n"
    
    # Add estimated completion date if available
    if 'estimated_completion_date' in row and pd.notna(row['estimated_completion_date']):
        text += f"Estimated completion date: {row['estimated_completion_date'].strftime('%Y-%m-%d')}\n"
    
    # Add project due date if available
    if 'project_due_date' in row and pd.notna(row['project_due_date']):
        text += f"Due date: {row['project_due_date'].strftime('%Y-%m-%d')}\n"
    
    # Add remaining tasks info
    if 'remaining_tasks' in row:
        text += f"Remaining tasks: {row['remaining_tasks']}\n"
    
    # Add completion status
    if 'days_difference' in row and pd.notna(row['days_difference']):
        if row['days_difference'] > 0:
            text += f"Project is {row['days_difference']} days behind schedule.\n"
        else:
            text += f"Project is {abs(row['days_difference'])} days ahead of schedule.\n"
    
    text += _add_project_detail_text(project_detail)
    
    return text

def _add_project_detail_text(project_detail):
    """Add text from project details."""
    if not project_detail:
        return ""
    
    text = ""
    if 'owner' in project_detail:
        text += f"Owner: {project_detail['owner']}\n"
    
    if 'members_count' in project_detail:
        text += f"Team members: {project_detail['members_count']}\n"
    
    if 'total_tasks' in project_detail and 'completed_tasks' in project_detail:
        completion_pct = (project_detail['completed_tasks'] / project_detail['total_tasks']) * 100 if project_detail['total_tasks'] > 0 else 0
        text += f"Progress: {completion_pct:.1f}% ({project_detail['completed_tasks']} of {project_detail['total_tasks']} tasks completed)\n"
    
    if 'overdue_tasks' in project_detail:
        text += f"Overdue tasks: {project_detail['overdue_tasks']}\n"
    
    return text

def _process_metadata_value(v):
    """Process a single metadata value, handling special types."""
    if pd.isna(v):
        return None
    elif isinstance(v, (pd.Timestamp, pd.Timedelta)):
        return str(v)
    return v

def _create_metadata_dict(data_dict, additional_dict=None):
    """Create metadata dictionary from a data dictionary, handling special types."""
    metadata = {k: _process_metadata_value(v) for k, v in data_dict.items()}
    
    # Add additional metadata if provided
    if additional_dict:
        for k, v in additional_dict.items():
            if k not in metadata:
                metadata[k] = _process_metadata_value(v)
    
    return metadata

def create_project_documents(project_df: pd.DataFrame, project_details: Optional[List[Dict[str, Any]]] = None) -> List[Document]:
    """
    Convert project data to LlamaIndex documents.
    
    Args:
        project_df: DataFrame containing project data
        project_details: List of detailed project information (optional)
        
    Returns:
        List of Document objects
    """
    project_docs = []
    
    # Process project DataFrame
    for _, row in project_df.iterrows():
        # Find matching project detail if available
        project_detail = next((p for p in (project_details or []) if p['name'] == row['project']), None)
        
        # Create text representation
        text = _create_project_text(row, project_detail)
        
        # Create metadata
        metadata = _create_metadata_dict(row.to_dict(), project_detail)
        
        # Create document
        doc = Document(text=text, metadata=metadata)
        project_docs.append(doc)
    
    return project_docs

def _create_task_text(row):
    """Create text representation of a task."""
    text = f"Task: {row['name']}\n"
    text += f"Project: {row['project']}\n"
    text += f"Status: {row['status']}\n"
    text += f"Assignee: {row['assignee']}\n"
    
    # Add due date if available
    if 'due_date' in row and pd.notna(row['due_date']):
        text += f"Due date: {row['due_date'].strftime('%Y-%m-%d')}\n"
    
    # Add creation date if available
    if 'created_at' in row and pd.notna(row['created_at']):
        text += f"Created at: {row['created_at'].strftime('%Y-%m-%d')}\n"
    
    # Add completion date if available
    if 'completed_at' in row and pd.notna(row['completed_at']):
        text += f"Completed at: {row['completed_at'].strftime('%Y-%m-%d')}\n"
    
    # Add section if available
    if 'section' in row:
        text += f"Section: {row['section']}\n"
    
    # Add tags if available
    if 'tags' in row and row['tags']:
        tags_str = ', '.join(row['tags']) if isinstance(row['tags'], list) else row['tags']
        text += f"Tags: {tags_str}\n"
    
    return text

def create_task_documents(task_df: pd.DataFrame) -> List[Document]:
    """
    Convert task data to LlamaIndex documents.
    
    Args:
        task_df: DataFrame containing task data
        
    Returns:
        List of Document objects
    """
    task_docs = []
    
    # Process task DataFrame
    for _, row in task_df.iterrows():
        # Create text representation
        text = _create_task_text(row)
        
        # Create metadata
        metadata = _create_metadata_dict(row.to_dict())
        
        # Create document
        doc = Document(text=text, metadata=metadata)
        task_docs.append(doc)
    
    return task_docs

def create_indices(api_key: str, project_docs: List[Document], task_docs: List[Document]) -> tuple:
    """
    Create vector indices for project and task documents.
    
    Args:
        api_key: OpenAI API key
        project_docs: List of project documents
        task_docs: List of task documents
        
    Returns:
        Tuple of (project_index, task_index)
    """
    try:
        # Set OpenAI API key for embeddings
        openai.api_key = api_key
        
        # Create embedding model
        embed_model = OpenAIEmbedding(api_key=api_key)
        
        # Create indices
        project_index = VectorStoreIndex.from_documents(
            project_docs,
            embed_model=embed_model
        )
        
        task_index = VectorStoreIndex.from_documents(
            task_docs,
            embed_model=embed_model
        )
        
        logger.info("Indices created successfully")
        return project_index, task_index
        
    except Exception as e:
        logger.error(f"Error creating indices: {e}")
        raise RuntimeError(f"Failed to create indices: {e}") 