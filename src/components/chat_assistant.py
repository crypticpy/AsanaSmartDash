"""
Chat assistant component for the Asana Portfolio Dashboard.
This module contains the UI components for the chat interface.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List
import plotly.graph_objects as go
import time
import logging
import uuid

# Import chat logic
from src.utils.chat import AsanaChatAssistant

# Configure logging
logger = logging.getLogger("asana_dashboard.chat")

def initialize_chat_state():
    """Initialize chat-related session state variables if they don't exist."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hello! I can help you analyze your Asana projects. What would you like to know?"}
        ]
    
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = 0
        
    if "chat_initialized" not in st.session_state:
        st.session_state.chat_initialized = False

def _display_chat_header(compact: bool):
    """Display the chat interface header based on layout type."""
    if not compact:
        st.title("Asana Project Assistant")
        st.markdown(
            """
            Ask questions about your projects, tasks, timelines, and resource allocation. Some examples:
            - *"Which projects are behind schedule?"*
            - *"Who has the most tasks assigned to them?"*
            - *"Show me the completion status of all projects"*
            - *"When is the Marketing Campaign project due?"*
            - *"Create a chart showing task distribution by assignee"*
            - *"Analyze the workload across team members"*
            """
        )
    else:
        st.markdown("### Asana Project Assistant")

def _initialize_chat_assistant():
    """Initialize the chat assistant if not already created. Returns True if successful."""
    if "chat_assistant" in st.session_state:
        return True

    # Make sure we have the necessary data in session state
    if any(
        key not in st.session_state for key in ["task_df", "project_estimates"]
    ):
        missing_keys = [key for key in ["task_df", "project_estimates"] if key not in st.session_state]
        st.warning(f"Please load your Asana data first. Missing data: {', '.join(missing_keys)}")
        return False

    with st.spinner("Setting up the AI assistant..."):
        try:
            _create_chat_assistant()
            st.session_state.chat_initialized = True
            logger.info("Chat assistant initialized successfully")
            return True
        except Exception as e:
            _handle_initialization_error(e)
            return False

def _create_chat_assistant():
    """Create and store the chat assistant instance in session state."""
    project_details = st.session_state.get("project_details", [])
    api_instances = st.session_state.get("api_instances", None)

    st.session_state.chat_assistant = AsanaChatAssistant(
        st.session_state.project_estimates, 
        st.session_state.task_df,
        project_details,
        api_instances
    )

def _handle_initialization_error(error):
    """Handle errors during chat assistant initialization."""
    st.error(f"Error initializing chat assistant: {error}")
    logger.error(f"Error initializing chat assistant: {error}")
    
    # Provide detailed error if OpenAI API key is missing
    if "openai_api_key" in str(error).lower():
        st.error(
            "Please provide your OpenAI API key in the sidebar to use the AI assistant features. "
            "You can get an API key from https://platform.openai.com/api-keys"
        )
        # Add a button to navigate to the sidebar
        if st.button("Go to Settings"):
            # This will trigger a rerun with the sidebar expanded
            st.session_state.sidebar_expanded = True
            st.rerun()

def _display_chat_history(compact: bool):
    """Display the chat message history."""
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display visualization if available and explicitly requested
            if "visualization" in message and message["visualization"] is not None and message.get("show_viz", True):
                st.plotly_chart(
                    message["visualization"], 
                    use_container_width=True,
                    height=250 if compact else 350,
                    key=f"viz_{id(message)}"
                )

def _should_show_visualization(query: str) -> bool:
    """Determine if visualization should be shown based on query content."""
    query = query.lower()
    return any(term in query for term in [
        "chart", "graph", "plot", "visual", "show me", "display"
    ])

def _handle_chat_response(response, prompt, message_placeholder, viz_placeholder, compact: bool):
    """Process and display the chat assistant's response."""
    show_viz = _should_show_visualization(prompt)
    
    # Update the message placeholder with the response text
    message_placeholder.markdown(response["text"])
    
    # Display visualization if available and requested
    if response.get("visualization") is not None and show_viz:
        viz_placeholder.plotly_chart(
            response["visualization"],
            use_container_width=True,
            height=250 if compact else 350
        )
    
    # Add to chat history
    st.session_state.chat_messages.append({
        "role": "assistant", 
        "content": response["text"],
        "visualization": response.get("visualization"),
        "show_viz": show_viz
    })

def _handle_chat_error(error, message_placeholder):
    """Handle errors during chat processing."""
    error_message = f"I'm sorry, I encountered an error: {str(error)}"
    logger.error(f"Error in chat processing: {error}")
    
    # Update the message placeholder with the error
    message_placeholder.markdown(error_message)
    
    # Add to chat history
    st.session_state.chat_messages.append({
        "role": "assistant", 
        "content": error_message
    })

def _process_user_input(prompt, compact: bool):
    """Process user input and generate a response."""
    # Add user message to chat history
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response with a spinner
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        viz_placeholder = st.empty()
        
        # Show initial loading message
        message_placeholder.markdown("Thinking...")
        
        try:
            # Process the query
            response = st.session_state.chat_assistant.process_query(prompt)
            _handle_chat_response(response, prompt, message_placeholder, viz_placeholder, compact)
        except Exception as e:
            _handle_chat_error(e, message_placeholder)

def create_chat_interface(compact: bool = False):
    """
    Create the chat interface for the Asana Dashboard using Streamlit's native chat components.
    
    Args:
        compact: Whether to use a compact layout (for sidebar)
    """
    # Initialize session state
    initialize_chat_state()

    # Set up the header
    _display_chat_header(compact)

    # Initialize the chat assistant
    if not _initialize_chat_assistant():
        return

    # Display chat messages from history
    _display_chat_history(compact)

    if prompt := st.chat_input(
        "Ask about your Asana projects...",
        key=f"chat_input_{id(st.session_state)}",
    ):
        _process_user_input(prompt, compact)

def create_sidebar_chat():
    """Create a compact chat interface for the sidebar."""
    with st.sidebar.expander("Chat Assistant", expanded=False):
        create_chat_interface(compact=True)

def create_chat_tab():
    """Create a dedicated chat tab for the dashboard."""
    # Set current tab to Chat Assistant (index 3) when this function is called
    if "current_tab" in st.session_state:
        st.session_state.current_tab = 3
        
    create_chat_interface(compact=False)

def add_floating_chat_button():
    """Add a floating chat button to the dashboard."""
    # Initialize state
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    
    # Define callback to toggle chat
    def toggle_chat():
        st.session_state.show_chat = not st.session_state.show_chat
        # Set current tab to Chat Assistant (index 3) when chat is shown
        if st.session_state.show_chat:
            st.session_state.current_tab = 3
    
    # Add custom CSS for floating button
    st.markdown(
        """
        <style>
        .floating-chat-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .floating-chat-button:hover {
            background-color: #45a049;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Add button
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        st.button("💬", key="chat_button", on_click=toggle_chat)
    