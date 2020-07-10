from starlette.testclient import TestClient


def test_base():
    from rest import API, Endpoint

    api = API('/api/v1')
    client = TestClient(api.router)

    @api.register
    class Hello(Endpoint):

        def get(self, request, **params):
            return "Hello Tests!"

    res = client.post('/hello')
    assert res.status_code == 405

    res = client.get('/hello')
    assert res.status_code == 200
    assert res.json() == 'Hello Tests!'

    collection = list(range(99))

    @api.register
    class Range(Endpoint):

        class Meta:
            methods = 'get', 'post', 'delete'
            filters = 'num',
            per_page = 3

        def get_many(self, request, **kwargs):
            return collection

        async def get_one(self, request, **kwargs):
            resource = await super().get_one(request, **kwargs)
            if resource:
                return self.collection[int(resource)]

        async def post(self, request, **kwargs):
            return await self.load(request, **kwargs)

    res = client.get('/range?some=22')
    assert res.status_code == 200
    assert res.headers['x-total-count'] == '99'
    assert res.headers['x-limit'] == '3'
    assert res.json() == [0, 1, 2]

    res = client.get('/range?page=1')
    assert res.json() == [3, 4, 5]

    res = client.get('/range?where={"num":1}')
    assert res.status_code == 200
    assert res.json() == [1]

    res = client.get('/range?where={"num":{"$gt":3}}')
    assert res.status_code == 200
    assert res.json() == [4, 5, 6]

    res = client.get('/range/2')
    assert res.status_code == 200
    assert res.json() == 2

    res = client.get('/range/?sort=2')
    assert res.status_code == 200
    assert res.json()

    res = client.put('/range')
    assert res.status_code == 405

    res = client.post('/range', data='{"test": "passed"}')
    assert res.status_code == 200

    res = client.delete('/range')
    assert res.status_code == 404
    assert res.json() == {
        'description': 'Nothing matches the given URI',
        'reason': 'Resource Not Found'}
