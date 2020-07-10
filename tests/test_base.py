import pytest


async def test_base():
    from rest.backends import BACKENDS
    assert BACKENDS


def test_api():
    from rest import API

    api = API('/v1')
    assert api
    assert api.prefix == '/v1'
    assert api.backend
    assert api.router
    assert api.register


def test_exceptions():
    from rest import APIException

    with pytest.raises(APIException):
        raise APIException(reason='test')


def test_resource():
    from rest import Endpoint

    class Test(Endpoint):

        class Meta:
            methods = 'get', 'put'

    assert Test.opts
    assert Test.opts.methods == ['GET', 'PUT']
