from rest_framework import status
from rest_framework.response import Response

from .versioning import add_api_version_header


def api_response(data=None, msg: str = "", code: int = 0, status_code: int = status.HTTP_200_OK, headers=None):
    """
    Standard API v1 response envelope.

    Args:
        data: payload data
        msg: message string
        code: business code (0 success, non-zero error)
        status_code: HTTP status
        headers: optional headers dict
    """
    body = {
        "code": code,
        "data": data,
        "msg": msg,
    }
    response = Response(body, status=status_code, headers=headers)
    return add_api_version_header(response)
