import json

import httpx
import pytest

from app.providers.crusoe import CrusoeClient, ProviderError, PREFERRED_MODEL
from app.settings import Settings

pytestmark = pytest.mark.asyncio


def catalog(parameters=None):
    return {'data': [{'id': PREFERRED_MODEL, 'supported_parameters': parameters if parameters is not None else ['tools', 'tool_choice', 'max_tokens', 'parallel_tool_calls']}]}


async def no_sleep(_):
    pass


async def test_real_protocol_preserves_tool_call_and_result_order():
    requests = []

    def handler(request):
        assert request.url.host == 'api.inference.crusoecloud.com'
        assert request.headers['authorization'] == 'Bearer synthetic-test-key'
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json=catalog())
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'call-ready', 'type': 'function', 'function': {'name': 'ready', 'arguments': '{}'}}]}
        else:
            assert body['messages'][-2]['tool_calls'][0]['id'] == 'call-ready'
            assert body['messages'][-1] == {'role': 'tool', 'tool_call_id': 'call-ready', 'content': '{"ready":true}'}
            assert body['messages'][0] == requests[0]['messages'][0]
            message = {'role': 'assistant', 'content': 'Ready.'}
        assert body['max_tokens'] == 4096
        assert body['parallel_tool_calls'] is False
        return httpx.Response(200, headers={'x-request-id': 'req-test'}, json={
            'id': f'completion-{len(requests)}', 'choices': [{'message': message, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}})

    provider = CrusoeClient(Settings(api_key='synthetic-test-key'), transport=httpx.MockTransport(handler))
    try:
        result = await provider.smoke_test()
        assert result['tool_round_trip'] is True
        assert len(result['calls']) == 2
        assert result['calls'][0]['request_id'] == 'req-test'
        assert result['calls'][0]['usage']['total_tokens'] == 110
    finally:
        await provider.close()


async def test_retries_are_bounded_and_errors_do_not_echo_credentials():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(503, text='danger synthetic-test-key')

    provider = CrusoeClient(Settings(api_key='synthetic-test-key'), transport=httpx.MockTransport(handler), sleep=no_sleep)
    try:
        with pytest.raises(ProviderError) as error:
            await provider.discover()
        assert len(attempts) == 3
        assert 'synthetic-test-key' not in str(error.value)
        assert error.value.code == 'http_503'
    finally:
        await provider.close()


async def test_auth_failure_is_not_retried_or_exposed():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(401, json={'error': 'synthetic-secret-key'})

    provider = CrusoeClient(Settings(api_key='synthetic-secret-key'), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderError, match='authentication_failed') as error:
            await provider.discover()
        assert len(attempts) == 1
        assert 'synthetic-secret-key' not in str(error.value)
    finally:
        await provider.close()


@pytest.mark.parametrize('body,code', [(catalog([]), 'tools_unavailable'), ({'data': []}, 'model_unavailable')])
async def test_catalog_rejects_unavailable_model_or_missing_tool_support(body, code):
    provider = CrusoeClient(Settings(api_key='synthetic'), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))
    try:
        with pytest.raises(ProviderError) as error:
            await provider.discover()
        assert error.value.code == code
    finally:
        await provider.close()


async def test_missing_key_never_sends_network_request():
    def handler(_):
        pytest.fail('No request should be sent without a key.')
    provider = CrusoeClient(Settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderError) as error:
            await provider.discover()
        assert error.value.code == 'missing_key'
    finally:
        await provider.close()


async def test_empty_completion_is_not_success():
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json=catalog())
        return httpx.Response(200, json={'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}]})
    provider = CrusoeClient(Settings(api_key='synthetic'), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderError) as error:
            await provider.chat([{'role': 'user', 'content': 'test'}], [])
        assert error.value.code == 'empty_completion'
    finally:
        await provider.close()
