ROM python:latest
COPY . ./
WORKDIR /refinance
RUN pip install pipenv && python3 -m pipenv install --system
EXPOSE 8080
ENTRYPOINT ["uvicorn", "refinance.app:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

