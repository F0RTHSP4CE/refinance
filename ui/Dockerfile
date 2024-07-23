FROM python:3.12

COPY . /opt/ui

WORKDIR /opt/ui
RUN pip install -r requirements.txt

EXPOSE 9000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9000", "app.app:app"]
