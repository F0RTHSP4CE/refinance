FROM python:3.12

COPY . /opt/
ADD ../Pipfile /opt

WORKDIR /opt/ui
RUN pip install pipenv
RUN pipenv install --system --dev

WORKDIR /opt
EXPOSE 5000
ENTRYPOINT ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "ui.app:app"]
