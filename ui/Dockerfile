FROM python:3.12

COPY . /opt/ui

WORKDIR /opt/ui
RUN pip install -r requirements.txt

EXPOSE 5000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:5000", "app.app:app"]
