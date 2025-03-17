"""
Query processor for the Asana Chat Assistant.

This module handles the processing of user queries and generation of responses.
"""
import logging
import re
import json
from typing import Dict, Any, Optional, Union, List, Callable
import plotly.graph_objects as go

from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.chat_engine.simple import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from src.utils.chat.visualization_handler import extract_visualization_info, generate_visualization
from src.utils.chat.data_context import DataContextManager
from src.utils.chat.tool_functions import AsanaToolFunctions

logger = logging.getLogger("asana_chat_assistant")

def setup_query_engine(project_index: VectorStoreIndex, task_index: VectorStoreIndex, llm: OpenAI) -> RouterQueryEngine:
    """
    Set up the query engine using a router to direct queries to the appropriate index.
    
    Args:
        project_index: Vector index for project data
        task_index: Vector index for task data
        llm: Language model instance
        
    Returns:
        Router query engine
    """
    try:
        # Create query engines for each index
        project_engine = project_index.as_query_engine(
            similarity_top_k=5,
            response_mode=ResponseMode.COMPACT
        )
        
        task_engine = task_index.as_query_engine(
            similarity_top_k=10,
            response_mode=ResponseMode.COMPACT
        )
        
        # Create query engine tools
        tools = [
            QueryEngineTool.from_defaults(
                query_engine=project_engine,
                name="project_info",
                description=(
                    "Useful for answering questions about projects, including completion estimates, "
                    "due dates, progress, and project owners."
                )
            ),
            QueryEngineTool.from_defaults(
                query_engine=task_engine,
                name="task_info",
                description=(
                    "Useful for answering questions about specific tasks, including status, "
                    "assignees, due dates, and completion timestamps."
                )
            )
        ]
        
        # Create router query engine
        query_engine = RouterQueryEngine.from_defaults(
            query_engine_tools=tools,
            select_multi=True,  # Allow multiple tools to be selected
            llm=llm
        )
        
        logger.info("Query engine created successfully")
        return query_engine
        
    except Exception as e:
        logger.error(f"Error creating query engine: {e}")
        raise RuntimeError(f"Failed to create query engine: {e}")

def setup_chat_engine(
    llm: OpenAI, 
    project_count: int = 0, 
    task_count: int = 0, 
    assignee_count: int = 0
) -> tuple:
    """
    Set up the chat engine with memory for conversation context.
    
    Args:
        llm: Language model instance
        project_count: Number of projects
        task_count: Number of tasks
        assignee_count: Number of assignees
        
    Returns:
        Tuple of (chat_engine, memory)
    """
    try:
        # Initialize memory for chat context
        memory = ChatMemoryBuffer.from_defaults(token_limit=1500)
        
        # Create system prompt with context about Asana data
        system_prompt = f"""
        You are an AI assistant for an Asana Portfolio Dashboard. You can access information about Asana projects, tasks, timelines, and resource allocation.
        
        The dashboard contains the following data:
        - {project_count} projects with status, due dates, and completion estimates
        - {task_count} tasks with assignees, status, due dates, and completion status
        - Resource allocation across {assignee_count} team members
        - Timeline visualizations for projects
        
        When answering questions:
        1. Use the specific data from the Asana projects to provide accurate insights.
        2. If appropriate, suggest a relevant visualization that could help understand the data.
        3. For questions about specific projects or tasks, provide detailed information.
        4. For questions about trends or analytics, mention relevant metrics.
        5. Be concise but informative, and focus on actionable insights.
        6. When asked about counts or statistics, use the exact numbers provided in the context.
        
        You can handle queries about:
        - Project status and progress
        - Task distribution and completion rates
        - Resource allocation and team workload
        - Timeline and scheduling
        - Recommendations for project management
        
        If you suggest a visualization, specify one of the following types:
        - "timeline" for project schedules and deadlines
        - "resource_allocation" for team workload distribution
        - "task_status" for task completion status distribution
        - "velocity" for team productivity over time
        - "burndown" for task completion trend analysis
        - "project_progress" for project completion percentage
        
        Always base your responses on the actual data available in the Asana dashboard.
        """
        
        # Create a system message
        if hasattr(llm.metadata, 'system_role'):
            system_role = llm.metadata.system_role
        else:
            system_role = "system"
            
        prefix_messages = [
            ChatMessage(content=system_prompt, role=system_role)
        ]
        
        # Create a simple chat engine
        chat_engine = SimpleChatEngine.from_defaults(
            llm=llm,
            memory=memory,
            prefix_messages=prefix_messages
        )
        
        logger.info("Chat engine created successfully")
        return chat_engine, memory
        
    except Exception as e:
        logger.error(f"Error creating chat engine: {e}")
        raise RuntimeError(f"Failed to create chat engine: {e}")

