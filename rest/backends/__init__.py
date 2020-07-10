import abc


class ABCBackend(abc.ABC):

    @abc.abstractmethod
    def bind(self, app):
        pass

    @abc.abstractmethod
    def register(self, resource_cls, *paths, methods=None):
        pass

    @abc.abstractmethod
    def to_response(self, response, status=200):
        pass

    @abc.abstractmethod
    def get_params(self, request):
        pass

    @abc.abstractmethod
    async def get_data(self, request):
        pass


BACKENDS = []

try:
    from .starlette import BackendStarlette

    BACKENDS.append(BackendStarlette)
except ImportError:
    pass
