import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lambda'))

import chaps_kitty as ck


SKILL_ID = ck.SKILL_ID
USGS_BODY = {'value': {'timeSeries': [{'values': [{'value': [{'value': '1071.23'}]}]}]}}


def session_event(request_type, intent_name=None, attributes=None, new=False, app_id=SKILL_ID):
    event = {
        'session': {
            'new': new,
            'sessionId': 's1',
            'application': {'applicationId': app_id},
            'attributes': attributes or {},
        },
        'request': {
            'type': request_type,
            'requestId': 'r1',
        },
    }
    if intent_name:
        event['request']['intent'] = {'name': intent_name}
    return event


def audio_event(request_type='AudioPlayer.PlaybackStarted'):
    return {
        'context': {
            'System': {
                'application': {'applicationId': SKILL_ID},
            },
            'AudioPlayer': {
                'token': 'angry-chaps-kitty-abc',
                'offsetInMilliseconds': 1200,
            },
        },
        'request': {
            'type': request_type,
            'requestId': 'r2',
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
        self.assertEqual(result['response'], {})

    def test_wrong_app_id_raises(self):
        event = session_event('LaunchRequest', app_id='nope')
        with self.assertRaises(ValueError):
            ck.handler(event, None)

    def test_welcome_stores_last_speech(self):
        event = session_event('LaunchRequest', new=True)
        result = ck.handler(event, None)
        self.assertIn('last_speech_output', result['sessionAttributes'])
        self.assertIn('lake level', result['sessionAttributes']['last_speech_output'])

    def test_repeat_uses_stored_speech(self):
        event = session_event(
            'IntentRequest',
            'AMAZON.RepeatIntent',
            attributes={'last_speech_output': 'meow'},
        )
        result = ck.handler(event, None)
        self.assertEqual(result['response']['outputSpeech']['text'], 'meow')

    def test_unknown_intent_speaks_instead_of_raising(self):
        event = session_event('IntentRequest', 'NotARealIntent')
        result = ck.handler(event, None)
        self.assertIn('does not know', result['response']['outputSpeech']['text'])

    def test_navigate_home_ends_session(self):
        event = session_event('IntentRequest', 'AMAZON.NavigateHomeIntent')
        result = ck.handler(event, None)
        self.assertTrue(result['response']['shouldEndSession'])

    def test_resume_uses_audioplayer_context(self):
        event = audio_event()
        event['session'] = {
            'new': False,
            'sessionId': 's1',
            'application': {'applicationId': SKILL_ID},
            'attributes': {},
        }
        event['request'] = {
            'type': 'IntentRequest',
            'requestId': 'r3',
            'intent': {'name': 'AMAZON.ResumeIntent'},
        }
        result = ck.handler(event, None)
        stream = result['response']['directives'][0]['audioItem']['stream']
        self.assertEqual(stream['token'], 'angry-chaps-kitty-abc')
        self.assertEqual(stream['offsetInMilliseconds'], 1200)

    def test_play_tokens_are_not_frozen_at_import(self):
        first = ck.duck_with_blue_and_chief()
        second = ck.duck_with_blue_and_chief()
        t1 = first['response']['directives'][0]['audioItem']['stream']['token']
        t2 = second['response']['directives'][0]['audioItem']['stream']['token']
        self.assertNotEqual(t1, t2)


class LakeLevelTests(unittest.TestCase):
    def test_fetch_parses_usgs_json(self):
        body = json.dumps(USGS_BODY).encode()
        with mock.patch('chaps_kitty.urllib.request.urlopen', return_value=FakeHttpResponse(body)):
            self.assertEqual(ck.fetch_lake_level(), '1071.23')

    def test_get_lake_level_survives_usgs_failure(self):
        with mock.patch('chaps_kitty.urllib.request.urlopen', side_effect=URLError('timeout')):
            result = ck.get_lake_level()
        self.assertIn('could not find the lake level', result['response']['outputSpeech']['text'])


class TideTests(unittest.TestCase):
    def test_upcoming_tides_skips_past_and_takes_next_two(self):
        now = ck.parse_tide_time('2026-09-13 12:00')
        predictions = [
            {'t': '2026-09-13 01:53', 'v': '2.25', 'type': 'H'},
            {'t': '2026-09-13 09:03', 'v': '0.541', 'type': 'L'},
            {'t': '2026-09-13 15:00', 'v': '2.109', 'type': 'H'},
            {'t': '2026-09-13 20:59', 'v': '1.187', 'type': 'L'},
        ]
        events = ck.upcoming_tides(predictions, now)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][1], 'high')
        self.assertEqual(events[1][1], 'low')
        speech = ck.format_tide_speech(events, now)
        self.assertIn('high', speech)
        self.assertIn('2.1 feet', speech)
        self.assertIn('3 PM', speech)
        self.assertIn('low tide', speech)

    def test_get_gulfport_tide_survives_noaa_failure(self):
        with mock.patch('chaps_kitty.urllib.request.urlopen', side_effect=URLError('timeout')):
            result = ck.get_gulfport_tide()
        self.assertIn(
            'could not find the Gulfport tide', result['response']['outputSpeech']['text']
        )

    def test_tide_intent_routes(self):
        event = session_event('IntentRequest', 'Tide')
        with mock.patch('chaps_kitty.get_gulfport_tide', return_value={'ok': True}):
            self.assertEqual(ck.handler(event, None), {'ok': True})


