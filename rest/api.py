import inspect

from .backends import BACKENDS
from .endpoint import Endpoint


class API:

    def __init__(self, prefix='', backend=None):
        self.prefix = '/' + prefix.strip('/')
        self.backend = backend or (BACKENDS and BACKENDS[0](self))

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def register(self, endpoint, *paths, methods=None):
        """Register given resource with given params."""
        if not (inspect.isclass(endpoint) and issubclass(endpoint, Endpoint)):
            paths = [endpoint] + list(paths)

            def wrapper(endpoint):
                self.register(endpoint, *paths, methods=methods)

            return wrapper

        methods = methods or endpoint.opts.methods
        if not paths:
            paths = [f"/{endpoint.opts.name}", f"/{endpoint.opts.name}/{{{endpoint.opts.name}}}"]

        return self.backend.register(endpoint, *paths, methods=methods)

    async def authorize(self, request, **params):
        """Default authorization method."""
        pass
