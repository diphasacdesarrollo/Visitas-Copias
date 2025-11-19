# apps/core/middleware.py
import time, logging
from django.db import connection

logger = logging.getLogger(__name__)

class PerfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        start_q = len(getattr(connection, "queries", []))  # solo en DEBUG

        response = self.get_response(request)

        total = (time.perf_counter() - start) * 1000  # ms
        queries = getattr(connection, "queries", [])
        n_queries = max(len(queries) - start_q, 0)
        db_time = 0.0
        if n_queries:
            # connection.queries tiene 'time' como string en segundos
            db_time = sum(float(q.get("time", 0)) for q in queries[-n_queries:]) * 1000

        logger.warning(
            "[PERF] %s %s -> %d ms (DB %d queries / %.1f ms)",
            request.method, request.path, total, n_queries, db_time
        )
        return response
