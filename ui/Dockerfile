FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./ui /opt/ui
COPY pyproject.toml /opt/ui/
COPY uv.lock /opt/ui/

WORKDIR /opt/ui
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export > requirements.txt && \
    uv pip install --system -r requirements.txt

EXPOSE 9000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9000", "app.app:app"]
