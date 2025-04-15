# Facebook Automation Panel

A graphical application for managing and automating Facebook accounts using Python and Playwright.

## Features

- Account management
- Facebook automation workflows
- Session persistence
- Stealth browsing
- System resource monitoring
- Concurrent operations

## Architecture

This application follows the Model-View-Controller (MVC) pattern:

### Models

Models handle data management and business logic:

- `models/account_model.py`: Manages Facebook accounts
- `models/playwright/browser_manager.py`: Manages browser instances
- `models/playwright/session_handler.py`: Handles browser sessions
- `models/playwright/automation_handler.py`: Implements automation actions

### Views

Views handle the user interface:

- TBD: Views will be implemented based on existing UI components

### Controllers

Controllers coordinate between models and views:

- `controllers/account_controller.py`: Handles account operations
- `controllers/automation_controller.py`: Manages workflow operations
- `controllers/monitoring_controller.py`: Controls monitoring and logging

### Utilities

- `utils/logger.py`: Centralized logging system

## Requirements

- Python 3.12+
- Required packages:
  - customtkinter>=5.2.2
  - patchright>=1.51.0
  - playwright-stealth>=1.0.6
  - psutil>=7.0.0
  - setuptools>=78.1.0

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/facebook_automation_panel.git
   cd facebook_automation_panel
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv add customtkinter patchright playwright-stealth psutil setuptools
   ```

3. Install Playwright browsers:
   ```
   playwright install --with-deps
   ```

## Usage

Run the application:
```
uv run app.py
```

For debugging:
```
uv run app.py --debug
```

## Directory Structure

```
facebook_automation_panel/
├── app.py                      # Main application
├── models/                     # Data models
│   ├── account_model.py        # Account data management
│   └── playwright/             # Browser automation
│       ├── browser_manager.py  # Browser management
│       ├── session_handler.py  # Session handling
│       └── automation_handler.py # Automation actions
├── controllers/                # Business logic
│   ├── account_controller.py   # Account operations
│   ├── automation_controller.py # Workflow operations
│   └── monitoring_controller.py # System monitoring
├── views/                      # UI components
│   └── ...                     # TBD
├── utils/                      # Utilities
│   └── logger.py               # Logging system
├── sessions/                   # Browser sessions storage
├── accounts.json               # Account data
└── workflows.json              # Workflow configurations
```

## License

[MIT License](LICENSE)
