FROM python:3.12

COPY . /opt/api

WORKDIR /opt/api
RUN pip install pipenv
RUN pipenv install --system --dev

WORKDIR /opt
EXPOSE 8000
ENTRYPOINT ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
