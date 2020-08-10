import pytest
import marshmallow as ma
from starlette.testclient import TestClient


@pytest.fixture
def api():
    from rest import API

    return API('/api/v1')


@pytest.fixture
def client(api):
    return TestClient(api.router)


def test_simple_views(api, client):

    @api.register('/sync', methods=('get', 'post'))
    def sync_func(request, **params):
        return 'SYNC OK'

    @api.register('/async')
    async def async_func(request, **params):
        return 'ASYNC OK'

    res = client.get('/sync')
    assert res.status_code == 200
    assert res.json() == 'SYNC OK'

    res = client.post('/sync')
    assert res.status_code == 200
    assert res.json() == 'SYNC OK'

    res = client.delete('/sync')
    assert res.status_code == 405

    res = client.get('/async')
    assert res.status_code == 200
    assert res.json() == 'ASYNC OK'


def test_resources(api, client):
    from rest import Endpoint, APIUnauthorized

    @api.register
    class Hello(Endpoint):

        def get(self, request, **params):
            return "Hello Tests!"

    res = client.post('/hello')
    assert res.status_code == 405

    res = client.get('/hello')
    assert res.status_code == 200
    assert res.json() == 'Hello Tests!'

    collection = [{'id': n} for n in range(99)]

    @api.register
    class Range(Endpoint):

        class Meta:
            methods = 'get', 'post', 'delete'
            filters = 'id',
            per_page = 3

            class Schema(ma.Schema):
                id = ma.fields.Integer()

        async def authorize(self, request, **kwargs):
            anon = request.query_params.get('anonymous')
            if anon:
                raise APIUnauthorized()

        async def get_many(self, request, **kwargs):
            return collection

        async def get_one(self, request, **kwargs):
            resource = await super().get_one(request, **kwargs)
            if resource:
                return self.collection[int(resource)]

        async def post(self, request, **kwargs):
            return await self.load(request, **kwargs)

    res = client.get('/range?anonymous=1')
    assert res.status_code == 401

    res = client.get('/range?some=22')
    assert res.status_code == 200
    assert res.headers['x-total-count'] == '99'
    assert res.headers['x-limit'] == '3'
    assert res.json() == [{'id': 0}, {'id': 1}, {'id': 2}]

    res = client.get('/range?page=1')
    assert res.json() == [{'id': 3}, {'id': 4}, {'id': 5}]

    res = client.get('/range?where={"id":1}')
    assert res.status_code == 200
    assert res.json() == [{'id': 1}]

    res = client.get('/range?where={"id":{"$gt":3}}')
    assert res.status_code == 200
    assert res.json() == [{'id': 4}, {'id': 5}, {'id': 6}]

    res = client.get('/range/2')
    assert res.status_code == 200
    assert res.json() == {'id': 2}

    res = client.get('/range/?sort=2')
    assert res.status_code == 200
    assert res.json()

    res = client.put('/range')
    assert res.status_code == 405

    res = client.post('/range', json={"test": "passed"})
    assert res.status_code == 400
    json = res.json()
    assert json
    assert json['errors']

    res = client.post('/range', json={"id": 7})
    assert res.status_code == 200

    res = client.delete('/range')
    assert res.status_code == 404
    assert res.json() == {
        'description': 'Nothing matches the given URI',
        'reason': 'Resource Not Found'}
