 # Slack-NVD Vulnerability Management Bot

 - This repository contains a Flask-based Slack bot that automates the process of fetching vulnerabilities from the National Vulnerability Database (NVD) and notifying an admin in a Slack channel. The admin can then assign these vulnerabilities to specific users in the Slack workspace.

 ## Table of Contents
  
  - Features
  - Requirements
  - Installation
  - Configuration
  - Usage
  - Handling Rate Limits
  - Troubleshooting

  ## Features

  - Fetch Vulnerabilities: Automatically fetch vulnerabilities from the NVD API.
  - Notify Admin: Send notifications to the admin with options to assign the vulnerability to users.
  - Forward to User: Forward the vulnerability details to a selected user in the Slack workspace.
  - Interactive Messages: Support for interactive messages in Slack (e.g.,dropdowns and buttons).

  ## Requirements

  - Python 3.8+
  - Flask
  - Slack_Sdk
  - Requests
  - Schedule

  ## Installation

  ### Create a Virtual Environment:
  - python3 -m venv venv.
  - source venv/bin/activate.

  ### Install Dependencies:
  - pip install -r requirements.txt

  ## Configuration

  ### Create a Slack App:
  - Go to Slack API and create a new app.
  - Enable the following OAuth Scopes:
    - channels:read
    - chat:write
    - users:read
    - Commands
  - Install the app to your workspace and note the OAuth Token.

  ### Set Up config.json:
   - Create a config.json file in the root directory with the following content:
   - { 
        “slack_bot_token": "xoxb-your-slack-bot-token",
        "admin_channel": "#admin-channel",
        "nvd_api_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
        "port": 3000
    }
   - Replace the placeholder values with your actual Slack Bot Token, the Slack channel for the admin notifications, and the port number you want the Flask app to run on.

  ### Expose Flask App:
  - If you are testing locally, you may need to expose your local Flask app to the internet using a tool like ngrok.
  - Update the Slack app's Interactivity settings with the ngrok URL.

  ## Usage:

  ### Start the Flask App:
  - python app.py or whatever you have saved your script in your system.
  
  ### Interact with the Bot:
   - The bot will automatically fetch vulnerabilities and notify the admin in the specified Slack channel.
   - The admin can assign the vulnerability to a user by selecting them from a dropdown list.
   - The selected user will receive a notification in Slack with the vulnerability details and an option to mark it as
resolved.

  ### Scheduling:
  - The script is set up to fetch vulnerabilities every hour at the 15th minute (e.g., 00:15, 01:15, etc.).
  - You can adjust the scheduling in the job function within app.py.

  ## Handling Rate Limits 
  - The Slack API has rate limits on requests. If your app hits the ratelimit, the script will automatically retry after the specified time (as
provided by the Retry-After header in Slack's response).

  ## Troubleshooting
  ### Interactive Messages Resetting:
  - If the selected user resets after making a choice, ensure that the bot responds properly to Slack's
interactive message payloads.
  ### Missing Events:
  - Ensure that your Flask endpoint (/slack/events) is publicly accessible and correctly set up in your Slack app's
Interactivity settings.
  ### Rate Limits: 
  - If you encounter rate limits frequently, consider reducing the frequency of your requests or optimizing your user
fetching logic.
