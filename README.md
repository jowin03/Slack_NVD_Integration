# Slack-NVD Integration

## Overview
 - This repository contains a Flask-based Slack bot that automates the process of fetching vulnerabilities from the National Vulnerability Database (NVD) and notifying an admin in a Slack channel. The admin can then assign these vulnerabilities to specific users in the Slack workspace, allowing them to address the issues.

### Table of Contents
 - Features
 - Requirements
 -Installation
 -Configuration
 - Usage
 - Handling Rate Limits
 - Troubleshooting
 
### Features
 - Fetch Vulnerabilities: Automatically fetch vulnerabilities from the NVD API.
 - Notify Admin: Send notifications to the admin with options to assign the vulnerability to users.
 - Forward to User: Forward the vulnerability details to selected users in the Slack workspace.
 - Interactive Messages: Support for interactive messages in Slack (e.g., dropdowns and buttons).
 - Task Confirmation: Users can confirm the resolution of vulnerabilities, notifying the admin of task completion.
 - Logging: Detailed logging for tracking operations and debugging issues.

### Requirements
 - Python 3.8+
 - Flask
 - Slack_SDK
 - Requests
 - Schedule
 - Logging

### Installation

#### Create a Virtual Environment
 - python3 -m venv venv
 - source venv/bin/activate  # On Windows use `venv\Scripts\activate`

#### Install Dependencies
 - pip install -r requirements.txt

#### Set Up the Environment
1. Configuration File:
 - Create a config.json file in the root directory of your project.
 - Include the following configurations:
- {
    "slack_bot_token": "YOUR_SLACK_BOT_TOKEN",
    "admin_user_id": "ADMIN_SLACK_USER_ID",
    
    "nvd_api_url": "https://services.nvd.nist.gov/rest/json/cves/2.0"
 }

2. Environment Variables:
 - If using a .env file for environment variables (optional):
 - SLACK_BOT_TOKEN=YOUR_SLACK_BOT_TOKEN
 - ADMIN_USER_ID=ADMIN_SLACK_USER_ID
 - NVD_API_URL=https://services.nvd.nist.gov/rest/json/cves/2.0
 - You can use the python-dotenv package to load these variables.

### Configuration
1. Logging Configuration:
 - Logging is set up to provide detailed output during the script's operation. Modify the logging level as needed in the script:
 - logging.basicConfig(level=logging.DEBUG)
 - logger = logging.getLogger(__name__)

2. Scheduling:
 - The script uses schedule to run a job every minute at 00:50 to fetch vulnerabilities and notify the admin:
 - schedule.every().minute.at(":50").do(job)

### Usage
1. Running the Flask Application:
 - Start the Flask server and the scheduler thread:
 - python main.py

2. Handling Slack Events:
 - The Flask app listens for Slack events at the /slack/events endpoint. Ensure this endpoint is correctly set in your Slack app's event subscription settings.

3. Interactive Modals:
 - The admin will receive vulnerability notifications with a "Select Users" button to assign tasks.
 - Upon selection, users will receive a message with the details and a "Reply" button to confirm resolution.

### Handling Rate Limits
 - The script includes basic error handling for Slack API rate limits. In case of rate limiting, it will log an error and you may need to implement a backoff strategy depending on your Slack workspace's usage.

### Troubleshooting
 #### Error Sending Messages:
 - Ensure the Slack Bot Token is valid and has the required permissions.
 - Check the config.json for correct user IDs and API URLs.
 
 #### Modal Errors:
 - If encountering issues with Slack modals, ensure the payload conforms to Slack's API specifications and that required blocks are included.

#### Missing Triggers:
 - If the trigger_id is missing in Slack events, verify that the correct scopes and permissions are granted to your Slack app.
