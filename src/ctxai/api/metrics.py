"""Prometheus metrics endpoint — GET /api/metrics.

Returns Prometheus text-formatted metrics.  Restricted to loopback
addresses by default so that only internal monitoring can scrape it.
"""

from __future__ import annotations

from typing import Any

from ctxai.helpers.api import ApiHandler
from ctxai.helpers.flask_compat import Response
from ctxai.helpers.prometheus_metrics import metrics


class Metrics(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_loopback(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Any) -> Response:
        return Response(
            response=metrics.generate_latest(),
            status=200,
            mimetype="text/plain; version=0.0.4; charset=utf-8",
        )
