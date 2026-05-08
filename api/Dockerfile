FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./api /opt/api
COPY pyproject.toml /opt/api/
COPY uv.lock /opt/api/

WORKDIR /opt/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export > requirements.txt && \
    uv pip install --system -r requirements.txt

EXPOSE 8000
RUN chmod +x /opt/api/entrypoint.sh
ENTRYPOINT ["/opt/api/entrypoint.sh"]
