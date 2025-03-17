"""
Sidebar component for the Asana Portfolio Dashboard.
"""
import streamlit as st
from typing import Dict, Any, Tuple
import hydralit_components as hc
from src.utils.config import get_manager, save_config

def create_sidebar() -> Tuple[str, str, str, str]:
    """
    Create the sidebar with configuration options.
    
    Returns:
        Tuple of (api_token, portfolio_gid, team_gid, openai_api_key)
    """
    st.sidebar.title("Asana Configuration")
    
    # Get configuration
    config = get_manager()
    
    # API Token input with toggle for visibility
    st.sidebar.subheader("Asana API Token")
    show_token = st.sidebar.checkbox("Show API Token", value=False)
    api_token = st.sidebar.text_input(
        "API Token",
        type="password" if not show_token else "default",
        value=config.get("ASANA_API_TOKEN", ""),
        help="Your Asana Personal Access Token"
    )
    
    # Portfolio GID input
    st.sidebar.subheader("Portfolio GID")
    portfolio_gid = st.sidebar.text_input(
        "Portfolio GID",
        value=config.get("PORTFOLIO_GID", ""),
        help="The GID of your Asana Portfolio"
    )
    
    # Team GID input
    st.sidebar.subheader("Team GID")
    team_gid = st.sidebar.text_input(
        "Team GID",
        value=config.get("TEAM_GID", ""),
        help="The GID of your Asana Team"
    )
    
    # OpenAI API Key input
    st.sidebar.subheader("OpenAI API Key")
    show_openai_key = st.sidebar.checkbox("Show OpenAI API Key", value=False)
    openai_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password" if not show_openai_key else "default",
        value=config.get("OPENAI_API_KEY", ""),
        help="Your OpenAI API Key (required for AI assistant features)"
    )
    
    # Save credentials button
    if st.sidebar.button("Save Configuration"):
        config["ASANA_API_TOKEN"] = api_token
        config["PORTFOLIO_GID"] = portfolio_gid
        config["TEAM_GID"] = team_gid
        config["OPENAI_API_KEY"] = openai_api_key
        save_config(config)
        st.sidebar.success("Configuration saved!")
    
    # Clear credentials button
    if st.sidebar.button("Clear Saved Credentials"):
        config.clear()
        save_config(config)
        st.sidebar.success("Credentials cleared!")
        st.rerun()
    
    # Add refresh data button
    if st.sidebar.button("Refresh Data", type="primary"):
        st.cache_data.clear()
        st.sidebar.success("Cache cleared! Data will be refreshed.")
    
    # Add sidebar info
    with st.sidebar.expander("About"):
        st.markdown("""
        # Asana Portfolio Dashboard
        
        This dashboard provides insights into your Asana projects and tasks.
        
        ## How to use
        1. Enter your Asana API Token
        2. Enter your Portfolio GID
        3. Enter your Team GID
        4. Enter your OpenAI API Key (for AI features)
        5. Click "Save Configuration"
        
        ## Data Privacy
        Your credentials are stored locally and are not shared with any third parties.
        """)
    
    return api_token, portfolio_gid, team_gid, openai_api_key 