def detect_function_call(query: str) -> Optional[Dict[str, Any]]:
    """
    Detect if a function call is needed based on the query.
    
    Args:
        query: User's query text
        
    Returns:
        Dictionary with function call info or None
    """
    query_lower = query.lower()

    # Function call patterns
    function_patterns = [
        # Project count
        (r"how many projects", "get_project_count", {}),
        (r"number of projects", "get_project_count", {}),
        (r"total projects", "get_project_count", {}),
        (r"project count", "get_project_count", {}),

        # Project details
        (r"tell me about (the )?project ['\"](.*?)['\"]", "get_project_by_name", lambda m: {"project_name": m.group(2)}),
        (r"details (for|about) (the )?project ['\"](.*?)['\"]", "get_project_by_name", lambda m: {"project_name": m.group(3)}),
        (r"show me (the )?project ['\"](.*?)['\"]", "get_project_by_name", lambda m: {"project_name": m.group(2)}),

        # Assignee tasks
        (r"tasks assigned to ['\"](.*?)['\"]", "get_tasks_by_assignee", lambda m: {"assignee": m.group(1)}),
        (r"what is ['\"](.*?)['\"] working on", "get_tasks_by_assignee", lambda m: {"assignee": m.group(1)}),
        (r"['\"](.*?)['\"] tasks", "get_tasks_by_assignee", lambda m: {"assignee": m.group(1)}),

        # Overdue tasks
        (r"overdue tasks", "get_overdue_tasks", {}),
        (r"tasks that are overdue", "get_overdue_tasks", {}),
        (r"late tasks", "get_overdue_tasks", {}),

        # Task status distribution
        (r"task status distribution", "get_task_status_distribution", {}),
        (r"distribution of tasks", "get_task_status_distribution", {}),
        (r"task breakdown", "get_task_status_distribution", {}),

        # Project progress
        (r"project progress", "get_project_progress", {}),
        (r"progress of (all )?projects", "get_project_progress", {}),
        (r"how are (the )?projects progressing", "get_project_progress", {})
    ]

    # Check each pattern
    for pattern, function_name, param_extractor in function_patterns:
        if match := re.search(pattern, query_lower):
            params = param_extractor(match) if callable(param_extractor) else param_extractor
            return {
                "function": function_name,
                "params": params
            }

    return None

def execute_function_call(
    function_call: Dict[str, Any], 
    tool_functions: AsanaToolFunctions
) -> Optional[Dict[str, Any]]:
    """
    Execute a function call using the tool functions.
    
    Args:
        function_call: Function call info
        tool_functions: Tool functions instance
        
    Returns:
        Function result or None if function not found
    """
    function_name = function_call["function"]
    params = function_call["params"]
    
    # Map function names to methods
    function_map = {
        "get_project_count": tool_functions.get_project_count,
        "get_project_by_name": tool_functions.get_project_by_name,
        "get_tasks_by_assignee": tool_functions.get_tasks_by_assignee,
        "get_overdue_tasks": tool_functions.get_overdue_tasks,
        "get_task_status_distribution": tool_functions.get_task_status_distribution,
        "get_project_progress": tool_functions.get_project_progress
    }
    
    if function_name in function_map:
        try:
            logger.info(f"Executing function: {function_name} with params: {params}")
            result = function_map[function_name](**params)
            logger.info(f"Function result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {
                "error": f"Error executing function {function_name}: {str(e)}",
                "result": f"I encountered an error while retrieving that information: {str(e)}"
            }
    
    logger.warning(f"Function not found: {function_name}")
    return None

