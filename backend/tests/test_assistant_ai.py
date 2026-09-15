import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import test_assistant as fixtures
from app.core.config import settings
from app.schemas.assistant import ChatRequest, Filters, PreferenceIntent
from app.services import assistant_ai
from app.services.assistant_chat import answer_chat
from app.services.recommendation_enrichment import enrich_metadata
from app.models.movie import Movie


def intent(**changes):
    return PreferenceIntent(action='recommend', filters=Filters(genres=['Science Fiction']), reference_titles=[], reason='none').model_copy(update=changes)


def provider_response(value=None):
    return {'status': 'completed', 'output': [{'type':'message', 'content':[{'type':'output_text', 'text':(value or intent()).model_dump_json()}]}]}


class AssistantAITests(unittest.TestCase):
    setUp = fixtures.AssistantTests.setUp
    tearDown = fixtures.AssistantTests.tearDown

    def test_strict_schema_has_required_fields_and_no_defaults(self):
        schema = assistant_ai.strict_schema()
        self.assertEqual(set(schema['required']), set(schema['properties']))
        self.assertEqual(set(schema['$defs']['Filters']['required']), set(schema['$defs']['Filters']['properties']))
        self.assertNotIn('"default":', json.dumps(schema))

    def test_missing_key_does_not_call_network(self):
        with patch.object(settings, 'ENABLE_ASSISTANT_AI', False), patch.object(assistant_ai, 'urlopen') as network:
            result = answer_chat(self.db, ChatRequest(message='something lighthearted', use_ai=True))
        network.assert_not_called()
        self.assertEqual(result['mode'], 'ai-unavailable')
        self.assertTrue(result['needs_clarification'])

    def test_transport_is_bounded_and_does_not_send_profile(self):
        assistant_ai._calls.clear()
        with patch.object(settings, 'ENABLE_ASSISTANT_AI', True), patch.object(settings, 'OPENAI_API_KEY', 'test-only-key'), patch.object(assistant_ai, 'urlopen', return_value=io.BytesIO(json.dumps(provider_response()).encode())) as network:
            parsed = assistant_ai.extract_preferences(ChatRequest(message='something futuristic', favorite_ids=[1], use_ai=True))
        request = network.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body['store'], False)
        self.assertEqual(body['max_output_tokens'], 700)
        self.assertEqual(network.call_args.kwargs['timeout'], 12)
        self.assertEqual(set(json.loads(body['input'])), {'message','current_filters'})
        self.assertEqual(parsed.filters.genres, ['Science Fiction'])

    def test_refused_malformed_and_incomplete_responses_preserve_filters(self):
        cases = [{'status':'incomplete'}, {'status':'completed', 'output':[{'type':'message','content':[{'type':'refusal','refusal':'no'}]}]}, {'status':'completed','output':None}, {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"unexpected":true}'}]}]}]
        for case in cases:
            assistant_ai._calls.clear()
            with patch.object(settings, 'ENABLE_ASSISTANT_AI', True), patch.object(settings, 'OPENAI_API_KEY', 'test-only-key'), patch.object(assistant_ai, 'urlopen', return_value=io.BytesIO(json.dumps(case).encode())):
                result = answer_chat(self.db, ChatRequest(message='something futuristic', filters=Filters(max_runtime=100), use_ai=True))
            self.assertEqual(result['items'], [])
            self.assertEqual(result['filters'].max_runtime, 100)
            self.assertTrue(result['needs_clarification'])

    def test_provider_error_is_redacted_and_not_retried(self):
        assistant_ai._calls.clear()
        with patch.object(settings, 'ENABLE_ASSISTANT_AI', True), patch.object(settings, 'OPENAI_API_KEY', 'test-only-key'), patch.object(assistant_ai, 'urlopen', side_effect=HTTPError('https://example.invalid/test-only-key', 429, 'test-only-key', {}, None)) as network:
            result = answer_chat(self.db, ChatRequest(message='recommend', use_ai=True))
        self.assertNotIn('test-only-key', json.dumps(result, default=str))
        self.assertEqual(network.call_count, 1)
        self.assertEqual(result['mode'], 'ai-unavailable')

    def test_quota_stops_additional_calls(self):
        assistant_ai._calls.clear()
        with patch.object(settings, 'ENABLE_ASSISTANT_AI', True), patch.object(settings, 'OPENAI_API_KEY', 'test-only-key'), patch.object(settings, 'ASSISTANT_AI_CALLS_PER_HOUR', 1), patch.object(assistant_ai, 'urlopen', return_value=io.BytesIO(json.dumps(provider_response()).encode())) as network:
            assistant_ai.extract_preferences(ChatRequest(message='recommend'))
            with self.assertRaises(assistant_ai.AssistantAIUnavailable):
                assistant_ai.extract_preferences(ChatRequest(message='recommend'))
        self.assertEqual(network.call_count, 1)
        assistant_ai._calls.clear()

    def test_ai_intent_still_obeys_real_catalog_and_constraints(self):
        value = intent(filters=Filters(genres=['Science Fiction'], excluded_genres=['Horror'], max_runtime=119), reference_titles=['Space Seed'])
        with patch('app.services.assistant_chat.extract_preferences', return_value=value):
            result = answer_chat(self.db, ChatRequest(message='like Space Seed, futuristic and short', use_ai=True))
        self.assertEqual([item['movie']['id'] for item in result['items']], [2])
        self.assertEqual(result['mode'], 'ai-preferences-v1')

    def test_invented_reference_is_not_recommended(self):
        with patch('app.services.assistant_chat.extract_preferences', return_value=intent(reference_titles=['An invented movie'])):
            result = answer_chat(self.db, ChatRequest(message='something similar', use_ai=True))
        self.assertTrue(result['needs_clarification'])
        self.assertEqual(result['items'], [])

    def test_real_but_unmentioned_reference_does_not_invent_user_taste(self):
        with patch('app.services.assistant_chat.extract_preferences', return_value=intent(reference_titles=['Space Seed'])):
            result = answer_chat(self.db, ChatRequest(message='a movie for tonight', use_ai=True))
        self.assertTrue(result['needs_clarification'])
        self.assertEqual(result['items'], [])

    def test_natural_more_uses_seen_ids(self):
        with patch('app.services.assistant_chat.extract_preferences', return_value=intent(action='more')):
            result = answer_chat(self.db, ChatRequest(message='give me a different batch', seen_ids=[1,2,4,5,6,7], use_ai=True))
        self.assertEqual(result['items'], [])
        self.assertEqual(result['action'], 'more')

    def test_ai_requires_authenticated_csrf_request(self):
        self.assertEqual(self.client.post('/api/assistant/chat', json={'message':'recommend','use_ai':True}).status_code, 401)
        registration = self.client.post('/api/auth/register', json={'username':'ai_reader','password':'long-test-password-123'})
        self.assertEqual(self.client.post('/api/assistant/chat', json={'message':'recommend','use_ai':True}).status_code, 403)
        with patch('app.services.assistant_chat.extract_preferences', return_value=intent()):
            response = self.client.post('/api/assistant/chat', json={'message':'recommend','use_ai':True}, headers={'X-CSRF-Token':registration.json()['csrf_token']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'ai-preferences-v1')

    def test_enrichment_plan_never_calls_provider(self):
        with patch('app.services.recommendation_enrichment._tmdb_get') as network:
            report = enrich_metadata(self.db, limit=1)
        network.assert_not_called()
        self.assertEqual(report['selected_ids'], [5])
        self.assertEqual(report['updated'], 0)

    def test_enrichment_preserves_existing_fields_and_catalog(self):
        movie = self.db.get(Movie,5)
        movie.provider_metadata = {'imdb_rating':'8.5', 'custom':{'keep':True}}
        self.db.commit()
        before = (movie.title, movie.tmdb_id, movie.genres)
        with patch.object(settings, 'TMDB_API_KEY','test-key'), patch('app.services.recommendation_enrichment._tmdb_get', return_value={'id':5,'runtime':95,'original_language':'en'}):
            report = enrich_metadata(self.db, limit=1, apply=True)
        self.assertEqual(report['updated'], 1)
        self.assertEqual(movie.provider_metadata['runtime'], '95 min')
        self.assertEqual(movie.provider_metadata['custom'], {'keep':True})
        self.assertEqual(movie.provider_metadata['imdb_rating'], '8.5')
        self.assertEqual(before, (movie.title, movie.tmdb_id, movie.genres))
        self.assertIn('verified_at', movie.provider_metadata['recommendation_enrichment'])

    def test_enrichment_rejects_wrong_identity_and_missing_key(self):
        with patch.object(settings, 'TMDB_API_KEY',''):
            with self.assertRaises(ValueError): enrich_metadata(self.db, apply=True)
        with patch.object(settings, 'TMDB_API_KEY','test-key'), patch('app.services.recommendation_enrichment._tmdb_get', return_value={'id':999,'runtime':95,'original_language':'en'}):
            result=enrich_metadata(self.db, limit=1, apply=True)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(self.db.get(Movie,5).provider_metadata['runtime'], None)
