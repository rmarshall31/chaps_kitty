import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambda"))

import chaps_kitty as ck  # noqa: E402


SKILL_ID = ck.SKILL_ID
USGS_BODY = {
    "value": {
        "timeSeries": [{
            "values": [{
                "value": [{"value": "1071.23"}]
            }]
        }]
    }
}


def session_event(request_type, intent_name=None, attributes=None,
                  new=False, app_id=SKILL_ID):
    event = {
        "session": {
            "new": new,
            "sessionId": "s1",
            "application": {"applicationId": app_id},
            "attributes": attributes or {},
        },
        "request": {
            "type": request_type,
            "requestId": "r1",
        },
    }
    if intent_name:
        event["request"]["intent"] = {"name": intent_name}
    return event


def audio_event(request_type="AudioPlayer.PlaybackStarted"):
    return {
        "context": {
            "System": {
                "application": {"applicationId": SKILL_ID},
            },
            "AudioPlayer": {
                "token": "angry-chaps-kitty-abc",
                "offsetInMilliseconds": 1200,
            },
        },
        "request": {
            "type": request_type,
            "requestId": "r2",
        },
    }


class FakeHttpResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class HandlerTests(unittest.TestCase):
    def test_audioplayer_without_session_does_not_raise(self):
        result = ck.handler(audio_event(), None)
        self.assertEqual(result["response"], {})

    def test_wrong_app_id_raises(self):
        event = session_event("LaunchRequest", app_id="nope")
        with self.assertRaises(ValueError):
            ck.handler(event, None)

    def test_welcome_stores_last_speech(self):
        event = session_event("LaunchRequest", new=True)
        result = ck.handler(event, None)
        self.assertIn(
            "last_speech_output", result["sessionAttributes"])
        self.assertIn(
            "lake level",
            result["sessionAttributes"]["last_speech_output"])

    def test_repeat_uses_stored_speech(self):
        event = session_event(
            "IntentRequest",
            "AMAZON.RepeatIntent",
            attributes={"last_speech_output": "meow"},
        )
        result = ck.handler(event, None)
        self.assertEqual(
            result["response"]["outputSpeech"]["text"], "meow")

    def test_unknown_intent_speaks_instead_of_raising(self):
        event = session_event("IntentRequest", "NotARealIntent")
        result = ck.handler(event, None)
        self.assertIn(
            "does not know",
            result["response"]["outputSpeech"]["text"])

    def test_navigate_home_ends_session(self):
        event = session_event(
            "IntentRequest", "AMAZON.NavigateHomeIntent")
        result = ck.handler(event, None)
        self.assertTrue(result["response"]["shouldEndSession"])

    def test_resume_uses_audioplayer_context(self):
        event = audio_event()
        event["session"] = {
            "new": False,
            "sessionId": "s1",
            "application": {"applicationId": SKILL_ID},
            "attributes": {},
        }
        event["request"] = {
            "type": "IntentRequest",
            "requestId": "r3",
            "intent": {"name": "AMAZON.ResumeIntent"},
        }
        result = ck.handler(event, None)
        stream = result["response"]["directives"][0]["audioItem"]["stream"]
        self.assertEqual(stream["token"], "angry-chaps-kitty-abc")
        self.assertEqual(stream["offsetInMilliseconds"], 1200)

    def test_play_tokens_are_not_frozen_at_import(self):
        first = ck.duck_with_blue_and_chief()
        second = ck.duck_with_blue_and_chief()
        t1 = first["response"]["directives"][0]["audioItem"]["stream"]["token"]
        t2 = second["response"]["directives"][0]["audioItem"]["stream"]["token"]
        self.assertNotEqual(t1, t2)


class LakeLevelTests(unittest.TestCase):
    def test_fetch_parses_usgs_json(self):
        body = json.dumps(USGS_BODY).encode()
        with mock.patch(
                "chaps_kitty.urllib.request.urlopen",
                return_value=FakeHttpResponse(body)):
            self.assertEqual(ck.fetch_lake_level(), "1071.23")

    def test_get_lake_level_survives_usgs_failure(self):
        with mock.patch(
                "chaps_kitty.urllib.request.urlopen",
                side_effect=URLError("timeout")):
            result = ck.get_lake_level()
        self.assertIn(
            "could not find the lake level",
            result["response"]["outputSpeech"]["text"])


class TideTests(unittest.TestCase):
    def test_upcoming_tides_skips_past_and_takes_next_two(self):
        now = ck.parse_tide_time("2026-09-13 12:00")
        predictions = [
            {"t": "2026-09-13 01:53", "v": "2.25", "type": "H"},
            {"t": "2026-09-13 09:03", "v": "0.541", "type": "L"},
            {"t": "2026-09-13 15:00", "v": "2.109", "type": "H"},
            {"t": "2026-09-13 20:59", "v": "1.187", "type": "L"},
        ]
        events = ck.upcoming_tides(predictions, now)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][1], "high")
        self.assertEqual(events[1][1], "low")
        speech = ck.format_tide_speech(events, now)
        self.assertIn("high", speech)
        self.assertIn("2.1 feet", speech)
        self.assertIn("3 PM", speech)
        self.assertIn("low tide", speech)

    def test_get_gulfport_tide_survives_noaa_failure(self):
        with mock.patch(
                "chaps_kitty.urllib.request.urlopen",
                side_effect=URLError("timeout")):
            result = ck.get_gulfport_tide()
        self.assertIn(
            "could not find the Gulfport tide",
            result["response"]["outputSpeech"]["text"])

    def test_tide_intent_routes(self):
        event = session_event("IntentRequest", "Tide")
        with mock.patch(
                "chaps_kitty.get_gulfport_tide",
                return_value={"ok": True}):
            self.assertEqual(ck.handler(event, None), {"ok": True})


if __name__ == "__main__":
    unittest.main()
