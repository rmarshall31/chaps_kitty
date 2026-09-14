import json
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SKILL_ID = "amzn1.ask.skill.d63439df-7309-4d8a-be34-e223a9850846"
LAKE_LANIER_URL = (
    "https://waterservices.usgs.gov/nwis/iv/"
    "?site=02334400&parameterCd=00062&format=json"
)
ANGRY_CHAPS_KITTY_MP3 = "https://s3.amazonaws.com/chapskitty/cat.mp3"
GULFPORT_STATION = "8726486"
GULFPORT_TZ = ZoneInfo("America/New_York")
HTTP_TIMEOUT_SECONDS = 5
USER_AGENT = "chaps-kitty-alexa-skill"
REPROMPT = (
    "Ask Chaps Kitty a question that you think Chaps Kitty might know"
)
HTTP_FETCH_ERRORS = (
    urllib.error.URLError, TimeoutError, json.JSONDecodeError,
    KeyError, IndexError, TypeError, OSError,
)
PLAY_INTENTS = (
    "AntagonizeDogs",
    "AMAZON.PreviousIntent",
    "AMAZON.StartOverIntent",
    "AMAZON.NextIntent",
)
END_INTENTS = (
    "AMAZON.CancelIntent",
    "AMAZON.StopIntent",
    "AMAZON.NavigateHomeIntent",
)


def empty_response():
    return {
        'version': '1.0',
        'response': {}
    }


def speak(title, output, reprompt_text, should_end_session,
          session_attributes=None):
    attrs = dict(session_attributes or {})
    attrs['last_speech_output'] = output
    return {
        'version': '1.0',
        'sessionAttributes': attrs,
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': output
            },
            'card': {
                'type': 'Simple',
                'title': title,
                'content': output
            },
            'reprompt': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': reprompt_text
                }
            },
            'shouldEndSession': should_end_session
        }
    }


def application_id(event):
    session_app = (event.get('session') or {}).get('application') or {}
    if session_app.get('applicationId'):
        return session_app['applicationId']
    system = (event.get('context') or {}).get('System') or {}
    return (system.get('application') or {}).get('applicationId')


def audio_player_state(event):
    player = (event.get('context') or {}).get('AudioPlayer') or {}
    return (
        player.get('token') or '',
        player.get('offsetInMilliseconds') or 0,
    )


def http_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        return json.load(resp)


def fetch_lake_level():
    data = http_json(LAKE_LANIER_URL)
    return data['value']['timeSeries'][0]['values'][0]['value'][0]['value']


def tide_predictions_url(now=None):
    now = now or datetime.now(GULFPORT_TZ)
    start = now.strftime("%Y%m%d")
    return (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?begin_date={start}&range=48&station={GULFPORT_STATION}"
        "&product=predictions&datum=MLLW&time_zone=lst_ldt"
        "&units=english&interval=hilo&format=json"
        f"&application={USER_AGENT}"
    )