MARINE_PRODUCT = """
GMZ856-141315-
Coastal waters from Bonita Beach to Englewood FL out 20 NM-
842 PM EDT Sun Sep 13 2026

.OVERNIGHT...North winds around 5 knots. Seas 1 foot or less.

$$

GMZ853-141315-
Coastal waters from Englewood to Tarpon Springs FL out 20 NM-
842 PM EDT Sun Sep 13 2026

.OVERNIGHT...Northwest winds around 5 knots, becoming west. Seas
1 foot or less. Bay and inland waters smooth.
.MONDAY...Northwest winds 5 to 10 knots. Seas 1 foot or less.
Bay and inland waters light chop.
.MONDAY NIGHT...North winds 5 to 10 knots, becoming east after
midnight. Seas 1 foot or less.
.TUESDAY...East winds 5 to 10 knots. Seas 1 foot or less.

Winds and seas higher in and near thunderstorms.

$$
"""


class MarineForecastTests(unittest.TestCase):
    def test_extracts_requested_zone_and_first_three_periods(self):
        periods = ck.marine_zone_periods(MARINE_PRODUCT)
        self.assertEqual(len(periods), 4)
        speech = ck.format_marine_forecast(periods)
        self.assertIn('National Weather Service Tampa Bay', speech)
        self.assertIn('Englewood to Tarpon Springs', speech)
        self.assertIn('Overnight: Northwest winds', speech)
        self.assertIn('Monday Night: North winds', speech)
        self.assertNotIn('Tuesday:', speech)
        self.assertNotIn('Bonita Beach', speech)

    def test_missing_zone_raises(self):
        with self.assertRaises(ValueError):
            ck.marine_zone_periods('no marine forecast here')

    def test_get_marine_forecast_survives_nws_failure(self):
        with mock.patch('chaps_kitty.urllib.request.urlopen', side_effect=URLError('timeout')):
            result = ck.get_marine_forecast()
        self.assertIn(
            'could not find the marine forecast', result['response']['outputSpeech']['text']
        )

    def test_marine_forecast_intent_routes(self):
        event = session_event('IntentRequest', 'MarineForecast')
        with mock.patch('chaps_kitty.get_marine_forecast', return_value={'ok': True}):
            self.assertEqual(ck.handler(event, None), {'ok': True})


