FROM python:3.12

COPY . /opt

WORKDIR /opt
RUN pip install pipenv
RUN pipenv install --system --dev

EXPOSE 8000
ENTRYPOINT ["uvicorn", "refinance.app:app", "--host", "0.0.0.0", "--port", "8000"]
