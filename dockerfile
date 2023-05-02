FROM python:3.10-slim-buster

WORKDIR /

COPY "main.py" "/scene-host/main.py"
COPY "requirements.txt" "/scene-host/requirements.txt"
COPY "src" "/scene-host/src"

RUN apt update
RUN apt-get install git -y
RUN pip install -r /scene-host/requirements.txt

WORKDIR /scene-host

ENTRYPOINT [ "/scene-host/main.py" ]