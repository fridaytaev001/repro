"""Crusoe's OpenAI-compatible HTTP interface, with bounded, redacted errors."""
import asyncio
import random
from typing import Callable

import httpx

BASE_URL = 'https://api.inference.crusoecloud.com/v1'
PREFERRED_MODEL = 'nvidia/Nemotron-3-Super-120B-A12B'


class ProviderError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class CrusoeClient:
    execution_mode = 'live'
    provider_name = 'Crusoe'
    def __init__(self, settings, on_request: Callable | None = None,
                 transport=None, sleep=asyncio.sleep):
        self.settings = settings
        self.on_request = on_request or (lambda *args: None)
        self.sleep = sleep
        self.http = httpx.AsyncClient(base_url=BASE_URL + '/',
            headers={'Authorization': f'Bearer {settings.api_key}'},
            timeout=httpx.Timeout(45, connect=10), transport=transport,
            follow_redirects=False)
        self.model = None

    async def close(self):
        await self.http.aclose()

    async def request(self, method, path, **kwargs):
        if not self.settings.api_key:
            raise ProviderError('missing_key', 'Set CRUSOE_API_KEY in the local .env file, then start this case again.')
        for attempt in range(3):
            self.on_request('request', {'operation': path, 'attempt': attempt + 1})
            try:
                response = await self.http.request(method, path, **kwargs)
            except httpx.HTTPError:
                if attempt < 2:
                    self.on_request('retry', {'reason': 'network_error', 'attempt': attempt + 1})
                    await self.sleep(2 ** attempt + random.uniform(0, .3))
                    continue
                raise ProviderError('network_error', 'Could not reach Crusoe after bounded retries.') from None
            if response.status_code in {429, 502, 503, 504} and attempt < 2:
                self.on_request('retry', {'reason': f'http_{response.status_code}', 'attempt': attempt + 1})
                await self.sleep(2 ** attempt + random.uniform(0, .3))
                continue
            if response.status_code >= 300:
                code = 'authentication_failed' if response.status_code in {401, 403} else f'http_{response.status_code}'
                # Never include raw error bodies or request headers in evidence.
                raise ProviderError(code, f'Crusoe request failed ({code}). Check the local provider configuration.')
            try:
                body = response.json()
            except ValueError:
                raise ProviderError('invalid_response', 'Crusoe returned a non-JSON response.') from None
            request_id = response.headers.get('x-request-id') or response.headers.get('request-id')
            return body, request_id

    async def discover(self):
        body, _ = await self.request('GET', 'models')
        models = body.get('data', []) if isinstance(body, dict) else []
        if not isinstance(models, list):
            raise ProviderError('invalid_catalog', 'Crusoe model catalog is malformed.')
        wanted = self.settings.model or PREFERRED_MODEL
        model = next((m for m in models if isinstance(m, dict) and m.get('id') == wanted), None)
        if not model and not self.settings.model:
            model = next((m for m in models if isinstance(m, dict)
                          and str(m.get('id', '')).lower() == wanted.lower()), None)
        if not model:
            raise ProviderError('model_unavailable', 'The selected model is absent from the live catalog. Set CRUSOE_MODEL to an exact available tool-calling model ID.')
        if 'tools' not in model.get('supported_parameters', []):
            raise ProviderError('tools_unavailable', 'The live catalog does not advertise tool support for the selected model.')
        self.model = model
        return {'id': model['id'], 'supported_parameters': model.get('supported_parameters', []),
                'context_length': model.get('context_length'), 'pricing': model.get('pricing')}

    async def chat(self, messages, tools, tool_choice=None):
        if not self.model:
            await self.discover()
        parameters = self.model.get('supported_parameters', [])
        payload = {'model': self.model['id'], 'messages': messages, 'tools': tools}
        if 'max_tokens' in parameters:
            payload['max_tokens'] = self.settings.max_output_tokens
        elif 'max_completion_tokens' in parameters:
            payload['max_completion_tokens'] = self.settings.max_output_tokens
        else:
            raise ProviderError('output_limit_unavailable', 'The selected model does not advertise a supported output-token limit.')
        if 'parallel_tool_calls' in parameters:
            payload['parallel_tool_calls'] = False
        if tool_choice is not None and 'tool_choice' in parameters:
            payload['tool_choice'] = tool_choice
        body, request_id = await self.request('POST', 'chat/completions', json=payload)
        try:
            choice = body['choices'][0]
            raw_message = choice['message']
            message = {'role': 'assistant', 'content': raw_message.get('content')}
            calls = raw_message.get('tool_calls') or []
            if calls:
                message['tool_calls'] = calls
            if not message['content'] and not calls:
                raise ProviderError('empty_completion', 'Crusoe returned no content or tool calls; the output budget may be exhausted.')
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError('invalid_completion', 'Crusoe returned an invalid chat-completion response.') from None
        usage = body.get('usage') if isinstance(body.get('usage'), dict) else None
        return {'message': message, 'usage': usage, 'request_id': request_id,
                'response_id': body.get('id'), 'model': self.model['id'],
                'finish_reason': choice.get('finish_reason')}

    async def smoke_test(self):
        catalog = await self.discover()
        tool = {'type': 'function', 'function': {'name': 'ready',
            'description': 'Confirm tool calling is ready.',
            'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}
        first_user = {'role': 'user', 'content': 'Call ready now with empty arguments. After the tool result, reply with a short readiness message.'}
        first = await self.chat([first_user], [tool], tool_choice={'type': 'function', 'function': {'name': 'ready'}})
        calls = first['message'].get('tool_calls', [])
        if len(calls) != 1 or calls[0].get('function', {}).get('name') != 'ready':
            raise ProviderError('smoke_tool_failed', 'The selected model did not produce the expected readiness tool call.')
        messages = [first_user,
                    first['message'], {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': '{"ready":true}'}]
        second = await self.chat(messages, [tool])
        if second['message'].get('tool_calls') or not second['message'].get('content'):
            raise ProviderError('smoke_round_trip_failed', 'The model did not finish the readiness tool round trip.')
        return {'catalog': catalog, 'tool_round_trip': True,
                'calls': [{k: result[k] for k in ('model', 'request_id', 'response_id', 'usage', 'finish_reason')}
                          for result in (first, second)]}
