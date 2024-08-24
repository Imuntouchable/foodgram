from rest_framework.pagination import (LimitOffsetPagination,
                                       PageNumberPagination)


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'limit'


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100
