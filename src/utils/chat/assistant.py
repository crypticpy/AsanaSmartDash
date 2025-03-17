"""
Main Asana Chat Assistant class.

This module contains the core class for the AI chat assistant that answers
questions about Asana projects and tasks.
"""
import logging
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
import plotly.graph_objects as go

from llama_index.llms.openai import OpenAI

# Import custom modules
from src.utils.chat.document_indexer import (
    create_project_documents, create_task_documents, create_indices
)
from src.utils.chat.query_processor import (
    setup_query_engine, setup_chat_engine, process_query
)
from src.utils.chat.data_context import DataContextManager
from src.utils.chat.tool_functions import AsanaToolFunctions
from src.utils.chat.api_wrapper import AsanaAPIWrapper

class AsanaChatAssistant:
    """
    AI chat assistant for the Asana Portfolio Dashboard.
    This class processes natural language queries about Asana projects and tasks,
    and generates responses and visualizations.
    """
    def __init__(
        self, 
        project_df: pd.DataFrame, 
        task_df: pd.DataFrame, 
        project_details: Optional[List[Dict[str, Any]]] = None,
        api_instances: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the chat assistant with project and task data.
        
        Args:
            project_df: DataFrame containing project data with completion estimates
            task_df: DataFrame containing task data
            project_details: List of detailed project information (optional)
            api_instances: Dictionary of Asana API instances (optional)
        """
        # Set up logger first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("asana_chat_assistant")
        
        self.project_df = project_df
        self.task_df = task_df
        self.project_details = project_details or []
        self.api_instances = api_instances
        
        # Initialize components
        self.setup_llm()
        self.setup_data_context()
        self.setup_tool_functions()
        self.setup_api_wrapper()
        self.setup_indices()
        self.setup_query_engine()
        self.setup_chat_engine()
        
        self.logger.info("AsanaChatAssistant initialized successfully")
    
    def setup_llm(self):
        """Initialize the LLM (OpenAI GPT-4o)."""
        try:
            # Get API key from session state (user input)
            if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
                api_key = st.session_state.openai_api_key
            else:
                # Fallback to secrets if available (for backward compatibility)
                try:
                    api_key = st.secrets["openai_api_key"]
                except:
                    raise RuntimeError("OpenAI API key not found. Please provide your OpenAI API key in the sidebar.")
            
            # Initialize OpenAI LLM
            self.llm = OpenAI(
                model="gpt-4o",
                api_key=api_key,
                temperature=0.2  # Lower temperature for more factual responses
            )
            
            self.logger.info("LLM initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing LLM: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {e}")
    
    def setup_data_context(self):
        """Set up the data context manager."""
        try:
            self.data_context = DataContextManager(
                self.project_df,
                self.task_df,
                self.project_details
            )
            self.logger.info("Data context manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing data context manager: {e}")
            self.data_context = None
    
    def setup_tool_functions(self):
        """Set up the tool functions."""
        try:
            self.tool_functions = AsanaToolFunctions(
                self.project_df,
                self.task_df,
                self.project_details
            )
            self.logger.info("Tool functions initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing tool functions: {e}")
            self.tool_functions = None
    
    def setup_api_wrapper(self):
        """Set up the API wrapper if API instances are available."""
        if self.api_instances:
            try:
                self.api_wrapper = AsanaAPIWrapper(self.api_instances)
                self.logger.info("API wrapper initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing API wrapper: {e}")
                self.api_wrapper = None
        else:
            self.logger.info("No API instances provided, skipping API wrapper initialization")
            self.api_wrapper = None
    
    def setup_indices(self):
        """Set up vector indices for project and task data."""
        try:
            # Get API key from session state (user input)
            if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
                api_key = st.session_state.openai_api_key
            else:
                # Fallback to secrets if available (for backward compatibility)
                try:
                    api_key = st.secrets["openai_api_key"]
                except:
                    raise RuntimeError("OpenAI API key not found. Please provide your OpenAI API key in the sidebar.")
            
            # Convert project data to documents
            project_docs = create_project_documents(self.project_df, self.project_details)
            
            # Convert task data to documents
            task_docs = create_task_documents(self.task_df)
            
            # Create indices
            self.project_index, self.task_index = create_indices(api_key, project_docs, task_docs)
            
            self.logger.info("Indices setup completed successfully")
        except Exception as e:
            self.logger.error(f"Error setting up indices: {e}")
            raise RuntimeError(f"Failed to set up indices: {e}")
    
    def setup_query_engine(self):
        """Set up the query engine to direct queries to the appropriate index."""
        try:
            self.query_engine = setup_query_engine(
                self.project_index, 
                self.task_index, 
                self.llm
            )
            self.logger.info("Query engine setup completed successfully")
        except Exception as e:
            self.logger.error(f"Error setting up query engine: {e}")
            raise RuntimeError(f"Failed to set up query engine: {e}")
    
    def setup_chat_engine(self):
        """Set up the chat engine with memory for conversation context."""
        try:
            # Get basic statistics for the system prompt
            project_count = 0 if self.project_df.empty else len(self.project_df)
            task_count = 0 if self.task_df.empty else len(self.task_df)
            assignee_count = 0 if self.task_df.empty else self.task_df['assignee'].nunique()
            
            self.chat_engine, self.memory = setup_chat_engine(
                self.llm,
                project_count=project_count,
                task_count=task_count,
                assignee_count=assignee_count
            )
            self.logger.info("Chat engine setup completed successfully")
        except Exception as e:
            self.logger.error(f"Error setting up chat engine: {e}")
            raise RuntimeError(f"Failed to set up chat engine: {e}")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and generate a response with optional visualization.
        
        Args:
            query: User's query text
            
        Returns:
            Dictionary containing the response text and optional visualization
        """
        # Get additional context from data context manager
        additional_context = None
        if self.data_context:
            additional_context = self.data_context.get_context_summary()
        
        return process_query(
            query, 
            self.chat_engine, 
            self.query_engine, 
            self.project_df, 
            self.task_df, 
            self.project_details,
            data_context=self.data_context,
            tool_functions=self.tool_functions,
            additional_context=additional_context
        ) 