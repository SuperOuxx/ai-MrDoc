from rest_framework.pagination import PageNumberPagination

from app_api_v1.utils.responses import api_response


class ApiPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        payload = {
            "results": data,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
        }
        return api_response(data=payload, msg="ok")
