from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta
import sys

app = Flask(__name__)
app.debug = True

# Enable HTTPS traffic for OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def print_debug(message):
    """Helper function to ensure debug messages are printed"""
    print(message, file=sys.stderr, flush=True)

def create_flow():
    """Create OAuth2 flow instance with debug logging."""
    print_debug("Creating OAuth flow")
    redirect_uri = "https://calendar-bot-1-darren8.replit.app/oauth2callback"
    try:
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        print_debug("OAuth flow created successfully")
        return flow
    except Exception as e:
        print_debug(f"Error creating flow: {str(e)}")
        raise

@app.route('/')
def home():
    """Home page and auth check with debug logging."""
    print_debug("\n=== Checking Authentication ===")
    print_debug(f"Current directory: {os.getcwd()}")
    print_debug(f"Files in directory: {os.listdir()}")

    if os.path.exists('token.pickle'):
        print_debug("token.pickle exists")
        try:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                print_debug("Successfully loaded credentials from token.pickle")
                return 'Calendar Bot is running and authenticated!'
        except Exception as e:
            print_debug(f"Error loading token.pickle: {str(e)}")
    else:
        print_debug("token.pickle does not exist")

    if not os.path.exists('credentials.json'):
        print_debug("credentials.json not found")
        return 'Error: credentials.json file not found'

    try:
        flow = create_flow()
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        return f'<a href="{auth_url}">Click here to authorize with Google Calendar</a>'
    except Exception as e:
        error_msg = f"Error creating authorization URL: {str(e)}"
        print_debug(error_msg)
        return error_msg

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth2 callback with detailed logging."""
    print_debug("\n=== OAuth Callback Started ===")

    try:
        print_debug("Creating flow")
        flow = create_flow()

        print_debug("Fetching token")
        flow.fetch_token(
            authorization_response=request.url
        )

        print_debug("Token fetched successfully")
        credentials = flow.credentials

        print_debug("Attempting to save token.pickle")
        try:
            with open('token.pickle', 'wb') as token:
                pickle.dump(credentials, token)
            print_debug("token.pickle saved successfully")
        except Exception as e:
            print_debug(f"Error saving token.pickle: {str(e)}")
            raise

        print_debug("Checking if token.pickle was created")
        if os.path.exists('token.pickle'):
            size = os.path.getsize('token.pickle')
            print_debug(f"token.pickle exists, size: {size} bytes")
        else:
            print_debug("token.pickle was not created")

        return 'Successfully authenticated! You can close this window.'

    except Exception as e:
        error_msg = f"Error in OAuth callback: {str(e)}"
        print_debug(error_msg)
        return error_msg

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    print_debug("\n=== Webhook Request Received ===")

    if not os.path.exists('token.pickle'):
        print_debug("No token.pickle found - not authenticated")
        return jsonify({'status': 'error', 'message': 'Bot not authenticated'}), 401

    try:
        data = request.get_json()
        print_debug(f"Received webhook data: {data}")

        # Load credentials
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

        service = build('calendar', 'v3', credentials=credentials)

        # Process the event
        if data['action'] == 'add_event':
            event_details = data['eventDetails']

            event = {
                'summary': event_details['title'],
                'description': event_details.get('description', ''),
                'start': {
                    'dateTime': event_details['startDate'],
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': event_details['endDate'],
                    'timeZone': 'UTC',
                }
            }

            # Add attendees if provided
            if 'attendees' in event_details:
                event['attendees'] = event_details['attendees']

            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()

            print_debug(f"Event created: {created_event}")
            return jsonify({
                'status': 'success',
                'event': created_event
            })

        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

    except Exception as e:
        print_debug(f"Error in webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    print_debug("Starting Calendar Bot...")
    app.run(host='0.0.0.0', port=8080)