from abc import ABCMeta
import json
import inspect
import math
import marshmallow as ma

from .exceptions import APINotFound, APIBadRequest, APIException
from .filters import Filters
from .utils import to_coroutine


HEADERS = {'HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
PAGE_QUERY = 'page'
PER_PAGE_QUERY = 'per_page'
SORT_QUERY = 'sort'
FILTERS_QUERY = 'where'


class EndpointOptions:

    def __init__(self, cls):
        """Prepare meta options."""

        for base in reversed(cls.mro()):
            if not hasattr(base, "Meta"):
                continue

            for k, v in base.Meta.__dict__.items():
                if k.startswith('__'):
                    continue
                setattr(self, k, v)

        # Generate name
        self.name = self.name or cls.__name__.lower().split('endpoint', 1)[0] or\
            cls.__name__.lower()

        self.per_page = int(self.per_page or 0)

        # Setup Schema
        self.schema_meta = self.schema_meta or {
            k[7:]: self.__dict__[k] for k in self.__dict__
            if k.startswith('schema_') and not k == 'schema_meta'
        }

        # Setup filters
        self.filters = self.filters_converter(*self.filters, endpoint=cls)

        # Setup sorting
        if not isinstance(self.sorting, dict):
            self.sorting = dict(
                n if isinstance(n, (list, tuple)) else (n, n) for n in self.sorting)

        # Setup methods
        if not isinstance(self.methods, (list, tuple, set)):
            self.methods = [self.methods]
        self.methods = [m.upper() for m in self.methods if m.upper() in HEADERS]

    def __repr__(self):
        """String representation."""
        return "<Options %s>" % self.name


class EndpointMeta(ABCMeta):

    coroutines = {
        'authorize', 'dispatch', 'get_many', 'get_one', 'get_schema', 'paginate', 'filter',
        'dump', 'load', 'sort', 'save', 'get', 'post', 'put', 'patch', 'delete'
    }

    def __new__(mcs, name, bases, params):
        """Initialize options"""
        params = {
            k: (k in mcs.coroutines) and to_coroutine(v) or v
            for k, v in params.items()
        }
        cls = super(EndpointMeta, mcs).__new__(mcs, name, bases, params)
        cls.opts = cls.OPTIONS_CLASS(cls)
        return cls


class Endpoint(metaclass=EndpointMeta):
    """Implement REST resource."""

    OPTIONS_CLASS = EndpointOptions

    # Default options
    class Meta:

        # Endpoint name
        name = None

        # Allowed methods
        methods = 'get'

        # Tune Schema
        Schema = None
        schema_meta = None

        # per_page: Paginate results (set to None for disable pagination)
        per_page = None

        # Resource filters
        filters = ()

        # Filters converter class
        filters_converter = Filters

        # Define allowed resource sorting params
        sorting = ()

    def __init__(self, api):
        self.api = api
        self.resource = self.collection = self.headers = self.filters = None

    @classmethod
    def as_view(cls, api):
        """Prepare a view to work with the class."""

        async def view(request):
            endpoint = cls(api)
            response = await endpoint.dispatch(request)
            while inspect.isawaitable(response):
                response = await response

            return api.to_response(response, headers=endpoint.headers)

        return view

    async def authorize(self, request, **params):
        """Authorize the request."""

        # Support api.authorize method
        return await self.api.authorize(request, **params)

    async def dispatch(self, request):
        """Dispatch current request by methods."""

        method = getattr(self, request.method.lower())
        params = self.api.get_params(request)

        try:
            await self.authorize(request, **params)
            self.collection = await self.get_many(request, **params)

            if request.method == 'POST':
                return await method(request, **params)

            resource = await self.get_one(request, **params)
            if request.method == 'GET' and not resource:
                query = self.api.get_query(request)

                # TODO: Sorting

                # Filter resources
                if FILTERS_QUERY in query:
                    try:
                        data = json.loads(query.get(FILTERS_QUERY))
                        assert data
                        self.collection = await self.filter(request, data, **params)
                    except (ValueError, TypeError, AssertionError):
                        pass

                # Paginate resources
                per_page = query.get(PER_PAGE_QUERY) or self.opts.per_page
                if per_page:
                    try:
                        per_page = int(per_page)
                        page = int(query.get(PAGE_QUERY, 0))
                        if per_page and page >= 0:
                            self.collection, total = await self.paginate(
                                request, page=page, per_page=per_page)
                            self.headers = make_pagination_headers(per_page, page, total)

                    except ValueError:
                        raise APIBadRequest(reason='Pagination params are invalid')

            return await method(request, resource=resource, **params)

        except APIException as exc:
            return self.api.to_response(exc.json, status_code=exc.status_code)

    async def get_many(self, request, **params):
        """Prepare a collection of resources."""
        return []

    async def get_one(self, request, **params):
        """Prepare a resource."""
        return params.get(self.opts.name)

    async def get_schema(self, request, **params):
        """Initialize marshmallow schema for serialization/deserialization."""
        return self.opts.Schema and self.opts.Schema()

    async def filter(self, request, data, **params):
        """Filter collection of resources."""
        self.filters, collection = self.opts.filters.filter(
            data, self.collection, endpoint=self, **params)

        return collection

    async def sort(self, request, **params):
        """Sort the current collection. Just placeholder for the heirs."""
        return self.collection

    async def paginate(self, request, *, page=0, per_page=0, **params):
        """Paginate collection.

        :param request: client's request
        :param page: current page
        :param per_page: limit items per page
        :returns: (paginated collection, count of resources)
        """
        offset = page * per_page
        return self.collection[offset: offset + per_page], len(self.collection)

    async def dump(self, request, data, *, many=..., **params):
        """Serialize the given response."""
        schema = await self.get_schema(request, **params)
        if many is ...:
            many = isinstance(data, (list, tuple, set))

        return schema.dump(data, many=many) if schema else data

    async def load(self, request, *, resource=None, **params):
        """Load data from request and create/update a resource."""
        try:
            data = await self.api.get_data(request)
        except (ValueError, TypeError) as exc:
            raise APIBadRequest(reason=str(exc))

        schema = await self.get_schema(request, resource=resource, **params)
        if not schema:
            return data

        try:
            resource = schema.load(
                data, partial=resource is not None, many=isinstance(data, list))
        except ma.ValidationError as exc:
            raise APIBadRequest(reason='Invalid data', errors=exc.messages)

        return resource

    async def save(self, request, *, resource=None, **params):
        """Save the given resource. Just placeholder for the heirs."""
        return resource

    async def get(self, request, *, resource=None, **params):
        """Get resource or collection of resources"""
        if resource is not None and resource != '':
            return self.dump(request, resource, **params)

        return self.dump(request, self.collection, many=True, **params)

    async def post(self, request, *, resource=None, **params):
        """Create a resource."""
        resource = await self.load(request, resource=resource, **params)
        resource = await self.save(request, resource=resource, **params)
        return self.dump(request, resource, many=isinstance(resource, list), **params)

    async def put(self, request, *, resource=None, **params):
        """Update a resource."""
        if self.resource is None:
            raise APINotFound(reason='Resource Not Found')

        return await self.post(request, resource=resource, **params)

    patch = put

    async def delete(self, request, *, resource=None, **kwargs):
        """Delete a resource."""
        if resource is None:
            raise APINotFound(reason='Resource Not Found')

        self.collection.remove(resource)


def make_pagination_headers(limit, curpage, total):
    """Return Link Hypermedia Header."""
    lastpage = math.ceil(total / limit) - 1
    return {
        'X-Total-Count': str(total), 'X-Limit': str(limit),
        'X-Page-Last': str(lastpage), 'X-Page': str(curpage)
    }
