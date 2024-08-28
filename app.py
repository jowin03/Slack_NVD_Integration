from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
import json
import threading
import schedule
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration from JSON file
with open('config.json') as f:
    config = json.load(f)

SLACK_BOT_TOKEN = config['slack_bot_token']
ADMIN_CHANNEL_ID = config['admin_channel_id']
NVD_API_URL = config['nvd_api_url']
PORT = config['port']

client = WebClient(token=SLACK_BOT_TOKEN)

# A set to track resolved vulnerabilities
resolved_vulnerabilities = set()


# Update the fetch_vulnerabilities function to accept start and limit parameters
def fetch_vulnerabilities(start=0, limit=20):
    """Fetch vulnerabilities from NVD API with pagination."""
    params = {
        'startIndex': start,
        'resultsPerPage': limit
    }
    response = requests.get(NVD_API_URL, params=params)
    return response.json()


def send_message_to_admin(vulnerability):
    """Send a message to the Slack admin with vulnerability details."""
    description = vulnerability['cve']['descriptions'][0]['value']
    message = {
        "channel": ADMIN_CHANNEL_ID,
        "text": "New Vulnerability Found",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"New Vulnerability Found:\n\n{description}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Select Users"
                        },
                        "action_id": "user_selection"
                    }
                ]
            }
        ]
    }
    try:
        client.chat_postMessage(**message)
    except SlackApiError as e:
        logger.error(f"Error sending message: {e.response['error']}")

def send_message_to_user(user, description):
    """Send a vulnerability message to a specific user."""
    message = {
        "channel": user,
        "blocks": [
            {
                "type": "section",
                "block_id": "vulnerability_description",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Vulnerability Details:\n\n{description}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reply"
                        },
                        "action_id": "confirm"
                    }
                ]
            }
        ],
        "text": "Vulnerability Details"
    }
    try:
        response = client.chat_postMessage(**message)
        logger.debug(f"Message sent to {user}: {response}")
        # Track the message ID or vulnerability ID to avoid resending
        resolved_vulnerabilities.add(description)
    except SlackApiError as e:
        logger.error(f"Error sending message: {e.response['error']}")

def job():
    """Scheduled job to fetch vulnerabilities and notify the admin with pagination."""
    start = 0
    limit = 20  # Number of vulnerabilities to fetch at a time
    while True:
        vulnerabilities = fetch_vulnerabilities(start=start, limit=limit)
        if not vulnerabilities.get('vulnerabilities'):
            break
        for vulnerability in vulnerabilities['vulnerabilities']:
            description = vulnerability['cve']['descriptions'][0]['value']
            if description not in resolved_vulnerabilities:
                send_message_to_admin(vulnerability)
        start += limit
        time.sleep(5)  # Delay to simulate pagination and avoid overloading the system


