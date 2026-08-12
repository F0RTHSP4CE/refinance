from datetime import date


def fetch_stats_bundle(
    api,
    subject_type: str,
    subject_id: int,
    *,
    months: int,
    limit: int | None = None,
    cached_only: bool = False,
) -> dict:
    """Fetch a stats bundle with shared timeframe and cache parameters."""
    params = {
        "months": max(1, months),
        "timeframe_to": date.today().isoformat(),
    }
    if limit is not None:
        params["limit"] = max(1, limit)
    if cached_only:
        params["cached_only"] = 1
    return api.http("GET", f"stats/{subject_type}/{subject_id}", params=params).json()
