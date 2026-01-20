from django.conf import settings


def add_api_version_header(response, version: str = None):
    """
    Attach API version header to the response.

    Args:
        response: DRF Response
        version: optional override version string
    """
    response["API-Version"] = version or getattr(settings, "API_V1_VERSION", "1.0")
    return response
