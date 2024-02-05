FROM python:3.11.0

ENV PYTEST_ENV=docker

WORKDIR /code

COPY requirements.txt ./

RUN apt-get update
RUN python3 -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /code/requirements.txt

COPY . .


CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]