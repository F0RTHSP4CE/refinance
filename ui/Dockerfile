FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

ENV UV_CACHE_DIR=/root/.cache/uv \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

RUN uv venv /venv

COPY pyproject.toml uv.lock /opt/ui/
COPY ./ui /opt/ui/

WORKDIR /opt/ui

RUN --mount=type=cache,target=/root/.cache/uv \
    uv export > requirements.txt && \
    uv pip install -r requirements.txt


FROM python:3.12-alpine

ENV PATH="/venv/bin:$PATH"

COPY --from=builder /venv /venv
COPY ./ui /opt/ui

WORKDIR /opt/ui

EXPOSE 9000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9000", "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "app.app:app"]
