import logging
import contextvars
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable

from shared.base_service import _MAX_WORKERS_CEILING
logger = logging.getLogger(__name__)

_PARALLEL_MAX_WORKERS = min(4, _MAX_WORKERS_CEILING)


def run_queries_parallel(
    sub_queries: list[str],
    request_id: str,
    run_single_fn: Callable[[str, str], str],
    synthesize_fn: Callable[[list[str], str], str],
    original_query: str,
) -> str:
    if not sub_queries or len(sub_queries) <= 1:
        return run_single_fn(sub_queries[0], request_id) if sub_queries else ""

    logger.info(
        "Split into sub-queries",
        extra={
            "request_id": request_id,
            "count": len(sub_queries),
            "queries": sub_queries,
        },
    )

    # Capture the current context so ContextVars propagate to worker threads
    ctx = contextvars.copy_context()

    def _run_with_context(sq: str, rid: str) -> str:
        return ctx.run(run_single_fn, sq, rid)

    answers: list[str] = [""] * len(sub_queries)
    max_workers = min(_PARALLEL_MAX_WORKERS, _MAX_WORKERS_CEILING, len(sub_queries))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_to_idx = {
            pool.submit(_run_with_context, sq, request_id): i
            for i, sq in enumerate(sub_queries)
        }
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            sq = sub_queries[i]
            try:
                ans = fut.result()
                answers[i] = f"**Kết quả [{i + 1}] — {sq}**\n{ans}"
            except Exception as e:
                logger.exception("Sub-query %d failed", i + 1, extra={"request_id": request_id})
                answers[i] = (
                    f"**Kết quả [{i + 1}] — {sq}**\nKhông thể lấy dữ liệu: {e}"
                )

    return synthesize_fn(answers, original_query)
