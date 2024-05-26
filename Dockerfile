FROM python:3.12

COPY refinance /opt/refinance
COPY Pipfile /opt/Pipfile
COPY Pipfile.lock /opt/Pipfile.lock

WORKDIR /opt
RUN pip install pipenv
RUN pipenv install --system

EXPOSE 8000
ENTRYPOINT ["uvicorn", "refinance.app:app", "--host", "0.0.0.0", "--port", "8000"]
