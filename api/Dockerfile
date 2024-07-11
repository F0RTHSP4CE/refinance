FROM python:3.12

COPY . /opt/api

WORKDIR /opt/api
RUN pip install -r requirements.txt

EXPOSE 8000
ENTRYPOINT ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
