import json
import uuid
import urllib.error
import urllib.request

SKILL_ID = "amzn1.ask.skill.d63439df-7309-4d8a-be34-e223a9850846"
LAKE_LANIER_URL = (
    "https://waterservices.usgs.gov/nwis/iv/"
    "?site=02334400&parameterCd=00062&format=json"
)
ANGRY_CHAPS_KITTY_MP3 = "https://s3.amazonaws.com/chapskitty/cat.mp3"
USGS_TIMEOUT_SECONDS = 5
USER_AGENT = "chaps-kitty-alexa-skill"


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
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


def build_ssml_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': "SSML",
            'ssml': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': "SSML",
                'ssml': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


def empty_response():
    return {
        'version': '1.0',
        'response': {}
    }


def speak(title, output, reprompt_text, should_end_session,
          session_attributes=None):
    attrs = dict(session_attributes or {})
    attrs['last_speech_output'] = output
    return build_response(attrs, build_speechlet_response(
        title, output, reprompt_text, should_end_session))


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


def fetch_lake_level():
    req = urllib.request.Request(
        LAKE_LANIER_URL,
        headers={'User-Agent': USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=USGS_TIMEOUT_SECONDS) as resp:
        data = json.load(resp)
    return data['value']['timeSeries'][0]['values'][0]['value'][0]['value']


def get_lake_level():
    try:
        lake_level = fetch_lake_level()
        speech_output = (
            f"Lake Lanier is currently {lake_level} feet above sea level"
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
            KeyError, IndexError, TypeError, OSError):
        speech_output = (
            "Chaps kitty could not find the lake level right now."
        )
    return speak(
        "Lake Level", speech_output, speech_output, True)


def get_the_schnoozinist():
    speech_output = "Chaps kitty is the schnoozinist kitty"
    return speak(
        "The Schnoozinist", speech_output, speech_output, True)


def get_treat_storage_location():
    speech_output = "In the bellies, the bellies for the treats"
    return speak(
        "Treat storage", speech_output, speech_output, True)


def get_welcome_response():
    speech_output = (
        "The Chaps Kitty skill can tell you many things that Chaps Kitty "
        "knows, for example, you can ask Chaps Kitty what the current "
        "lake level is."
    )
    reprompt_text = (
        "Ask Chaps Kitty a question that you think Chaps Kitty might know"
    )
    return speak("Welcome", speech_output, reprompt_text, False)


def get_help_response():
    speech_output = (
        "The Chaps Kitty skill can tell you many things that Chaps Kitty "
        "knows, for example, you can ask Chaps Kitty what the current "
        "lake level is. What would you like Chaps Kitty to tell you about?"
    )
    reprompt_text = (
        "Ask Chaps Kitty a question that you think Chaps Kitty might know"
    )
    return speak("Welcome", speech_output, reprompt_text, False)


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
    print("ducking with blue and chief")
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


def handle_resume_intent(event):
    token, offset_in_milliseconds = audio_player_state(event)
    return duck_with_blue_and_chief(token, offset_in_milliseconds)


def handle_previous_intent():
    return duck_with_blue_and_chief()


def handle_start_over_intent():
    return duck_with_blue_and_chief()


def handle_next_intent():
    return duck_with_blue_and_chief()


def on_session_started(session_started_request, session):
    print(
        f"on_session_started requestId="
        f"{session_started_request['requestId']}, "
        f"sessionId={session['sessionId']}"
    )


def on_launch(launch_request, session):
    print(
        f"on_launch requestId={launch_request['requestId']}, "
        f"sessionId={session.get('sessionId')}"
    )
    return get_welcome_response()


def on_intent(intent_request, session, event):
    print(
        f"on_intent requestId={intent_request['requestId']}, "
        f"sessionId={session.get('sessionId')}"
    )

    intent_name = intent_request['intent']['name']
    session_attributes = session.get('attributes') or {}

    if intent_name == "LakeLevel":
        return get_lake_level()
    elif intent_name == "Schnoozins":
        return get_the_schnoozinist()
    elif intent_name == "Treats":
        return get_treat_storage_location()
    elif intent_name == "AntagonizeDogs":
        return duck_with_blue_and_chief()
    elif intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    elif intent_name in (
            "AMAZON.CancelIntent",
            "AMAZON.StopIntent",
            "AMAZON.NavigateHomeIntent"):
        return handle_session_end_request()
    elif intent_name == "AMAZON.RepeatIntent":
        return handle_repeat_intent(session_attributes)
    elif intent_name == "AMAZON.PauseIntent":
        return handle_pause_intent(session_attributes)
    elif intent_name == "AMAZON.ResumeIntent":
        return handle_resume_intent(event)
    elif intent_name == "AMAZON.PreviousIntent":
        return handle_previous_intent()
    elif intent_name == "AMAZON.StartOverIntent":
        return handle_start_over_intent()
    elif intent_name == "AMAZON.NextIntent":
        return handle_next_intent()

    speech_output = "Chaps kitty does not know about that."
    return speak("Unknown", speech_output, speech_output, False)


def on_session_ended(session_ended_request, session):
    print(
        f"on_session_ended requestId={session_ended_request['requestId']}, "
        f"sessionId={session.get('sessionId')}"
    )
    return empty_response()


def handler(event, context):
    app_id = application_id(event)
    print(f"applicationId={app_id}")
    if app_id != SKILL_ID:
        raise ValueError("Invalid Application ID")

    session = event.get('session') or {}
    request = event['request']
    if session.get('new'):
        on_session_started(
            {'requestId': request['requestId']}, session)

    request_type = request['type']
    if request_type == "LaunchRequest":
        return on_launch(request, session)
    if request_type == "IntentRequest":
        return on_intent(request, session, event)
    if request_type == "SessionEndedRequest":
        return on_session_ended(request, session)
    if (request_type.startswith("AudioPlayer.")
            or request_type == "System.ExceptionEncountered"):
        return empty_response()
    return empty_response()