WP_POSTS = [
    {
        'date': '2026-08-22T18:28:37',
        'date_gmt': '2026-08-22T18:28:37',
        'slug': 'hubbards-marina-fishing-report-8-22-26',
        'title': {'rendered': 'Hubbard&#8217;s Marina Fishing Report 8-22-26'},
        'content': {
            'rendered': (
                '<p>Inshore Fishing Report The snook bite has been really '
                'good around the passes. Folks are having better success '
                'with smaller lures. Wahoo are possible too</p>'
                '<p>Spread the word by visiting: https://returnemright.org/. '
                'TERMS OF REFERENCE- Inshore: This covers the inner bays.</p>'
                '<p>Thank you for reading our report.</p>'
            )
        },
    },
    {
        'date': '2026-08-09T05:25:58',
        'date_gmt': '2026-08-09T05:25:58',
        'slug': 'hubbards-marina-cruise-news-2',
        'title': {'rendered': "Hubbard's Marina Cruise News"},
        'content': {'rendered': '<p>Wildlife update.</p>'},
    },
]


class FishingReportTests(unittest.TestCase):
    def test_skips_cruise_news_and_speaks_age(self):
        now = ck.parse_wp_datetime('2026-09-13T12:00:00').astimezone(ck.GULFPORT_TZ)
        post = ck.latest_fishing_report(WP_POSTS)
        self.assertIn('fishing-report', post['slug'])
        speech = ck.format_fishing_report_speech(post, now)
        self.assertIn('August 22nd', speech)
        self.assertIn('22 days old', speech)
        self.assertIn('snook bite', speech)
        self.assertNotIn('weekly', speech)

    def test_speaks_past_the_wordpress_excerpt_cutoff(self):
        now = ck.parse_wp_datetime('2026-09-13T12:00:00').astimezone(ck.GULFPORT_TZ)
        speech = ck.format_fishing_report_speech(WP_POSTS[0], now)
        self.assertIn('Wahoo are possible too', speech)

    def test_credits_hubbards_marina(self):
        now = ck.parse_wp_datetime('2026-09-13T12:00:00').astimezone(ck.GULFPORT_TZ)
        speech = ck.format_fishing_report_speech(WP_POSTS[0], now)
        self.assertIn("Hubbard's Marina fishing report", speech)
        self.assertIn('Captain Dylan Hubbard', speech)
        self.assertIn('hubbardsmarina.com', speech)

    def test_credit_survives_truncation(self):
        now = ck.parse_wp_datetime('2026-09-13T12:00:00').astimezone(ck.GULFPORT_TZ)
        post = dict(WP_POSTS[0], content={'rendered': '<p>' + 'Snook are biting. ' * 900 + '</p>'})
        speech = ck.format_fishing_report_speech(post, now)
        self.assertLessEqual(len(speech), ck.MAX_SPEECH_CHARS)
        self.assertTrue(speech.endswith(ck.REPORT_CREDIT))

    def test_drops_boilerplate_and_links(self):
        speech = ck.report_body(WP_POSTS[0])
        self.assertNotIn('TERMS OF REFERENCE', speech)
        self.assertNotIn('Thank you for reading', speech)
        self.assertNotIn('returnemright', speech)

    def test_long_report_stays_under_alexa_limit(self):
        now = ck.parse_wp_datetime('2026-09-13T12:00:00').astimezone(ck.GULFPORT_TZ)
        post = dict(WP_POSTS[0], content={'rendered': '<p>' + 'Snook are biting. ' * 900 + '</p>'})
        speech = ck.format_fishing_report_speech(post, now)
        self.assertLessEqual(len(speech), ck.MAX_SPEECH_CHARS)
        self.assertTrue(speech.endswith('.'))

    def test_today_is_not_called_old(self):
        now = ck.parse_wp_datetime('2026-08-22T20:00:00').astimezone(ck.GULFPORT_TZ)
        speech = ck.format_fishing_report_speech(WP_POSTS[0], now)
        self.assertIn('today', speech)

    def test_get_fishing_report_survives_wp_failure(self):
        with mock.patch('chaps_kitty.urllib.request.urlopen', side_effect=URLError('timeout')):
            result = ck.get_fishing_report()
        self.assertIn(
            "could not find the Hubbard's Marina fishing report",
            result['response']['outputSpeech']['text'],
        )

    def test_fishing_report_intent_routes(self):
        event = session_event('IntentRequest', 'FishingReport')
        with mock.patch('chaps_kitty.get_fishing_report', return_value={'ok': True}):
            self.assertEqual(ck.handler(event, None), {'ok': True})


if __name__ == '__main__':
    unittest.main()
