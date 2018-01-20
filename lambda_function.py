from __future__ import print_function

import json

import requests

lake_lanier_url = "https://waterservices.usgs.gov/nwis/iv/?site=02334400&parameterCd=00062&format=json"


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


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------


def get_lake_level():
    r = requests.get(lake_lanier_url)
    data = json.loads(r.text)
    lake_level = data["value"]["timeSeries"][0]["values"][0]["value"][0]["value"]
    session_attributes = {}
    card_title = "Lake Level"
    speech_output = "Lake Lanier is currently {level} feet above sea level".format(level=lake_level)
    reprompt_text = "Lake Lanier is currently {level} feet above sea level".format(level=lake_level)
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_next_president():
    session_attributes = {}
    card_title = "Next President"
    speech_output = "Bernie Sanders will win the presidential election in 2020"
    reprompt_text = "Bernie Sanders will win the presidential election in 2020"
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
    speech_output = "The Chaps Kitty skill can tell you many things that Chaps Kitty knows, for example, " \
                    "you can ask Chaps Kitty what the current lake level is."
    reprompt_text = "Ask Chaps Kitty a question that you think Chaps Kitty might know"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Please remember the Chaps Kitty skill the next time you have a question that " \
                    "you think Chaps Kitty may know the answer two."
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    return get_welcome_response()


def on_intent(intent_request, session):
    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent_name = intent_request['intent']['name']

    if intent_name == "LakeLevel":
        return get_lake_level()
    if intent_name == "NextPrez":
        return get_next_president()
    if intent_name == "Schnoozins":
        return get_the_schnoozinist()
    if intent_name == "Treats":
        return get_treat_storage_location()
    if intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    if intent_name == "AMAZON.CancelIntent":
        return handle_session_end_request()
    if intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])


# --------------- Main handler ------------------

def lambda_handler(event, context):
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill.d63439df-7309-4d8a-be34-e223a9850846"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