def process_query(
    query: str, 
    chat_engine: SimpleChatEngine, 
    query_engine: RouterQueryEngine, 
    project_df, 
    task_df, 
    project_details,
    data_context: Optional[DataContextManager] = None,
    tool_functions: Optional[AsanaToolFunctions] = None,
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a user query and generate a response with optional visualization.
    
    Args:
        query: User's query text
        chat_engine: Chat engine instance
        query_engine: Query engine instance
        project_df: DataFrame with project data
        task_df: DataFrame with task data
        project_details: List of project details
        data_context: Data context manager (optional)
        tool_functions: Tool functions instance (optional)
        additional_context: Additional context to include (optional)
        
    Returns:
        Dictionary containing the response text and optional visualization
    """
    try:
        logger.info(f"Processing query: {query}")

        # Build context and get response
        context_parts = _gather_context_parts(query, data_context, tool_functions, additional_context, query_engine)
        response_text = _get_chat_response(query, chat_engine, context_parts)

        return _create_result_with_visualization(
            query, response_text, project_df, task_df, project_details
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {
            "text": f"I'm sorry, I encountered an error while processing your request: {str(e)}",
            "visualization": None
        }

def _gather_context_parts(
    query: str,
    data_context: Optional[DataContextManager],
    tool_functions: Optional[AsanaToolFunctions],
    additional_context: Optional[str],
    query_engine: RouterQueryEngine
) -> List[str]:
    """Gather all context parts for the query."""
    context_parts = []

    # Add data context if available
    if data_context:
        context_parts.append(data_context.get_query_specific_context(query))

    # Add function call results if available
    _add_function_call_results(query, tool_functions, context_parts)

    # Add additional context if provided
    if additional_context:
        context_parts.append(additional_context)

    # Add query engine results
    _add_query_engine_results(query, query_engine, context_parts)
    
    return context_parts

def _add_function_call_results(
    query: str,
    tool_functions: Optional[AsanaToolFunctions],
    context_parts: List[str]
) -> None:
    """Add function call results to context parts if available."""
    if not tool_functions:
        return
        
    function_call = detect_function_call(query)
    if not function_call:
        return
        
    function_result = execute_function_call(function_call, tool_functions)
    if function_result and "result" in function_result:
        context_parts.append(f"Function result: {function_result['result']}")

def _add_query_engine_results(
    query: str,
    query_engine: RouterQueryEngine,
    context_parts: List[str]
) -> None:
    """Add query engine results to context parts."""
    try:
        query_engine_response = query_engine.query(query)
        logger.info("Retrieved information from query engine")
        if query_engine_response:
            context_parts.append(f"Retrieved information: {query_engine_response.response}")
    except Exception as e:
        logger.warning(f"Error retrieving information from query engine: {e}")

def _get_chat_response(
    query: str,
    chat_engine: SimpleChatEngine,
    context_parts: List[str]
) -> str:
    """Get chat response with or without context."""
    if context_parts:
        combined_context = "\n\n".join(context_parts)
        context_query = f"Based on the following information:\n\n{combined_context}\n\nUser question: {query}"
        chat_response = chat_engine.chat(context_query)
    else:
        chat_response = chat_engine.chat(query)
    
    return str(chat_response)

def _create_result_with_visualization(
    query: str,
    response_text: str,
    project_df,
    task_df,
    project_details
) -> Dict[str, Any]:
    """Create result dictionary with visualization if needed."""
    result = {
        "text": response_text,
        "visualization": None,
        "viz_type": None
    }

    # Check if visualization is needed
    viz_info = extract_visualization_info(query, response_text)
    if not viz_info["needed"]:
        return result

    # Generate visualization
    viz_type = viz_info["type"]
    viz_params = viz_info["params"]

    logger.info(f"Generating visualization: {viz_type}")
    if visualization := generate_visualization(
        viz_type, viz_params, project_df, task_df, project_details
    ):
        result["visualization"] = visualization
        result["viz_type"] = viz_type

    return result 