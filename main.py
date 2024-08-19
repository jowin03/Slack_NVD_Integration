import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
import json
import schedule
import time

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

SLACK_BOT_TOKEN = config['slack_bot_token']
ADMIN_CHANNEL = config['admin_channel']
NVD_API_URL = config['nvd_api_url']
PORT = config['port']

client = WebClient(token=SLACK_BOT_TOKEN)

def fetch_vulnerabilities(start=0, limit=50):
    """Fetch vulnerabilities from the NVD API with pagination."""
    params = {
        'startIndex': start,
        'resultsPerPage': limit
    }
    response = requests.get(NVD_API_URL, params=params)
    vulnerabilities = response.json()
    return vulnerabilities

def fetch_all_users():
    """Fetch all users in the Slack workspace with pagination and handle rate limits."""
    users_list = []
    cursor = None
    
    while True:
        try:
            response = client.users_list(cursor=cursor)
            users = response['members']
            for user in users:
                if not user['is_bot'] and user['id'] != 'USLACKBOT':
                    users_list.append({
                        "text": user['profile']['real_name'],
                        "value": user['id']
                    })
            
            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break

        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Retrying in {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Slack API error: {e.response['error']}")
                break

    return users_list

def send_vulnerability_to_admin(vulnerability):
    """Send the vulnerability details to the System Admin via Slack."""
    users_list = fetch_all_users()
    
    try:
        client.chat_postMessage(
            channel=ADMIN_CHANNEL,
            text=f"New Vulnerability Found: {vulnerability['descriptions'][0]['value']}",
            attachments=[
                {
                    "text": "Who should take care of this?",
                    "fallback": "You are unable to choose an option",
                    "callback_id": "vulnerability_action",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [
                        {
                            "name": "users_list",
                            "text": "Select a user...",
                            "type": "select",
                            "options": users_list
                        },
                        {
                            "name": "forward",
                            "text": "Forward",
                            "type": "button",
                            "value": "forward"
                        }
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Error sending message to admin: {e}")

def forward_vulnerability_to_user(vulnerability, user_id):
    """Forward the vulnerability details to the selected user."""
    try:
        client.chat_postMessage(
            channel=user_id,
            text=f"You have been assigned a new vulnerability: {vulnerability['descriptions'][0]['value']}",
            attachments=[
                {
                    "text": "Have you resolved this issue?",
                    "fallback": "You are unable to respond",
                    "callback_id": "resolve_vulnerability",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [
                        {
                            "name": "reply",
                            "text": "Reply",
                            "type": "button",
                            "value": "resolved"
                        }
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Error forwarding message to user {user_id}: {e}")

def handle_action(payload):
    """Handle actions from Slack (forward and reply buttons)."""
    action = payload['actions'][0]
    user_id = payload['user']['id']
    channel_id = payload['channel']['id']
    
    if action['name'] == 'users_list':
        selected_user_id = action['selected_options'][0]['value']
        vulnerability = fetch_vulnerabilities(start=0, limit=1)['vulnerabilities'][0]['cve']
        
        # Forward the vulnerability to the selected user
        forward_vulnerability_to_user(vulnerability, selected_user_id)
        
        # Acknowledge the action
        response = {
            "replace_original": False,
            "text": f"Vulnerability forwarded to <@{selected_user_id}> successfully.",
        }
        return jsonify(response)
        
    elif action['name'] == 'reply':
        client.chat_postMessage(
            channel=ADMIN_CHANNEL,
            text=f"User <@{user_id}> has resolved the issue."
        )
        client.chat_postMessage(
            channel=channel_id,
            text="Thank you for resolving the issue!"
        )
        return jsonify({'status': 'ok'})

def job():
    """Scheduled job to fetch vulnerabilities and notify the admin."""
    start = 0
    limit = 50
    while True:
        vulnerabilities = fetch_vulnerabilities(start=start, limit=limit)
        if not vulnerabilities['vulnerabilities']:
            break
        for vulnerability in vulnerabilities['vulnerabilities']:
            send_vulnerability_to_admin(vulnerability['cve'])
        start += limit

# Schedule the job to run every minute at 00:15
schedule.every().minute.at(":15").do(job)

app = Flask(__name__)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.form
    print("Received data:", data)  # Debugging line to inspect incoming data

    # Check if the payload is present in the data
    if not data or "payload" not in data:
        print("Error: Received empty data or no payload found.")
        return jsonify({'status': 'error', 'message': 'Empty data or no payload found'})

    # Parse the payload
    payload = json.loads(data["payload"])
    print("Parsed payload:", payload)  # Debugging line to inspect parsed payload
    
    # Handle interactive message events
    if 'type' in payload and payload['type'] == 'interactive_message':
        return handle_action(payload)
    
    # Handle URL verification for Slack event subscriptions
    if "challenge" in data:
        return jsonify({'challenge': data['challenge']})

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # Start the scheduler in a separate thread
    import threading
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Run the Flask app
    app.run(port=PORT)
