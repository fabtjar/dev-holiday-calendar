import json
import os.path
import pickle

from datetime import datetime

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.join(DIR_PATH, 'config.json')
TOKEN_PICKLE_PATH = os.path.join(DIR_PATH, 'token.pickle')
CREDENTIALS_PATH = os.path.join(DIR_PATH, 'credentials.json')


def get_config():
    with open(CONFIG_PATH, 'rb') as f:
        return json.load(f)


def get_credentials():
    credentials = None

    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, 'rb') as f:
            credentials = pickle.load(f)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                ['https://www.googleapis.com/auth/calendar.events']
            )
            credentials = flow.run_console()

        with open(TOKEN_PICKLE_PATH, 'wb') as f:
            pickle.dump(credentials, f)

    return credentials


def clear_dev_calendar(calendar_events, config):
    old_dev_holidays = get_calendar_events(calendar_events, config['calendar_ids']['dev'])

    for holiday in old_dev_holidays:
        calendar_events.delete(
            calendarId=config['calendar_ids']['dev'], eventId=holiday['id']
        ).execute()


def add_dev_holidays(calendar_events, config):
    all_holidays = get_calendar_events(calendar_events, config['calendar_ids']['holiday'])

    dev_holidays = []
    for holiday in all_holidays:
        try:
            name = holiday['summary'].split('-')[1].strip()
        except (IndexError, KeyError):
            continue

        if name in config['names']:
            dev_holidays.append({
                'summary': holiday['summary'],
                'start': {'date': holiday['start']['date']},
                'end': {'date': holiday['end']['date']}
            })

    for holiday in dev_holidays:
        calendar_events.insert(calendarId=config['calendar_ids']['dev'], body=holiday).execute()


def get_calendar_events(calendar_events, calendar_id):
    start_time = f'{datetime.now().year - 1}-01-01T00:00:00Z'

    events = []
    page_token = None
    while True:
        page_events = calendar_events.list(
            calendarId=calendar_id, pageToken=page_token, timeMin=start_time
        ).execute()
        events += page_events['items']
        page_token = page_events.get('nextPageToken')
        if not page_token:
            break
    return events


def main():
    config = get_config()
    service = build('calendar', 'v3', credentials=get_credentials())

    clear_dev_calendar(service.events(), config)
    add_dev_holidays(service.events(), config)


if __name__ == '__main__':
    main()
