from flask import Flask, request, jsonify, redirect
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta

app = Flask(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Get the Replit URL from environment
REPLIT_URL = os.getenv('REPLIT_URL', '')  # You'll need to set this in Replit secrets

# Update the create_flow function in your main.py
def create_flow():
    """Create OAuth2 flow instance."""
    redirect_uri = "https://calendar-bot-1-darren8.replit.app/oauth2callback"  # Hardcode for now
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

def get_calendar_service():
    """Gets Google Calendar service with proper authentication."""
    creds = None

    # Load saved credentials from token.pickle
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If credentials are invalid or don't exist, redirect to auth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None

        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

class CalendarBot:
    def __init__(self):
        self.service = get_calendar_service()

    def add_event(self, title, start_time, end_time, description="", location="", attendees=None):
        """Add a new event to Google Calendar."""
        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            }
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        event = self.service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'
        ).execute()

        return event

    def get_upcoming_events(self, days=7):
        """Get upcoming events for the next specified days."""
        now = datetime.utcnow()
        time_max = now + timedelta(days=days)

        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

# Initialize bot (will be None until authenticated)
bot = None

@app.route('/')
def home():
    """Home page and auth check."""
    global bot

    if not os.path.exists('credentials.json'):
        return 'Error: credentials.json file not found. Please upload it to Replit.'

    if bot is None or bot.service is None:
        flow = create_flow()
        auth_url = flow.authorization_url()
        return f'<a href="{auth_url[0]}">Click here to authorize with Google Calendar</a>'

    return 'Calendar Bot is running and authenticated!'

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth2 callback from Google."""
    global bot

    flow = create_flow()
    flow.fetch_token(
        authorization_response=request.url,
        code=request.args.get('code')
    )

    credentials = flow.credentials
    with open('token.pickle', 'wb') as token:
        pickle.dump(credentials, token)

    bot = CalendarBot()
    return 'Successfully authenticated! You can close this window.'

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests."""
    global bot

    print("Webhook request received")  # Debug print

    if bot is None or bot.service is None:
        print("Bot not authenticated")  # Debug print
        return jsonify({'status': 'error', 'message': 'Bot not authenticated'}), 401

    try:
        data = request.get_json()
        print(f"Received data: {data}")  # Debug print

        action = data.get('action')
        print(f"Action: {action}")  # Debug print

        if action == 'add_event':
            details = data['eventDetails']
            print(f"Event details: {details}")  # Debug print

            start_time = datetime.fromisoformat(details['startDate'].replace('Z', ''))
            end_time = datetime.fromisoformat(details['endDate'].replace('Z', ''))

            event = bot.add_event(
                title=details['title'],
                start_time=start_time,
                end_time=end_time,
                description=details.get('description', ''),
                location=details.get('location', ''),
                attendees=[a['email'] for a in details.get('attendees', [])]
            )
            return jsonify({'status': 'success', 'event': event})

        # Add this else block to handle invalid actions
        else:
            print(f"Invalid action: {action}")  # Debug print
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")  # Debug print
        return jsonify({'status': 'error', 'message': str(e)}), 500

app.run(host='0.0.0.0', port=8080)