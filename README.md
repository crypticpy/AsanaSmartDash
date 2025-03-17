# Asana Portfolio Dashboard

## Overview

This Asana Portfolio Dashboard is a powerful Streamlit application designed to provide comprehensive insights into your Asana projects and tasks. It offers a wide range of visualizations and metrics to help project managers and team leaders make data-driven decisions.

## Features

- **Project Overview**: Get a high-level view of all your projects with completion estimates and status indicators
- **Task Analytics**: Analyze task distribution, completion rates, and overdue tasks
- **Resource Allocation**: Visualize how resources are allocated across projects
- **Team Performance**: Track team velocity and productivity over time
- **Interactive Charts**: Explore data with interactive charts and filters
- **Project Cards**: View detailed project information in a clean, modern UI
- **AI Assistant**: Ask questions about your projects and get intelligent insights (requires OpenAI API key)
- **Responsive Design**: Optimized for both desktop and mobile viewing

## Installation

### Prerequisites

- Python 3.8 or higher
- Asana Personal Access Token
- Portfolio GID and Team GID from Asana
- OpenAI API Key (for AI assistant features)

### Setup

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/asana-portfolio-dashboard.git
   cd asana-portfolio-dashboard
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:

   ```
   python run.py
   ```

   Or directly with Streamlit:

   ```
   streamlit run app.py
   ```

2. Open your web browser and navigate to the provided URL (typically http://localhost:8501)

3. Enter your API credentials in the sidebar:

   - Asana Personal Access Token
   - Portfolio GID
   - Team GID
   - OpenAI API Key (for AI assistant features)

4. Save your configuration and explore your Asana data!

## Project Structure

```
asana-portfolio-dashboard/
├── app.py                  # Main application file
├── run.py                  # Script to run the application
├── requirements.txt        # Project dependencies
├── README.md               # Project documentation
├── src/                    # Source code
│   ├── components/         # UI components
│   │   ├── dashboard_metrics.py  # Dashboard metrics components
│   │   ├── project_card.py       # Project card component
│   │   ├── sidebar.py            # Sidebar component
│   │   └── chat_assistant.py     # Chat assistant component
│   ├── styles/             # CSS and styling
│   │   └── custom.py       # Custom CSS styles
│   ├── utils/              # Utility functions
│   │   ├── asana_api.py    # Asana API utilities
│   │   ├── config.py       # Configuration utilities
│   │   ├── data_processing.py  # Data processing utilities
│   │   ├── visualizations.py   # Visualization utilities
│   │   └── chat/           # Chat assistant utilities
│   └── pages/              # Additional pages (for future use)
└── venv/                   # Virtual environment (not tracked in git)
```

## Configuration

The application stores your API credentials locally in a `config.json` file. You can:

- Save your credentials for future use
- Clear saved credentials at any time
- Toggle visibility of your API tokens for security

## API Keys

### Asana API Token

Required for accessing your Asana data. You can get it from the [Asana Developer Console](https://app.asana.com/0/developer-console).

### Portfolio GID

Required for accessing your Asana portfolio. You can find it in the URL when viewing your portfolio in Asana.

### Team GID

Optional, used for team-specific features. You can find it in the URL when viewing your team in Asana.

### OpenAI API Key

Required for AI assistant features. You can get it from [OpenAI API Keys](https://platform.openai.com/api-keys).

## Data Privacy

This application does not store any of your Asana data or API keys on external servers. All data is fetched in real-time using the provided API credentials and is only stored temporarily in memory during the session or locally in your config file.

## Contributing

Contributions to improve the dashboard are welcome. Please feel free to submit a Pull Request or open an Issue to discuss potential improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
