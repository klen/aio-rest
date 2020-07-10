from starlette.routing import Mount, Router
from starlette.responses import Response, JSONResponse

from . import ABCBackend


class BackendStarlette(ABCBackend):

    def __init__(self, api):
        self.api = api
        self.router = Router()

    def bind(self, app):
        """Bind the current API to given Starlette app."""
        app.router.routes.append(Mount(self.api.prefix, self.router))

    def register(self, endpoint, *paths, methods=None):
        """Register the given Endpoint in routing."""

        for path in paths:
            self.router.add_route(
                path, endpoint.as_view(self.api), methods=methods)

        return endpoint

    def to_response(self, response, status_code=200, **options):
        """Prepare a response."""
        if isinstance(response, Response):
            return response

        return JSONResponse(response, status_code=status_code, **options)

    def get_params(self, request):
        """Get Path params from the given request."""
        return dict(request.path_params)

    def get_query(self, request):
        """Get Query params from the given request."""
        return dict(request.query_params)

    async def get_data(self, request):
        """Get data from the given request."""
        content_type = request.headers.get('content-type')
        if content_type in {'application/x-www-form-urlencoded', 'multipart/form-data'}:
            return await request.form()

        if content_type == 'application/json':
            return await request.json()

        data = await request.body()
        return data.decode('utf-8')
