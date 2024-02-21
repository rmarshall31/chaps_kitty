import json
import uuid

import requests

LAKE_LANIER_URL = "https://waterservices.usgs.gov/nwis/iv/?site=02334400&parameterCd=00062&format=json"
ANGRY_CHAPS_KITTY_MP3 = "https://s3.amazonaws.com/chapskitty/cat.mp3"


# --------------- Helpers that build all of the responses ----------------------

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


# --------------- Functions that control the skill's behavior ------------------


def get_lake_level():
    r = requests.get(LAKE_LANIER_URL)
    data = json.loads(r.text)
    lake_level = data["value"]["timeSeries"][0]["values"][0]["value"][0]["value"]
    session_attributes = {}
    card_title = "Lake Level"
    speech_output = f"Lake Lanier is currently {lake_level} feet above sea level"
    reprompt_text = f"Lake Lanier is currently {lake_level} feet above sea level"
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_the_schnoozinist():
    session_attributes = {}
    card_title = "The Schnoozinist"
    speech_output = "Chaps kitty is the schnoozinist kitty"
    reprompt_text = "Chaps kitty is the schnoozinist kitty"
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_treat_storage_location():
    session_attributes = {}
    card_title = "Treat storage"
    speech_output = "In the bellies, the bellies for the treats"
    reprompt_text = "In the bellies, the bellies for the treats"
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_welcome_response():
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "The Chaps Kitty skill can tell you many things that Chaps Kitty knows, for example, " \
                    "you can ask Chaps Kitty what the current lake level is."
    reprompt_text = "Ask Chaps Kitty a question that you think Chaps Kitty might know"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_help_response():
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "The Chaps Kitty skill can tell you many things that Chaps Kitty knows, for example, you can ask" \
                    "Chaps Kitty what the current lake level is. What would you like Chaps Kitty to tell you about?"
    reprompt_text = "Ask Chaps Kitty a question that you think Chaps Kitty might know"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Please remember the Chaps Kitty skill the next time you have a question that " \
                    "you think Chaps Kitty may know the answer to."
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def handle_repeat_intent(session_attributes):
    last_speech_output = session_attributes.get('last_speech_output', 'Sorry, I don\'t remember what I said last.')
    card_title = "Repeat"
    reprompt_text = last_speech_output
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, last_speech_output, reprompt_text, should_end_session))


def duck_with_blue_and_chief(token=f"angry-chaps-kitty-{uuid.uuid4()}", offset_in_milliseconds=0):
    print("ducking with blue and chief")
    response = {
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

    return response


def handle_pause_intent(session_attributes):
    response = {
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
    return response


def handle_resume_intent(session_attributes):
    token = session_attributes.get("token", "")
    offset_in_milliseconds = session_attributes.get("offsetInMilliseconds", 0)
    return duck_with_blue_and_chief(token, offset_in_milliseconds)


def handle_previous_intent():
    return duck_with_blue_and_chief()


def handle_start_over_intent():
    return duck_with_blue_and_chief()


def handle_next_intent():
    return duck_with_blue_and_chief()


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    print(f"on_session_started requestId={session_started_request['requestId']}, sessionId={session['sessionId']}")


def on_launch(launch_request, session):
    print(f"on_launch requestId={launch_request['requestId']}, sessionId={session['sessionId']}")
    return get_welcome_response()


def on_intent(intent_request, session):
    print(f"on_intent requestId={intent_request['requestId']}, sessionId={session['sessionId']}")

    intent_name = intent_request['intent']['name']

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
    elif intent_name == "AMAZON.CancelIntent":
        return handle_session_end_request()
    elif intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    elif intent_name == "AMAZON.RepeatIntent":
        return handle_repeat_intent(session.get('attributes', {}))
    elif intent_name == "AMAZON.PauseIntent":
        return handle_pause_intent(session.get('attributes', {}))
    elif intent_name == "AMAZON.ResumeIntent":
        return handle_resume_intent(session.get('attributes', {}))
    elif intent_name == "AMAZON.PreviousIntent":
        return handle_previous_intent()
    elif intent_name == "AMAZON.StartOverIntent":
        return handle_start_over_intent()
    elif intent_name == "AMAZON.NextIntent":
        return handle_next_intent()

    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    print(f"on_session_ended requestId={session_ended_request['requestId']}, sessionId={session['sessionId']}")


# --------------- Main handler ------------------

def handler(event, context):
    print(f"event.session.application.applicationId={event['session']['application']['applicationId']}")

    if (event['session']['application']['applicationId'] != "amzn1.ask.skill.d63439df-7309-4d8a-be34-e223a9850846"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']}, event['session'])
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    if event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    if event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
