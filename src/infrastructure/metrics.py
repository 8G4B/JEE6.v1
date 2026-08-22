import logging
import time

from prometheus_client import Counter, Histogram, start_http_server


logger = logging.getLogger(__name__)

COMMAND_COUNT = Counter(
    "jee6_bot_commands_total",
    "Total number of completed Discord commands.",
    ("command", "status"),
)
COMMAND_DURATION = Histogram(
    "jee6_bot_command_duration_seconds",
    "Discord command duration in seconds.",
    ("command",),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)


def start_metrics_server(host: str, port: int) -> None:
    if port <= 0:
        logger.info("Prometheus metrics server disabled")
        return
    start_http_server(port, addr=host)
    logger.info("Prometheus metrics server listening on %s:%d", host, port)


def start_command_timer(ctx) -> None:
    ctx.jee6_command_started_at = time.perf_counter()


def observe_command(ctx) -> None:
    started_at = getattr(ctx, "jee6_command_started_at", None)
    if started_at is None:
        return
    duration = time.perf_counter() - started_at
    command = ctx.command.qualified_name if ctx.command else "unknown"
    status = "error" if ctx.command_failed else "ok"
    COMMAND_COUNT.labels(command, status).inc()
    COMMAND_DURATION.labels(command).observe(duration)
    logger.info(
        "command_latency command=%s status=%s duration_ms=%.2f",
        command,
        status,
        duration * 1000,
    )
