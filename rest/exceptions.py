from http import HTTPStatus


class APIException(Exception):

    def __init__(self, *msgs, status_code=None, **json):
        super(APIException, self).__init__(*msgs)
        json.setdefault('description', self.status.description)
        self.status_code = status_code or self.status.value
        self.json = json

    status = HTTPStatus.BAD_REQUEST


APIBadRequest = APIException


class APIUnauthorized(APIException):

    status = HTTPStatus.UNAUTHORIZED


class APIPaymentRequired(APIException):

    status = HTTPStatus.PAYMENT_REQUIRED


class APIForbidden(APIException):

    status = HTTPStatus.FORBIDDEN


class APINotFound(APIException):

    status = HTTPStatus.NOT_FOUND


class APIMethodNotAllowed(APIException):

    status = HTTPStatus.METHOD_NOT_ALLOWED


class APINotAcceptable(APIException):

    status = HTTPStatus.NOT_ACCEPTABLE


class APIProxyAuthenticationRequired(APIException):

    status = HTTPStatus.PROXY_AUTHENTICATION_REQUIRED


class APIRequestTimeout(APIException):

    status = HTTPStatus.REQUEST_TIMEOUT


class APIConflict(APIException):

    status = HTTPStatus.CONFLICT


class APIGone(APIException):

    status = HTTPStatus.GONE
