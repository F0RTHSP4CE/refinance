FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./api /opt/api
COPY pyproject.toml /opt/api/
COPY uv.lock /opt/api/

WORKDIR /opt/api
RUN uv export > requirements.txt && \
    uv pip install --system -r requirements.txt

EXPOSE 8000
ENTRYPOINT ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-config=uvicorn-log.yml"]