# Schedule the job to run every minute at 00:50
schedule.every().minute.at(":50").do(job)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(5)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events."""
    logger.debug(f"Request content type: {request.content_type}")
    logger.debug(f"Request data: {request.data}")

    if request.content_type == 'application/x-www-form-urlencoded':
        data = request.form
        if "payload" in data:
            payload = json.loads(data["payload"])
        else:
            return jsonify({'error': 'Missing payload'}), 400
    elif request.content_type == 'application/json':
        payload = request.json
    else:
        return jsonify({'error': 'Unsupported media type'}), 415

    logger.debug(f"Received payload: {payload}")

    if 'type' in payload:
        if payload['type'] == 'block_actions':
            actions = payload.get('actions', [])
            if actions:
                action_id = actions[0]['action_id']
                user_id = payload['user']['id']
                logger.debug(f"Action ID: {action_id}, User ID: {user_id}")

                if action_id == 'user_selection':
                    return handle_user_selection(payload)
                elif action_id == 'confirm':
                    return handle_confirm(payload, user_id)
                else:
                    logger.debug(f"Unhandled action_id: {action_id}")
            else:
                logger.debug("No actions found.")
        elif payload['type'] == 'view_submission':
            return handle_view_submission(payload)
        else:
            logger.debug(f"Unhandled event type: {payload['type']}")
    else:
        logger.debug("Payload does not contain 'type' key")

    return jsonify({'status': 'ok'})


def handle_view_submission(payload):
    """Handle view submission."""
    view = payload.get('view', {})
    callback_id = view.get('callback_id')
    try:
        if callback_id == 'user_selection_modal':
            selected_users = get_selected_users_from_view(view.get('state', {}).get('values', {}))
            description = get_description_from_view(view.get('state', {}).get('values', {}))
            if not selected_users:
                logger.debug("No users selected.")
                return jsonify({'status': 'ok'})
            logger.debug(f"Selected Users: {selected_users}")
            logger.debug(f"Description: {description}")
            for user in selected_users:
                send_message_to_user(user, description)
            return jsonify({'status': 'ok'})
        else:
            logger.debug(f"Unhandled view_submission callback_id: {callback_id}")
            return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error in view submission: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to process submission'}), 500



def get_selected_users_from_view(values):
    """Retrieve selected users from the view state and filter out bots."""
    selected_users = []
    for block_id, block_values in values.items():
        if 'selected_users' in block_values:
            users = block_values['selected_users']['selected_users']
            selected_users.extend(filter_out_bots(users))
    return selected_users


def get_description_from_view(values):
    """Retrieve description from the view state."""
    for block_id, block_values in values.items():
        if 'description_input' in block_values:
            return block_values['description_input']['value']
    return "No description provided."

def open_modal(trigger_id):
    """Open a modal in Slack using an HTTP request."""
    modal_view = {
        "type": "modal",
        "callback_id": "user_selection_modal",
        "title": {"type": "plain_text", "text": "Select Users"},
        "blocks": [
            {
                "type": "input",
                "block_id": "user_selection_block",
                "label": {"type": "plain_text", "text": "Select users to forward the vulnerability."},
                "element": {
                    "type": "multi_users_select",
                    "placeholder": {"type": "plain_text", "text": "Select users"},
                    "action_id": "selected_users"
                }
            },
            {
                "type": "input",
                "block_id": "description_block",
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Provide details about the vulnerability"}
                }
            }
        ],
        "submit": {"type": "plain_text", "text": "Submit"}
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "trigger_id": trigger_id,
        "view": modal_view
    }
    try:
        response = requests.post("https://slack.com/api/views.open", headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for HTTP errors
        logger.debug(f"Modal response: {response.json()}")
        return jsonify({'status': 'Modal opened successfully'}), 200
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error opening modal: {e.response.text}")
        return jsonify({'status': 'Error opening modal'}), 500

def handle_user_selection(event):
    """Handle user selection action by opening a modal."""
    trigger_id = event.get('trigger_id')
    if trigger_id:
        return open_modal(trigger_id)
    else:
        logger.error("Trigger ID is missing in the event")
        return jsonify({'status': 'error', 'message': 'Trigger ID missing'}), 400

def handle_confirm(event, user_id):
    """Handle confirmation action."""
    logger.info(f"User {user_id} confirmed the vulnerability resolution.")
    
    # Notify the user that the task is completed
    send_completion_message(user_id)

    # Notify the admin that the task has been completed
    send_admin_notification(user_id)

    return jsonify({'status': 'ok'})

def filter_out_bots(selected_users):
    """Filter out bot users from the selected users."""
    filtered_users = []
    for user in selected_users:
        user_info = client.users_info(user=user)
        if not user_info['user']['is_bot']:
            filtered_users.append(user)
    return filtered_users

def send_completion_message(user_id):
    """Send a completion message to the user."""
    message = {
        "channel": user_id,
        "text": "You have successfully completed the task.",
    }
    try:
        client.chat_postMessage(**message)
    except SlackApiError as e:
        logger.error(f"Error sending completion message: {e.response['error']}")

def send_admin_notification(user_id):
    """Notify the admin that the user has completed the task."""
    message = {
        "channel": ADMIN_CHANNEL_ID,
        "text": f"User <@{user_id}> has completed the task.",
    }
    try:
        client.chat_postMessage(**message)
    except SlackApiError as e:
        logger.error(f"Error sending admin notification: {e.response['error']}")

if __name__ == '__main__':
    threading.Thread(target=run_scheduler).start()
    app.run(port=PORT)