def parse_tide_time(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(
        tzinfo=GULFPORT_TZ)


def upcoming_tides(predictions, now):
    events = []
    for row in predictions:
        when = parse_tide_time(row['t'])
        if when < now:
            continue
        kind = 'high' if row.get('type') == 'H' else 'low'
        events.append((when, kind, row['v']))
        if len(events) == 2:
            break
    return events


def format_tide_height(value):
    feet = round(float(value), 1)
    if feet == int(feet):
        return f"{int(feet)} feet"
    return f"{feet} feet"


def format_tide_when(when, now):
    clock = when.strftime("%-I:%M %p").replace(":00 ", " ")
    if when.date() == now.date():
        return f"at {clock}"
    if when.date() == (now + timedelta(days=1)).date():
        return f"tomorrow at {clock}"
    return f"on {when.strftime('%A')} at {clock}"


def format_tide_speech(events, now):
    first_when, first_kind, first_height = events[0]
    speech = (
        f"The next tide at Gulfport is {first_kind}, "
        f"{format_tide_height(first_height)}, "
        f"{format_tide_when(first_when, now)}."
    )
    if len(events) > 1:
        next_when, next_kind, next_height = events[1]
        speech += (
            f" After that, {next_kind} tide is "
            f"{format_tide_height(next_height)} "
            f"{format_tide_when(next_when, now)}."
        )
    return speech


def get_gulfport_tide(now=None):
    now = now or datetime.now(GULFPORT_TZ)
    try:
        data = http_json(tide_predictions_url(now))
        events = upcoming_tides(data['predictions'], now)
        if not events:
            raise ValueError("no upcoming tides")
        speech_output = format_tide_speech(events, now)
    except HTTP_FETCH_ERRORS + (ValueError,):
        speech_output = (
            "Chaps kitty could not find the Gulfport tide right now."
        )
    return speak("Tide", speech_output, speech_output, True)


def get_lake_level():
    try:
        lake_level = fetch_lake_level()
        speech_output = (
            f"Lake Lanier is currently {lake_level} feet above sea level"
        )
    except HTTP_FETCH_ERRORS:
        speech_output = (
            "Chaps kitty could not find the lake level right now."
        )
    return speak(
        "Lake Level", speech_output, speech_output, True)


def get_welcome_response():
    speech_output = (
        "The Chaps Kitty skill can tell you many things that Chaps Kitty "
        "knows, for example, you can ask Chaps Kitty what the current "
        "lake level is, or what the tide is in Gulfport."
    )
    return speak("Welcome", speech_output, REPROMPT, False)


def get_help_response():
    speech_output = (
        "The Chaps Kitty skill can tell you many things that Chaps Kitty "
        "knows, for example, you can ask about the lake level or the "
        "Gulfport tide. What would you like Chaps Kitty to tell you about?"
    )
    return speak("Welcome", speech_output, REPROMPT, False)


def handle_session_end_request():
    speech_output = (
        "Please remember the Chaps Kitty skill the next time you have a "
        "question that you think Chaps Kitty may know the answer to."
    )
    return speak("Session Ended", speech_output, None, True)


def handle_repeat_intent(session_attributes):
    last_speech_output = session_attributes.get(
        'last_speech_output',
        "Sorry, I don't remember what I said last.",
    )
    return speak(
        "Repeat", last_speech_output, last_speech_output, False,
        session_attributes)


def duck_with_blue_and_chief(token=None, offset_in_milliseconds=0):
    if not token:
        token = f"angry-chaps-kitty-{uuid.uuid4()}"
    return {
        "version": "1.0",
        "response": {
            "directives": [
                {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "REPLACE_ALL",
                    "audioItem": {
                        "stream": {
                            "token": token,
                            "url": ANGRY_CHAPS_KITTY_MP3,
                            "offsetInMilliseconds": offset_in_milliseconds
                        }
                    }
                }
            ],
            "shouldEndSession": True
        }
    }


def handle_pause_intent(session_attributes):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": {
            "directives": [
                {
                    "type": "AudioPlayer.Stop"
                }
            ],
            "shouldEndSession": True
        }
    }


def on_intent(intent_request, session, event):
    intent_name = intent_request['intent']['name']
    session_attributes = session.get('attributes') or {}

    if intent_name == "LakeLevel":
        return get_lake_level()
    if intent_name == "Tide":
        return get_gulfport_tide()
    if intent_name == "Schnoozins":
        return speak(
            "The Schnoozinist",
            "Chaps kitty is the schnoozinist kitty",
            "Chaps kitty is the schnoozinist kitty",
            True)
    if intent_name == "Treats":
        return speak(
            "Treat storage",
            "In the bellies, the bellies for the treats",
            "In the bellies, the bellies for the treats",
            True)
    if intent_name in PLAY_INTENTS:
        return duck_with_blue_and_chief()
    if intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    if intent_name in END_INTENTS:
        return handle_session_end_request()
    if intent_name == "AMAZON.RepeatIntent":
        return handle_repeat_intent(session_attributes)
    if intent_name == "AMAZON.PauseIntent":
        return handle_pause_intent(session_attributes)
    if intent_name == "AMAZON.ResumeIntent":
        return duck_with_blue_and_chief(*audio_player_state(event))

    speech_output = "Chaps kitty does not know about that."
    return speak("Unknown", speech_output, speech_output, False)


def handler(event, context):
    if application_id(event) != SKILL_ID:
        raise ValueError("Invalid Application ID")

    session = event.get('session') or {}
    request = event['request']
    request_type = request['type']
    if request_type == "LaunchRequest":
        return get_welcome_response()
    if request_type == "IntentRequest":
        return on_intent(request, session, event)
    return empty_response()
