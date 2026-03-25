FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

ENV UV_CACHE_DIR=/root/.cache/uv \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

RUN uv venv /venv

COPY pyproject.toml uv.lock /opt/api/
COPY ./api /opt/api/

WORKDIR /opt/api

RUN --mount=type=cache,target=/root/.cache/uv \
    uv export > requirements.txt && \
    uv pip install -r requirements.txt


FROM python:3.12-alpine

ENV PATH="/venv/bin:$PATH"

COPY --from=builder /venv /venv
COPY ./api /opt/api

WORKDIR /opt/api

EXPOSE 8000
ENTRYPOINT ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-config=uvicorn-log.yml"]
